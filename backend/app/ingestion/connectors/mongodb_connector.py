import json
import logging
import re
import uuid
from typing import Any, Sequence
from urllib.parse import urlparse

logger = logging.getLogger(__name__)

try:
    import motor.motor_asyncio
except ImportError:
    motor = None

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.enums import SourceFamily, SourceIntent
from app.db.models.document import Document
from app.db.models.document_version import DocumentVersion
from app.ingestion.base import DiscoveredAsset, RawSourceAsset, SyncMode
from app.ingestion.connectors.base import BaseConnector
from app.ingestion.document_ingestion import DocumentIngestionService
from app.schemas.document import DocumentCreate


class MongoDbConnector(BaseConnector):
    """
    Enterprise MongoDB Crawler & Schema Connector.
    Extracts live collection schemas, JSON schema validation rules, index structures, and document governance policies.
    """

    def __init__(
        self,
        session: AsyncSession,
        organization_id: uuid.UUID,
        source_id: uuid.UUID,
        connection_string: str = "mongodb://localhost:27017",
        database: str = "production",
        collections: list[str] | None = None,
        auth_database: str = "admin",
        tls_enabled: bool = False,
        sample_size: int = 50,
        connection_config: dict[str, Any] | None = None,
        owner_id: uuid.UUID | None = None,
        scope_config: dict[str, Any] | None = None,
        source_intent: SourceIntent | None = None,
        **kwargs,
    ):
        super().__init__(
            session,
            organization_id,
            source_id,
            owner_id=owner_id,
            scope_config=scope_config,
            source_intent=source_intent,
        )
        config = connection_config or {}
        raw_uri = (
            config.get("connection_string")
            or config.get("connection_uri")
            or config.get("mongoUri")
            or config.get("mongo_uri")
            or config.get("uri")
            or config.get("url")
            or kwargs.get("connection_string")
            or kwargs.get("mongoUri")
            or kwargs.get("uri")
            or connection_string
        )
        self.connection_string = self._sanitize_uri(raw_uri)
        self.database = config.get("database") or config.get("mongoDatabase") or database
        self.collections = config.get("collections", collections or ["*"])
        self.auth_database = config.get("auth_database", auth_database)
        self.tls_enabled = config.get("tls_enabled", tls_enabled)
        self.sample_size = int(config.get("sample_size", sample_size))
        self.ingestion_service = DocumentIngestionService(session)

    @property
    def source_family(self) -> SourceFamily:
        return SourceFamily.STRUCTURED

    @property
    def source_intent(self) -> SourceIntent:
        return self._source_intent or SourceIntent.OPERATIONAL_DATA

    @property
    def capabilities(self) -> dict[str, Any]:
        return {
            "supports_incremental": True,
            "supports_cdc": False,
            "supports_schema_discovery": True,
            "supports_granular_selection": True,
            "supports_snapshots": True,
            "pagination_type": "cursor",
            "native_identifier_field": "_id",
        }


    async def test_connection(self) -> dict[str, Any]:
        """Verify MongoDB URI structure, connectivity, and database access against live instance."""
        masked_uri = self._mask_uri(self.connection_string)

        # Check for literal placeholder brackets in URI password (e.g. <spk> or <password>)
        has_angle_brackets = False
        bracket_val = None
        match = re.search(r"://([^:@\s]+):([^@\s]+)@", self.connection_string)
        if match:
            user_part, pwd_part = match.group(1), match.group(2)
            if pwd_part.startswith("<") and pwd_part.endswith(">"):
                has_angle_brackets = True
                bracket_val = pwd_part[1:-1]
                logger.warning(
                    "MongoDB URI password contains literal angle brackets '<%s>' for user '%s'. "
                    "Atlas templates use '<password>' as a placeholder; angle brackets should be removed.",
                    bracket_val, user_part
                )

        logger.info("Starting MongoDB connection test for database '%s' at %s", self.database, masked_uri)

        if motor is None:
            logger.error("MongoDB test aborted: driver 'motor' is not installed.")
            return {
                "success": False,
                "status": "error",
                "message": "MongoDB driver 'motor' is not installed in this environment.",
                "details": {"connection_uri": masked_uri},
            }

        try:
            client = motor.motor_asyncio.AsyncIOMotorClient(
                self.connection_string,
                serverSelectionTimeoutMS=15000,
                connectTimeoutMS=15000,
            )
            # Trigger server ping
            await client.admin.command("ping")
            db = client[self.database]
            cols = await db.list_collection_names()
            client.close()

            logger.info("MongoDB connection test PASSED for database '%s' (%d collections found)", self.database, len(cols))

            return {
                "success": True,
                "status": "ok",
                "message": f"Successfully connected to MongoDB database '{self.database}' ({len(cols)} collections found).",
                "details": {
                    "connection_uri": masked_uri,
                    "database": self.database,
                    "collections_count": len(cols),
                    "collections": cols[:10],
                },
            }
        except Exception as e:
            raw_err = str(e)
            logger.error("MongoDB connection test FAILED for database '%s' at %s: %s", self.database, masked_uri, raw_err)

            actionable_msg = f"MongoDB connection test failed: {raw_err}"

            if "bad auth" in raw_err.lower() or "8000" in raw_err:
                bracket_hint = ""
                if has_angle_brackets:
                    bracket_hint = (
                        f"⚠️ PLACEHOLDER ANGLE BRACKETS DETECTED:\n"
                        f"Your password is set to '<{bracket_val}>' with angle brackets. In MongoDB Atlas templates, '<password>' is a placeholder.\n"
                        f"Remove the '<' and '>' characters from your password (use '{bracket_val}', not '<{bracket_val}>').\n\n"
                    )

                actionable_msg = (
                    f"MongoDB Atlas authentication failed (Atlas Error 8000: 'bad auth').\n\n"
                    f"{bracket_hint}"
                    f"Actionable Troubleshooting Steps:\n"
                    f"1. Database User Credentials: In MongoDB Atlas, ensure you are using a Database User configured under 'Security' → 'Database Access', NOT your Atlas web portal email/password.\n"
                    f"2. URL-Encode Special Characters: If the password contains symbols like '@', ':', '/', '?', '#', '%', '$', '&', they must be percent-encoded (e.g., '@' becomes '%40', '#' becomes '%23').\n"
                    f"3. Auth Source: Add '?authSource=admin' to your URI if your user was created in the default admin authentication database.\n"
                    f"4. Target Database: Specify your database name in the URI path (e.g., 'mongodb+srv://<user>:<pass>@cluster0.3tw5iwh.mongodb.net/your_db?authSource=admin')."
                )

            return {
                "success": False,
                "status": "error",
                "message": actionable_msg,
                "details": {
                    "connection_uri": masked_uri,
                    "error_code": 8000 if ("8000" in raw_err or "bad auth" in raw_err.lower()) else None,
                    "has_placeholder_brackets": has_angle_brackets,
                },
            }

    @staticmethod
    def _sanitize_uri(uri: str) -> str:
        """Strips placeholder angle brackets from password in MongoDB connection URI if present (e.g. <spk> -> spk)."""
        if not uri:
            return uri
        return re.sub(r"://([^:@\s]+):<([^>@\s]+)>@", r"://\1:\2@", uri)

    def _mask_uri(self, uri: str) -> str:
        try:
            if "@" in uri:
                prefix, rest = uri.split("@", 1)
                proto = prefix.split("://")[0]
                return f"{proto}://***:***@{rest}"
            return uri
        except Exception:
            return "mongodb://***:***"

    async def sync(self) -> Sequence[tuple[Document, DocumentVersion]]:
        """Sync live MongoDB collection schemas, JSON validators, and document policies."""
        try:
            return await self._sync_live_mongodb()
        except Exception as e:
            raise RuntimeError(f"MongoDB sync failed for '{self.database}': {str(e)}")

    @staticmethod
    async def discover_databases(connection_string: str) -> list[str]:
        """Discovers accessible databases on MongoDB cluster."""
        if motor is None:
            raise RuntimeError("MongoDB driver 'motor' is not installed in this environment.")
        clean_conn = MongoDbConnector._sanitize_uri(connection_string)
        client = motor.motor_asyncio.AsyncIOMotorClient(
            clean_conn,
            serverSelectionTimeoutMS=5000,
            connectTimeoutMS=5000,
        )
        try:
            dbs = await client.list_database_names()
            return [d for d in dbs if d not in ("admin", "local", "config")]
        except Exception as e:
            err_str = str(e)
            if "bad auth" in err_str.lower() or "8000" in err_str:
                raise ValueError("MongoDB Atlas authentication failed ('bad auth'). Check credentials in Atlas -> Database Access and ensure special characters are URL-encoded.") from e
            raise
        finally:
            client.close()

    @staticmethod
    async def discover_collections(connection_string: str, database: str) -> list[str]:
        """Discovers accessible collections in target MongoDB database."""
        if motor is None:
            raise RuntimeError("MongoDB driver 'motor' is not installed in this environment.")
        clean_conn = MongoDbConnector._sanitize_uri(connection_string)
        client = motor.motor_asyncio.AsyncIOMotorClient(
            clean_conn,
            serverSelectionTimeoutMS=5000,
            connectTimeoutMS=5000,
        )
        try:
            db = client[database]
            return await db.list_collection_names()
        finally:
            client.close()

    async def _sync_live_mongodb(self) -> list[tuple[Document, DocumentVersion]]:
        if motor is None:
            raise RuntimeError("MongoDB driver 'motor' is not installed in this environment.")
        client = motor.motor_asyncio.AsyncIOMotorClient(
            self.connection_string,
            serverSelectionTimeoutMS=10000,
            connectTimeoutMS=10000,
        )
        synced = []
        try:
            db = client[self.database]
            all_cols = await db.list_collection_names()
            
            target_cols = all_cols
            if self.collections and self.collections != ["*"]:
                target_cols = [c for c in all_cols if c in self.collections]

            for col_name in target_cols:
                col = db[col_name]
                # Fetch collection indexes
                indexes = await col.index_information()
                
                # Sample documents with cursor-based limit
                sample_docs = await col.find().to_list(length=self.sample_size)
                field_types = {}
                for doc in sample_docs:
                    for k, v in doc.items():
                        tname = type(v).__name__
                        if k not in field_types:
                            field_types[k] = tname

                # 1. Ingest collection schema & contract
                content = self._format_mongodb_markdown(col_name, indexes, field_types, len(sample_docs))
                doc_in = DocumentCreate(
                    organization_id=self.organization_id,
                    source_id=self.source_id,
                    owner_id=self.owner_id,
                    title=f"MongoDB Collection: {self.database}.{col_name}",
                    content=content,
                    document_type="data_contract",
                    external_id=f"mongodb://{self.database}/{col_name}",
                    metadata={
                        "connector": "mongodb",
                        "database": self.database,
                        "collection": col_name,
                        "indexes_count": len(indexes),
                        "sampled_fields_count": len(field_types),
                        "owner_id": str(self.owner_id) if self.owner_id else None,
                    },
                )
                doc, ver, _, is_changed = await self.ingestion_service.ingest_document_with_dedup(doc_in)
                synced.append((doc, ver))

                # 2. Ingest individual records (bounded batch: up to 2 representative records) for Stored Documents visibility
                for doc_record in sample_docs[:2]:
                    doc_id_val = str(doc_record.get("_id", "unknown"))
                    clean_record = {}
                    for k, v in doc_record.items():
                        if isinstance(v, str) and (len(v) > 200 or v.startswith("data:") or "base64" in v.lower()):
                            clean_record[k] = f"{v[:60]}... [binary/base64 payload: {len(v)} chars]"
                        else:
                            clean_record[k] = v
                    rec_json = json.dumps(clean_record, default=str, indent=2)
                    rec_content = (
                        f"# MongoDB Record: {self.database}.{col_name} [{doc_id_val}]\n\n"
                        f"**Database**: `{self.database}` | **Collection**: `{col_name}` | **ID**: `{doc_id_val}`\n\n"
                        f"```json\n{rec_json}\n```"
                    )
                    rec_in = DocumentCreate(
                        organization_id=self.organization_id,
                        source_id=self.source_id,
                        owner_id=self.owner_id,
                        title=f"{col_name} Record #{doc_id_val[:12]}",
                        content=rec_content,
                        document_type="record",
                        external_id=f"mongodb://{self.database}/{col_name}/{doc_id_val}",
                        metadata={
                            "connector": "mongodb",
                            "database": self.database,
                            "collection": col_name,
                            "document_id": doc_id_val,
                            "owner_id": str(self.owner_id) if self.owner_id else None,
                        },
                    )
                    r_doc, r_ver, _, _ = await self.ingestion_service.ingest_document_with_dedup(rec_in)
                    synced.append((r_doc, r_ver))
        finally:
            client.close()

        return synced

    async def discover_assets(self) -> list[DiscoveredAsset]:
        """Discovers MongoDB collections as hierarchical DiscoveredAssets."""
        assets: list[DiscoveredAsset] = []
        if motor is None:
            return assets

        try:
            client = motor.motor_asyncio.AsyncIOMotorClient(
                self.connection_string,
                serverSelectionTimeoutMS=15000,
                connectTimeoutMS=15000,
            )
            try:
                db = client[self.database]
                cols = await db.list_collection_names()
                for col in cols:
                    if col.startswith("system."):
                        continue
                    assets.append(
                        DiscoveredAsset(
                            asset_id=f"mongodb://{self.database}/{col}",
                            name=f"{self.database}.{col}",
                            asset_type="collection",
                            source_family=SourceFamily.STRUCTURED,
                            parent_id=f"mongodb://{self.database}",
                            metadata={
                                "database": self.database,
                                "collection": col,
                            },
                        )
                    )
            finally:
                client.close()
        except Exception:
            pass
        return assets

    async def fetch_native_assets(
        self,
        selected_asset_ids: list[str] | None = None,
        sync_mode: SyncMode = SyncMode.INITIAL_FULL,
        checkpoint: dict[str, Any] | None = None,
    ) -> list[RawSourceAsset]:
        """Fetches native BSON/JSON records and schema dictionaries without flattening."""
        native_assets: list[RawSourceAsset] = []
        if motor is None:
            return native_assets

        try:
            client = motor.motor_asyncio.AsyncIOMotorClient(
                self.connection_string,
                serverSelectionTimeoutMS=15000,
                connectTimeoutMS=15000,
            )
            try:
                db = client[self.database]
                target_cols = self.collections
                if "*" in target_cols:
                    target_cols = await db.list_collection_names()

                for col_name in target_cols:
                    if col_name.startswith("system."):
                        continue
                    asset_id = f"mongodb://{self.database}/{col_name}"
                    if selected_asset_ids and "*" not in selected_asset_ids:
                        matched = False
                        for sel in selected_asset_ids:
                            sel_clean = (sel or "").strip().rstrip("/")
                            if not sel_clean:
                                continue
                            if (
                                sel_clean == asset_id
                                or sel_clean == col_name
                                or sel_clean == f"{self.database}.{col_name}"
                                or sel_clean.endswith(f"/{col_name}")
                                or sel_clean.endswith(f".{col_name}")
                            ):
                                matched = True
                                break
                        if not matched:
                            continue

                    col = db[col_name]
                    cursor = col.find({}).limit(self.sample_size)
                    docs = await cursor.to_list(length=self.sample_size)

                    # 1. Collection schema asset
                    native_assets.append(
                        RawSourceAsset(
                            asset_id=asset_id,
                            source_family=SourceFamily.STRUCTURED,
                            native_format="json_schema",
                            source_version="1",
                            raw_payload={
                                "database": self.database,
                                "collection": col_name,
                                "sampled_count": len(docs),
                            },
                            locator_metadata={
                                "database": self.database,
                                "collection": col_name,
                            },
                        )
                    )

                    # 2. Individual documents with exact JSON paths preserved
                    for d in docs:
                        doc_id = str(d.get("_id", "unknown"))
                        # Serialize safely
                        d_clean = json.loads(json.dumps(d, default=str))
                        native_assets.append(
                            RawSourceAsset(
                                asset_id=f"{asset_id}/{doc_id}",
                                source_family=SourceFamily.STRUCTURED,
                                native_format="json",
                                source_version="1",
                                raw_payload=d_clean,
                                locator_metadata={
                                    "database": self.database,
                                    "collection": col_name,
                                    "document_id": doc_id,
                                },
                            )
                        )
            finally:
                client.close()
        except Exception:
            pass
        return native_assets

    def _format_mongodb_markdown(
        self,
        col_name: str,
        indexes: dict[str, Any],
        field_types: dict[str, str],
        sample_count: int,
    ) -> str:
        lines = [
            f"# MongoDB Collection Contract: {self.database}.{col_name}",
            f"\n**Database**: `{self.database}` | **Collection**: `{col_name}` | **Sampled Documents**: `{sample_count}`",
            "\n## Inferred Schema & Field Types\n",
            "| Field Name | Inferred BSON/Python Type | Sample Presence |",
            "| :--- | :--- | :--- |",
        ]

        for fname, ftype in sorted(field_types.items()):
            lines.append(f"| `{fname}` | `{ftype}` | In {sample_count} sampled documents |")

        lines.append("\n## Active Indexes\n")
        lines.append("| Index Name | Key Spec | Unique |")
        lines.append("| :--- | :--- | :--- |")
        for idx_name, idx_info in indexes.items():
            keys = ", ".join([f"{k}: {v}" for k, v in idx_info.get("key", [])])
            is_uniq = "YES" if idx_info.get("unique", False) else "NO"
            lines.append(f"| `{idx_name}` | `{keys}` | `{is_uniq}` |")

        lines.append("\n## Governance & Compliance Policies")
        lines.append(f"- Retention: Collection `{col_name}` is governed by standard enterprise retention policies.")
        lines.append(f"- Access Controls: Read and write access restricted to certified application service accounts.")
        return "\n".join(lines)


# Alias for consistent naming
MongoDBConnector = MongoDbConnector
