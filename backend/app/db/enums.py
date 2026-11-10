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

