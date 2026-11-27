from enum import Enum
from typing import Any, Dict, List, Set, Union

from app.db.enums import UserRole


class Permission(str, Enum):
    # Data Sources & Ingestion
    SOURCES_READ = "sources:read"
    SOURCES_SYNC = "sources:sync"
    SOURCES_MANAGE = "sources:manage"

    # Claims & Policy Truth
    CLAIMS_READ = "claims:read"
    CLAIMS_EXTRACT = "claims:extract"
    CLAIMS_EDIT = "claims:edit"
    CLAIMS_DELETE = "claims:delete"

    # Governance Issues & Conflict Engine
    CONFLICTS_READ = "conflicts:read"
    CONFLICTS_RESOLVE = "conflicts:resolve"
    CONFLICTS_OVERRIDE = "conflicts:override"

    # AI Decision Engine & Provenance Audit
    DECISIONS_EVALUATE = "decisions:evaluate"
    DECISIONS_AUDIT = "decisions:audit"

    # Organization & Workspace Governance
    ORG_SETTINGS_MANAGE = "org:settings"
    ORG_MEMBERS_MANAGE = "org:members"
    ORG_INVITE = "org:invite"


# Enterprise Role Permission Matrix (Separation of Duties enforced)
ROLE_PERMISSIONS: Dict[str, Set[str]] = {
    # 1. Chief Compliance Officer / Admin: Full System Authority
    "admin": {p.value for p in Permission},

    # 2. Data Steward: Ingestion, Pipeline Sync, Claim Extraction & Curation
    # NOTE: Restricted from resolving policy conflicts (Separation of Duties)
    "data_owner": {
        Permission.SOURCES_READ.value,
        Permission.SOURCES_SYNC.value,
        Permission.SOURCES_MANAGE.value,
        Permission.CLAIMS_READ.value,
        Permission.CLAIMS_EXTRACT.value,
        Permission.CLAIMS_EDIT.value,
        Permission.CONFLICTS_READ.value,
        Permission.DECISIONS_EVALUATE.value,
        Permission.DECISIONS_AUDIT.value,
    },

    # 3. Risk Auditor: Conflict Resolution, Claim Verification, Audit Validation
    # NOTE: Restricted from modifying raw data source pipelines
    "reviewer": {
        Permission.SOURCES_READ.value,
        Permission.CLAIMS_READ.value,
        Permission.CONFLICTS_READ.value,
        Permission.CONFLICTS_RESOLVE.value,
        Permission.DECISIONS_EVALUATE.value,
        Permission.DECISIONS_AUDIT.value,
    },

    # 4. Operator / Developer / AI Agent: Runtime Decision Evaluations & Claims Querying
    # NOTE: Read-only governance; cannot modify policy definitions or resolve conflicts
    "developer": {
        Permission.SOURCES_READ.value,
        Permission.CLAIMS_READ.value,
        Permission.CONFLICTS_READ.value,
        Permission.DECISIONS_EVALUATE.value,
    },

    # 5. Viewer: Read-only provenance and compliance observation
    "viewer": {
        Permission.SOURCES_READ.value,
        Permission.CLAIMS_READ.value,
        Permission.CONFLICTS_READ.value,
    },

    # 6. Compliance Officer: Full audit & conflict resolution authority, restricted from raw source management
    "compliance_officer": {
        Permission.SOURCES_READ.value,
        Permission.CLAIMS_READ.value,
        Permission.CLAIMS_EDIT.value,
        Permission.CONFLICTS_READ.value,
        Permission.CONFLICTS_RESOLVE.value,
        Permission.CONFLICTS_OVERRIDE.value,
        Permission.DECISIONS_EVALUATE.value,
        Permission.DECISIONS_AUDIT.value,
    },

    # 7. Auditor: Read-only audit observation across all surfaces
    "auditor": {
        Permission.SOURCES_READ.value,
        Permission.CLAIMS_READ.value,
        Permission.CONFLICTS_READ.value,
        Permission.DECISIONS_AUDIT.value,
    },
}


def normalize_role_str(role: Union[UserRole, str]) -> str:
    """Normalize role string or UserRole enum value."""
    if hasattr(role, "value"):
        return str(role.value).lower().strip()
    return str(role).lower().strip()


def has_permission(role: Union[UserRole, str], permission: Union[Permission, str]) -> bool:
    """Check if a given role possesses the requested permission."""
    r_str = normalize_role_str(role)
    p_str = permission.value if isinstance(permission, Permission) else str(permission)
    role_perms = ROLE_PERMISSIONS.get(r_str, set())
    return p_str in role_perms


def get_role_permissions(role: Union[UserRole, str]) -> List[str]:
    """Retrieve all granted permission strings for a role."""
    r_str = normalize_role_str(role)
    return sorted(list(ROLE_PERMISSIONS.get(r_str, set())))


def get_permission_matrix() -> Dict[str, Any]:
    """Return comprehensive metadata describing the entire RBAC permission matrix."""
    roles_metadata = {
        "admin": {
            "title": "Chief Compliance Officer (CCO)",
            "description": "Executive authority: full tenant governance, policy overrides, user promotions, and audit sign-offs.",
            "separation_of_duties": "Executive override authority across all workflows.",
            "badge_color": "#047857",
        },
        "data_owner": {
            "title": "Data Steward",
            "description": "Authority over data source ingestion, pipeline syncs, document ingestion, and claim definition curation.",
            "separation_of_duties": "Restricted from resolving policy conflicts to prevent unilateral compliance tampering.",
            "badge_color": "#1D4ED8",
        },
        "reviewer": {
            "title": "Risk Auditor / Reviewer",
            "description": "Authority to review, approve, and resolve semantic policy contradictions and evidence exceptions.",
            "separation_of_duties": "Restricted from altering source ingestion connectors.",
            "badge_color": "#4338CA",
        },
        "developer": {
            "title": "Operator / Developer / Agent",
            "description": "Operational access to query verified context layer and evaluate AI agent decision compliance.",
            "separation_of_duties": "Read-only policy access; no authority to resolve conflicts or alter sources.",
            "badge_color": "#B45309",
        },
        "viewer": {
            "title": "Compliance Observer",
            "description": "Read-only access to trust score dashboards and lineage graphs.",
            "separation_of_duties": "Zero mutation privileges.",
            "badge_color": "#64748B",
        },
        "compliance_officer": {
            "title": "Compliance Officer",
            "description": "Dedicated compliance authority: conflict resolution, policy override, and audit sign-off across governance workflows.",
            "separation_of_duties": "Restricted from direct source ingestion and pipeline management.",
            "badge_color": "#6D28D9",
        },
        "auditor": {
            "title": "External Auditor",
            "description": "Read-only audit observation across all surfaces including decisions, conflicts, and provenance graphs.",
            "separation_of_duties": "Zero mutation privileges; observation-only access.",
            "badge_color": "#78716C",
        },
    }

    matrix = {}
    for role_key, meta in roles_metadata.items():
        matrix[role_key] = {
            **meta,
            "permissions": get_role_permissions(role_key),
        }

    return {
        "roles": matrix,
        "all_permissions": [p.value for p in Permission],
    }
