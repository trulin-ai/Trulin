"""
Governed Context Package Schema (Enterprise Context Fabric Pattern).

Instead of treating retrieved context as loose, unanchored strings of text,
the GovernedContextPackage bundles:
1. Exact authoritative source identity & content hash
2. Verbatim evidence locator (exact quote and byte offsets)
3. Normative rule text with explicit modality (MUST, CANNOT, MAY, IS)
4. Explicit Actor and Recipient to prevent pronoun and directional reversals
5. Specific timing and deadline constraints (e.g. 'immediately upon receipt' vs 'within 30 days')
6. Conditions, Applicability scope, and Lex Specialis exceptions
7. Certification provenance (Human steward signed vs automated 9-gate certified)
8. Mirrored RBAC access roles
"""

from typing import Any
from pydantic import BaseModel, Field


class GovernedContextPackage(BaseModel):
    claim_id: str
    document_id: str | None = None
    document_title: str = "Enterprise Knowledge Repository"
    document_version_hash: str | None = None
    folder_name: str | None = None
    folder_id: str | None = None
    section: str | None = None
    page: int | None = None

    # Operative Rule & Verbatim Evidence
    rule_text: str
    verbatim_evidence: str
    byte_offsets: tuple[int, int] | None = None

    # Directed Semantics (prevents actor/recipient reversal)
    actor: str | None = None
    recipient: str | None = None
    modality: str = "MUST"  # MUST, CANNOT, MAY, IS, SHOULD
    timing_or_deadline: str | None = None  # e.g. "immediately upon receipt", "within 30 days"

    # Contextual Boundaries & Lex Specialis Exceptions
    topic: str | None = None
    conditions: list[str] = Field(default_factory=list)
    exceptions: list[str] = Field(default_factory=list)
    jurisdiction_or_scope: str = "global"

    # Governance & Verification Provenance
    certification_provenance: str = "automated_gate_passed"  # "human_steward_approved", "automated_gate_passed"
    certifier_name: str | None = None
    rbac_access_roles: list[str] = Field(default_factory=lambda: ["admin", "data_owner", "reviewer", "developer"])
    trust_score: float = 0.85
    evidence_lane: str = "canonical"  # "canonical" (for execution) vs "passage" (for explanation)

    def to_dict(self) -> dict[str, Any]:
        return {
            "claim_id": self.claim_id,
            "document_id": self.document_id,
            "document_title": self.document_title,
            "document_version_hash": self.document_version_hash,
            "folder_name": self.folder_name,
            "folder_id": self.folder_id,
            "section": self.section,
            "page": self.page,
            "rule_text": self.rule_text,
            "verbatim_evidence": self.verbatim_evidence,
            "byte_offsets": self.byte_offsets,
            "actor": self.actor,
            "recipient": self.recipient,
            "modality": self.modality,
            "timing_or_deadline": self.timing_or_deadline,
            "topic": self.topic,
            "conditions": self.conditions,
            "exceptions": self.exceptions,
            "jurisdiction_or_scope": self.jurisdiction_or_scope,
            "certification_provenance": self.certification_provenance,
            "certifier_name": self.certifier_name,
            "rbac_access_roles": self.rbac_access_roles,
            "trust_score": self.trust_score,
            "evidence_lane": self.evidence_lane,
        }
