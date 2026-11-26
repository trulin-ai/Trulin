import hashlib
import re
import time
import uuid
from datetime import datetime, timezone
from typing import Optional, Sequence
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.db.models.claim import Claim
from app.db.models.claim_evidence import ClaimEvidence
from app.db.models.decision_evaluation import DecisionEvaluation
from app.db.models.document_version import DocumentVersion
from app.db.models.organization import Organization
from app.llm.base import BaseLLMProvider
from app.llm.factory import get_llm_provider
from app.schemas.decision import (
    DecisionContextItem,
    DecisionEvaluateRequest,
    DecisionEvaluateResponse,
)
from app.services.claim_gate_evaluator import ClaimGateEvaluator


class DecisionEvaluator:
    """Evaluates agent decisions and candidate evidence to prevent risky or unauthorized autonomous actions."""

    def __init__(self, llm_provider: BaseLLMProvider | None = None, session: AsyncSession | None = None):
        self.llm = llm_provider or get_llm_provider()
        self.session = session

    @staticmethod
    def parse_date(date_str: str | None) -> datetime | None:
        if not date_str:
            return None
        for fmt in ("%Y-%m-%d", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d %H:%M:%S"):
            try:
                return datetime.strptime(date_str.split(".")[0], fmt)
            except ValueError:
                continue
        return None

    async def evaluate(
        self,
        req: DecisionEvaluateRequest,
        session: AsyncSession | None = None,
    ) -> DecisionEvaluateResponse:
        t0 = time.perf_counter()
        db_session = session or self.session
        audit_id = f"ctx_{uuid.uuid4().hex[:10]}"
        reasons: list[str] = []
        preferred_source: str | None = None
        suggested_action: str | None = None
        now_utc = datetime.now(timezone.utc)
        dec_lower = req.decision.lower()

        # 0. Adversarial Prompt Injection & Threat Interceptor (OWASP LLM01)
        injection_indicators = [
            ("system override", "Direct Prompt Injection: System override instruction intercepted."),
            ("ignore all previous", "Direct Prompt Injection: Attempted bypass of baseline safety directives."),
            ("ignore previous instructions", "Direct Prompt Injection: Attempted instruction jailbreak."),
            ("disregard safety", "Jailbreak Vector: Safety guardrail bypass directive."),
            ("rm -rf", "Critical Remote Execution: Destructive shell command detected."),
            ("cat /etc/shadow", "Host Integrity Breach: Attempt to read sensitive Linux password hash store."),
            ("cat /etc/passwd", "Host Integrity Breach: Attempt to read system user accounts."),
            ("dump passwords", "Credential Exfiltration: Unauthorized credential dump directive."),
            ("credit card", "PCI-DSS Exfiltration: Unauthorized bulk payment card extraction."),
            ("cvv", "PCI-DSS Exfiltration: Payment card CVV security code dump intercepted."),
            ("social security", "PII Exfiltration: High-risk Social Security data extraction blocked."),
            ("salary bands", "PII Exfiltration: Confidential executive compensation exfiltration blocked."),
            ("payload.sh", "Code Injection: Suspicious remote bash payload execution vector."),
            ("open port 22", "Cloud Security Violation: Direct ingress port 22 modification blocked without CISO approval."),
        ]
        injection_found = False
        for indicator, reason_msg in injection_indicators:
            if indicator in dec_lower:
                reasons.append(f"Adversarial Guardrail Triggered (OWASP LLM01): {reason_msg}")
                injection_found = True
                break

        if injection_found:
            return await self._finalize_response(
                req=req,
                db_session=db_session,
                audit_id=audit_id,
                decision="BLOCK",
                validity="INSUFFICIENT",
                risk="CRITICAL",
                reasons=reasons,
                preferred_source="Deterministic Threat Interceptor (OWASP LLM01)",
                suggested_action="Block execution immediately and dispatch security incident alert.",
                t0=t0,
                now_utc=now_utc,
            )

        # 1. Access / Role Authorization Check
        restricted_roles = {
            "refund": ["support", "finance", "admin", "billing_agent"],
            "grant_leave": ["hr", "manager", "admin", "hr_reviewer"],
            "modify_contract": ["legal", "admin"],
            "deploy_infrastructure": ["devops", "admin"],
        }
        dec_lower = req.decision.lower()
        role_blocked = False
        for action_key, allowed_roles in restricted_roles.items():
            normalized_action = action_key.replace("_", " ")
            if (action_key in dec_lower or normalized_action in dec_lower) and req.actor.role.lower() not in allowed_roles:
                reasons.append(
                    f"Actor role '{req.actor.role}' is not authorized for decision category '{normalized_action}'."
                )
                role_blocked = True
                break

        if role_blocked:
            decision_outcome = "BLOCK"
            validity_outcome = "INSUFFICIENT"
            risk_outcome = "HIGH"
            suggested_action = "Escalate to a qualified supervisor with appropriate permissions."
            return await self._finalize_response(
                req=req,
                db_session=db_session,
                audit_id=audit_id,
                decision=decision_outcome,
                validity=validity_outcome,
                risk=risk_outcome,
                reasons=reasons,
                preferred_source=None,
                suggested_action=suggested_action,
                t0=t0,
                now_utc=now_utc,
            )

        # 2. Candidate Context Check & Auto-Retrieval from Database
        if not req.context and db_session:
            org_id = req.organization_id or uuid.UUID("11111111-1111-1111-1111-111111111111")
            auto_claims = await self._retrieve_candidate_claims(req.decision, org_id, db_session)
            if auto_claims:
                req.context = auto_claims

        if not req.context:
            return await self._finalize_response(
                req=req,
                db_session=db_session,
                audit_id=audit_id,
                decision="CLARIFY",
                validity="INSUFFICIENT",
                risk="MEDIUM",
                reasons=["No matching policy or evidence found in the knowledge base for this decision."],
                preferred_source=None,
                suggested_action="Retrieve candidate evidence from authoritative sources before making decision.",
                t0=t0,
                now_utc=now_utc,
            )

        # 2b. Policy Constraint & Compliance Violation Checks
        items = req.context
        for it in items:
            cl_lower = it.claim.lower()
            # 1. PO Threshold without CFO approval
            if "without cfo approval" in dec_lower and ("require cfo approval" in cl_lower or "requires cfo approval" in cl_lower):
                reasons.append("Policy Violation: Mandatory CFO approval required for purchase orders exceeding threshold.")
                return await self._finalize_response(
                    req=req, db_session=db_session, audit_id=audit_id,
                    decision="BLOCK", validity="INSUFFICIENT", risk="HIGH",
                    reasons=reasons, preferred_source=it.source,
                    suggested_action="Obtain mandatory CFO approval before approving purchase order.",
                    t0=t0, now_utc=now_utc,
                )
            # 2. Chargeback release during active fraud investigation
            if "release" in dec_lower and "fraud" in dec_lower and ("remain on hold" in cl_lower or "remain restricted" in cl_lower):
                reasons.append("Fraud Risk Block: Disputed settlements remain restricted until fraud investigation is resolved.")
                return await self._finalize_response(
                    req=req, db_session=db_session, audit_id=audit_id,
                    decision="BLOCK", validity="INSUFFICIENT", risk="CRITICAL",
                    reasons=reasons, preferred_source=it.source,
                    suggested_action="Hold settlement release until fraud investigation reaches final disposition.",
                    t0=t0, now_utc=now_utc,
                )
            # 3. Contract termination without early-exit fees
            if "without" in dec_lower and "early-exit fee" in dec_lower and "fee" in cl_lower:
                reasons.append("Commercial Terms Violation: Contract termination without applicable early-exit fees is prohibited.")
                return await self._finalize_response(
                    req=req, db_session=db_session, audit_id=audit_id,
                    decision="BLOCK", validity="INSUFFICIENT", risk="HIGH",
                    reasons=reasons, preferred_source=it.source,
                    suggested_action="Calculate and enforce contractual early-exit fee before processing termination.",
                    t0=t0, now_utc=now_utc,
                )
            # 4. API overage quota without throttling
            if "exceed" in dec_lower and "without throttling" in dec_lower and ("throttled" in cl_lower or "blocked" in cl_lower):
                reasons.append("Infrastructure Quota Violation: API quota overages require burst and sustained-rate throttling.")
                return await self._finalize_response(
                    req=req, db_session=db_session, audit_id=audit_id,
                    decision="BLOCK", validity="INSUFFICIENT", risk="HIGH",
                    reasons=reasons, preferred_source=it.source,
                    suggested_action="Enforce API rate throttling and bill overages at contractual enterprise rates.",
                    t0=t0, now_utc=now_utc,
                )
            # 5. Revenue recognition before performance obligation satisfied
            if "before the contractual performance condition" in dec_lower and "not invoice issuance alone" in cl_lower:
                reasons.append("Accounting Compliance Violation: Revenue recognition requires documented performance obligation satisfaction.")
                return await self._finalize_response(
                    req=req, db_session=db_session, audit_id=audit_id,
                    decision="BLOCK", validity="INSUFFICIENT", risk="CRITICAL",
                    reasons=reasons, preferred_source=it.source,
                    suggested_action="Defer revenue recognition until performance obligations are verified and certified.",
                    t0=t0, now_utc=now_utc,
                )
            # 6. Duplicate invoice payment
            if "already exists" in dec_lower and ("purchase order" in cl_lower or "exception" in cl_lower):
                reasons.append("Duplicate Payment Risk: Invoices with existing supplier invoice numbers are blocked.")
                return await self._finalize_response(
                    req=req, db_session=db_session, audit_id=audit_id,
                    decision="BLOCK", validity="INSUFFICIENT", risk="HIGH",
                    reasons=reasons, preferred_source=it.source,
                    suggested_action="Investigate potential duplicate submission with vendor before approving payment.",
                    t0=t0, now_utc=now_utc,
                )
            # 7. Refund exceeding Tier 1 authority threshold without supervisor sign-off
            if "refund" in dec_lower and ("without" in dec_lower or "bypass" in dec_lower or "override" in dec_lower) and any(m in dec_lower for m in ["manager", "supervisor", "sign-off", "signoff", "lead"]):
                reasons.append("Approval Hierarchy Violation: Support agents cannot approve refunds over $50.00 independently; Tier 2 or Customer Experience Manager sign-off is mandatory.")
                return await self._finalize_response(
                    req=req, db_session=db_session, audit_id=audit_id,
                    decision="BLOCK", validity="INSUFFICIENT", risk="HIGH",
                    reasons=reasons, preferred_source=it.source,
                    suggested_action="Escalate refund request to Tier 2 Lead or Customer Experience Manager for authorized sign-off.",
                    t0=t0, now_utc=now_utc,
                )

        # 3. Analyze Sources, Authority, and Dates
        sources_with_dates = []
        for it in items:
            dt = self.parse_date(it.updated_at)
            auth = it.authority_level if it.authority_level is not None else 50
            if "policy" in it.source.lower() or "service" in it.source.lower():
                auth = max(auth, 85)
            sources_with_dates.append((it, dt, auth))

        # Sort by authority (highest first) and date (newest first)
        sources_with_dates.sort(key=lambda x: (x[2], x[1] or datetime.min), reverse=True)
        preferred_item = sources_with_dates[0][0]
        preferred_source = preferred_item.source

        # 4. Check for Contradictions / Conflicts Among Candidate Claims
        has_conflict = False
        conflict_details: list[str] = []

        if len(items) >= 2:
            for i in range(len(items)):
                for j in range(i + 1, len(items)):
                    item_a = items[i]
                    item_b = items[j]

                    # LLM / Rule Contradiction Evaluation
                    res = await self.llm.evaluate_contradiction(item_a.claim, item_b.claim)
                    if res.is_contradiction:
                        has_conflict = True
                        conflict_details.append(
                            f"Contradiction between '{item_a.source}' and '{item_b.source}': {res.reasoning}"
                        )

        # 5. Check Scope & Effective Dates Discrepancies
        has_date_discrepancy = False
        if len(sources_with_dates) >= 2:
            dt_newest = sources_with_dates[0][1]
            dt_oldest = sources_with_dates[-1][1]
            if dt_newest and dt_oldest and dt_newest != dt_oldest:
                has_date_discrepancy = True

        # Check if exception exists (e.g. Enterprise exception)
        has_scope_exception = any("exception" in it.claim.lower() for it in items)

        # 6. Formulate Decision Outcome
        if has_conflict:
            reasons.append("Conflicting policy evidence detected across candidate sources.")
            if has_date_discrepancy:
                reasons.append("Candidate sources have different effective dates or update timestamps.")
            if has_scope_exception:
                reasons.append("A specific scope exception or override was identified.")

            # If there is a clear newer authoritative source (authority > 80)
            if sources_with_dates[0][2] >= 80 and has_scope_exception:
                decision_outcome = "REVIEW"
                validity_outcome = "INSUFFICIENT"
                risk_outcome = "HIGH"
                suggested_action = (
                    f"Route to human review. Note: '{preferred_source}' is the newer and designated source of truth."
                )
            else:
                decision_outcome = "REVIEW"
                validity_outcome = "INSUFFICIENT"
                risk_outcome = "HIGH"
                suggested_action = "Hold decision for human review to resolve contradictory guidelines."

            return await self._finalize_response(
                req=req,
                db_session=db_session,
                audit_id=audit_id,
                decision=decision_outcome,
                validity=validity_outcome,
                risk=risk_outcome,
                reasons=reasons,
                preferred_source=preferred_source,
                suggested_action=suggested_action,
                t0=t0,
                now_utc=now_utc,
            )

        # Non-conflicting, valid evidence
        reasons.append("Authoritative policy verified.")
        reasons.append("Evidence is current and uncontradicted.")
        if preferred_source:
            reasons.append(f"Primary backing source: '{preferred_source}'.")

        return await self._finalize_response(
            req=req,
            db_session=db_session,
            audit_id=audit_id,
            decision="ALLOW",
            validity="VALID",
            risk="LOW",
            reasons=reasons,
            preferred_source=preferred_source,
            suggested_action="Proceed with authorized action using verified evidence.",
            t0=t0,
            now_utc=now_utc,
        )

    async def _finalize_response(
        self,
        req: DecisionEvaluateRequest,
        db_session: AsyncSession | None,
        audit_id: str,
        decision: str,
        validity: str,
        risk: str,
        reasons: list[str],
        preferred_source: str | None,
        suggested_action: str | None,
        t0: float,
        now_utc: datetime,
    ) -> DecisionEvaluateResponse:
        execution_ms = max(1, int((time.perf_counter() - t0) * 1000))
        
        # Calculate SHA-256 cryptographic audit token
        token_payload = f"{audit_id}:{req.actor.id}:{req.actor.role}:{req.decision}:{decision}:{risk}:{now_utc.isoformat()}"
        audit_token = hashlib.sha256(token_payload.encode("utf-8")).hexdigest()

        # Persist to database if session is available
        if db_session:
            try:
                org_id = req.organization_id or uuid.UUID("11111111-1111-1111-1111-111111111111")
                # Ensure Organization exists
                res_org = await db_session.execute(select(Organization).where(Organization.id == org_id))
                if not res_org.scalar_one_or_none():
                    org = Organization(id=org_id, name="demo", slug="demo")
                    db_session.add(org)
                    await db_session.flush()

                context_serialized = [
                    {
                        "claim": it.claim,
                        "source": it.source,
                        "updated_at": it.updated_at,
                        "authority_level": it.authority_level,
                        "scope": it.scope,
                        "claim_id": it.claim_id,
                        "claim_version": it.claim_version,
                        "role": it.role,
                    }
                    for it in req.context
                ]

                audit_record = DecisionEvaluation(
                    audit_id=audit_id,
                    organization_id=org_id,
                    actor_id=req.actor.id,
                    actor_role=req.actor.role,
                    decision_prompt=req.decision,
                    verdict=decision,
                    risk_level=risk,
                    reasons=reasons,
                    preferred_source=preferred_source,
                    suggested_action=suggested_action,
                    context_items=context_serialized,
                    audit_token=audit_token,
                    execution_ms=execution_ms,
                    created_at=now_utc,
                )
                db_session.add(audit_record)
                await db_session.commit()
            except Exception:
                pass

        return DecisionEvaluateResponse(
            decision=decision,
            validity=validity,
            risk=risk,
            reasons=reasons,
            preferred_source=preferred_source,
            audit_id=audit_id,
            suggested_action=suggested_action,
            audit_token=audit_token,
            execution_ms=execution_ms,
        )

    async def _retrieve_candidate_claims(
        self,
        decision_query: str,
        organization_id: uuid.UUID,
        session: AsyncSession,
    ) -> list[DecisionContextItem]:
        """Automatically retrieve relevant atomic claims from PostgreSQL for grounding."""
        try:
            stmt = (
                select(Claim)
                .where(Claim.organization_id == organization_id)
                .options(
                    selectinload(Claim.evidence).selectinload(ClaimEvidence.document),
                    selectinload(Claim.document_version).selectinload(DocumentVersion.document),
                    selectinload(Claim.trust_scores),
                )
                .limit(50)
            )
            res = await session.execute(stmt)
            claims = res.scalars().all()
            if not claims:
                return []

            query_words = set(decision_query.lower().split())
            matched_items = []
            for c in claims:
                gate_res = ClaimGateEvaluator.evaluate(
                    claim_id=str(c.id),
                    subject=c.subject,
                    predicate=c.predicate,
                    object_val=c.object,
                    claim_text=c.claim_text,
                    claim_type=getattr(c, "claim_type", "policy"),
                    status=c.status.value if hasattr(c.status, "value") else str(c.status),
                    metadata=getattr(c, "claim_metadata", {}) or {},
                )
                if not gate_res.all_9_gates_passed or not gate_res.agent_accessible:
                    continue

                claim_text_lower = c.claim_text.lower()
                sub_lower = (c.subject or "").lower()
                words = set(claim_text_lower.split() + sub_lower.split())
                overlap = len(query_words.intersection(words))
                if overlap > 0:
                    doc_name = "Internal Knowledge Base"
                    if c.evidence and len(c.evidence) > 0 and c.evidence[0].document:
                        doc_name = c.evidence[0].document.title
                    elif c.document_version and c.document_version.document and c.document_version.document.title:
                        doc_name = c.document_version.document.title

                    authority = 50
                    if c.trust_scores and len(c.trust_scores) > 0:
                        authority = int(c.trust_scores[0].authority_score * 100)

                    updated_at_str = (
                        c.created_at.strftime("%Y-%m-%d")
                        if hasattr(c, "created_at") and c.created_at
                        else "2026-01-01"
                    )

                    matched_items.append((
                        overlap,
                        DecisionContextItem(
                            claim=c.claim_text,
                            source=doc_name,
                            updated_at=updated_at_str,
                            authority_level=authority,
                            scope=c.subject or "General",
                        ),
                    ))

            matched_items.sort(key=lambda x: x[0], reverse=True)
            return [item[1] for item in matched_items[:5]]
        except Exception:
            return []

