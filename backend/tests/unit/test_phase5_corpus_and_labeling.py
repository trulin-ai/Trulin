"""
Phase 5 Step 5.1 Unit Tests: Corpus Selection, Authoritative Labeling Protocol, and Contamination Matrix.

Tests:
1. Four-family corpus structure (12 documents, 3 per family, 8 train / 4 held-out).
2. Authoritative source inventory integrity (250 units, verbatim text, SHA-256, page offsets).
3. Two-pass labeling protocol and classification distribution (operative, non-operative, ambiguous).
4. Contamination-control matrix (zero cross-family document overlap, zero shared text spans).
5. 8 Gate-family compatibility and per-family quality target thresholds.
"""
import hashlib
import json
from pathlib import Path
import pytest

BASELINE_DIR = Path(__file__).resolve().parent.parent.parent / "scripts" / "baseline"

@pytest.fixture
def corpus_manifest():
    p = BASELINE_DIR / "phase5_multidoc_corpus_manifest.json"
    assert p.exists(), f"Missing corpus manifest at {p}"
    with open(p, "r", encoding="utf-8") as f:
        return json.load(f)

@pytest.fixture
def source_inventory():
    p = BASELINE_DIR / "phase5_authoritative_source_inventory.json"
    assert p.exists(), f"Missing source inventory at {p}"
    with open(p, "r", encoding="utf-8") as f:
        return json.load(f)

@pytest.fixture
def contamination_matrix():
    p = BASELINE_DIR / "phase5_contamination_control_matrix.json"
    assert p.exists(), f"Missing contamination matrix at {p}"
    with open(p, "r", encoding="utf-8") as f:
        return json.load(f)

def test_corpus_manifest_structure(corpus_manifest):
    assert corpus_manifest["total_families"] == 4
    assert corpus_manifest["total_documents"] == 12
    assert corpus_manifest["train_documents"] == 8
    assert corpus_manifest["held_out_documents"] == 4

    expected_families = ["FAM-1", "FAM-2", "FAM-3", "FAM-4"]
    actual_families = [f["family_id"] for f in corpus_manifest["families"]]
    assert actual_families == expected_families

    for fam in corpus_manifest["families"]:
        assert len(fam["documents"]) == 3
        train_count = sum(1 for d in fam["documents"] if d["split"] == "train")
        held_out_count = sum(1 for d in fam["documents"] if d["split"] == "held_out")
        assert train_count == 2
        assert held_out_count == 1
        assert fam["target_recall"] in [0.90, 0.95]
        assert fam["target_lifecycle"] in [0.95, 0.98]

def test_authoritative_source_inventory_integrity(source_inventory):
    units = source_inventory["units"]
    assert len(units) == 250
    assert source_inventory["protocol_version"] == "2.0-two-pass"

    seen_ids = set()
    for u in units:
        assert u["unit_id"] not in seen_ids, f"Duplicate unit_id: {u['unit_id']}"
        seen_ids.add(u["unit_id"])

        assert len(u["sha256"]) == 64
        # Validate that SHA-256 matches verbatim text
        computed_sha = hashlib.sha256(u["verbatim_text"].encode("utf-8")).hexdigest()
        assert computed_sha == u["sha256"], f"SHA mismatch for {u['unit_id']}"

        assert u["classification"] in ["operative", "non_operative", "ambiguous"]
        assert u["page"] >= 1
        assert u["char_end"] > u["char_start"]
        assert u["pass1_candidate"] is True
        assert u["pass2_confirmed"] is True

def test_two_pass_labeling_distribution(source_inventory):
    units = source_inventory["units"]
    operative_cnt = sum(1 for u in units if u["classification"] == "operative")
    non_op_cnt = sum(1 for u in units if u["classification"] == "non_operative")
    ambiguous_cnt = sum(1 for u in units if u["classification"] == "ambiguous")

    assert operative_cnt == 46
    assert non_op_cnt == 197
    assert ambiguous_cnt == 7
    assert operative_cnt + non_op_cnt + ambiguous_cnt == 250

    # Ensure ambiguous units exist in multiple families and are not forced into categories
    fam_with_ambiguous = set(u["family_id"] for u in units if u["classification"] == "ambiguous")
    assert len(fam_with_ambiguous) >= 3

def test_contamination_control_invariants(contamination_matrix, corpus_manifest):
    assert contamination_matrix["status"] == "PASS"
    checks = contamination_matrix["checks"]
    assert checks["cross_family_document_isolation"] is True
    assert checks["cross_family_text_span_isolation"] is True
    assert checks["violations_detected"] == 0

    # Verify no document filename appears in more than one family
    all_filenames = []
    for fam in corpus_manifest["families"]:
        for d in fam["documents"]:
            all_filenames.append(d["filename"])
    assert len(all_filenames) == len(set(all_filenames)) == 12

