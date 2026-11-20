import decimal
import logging
import re
import uuid
from typing import Any
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.repositories.chat_repository import ChatRepository
from app.decision_engine.evaluator import DecisionEvaluator
from app.llm.factory import get_llm_provider
from app.retrieval.engine import ContextRetrievalEngine
from app.schemas.context import ContextQueryRequest
from app.schemas.decision import DecisionActor, DecisionContextItem, DecisionEvaluateRequest
from app.services.answer_verifier import AnswerVerifier
from app.services.context_resolver import ConversationContextResolver

logger = logging.getLogger(__name__)


class ChatService:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.repo = ChatRepository(session)
        self.llm = get_llm_provider()
        self.resolver = ConversationContextResolver(self.llm)

    @staticmethod
    def generate_smart_title(query: str, fallback: str = "New Conversation") -> str:
        if not query or not query.strip():
            return fallback

        import re
        text = query.strip()
        text = re.sub(r"\[Attached Document:[^\]]+\]", "", text, flags=re.IGNORECASE)
        text = re.sub(r"```[\s\S]*?```", "", text)
        text = text.strip()

        prefixes = [
            r"^(?:can\s+(?:you|we|i)\s+(?:please\s+)?(?:tell\s+me\s+about|explain|check|verify|give\s+me|show\s+me|help\s+me\s+with))\s*",
            r"^(?:could\s+(?:you|we|i)\s+(?:please\s+)?(?:tell\s+me\s+about|explain|check|verify|give\s+me|show\s+me))\s*",
            r"^(?:what\s+(?:is|are|does|do)\s+(?:the|our|your)?\s*(?:policy|rules?|guidelines?|standard|requirements?|procedure)\s+(?:for|about|on|regarding)?)\s*",
            r"^(?:what\s+(?:is|are|does|do)\s+(?:the|our|your)?)\s*",
            r"^(?:tell\s+me\s+(?:about|regarding))\s*",
            r"^(?:explain\s+(?:the|our|how)?)\s*",
            r"^(?:how\s+(?:do|can|does|should)\s+(?:we|i|a\s+user)?)\s*",
            r"^(?:is\s+it\s+(?:allowed|permitted|possible)\s+to)\s*",
            r"^(?:am\s+i\s+(?:allowed|permitted)\s+to)\s*",
            r"^(?:can\s+(?:i|we|an\s+agent)\s+)\s*",
            r"^(?:please\s+)\s*",
            r"^(?:i\s+(?:want|need|would\s+like)\s+to\s+(?:know|check|understand)\s+(?:about)?)\s*",
        ]
        cleaned = text
        for pat in prefixes:
            cleaned = re.sub(pat, "", cleaned, flags=re.IGNORECASE).strip()

        cleaned = re.sub(r"^[^\w]+", "", cleaned)
        cleaned = re.sub(r"[?!.,;:\"']+$", "", cleaned).strip()

        if not cleaned:
            cleaned = text[:36].strip()

        words = cleaned.split()
        if len(words) > 6:
            cleaned = " ".join(words[:6])

        words = cleaned.split()
        minor_words = {"a", "an", "the", "and", "but", "or", "for", "nor", "on", "at", "to", "by", "in", "of"}
        titled_words = []
        for i, w in enumerate(words):
            if i == 0 or w.lower() not in minor_words or i == len(words) - 1:
                titled_words.append(w.capitalize() if not w.isupper() else w)
            else:
                titled_words.append(w.lower())
        title = " ".join(titled_words)

        if len(title) > 48:
            title = title[:45].rstrip() + "..."

        return title or fallback

    async def list_sessions(
        self,
        organization_id: uuid.UUID,
        user_id: uuid.UUID | None = None,
        workspace_id: str | None = None,
        limit: int = 50,
    ) -> list[dict[str, Any]]:
        sessions = await self.repo.list_sessions(organization_id, user_id, workspace_id, limit)
        results = []
        needs_commit = False
        for s in sessions:
            title_str = (s.title or "").strip()
            is_generic = (
                not title_str
                or title_str in ("New Conversation", "Untitled Conversation")
                or title_str.endswith("New Conversation")
                or title_str.startswith("[")
            )
            if is_generic and s.messages:
                first_user_msg = next((m for m in s.messages if m.role == "user" and m.content), None)
                if first_user_msg:
                    smart = self.generate_smart_title(first_user_msg.content)
                    if smart and smart != "New Conversation":
                        s.title = smart
                        needs_commit = True
            results.append(s.to_dict())
        if needs_commit:
            try:
                await self.session.commit()
            except Exception:
                pass
        return results

    async def get_session(self, session_id: uuid.UUID) -> dict[str, Any] | None:
        s = await self.repo.get_session(session_id)
        if not s:
            return None
        res = s.to_dict()
        res["messages"] = [m.to_dict() for m in (s.messages or [])]
        return res

    async def create_session(
        self,
        organization_id: uuid.UUID,
        user_id: uuid.UUID | None,
        user_name: str,
        user_role: str,
        title: str = "New Conversation",
        workspace_id: str | None = "all",
        domain: str | None = "global",
    ) -> dict[str, Any]:
        s = await self.repo.create_session(
            organization_id=organization_id,
            user_id=user_id,
            user_name=user_name,
            user_role=user_role,
            title=title,
            workspace_id=workspace_id or "all",
            domain=domain or "global",
        )
        await self.session.commit()
        return s.to_dict()

    async def update_session_title(self, session_id: uuid.UUID, title: str) -> dict[str, Any] | None:
        session_obj = await self.repo.update_session_title(session_id, title)
        if not session_obj:
            return None
        await self.session.commit()
        return session_obj.to_dict()

    async def delete_session(self, session_id: uuid.UUID) -> bool:
        success = await self.repo.delete_session(session_id)
        await self.session.commit()
        return success

    async def process_user_message(
        self,
        session_id: uuid.UUID,
        organization_id: uuid.UUID,
        content: str,
        user_id: uuid.UUID | None = None,
        user_name: str = "User",
        user_role: str = "developer",
        workspace_id: str | None = None,
        domain: str | None = None,
    ) -> dict[str, Any]:
        # 1. Fetch existing session & conversation history
        session_obj = await self.repo.get_session(session_id)
        recent_history: list[dict[str, str]] = []
        if session_obj and session_obj.messages:
            for m in session_obj.messages[-6:]:
                if m.role in ("user", "assistant") and m.content:
                    recent_history.append({"role": m.role, "content": m.content})

        # 2. Store new user message in DB
        user_msg = await self.repo.add_message(
            session_id=session_id,
            role="user",
            content=content,
            metadata_json={"author": user_name, "role": user_role, "workspace_id": workspace_id, "domain": domain},
        )

        effective_domain = domain or (session_obj.domain if session_obj else None) or "global"
        effective_workspace = workspace_id or (session_obj.workspace_id if session_obj else None) or "all"

        # 3. Detect operational mode (Mode A: Document Q&A vs Mode B: Action Evaluation)
        q_lower = content.lower().strip()

        # Questions asking for policy terms, explanations, or definitions are strictly Document Q&A
        is_explicit_document_inquiry = q_lower.startswith((
            "what is ", "what are ", "what does ", "what must ", "how long ", "what notice ",
            "does this ", "explain ", "describe ", "which ", "who "
        ))

        is_action_eval = False
        if not is_explicit_document_inquiry:
            action_eval_patterns = [
                r"\bcan\s+(?:i|we|the\s+agent|an\s+agent|a\s+user|support|tier\s*2)\b",
                r"\bmay\s+(?:i|we|the\s+agent|an\s+agent|a\s+user|support)\b",
                r"\b(?:is|are)\s+(?:the\s+agent|an\s+agent|users?)\s+allowed\s+to\b",
                r"\bam\s+i\s+allowed\s+to\b",
                r"\b(?:approve|issue\s+refund|grant\s+access|override|open\s+port|bypass|execute|wire\s+transfer)\b",
            ]
            has_action_actor = any(re.search(p, q_lower) for p in action_eval_patterns)
            has_action_verb = bool(re.search(r"\b(?:can|may|allowed|approve|authoriz\w*|issue|wire|disburse|bypass)\b", q_lower))
            has_action_target = bool(re.search(r"\b(?:refund|credit|firewall|port\s*22|bypass|wire\s*transfer|wire|payment|disbursement|sign-off)\b", q_lower))
            is_action_eval = has_action_actor or (has_action_verb and has_action_target)

        mode = "action_evaluation" if is_action_eval else "document_qa"

        # 4. Resolve conversational query for multi-turn context and query Context Retrieval Engine
        resolved_query = await self.resolver.resolve_query(content, recent_history)

        retrieval_engine = ContextRetrievalEngine(self.session, self.llm)
        default_agent_id = uuid.UUID("88888888-8888-8888-8888-888888888888")
        context_req = ContextQueryRequest(
            organization_id=organization_id,
            agent_id=default_agent_id,
            query=resolved_query,
            min_trust_score=decimal.Decimal("0.50"),
            max_results=8,
            domain=effective_domain,
            workspace_id=effective_workspace,
        )
        context_res = await retrieval_engine.query_context(context_req)

        # 5. Extract retrieved context, conflicts, and trust scores
        included_claims = context_res.context
        has_conflicts = len(context_res.conflicts) > 0

        avg_trust = (
            sum(float(item.trust_score) for item in included_claims) / len(included_claims)
            if included_claims else 0.50
        )

        # 6. Formulate citations with full provenance (deduplicating identical claim statements)
        citations = []
        seen_claims = set()
        for idx, item in enumerate(included_claims):
            norm_text = item.claim.strip().lower()
            if norm_text in seen_claims:
                continue
            seen_claims.add(norm_text)
            citations.append({
                "source_index": idx + 1,
                "claim_id": item.claim_id,
                "document_id": item.document_id,
                "folder_name": getattr(item.source, "folder_name", None) or (item.governed_package.folder_name if item.governed_package else None) or "Enterprise Policies",
                "folder_id": getattr(item.source, "folder_id", None) or (item.governed_package.folder_id if item.governed_package else None),
                "evidence_lane": getattr(item, "evidence_lane", "canonical"),
                "claim_text": item.claim,
                "trust_score": float(item.trust_score),
                "source_title": item.source.document if item.source else "Knowledge Base",
                "section": item.source.section if item.source else None,
                "page": item.source.page if item.source else None,
                "validity": item.validity.status if item.validity else "active",
                "evidence": item.evidence,
                "subject": item.governed_package.actor if item.governed_package else getattr(item, "subject", "Customer"),
                "predicate": getattr(item, "predicate", "governs"),
                "object": item.governed_package.recipient if item.governed_package else getattr(item, "object", item.claim),
                "modality": item.governed_package.modality if item.governed_package else "MUST",
                "certification_tier": getattr(item.governed_package, "certification_provenance", "AUTOMATED_CERTIFIED"),
                "section_context": [
                    sc.model_dump() if hasattr(sc, "model_dump") else sc
                    for sc in getattr(item, "section_context", [])
                ],
            })

        warnings = []
        if has_conflicts:
            for conf in context_res.conflicts:
                desc = conf.get("description") or "Contradictory evidence detected between active sources."
                warnings.append(f"Disputed evidence: {desc}")

        # 7. Execute according to Mode
        audit_id = None
        risk_level = None
        answer_status = None

        if mode == "action_evaluation":
            # Mode B: Evaluate Proposed Action via DecisionEvaluator
            decision_contexts = [
                DecisionContextItem(
                    claim=item.claim,
                    source=item.source.document if item.source else "Knowledge Base",
                    authority_level=int(float(item.trust_score) * 100),
                    scope=effective_domain,
                )
                for item in included_claims
            ]
            evaluator = DecisionEvaluator(llm_provider=self.llm, session=self.session)
            eval_req = DecisionEvaluateRequest(
                decision=content,
                actor=DecisionActor(id=str(user_id or "user-default"), role=user_role),
                context=decision_contexts,
                organization_id=organization_id,
            )
            eval_res = await evaluator.evaluate(eval_req, session=self.session)

            decision = eval_res.decision  # ALLOW, BLOCK, REVIEW, CLARIFY
            risk_level = eval_res.risk    # LOW, MEDIUM, HIGH
            audit_id = eval_res.audit_id
            confidence = round(max(0.70, avg_trust), 2)
            answer_status = "EVALUATED"

            action_eval_data = {
                "verdict": decision,
                "reason": eval_res.reasons[0] if eval_res.reasons else "Evaluated against enterprise baseline policies.",
                "matched_claims": [c.claim for c in decision_contexts],
                "missing_requirements": [r for r in eval_res.reasons if any(k in r.lower() for k in ["missing", "not authorized", "insufficient", "approval", "required", "blocked", "role"])],
                "audit_id": audit_id,
                "suggested_action": eval_res.suggested_action,
                "risk_level": risk_level,
            }

            # Format authoritative decision report
            bullet_reasons = "\n".join(f"- {r}" for r in eval_res.reasons) if eval_res.reasons else "- Evaluated against enterprise baseline policies."
            next_action_str = f"\n\n**Recommended Next Action:** {eval_res.suggested_action}" if eval_res.suggested_action else ""
            synthesized_answer = (
                f"### 🛡️ Decision Governance Verdict: **{decision}**\n\n"
                f"**Evaluated Action:** {content}\n\n"
                f"**Policy Findings & Entitlements:**\n{bullet_reasons}"
                f"{next_action_str}\n\n"
                f"🔒 **Governance Audit ID:** `{audit_id}` • **Risk Assessment:** {risk_level}"
            )
        else:
            # Mode A: Document Q&A Synthesis with typed PolicyAnswerContract
            from app.services.policy_answer_synthesizer import PolicyAnswerSynthesizer
            from app.services.policy_wording_refiner import PolicyWordingRefiner

            structured_contract = PolicyAnswerSynthesizer.synthesize_structured(
                query=content,
                citations=citations,
                has_conflicts=has_conflicts,
                conflicts_data=context_res.conflicts,
                warnings=warnings,
                history=recent_history,
                workspace=effective_workspace,
            )
            structured_contract, synthesized_answer = await PolicyWordingRefiner.refine_contract(
                contract=structured_contract,
                citations=citations,
                has_conflicts=has_conflicts,
                llm_provider=self.llm,
            )
            answer_status = structured_contract.verification_status

            if answer_status == "NO_VERIFIED_RULE":
                decision = "CLARIFY"
                confidence = 0.50
            elif answer_status == "DISPUTED":
                decision = "REVIEW"
                confidence = round(max(0.65, avg_trust * 0.85), 2)
            elif answer_status == "VERIFIED":
                decision = "ALLOW"
                confidence = round(min(0.99, max(0.85, avg_trust)), 2)
            else:
                decision = "REVIEW"
                confidence = round(avg_trust, 2)

        # 7. Verify synthesized answer against retrieved citations and numerical assertions
        verification_result = AnswerVerifier.verify(
            synthesized_answer=synthesized_answer,
            citations=citations,
            has_conflicts=has_conflicts,
            mode=mode,
        )

        if not verification_result.is_verified:
            if verification_result.verification_status == "CITATION_MISMATCH":
                if mode == "document_qa":
                    answer_status = "PARTIAL"
                    confidence = min(confidence, 0.60)
            elif verification_result.verification_status == "PARTIALLY_GROUNDED":
                if answer_status == "ANSWERED":
                    answer_status = "PARTIAL"
                    confidence = min(confidence, 0.70)

        if verification_result.hallucination_warnings:
            for hw in verification_result.hallucination_warnings:
                if hw not in warnings:
                    warnings.append(hw)

        metadata_json = {
            "mode": mode,
            "resolved_query": resolved_query if resolved_query != content else None,
            "answer_status": answer_status,
            "decision": decision,
            "risk_level": risk_level,
            "audit_id": audit_id,
            "confidence": confidence,
            "trust_score": round(avg_trust, 2),
            "citations": citations,
            "warnings": warnings,
            "has_conflicts": has_conflicts,
            "conflicts": context_res.conflicts,
            "total_evaluated_claims": len(context_res.context),
            "verification": verification_result.to_dict(),
            "structured_answer": structured_contract.model_dump() if "structured_contract" in locals() else None,
            "action_evaluation": action_eval_data if "action_eval_data" in locals() else None,
        }

        # 8. Store assistant message in DB
        assistant_msg = await self.repo.add_message(
            session_id=session_id,
            role="assistant",
            content=synthesized_answer,
            metadata_json=metadata_json,
        )

        # 9. Auto-assign smart title if current title is generic or blank
        current_title = (session_obj.title or "").strip() if session_obj else ""
        is_generic_title = (
            not current_title
            or current_title in ("New Conversation", "Untitled Conversation")
            or current_title.endswith("New Conversation")
            or current_title.startswith("[")
        )
        if is_generic_title and session_obj:
            smart_title = self.generate_smart_title(content)
            if smart_title and smart_title != "New Conversation":
                session_obj.title = smart_title
                current_title = smart_title

        await self.session.commit()

        return {
            "session_id": str(session_id),
            "session_title": current_title,
            "user_message": user_msg.to_dict(),
            "assistant_message": assistant_msg.to_dict(),
        }
