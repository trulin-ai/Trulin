"""
Response Planner Service for Adaptive Policy Answers.

Determines the optimal answer structure, display depth, grouping dimension,
and required sections before deterministic synthesis begins:
1. Classifies user query into 8 QuestionType categories:
   - LOOKUP (deadline, window, threshold, fee, single metric)
   - INTERPRETATION (meaning, scope of restriction, clause application)
   - COMPARISON (cross-document or cross-tier variance)
   - PROCEDURE (prerequisites, step-by-step checklists)
   - ACTION_ASSESSMENT (permission to execute: ALLOW / BLOCK)
   - CONFLICT (competing pathways: Path A vs Path B)
   - OVERVIEW (broad thematic policy review)
   - UNSUPPORTED (fail-closed abstention when no verified rules exist)
2. Resolves display depth (Brief, Standard, Detailed).
3. Selects grouping strategy (topic, step, criterion, entity, pathway).
4. Determines required section composition without using rigid company-specific templates.
"""

import logging
import re
from typing import Any, Dict, List, Optional

from app.schemas.chat import (
    DisplayDepth,
    QuestionType,
    ResponsePlan,
)

logger = logging.getLogger(__name__)


class ResponsePlanner:
    """Deterministic, evidence-grounded response planner."""

    # Linguistic pattern matchers for query classification
    LOOKUP_PATTERNS = [
        r"\b(?:what is the|how long is the|what are the)\s+(?:notice period|refund window|grace period|retention period|timeframe|deadline|fee|rate|limit|cap|threshold)\b",
        r"\bwhat notice is required\b",
        r"\bhow many (?:days|months|hours|weeks|years|retries)\b",
        r"\bwhat is the (?:dollar|monetary|maximum|minimum)\s+(?:limit|cap|amount|threshold)\b",
        r"\bwhat is the return window\b",
        r"\bhow long (?:do we|is|does)\b",
    ]

    PROCEDURE_PATTERNS = [
        r"\bwhat (?:must|should) (?:a customer|an employee|the user|we|an agent) do (?:before|prior to|to)\b",
        r"\bwhat must happen before\b",
        r"\bwhat are the (?:steps|prerequisites|requirements|conditions) (?:for|to|before)\b",
        r"\bhow do (?:i|we|they) (?:submit|request|transfer|execute|initiate|appeal)\b",
        r"\bprocedure for\b",
        r"\bprerequisites for\b",
    ]

    COMPARISON_PATTERNS = [
        r"\b(?:how do|what is the difference between|compare|differences? between)\b",
        r"\b(?:vs\.?|versus)\b",
        r"\bhow does .* differ from\b",
        r"\bcompare .* (?:and|with|to)\b",
    ]

    OVERVIEW_PATTERNS = [
        r"\b(?:summarize|provide an overview of|give an overview of|overview of)\b",
        r"\bwhat are the (?:main|key|general|overall) (?:rules|terms|policies|provisions)\b",
        r"\bexplain (?:all|the overall|the comprehensive)\b",
    ]

    ACTION_ASSESSMENT_PATTERNS = [
        r"\bcan (?:i|we|an? agent|the user|support|tier\s*2)\b",
        r"\bmay (?:i|we|an? agent|the user)\b",
        r"\b(?:is|are) (?:the agent|an agent|users?|we) allowed to\b",
        r"\bam i allowed to\b",
        r"\bis it (?:allowed|permitted|possible) to\b",
    ]

    @classmethod
    def classify_question_type(
        cls,
        query: str,
        citations: List[Dict[str, Any]],
        has_conflicts: bool = False,
        mode: str = "document_qa",
    ) -> QuestionType:
        """Classifies the user query into one of the 8 canonical QuestionType categories."""
        # 1. Unsupported Check: No citations or zero eligible evidence
        if not citations or len(citations) == 0:
            return QuestionType.UNSUPPORTED

        q_lower = query.lower().strip()

        # Check for explicit irrelevant / unsupported topics
        if any(unsupported_phrase in q_lower for unsupported_phrase in [
            "quantum teleportation", "time travel", "faster than light", "crypto reimbursement"
        ]) and len(citations) == 0:
            return QuestionType.UNSUPPORTED

        # 2. Conflict State: Explicit conflicts surfaced in retrieval
        if has_conflicts:
            return QuestionType.CONFLICT

        # 3. Action Assessment Mode: Explicitly triggered action evaluation
        if mode == "action_evaluation":
            return QuestionType.ACTION_ASSESSMENT

        for pat in cls.ACTION_ASSESSMENT_PATTERNS:
            if re.search(pat, q_lower):
                # If there's an action verb + target (refund, port, wire, approve)
                if any(v in q_lower for v in ["approve", "refund", "open port", "wire", "execute", "override", "bypass"]):
                    return QuestionType.ACTION_ASSESSMENT

        # 4. Procedure Check: Sequence, prerequisites, steps
        for pat in cls.PROCEDURE_PATTERNS:
            if re.search(pat, q_lower):
                return QuestionType.PROCEDURE

        # 5. Comparison Check: Differences, comparing policies or tiers
        for pat in cls.COMPARISON_PATTERNS:
            if re.search(pat, q_lower):
                return QuestionType.COMPARISON

        # 6. Lookup Check: Specific deadlines, windows, thresholds, caps
        for pat in cls.LOOKUP_PATTERNS:
            if re.search(pat, q_lower):
                return QuestionType.LOOKUP

        # 7. Overview Check: Summarize, high-level review
        for pat in cls.OVERVIEW_PATTERNS:
            if re.search(pat, q_lower):
                return QuestionType.OVERVIEW

        # 8. Default: Interpretation (understanding policy meaning, terms, scope)
        return QuestionType.INTERPRETATION

    @classmethod
    def resolve_depth(
        cls,
        question_type: QuestionType,
        requested_depth: Optional[DisplayDepth | str] = None,
        num_citations: int = 1,
    ) -> DisplayDepth:
        """
        Resolves initial display depth based on question type and explicit user preference.
        Depth-Scope Decoupling Invariant: Changing depth never modifies retrieval scope.
        """
        # User preference always takes priority if explicitly set and not AUTO
        if requested_depth:
            depth_str = str(requested_depth).lower()
            if depth_str in (DisplayDepth.BRIEF.value, "brief"):
                return DisplayDepth.BRIEF
            elif depth_str in (DisplayDepth.DETAILED.value, "detailed"):
                return DisplayDepth.DETAILED
            elif depth_str in (DisplayDepth.STANDARD.value, "standard"):
                return DisplayDepth.STANDARD

        # Default heuristic based on question type
        if question_type in (QuestionType.LOOKUP, QuestionType.UNSUPPORTED):
            return DisplayDepth.BRIEF
        elif question_type == QuestionType.OVERVIEW:
            return DisplayDepth.DETAILED
        elif question_type == QuestionType.COMPARISON and num_citations >= 3:
            return DisplayDepth.DETAILED
        else:
            return DisplayDepth.STANDARD

    @classmethod
    def resolve_group_by(cls, question_type: QuestionType) -> str:
        """Determines the organizational grouping dimension for explanation blocks."""
        mapping = {
            QuestionType.LOOKUP: "topic",
            QuestionType.INTERPRETATION: "topic",
            QuestionType.PROCEDURE: "step",
            QuestionType.COMPARISON: "criterion",
            QuestionType.ACTION_ASSESSMENT: "criteria",
            QuestionType.CONFLICT: "pathway",
            QuestionType.OVERVIEW: "topic",
            QuestionType.UNSUPPORTED: "topic",
        }
        return mapping.get(question_type, "topic")

    @classmethod
    def resolve_required_sections(cls, question_type: QuestionType) -> List[str]:
        """Selects only the substantive sections needed for the given question type."""
        mapping = {
            QuestionType.LOOKUP: ["summary", "conditions", "evidence"],
            QuestionType.INTERPRETATION: ["summary", "explanation", "conditions", "evidence"],
            QuestionType.PROCEDURE: ["summary", "prerequisites", "evidence"],
            QuestionType.COMPARISON: ["summary", "comparison", "evidence"],
            QuestionType.ACTION_ASSESSMENT: ["verdict", "requirements", "evidence"],
            QuestionType.CONFLICT: ["summary", "pathways", "escalation", "evidence"],
            QuestionType.OVERVIEW: ["summary", "thematic_blocks", "evidence"],
            QuestionType.UNSUPPORTED: ["abstention", "scope"],
        }
        return mapping.get(question_type, ["summary", "explanation", "evidence"])

    @classmethod
    def detect_unanswered_parts(cls, query: str, citations: List[Dict[str, Any]]) -> List[str]:
        """Identifies multi-part query clauses that lack supporting evidence in retrieved claims."""
        unanswered = []
        q_lower = query.lower()

        # Multi-part connector detection (e.g. "and what about X?", "as well as Y?")
        split_clauses = re.split(r"\b(?:and what about|as well as|and also|what is the policy for)\b", q_lower)
        if len(split_clauses) > 1:
            all_evidence_text = " ".join(
                c.get("claim_text", "") + " " + c.get("evidence", "") for c in citations
            ).lower()

            for clause in split_clauses[1:]:
                clause_clean = clause.strip(" ?.,")
                if len(clause_clean) > 8:
                    # Check if key tokens in the sub-clause appear in evidence
                    tokens = [t for t in clause_clean.split() if len(t) > 3 and t not in ("what", "policy", "about", "does", "have")]
                    if tokens and not any(t in all_evidence_text for t in tokens):
                        unanswered.append(f"Policy coverage regarding '{clause_clean}' was not found in active scope.")

        return unanswered

    @classmethod
    def plan_response(
        cls,
        query: str,
        citations: List[Dict[str, Any]],
        has_conflicts: bool = False,
        requested_depth: Optional[str] = None,
        mode: str = "document_qa",
    ) -> ResponsePlan:
        """
        Orchestrates planning for an incoming query, generating a typed ResponsePlan.
        """
        q_type = cls.classify_question_type(
            query=query,
            citations=citations,
            has_conflicts=has_conflicts,
            mode=mode,
        )

        resolved_depth = cls.resolve_depth(
            question_type=q_type,
            requested_depth=requested_depth,
            num_citations=len(citations),
        )

        group_by = cls.resolve_group_by(q_type)
        required_sections = cls.resolve_required_sections(q_type)
        unanswered = cls.detect_unanswered_parts(query, citations)

        req_depth_enum = DisplayDepth.AUTO
        if requested_depth:
            try:
                req_depth_enum = DisplayDepth(requested_depth.lower())
            except ValueError:
                req_depth_enum = DisplayDepth.AUTO

        return ResponsePlan(
            question_type=q_type,
            requested_depth=req_depth_enum,
            resolved_depth=resolved_depth,
            scope_status="resolved" if citations else "unsupported",
            group_by=group_by,
            required_sections=required_sections,
            unanswered_parts=unanswered,
        )
