"""
Platform Data Reset & Clean Baseline Bootstrapper.

Completely wipes all platform data:
1. Truncates all transactional, governance, and entity tables in PostgreSQL.
2. Clears all uploaded files and document artifacts from storage/uploads.
3. Resets in-memory telemetry and review logs.
4. Idempotently provisions a pristine primary enterprise organization (SSFA Capital Holdings)
   with the 5 canonical personas (Sarah Chen, Marcus Vance, Elena Rostova, Alex Vance, Devin Zhao),
   standard folder hierarchy, and dedicated file upload connector.
"""

import asyncio
import os
import shutil
import sys
import uuid
from pathlib import Path

# Ensure backend root is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from sqlalchemy import text
from app.db.database import AsyncSessionLocal
from app.db.enums import RecordStatus, SourceFamily, SourceIntent, UserRole
from app.db.models.data_source import DataSource
from app.db.models.organization import Organization
from app.db.repositories.user_repository import UserRepository
from app.services.feedback_telemetry_service import FeedbackTelemetryService
from app.services.folder_service import FolderService


PRIMARY_ORG_ID = uuid.UUID("11111111-1111-1111-1111-111111111111")
STORAGE_UPLOADS_DIR = Path(__file__).resolve().parents[1] / "storage" / "uploads"

TABLES_TO_WIPE = [
    "agent_context_items",
    "agent_requests",
    "agents",
    "chat_messages",
    "chat_sessions",
    "claim_conflicts",
    "claim_trust_scores",
    "claim_validity",
    "claim_evidence",
    "claims",
    "decision_evaluations",
    "document_versions",
    "documents",
    "folders",
    "data_sources",
    "hitl_escalations",
    "human_reviews",
    "organization_invites",
    "user_activity_logs",
    "webhook_dispatch_logs",
    "webhook_subscriptions",
    "users",
    "organizations",
]


async def reset_platform_data():
    print("=" * 80)
    print("TRULIN PLATFORM — COMPLETE DATA RESET & FRESH BOOTSTRAP")
    print("=" * 80)

    # 1. Truncate PostgreSQL tables
    print("\n[Step 1/4] Truncating database tables...")
    async with AsyncSessionLocal() as session:
        # Get existing public tables to avoid truncating non-existent ones
        res = await session.execute(
            text("SELECT table_name FROM information_schema.tables WHERE table_schema = 'public'")
        )
        existing_tables = set(r[0] for r in res.fetchall())

        tables_to_truncate = [t for t in TABLES_TO_WIPE if t in existing_tables]
        truncate_sql = f"TRUNCATE TABLE {', '.join(tables_to_truncate)} CASCADE;"
        print(f"  Executing TRUNCATE on {len(tables_to_truncate)} tables...")
        await session.execute(text(truncate_sql))
        await session.commit()
        print("  -> Database tables truncated successfully.")

    # 2. Clear storage/uploads directory
    print("\n[Step 2/4] Wiping physical file storage...")
    if STORAGE_UPLOADS_DIR.exists():
        file_count = 0
        dir_count = 0
        for item in STORAGE_UPLOADS_DIR.iterdir():
            if item.is_dir():
                shutil.rmtree(item)
                dir_count += 1
            else:
                item.unlink()
                file_count += 1
        print(f"  -> Removed {dir_count} document folders and {file_count} standalone files.")
    else:
        STORAGE_UPLOADS_DIR.mkdir(parents=True, exist_ok=True)
    STORAGE_UPLOADS_DIR.mkdir(parents=True, exist_ok=True)
    print("  -> Storage uploads directory is clean and ready.")

    # 3. Clear In-Memory Telemetry Logs
    print("\n[Step 3/4] Resetting in-memory telemetry...")
    FeedbackTelemetryService.clear_pilot_feedback()
    print("  -> In-memory feedback logs cleared.")

    # 4. Bootstrap Clean Primary Enterprise Organization
    print("\n[Step 4/4] Provisioning clean primary organization & personas...")
    async with AsyncSessionLocal() as session:
        # 4a. Create Primary Organization
        org = Organization(
            id=PRIMARY_ORG_ID,
            name="SSFA Capital Holdings",
            slug="ssfa-capital",
            domain_whitelist=["ssfa.com", "regulatory-watch.org", "demo.local"],
            allowed_auth_methods=["password", "sso", "persona"],
            governance_config={
                "min_trust_score": 0.85,
                "require_steward_approval": True,
                "auto_quarantine_on_conflict": True,
            },
            setup_completed=True,
        )
        session.add(org)
        await session.flush()
        print(f"  -> Primary Organization created: {org.name} ({org.id})")

        # 4b. Seed Canonical Enterprise Personas
        user_repo = UserRepository(session)
        seeded_users = await user_repo.seed_default_personas(PRIMARY_ORG_ID)
        await session.flush()
        print(f"  -> Seeded {len(seeded_users)} canonical personas:")
        for u in seeded_users:
            print(f"     - {u.name} ({u.email}) [Role: {u.role.value if hasattr(u.role, 'value') else u.role}]")

        # 4c. Provision Standard Enterprise Folder Hierarchy
        folder_service = FolderService(session)
        inbox = await folder_service.ensure_system_inbox(PRIMARY_ORG_ID)
        hierarchy = await folder_service.ensure_enterprise_hierarchy(PRIMARY_ORG_ID)
        await session.flush()
        print(f"  -> Enterprise Folder Hierarchy provisioned: Inbox + {len(hierarchy)} domain folders")

        # 4d. Provision Dedicated Direct File Upload Data Source
        upload_source = DataSource(
            id=uuid.uuid4(),
            organization_id=PRIMARY_ORG_ID,
            name="Direct Document Upload",
            source_type="file",
            source_family=SourceFamily.DOCUMENT,
            source_intent=SourceIntent.GOVERNANCE_POLICY,
            external_id=f"file-upload-{str(PRIMARY_ORG_ID)[:8]}",
            authority_level=85,
            status=RecordStatus.ACTIVE,
            scope_config={"include_all_uploads": True},
            capabilities={"supports_file_upload": True, "supports_snapshots": True},
        )
        session.add(upload_source)
        await session.commit()
        print(f"  -> Dedicated File Upload Data Source provisioned: {upload_source.name}")

    # 5. Final Verification of Database State
    print("\n" + "=" * 80)
    print("VERIFYING CLEAN DATABASE STATE")
    print("=" * 80)
    async with AsyncSessionLocal() as session:
        for t in [
            "organizations",
            "users",
            "folders",
            "data_sources",
            "documents",
            "document_versions",
            "claims",
            "claim_evidence",
            "claim_conflicts",
            "chat_sessions",
            "chat_messages",
            "decision_evaluations",
        ]:
            cnt = (await session.execute(text(f'SELECT COUNT(*) FROM "{t}"'))).scalar()
            print(f"  - {t}: {cnt}")

    print("\n" + "=" * 80)
    print("PLATFORM DATA RESET COMPLETE — CLEAN SLATE READY FOR TESTING")
    print("=" * 80)


if __name__ == "__main__":
    asyncio.run(reset_platform_data())
