from enum import Enum


class OrganizationStatus(str, Enum):
    ACTIVE = "active"
    SUSPENDED = "suspended"
    DELETED = "deleted"


class UserRole(str, Enum):
    ADMIN = "admin"
    DATA_OWNER = "data_owner"
    REVIEWER = "reviewer"
    DEVELOPER = "developer"
    VIEWER = "viewer"
    COMPLIANCE_OFFICER = "compliance_officer"
    AUDITOR = "auditor"


class RecordStatus(str, Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"
    DELETED = "deleted"
    PROCESSING = "processing"
    FAILED = "failed"


class ClaimStatus(str, Enum):
    CANDIDATE = "candidate"
    VERIFIED = "verified"
    REJECTED = "rejected"
    OUTDATED = "outdated"
    CONFLICTED = "conflicted"
    ACTIVE = "active"
    SUPERSEDED = "superseded"


class ConflictStatus(str, Enum):
    DETECTED = "detected"
    HUMAN_REVIEW_REQUIRED = "human_review_required"
    RESOLVED = "resolved"
    DISMISSED = "dismissed"
    UNRESOLVED_AMBIGUITY = "UNRESOLVED_AMBIGUITY"
    UNRESOLVED_AMBIGUITY_LOWER = "unresolved_ambiguity"


class ConflictType(str, Enum):
    """The 10 first-class conflict types required by the Master Plan."""
    DIRECT_CONTRADICTION = "direct_contradiction"
    TEMPORAL_CONFLICT = "temporal_conflict"
    SCOPE_CONFLICT = "scope_conflict"
    AUTHORITY_CONFLICT = "authority_conflict"
    NUMERIC_CONFLICT = "numeric_conflict"
    MODALITY_CONFLICT = "modality_conflict"
    EXCEPTION_CONFLICT = "exception_conflict"
    ORGANIZATIONAL_CONFLICT = "organizational_conflict"
    VERSION_CONFLICT = "version_conflict"
    CONDITIONAL_CONFLICT = "conditional_conflict"

    @classmethod
    def normalize(cls, value: object) -> "ConflictType":
        """Normalize legacy strings or partial tokens into the canonical 10 types."""
        if isinstance(value, cls):
            return value
        if not value or not isinstance(value, str):
            return cls.DIRECT_CONTRADICTION
        v = value.lower().strip()
        mapping = {
            "direct_contradiction": cls.DIRECT_CONTRADICTION,
            "contradiction": cls.DIRECT_CONTRADICTION,
            "policy_contradiction": cls.DIRECT_CONTRADICTION,
            "temporal_conflict": cls.TEMPORAL_CONFLICT,
            "temporal_outdated": cls.TEMPORAL_CONFLICT,
            "outdated": cls.TEMPORAL_CONFLICT,
            "expired": cls.TEMPORAL_CONFLICT,
            "temporal_expiration_precedence": cls.TEMPORAL_CONFLICT,
            "temporal_obsolescence": cls.TEMPORAL_CONFLICT,
            "scope_conflict": cls.SCOPE_CONFLICT,
            "disjoint_scopes": cls.SCOPE_CONFLICT,
            "applicability_scope_discrepancy": cls.SCOPE_CONFLICT,
            "disjoint_applicability_scope": cls.SCOPE_CONFLICT,
            "authority_conflict": cls.AUTHORITY_CONFLICT,
            "authority_hierarchy_precedence": cls.AUTHORITY_CONFLICT,
            "authority_discrepancy": cls.AUTHORITY_CONFLICT,
            "numeric_conflict": cls.NUMERIC_CONFLICT,
            "numerical_discrepancy": cls.NUMERIC_CONFLICT,
            "incompatible_numeric_value": cls.NUMERIC_CONFLICT,
            "numeric_value_mismatch": cls.NUMERIC_CONFLICT,
            "genuine_boundary_ambiguity": cls.NUMERIC_CONFLICT,
            "modality_conflict": cls.MODALITY_CONFLICT,
            "deontic_opposition": cls.MODALITY_CONFLICT,
            "modality_opposition": cls.MODALITY_CONFLICT,
            "exception_conflict": cls.EXCEPTION_CONFLICT,
            "lex_specialis_exception": cls.EXCEPTION_CONFLICT,
            "compatible_exception": cls.EXCEPTION_CONFLICT,
            "organizational_conflict": cls.ORGANIZATIONAL_CONFLICT,
            "cross_department": cls.ORGANIZATIONAL_CONFLICT,
            "inter_departmental": cls.ORGANIZATIONAL_CONFLICT,
            "version_conflict": cls.VERSION_CONFLICT,
            "temporal_version_precedence": cls.VERSION_CONFLICT,
            "version_lineage": cls.VERSION_CONFLICT,
            "conditional_conflict": cls.CONDITIONAL_CONFLICT,
            "conditional_mismatch": cls.CONDITIONAL_CONFLICT,
            "precondition_conflict": cls.CONDITIONAL_CONFLICT,
            "non_overlapping_conditional_scope": cls.CONDITIONAL_CONFLICT,
        }
        return mapping.get(v, cls.DIRECT_CONTRADICTION)


class ReviewDecision(str, Enum):
    APPROVE = "approve"
    REJECT = "reject"
    OVERRIDE = "override"
    MARK_OUTDATED = "mark_outdated"
    MERGE = "merge"
    ESCALATE = "escalate"


class SourceFamily(str, Enum):
    """Native source family categories harmonized between Layer 1 & Layer 2."""
    DOCUMENT = "document"                    # PDF, DOCX, Markdown, HTML, Confluence pages
    STRUCTURED = "structured"                # Layer 2 primary naming
    STRUCTURED_DATA = "structured"           # Layer 1 alias
    CONVERSATION = "conversation"            # Slack, Teams, Jira comments, Email threads
    CONVERSATIONAL = "conversation"          # Alias
    METADATA = "metadata"                    # Layer 2 primary naming
    METADATA_OPERATIONAL = "metadata"        # Layer 1 alias

    @classmethod
    def _missing_(cls, value: object):
        if isinstance(value, str):
            val_lower = value.lower().strip()
            if val_lower in ("structured", "structured_data", "relational", "database"):
                return cls.STRUCTURED
            if val_lower in ("metadata", "metadata_operational"):
                return cls.METADATA
            if val_lower in ("document", "documents", "file"):
                return cls.DOCUMENT
            if val_lower in ("conversation", "conversational", "chat", "discussions"):
                return cls.CONVERSATION
        return super()._missing_(value)


class SourceIntent(str, Enum):
    """Business semantic intent declared for data source to prevent misclassification."""
    GOVERNANCE_POLICY = "governance_policy"  # Mandatory policies, compliance regulations, constraints
    OPERATIONAL_DATA = "operational_data"    # Operational records, facts, telemetry, DB records
    PROPOSALS_DISCUSSIONS = "discussions"    # Ideas, proposals, discussions, meeting notes
    FACTUAL_KNOWLEDGE = "factual_knowledge"  # Q&A pairs, data dictionary, definitions
    ANALYTICS_METRIC = "analytics_metric"    # Calculated measures, KPIs, aggregation rules

