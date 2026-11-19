import math
import re
from typing import Optional, Sequence, Set
from sqlalchemy import or_, select
from sqlalchemy.orm import selectinload

from app.conflict_engine.facet_registry import ENTERPRISE_FACET_REGISTRY
from app.db.models.claim import Claim

# Operational facets for sharding enterprise governance policies
FACET_PATTERNS = {
    "support_channels": [
        r"\bphone\b", r"\bcall\b", r"\blive\s+chat\b", r"\bemail\s+support\b",
        r"\bresponse\s+within\b", r"\bhours?\s*\((?:pacific|est|utc|gmt)\)",
        r"\bcontact\s+(?:information|us)\b", r"\bhelp\s+desk\b"
    ],
    "store_credit": [
        r"\bstore\s+credit\b", r"\bvalid\s+for\b", r"\bredeemable\b",
        r"\bgift\s+card\b", r"\bvoucher\b", r"\bcredit\s+balance\b"
    ],
    "fraud_penalties": [
        r"\babuse\b", r"\bfraud\b", r"\bcounterfeit\b", r"\bsuspended\b",
        r"\baccount\s+closed\b", r"\bwardrobing\b", r"\bappeals?\b",
        r"\bprohibited\b", r"\bviolat(?:ion|ing)\b"
    ],
    "statutory_rights": [
        r"\bcooling-off\b", r"\bstatutory\b", r"\bdistance\s+purchas(?:e|es|ing)\b",
        r"\beu\s+and\s+uk\b", r"\bjurisdiction\b", r"\bmandatory\s+law\b"
    ],
    "price_adjustments": [
        r"\bprice\s+adjustment\b", r"\bdrops?\s+in\s+price\b", r"\bmatch(?:ing|es)?\s+price\b",
        r"\bprice\s+guarantee\b", r"\bsale\s+price\b"
    ],
    "product_warranty": [
        r"\bwarranty\b", r"\bdefect(?:ive|s)?\b", r"\brepair\b",
        r"\breplace(?:ment)?\b", r"\bmanufacturing\b", r"\blifetime\s+guarantee\b"
    ],
    "subscriptions": [
        r"\bsubscription\b", r"\btrailhead\s+box\b", r"\bfree\s+trial\b",
        r"\bmonthly\s+gear\b", r"\brenewal\b", r"\bmembership\s+fee\b",
        r"\bannual\s+plan\b"
    ],
    "shipping_costs": [
        r"\breturn\s+(?:freight|shipping|label)\b", r"\bcarrier\s+costs?\b",
        r"\bshipping\s+fee\b", r"\bdeducted\s+from\s+refund\b", r"\bfree\s+shipping\b"
    ],
    "refund_processing_sla": [
        r"\bwarehouse\s+receipt\b", r"\binspection\b", r"\bbank\s+transfer\b",
        r"\bposted\s+by\s+bank\b", r"\bbusiness\s+days\s+after\b", r"\bprocessing\s+time\b"
    ],
    "return_window": [
        r"\breturn\s+window\b", r"\breturn\s+policy\b", r"\bdays?\s+from\s+delivery\b",
        r"\breturned\s+within\b", r"\bcalendar\s+days?\b", r"\breceipt-less\b"
    ],
    "chargebacks_and_disputes": [
        r"\bchargeback\b", r"\bdispute\b", r"\bcard\s+issuer\b", r"\bpayment\s+processor\b",
        r"\bnotifies\s+us\s+within\b", r"\bduplicate\s+recoveries\b", r"\b4853\b", r"\b4837\b",
        r"\b4855\b", r"\b4834\b", r"\b4841\b"
    ],
    "order_cancellations": [
        r"\bcancel\b", r"\bcancellation\b", r"\border\s+status\b", r"\bpre-order\b", r"\bbackordered\b"
    ],
    "approval_thresholds": [
        r"\bapproval\s+threshold\b", r"\bagent\s+may\s+approve\b", r"\bteam\s+lead\s+approval\b",
        r"\bdirector\s+approval\b", r"\bmanager\s+approval\b"
    ],
    "security_compliance": [
        r"\bsoc\s*2\b", r"\bgdpr\b", r"\bhipaa\b", r"\bdata\s+retention\b",
        r"\baccess\s+control\b", r"\bencryption\b", r"\bmulti-factor\b"
    ],
}

STOPWORDS = {
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


class FacetSharder:
    """
    Tier 1 High-Scale Candidate Generator.
    
    Reduces O(N²) cross-comparison down to O(K) by:
    1. Classifying claims into discrete operational governance facets.
    2. Constructing high-selectivity SQL inverted token filters.
    3. Applying vector embedding similarity thresholds (default >= 0.65).
    """

    @classmethod
    def detect_facet(cls, text: str) -> str:
        """Categorize claim text into an operational facet using enterprise registry and retail patterns."""
        t_lower = text.lower()
        # 1. Check enterprise governance & HR domain facets
        for facet_name, defn in ENTERPRISE_FACET_REGISTRY.items():
            if any(re.search(p, t_lower) for p in defn.patterns):
                return facet_name

        # 2. Check operational retail & customer support patterns
        for facet, patterns in FACET_PATTERNS.items():
            if any(re.search(p, t_lower) for p in patterns):
                return facet
        return "general"

    @classmethod
    def are_facets_compatible(cls, facet_a: str, facet_b: str) -> bool:
        """Return True if two facets are eligible to contradict one another."""
        if facet_a == "general" or facet_b == "general":
            return True
        return facet_a == facet_b

    @classmethod
    def extract_salient_tokens(cls, text: str, max_tokens: int = 5) -> list[str]:
        """Extract high-entropy domain tokens to build selective SQL match clauses."""
        raw_words = re.findall(r"[a-z]{3,}", text.lower())
        meaningful = [re.sub(r"s$", "", w) for w in raw_words if w not in STOPWORDS and len(w) >= 4]
        # Keep unique in order
        seen = set()
        result = []
        for w in meaningful:
            if w not in seen:
                seen.add(w)
                result.append(w)
                if len(result) >= max_tokens:
                    break
        return result

    @classmethod
    def cosine_similarity(cls, vec_a: Sequence[float], vec_b: Sequence[float]) -> float:
        """Compute cosine similarity between two dense embedding vectors."""
        if not vec_a or not vec_b or len(vec_a) != len(vec_b):
            return 0.0
        dot = sum(a * b for a, b in zip(vec_a, vec_b))
        norm_a = math.sqrt(sum(a * a for a in vec_a))
        norm_b = math.sqrt(sum(b * b for b in vec_b))
        if norm_a == 0 or norm_b == 0:
            return 0.0
        return dot / (norm_a * norm_b)

    @classmethod
    def build_candidate_query(
        cls,
        target_claim: Claim,
        limit: int = 100,
    ):
        """
        Build an index-optimized SQL query that pulls ONLY high-affinity candidate claims
        rather than performing a full table scan across the organization's entire corpus.
        """
        target_facet = cls.detect_facet(target_claim.claim_text)
        salient_tokens = cls.extract_salient_tokens(target_claim.claim_text, max_tokens=4)

        base_stmt = (
            select(Claim)
            .where(
                Claim.organization_id == target_claim.organization_id,
                Claim.id != target_claim.id,
            )
            .options(
                selectinload(Claim.document_version),
                selectinload(Claim.validity_records),
            )
        )

        # If salient tokens exist, filter using SQL OR clauses across salient tokens
        if salient_tokens:
            token_filters = [Claim.claim_text.ilike(f"%{tok}%") for tok in salient_tokens]
            if target_claim.subject:
                subj_tokens = cls.extract_salient_tokens(target_claim.subject, max_tokens=2)
                for st in subj_tokens:
                    token_filters.append(Claim.subject.ilike(f"%{st}%"))
            base_stmt = base_stmt.where(or_(*token_filters))

        base_stmt = base_stmt.limit(limit)
        return base_stmt, target_facet
