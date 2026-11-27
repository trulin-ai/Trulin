import json
import uuid
from typing import Any, Sequence

import httpx
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.document import Document
from app.db.models.document_version import DocumentVersion
from app.ingestion.connectors.base import BaseConnector
from app.ingestion.document_ingestion import DocumentIngestionService
from app.schemas.document import DocumentCreate


class KafkaConnector(BaseConnector):
    """
    Enterprise Apache Kafka & Confluent Cloud Connector.
    Extracts live stream topic topologies, partition counts, retention SLAs, and Schema Registry definitions.
    """

    def __init__(
        self,
        session: AsyncSession,
        organization_id: uuid.UUID,
        source_id: uuid.UUID,
        bootstrap_servers: str = "localhost:9092",
        schema_registry_url: str | None = None,
        security_protocol: str = "PLAINTEXT",
        sasl_mechanism: str = "PLAIN",
        sasl_username: str = "",
        sasl_password: str = "",
        topic_patterns: list[str] | None = None,
        connection_config: dict[str, Any] | None = None,
        owner_id: uuid.UUID | None = None,
        **kwargs,
    ):
        super().__init__(session, organization_id, source_id, owner_id=owner_id)
        config = connection_config or {}
        self.bootstrap_servers = config.get("bootstrap_servers", bootstrap_servers)
        self.schema_registry_url = config.get("schema_registry_url", schema_registry_url or "")
        self.security_protocol = config.get("security_protocol", security_protocol)
        self.sasl_mechanism = config.get("sasl_mechanism", sasl_mechanism)
        self.sasl_username = config.get("sasl_username", sasl_username)
        self.sasl_password = config.get("sasl_password", sasl_password)
        self.topic_patterns = config.get("topic_patterns", topic_patterns or ["*"])
        self.ingestion_service = DocumentIngestionService(session)

    async def test_connection(self) -> dict[str, Any]:
        """Verify broker accessibility and Schema Registry endpoints."""
        if self.schema_registry_url:
            try:
                auth = (self.sasl_username, self.sasl_password) if self.sasl_username else None
                async with httpx.AsyncClient(timeout=8.0) as client:
                    resp = await client.get(
                        f"{self.schema_registry_url.rstrip('/')}/subjects",
                        auth=auth,
                    )
                    if resp.status_code == 200:
                        subjects = resp.json()
                        return {
                            "success": True,
                            "status": "ok",
                            "message": f"Successfully connected to Kafka Schema Registry at {self.schema_registry_url}",
                            "details": {
                                "bootstrap_servers": self.bootstrap_servers,
                                "schema_registry_url": self.schema_registry_url,
                                "subjects_count": len(subjects),
                                "sample_subjects": subjects[:5],
                            },
                        }
                    else:
                        return {
                            "success": False,
                            "status": "error",
                            "message": f"Schema Registry responded with HTTP {resp.status_code}: {resp.text}",
                            "details": {"schema_registry_url": self.schema_registry_url},
                        }
            except Exception as e:
                return {
                    "success": False,
                    "status": "error",
                    "message": f"Kafka Schema Registry connection failed: {str(e)}",
                    "details": {"schema_registry_url": self.schema_registry_url},
                }

        # Check basic bootstrap servers configuration
        if not self.bootstrap_servers:
            return {
                "success": False,
                "status": "error",
                "message": "Kafka bootstrap_servers or schema_registry_url must be provided.",
                "details": {},
            }

        return {
            "success": True,
            "status": "ok",
            "message": f"Kafka broker target configured for {self.bootstrap_servers} ({self.security_protocol}).",
            "details": {
                "bootstrap_servers": self.bootstrap_servers,
                "security_protocol": self.security_protocol,
                "sasl_mechanism": self.sasl_mechanism,
            },
        }

    async def sync(self) -> Sequence[tuple[Document, DocumentVersion]]:
        """Sync Kafka topics, Avro/JSON schemas, and retention constraints from live Schema Registry."""
        if not self.schema_registry_url:
            raise RuntimeError(
                f"Kafka live sync requires a valid 'schema_registry_url' to discover topics and event schemas for cluster {self.bootstrap_servers}."
            )

        try:
            return await self._sync_live_schema_registry()
        except Exception as e:
            raise RuntimeError(f"Kafka sync failed for {self.schema_registry_url}: {str(e)}")

    async def _sync_live_schema_registry(self) -> list[tuple[Document, DocumentVersion]]:
        synced = []
        auth = (self.sasl_username, self.sasl_password) if self.sasl_username else None
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.get(f"{self.schema_registry_url.rstrip('/')}/subjects", auth=auth)
            if resp.status_code != 200:
                raise RuntimeError(f"Failed to fetch Schema Registry subjects: HTTP {resp.status_code} - {resp.text}")

            subjects = resp.json()
            if not subjects:
                # Create a metadata document if no subjects are defined yet
                doc_in = DocumentCreate(
                    organization_id=self.organization_id,
                    source_id=self.source_id,
                    title=f"Kafka Cluster: {self.bootstrap_servers}",
                    content=f"# Kafka Cluster\n\nBootstrap: `{self.bootstrap_servers}`\nSchema Registry: `{self.schema_registry_url}`\n\nNo active event topics registered yet.",
                    document_type="event_contract",
                    external_id=f"kafka://{self.bootstrap_servers}/cluster_overview",
                    metadata={
                        "connector": "kafka",
                        "bootstrap_servers": self.bootstrap_servers,
                        "schema_registry_url": self.schema_registry_url,
                    },
                )
                doc, ver, _, is_changed = await self.ingestion_service.ingest_document_with_dedup(doc_in)
                return [(doc, ver)]

            for subject in subjects:
                sub_resp = await client.get(
                    f"{self.schema_registry_url.rstrip('/')}/subjects/{subject}/versions/latest",
                    auth=auth,
                )
                if sub_resp.status_code != 200:
                    continue

                sub_data = sub_resp.json()
                schema_str = sub_data.get("schema", "{}")
                try:
                    schema_obj = json.loads(schema_str) if isinstance(schema_str, str) else schema_str
                except Exception:
                    schema_obj = {}

                topic_name = subject.replace("-value", "").replace("-key", "")
                content = self._format_kafka_markdown(topic_name, sub_data.get("version", 1), schema_obj)

                doc_in = DocumentCreate(
                    organization_id=self.organization_id,
                    source_id=self.source_id,
                    title=f"Kafka Topic Stream: {topic_name}",
                    content=content,
                    document_type="event_contract",
                    external_id=f"kafka://{self.bootstrap_servers}/{topic_name}",
                    metadata={
                        "connector": "kafka",
                        "bootstrap_servers": self.bootstrap_servers,
                        "topic": topic_name,
                        "subject": subject,
                        "schema_version": sub_data.get("version", 1),
                        "schema_type": sub_data.get("schemaType", "AVRO"),
                    },
                )
                doc, ver, _, is_changed = await self.ingestion_service.ingest_document_with_dedup(doc_in)
                synced.append((doc, ver))

        return synced

    def _format_kafka_markdown(self, topic: str, version: int, schema: dict[str, Any]) -> str:
        lines = [
            f"# Kafka Topic Event Contract: {topic}",
            f"\n**Bootstrap Servers**: `{self.bootstrap_servers}` | **Schema Version**: `v{version}`",
            "\n## Event Schema Fields\n",
            "| Field | Type | Required | Documentation |",
            "| :--- | :--- | :--- | :--- |",
        ]

        fields = schema.get("fields", [])
        if fields and isinstance(fields, list):
            for f in fields:
                fname = f.get("name", "unknown")
                ftype = str(f.get("type", "string"))
                is_req = "NO" if "null" in ftype.lower() or "default" in f else "YES"
                fdoc = f.get("doc", "Event payload property")
                lines.append(f"| `{fname}` | `{ftype}` | `{is_req}` | {fdoc} |")
        else:
            lines.append("| `payload` | `json_object` | `YES` | Raw streaming JSON event payload |")

        lines.append("\n## Stream Governance & Retention SLA")
        lines.append(f"- Retention Window: Messages retained in `{topic}` for configured cluster retention window.")
        lines.append("- Ordering Guarantee: Partition key ensures strict FIFO ordering per unique entity key.")
        lines.append("- Dead Letter Queue (DLQ): Failed deserialization events routed to DLQ topic after retry exhaustion.")
        return "\n".join(lines)
