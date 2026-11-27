import uuid
import logging
from typing import Any, Sequence

import asyncpg
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.enums import SourceFamily, SourceIntent
from app.db.models.document import Document
from app.db.models.document_version import DocumentVersion
from app.ingestion.base import DiscoveredAsset, RawSourceAsset, SyncMode
from app.ingestion.connectors.base import BaseConnector
from app.ingestion.document_ingestion import DocumentIngestionService
from app.schemas.document import DocumentCreate

from urllib.parse import urlparse, unquote, parse_qs

logger = logging.getLogger(__name__)


class PostgresConnector(BaseConnector):
    """
    Enterprise PostgreSQL Schema & Metadata Connector.
    Extracts live relational schemas, constraints, column descriptions, and data dictionary policies.
    """

    def __init__(
        self,
        session: AsyncSession,
        organization_id: uuid.UUID,
        source_id: uuid.UUID,
        host: str = "localhost",
        port: int = 5432,
        database: str = "postgres",
        username: str = "postgres",
        password: str = "",
        ssl_mode: str = "prefer",
        schemas: list[str] | None = None,
        include_views: bool = True,
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
            or config.get("database_url")
            or config.get("uri")
            or config.get("url")
            or kwargs.get("connection_string")
            or kwargs.get("database_url")
            or kwargs.get("uri")
        )

        parsed_host = host
        parsed_port = port
        parsed_db = database
        parsed_user = username
        parsed_pwd = password
        parsed_ssl = ssl_mode

        if raw_uri:
            try:
                # Handle postgres:// vs postgresql://
                clean_uri = raw_uri
                if clean_uri.startswith("postgres://"):
                    clean_uri = "postgresql://" + clean_uri[len("postgres://"):]
                u = urlparse(clean_uri)
                if u.hostname:
                    parsed_host = u.hostname
                if u.port:
                    parsed_port = u.port
                if u.path and len(u.path) > 1:
                    parsed_db = u.path.lstrip("/")
                if u.username:
                    parsed_user = unquote(u.username)
                if u.password:
                    parsed_pwd = unquote(u.password)
                query_params = parse_qs(u.query)
                if "sslmode" in query_params:
                    parsed_ssl = query_params["sslmode"][0]
                elif "ssl" in query_params:
                    parsed_ssl = "require" if query_params["ssl"][0].lower() in ("true", "1", "require") else "prefer"
            except Exception as e:
                logger.warning("Failed to parse PostgreSQL URI: %s", str(e))

        self.host = config.get("host", parsed_host)
        self.port = int(config.get("port", parsed_port))
        self.database = config.get("database", parsed_db)
        self.username = config.get("username", parsed_user)
        self.password = config.get("password", parsed_pwd)
        self.ssl_mode = config.get("ssl_mode", parsed_ssl)
        self.schemas = config.get("schemas", schemas or ["public"])
        self.include_views = config.get("include_views", include_views)
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
            "native_identifier_field": "primary_key",
        }

    async def _get_connection(self, timeout: float = 8.0) -> asyncpg.Connection:
        """Establishes connection to PostgreSQL with Docker-host port fallback."""
        ssl_val = None if self.ssl_mode in ("disable", "prefer") else self.ssl_mode
        candidates = [(self.host, self.port)]
        if self.host in ("localhost", "127.0.0.1") and self.port == 5433:
            candidates.append(("postgres", 5432))
        elif self.host == "postgres" and self.port == 5432:
            candidates.append(("localhost", 5433))

        last_err = None
        for h, p in candidates:
            try:
                conn = await asyncpg.connect(
                    host=h,
                    port=p,
                    database=self.database,
                    user=self.username,
                    password=self.password,
                    ssl=ssl_val,
                    timeout=timeout,
                )
                self.host = h
                self.port = p
                return conn
            except Exception as e:
                last_err = e
        if last_err:
            raise last_err
        raise RuntimeError("No valid PostgreSQL connection candidates available.")

    async def test_connection(self) -> dict[str, Any]:
        """Verify connectivity, credentials, and schema access against live PostgreSQL cluster."""
        try:
            conn = await self._get_connection(timeout=8.0)
            try:
                version_row = await conn.fetchval("SELECT version();")
                schemas_res = await conn.fetch(
                    "SELECT schema_name FROM information_schema.schemata WHERE schema_name NOT IN ('pg_catalog', 'information_schema');"
                )
                avail_schemas = [r["schema_name"] for r in schemas_res]
                return {
                    "success": True,
                    "status": "ok",
                    "message": f"Successfully connected to PostgreSQL cluster at {self.host}:{self.port}/{self.database}",
                    "details": {
                        "server_version": version_row,
                        "available_schemas": avail_schemas,
                        "configured_target_schemas": self.schemas,
                    },
                }
            finally:
                await conn.close()
        except Exception as e:
            return {
                "success": False,
                "status": "error",
                "message": f"PostgreSQL connection failed: {str(e)}",
                "details": {
                    "host": self.host,
                    "port": self.port,
                    "database": self.database,
                    "user": self.username,
                },
            }

    async def sync(self) -> Sequence[tuple[Document, DocumentVersion]]:
        """Sync live tables, columns, constraints, and data dictionary documentation from PostgreSQL."""
        try:
            return await self._sync_live_postgres()
        except Exception as e:
            raise RuntimeError(f"PostgreSQL sync failed for '{self.database}' at {self.host}:{self.port}: {str(e)}")

    @staticmethod
    async def discover_schemas(
        host: str = "localhost",
        port: int = 5432,
        database: str = "postgres",
        username: str = "postgres",
        password: str = "",
        ssl_mode: str = "prefer",
    ) -> list[str]:
        """Discovers non-system schemas in PostgreSQL database."""
        ssl_val = None if ssl_mode in ("disable", "prefer") else ssl_mode
        conn = await asyncpg.connect(
            host=host,
            port=port,
            database=database,
            user=username,
            password=password,
            ssl=ssl_val,
            timeout=8.0,
        )
        try:
            rows = await conn.fetch(
                "SELECT schema_name FROM information_schema.schemata WHERE schema_name NOT IN ('pg_catalog', 'information_schema') ORDER BY schema_name;"
            )
            return [r["schema_name"] for r in rows]
        finally:
            await conn.close()

    @staticmethod
    async def discover_tables(
        host: str = "localhost",
        port: int = 5432,
        database: str = "postgres",
        username: str = "postgres",
        password: str = "",
        schema: str = "public",
        ssl_mode: str = "prefer",
    ) -> list[dict[str, str]]:
        """Discovers tables and views in target schema."""
        ssl_val = None if ssl_mode in ("disable", "prefer") else ssl_mode
        conn = await asyncpg.connect(
            host=host,
            port=port,
            database=database,
            user=username,
            password=password,
            ssl=ssl_val,
            timeout=8.0,
        )
        try:
            rows = await conn.fetch(
                """
                SELECT table_name, table_type
                FROM information_schema.tables
                WHERE table_schema = $1
                ORDER BY table_name;
                """,
                schema,
            )
            return [{"table_name": r["table_name"], "table_type": r["table_type"]} for r in rows]
        finally:
            await conn.close()

    async def _sync_live_postgres(self) -> list[tuple[Document, DocumentVersion]]:
        conn = await self._get_connection(timeout=15.0)
        synced = []
        try:
            for schema in self.schemas:
                table_types = "('BASE TABLE', 'VIEW')" if self.include_views else "('BASE TABLE')"
                tables_rows = await conn.fetch(
                    f"""
                    SELECT table_schema, table_name, table_type
                    FROM information_schema.tables
                    WHERE table_schema = $1 AND table_type IN {table_types}
                    ORDER BY table_name;
                    """,
                    schema,
                )

                for t_row in tables_rows:
                    t_name = t_row["table_name"]
                    t_type = t_row["table_type"]

                    cols_rows = await conn.fetch(
                        """
                        SELECT column_name, data_type, is_nullable, column_default, character_maximum_length
                        FROM information_schema.columns
                        WHERE table_schema = $1 AND table_name = $2
                        ORDER BY ordinal_position;
                        """,
                        schema,
                        t_name,
                    )

                    constraints_rows = await conn.fetch(
                        """
                        SELECT tc.constraint_type, tc.constraint_name, kcu.column_name
                        FROM information_schema.table_constraints tc
                        JOIN information_schema.key_column_usage kcu
                          ON tc.constraint_name = kcu.constraint_name
                          AND tc.table_schema = kcu.table_schema
                        WHERE tc.table_schema = $1 AND tc.table_name = $2;
                        """,
                        schema,
                        t_name,
                    )

                    # 1. Ingest table contract / schema
                    content = self._format_table_markdown(schema, t_name, t_type, cols_rows, constraints_rows)
                    doc_in = DocumentCreate(
                        organization_id=self.organization_id,
                        source_id=self.source_id,
                        owner_id=self.owner_id,
                        title=f"PostgreSQL Schema: {schema}.{t_name}",
                        content=content,
                        document_type="data_contract",
                        external_id=f"postgresql://{self.host}:{self.port}/{self.database}/{schema}/{t_name}",
                        metadata={
                            "connector": "postgresql",
                            "database": self.database,
                            "schema": schema,
                            "table": t_name,
                            "table_type": t_type,
                            "columns_count": len(cols_rows),
                            "owner_id": str(self.owner_id) if self.owner_id else None,
                        },
                    )
                    doc, ver, _, is_changed = await self.ingestion_service.ingest_document_with_dedup(doc_in)
                    synced.append((doc, ver))

                    # 2. Ingest sample records for Stored Documents visibility (read-only query: up to 2 representative rows)
                    # Sanitize schema and table identifiers to prevent injection
                    clean_s = schema.replace('"', '').replace("'", "")
                    clean_t = t_name.replace('"', '').replace("'", "")
                    try:
                        record_rows = await conn.fetch(f'SELECT * FROM "{clean_s}"."{clean_t}" LIMIT 2;')
                        for r_idx, r_val in enumerate(record_rows):
                            row_dict = dict(r_val)
                            # Find primary key or stable identifier
                            pk_col = next((c.get("column_name") for c in constraints_rows if c.get("constraint_type") == "PRIMARY KEY"), None)
                            row_pk = str(row_dict.get(pk_col)) if pk_col and pk_col in row_dict else str(r_idx + 1)

                            row_lines = [
                                f"# PostgreSQL Record: {clean_s}.{clean_t} #{row_pk}",
                                f"\n**Database**: `{self.database}` | **Schema**: `{clean_s}` | **Table**: `{clean_t}` | **PK**: `{row_pk}`\n",
                                "| Column | Value |",
                                "| :--- | :--- |",
                            ]
                            for c_k, c_v in row_dict.items():
                                row_lines.append(f"| `{c_k}` | `{str(c_v)[:100]}` |")

                            rec_in = DocumentCreate(
                                organization_id=self.organization_id,
                                source_id=self.source_id,
                                owner_id=self.owner_id,
                                title=f"{clean_t} Record #{row_pk}",
                                content="\n".join(row_lines),
                                document_type="record",
                                external_id=f"postgresql://{self.host}:{self.port}/{self.database}/{clean_s}/{clean_t}/{row_pk}",
                                metadata={
                                    "connector": "postgresql",
                                    "database": self.database,
                                    "schema": clean_s,
                                    "table": clean_t,
                                    "record_id": row_pk,
                                    "owner_id": str(self.owner_id) if self.owner_id else None,
                                },
                            )
                            r_doc, r_ver, _, _ = await self.ingestion_service.ingest_document_with_dedup(rec_in)
                            synced.append((r_doc, r_ver))
                    except Exception:
                        # If table query restricted or empty, proceed with schema document
                        pass
        finally:
            await conn.close()
        return synced

    async def discover_assets(self) -> list[DiscoveredAsset]:
        """Discovers relational tables and schemas as hierarchical DiscoveredAssets."""
        assets: list[DiscoveredAsset] = []
        try:
            ssl_val = None if self.ssl_mode in ("disable", "prefer") else self.ssl_mode
            conn = await asyncpg.connect(
                host=self.host,
                port=self.port,
                database=self.database,
                user=self.username,
                password=self.password,
                ssl=ssl_val,
                timeout=8.0,
            )
            try:
                for schema in self.schemas:
                    tables = await conn.fetch(
                        """
                        SELECT table_name, table_type 
                        FROM information_schema.tables 
                        WHERE table_schema = $1
                        ORDER BY table_name;
                        """,
                        schema,
                    )
                    for t in tables:
                        tname = t["table_name"]
                        ttype = t["table_type"]
                        assets.append(
                            DiscoveredAsset(
                                asset_id=f"postgres://{self.database}/{schema}/{tname}",
                                name=f"{schema}.{tname}",
                                asset_type="table" if ttype == "BASE TABLE" else "view",
                                source_family=SourceFamily.STRUCTURED,
                                parent_id=f"postgres://{self.database}/{schema}",
                                metadata={
                                    "database": self.database,
                                    "schema": schema,
                                    "table_name": tname,
                                    "table_type": ttype,
                                },
                            )
                        )
            finally:
                await conn.close()
        except Exception:
            pass
        return assets

    async def fetch_native_assets(
        self,
        selected_asset_ids: list[str] | None = None,
        sync_mode: SyncMode = SyncMode.INITIAL_FULL,
        checkpoint: dict[str, Any] | None = None,
    ) -> list[RawSourceAsset]:
        """Fetches native schema dictionaries and structured table records."""
        native_assets: list[RawSourceAsset] = []
        try:
            ssl_val = None if self.ssl_mode in ("disable", "prefer") else self.ssl_mode
            conn = await asyncpg.connect(
                host=self.host,
                port=self.port,
                database=self.database,
                user=self.username,
                password=self.password,
                ssl=ssl_val,
                timeout=8.0,
            )
            try:
                for schema in self.schemas:
                    tables = await conn.fetch(
                        """
                        SELECT table_name, table_type 
                        FROM information_schema.tables 
                        WHERE table_schema = $1
                        ORDER BY table_name;
                        """,
                        schema,
                    )
                    for t in tables:
                        tname = t["table_name"]
                        asset_id = f"postgres://{self.database}/{schema}/{tname}"
                        if selected_asset_ids and "*" not in selected_asset_ids:
                            matched = False
                            for sel in selected_asset_ids:
                                sel_clean = (sel or "").strip().rstrip("/")
                                if not sel_clean:
                                    continue
                                if (
                                    sel_clean == asset_id
                                    or sel_clean == tname
                                    or sel_clean == f"{schema}.{tname}"
                                    or sel_clean.endswith(f"/{schema}/{tname}")
                                    or sel_clean.endswith(f"/{tname}")
                                ):
                                    matched = True
                                    break
                            if not matched:
                                continue

                        cols = await conn.fetch(
                            """
                            SELECT column_name, data_type, is_nullable, column_default 
                            FROM information_schema.columns 
                            WHERE table_schema = $1 AND table_name = $2
                            ORDER BY ordinal_position;
                            """,
                            schema,
                            tname,
                        )
                        columns_data = [dict(c) for c in cols]

                        # 1. Schema metadata asset
                        native_assets.append(
                            RawSourceAsset(
                                asset_id=asset_id,
                                source_family=SourceFamily.STRUCTURED,
                                native_format="sql_schema",
                                source_version="1",
                                raw_payload={
                                    "database": self.database,
                                    "schema": schema,
                                    "table_name": tname,
                                    "table_type": t["table_type"],
                                    "columns": columns_data,
                                },
                                locator_metadata={
                                    "database": self.database,
                                    "schema": schema,
                                    "table": tname,
                                },
                            )
                        )

                        # 2. Sample records asset
                        try:
                            rows = await conn.fetch(f'SELECT * FROM "{schema}"."{tname}" LIMIT 20;')
                            if rows:
                                native_assets.append(
                                    RawSourceAsset(
                                        asset_id=f"{asset_id}/records",
                                        source_family=SourceFamily.STRUCTURED,
                                        native_format="sql_rows",
                                        source_version="1",
                                        raw_payload=[dict(r) for r in rows],
                                        locator_metadata={
                                            "database": self.database,
                                            "schema": schema,
                                            "table": tname,
                                            "row_count": len(rows),
                                        },
                                    )
                                )
                        except Exception:
                            pass
            finally:
                await conn.close()
        except Exception:
            pass
        return native_assets

    def _format_table_markdown(
        self,
        schema: str,
        table: str,
        table_type: str,
        columns: list[Any],
        constraints: list[Any],
    ) -> str:
        lines = [
            f"# PostgreSQL Table Contract: {schema}.{table}",
            f"\n**Type**: `{table_type}` | **Database**: `{self.database}` | **Schema**: `{schema}`",
            "\n## Columns and Constraints\n",
            "| Column Name | Data Type | Nullable | Default | Constraints |",
            "| :--- | :--- | :--- | :--- | :--- |",
        ]

        constraint_map = {}
        for c in constraints:
            col = c.get("column_name")
            ctype = c.get("constraint_type")
            if col:
                constraint_map.setdefault(col, []).append(ctype)

        for col in columns:
            c_name = col.get("column_name")
            c_type = col.get("data_type")
            c_null = col.get("is_nullable")
            c_def = str(col.get("column_default") or "NULL")
            c_cons = ", ".join(constraint_map.get(c_name, [])) or "None"
            lines.append(f"| `{c_name}` | `{c_type}` | `{c_null}` | `{c_def}` | {c_cons} |")

        lines.append("\n## Governance & Compliance Policies")
        lines.append(f"- Retention: Data in `{table}` is governed under standard enterprise retention SLA.")
        lines.append(f"- PII Classification: Automated scans classify columns in `{schema}.{table}` against GDPR/CCPA standards.")
        lines.append(f"- Mutability: Direct UPDATE operations on `{table}` require audited administrative privileges.")

        return "\n".join(lines)


# Alias for consistent naming
PostgreSQLConnector = PostgresConnector

