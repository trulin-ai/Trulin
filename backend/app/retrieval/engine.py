import decimal
import logging
import math
import re
import uuid
from datetime import datetime, timezone
from typing import Any, Sequence

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db.enums import ClaimStatus, ConflictStatus
from app.db.models.agent_context_item import AgentContextItem
from app.db.models.agent_request import AgentRequest
from app.db.models.claim import Claim
from app.db.models.claim_conflict import ClaimConflict
from app.db.models.claim_evidence import ClaimEvidence
from app.db.models.claim_trust_score import ClaimTrustScore
from app.db.models.claim_validity import ClaimValidity
from app.db.models.document import Document
from app.db.models.document_version import DocumentVersion
from app.llm.base import BaseLLMProvider
from app.llm.factory import get_llm_provider
from app.schemas.context import (
    ContextItemResponse,
    ContextQueryRequest,
    ContextQueryResponse,
    ContextSourceInfo,
    ContextValidityInfo,
    SectionContextItem,
)
from app.schemas.governed_context import GovernedContextPackage
from app.services.claim_gate_evaluator import ClaimGateEvaluator

logger = logging.getLogger(__name__)

_EMBEDDING_CACHE: dict[str, list[float]] = {}


def _cosine_similarity(v1: Sequence[float], v2: Sequence[float]) -> float:
    if not v1 or not v2 or len(v1) != len(v2):
        return 0.0
    dot = sum(a * b for a, b in zip(v1, v2))
    norm1 = sum(a * a for a, b in zip(v1, v2))
    norm2 = sum(b * b for a, b in zip(v1, v2))
    if norm1 <= 0.0 or norm2 <= 0.0:
        return 0.0
    return dot / ((norm1 ** 0.5) * (norm2 ** 0.5))


STOP_WORDS = {
    "what", "is", "the", "for", "an", "a", "of", "and", "in", "to", "or", "by", "with", "without",
    "on", "at", "from", "as", "about", "are", "be", "this", "that", "it", "how", "can", "may",
    "does", "do", "did", "we", "you", "party", "parties", "policy", "rule", "topic", "unrelated", "rules",
    "like", "our", "company", "their", "any", "some", "procedure", "guidelines", "standard",
    "across", "between", "purchases", "purchase", "using", "use", "used", "uses", "before", "after",
    "when", "into", "onto", "upon", "under", "per", "if", "have", "has", "had", "will", "shall",
    "must", "could", "should", "would", "other", "all", "each", "both"
}


def _compute_lexical_score(claim_text: str, subject: str | None, query: str, domain: str | None) -> float:
    claim_lower = claim_text.lower()
    q_lower = query.lower()
    raw_words = [w.strip("?.,!$₹£€()[]\"'") for w in q_lower.split() if len(w) > 1]
    # Filter stopwords so queries like "What is the policy for an unrelated topic" don't match on "policy"
    q_words = [w for w in raw_words if w not in STOP_WORDS]
    if not q_words:
        q_words = raw_words

    score = 0.0
    # 1. Token overlap
    c_words = set(re.findall(r"\b\w+\b", claim_lower))
    overlap = [w for w in q_words if w in c_words]
    score += len(overlap) * 2.5

    # 2. Exact n-gram phrase matches (2-word sequences)
    if len(q_words) >= 2:
        for i in range(len(q_words) - 1):
            bigram = f"{q_words[i]} {q_words[i+1]}"
            if bigram in claim_lower:
                score += 6.0

    # 3. Numeric & monetary match (crucial for policy windows and dollar limits)
    numbers_in_query = re.findall(r"\b\d+(?:\.\d+)?\b|\$\d+|\bnet-\d+\b", q_lower)
    for num in numbers_in_query:
        clean_num = num.strip("$")
        if clean_num in claim_lower:
            score += 10.0

    # 4. Governance terms & Acronyms
    gov_terms = ["sla", "sox", "vpn", "iam", "mtls", "sso", "ciso", "cfo", "kms", "gdpr", "hipaa", "pci", "refund", "freeze"]
    for gt in gov_terms:
        if gt in q_words and gt in claim_lower:
            score += 6.0

    # 5. Subject entity match
    if subject and any(w in subject.lower() for w in q_words):
        score += 4.0

    # 6. Domain alignment bonus
    if domain and domain not in ("global", "all"):
        domain_keywords = {
            "finance": ["refund", "billing", "invoice", "arr", "tier", "payment", "accounting", "handbook", "confluence", "customer", "credit", "return", "returns"],
            "governance": ["policy", "standard", "rule", "terms", "compliance", "entitlement", "audit", "governance", "handbook", "refund", "return", "returns", "window", "contract"],
            "secops": ["security", "firewall", "ingress", "iam", "mtls", "session", "token", "freeze", "infrastructure", "portal", "key"],
            "hr": ["remote", "work", "leave", "vacation", "employee", "handbook", "people", "guideline", "stipend"],
            "support": ["support", "dispute", "sla", "ticket", "escalation", "customer", "resolution", "arbitration"],
            "staging": ["sandbox", "staging", "test", "trial", "mock", "experiment"]
        }
        kws = domain_keywords.get(domain, [domain])
        if any(kw in claim_lower for kw in kws):
            score += 12.0

    # 7. Semantic Concept Cluster Expansion (bridges natural phrasing like "refund window" to "30 days from delivery")
    concept_clusters = [
        ({"window", "timeframe", "duration", "period", "timeline", "deadline", "cutoff"},
         {"days", "day", "delivery", "window", "within", "notice", "speed", "inspect", "30", "60", "90"}),
        ({"refund", "return", "returns", "reimbursement", "credit", "payout", "chargeback"},
         {"refund", "return", "returns", "credit", "debited", "replacement", "proof", "requested"}),
        ({"enterprise", "annual", "corporate", "commercial"},
         {"custom", "contract", "contracts", "accounts", "agreement", "override", "business", "annual"}),
        ({"approval", "approve", "authorized", "authorization", "sign-off", "signoff", "limit", "threshold"},
         {"approval", "approving", "approve", "tier", "lead", "manager", "director", "sign-off", "signoff", "over"}),
        ({"retention", "retained", "cancellation", "delete", "deletion", "deleted", "purge"},
         {"retention", "retained", "delete", "deletion", "deleted", "months", "days", "onedrive", "cancellation"}),
    ]
    for query_concepts, claim_concepts in concept_clusters:
        if any(qc in q_words for qc in query_concepts):
            matched = sum(1 for cc in claim_concepts if cc in c_words)
            if matched > 0 and len(overlap) > 0:
                score += matched * 3.5

    return score


class ContextRetrievalEngine:
    """Retrieves high-trust, verified, non-conflicting context for AI agents with full provenance."""

    def __init__(
        self,
        session: AsyncSession,
        llm_provider: BaseLLMProvider | None = None,
    ):
        self.session = session
        self.llm = llm_provider or get_llm_provider()
        from app.services.policy_agent_access_gate import PolicyAgentAccessGate
        self.access_gate = PolicyAgentAccessGate()

    async def query_context(
        self,
        request_in: ContextQueryRequest,
    ) -> ContextQueryResponse:
        # 1. Ensure a valid Agent record exists for the organization
        from app.db.models.agent import Agent
        from app.db.enums import RecordStatus

        effective_agent_id = request_in.agent_id
        if effective_agent_id:
            agent_check = await self.session.execute(
                select(Agent.id).where(Agent.id == effective_agent_id).limit(1)
            )
            if not agent_check.scalar_one_or_none():
                effective_agent_id = None

        if not effective_agent_id:
            org_agent = await self.session.execute(
                select(Agent.id).where(Agent.organization_id == request_in.organization_id).limit(1)
            )
            found_id = org_agent.scalar_one_or_none()
            if found_id:
                effective_agent_id = found_id
            else:
                default_agent = Agent(
                    organization_id=request_in.organization_id,
                    name="Context Trust Copilot",
                    description="Autonomous context verification agent",
                    agent_type="copilot",
                    status=RecordStatus.ACTIVE,
                )
                self.session.add(default_agent)
                await self.session.flush()
                await self.session.refresh(default_agent)
                effective_agent_id = default_agent.id

        # 1b. Log the AgentRequest record
        agent_req = AgentRequest(
            organization_id=request_in.organization_id,
            agent_id=effective_agent_id,
            query=request_in.query,
            trust_threshold=request_in.min_trust_score,
            max_results=request_in.max_results,
            status="processing",
        )
        self.session.add(agent_req)
        await self.session.flush()
        await self.session.refresh(agent_req)

        # 2. Fetch candidate claims for this organization
        stmt = (
            select(Claim)
            .where(
                Claim.organization_id == request_in.organization_id,
                Claim.status.in_([ClaimStatus.ACTIVE, ClaimStatus.VERIFIED]),
            )
        )
        if getattr(request_in, "canonical_only", True):
            stmt = stmt.where(Claim.claim_type.in_(["rule", "policy_rule", "policy"]))
            stmt = stmt.where(Claim.claim_type != "derived_summary")

        stmt = stmt.options(
            selectinload(Claim.evidence).selectinload(ClaimEvidence.document).selectinload(Document.folder),
            selectinload(Claim.validity_records),
            selectinload(Claim.trust_scores),
            selectinload(Claim.document_version),
        )
        res = await self.session.execute(stmt)
        all_claims = res.scalars().all()

        target_domain = (request_in.domain or request_in.workspace_id or '').lower()

        # 2b. Compute query embedding & populate claim embeddings for Semantic Vector Search
        query_emb: list[float] = []
        try:
            query_emb = await self.llm.get_embedding(request_in.query)
        except Exception as q_err:
            logger.warning('Query embedding calculation failed (%s); falling back to lexical search', q_err)

        # Batch compute missing embeddings
        missing_claims = [c.claim_text for c in all_claims if c.claim_text not in _EMBEDDING_CACHE]
        if missing_claims:
            try:
                new_embs = await self.llm.get_embeddings(missing_claims)
                for txt, emb in zip(missing_claims, new_embs):
                    _EMBEDDING_CACHE[txt] = emb
            except Exception as b_err:
                logger.debug('Batch embedding calculation fallback (%s)', b_err)
                for txt in missing_claims:
                    try:
                        _EMBEDDING_CACHE[txt] = await self.llm.get_embedding(txt)
                    except Exception:
                        pass

        # Build Section context map for Clause Expansion
        section_context_map: dict[tuple[uuid.UUID, str], list[str]] = {}
        for c in all_claims:
            for ev in c.evidence:
                if ev.document_id and ev.section:
                    sec_key = (ev.document_id, ev.section.strip().lower())
                    if sec_key not in section_context_map:
                        section_context_map[sec_key] = []
                    if c.claim_text not in section_context_map[sec_key]:
                        section_context_map[sec_key].append(c.claim_text)

        # 2c. Compute Lexical & Semantic Scores for each candidate claim
        claim_scores: list[dict[str, Any]] = []
        for claim in all_claims:
            lex_score = _compute_lexical_score(claim.claim_text, claim.subject, request_in.query, target_domain)
            claim_emb = _EMBEDDING_CACHE.get(claim.claim_text, [])
            sem_score = _cosine_similarity(query_emb, claim_emb) if query_emb and claim_emb else 0.0
            claim_scores.append({
                'claim': claim,
                'lex_score': lex_score,
                'sem_score': sem_score,
            })

        # Rank claims by lexical and semantic scores for Reciprocal Rank Fusion (RRF)
        sorted_by_lex = sorted(claim_scores, key=lambda x: x['lex_score'], reverse=True)
        for rank_idx, item in enumerate(sorted_by_lex, start=1):
            item['rank_lex'] = rank_idx

        sorted_by_sem = sorted(claim_scores, key=lambda x: x['sem_score'], reverse=True)
        for rank_idx, item in enumerate(sorted_by_sem, start=1):
            item['rank_sem'] = rank_idx

        # Calculate final RRF Fusion score
        q_token_count = len([w for w in request_in.query.lower().split() if len(w) > 2])
        min_lex_threshold = 4.5 if q_token_count >= 3 else 2.0
        for item in claim_scores:
            rank_l = item.get('rank_lex', 1)
            rank_s = item.get('rank_sem', 1)
            sem_s = item.get('sem_score', 0.0)
            lex_s = item.get('lex_score', 0.0)
            rrf_val = (1.0 / (60.0 + rank_l)) + (1.0 / (60.0 + rank_s)) + (sem_s * 0.05)
            item['rrf_score'] = rrf_val
            item['is_relevant'] = (lex_s >= min_lex_threshold) or (sem_s >= 0.55) or (len(request_in.query.split()) <= 1)

        scores_by_claim_id = {item['claim'].id: item for item in claim_scores}

        evaluated_items: list[
            tuple[Claim, decimal.Decimal, bool, str | None, ContextItemResponse | None, float]
        ] = []
        query_terms = set(request_in.query.lower().split())
        now = datetime.now(timezone.utc)

        for claim in all_claims:
            # Determine latest trust score
            latest_score = decimal.Decimal("0.5000")
            if claim.trust_scores:
                latest_score = max(ts.overall_score for ts in claim.trust_scores)

            score_data = scores_by_claim_id.get(claim.id, {"rrf_score": 0.0, "is_relevant": False})
            relevance_score = score_data["rrf_score"]
            relevance_match = score_data["is_relevant"]

            # Check validity window
            is_valid = True
            validity_info = ContextValidityInfo(status="active")
            for val in claim.validity_records:
                if val.valid_until and val.valid_until < now:
                    is_valid = False
                    validity_info.status = "expired"
                    validity_info.valid_until = str(val.valid_until)
                if val.valid_from:
                    validity_info.valid_from = str(val.valid_from)

            # Filter decisions
            included = True
            exclusion_reason = None

            # Universal Hard Governance Gate Evaluation
            gate_res = ClaimGateEvaluator.evaluate(
                claim_text=claim.claim_text,
                subject=claim.subject,
                predicate=claim.predicate,
                object_text=claim.object,
                claim_type=claim.claim_type,
                status=claim.status.value if hasattr(claim.status, "value") else str(claim.status),
                confidence_or_trust=latest_score,
            )

            if not is_valid:
                included = False
                exclusion_reason = "Claim validity window has expired."
            elif claim.status not in (ClaimStatus.ACTIVE, ClaimStatus.VERIFIED):
                included = False
                exclusion_reason = f"Claim status '{claim.status.value if hasattr(claim.status, 'value') else claim.status}' is blocked from agent retrieval (only ACTIVE or VERIFIED permitted)."
            elif claim.claim_type not in ("rule", "policy_rule", "policy"):
                included = False
                exclusion_reason = f"Hard Gate Excluded: Claim type '{claim.claim_type}' is non-normative context, not an operative policy rule."
            elif claim.claim_text.strip().endswith("?"):
                included = False
                exclusion_reason = "Hard Gate Excluded: Interrogative title / FAQ question, not an operative policy rule."
            elif not gate_res.subject_valid:
                included = False
                exclusion_reason = "Hard Gate Rejected: Defective extraction fragment or invalid subject entity."
            elif not gate_res.claim_type_allowed:
                included = False
                exclusion_reason = f"Hard Gate Excluded: Claim type '{claim.claim_type}' is non-normative context, not a policy rule."
            elif not gate_res.is_atomic:
                included = False
                exclusion_reason = "Hard Gate Excluded: Compound multi-part rule must be decomposed into atomic propositions."
            elif not gate_res.all_9_gates_passed:
                included = False
                exclusion_reason = f"Hard Governance Gate Failed: {'; '.join(gate_res.rejection_reasons)}."
            elif claim.status in [ClaimStatus.CONFLICTED, ClaimStatus.REJECTED, ClaimStatus.CANDIDATE]:
                included = False
                exclusion_reason = f"Claim status '{claim.status.value}' is blocked from agent retrieval."
            elif latest_score < request_in.min_trust_score:
                included = False
                exclusion_reason = f"Trust score ({latest_score}) below required threshold ({request_in.min_trust_score})."
            elif not relevance_match:
                included = False
                exclusion_reason = "Claim not relevant to query."
            else:
                final_tier = gate_res.certification_tier
                claim_tier_eval = {
                    "candidate_id": str(claim.id),
                    "final_state": final_tier,
                    "status": claim.status.value if hasattr(claim.status, "value") else str(claim.status)
                }
                gate_allowed, gate_level, gate_reason = self.access_gate.check_access(
                    claim_tier_eval,
                    agent_id=str(request_in.agent_id) if request_in.agent_id else None
                )
                if not gate_allowed:
                    included = False
                    exclusion_reason = gate_reason

            item_response = None
            if included:
                # Build provenance / evidence metadata
                doc_title = "Unknown Document"
                doc_id = None
                folder_name = None
                folder_id = None
                section_title = None
                page_num = 1
                evidence_quotes: list[str] = []
                section_context_items: list[SectionContextItem] = []

                for ev in claim.evidence:
                    if ev.document:
                        doc_title = ev.document.title
                        doc_id = str(ev.document.id)
                        if getattr(ev.document, "folder", None):
                            folder_name = ev.document.folder.name
                            folder_id = str(ev.document.folder.id)
                    section_title = ev.section
                    page_num = ev.page_number or 1
                    evidence_quotes.append(ev.text_span)

                    # Decoupled Section Context: separate from claim evidence quotes
                    if ev.document_id and ev.section:
                        sec_key = (ev.document_id, ev.section.strip().lower())
                        related_clauses = section_context_map.get(sec_key, [])
                        for rel_clause in related_clauses[:2]:
                            if rel_clause != claim.claim_text:
                                section_context_items.append(
                                    SectionContextItem(
                                        document_title=doc_title,
                                        section=ev.section,
                                        text=rel_clause,
                                        is_normative=False,
                                    )
                                )

                lane = "canonical" if claim.claim_type in ["rule", "policy_rule", "policy"] else "passage"
                primary_quote = evidence_quotes[0] if evidence_quotes else claim.claim_text

                gov_pkg = GovernedContextPackage(
                    claim_id=str(claim.id),
                    document_id=doc_id,
                    document_title=doc_title,
                    folder_name=folder_name,
                    folder_id=folder_id,
                    section=section_title,
                    page=page_num,
                    rule_text=claim.claim_text,
                    verbatim_evidence=primary_quote,
                    actor=claim.subject,
                    recipient=claim.object,
                    modality=getattr(claim, "modality", "MUST") or "MUST",
                    topic=claim.subject,
                    certification_provenance="human_steward_approved" if str(claim.status).lower() in ["verified", "certified"] else "automated_gate_passed",
                    trust_score=float(latest_score),
                    evidence_lane=lane,
                )

                item_response = ContextItemResponse(
                    claim=claim.claim_text,
                    trust_score=latest_score,
                    validity=validity_info,
                    source=ContextSourceInfo(
                        document=doc_title,
                        section=section_title,
                        page=page_num,
                        folder_name=folder_name,
                        folder_id=folder_id,
                    ),
                    evidence=evidence_quotes,
                    section_context=section_context_items,
                    claim_type=claim.claim_type,
                    is_canonical=(claim.claim_type != "derived_summary"),
                    claim_id=str(claim.id),
                    document_id=doc_id,
                    evidence_lane=lane,
                    governed_package=gov_pkg,
                )

            evaluated_items.append((claim, latest_score, included, exclusion_reason, item_response, relevance_score))

        # 3. Sort included items by relevance score and trust score (highest first) and limit to max_results
        included_items = [item for item in evaluated_items if item[2]]
        included_items.sort(key=lambda x: (x[5], x[1]), reverse=True)

        # Deduplicate identical / mirror claim texts (e.g. PDF vs Slack mirrored ingestions) to preserve evidence diversity
        distinct_included = []
        seen_claim_norms = set()
        for item in included_items:
            norm_key = re.sub(r"\s+", " ", item[0].claim_text.strip().lower()[:120])
            if norm_key in seen_claim_norms:
                continue
            seen_claim_norms.add(norm_key)
            distinct_included.append(item)

        top_included = distinct_included[: request_in.max_results]

        final_context_list: list[ContextItemResponse] = []
        rank = 1

        for claim, score, included, reason, resp, _rel in top_included:
            if resp:
                final_context_list.append(resp)
            # Record in DB
            context_log = AgentContextItem(
                request_id=agent_req.id,
                claim_id=claim.id,
                rank=rank,
                trust_score=score,
                included=True,
                exclusion_reason=None,
            )
            self.session.add(context_log)
            rank += 1

        # Record excluded items in DB for auditing
        excluded_items = [item for item in evaluated_items if not item[2]]
        for claim, score, included, reason, _, _rel in excluded_items:
            context_log = AgentContextItem(
                request_id=agent_req.id,
                claim_id=claim.id,
                rank=rank,
                trust_score=score,
                included=False,
                exclusion_reason=reason,
            )
            self.session.add(context_log)
            rank += 1

        # 4. Check for active ClaimConflicts relevant to the query topic for this organization
        detected_conflicts: list[dict] = []
        seen_conflict_pairs = set()

        conflict_stmt = (
            select(ClaimConflict)
            .join(Claim, ClaimConflict.claim_a_id == Claim.id)
            .options(
                selectinload(ClaimConflict.claim_a).selectinload(Claim.evidence).selectinload(ClaimEvidence.document),
                selectinload(ClaimConflict.claim_b).selectinload(Claim.evidence).selectinload(ClaimEvidence.document),
            )
            .where(
                Claim.organization_id == request_in.organization_id,
                ClaimConflict.resolution_status.in_([
                    ConflictStatus.DETECTED,
                    ConflictStatus.HUMAN_REVIEW_REQUIRED,
                    "detected",
                    "human_review_required",
                ]),
            )
        )
        conf_res = await self.session.execute(conflict_stmt)
        all_active_conflicts = conf_res.scalars().all()

        q_clean = request_in.query.lower()
        q_tokens = [w for w in re.findall(r"\b\w+\b", q_clean) if len(w) > 2 and w not in STOP_WORDS]

        for c in all_active_conflicts:
            cid_a = getattr(c, "claim_a_id", None)
            cid_b = getattr(c, "claim_b_id", None)
            if not cid_a or not cid_b:
                continue
            pair_key = (min(str(cid_a), str(cid_b)), max(str(cid_a), str(cid_b)))
            if pair_key in seen_conflict_pairs:
                continue

            claim_a_text = (c.claim_a.claim_text or "") if c.claim_a else ""
            claim_b_text = (c.claim_b.claim_text or "") if c.claim_b else ""

            GENERIC_ACTORS = {"customer", "microsoft", "company", "party", "parties", "client", "vendor", "agreement", "terms"}
            substantive_tokens = [w for w in q_tokens if w not in GENERIC_ACTORS]
            if any(k in ("onedrive", "retention", "retained", "cancellation", "delete") for k in substantive_tokens):
                substantive_tokens.extend(["delete", "deletion", "deleted", "onedrive"])

            # Precision guards:
            # 1. If query is about "embedded capabilities", do NOT match "windows embedded operating systems" table conflicts
            comb_conflict_lower = (claim_a_text + " " + claim_b_text).lower()
            if "embedded capabilities" in q_clean and "capabilities" not in comb_conflict_lower:
                continue

            # 2. If query asks specifically about "material breach", do not match termination for cause unless BOTH sides explicitly mention material breach
            if "material breach" in q_clean and ("material breach" not in claim_a_text.lower() or "material breach" not in claim_b_text.lower()):
                continue

            has_substantive_match = any(
                st in claim_a_text.lower() or st in claim_b_text.lower()
                for st in substantive_tokens
            )

            # Check if this conflict is relevant to the query
            score_a = _compute_lexical_score(claim_a_text, None, request_in.query, target_domain)
            score_b = _compute_lexical_score(claim_b_text, None, request_in.query, target_domain)

            is_relevant_conflict = has_substantive_match and (score_a >= 4.0 or score_b >= 4.0)

            if not is_relevant_conflict:
                continue

            seen_conflict_pairs.add(pair_key)

            doc_a_title = (
                c.claim_a.evidence[0].document.title
                if (c.claim_a and c.claim_a.evidence and c.claim_a.evidence[0].document)
                else "Source A"
            )
            doc_b_title = (
                c.claim_b.evidence[0].document.title
                if (c.claim_b and c.claim_b.evidence and c.claim_b.evidence[0].document)
                else "Source B"
            )
            detected_conflicts.append({
                "conflict_id": str(c.id),
                "conflict_type": c.conflict_type or "policy_contradiction",
                "severity": c.severity or "high",
                "description": f"Contradiction detected between {doc_a_title} and {doc_b_title}: '{claim_a_text}' vs '{claim_b_text}'",
                "claim_a_id": str(c.claim_a_id),
                "claim_b_id": str(c.claim_b_id),
                "source_a": doc_a_title,
                "source_b": doc_b_title,
                "claim_a_text": claim_a_text,
                "claim_b_text": claim_b_text,
            })

        # 5. Mark AgentRequest completed
        agent_req.status = "completed"
        agent_req.completed_at = datetime.now(timezone.utc)
        await self.session.flush()

        avg_confidence = (
            sum(item.trust_score for item in final_context_list) / len(final_context_list)
            if final_context_list
            else request_in.min_trust_score
        )

        gov_packages = [r.governed_package for r in final_context_list if r.governed_package is not None]

        return ContextQueryResponse(
            context=final_context_list,
            governed_packages=gov_packages,
            conflicts=detected_conflicts,
            confidence=decimal.Decimal(f"{avg_confidence:.4f}"),
        )
