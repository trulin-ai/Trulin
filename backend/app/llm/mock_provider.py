import hashlib
import math
import re
from typing import Sequence

from app.llm.base import BaseLLMProvider
from app.llm.schemas import (
    ClaimExtractionResult,
    ContradictionResult,
    ExtractedClaim,
)


class MockLLMProvider(BaseLLMProvider):
    """Deterministic Mock LLM Provider for offline development and testing with zero API keys/costs."""

    def __init__(self, embedding_dim: int = 1536):
        self.embedding_dim = embedding_dim

    async def extract_claims(
        self,
        document_title: str,
        section_title: str,
        section_content: str,
    ) -> ClaimExtractionResult:
        claims: list[ExtractedClaim] = []
        if not section_content or not section_content.strip():
            return ClaimExtractionResult(
                claims=[],
                extraction_model="mock-v2",
                extraction_method="mock_rule_extractor",
            )

        from app.normalization.normalizer import DocumentNormalizer

        # 1. Linearize tables in section content so table rules survive grammar gates
        cleaned_content = DocumentNormalizer.linearize_table_content(section_content.strip())

        # 2. Structure-aware sentence & bullet segmentation (protects decimal clauses 3.3., versions, etc.)
        raw_sentences = DocumentNormalizer.structure_aware_segmentation(cleaned_content)
        
        # 3. Candidate clause decomposition (split compound clauses: ';', ' and must ', ' and can ')
        candidate_clauses = []
        for sentence in raw_sentences:
            s = sentence.strip().lstrip("-*• ")
            if not s or len(s) < 8:
                continue
            # Split on semicolons or compound coordination if sentence is long
            if ";" in s and len(s) > 50:
                for sub in s.split(";"):
                    if sub.strip():
                        candidate_clauses.append(sub.strip())
            elif " and must " in s:
                parts = s.split(" and must ")
                candidate_clauses.append(parts[0].strip())
                candidate_clauses.append("must " + parts[1].strip())
            elif " and can " in s:
                parts = s.split(" and can ")
                candidate_clauses.append(parts[0].strip())
                candidate_clauses.append("can " + parts[1].strip())
            else:
                candidate_clauses.append(s)

        # Qualified anchor for entities
        doc_clean = document_title.strip()
        sec_clean = section_title.strip() if section_title and section_title != "General" else ""
        anchor = f"{doc_clean}: {sec_clean}" if (sec_clean and sec_clean.lower() not in doc_clean.lower()) else (sec_clean or doc_clean)

        # Propositional Gatekeeper definitions
        TOC_LINE_RE = re.compile(r"^[0-9.]*\s*[A-Za-z\s&,/-]{3,}\s+\d+(?:\s+[0-9.]+)?$")
        DOT_LEADER_RE = re.compile(r"\.{2,}\s*\d+")
        PREDICATE_TOKENS = {
            "is", "are", "was", "were", "be", "been", "being",
            "must", "shall", "can", "may", "will", "would", "should", "cannot", "could",
            "requires", "required", "require", "requiring",
            "applies", "applied", "apply", "applying",
            "deducted", "deduct", "deducts", "deducting",
            "adjusted", "adjust", "adjusts", "adjusting",
            "recovered", "recover", "recovers", "recovering",
            "eligible", "entitled", "prohibited", "allowed", "permitted",
            "serves", "serve", "serving", "served",
            "submits", "submit", "submitting", "submitted",
            "provides", "provide", "providing", "provided",
            "represents", "represent", "representing", "represented",
            "governs", "govern", "governing", "governed",
            "includes", "include", "including", "included",
            "excludes", "exclude", "excluding", "excluded",
            "terminates", "terminate", "terminating", "terminated",
            "resigns", "resign", "resigning", "resigned",
            "approves", "approve", "approving", "approved",
            "reimburses", "reimburse", "reimbursing", "reimbursed",
            "receives", "receive", "receiving", "received",
            "grants", "grant", "granting", "granted",
            "waives", "waive", "waiving", "waived",
            "contains", "contain", "containing", "contained",
            "has", "have", "had", "having",
            "payable", "specifies", "stipulates",
        }

        for s in candidate_clauses:
            if not s or len(s) < 8:
                continue

            # Stage 2 TOC/Fragment Gatekeeper: Reject dangling page numbers and dot leaders
            if DOT_LEADER_RE.search(s) or TOC_LINE_RE.match(s):
                continue

            # Stage 3 Propositional Gatekeeper: Require finite predicate, copula, modal, or linearized table rule
            is_table_rule = s.lower().startswith("policy rule:")
            words = set(re.findall(r"\b[a-z]+\b", s.lower()))
            has_predicate = bool(words & PREDICATE_TOKENS)

            if not is_table_rule and not has_predicate:
                # Reject non-assertive headers, fragments, or index entries
                continue

            # Skip code, raw json, or synthetic dataset boilerplate
            if s.startswith("{") or s.startswith("[") or '"connectors":' in s or '"documents":' in s or "synthetic" in s.lower():
                continue

            if len(s) > 300:
                s = s[:300].rsplit(" ", 1)[0] + "."

            # Modality detection
            s_lower = s.lower()
            if any(k in s_lower for k in ["cannot", "must not", "prohibited", "never", "not permitted"]):
                modality = "CANNOT"
            elif any(k in s_lower for k in ["must", "required", "shall", "mandatory", "strictly"]):
                modality = "MUST"
            elif any(k in s_lower for k in ["can", "may", "permitted", "allowed", "eligible"]):
                modality = "CAN"
            else:
                modality = "IS"

            # Numeric & Unit extraction (e.g. 14 days, 30 days, 99.9%, $500)
            numeric_val = None
            numeric_unit = None
            num_match = re.search(r"(\d+(?:\.\d+)?)\s*(days?|hours?|months?|years?|weeks?|%|percent|usd|\$|gb|mb|ms|seconds?)(?:\b|[^\w]|$)", s_lower)
            if num_match:
                try:
                    numeric_val = float(num_match.group(1))
                    numeric_unit = num_match.group(2).replace("$", "USD").replace("percent", "%")
                except ValueError:
                    pass

            # S-P-O breakdown with entity anchoring
            subject = anchor
            predicate = "specifies"
            obj = s

            # Pattern matches for common policy / statement structures
            for pred_word in [" receive ", " receives ", " are granted ", " is granted ", " can ", " must ", " is ", " requires "]:
                if pred_word in s:
                    parts = s.split(pred_word, 1)
                    sub_cand = parts[0].strip()
                    # Resolve dangling pronouns
                    if sub_cand.lower() in ["they", "it", "these", "this", "employees", "users", "all users"] and anchor:
                        subject = f"{anchor} ({sub_cand})"
                    elif len(sub_cand) > 2:
                        subject = sub_cand
                    predicate = pred_word.strip()
                    obj = parts[1].strip()
                    break

            claim_type_val = "policy"
            if any(w in section_title.lower() or w in document_title.lower() or w in s_lower for w in ("case study", "case studies", "sample case", "20.2")):
                claim_type_val = "EXAMPLE"
            elif any(w in section_title.lower() or w in s_lower for w in ("contact", "support channel", "phone", "email", "support hours")):
                claim_type_val = "CONTACT_INFORMATION"
            elif any(w in section_title.lower() or w in s_lower for w in ("summary", "overview", "executive summary")):
                claim_type_val = "SUMMARY"
            elif ("policy" in document_title.lower() or "leave" in s_lower or "refund" in s_lower or "allowance" in s_lower):
                claim_type_val = "policy"
            else:
                claim_type_val = "statement"

            claim = ExtractedClaim(
                claim_text=s,
                subject=subject[:250],
                predicate=predicate[:250],
                object=obj,
                claim_type=claim_type_val,
                modality=modality,
                numeric_value=numeric_val,
                numeric_unit=numeric_unit,
                scope=anchor if anchor else None,
                confidence=0.95,
                evidence_text_span=s,
            )
            claims.append(claim)

        return ClaimExtractionResult(
            claims=claims,
            extraction_model="mock-rule-extractor-v2",
            extraction_method="mock_atomic_extractor",
        )

    async def get_embedding(self, text: str) -> list[float]:
        """Generate a deterministic 1536-dim unit vector based on text token hashing."""
        vector = [0.0] * self.embedding_dim
        words = re.findall(r"\w+", text.lower())
        if not words:
            vector[0] = 1.0
            return vector

        for word in words:
            # Map word hash into dimension indices
            h = int(hashlib.md5(word.encode("utf-8")).hexdigest(), 16)
            idx = h % self.embedding_dim
            vector[idx] += 1.0

        # Normalize to unit length (L2 norm)
        norm = math.sqrt(sum(v * v for v in vector))
        if norm > 0:
            vector = [v / norm for v in vector]

        return vector

    async def get_embeddings(self, texts: Sequence[str]) -> list[list[float]]:
        return [await self.get_embedding(t) for t in texts]

    async def evaluate_contradiction(
        self,
        claim_a_text: str,
        claim_b_text: str,
    ) -> ContradictionResult:
        """Context-aware contradiction detector between two claims."""
        a_lower = claim_a_text.lower()
        b_lower = claim_b_text.lower()

        # Comprehensive stopwords + document structural noise
        stopwords = {
            "a", "about", "above", "after", "again", "against", "all", "am", "an", "and",
            "any", "are", "aren't", "as", "at", "be", "because", "been", "before", "being",
            "below", "between", "both", "but", "by", "can", "can't", "cannot", "could",
            "couldn't", "did", "didn't", "do", "does", "doesn't", "doing", "don't", "down",
            "during", "each", "few", "for", "from", "further", "had", "hadn't", "has",
            "hasn't", "have", "haven't", "having", "he", "he'd", "he'll", "he's", "her",
            "here", "here's", "hers", "herself", "him", "himself", "his", "how", "how's",
            "i", "i'd", "i'll", "i'm", "i've", "if", "in", "into", "is", "isn't", "it",
            "it's", "its", "itself", "let's", "me", "more", "most", "mustn't", "my",
            "myself", "no", "nor", "not", "of", "off", "on", "once", "only", "or", "other",
            "ought", "our", "ours", "ourselves", "out", "over", "own", "same", "shan't",
            "she", "she'd", "she'll", "she's", "should", "shouldn't", "so", "some", "such",
            "than", "that", "that's", "the", "their", "theirs", "them", "themselves",
            "then", "there", "there's", "these", "they", "they'd", "they'll", "they're",
            "they've", "this", "those", "through", "to", "too", "under", "until", "up",
            "very", "was", "wasn't", "we", "we'd", "we'll", "we're", "we've", "were",
            "weren't", "what", "what's", "when", "when's", "where", "where's", "which",
            "while", "who", "who's", "whom", "why", "why's", "with", "won't", "would",
            "wouldn't", "you", "you'd", "you'll", "you're", "you've", "your", "yours",
            "page", "section", "document", "policy", "requirement", "standard", "rule",
            "item", "clause", "specified", "specifies", "accordance", "following", "general",
            "total", "part", "details", "described", "provides", "including", "also", "per",
            "one", "two", "three", "four", "five", "first", "second", "third", "must", "may"
        }

        # Tokenize meaningful content words (length >= 3)
        words_a = {re.sub(r"s$", "", w) for w in re.findall(r"[a-z]{3,}", a_lower)} - stopwords
        words_b = {re.sub(r"s$", "", w) for w in re.findall(r"[a-z]{3,}", b_lower)} - stopwords
        meaningful_common_words = words_a.intersection(words_b)

        # Check for structural / document governance headers
        header_patterns = r"\b(?:document\s*id|version\s*:\s*\d+|authority\s*:\s*\d+|classification\s*:|synthetic\s*enterprise\s*dataset|bilingual\s*policy\s*style|section\s*purpose\s*:|page\s*\d+)\b"
        is_header_a = bool(re.search(header_patterns, a_lower)) and not any(w in a_lower for w in ["must not", "prohibited", "forbidden", "cannot"])
        is_header_b = bool(re.search(header_patterns, b_lower)) and not any(w in b_lower for w in ["must not", "prohibited", "forbidden", "cannot"])

        # Strip technical protocol standards, metadata tags, and page numbers from numeric checks
        meta_strip = r"\b(?:aes[-_]?\d+|tls\s*\d+(?:\.\d+)?|sha[-_]?\d+|oauth\s*\d+(?:\.\d+)?|iso\s*\d+|soc\s*\d+|http[s]?\s*/?\s*\d+(?:\.\d+)?|version\s*[:=]?\s*\d+(?:\.\d+)?|authority\s*[:=]?\s*\d+|chapter\s*[:=]?\s*\d+|page\s*[:=]?\s*\d+|rf-\d+-\d+|ssfa-\d+|control\s*rule\s*[:=]?\s*\d+(?:\.\d+)*)\b"
        clean_a = re.sub(meta_strip, "", a_lower)
        clean_b = re.sub(meta_strip, "", b_lower)

        # Check for numeric metrics in both claims
        nums_a = set(re.findall(r"\b\d+(?:[.,]\d+)?\b", clean_a))
        nums_b = set(re.findall(r"\b\d+(?:[.,]\d+)?\b", clean_b))

        # If claims are identical after stripping metadata, they cannot contradict
        if " ".join(clean_a.split()) == " ".join(clean_b.split()):
            return ContradictionResult(
                is_contradiction=False,
                conflict_type="compatible",
                severity="low",
                confidence=0.95,
                reasoning="Claims have identical content and are fully consistent.",
            )

        # Check for complementary segregation-of-duties or self-approval patterns
        is_segregation_a = "own transaction" in a_lower or "segregation of duties" in a_lower or "self-approv" in a_lower
        is_segregation_b = "own transaction" in b_lower or "segregation of duties" in b_lower or "self-approv" in b_lower
        is_complementary_approval = (is_segregation_a or is_segregation_b) and ("approval" in a_lower or "approv" in a_lower) and ("approval" in b_lower or "approv" in b_lower)

        # Opposing directive pairs
        direct_opposing_pairs = [
            ("allow", "prohibit"),
            ("allowed", "prohibited"),
            ("permitted", "forbidden"),
            ("required", "optional"),
            ("mandatory", "voluntary"),
            ("enabled", "disabled"),
            ("on-site", "remote"),
            ("onsite", "remote"),
        ]

        has_direct_opposing = any(
            (p[0] in a_lower and p[1] in b_lower) or (p[1] in a_lower and p[0] in b_lower)
            for p in direct_opposing_pairs
        )

        # Modal verbs (must vs must not, can vs cannot) require matching predicate action verb
        has_modal_opposing = False
        if not is_complementary_approval:
            # Check 'must' vs 'must not'
            if ("must not" in a_lower and re.search(r"\bmust\s+(?!not\b)(\w+)", b_lower)) or \
               ("must not" in b_lower and re.search(r"\bmust\s+(?!not\b)(\w+)", a_lower)):
                verb_must = re.findall(r"\bmust\s+(?!not\b)([a-z]{3,})", a_lower if "must not" in b_lower else b_lower)
                verb_must_not = re.findall(r"\bmust\s+not\s+([a-z]{3,})", b_lower if "must not" in b_lower else a_lower)
                if verb_must and verb_must_not and set(verb_must).intersection(set(verb_must_not)):
                    has_modal_opposing = True

            # Check 'can' vs 'cannot'
            elif ("cannot" in a_lower and re.search(r"\bcan\s+(\w+)", b_lower)) or \
                 ("cannot" in b_lower and re.search(r"\bcan\s+(\w+)", a_lower)):
                verb_can = re.findall(r"\bcan\s+([a-z]{3,})", a_lower if "cannot" in b_lower else b_lower)
                verb_cannot = re.findall(r"\bcannot\s+([a-z]{3,})", b_lower if "cannot" in b_lower else a_lower)
                if verb_can and verb_cannot and set(verb_can).intersection(set(verb_cannot)):
                    has_modal_opposing = True

        has_opposing_terms = has_direct_opposing or has_modal_opposing

        # Opposing directives: Must share at least 1 meaningful subject keyword (e.g., "remote work", "engineering")
        if has_opposing_terms and len(meaningful_common_words) >= 1:
            context_snippet = ", ".join(list(meaningful_common_words)[:3])
            return ContradictionResult(
                is_contradiction=True,
                conflict_type="direct_contradiction",
                severity="high",
                confidence=0.90,
                reasoning=f"Claims share subject ({context_snippet}) but contain mutually opposing rules or constraints.",
            )

        # If either claim is pure document structure/metadata, it does not contradict operational rules
        if is_header_a or is_header_b:
            return ContradictionResult(
                is_contradiction=False,
                conflict_type="compatible",
                severity="low",
                confidence=0.88,
                reasoning="Document structure, metadata header, and operational content are compatible.",
            )

        # Domain metric units & policy constraint keywords
        metric_keywords = {
            "day", "week", "month", "year", "hour", "minute", "leave", "allowance",
            "limit", "amount", "threshold", "window", "rate", "sla", "discount",
            "fee", "charge", "price", "cost", "salary", "bonus", "score", "percent"
        }
        constraint_keywords = {
            "window", "exception", "threshold", "limit", "cap", "maximum", "minimum",
            "eligible", "eligibility", "allowed", "permitted", "required", "grant", "granted", "approval", "signoff"
        }

        shared_metrics = meaningful_common_words.intersection(metric_keywords)
        has_constraint_context = (
            any(w in a_lower for w in constraint_keywords) and
            any(w in b_lower for w in constraint_keywords)
        )

        # Extract semantic units
        curr_a = set(re.findall(r"\$[\d,]+(?:\.\d+)?|\b\d+(?:[.,]\d+)?\s*(?:dollars?|usd|inr|rupees?|eur|euros?)\b", clean_a))
        curr_b = set(re.findall(r"\$[\d,]+(?:\.\d+)?|\b\d+(?:[.,]\d+)?\s*(?:dollars?|usd|inr|rupees?|eur|euros?)\b", clean_b))
        
        dur_a = set(re.findall(r"\b\d+[-\s]*(?:days?|weeks?|months?|years?|hours?|mins?|minutes?)\b", clean_a))
        dur_b = set(re.findall(r"\b\d+[-\s]*(?:days?|weeks?|months?|years?|hours?|mins?|minutes?)\b", clean_b))

        pct_a = set(re.findall(r"\b\d+(?:\.\d+)?\s*(?:\%|percent)\b", clean_a))
        pct_b = set(re.findall(r"\b\d+(?:\.\d+)?\s*(?:\%|percent)\b", clean_b))

        # Pillar 2: Check if either claim is an illustrative scenario or transaction sample
        illustrative_patterns = [
            r"\bexample\s*:\s*transaction\b",
            r"\bfor\s+example\b",
            r"\bhypothetical\b",
            r"\bsample\s+transaction\b",
            r"\billustrative\s+only\b",
            r"\brf-\d+-\d+\b",
            r"\bcase\s+[a-f]\b",
            r"\bsample\s+case\b",
            r"\bcase\s+[a-f]\s*-\b",
        ]
        if any(re.search(p, a_lower) for p in illustrative_patterns) or any(re.search(p, b_lower) for p in illustrative_patterns):
            return ContradictionResult(
                is_contradiction=False,
                conflict_type="illustrative_example",
                severity="low",
                confidence=0.92,
                reasoning="One or both claims are concrete transaction scenarios or illustrative examples rather than conflicting policy rules.",
            )

        # Pillar 2b: Executive Summary, Table of Contents, or Revision History vs. Detail Clauses
        summary_patterns = [
            r"\bpolicy\s+summary\b",
            r"\bsummary\s+at\s+a\s+glance\b",
            r"\btable\s+of\s+contents\b",
            r"\brevision\s+history\b",
            r"\bcase\s+studies\b",
            r"\bpage\s+22\b",
            r"\bversion\s+4\.[0-2]\b",
        ]
        if any(re.search(p, a_lower) for p in summary_patterns) or any(re.search(p, b_lower) for p in summary_patterns):
            return ContradictionResult(
                is_contradiction=False,
                conflict_type="compatible_summary",
                severity="low",
                confidence=0.92,
                reasoning="One claim is an executive summary table, index, or revision history that outlines detailed canonical clauses.",
            )

        # Pillar 3: Detect temporal versioning (legacy vs current)
        if ("legacy" in a_lower and "current" in b_lower) or ("legacy" in b_lower and "current" in a_lower):
            return ContradictionResult(
                is_contradiction=True,
                conflict_type="temporal_outdated",
                severity="medium",
                confidence=0.95,
                reasoning="One claim represents legacy policy evidence superseded by current active policy evidence.",
            )

        # Pillar 4: Semantic Facet Alignment (Prevent Apples-to-Oranges Matching)
        def _detect_facet(text: str) -> str:
            if any(k in text for k in ["phone", "call", "live chat", "email support", "response within", "hours (pacific", "gmt", "status line", "contact information"]):
                return "support_channels"
            if any(k in text for k in ["store credit", "valid for 5 years", "redeemable online"]):
                return "store_credit"
            if any(k in text for k in ["privacy policy", "retained for 7 years", "audit purposes", "stored per our privacy"]):
                return "privacy_retention"
            if any(k in text for k in ["email your rma", "label within 1 hour", "instantly online", "rma issued"]):
                return "rma_issuance"
            if any(k in text for k in ["abuse", "fraud", "counterfeit", "suspended for", "account closed", "wardrobing", "appeals in writing"]):
                return "fraud_penalties"
            if any(k in text for k in ["cooling-off", "statutory rights", "distance purchases"]):
                return "statutory_rights"
            if any(k in text for k in ["price adjustment", "drops in price"]):
                return "price_adjustments"
            if any(k in text for k in ["pause for up to", "pausing instead of cancelling"]):
                return "subscription_pause"
            if any(k in text for k in ["own carrier", "reimbursement for carrier"]):
                return "carrier_reimbursement"
            if any(k in text for k in ["digital goods", "trail guides", "video courses", "corrupt or inaccessible"]):
                return "digital_products"
            if any(k in text for k in ["warranty period", "manufacturing defects", "repair, replace", "tents and shelters 2 years"]):
                return "product_warranty"
            if any(k in text for k in ["subscription", "trailhead box", "free trial", "monthly gear box", "accidental renewal"]):
                return "subscriptions"
            if any(k in text for k in ["return freight", "carrier costs", "return shipping", "label cost", "deducted from refund"]):
                return "shipping_costs"
            if any(k in text for k in ["warehouse receipt", "inspection 1-2", "bank transfer 5-10", "posted by bank"]):
                return "refund_processing_sla"
            if any(k in text for k in ["chargeback", "dispute", "card issuer", "payment processor", "notifies us within", "duplicate recoveries", "4853", "4837", "4855", "4834", "4841"]):
                return "chargebacks_and_disputes"
            if any(k in text for k in ["cancel", "cancellation", "order status", "pre-order", "backordered"]):
                return "order_cancellations"
            if any(k in text for k in ["approval threshold", "agent may approve", "team lead approval", "director approval"]):
                return "approval_thresholds"
            if any(k in text for k in ["stolen", "police report", "courtesy replacement"]):
                return "stolen_packages"
            if any(k in text for k in ["gift card", "e-gift card", "balances under", "california, balances"]):
                return "gift_cards"
            if any(k in text for k in ["cash (in-store)", "cash refund", "cash purchases under", "cash up to"]):
                return "cash_refund_limits"
            if any(k in text for k in ["return window", "return policy", "days of the delivery", "returned within 30", "calendar days"]):
                return "return_window"
            return "general"

        facet_a = _detect_facet(a_lower)
        facet_b = _detect_facet(b_lower)

        # If two claims govern distinct operational facets, they do not contradict
        if facet_a != "general" and facet_b != "general" and facet_a != facet_b:
            return ContradictionResult(
                is_contradiction=False,
                conflict_type="orthogonal_domains",
                severity="low",
                confidence=0.92,
                reasoning=f"Claims govern orthogonal operational facets ({facet_a} vs {facet_b}) and do not compete.",
            )

        # Pillar 5: Hierarchical Exceptions within the same domain (Lex Specialis)
        # E.g. Standard merchandise (30d) vs Premium loyalty tier (60d) or Specialty items (45d)
        is_tier_exception_a = any(k in a_lower for k in ["exception", "upon vp approval", "enterprise tier", "premium tier", "specialty items", "rest of world", "statutory", "receipt-less", "keep it", "vip", "platinum", "custom contract"])
        is_tier_exception_b = any(k in b_lower for k in ["exception", "upon vp approval", "enterprise tier", "premium tier", "specialty items", "rest of world", "statutory", "receipt-less", "keep it", "vip", "platinum", "custom contract"])
        is_baseline_a = any(k in a_lower for k in ["standard merchandise", "most items", "standard return policy"])
        is_baseline_b = any(k in b_lower for k in ["standard merchandise", "most items", "standard return policy"])

        if (is_tier_exception_a and is_baseline_b) or (is_tier_exception_b and is_baseline_a) or (is_tier_exception_a and is_tier_exception_b and facet_a == facet_b):
            return ContradictionResult(
                is_contradiction=False,
                conflict_type="compatible_exception",
                severity="low",
                confidence=0.92,
                reasoning="Claims define a standard baseline and a conditional loyalty/category exception (Lex Specialis).",
            )

        # If claims affirm identical primary numerical values, they agree
        shared_nums = nums_a.intersection(nums_b)
        if bool(shared_nums) and len(meaningful_common_words) >= 1:
            return ContradictionResult(
                is_contradiction=False,
                conflict_type="compatible",
                severity="low",
                confidence=0.95,
                reasoning=f"Claims affirm matching thresholds ({list(shared_nums)[:2]}).",
            )

        # Semantic unit mismatch check:
        # Avoid generic domain words (like 'customer', 'order', 'refund', 'policy') creating false-positive matches
        domain_generic_words = {"customer", "order", "item", "refund", "return", "policy", "store", "northwind", "within", "plus", "days", "day"}
        specific_common_words = meaningful_common_words - domain_generic_words

        is_same_specific_facet = (facet_a == facet_b and facet_a != "general")
        has_strong_semantic_alignment = (len(specific_common_words) >= 1) or is_same_specific_facet

        has_unit_conflict = (
            (bool(curr_a) and bool(curr_b) and curr_a != curr_b and (is_same_specific_facet or has_constraint_context or (facet_a == "general" and facet_b == "general" and len(specific_common_words) >= 1))) or
            (bool(dur_a) and bool(dur_b) and dur_a != dur_b and (is_same_specific_facet or has_constraint_context or (facet_a == "general" and facet_b == "general" and len(specific_common_words) >= 1))) or
            (bool(pct_a) and bool(pct_b) and pct_a != pct_b and (is_same_specific_facet or has_constraint_context or (facet_a == "general" and facet_b == "general" and len(specific_common_words) >= 1)))
        )

        is_numerical_conflict = (
            (has_unit_conflict and (has_strong_semantic_alignment or has_constraint_context)) or
            (
                bool(nums_a) and bool(nums_b) and nums_a != nums_b and (is_same_specific_facet or has_constraint_context) and (
                    (len(meaningful_common_words) >= 2 and (shared_metrics or has_constraint_context))
                )
            )
        )

        if is_numerical_conflict:
            context_snippet = ", ".join(list(meaningful_common_words)[:3])
            return ContradictionResult(
                is_contradiction=True,
                conflict_type="numerical_discrepancy",
                severity="high",
                confidence=0.92,
                reasoning=f"Claims share subject context ({context_snippet}) and facet ({facet_a}) but specify conflicting numerical thresholds: {list(nums_a)[:2]} vs {list(nums_b)[:2]}.",
            )

        return ContradictionResult(
            is_contradiction=False,
            conflict_type="compatible",
            severity="low",
            confidence=0.85,
            reasoning="Claims do not contradict or apply to different non-overlapping domains.",
        )

    async def generate_grounded_answer(
        self,
        query: str,
        citations: list[dict],
        has_conflicts: bool = False,
        warnings: list[str] | None = None,
        history: list[dict] | None = None,
    ) -> str:
        """Intelligent Hybrid grounded synthesis with metric extraction and gap analysis."""
        from app.services.policy_answer_synthesizer import PolicyAnswerSynthesizer
        return PolicyAnswerSynthesizer.synthesize(
            query=query,
            citations=citations,
            has_conflicts=has_conflicts,
            warnings=warnings,
            history=history,
        )

