import decimal
import uuid
from datetime import datetime

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    JSON,
    Numeric,
    String,
    Text,
    text,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.db.enums import ConflictStatus


class ClaimConflict(Base):
    __tablename__ = "claim_conflicts"

    __table_args__ = (
        CheckConstraint(
            "confidence BETWEEN 0 AND 1",
            name="chk_conflict_confidence",
        ),
        CheckConstraint(
            "claim_a_id <> claim_b_id",
            name="chk_different_claims",
        ),
        Index(
            "idx_conflicts_claim_a",
            "claim_a_id",
        ),
        Index(
            "idx_conflicts_claim_b",
            "claim_b_id",
        ),
        Index(
            "idx_conflicts_status",
            "resolution_status",
        ),
        Index(
            "uq_claim_conflict_pair",
            text("LEAST(claim_a_id, claim_b_id)"),
            text("GREATEST(claim_a_id, claim_b_id)"),
            unique=True,
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )

    claim_a_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey(
            "claims.id",
            ondelete="CASCADE",
            name="fk_conflict_claim_a",
        ),
        nullable=False,
    )

    claim_b_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey(
            "claims.id",
            ondelete="CASCADE",
            name="fk_conflict_claim_b",
        ),
        nullable=False,
    )

    conflict_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
    )

    severity: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
    )

    confidence: Mapped[decimal.Decimal] = mapped_column(
        Numeric(5, 4),
        nullable=False,
    )

    resolution_status: Mapped[ConflictStatus] = mapped_column(
        Enum(
            ConflictStatus,
            name="conflict_status",
            native_enum=False,
            values_callable=lambda x: [e.value for e in x],
        ),
        nullable=False,
        default=ConflictStatus.DETECTED,
        server_default=text("'detected'"),
    )

    resolved_claim_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey(
            "claims.id",
            ondelete="SET NULL",
            name="fk_conflict_resolved_claim",
        ),
        nullable=True,
    )

    resolved_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey(
            "users.id",
            ondelete="SET NULL",
            name="fk_conflict_resolved_by",
        ),
        nullable=True,
    )

    resolved_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    # Master Plan Structured Conflict Contract Fields
    conflicting_fields: Mapped[list[str] | None] = mapped_column(
        JSON,
        nullable=True,
        default=list,
    )

    supporting_evidence: Mapped[dict | None] = mapped_column(
        JSON,
        nullable=True,
        default=dict,
    )

    source_authority: Mapped[dict | None] = mapped_column(
        JSON,
        nullable=True,
        default=dict,
    )

    applicable_scope: Mapped[dict | None] = mapped_column(
        JSON,
        nullable=True,
        default=dict,
    )

    effective_dates: Mapped[dict | None] = mapped_column(
        JSON,
        nullable=True,
        default=dict,
    )

    reviewer_decision: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True,
    )

    resolution_rationale: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=text("NOW()"),
    )

    # Relationships
    claim_a = relationship(
        "Claim",
        foreign_keys=[claim_a_id],
        back_populates="conflicts_as_a",
    )

    claim_b = relationship(
        "Claim",
        foreign_keys=[claim_b_id],
        back_populates="conflicts_as_b",
    )

    resolved_claim = relationship(
        "Claim",
        foreign_keys=[resolved_claim_id],
        back_populates="conflicts_resolved",
    )

    resolver = relationship(
        "User",
        foreign_keys=[resolved_by],
        back_populates="resolved_conflicts",
    )
