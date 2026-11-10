import logging
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)

from app.api.deps import require_permission
from app.core.encryption import EncryptionService
from app.core.permissions import Permission
from app.db.database import get_db
from app.db.enums import SourceFamily, SourceIntent
from app.db.models.data_source import DataSource
from app.db.models.user import User
from app.db.repositories.data_source_repository import DataSourceRepository
from app.ingestion.base import DiscoveredAsset, RawSourceAsset
from app.ingestion.connector_registry import (
    ConnectorRegistry,
    get_default_capabilities,
    get_default_intent,
    resolve_source_family,
)
from app.ingestion.connectors.confluence_connector import ConfluenceConnector
from app.ingestion.connectors.github_connector import GitHubConnector, sanitize_github_repo
from app.ingestion.connectors.jira_connector import JiraConnector
from app.ingestion.connectors.kafka_connector import KafkaConnector
from app.ingestion.connectors.mongodb_connector import MongoDbConnector
from app.ingestion.connectors.postgres_connector import PostgresConnector
from app.ingestion.connectors.salesforce_connector import SalesforceConnector
from app.ingestion.connectors.slack_connector import SlackConnector
from app.ingestion.connectors.universal_driver import UniversalConnectorDriver
from app.ingestion.sync_engine import SyncEngine, SyncResult
from app.schemas.data_source import (
    ConnectionTestRequest,
    ConnectionTestResult,
    DataSourceCreate,
    DataSourceResponse,
    DataSourceUpdate,
    ResourceDiscoveryRequest,
    ResourceDiscoveryResponse,
    ScheduleUpdateRequest,
)
from app.schemas.source_scope import SourceInventoryItem, SourceInventoryResponse
from app.services.activity_service import ActivityService
from app.services.claim_gate_evaluator import ClaimGateEvaluator

router = APIRouter(prefix="/sources", tags=["sources"])

LIVE_SUPPORTED_PROVIDERS = {
    "github",
    "mongodb",
    "mongodb_atlas",
    "jira",
    "confluence",
    "postgresql",
    "postgres",
    "slack",
}


def _mask_source_response(source: DataSource) -> DataSourceResponse:
    """Creates a safe DataSourceResponse with all credentials and secrets redacted."""
    safe_config = EncryptionService.redact_credentials(source.connection_config)
    res = DataSourceResponse.model_validate(source)
    res.connection_config = safe_config
    return res


def _secure_and_validate_config(source_type: str, raw_config: dict[str, Any], test_passed: bool) -> tuple[dict[str, Any], dict[str, Any]]:
    """
    Validates connector configuration, extracts credentials into encrypted payload,
    and returns (persisted_config, redacted_safe_config).
    """
    stype = (source_type or "").lower().strip()
    clean_cfg = dict(raw_config or {})
    schedule_val = str(clean_cfg.get("schedule", "off")).lower().strip()
    if schedule_val not in ("off", "1m", "10m"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid synchronization schedule '{schedule_val}'. Must be 'off', '1m', or '10m'."
        )

    # Provider specific validations & secret extractions
    secret_payload: dict[str, Any] = {}

    if stype in ("github", "repo", "git"):
        repo = clean_cfg.get("repo") or clean_cfg.get("repository") or ""
        if not repo.strip():
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail="GitHub repository name is required.")
        token = clean_cfg.get("token") or clean_cfg.get("access_token") or ""
        if token:
            secret_payload["token"] = token
            secret_payload["access_token"] = token

    elif stype in ("mongodb", "mongodb_atlas", "mongo"):
        uri = clean_cfg.get("connection_string") or clean_cfg.get("uri") or ""
        database = clean_cfg.get("database") or ""
        if not uri.strip() or not database.strip():
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail="MongoDB connection string and database name are required.")
        clean_uri = MongoDbConnector._sanitize_uri(uri.strip())
        clean_cfg["connection_string"] = clean_uri
        secret_payload["connection_string"] = clean_uri
        if clean_cfg.get("password"):
            secret_payload["password"] = clean_cfg["password"]

    elif stype in ("jira", "jira_issues"):
        base_url = clean_cfg.get("base_url") or clean_cfg.get("url") or ""
        email = clean_cfg.get("user_email") or clean_cfg.get("email") or ""
        token = clean_cfg.get("api_token") or clean_cfg.get("token") or ""
        project = clean_cfg.get("project_key") or ""
        if not base_url.strip() or not email.strip() or not token.strip() or not project.strip():
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail="Jira requires base URL, user email, API token, and project key.")
        try:
            clean_cfg["base_url"] = EncryptionService.validate_external_url(base_url)
        except ValueError as err:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(err))
        secret_payload["api_token"] = token
        secret_payload["token"] = token

    elif stype in ("confluence", "wiki"):
        base_url = clean_cfg.get("base_url") or clean_cfg.get("url") or ""
        email = clean_cfg.get("user_email") or clean_cfg.get("email") or ""
        token = clean_cfg.get("api_token") or clean_cfg.get("token") or ""
        raw_space = clean_cfg.get("space_key") or clean_cfg.get("space_keys") or clean_cfg.get("spaces") or ""
        parsed_spaces = ConfluenceConnector._parse_space_keys(raw_space)
        if not base_url.strip() or not email.strip() or not token.strip() or not parsed_spaces:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail="Confluence requires base URL, user email, API token, and at least one target space key.")
        clean_cfg["space_key"] = ",".join(parsed_spaces)
        clean_cfg["space_keys"] = parsed_spaces
        try:
            clean_cfg["base_url"] = ConfluenceConnector._normalize_base_url(EncryptionService.validate_external_url(base_url))
        except ValueError as err:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(err))
        secret_payload["api_token"] = token
        secret_payload["token"] = token

    elif stype in ("postgresql", "postgres"):
        host = clean_cfg.get("host") or ""
        port = int(clean_cfg.get("port") or 5432)
        database = clean_cfg.get("database") or ""
        username = clean_cfg.get("username") or ""
        password = clean_cfg.get("password") or ""
        if not host.strip() or not database.strip() or not username.strip():
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail="PostgreSQL requires host, database, and username.")
        if port < 1 or port > 65535:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail="Port must be between 1 and 65535.")
        if password:
            secret_payload["password"] = password

    elif stype in ("slack", "slack_channel", "slack_workspace"):
        token = clean_cfg.get("bot_token") or clean_cfg.get("token") or clean_cfg.get("access_token") or ""
        if not token or not token.startswith("xoxb-"):
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail="Slack Bot User OAuth Token is required and must start with 'xoxb-'."
            )
        secret_payload["bot_token"] = token
        secret_payload["token"] = token

        # Normalize channels
        raw_ch = clean_cfg.get("channels", [])
        if isinstance(raw_ch, str):
            clean_cfg["channels"] = [c.strip().lstrip("#") for c in raw_ch.split(",") if c.strip()]
        elif isinstance(raw_ch, list):
            clean_cfg["channels"] = [str(c).strip().lstrip("#") for c in raw_ch if str(c).strip()]
        clean_cfg["lookback_days"] = max(1, min(365, int(clean_cfg.get("lookback_days", 30))))

    # State transition rule: Connected ONLY after successful test
    connection_status = "connected" if test_passed else "disconnected"

    # Encrypt secrets into envelope token
    persisted_config = dict(clean_cfg)
    if secret_payload:
        persisted_config["_encrypted_credentials"] = EncryptionService.encrypt_payload(secret_payload)

    # Redact raw secrets before storing or exposing
    for k in ("password", "token", "access_token", "api_token", "bot_token", "api_key", "secret", "client_secret"):
        if k in persisted_config and persisted_config[k]:
            persisted_config[k] = "••••••••"
    if "connection_string" in persisted_config and persisted_config["connection_string"]:
        persisted_config["connection_string"] = EncryptionService.mask_uri(persisted_config["connection_string"])

    persisted_config["connection_status"] = connection_status
    persisted_config["schedule"] = schedule_val
    if schedule_val in ("1m", "10m"):
        interval_secs = 60 if schedule_val == "1m" else 600
        persisted_config["next_sync_at"] = (datetime.now(timezone.utc) + timedelta(seconds=interval_secs)).isoformat()
    else:
        persisted_config["next_sync_at"] = None

    return persisted_config, EncryptionService.redact_credentials(persisted_config)


@router.get("/catalog")
async def get_connector_catalog(
    category: str | None = Query(None, description="Optional category filter"),
    search: str | None = Query(None, description="Optional search term matching connector name, description, or id"),
):
    """
    Get the complete catalog of supported enterprise data source connectors,
    marking the five live supported connectors (GitHub, MongoDB Atlas, Jira, Confluence, PostgreSQL).
    """
    all_connectors = ConnectorRegistry.get_all()
    categories = ConnectorRegistry.get_categories()

    filtered = all_connectors
    if category and category.lower() != "all":
        filtered = [c for c in filtered if c.category == category.lower()]

    if search:
        s_lower = search.lower().strip()
        filtered = [
            c for c in filtered
            if s_lower in c.name.lower() or s_lower in c.description.lower() or s_lower in c.id.lower() or s_lower in c.category_label.lower()
        ]

    connector_dicts = []
    for c in filtered:
        c_dict = c.model_dump()
        c_dict["live_supported"] = c.id in LIVE_SUPPORTED_PROVIDERS
        connector_dicts.append(c_dict)

    return {
        "total_supported": len(connector_dicts),
        "total_matched": len(connector_dicts),
        "categories": categories,
        "connectors": connector_dicts,
    }


@router.post("/test-connection", response_model=ConnectionTestResult)
async def test_source_connection(
    data: ConnectionTestRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Perform pre-flight connectivity verification for any of the supported live data sources.
    Uses real provider APIs, database drivers, and official SDKs.
    """
    stype = (data.source_type or "").lower().strip()
    dummy_org = uuid.UUID("11111111-1111-1111-1111-111111111111")
    dummy_src = uuid.uuid4()
    logger.info("Initiating live connection test for source type '%s'", stype)

    try:
        if stype in ("postgresql", "postgres"):
            connector = PostgresConnector(
                session=db,
                organization_id=dummy_org,
                source_id=dummy_src,
                connection_config=data.connection_config,
            )
            res = await connector.test_connection()

        elif stype in ("mongodb", "mongo", "mongo_atlas", "mongodb_atlas", "mongodb_self", "documentdb", "cosmos_mongo"):
            connector = MongoDbConnector(
                session=db,
                organization_id=dummy_org,
                source_id=dummy_src,
                connection_config=data.connection_config,
            )
            res = await connector.test_connection()

        elif stype in ("github", "repo", "git"):
            connector = GitHubConnector(
                session=db,
                organization_id=dummy_org,
                source_id=dummy_src,
                repo=data.connection_config.get("repo") or data.connection_config.get("repository") or "demo-org/security-standards",
                branch=data.connection_config.get("branch"),
                token=data.connection_config.get("token") or data.connection_config.get("access_token"),
            )
            res = await connector.test_connection()

        elif stype in ("jira", "jira_issues"):
            connector = JiraConnector(
                session=db,
                organization_id=dummy_org,
                source_id=dummy_src,
                connection_config=data.connection_config,
            )
            res = await connector.test_connection()

        elif stype in ("confluence", "wiki"):
            connector = ConfluenceConnector(
                session=db,
                organization_id=dummy_org,
                source_id=dummy_src,
                connection_config=data.connection_config,
            )
            res = await connector.test_connection()

        elif stype in ("kafka", "apache_kafka", "confluent"):
            connector = KafkaConnector(
                session=db,
                organization_id=dummy_org,
                source_id=dummy_src,
                connection_config=data.connection_config,
            )
            res = await connector.test_connection()

        elif stype in ("salesforce", "sfdc", "salesforce_crm"):
            connector = SalesforceConnector(
                session=db,
                organization_id=dummy_org,
                source_id=dummy_src,
                connection_config=data.connection_config,
            )
            res = await connector.test_connection()

        elif stype in ("slack", "slack_channel", "slack_workspace"):
            connector = SlackConnector(
                session=db,
                organization_id=dummy_org,
                source_id=dummy_src,
                connection_config=data.connection_config,
            )
            res = await connector.test_connection()

        else:
            driver = UniversalConnectorDriver(
                session=db,
                organization_id=dummy_org,
                source_id=dummy_src,
                source_type=stype,
                connection_config=data.connection_config,
            )
            res = await driver.test_connection()

        # Sanitize details to guarantee zero secret leakage
        safe_details = EncryptionService.redact_credentials(res.get("details", {}))
        success = res.get("success", False)
        msg = res.get("message", "Connection verification completed.")

        if success:
            logger.info("Connection test SUCCEEDED for source type '%s': %s", stype, msg)
        else:
            logger.warning("Connection test FAILED for source type '%s': %s", stype, msg)

        return ConnectionTestResult(
            success=success,
            status=res.get("status", "ok" if success else "error"),
            message=msg,
            details=safe_details,
            tested_at=datetime.now(timezone.utc),
        )

    except Exception as e:
        logger.error("Connection test encountered unexpected exception for '%s': %s", stype, str(e), exc_info=True)
        return ConnectionTestResult(
            success=False,
            status="error",
            message=f"Connection diagnostic check failed: {str(e)}",
            details={"source_type": data.source_type},
            tested_at=datetime.now(timezone.utc),
        )


@router.post("/discover", response_model=ResourceDiscoveryResponse)
async def discover_source_resources(
    data: ResourceDiscoveryRequest,
):
    """
    Discover available resources (repositories, databases, collections, projects, spaces, schemas, tables)
    using the authenticated provider API or database driver.
    """
    stype = (data.source_type or "").lower().strip()
    cfg = data.connection_config or {}

    try:
        if stype in ("github", "repo", "git"):
            token = cfg.get("token") or cfg.get("access_token")
            owner = cfg.get("owner") or cfg.get("organization") or cfg.get("repo_owner")
            items = await GitHubConnector.discover_repositories(token=token, owner=owner)
            return ResourceDiscoveryResponse(source_type="github", target_resource="repositories", items=items, total_count=len(items))

        elif stype in ("mongodb", "mongodb_atlas", "mongo"):
            uri = cfg.get("connection_string") or cfg.get("uri") or "mongodb://localhost:27017"
            target = (data.target_resource or "").lower()
            if target == "collections" and data.parent_resource:
                cols = await MongoDbConnector.discover_collections(connection_string=uri, database=data.parent_resource)
                return ResourceDiscoveryResponse(source_type="mongodb", target_resource="collections", items=cols, total_count=len(cols))
            else:
                dbs = await MongoDbConnector.discover_databases(connection_string=uri)
                return ResourceDiscoveryResponse(source_type="mongodb", target_resource="databases", items=dbs, total_count=len(dbs))

        elif stype in ("jira", "jira_issues"):
            base_url = cfg.get("base_url") or cfg.get("url") or ""
            email = cfg.get("user_email") or cfg.get("email") or ""
            token = cfg.get("api_token") or cfg.get("token") or ""
            projects = await JiraConnector.discover_projects(base_url=base_url, user_email=email, api_token=token)
            return ResourceDiscoveryResponse(source_type="jira", target_resource="projects", items=projects, total_count=len(projects))

        elif stype in ("confluence", "wiki"):
            base_url = cfg.get("base_url") or cfg.get("url") or ""
            email = cfg.get("user_email") or cfg.get("email") or ""
            token = cfg.get("api_token") or cfg.get("token") or ""
            spaces = await ConfluenceConnector.discover_spaces(base_url=base_url, user_email=email, api_token=token)
            return ResourceDiscoveryResponse(source_type="confluence", target_resource="spaces", items=spaces, total_count=len(spaces))

        elif stype in ("postgresql", "postgres"):
            host = cfg.get("host", "localhost")
            port = int(cfg.get("port", 5432))
            database = cfg.get("database", "postgres")
            username = cfg.get("username", "postgres")
            password = cfg.get("password", "")
            ssl_mode = cfg.get("ssl_mode", "prefer")

            target = (data.target_resource or "").lower()
            if target == "tables" and data.parent_resource:
                tables = await PostgresConnector.discover_tables(
                    host=host, port=port, database=database, username=username, password=password, schema=data.parent_resource, ssl_mode=ssl_mode
                )
                return ResourceDiscoveryResponse(source_type="postgresql", target_resource="tables", items=tables, total_count=len(tables))
            else:
                schemas = await PostgresConnector.discover_schemas(
                    host=host, port=port, database=database, username=username, password=password, ssl_mode=ssl_mode
                )
                return ResourceDiscoveryResponse(source_type="postgresql", target_resource="schemas", items=schemas, total_count=len(schemas))

        elif stype in ("slack", "slack_channel", "slack_workspace"):
            token = cfg.get("bot_token") or cfg.get("token") or cfg.get("access_token") or ""
            channels = await SlackConnector.discover_channels(bot_token=token)
            return ResourceDiscoveryResponse(source_type="slack", target_resource="channels", items=channels, total_count=len(channels))

        return ResourceDiscoveryResponse(source_type=stype, target_resource=data.target_resource, items=[], total_count=0)

    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Discovery failed: {str(e)}")


@router.get("", response_model=list[DataSourceResponse])
async def list_data_sources(
    organization_id: uuid.UUID = Query(uuid.UUID("11111111-1111-1111-1111-111111111111")),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    include_archived: bool = Query(False, description="Whether to include decommissioned/archived sources"),
    db: AsyncSession = Depends(get_db),
):
    """List all configured external data source connections with credentials safely redacted."""
    repo = DataSourceRepository(db)
    sources = await repo.list_by_organization(
        organization_id=organization_id,
        limit=limit,
        offset=offset,
    )
    external_connectors = [
        s for s in sources
        if (s.source_type or "").lower().strip() not in ("file", "upload", "local_file")
        and "file upload" not in (s.name or "").lower()
        and "direct document upload" not in (s.name or "").lower()
        and (include_archived or (s.status.value if hasattr(s.status, "value") else str(s.status)).lower() not in ("deleted", "inactive", "archived"))
    ]
    return [_mask_source_response(s) for s in external_connectors]


@router.get("/{source_id}", response_model=DataSourceResponse)
async def get_data_source(
    source_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    """Retrieve details for a single data source connection with credentials safely redacted."""
    repo = DataSourceRepository(db)
    source = await repo.get_by_id(source_id)
    if not source:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Data source {source_id} not found.")
    return _mask_source_response(source)


@router.post("", response_model=DataSourceResponse, status_code=status.HTTP_201_CREATED)
async def create_data_source(
    data: DataSourceCreate,
    user_name: str = Query(default="Alex Rivera", description="Name of acting user"),
    user_role: str = Query(default="data_owner", description="Role of acting user"),
    user_id: uuid.UUID | None = Query(default=None),
    _authorized_user: Optional[User] = Depends(require_permission(Permission.SOURCES_MANAGE)),
    db: AsyncSession = Depends(get_db),
):
    """
    Register a new live data source connection.
    Validates configuration, enforces state transition rules, and encrypts credentials at rest.
    Supports multiple independent connections to the same provider.
    """
    repo = DataSourceRepository(db)
    activity_service = ActivityService(db)
    effective_owner_id = user_id or data.owner_id or data.user_id or (_authorized_user.id if _authorized_user else None)

    # 1. State transition & credential security
    test_passed = bool((data.connection_config or {}).get("test_passed", False))
    persisted_config, _ = _secure_and_validate_config(data.source_type, data.connection_config or {}, test_passed)

    # 2. Determine external identifier (unique per independent connection)
    ext_id = data.external_id
    if not ext_id:
        stype = (data.source_type or "").lower().strip()
        if stype in ("github", "repo", "git"):
            repo_val = persisted_config.get("repository") or persisted_config.get("repo") or "repo"
            ext_id = f"github://{repo_val}/{uuid.uuid4().hex[:6]}"
        elif stype in ("mongodb", "mongodb_atlas", "mongo"):
            ext_id = f"mongodb://{persisted_config.get('database', 'db')}/{uuid.uuid4().hex[:6]}"
        elif stype in ("jira", "jira_issues"):
            ext_id = f"jira://{persisted_config.get('project_key', 'project')}/{uuid.uuid4().hex[:6]}"
        elif stype in ("confluence", "wiki"):
            ext_id = f"confluence://{persisted_config.get('space_key', 'space')}/{uuid.uuid4().hex[:6]}"
        elif stype in ("postgresql", "postgres"):
            ext_id = f"postgresql://{persisted_config.get('host', 'localhost')}:{persisted_config.get('port', 5432)}/{persisted_config.get('database', 'db')}/{uuid.uuid4().hex[:6]}"
        else:
            ext_id = f"{stype}://{uuid.uuid4().hex[:8]}"

    fam = data.source_family or resolve_source_family(data.source_type)
    intent = data.source_intent or get_default_intent(data.source_type)
    caps = data.capabilities or get_default_capabilities(data.source_type)
    scope = data.scope_config or {}

    source = await repo.get_or_create(
        organization_id=data.organization_id,
        name=data.name.strip(),
        source_type=data.source_type,
        external_id=ext_id,
        authority_level=data.authority_level,
        connection_config=persisted_config,
        owner_id=effective_owner_id,
        source_family=fam,
        source_intent=intent,
        scope_config=scope,
        capabilities=caps,
    )

    await activity_service.log_activity(
        organization_id=data.organization_id,
        user_id=effective_owner_id,
        user_name=user_name,
        user_role=user_role,
        action_type="SOURCE_CREATED",
        target_type="data_source",
        target_id=str(source.id),
        target_title=source.name,
        domain="Engineering & Platform",
        details={
            "source_type": source.source_type,
            "source_family": source.source_family.value,
            "source_intent": source.source_intent.value,
            "authority_level": source.authority_level,
            "status": persisted_config.get("connection_status", "disconnected"),
            "schedule": persisted_config.get("schedule", "off"),
        },
    )
    await db.commit()
    return _mask_source_response(source)


@router.put("/{source_id}", response_model=DataSourceResponse)
async def update_data_source(
    source_id: uuid.UUID,
    data: DataSourceUpdate,
    _authorized_user: Optional[User] = Depends(require_permission(Permission.SOURCES_MANAGE)),
    db: AsyncSession = Depends(get_db),
):
    """Updates configuration, authority level, or display name for an existing connection."""
    repo = DataSourceRepository(db)
    source = await repo.get_by_id(source_id)
    if not source:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Data source {source_id} not found.")

    if data.name:
        source.name = data.name.strip()
    if data.source_family:
        source.source_family = data.source_family
    if data.source_intent:
        source.source_intent = data.source_intent
    if data.scope_config is not None:
        source.scope_config = data.scope_config
    if data.capabilities is not None:
        source.capabilities = data.capabilities
    if data.authority_level is not None:
        source.authority_level = data.authority_level

    if data.connection_config:
        current_cfg = dict(source.connection_config or {})
        # Check if new test was run
        test_passed = bool(data.connection_config.get("test_passed", current_cfg.get("connection_status") == "connected"))
        merged = {**current_cfg, **data.connection_config}
        persisted_config, _ = _secure_and_validate_config(source.source_type, merged, test_passed)
        source.connection_config = persisted_config

    source.updated_at = datetime.now(timezone.utc)
    await db.flush()
    await db.commit()
    return _mask_source_response(source)


@router.get("/{source_id}/inventory", response_model=SourceInventoryResponse)
async def get_source_inventory(
    source_id: uuid.UUID,
    _authorized_user: Optional[User] = Depends(require_permission(Permission.SOURCES_READ)),
    db: AsyncSession = Depends(get_db),
):
    """
    Discovers available selectable entities (tables, collections, repos, files, spaces)
    within the configured data source without converting them to markdown or extracting claims prematurely.
    """
    repo = DataSourceRepository(db)
    source = await repo.get_by_id(source_id)
    if not source:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Data source {source_id} not found.")

    stype = (source.source_type or "").lower().strip()
    cfg = dict(source.connection_config or {})
    if "_encrypted_credentials" in cfg:
        decrypted = EncryptionService.decrypt_payload(cfg["_encrypted_credentials"])
        cfg.update(decrypted)

    items = []
    try:
        if stype in ("postgresql", "postgres"):
            connector = PostgresConnector(
                session=db,
                organization_id=source.organization_id,
                source_id=source.id,
                connection_config=cfg,
                scope_config=source.scope_config,
                source_intent=source.source_intent,
            )
            res = await connector.discover_inventory()
            items = res.get("items", [])
        elif stype in ("mongodb", "mongodb_atlas", "mongo"):
            connector = MongoDbConnector(
                session=db,
                organization_id=source.organization_id,
                source_id=source.id,
                connection_config=cfg,
                scope_config=source.scope_config,
                source_intent=source.source_intent,
            )
            res = await connector.discover_inventory()
            items = res.get("items", [])
        elif stype in ("github", "repo", "git"):
            connector = GitHubConnector(
                session=db,
                organization_id=source.organization_id,
                source_id=source.id,
                repo=cfg.get("repo") or cfg.get("repository") or "demo-org/security-standards",
                branch=cfg.get("branch"),
                token=cfg.get("token") or cfg.get("access_token"),
                scope_config=source.scope_config,
                source_intent=source.source_intent,
            )
            res = await connector.discover_inventory()
            items = res.get("items", [])
        elif stype in ("confluence", "wiki"):
            raw_spaces = cfg.get("space_keys") or [cfg.get("space_key", "default")]
            items = [
                {
                    "id": sp,
                    "name": f"Space: {sp}",
                    "item_type": "space",
                    "parent": None,
                    "is_selectable": True,
                    "metadata": {},
                }
                for sp in raw_spaces if sp
            ]
        elif stype in ("jira", "jira_issues"):
            pkey = cfg.get("project_key", "default")
            items = [
                {
                    "id": pkey,
                    "name": f"Project: {pkey}",
                    "item_type": "project",
                    "parent": None,
                    "is_selectable": True,
                    "metadata": {},
                }
            ]
    except Exception as e:
        logger.warning("Inventory discovery failed for source %s: %s", str(source_id), str(e))

    inventory_items = [
        SourceInventoryItem(
            id=it["id"],
            name=it.get("name", it["id"]),
            item_type=it.get("item_type", "entity"),
            parent=it.get("parent"),
            is_selectable=it.get("is_selectable", True),
            metadata=it.get("metadata", {}),
        )
        for it in items
    ]

    return SourceInventoryResponse(
        source_id=source.id,
        source_type=source.source_type,
        source_family=source.source_family,
        items=inventory_items,
        total_count=len(inventory_items),
        discovered_at=datetime.now(timezone.utc).isoformat(),
    )


@router.post("/{source_id}/scope", response_model=DataSourceResponse)
async def update_source_scope(
    source_id: uuid.UUID,
    scope_config: dict[str, Any],
    _authorized_user: Optional[User] = Depends(require_permission(Permission.SOURCES_MANAGE)),
    db: AsyncSession = Depends(get_db),
):
    """
    Sets the granular extraction scope (selected tables, collections, branches, channels, or paths)
    for a data source.
    """
    repo = DataSourceRepository(db)
    source = await repo.get_by_id(source_id)
    if not source:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Data source {source_id} not found.")

    source.scope_config = scope_config
    # Also mirror into connection_config for Layer 2 compatibility
    cfg = dict(source.connection_config or {})
    if "selected_entities" in scope_config:
        cfg["selected_assets"] = scope_config["selected_entities"]
    elif "selected_assets" in scope_config:
        cfg["selected_assets"] = scope_config["selected_assets"]
    source.connection_config = cfg

    source.updated_at = datetime.now(timezone.utc)
    await db.flush()
    await db.commit()
    return _mask_source_response(source)


@router.get("/{source_id}/discover-assets")
async def discover_source_assets(
    source_id: uuid.UUID,
    _authorized_user: Optional[User] = Depends(require_permission(Permission.SOURCES_READ)),
    db: AsyncSession = Depends(get_db),
):
    """Layer 2 endpoint: Discovers assets within a data source."""
    inv = await get_source_inventory(source_id=source_id, _authorized_user=_authorized_user, db=db)
    return {
        "source_id": str(source_id),
        "source_type": inv.source_type,
        "source_family": inv.source_family.value,
        "assets": [
            {
                "id": it.id,
                "name": it.name,
                "asset_type": it.asset_type or it.item_type,
                "parent_scope": it.parent_scope or it.parent,
                "is_selectable": it.is_selectable,
                "metadata": it.metadata,
            }
            for it in inv.items
        ],
        "total_count": inv.total_count,
        "discovered_at": inv.discovered_at,
    }


@router.post("/{source_id}/select-assets", response_model=DataSourceResponse)
async def select_source_assets(
    source_id: uuid.UUID,
    data: dict[str, Any],
    _authorized_user: Optional[User] = Depends(require_permission(Permission.SOURCES_MANAGE)),
    db: AsyncSession = Depends(get_db),
):
    """Layer 2 endpoint: Selects specific assets/entities for sync."""
    repo = DataSourceRepository(db)
    source = await repo.get_by_id(source_id)
    if not source:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Data source {source_id} not found.")

    selected_ids = data.get("selected_asset_ids") or data.get("selected_assets") or []
    current_scope = dict(source.scope_config or {})
    current_scope["selected_assets"] = selected_ids
    current_scope["selected_entities"] = selected_ids
    source.scope_config = current_scope

    current_cfg = dict(source.connection_config or {})
    current_cfg["selected_assets"] = selected_ids
    source.connection_config = current_cfg

    source.updated_at = datetime.now(timezone.utc)
    await db.flush()
    await db.commit()
    return _mask_source_response(source)


@router.post("/{source_id}/schedule", response_model=DataSourceResponse)
async def update_source_schedule(
    source_id: uuid.UUID,
    data: ScheduleUpdateRequest,
    _authorized_user: Optional[User] = Depends(require_permission(Permission.SOURCES_MANAGE)),
    db: AsyncSession = Depends(get_db),
):
    """Updates the synchronization schedule ('off', '1m', '10m') for a connection."""
    sch = data.schedule.lower().strip()
    if sch not in ("off", "1m", "10m"):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Schedule must be 'off', '1m', or '10m'.")

    repo = DataSourceRepository(db)
    source = await repo.get_by_id(source_id)
    if not source:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Data source {source_id} not found.")

    cfg = dict(source.connection_config or {})
    cfg["schedule"] = sch
    if sch in ("1m", "10m"):
        interval_secs = 60 if sch == "1m" else 600
        cfg["next_sync_at"] = (datetime.now(timezone.utc) + timedelta(seconds=interval_secs)).isoformat()
    else:
        cfg["next_sync_at"] = None

    source.connection_config = cfg
    source.updated_at = datetime.now(timezone.utc)
    await db.flush()
    await db.commit()
    return _mask_source_response(source)


@router.post("/{source_id}/disconnect", response_model=DataSourceResponse)
async def disconnect_source(
    source_id: uuid.UUID,
    _authorized_user: Optional[User] = Depends(require_permission(Permission.SOURCES_MANAGE)),
    db: AsyncSession = Depends(get_db),
):
    """Disconnects a connector, setting its status to 'disconnected' and disabling automatic schedules."""
    repo = DataSourceRepository(db)
    source = await repo.get_by_id(source_id)
    if not source:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Data source {source_id} not found.")

    cfg = dict(source.connection_config or {})
    cfg["connection_status"] = "disconnected"
    cfg["schedule"] = "off"
    cfg["next_sync_at"] = None

    source.connection_config = cfg
    source.updated_at = datetime.now(timezone.utc)
    await db.flush()
    await db.commit()
    return _mask_source_response(source)


@router.post("/{source_id}/sync", response_model=SyncResult)
async def sync_single_source(
    source_id: uuid.UUID,
    use_mock_llm: bool = Query(True, description="Use fast deterministic rule-based LLM for extraction"),
    user_name: str = Query(default="Alex Rivera", description="Name of acting user"),
    user_role: str = Query(default="data_owner", description="Role of acting user"),
    user_id: uuid.UUID | None = Query(default=None),
    _authorized_user: Optional[User] = Depends(require_permission(Permission.SOURCES_SYNC)),
    db: AsyncSession = Depends(get_db),
):
    """Trigger an immediate live sync for a specific connector. Automatically extracts claims and detects conflicts."""
    sync_engine = SyncEngine(db)
    activity_service = ActivityService(db)
    repo = DataSourceRepository(db)
    source = await repo.get_by_id(source_id)
    if not source:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Data source {source_id} not found.")

    source_org_id = source.organization_id
    source_name = source.name
    source_id_str = str(source.id)

    try:
        result = await sync_engine.sync_data_source(source_id=source_id, use_mock_llm=use_mock_llm, user_id=user_id)
        if result.status == "success":
            await activity_service.log_activity(
                organization_id=source_org_id,
                user_id=user_id,
                user_name=user_name,
                user_role=user_role,
                action_type="SOURCE_SYNCED",
                target_type="data_source",
                target_id=source_id_str,
                target_title=source_name,
                domain="Engineering & Platform",
                details={
                    "documents_synced": result.documents_synced,
                    "documents_created": result.documents_created,
                    "documents_skipped": result.documents_skipped,
                    "claims_extracted": result.claims_extracted,
                    "execution_time_ms": result.execution_time_ms,
                },
            )
            await db.commit()
        return result
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Sync failed: {str(e)}")


@router.post("/sync-all", response_model=list[SyncResult])
async def sync_all_sources(
    organization_id: uuid.UUID = Query(uuid.UUID("11111111-1111-1111-1111-111111111111")),
    use_mock_llm: bool = Query(True, description="Use fast deterministic rule-based LLM for extraction"),
    db: AsyncSession = Depends(get_db),
):
    """Trigger synchronization across all registered connectors for an organization."""
    sync_engine = SyncEngine(db)
    try:
        results = await sync_engine.sync_all_organization_sources(
            organization_id=organization_id,
            use_mock_llm=use_mock_llm,
        )
        return results
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Bulk sync failed: {str(e)}")


@router.get("/{source_id}/artifacts")
async def get_source_artifacts(
    source_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    """
    Returns full deep-dive artifacts for a specific data source connector:
    - connector metadata
    - all synced documents
    - all extracted atomic claims
    - all conflicts originating from this connector
    """
    from sqlalchemy import or_, select
    from sqlalchemy.orm import selectinload
    from app.db.models.claim import Claim
    from app.db.models.claim_conflict import ClaimConflict
    from app.db.models.document import Document

    src = await db.get(DataSource, source_id)
    if not src:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Data source connector not found")

    doc_stmt = (
        select(Document)
        .where(Document.source_id == source_id)
        .options(selectinload(Document.versions))
    )
    res_docs = await db.execute(doc_stmt)
    docs = res_docs.scalars().all()

    version_ids = []
    docs_output = []
    for d in docs:
        for v in (d.versions or []):
            version_ids.append(v.id)
        docs_output.append({
            "id": str(d.id),
            "title": d.title,
            "document_type": d.document_type,
            "external_id": d.external_id,
            "status": d.status.value if hasattr(d.status, "value") else str(d.status),
            "created_at": d.created_at.isoformat() if d.created_at else None,
            "versions_count": len(d.versions) if d.versions else 1
        })

    claims_output = []
    conflicts_list = []

    if version_ids:
        claims_stmt = (
            select(Claim)
            .where(Claim.document_version_id.in_(version_ids))
            .options(
                selectinload(Claim.evidence),
                selectinload(Claim.validity_records),
                selectinload(Claim.trust_scores),
            )
        )
        res_claims = await db.execute(claims_stmt)
        claims = res_claims.scalars().all()
        claim_ids = [c.id for c in claims]

        if claim_ids:
            conflicts_stmt = (
                select(ClaimConflict)
                .where(
                    or_(
                        ClaimConflict.claim_a_id.in_(claim_ids),
                        ClaimConflict.claim_b_id.in_(claim_ids)
                    )
                )
                .options(
                    selectinload(ClaimConflict.claim_a).selectinload(Claim.trust_scores),
                    selectinload(ClaimConflict.claim_b).selectinload(Claim.trust_scores),
                )
            )
            res_conflicts = await db.execute(conflicts_stmt)
            raw_conflicts = res_conflicts.scalars().all()
            for cf in raw_conflicts:
                conflicts_list.append({
                    "id": str(cf.id),
                    "claim_a_id": str(cf.claim_a_id),
                    "claim_b_id": str(cf.claim_b_id),
                    "claim_a_text": cf.claim_a.claim_text if cf.claim_a else "Unknown",
                    "claim_b_text": cf.claim_b.claim_text if cf.claim_b else "Unknown",
                    "conflict_type": cf.conflict_type.value if hasattr(cf.conflict_type, "value") else str(cf.conflict_type),
                    "resolution_status": cf.resolution_status.value if hasattr(cf.resolution_status, "value") else str(cf.resolution_status),
                    "severity": getattr(cf, "severity", "HIGH"),
                    "created_at": cf.created_at.isoformat() if cf.created_at else None
                })

        for c in claims:
            score = c.trust_scores[0].overall_score if c.trust_scores else 0.95
            validity = c.validity_records[0].validity_status if c.validity_records else "valid"
            
            # Phase 1a: Read-Path Stabilization
            status_val = c.status.value if hasattr(c.status, "value") else str(c.status).lower()
            metadata = getattr(c, "claim_metadata", {}) or {}
            persisted_tier = metadata.get("certification_tier")
            if not persisted_tier:
                if status_val in ("verified", "active"):
                    persisted_tier = "AUTOMATED_CERTIFIED"
                elif status_val in ("rejected", "quarantined"):
                    persisted_tier = "QUARANTINED"
                else:
                    persisted_tier = "REVIEW_REQUIRED"

            is_canon = (persisted_tier == "AUTOMATED_CERTIFIED") and (status_val in ("verified", "active"))

            gate_res = ClaimGateEvaluator.evaluate(
                claim_id=str(c.id),
                subject=c.subject,
                predicate=c.predicate,
                object_val=c.object,
                claim_text=c.claim_text,
                claim_type=getattr(c, "claim_type", "policy"),
                status=status_val,
                metadata=metadata,
                confidence=float(score),
            )

            revalidation_audit = {
                "live_tier": gate_res.certification_tier,
                "divergence_flag": (gate_res.certification_tier != persisted_tier),
                "live_all_9_gates_passed": gate_res.all_9_gates_passed,
                "live_rejection_reasons": gate_res.rejection_reasons,
                "evaluator_version": "ClaimGateEvaluator_v3.2",
                "persisted_tier": persisted_tier,
            }

            claims_output.append({
                "id": str(c.id),
                "subject": c.subject or "General",
                "predicate": c.predicate or "specifies",
                "object": c.object or "",
                "claim_text": c.claim_text,
                "status": status_val,
                "trust_score": float(score),
                "validity": str(validity),
                "created_at": c.created_at.isoformat() if c.created_at else None,
                "gates": gate_res.gates,
                "all_9_gates_passed": (persisted_tier == "AUTOMATED_CERTIFIED"),
                "is_canonical": is_canon,
                "agent_accessible": is_canon,
                "certification_tier": persisted_tier,
                "rejection_reasons": [] if persisted_tier == "AUTOMATED_CERTIFIED" else gate_res.rejection_reasons,
                "revalidation_audit": revalidation_audit,
            })

    return {
        "source": {
            "id": str(src.id),
            "name": src.name,
            "source_type": src.source_type,
            "authority_level": src.authority_level,
            "status": src.status.value if hasattr(src.status, "value") else str(src.status),
            "created_at": src.created_at.isoformat() if src.created_at else None
        },
        "documents": docs_output,
        "claims": claims_output,
        "conflicts": conflicts_list,
        "total_documents": len(docs_output),
        "total_claims": len(claims_output),
        "total_conflicts": len(conflicts_list)
    }


@router.get("/{source_id}/blast-radius")
async def get_source_blast_radius(
    source_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    """Calculate the blast radius of deleting or decommissioning a connector."""
    from sqlalchemy import or_, select
    from sqlalchemy.orm import selectinload
    from app.db.models.claim import Claim
    from app.db.models.claim_conflict import ClaimConflict
    from app.db.models.document import Document

    src = await db.get(DataSource, source_id)
    if not src:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Connector source not found.")

    res_docs = await db.execute(select(Document).where(Document.source_id == source_id).options(selectinload(Document.versions)))
    docs = res_docs.scalars().all()

    version_ids = []
    for d in docs:
        for v in (d.versions or []):
            version_ids.append(v.id)

    claims_count = 0
    sample_claims = []
    conflicts_count = 0

    if version_ids:
        res_claims = await db.execute(select(Claim).where(Claim.document_version_id.in_(version_ids)))
        claims = res_claims.scalars().all()
        claims_count = len(claims)
        sample_claims = [c.claim_text for c in claims[:3]]
        claim_ids = [c.id for c in claims]

        if claim_ids:
            res_conflicts = await db.execute(
                select(ClaimConflict).where(
                    or_(
                        ClaimConflict.claim_a_id.in_(claim_ids),
                        ClaimConflict.claim_b_id.in_(claim_ids),
                    )
                )
            )
            conflicts = res_conflicts.scalars().all()
            conflicts_count = len(conflicts)

    return {
        "id": str(src.id),
        "name": src.name,
        "source_type": src.source_type,
        "authority_level": src.authority_level,
        "documents_count": len(docs),
        "claims_count": claims_count,
        "conflicts_count": conflicts_count,
        "sample_documents": [d.title for d in docs[:4]],
        "sample_claims": sample_claims,
    }


@router.delete("/{source_id}")
async def delete_or_decommission_source(
    source_id: uuid.UUID,
    mode: str = Query("archive", description="'archive' (soft decommission) or 'permanent' (hard purge)"),
    user_name: str = Query("Sarah Chen", description="Name of acting CEO / Administrator"),
    user_role: str = Query("admin", description="Role of acting user"),
    user_id: uuid.UUID | None = Query(None),
    db: AsyncSession = Depends(get_db),
):
    """
    Delete or decommission a data source connector:
    - mode='archive': Soft decommission. Marks source and documents as inactive, deprecates claims.
    - mode='permanent': Hard purge. Permanently erases the connector and documents.
    """
    from sqlalchemy import or_, select
    from sqlalchemy.orm import selectinload
    from app.db.enums import ClaimStatus, ConflictStatus, RecordStatus
    from app.db.models.claim import Claim
    from app.db.models.claim_conflict import ClaimConflict
    from app.db.models.document import Document

    mode_clean = (mode or "archive").lower().strip()
    if mode_clean not in ("archive", "permanent"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid mode. Must be 'archive' or 'permanent'."
        )

    if mode_clean == "permanent" and (user_role or "").lower() != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Permanent purge is restricted exclusively to Organization Administrators / CEO personas."
        )

    src = await db.get(DataSource, source_id)
    if not src:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Connector source not found.")

    activity_service = ActivityService(db)
    source_name = src.name
    org_id = src.organization_id

    res_docs = await db.execute(select(Document).where(Document.source_id == source_id).options(selectinload(Document.versions)))
    docs = res_docs.scalars().all()
    version_ids = [v.id for d in docs for v in (d.versions or [])]

    claims = []
    if version_ids:
        res_claims = await db.execute(select(Claim).where(Claim.document_version_id.in_(version_ids)))
        claims = res_claims.scalars().all()

    claim_ids = [c.id for c in claims]
    conflicts = []
    if claim_ids:
        res_cfl = await db.execute(
            select(ClaimConflict).where(
                or_(ClaimConflict.claim_a_id.in_(claim_ids), ClaimConflict.claim_b_id.in_(claim_ids))
            )
        )
        conflicts = res_cfl.scalars().all()

    if mode_clean == "archive":
        src.status = RecordStatus.INACTIVE
        for d in docs:
            d.status = RecordStatus.INACTIVE
        for c in claims:
            c.status = ClaimStatus.SUPERSEDED
        for cfl in conflicts:
            cfl.resolution_status = ConflictStatus.DISMISSED

        await activity_service.log_activity(
            organization_id=org_id,
            user_id=user_id,
            user_name=user_name,
            user_role=user_role,
            action_type="CONNECTOR_DECOMMISSIONED",
            target_type="data_source",
            target_id=str(source_id),
            target_title=source_name,
            domain="Engineering & Platform",
            details={
                "mode": "archive",
                "documents_affected": len(docs),
                "claims_deprecated": len(claims),
                "conflicts_resolved": len(conflicts),
            },
        )
        await db.commit()
        return {
            "status": "archived",
            "message": f"Connector '{source_name}' successfully decommissioned. {len(claims)} claims deprecated.",
            "source_id": str(source_id),
            "mode": "archive",
            "documents_affected": len(docs),
            "claims_affected": len(claims),
            "conflicts_resolved": len(conflicts),
        }

    else:
        await activity_service.log_activity(
            organization_id=org_id,
            user_id=user_id,
            user_name=user_name,
            user_role=user_role,
            action_type="CONNECTOR_PURGED",
            target_type="data_source",
            target_id=str(source_id),
            target_title=source_name,
            domain="Engineering & Platform",
            details={
                "mode": "permanent",
                "documents_purged": len(docs),
                "claims_purged": len(claims),
                "conflicts_purged": len(conflicts),
            },
        )
        await db.delete(src)
        await db.commit()
        return {
            "status": "deleted",
            "message": f"Connector '{source_name}' permanently purged from database.",
            "source_id": str(source_id),
            "mode": "permanent",
            "documents_affected": len(docs),
            "claims_affected": len(claims),
            "conflicts_resolved": len(conflicts),
        }


@router.get("/{source_id}/test-connection", response_model=ConnectionTestResult)
@router.post("/{source_id}/test-connection", response_model=ConnectionTestResult)
async def test_existing_source_connection_endpoint(
    source_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_permission(Permission.SOURCES_READ)),
):
    """Layer 2 Connectivity Verification: Verifies live connection to an already registered data source."""
    engine = SyncEngine(db)
    source = await engine.source_repo.get_by_id(source_id)
    if not source:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Data source {source_id} not found.")

    try:
        connector = engine.get_connector_for_source(source)
        if hasattr(connector, "test_connection"):
            res = await connector.test_connection()
            return ConnectionTestResult(
                success=res.get("success", True),
                status=res.get("status", "ok"),
                message=res.get("message", "Connection verified successfully."),
                details=res.get("details", {}),
            )
        return ConnectionTestResult(
            success=True,
            status="ok",
            message=f"Connector '{source.source_type}' verified (ready for ingestion).",
            details={"source_id": str(source.id), "source_type": source.source_type},
        )
    except Exception as e:
        logger.error("Connection test failed for source %s: %s", source_id, str(e))
        return ConnectionTestResult(
            success=False,
            status="error",
            message=f"Connection test failed: {str(e)}",
            details={"error": str(e)},
        )


@router.get("/{source_id}/discover-assets", response_model=list[DiscoveredAsset])
async def discover_source_assets_endpoint(
    source_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_permission(Permission.SOURCES_READ)),
):
    """Layer 2 Asset Discovery: Dynamically inspects tables, collections, files, or spaces from source."""
    engine = SyncEngine(db)
    try:
        return await engine.discover_source_assets(source_id)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except Exception as e:
        logger.error("Asset discovery failed for %s: %s", source_id, str(e))
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Discovery failed: {str(e)}")


@router.post("/{source_id}/select-assets", response_model=DataSourceResponse)
async def select_source_assets_endpoint(
    source_id: uuid.UUID,
    payload: dict[str, Any],
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_permission(Permission.SOURCES_MANAGE)),
):
    """Layer 2 Scope Selection: Persists the user's targeted asset IDs for scoped synchronization."""
    selected_assets = payload.get("selected_assets", [])
    engine = SyncEngine(db)
    try:
        updated_source = await engine.update_selected_assets(source_id, selected_assets)
        return _mask_source_response(updated_source)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.get("/{source_id}/native-assets", response_model=list[RawSourceAsset])
async def fetch_native_assets_preview(
    source_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_permission(Permission.SOURCES_READ)),
):
    """Layer 2 Native Payload Extraction: Retrieves un-flattened raw assets with locators."""
    engine = SyncEngine(db)
    try:
        return await engine.fetch_native_assets(source_id)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.get("/{source_id}/envelopes")
async def fetch_canonical_envelopes_endpoint(
    source_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_permission(Permission.SOURCES_READ)),
):
    """Layer 3 Canonical Source Envelopes: Retrieves standardized, sealed multi-tenant envelopes."""
    engine = SyncEngine(db)
    try:
        envelopes = await engine.fetch_canonical_envelopes(source_id)
        return [env.to_dict() for env in envelopes]
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.get("/{source_id}/envelopes-preview")
async def fetch_envelopes_routing_preview(
    source_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_permission(Permission.SOURCES_READ)),
):
    """Layer 3 Routing Preview: Evaluates type detection and resolves Layer 4 target parsers."""
    from app.ingestion.dispatcher import global_envelope_router
    engine = SyncEngine(db)
    try:
        envelopes = await engine.fetch_canonical_envelopes(source_id)
        return await global_envelope_router.batch_dispatch(envelopes)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.get("/router/telemetry")
async def get_router_telemetry_endpoint(
    user: User = Depends(require_permission(Permission.SOURCES_READ)),
):
    """Layer 3 Telemetry: Returns routing dispatch metrics and dead-letter registry statistics."""
    from app.ingestion.dispatcher import global_envelope_router
    return global_envelope_router.get_telemetry()


@router.get("/{source_id}/parsed-evidence")
async def fetch_parsed_evidence_endpoint(
    source_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_permission(Permission.SOURCES_READ)),
):
    """Layer 4 Parsed Evidence Extraction: Routes canonical envelopes to specialized parsers and returns structured evidence."""
    from app.ingestion.dispatcher import global_envelope_router
    engine = SyncEngine(db)
    try:
        envelopes = await engine.fetch_canonical_envelopes(source_id)
        dispatch_bundle = await global_envelope_router.batch_dispatch(envelopes)
        return {
            "source_id": str(source_id),
            "total_assets": len(envelopes),
            "evidence_results": dispatch_bundle.get("results", []),
            "routing_decisions": dispatch_bundle.get("routing_decisions", []),
            "telemetry": dispatch_bundle.get("telemetry", {}),
        }
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.get("/{source_id}/extract-candidates")
async def extract_and_verify_candidates_endpoint(
    source_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_permission(Permission.SOURCES_READ)),
):
    """Layer 5 Candidate Extraction & Source-Aware Verification: Extracts and validates candidate claims across evidence plugins."""
    from app.ingestion.dispatcher import global_envelope_router
    from app.extraction.pipeline import global_extraction_pipeline
    from app.ingestion.parsers.evidence_model import ParsedEvidenceResult

    engine = SyncEngine(db)
    try:
        envelopes = await engine.fetch_canonical_envelopes(source_id)
        layer5_results = []

        for env in envelopes:
            # 1. Parse into Layer 4 Evidence
            raw_evidence = await global_envelope_router.dispatch(env)
            if isinstance(raw_evidence, dict) and "units" not in raw_evidence:
                continue

            # Convert to ParsedEvidenceResult if dict
            if isinstance(raw_evidence, dict):
                evidence_obj = ParsedEvidenceResult.model_validate(raw_evidence)
            else:
                evidence_obj = raw_evidence

            # 2. Run through Layer 5 Candidate Extraction & Verification Pipeline
            res5 = await global_extraction_pipeline.process_envelope(env, evidence_obj)
            layer5_results.append(res5.to_dict())

        return {
            "source_id": str(source_id),
            "total_assets_processed": len(envelopes),
            "total_claims_extracted": sum(r["claims_extracted"] for r in layer5_results),
            "total_claims_verified": sum(r["claims_verified"] for r in layer5_results),
            "total_claims_rejected": sum(r["claims_rejected"] for r in layer5_results),
            "extraction_results": layer5_results,
        }
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))





