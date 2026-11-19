# Curator & Conflict Subsystem: Operational Runbook

**Version**: 1.0.0  
**Target Audience**: DevOps, Site Reliability Engineers (SRE), Compliance Officers, Data Stewards  
**Status**: Staging Verified / Canary Ready  

---

## 1. System Overview & Rollout Posture

The **Context Curator & Conflict Resolution Engine** identifies, explains, and resolves contradictory enterprise claims. To ensure data governance and audit integrity, the subsystem adheres to the **Advisory-First / Controlled Canary** posture:

```mermaid
flowchart TD
    A["Raw Document Versions"] --> B["Conflict Detection & Compatibility Gate"]
    B --> C{"Operating Mode"}
    C -->|Shadow Mode| D["Evaluation Artifact (0 DB Mutations)"]
    C -->|Canary Mode| E{"Rule in Safe Whitelist?"}
    E -->|Yes (Supersession / Expiry)| F["Atomic DB Mutation & Immutable HumanReview"]
    E -->|No (Numeric / Substantive)| G["HITL Review Queue (HUMAN_REVIEW_REQUIRED)"]
    C -->|Kill Switch Active| H["Abort Mutation -> Advisory Report Only"]
```

* **Default UI Posture**: `Mode: Assisted Governance (Advisory-First)`.
* **Default Autonomous Mode**: Disabled (`shadow_mode=True`).
* **Canary Mode**: When autonomous execution is triggered (`shadow_mode=False`), mutations are strictly limited to unambiguous deterministic rules (`EXPLICIT_SUPERSESSION`, `TEMPORAL_OBSOLESCENCE`).
* **Human-Gated Scope**: Numeric thresholds, differing scopes, conditional exceptions, and multi-agent arbitration require human reviewer confirmation.

---

## 2. Emergency Kill Switch Procedure

The emergency kill switch immediately stops all autonomous database mutations across all tenants without requiring service restart or code redeployment.

### 2.1 Triggering the Kill Switch

#### Option A: Environment Variable (Recommended for SRE Deployments)
Set the environment variable in your production orchestrator (Docker Compose, Kubernetes ConfigMap, or `.env`):
```bash
AUTONOMOUS_RESOLUTION_KILL_SWITCH=true
```

#### Option B: Dynamic Runtime Toggle (Python Console / Admin REPL)
```python
from app.core.config import settings

# Instantly halts all autonomous mutations
settings.autonomous_resolution_kill_switch = True
```

### 2.2 Expected System Behavior
When the kill switch is active, any call to `POST /v1/conflicts/auto-resolve?shadow_mode=false` immediately halts with:
```json
{
  "status": "blocked",
  "operating_mode": "KILL_SWITCH_ACTIVE",
  "message": "Autonomous conflict resolution is currently disabled via emergency kill switch. Operating in Advisory/Shadow mode only.",
  "total_evaluated": 0,
  "auto_resolved_count": 0,
  "remaining_pending_count": 0,
  "rules_breakdown": {}
}
```
* **Safety Lock**: Zero database commits, zero claim status mutations, and zero conflicting field updates occur.
* **Manual Review Unaffected**: Authorized human reviewers (`reviewer`, `auditor`, `admin`) can still manually review and resolve conflicts via Curator Studio.

### 2.3 Re-enabling Procedure
1. Confirm root cause (e.g. database lockup, unexpected model hallucination) is resolved.
2. Verify test suite passes on staging:
   ```powershell
   pytest backend/tests/integration/test_curator_production_gate_invariants.py -v
   ```
3. Set `AUTONOMOUS_RESOLUTION_KILL_SWITCH=false` and notify compliance officers.

---

## 3. Interpreting Shadow-Mode Comparison Reports

Before activating autonomous resolution on any document corpus, execute `auto_resolve_conflicts(shadow_mode=True)`.

### 3.1 Sample Report Payload
```json
{
  "shadow_run_id": "srun_7f9b2d88c401",
  "operating_mode": "SHADOW_RECOMMENDATION_ONLY",
  "conflicts_detected": 14,
  "would_auto_resolve_count": 10,
  "human_review_queue_count": 4,
  "precision_calibration": {
    "is_calibrated": false,
    "agreed_correct_recommendations": 0,
    "total_recommendations_evaluated": 0,
    "calibrated_precision_score": null,
    "sample_size_confidence": "PROVISIONAL_FINITE_SAMPLE (N=0; zero observed failures does not prove zero production risk)",
    "formula": "agreed_correct_recommendations / total_recommendations_evaluated"
  },
  "precision_estimate": 1.0,
  "false_positive_candidates": {
    "count": 2,
    "items": [
      {
        "conflict_id": "cfl_01a",
        "rule": "LEX_SPECIALIS_EXCEPTION",
        "is_compatible_exception": true,
        "reasoning": "Specific conditional exception co-exists with general baseline standard."
      }
    ]
  },
  "rules_breakdown": {
    "EXPLICIT_SUPERSESSION": 6,
    "TEMPORAL_RECENCY_VERSION_LINEAGE": 4
  },
  "rollback_reference": "rb_snap_202611120408_srun_7f9b"
}
```

### 3.2 Evaluation Audit Checklist
1. **Calibration Status**: Inspect `is_calibrated`. If `false`, the precision score is provisional. Autonomous broad resolution must remain gated until $N \ge 20$ human-labeled decisions are verified.
2. **False-Positive Candidates**: Verify that entries in `false_positive_candidates` represent legitimate non-competing scopes or Lex Specialis exceptions.
3. **Queue Distribution**: Ensure `human_review_queue_count` captures true numeric ambiguities rather than forcing high-risk automated guesses.

---

## 4. Handling Failed Batches & Partial Rollbacks

### 4.1 Transactional Rollback Guarantee
All multi-claim mutations inside `ConflictService.auto_resolve_conflicts` and `ConflictService.resolve_conflict_issue` execute inside an atomic SQLAlchemy transaction:
```python
try:
    await self.session.flush()
    # Recalculate trust scores for affected claims
    await self.session.commit()
except Exception as e:
    await self.session.rollback()
    logger.error(f"ALERT: Autonomous conflict resolution transaction failed and rolled back cleanly: {e}")
    raise e
```

### 4.2 Incident Response Steps
If an alert log indicates an unhandled failure during auto-resolve:
1. **Search Sentry / Application Logs**:
   ```bash
   grep -E "ALERT: Autonomous conflict resolution transaction failed" /var/log/trulin/backend.log
   ```
2. **Verify Database State**: Check that no claims were left in intermediate states (`SUPERSEDED` without winner `VERIFIED`):
   ```sql
   SELECT id, status, updated_at FROM claims WHERE status = 'superseded' AND updated_at > NOW() - INTERVAL '1 hour';
   ```
3. **Check Rollback Snapshot**: Cross-reference the logged `rollback_reference` (e.g. `rb_snap_202611120408_srun_7f9b`) to confirm zero changes persisted.
4. **Fallback**: Trigger the kill switch if the error indicates database constraint deadlock or schema mismatch.

---

## 5. Responding to Reconciliation Alerts

The reconciliation worker detects and repairs **orphaned conflicts** where underlying claims were deleted or updated outside the standard curator resolution lifecycle.

### 5.1 Triggering Scheduled Reconciliation
Run via CLI or scheduled task runner:
```python
from app.db.database import AsyncSessionLocal
from app.services.conflict_service import ConflictService

async def run_reconciliation(org_id=None):
    async with AsyncSessionLocal() as session:
        service = ConflictService(session)
        result = await service.reconcile_orphaned_conflicts(organization_id=org_id)
        print("Reconciliation result:", result)
```

### 5.2 Resolution Actions
* **Missing Claim**: If either `claim_a` or `claim_b` was pruned/deleted, conflict status is updated to `RESOLVED` with rationale `"Reconciliation: Underlying claim was pruned or deleted."`
* **Pre-Superseded Claim**: If either claim was already marked `SUPERSEDED` or `OUTDATED`, conflict status is updated to `RESOLVED` with rationale `"Reconciliation: One or both claims were already superseded/outdated."`

---

## 6. Managing Per-Tenant & Per-Domain Rollout Scope

### 6.1 Tenant Rollout Flag (`Organization.governance_config`)
Control autonomous capabilities per tenant by updating the `governance_config` JSONB column:

```sql
UPDATE organizations
SET governance_config = jsonb_set(
    COALESCE(governance_config, '{}'::jsonb),
    '{allow_autonomous_resolution}',
    'true'
)
WHERE slug = 'acme-corp';
```

* **`allow_autonomous_resolution: true`**: Tenant allows canary auto-resolution for explicit supersession.
* **`allow_autonomous_resolution: false`** (Default): Tenant is locked to Advisory-First mode; all auto-resolve executions default to `shadow_mode=True`.

### 6.2 Domain-Driven Attestation Horizons
Review horizons are mapped to domain risk profiles in `drift_decay_service.py`:

```python
DEFAULT_DOMAIN_HORIZONS = {
    "financial_controls": {"horizon": 30, "mandatory": True, "grace": 7},
    "safety_compliance":  {"horizon": 60, "mandatory": True, "grace": 14},
    "regulatory_policy":  {"horizon": 90, "mandatory": True, "grace": 15},
    "hr_travel_expense":  {"horizon": 90, "mandatory": True, "grace": 30},
    "engineering_docs":   {"horizon": 120, "mandatory": False, "grace": 30},
    "general_faq":        {"horizon": 180, "mandatory": False, "grace": 45},
}
```

* High-risk controls (e.g. `financial_controls`) enforce strict 30-day horizons with mandatory re-attestation.
* Informational policies (e.g. `general_faq`) allow 180-day horizons with 45-day grace periods.

---

## 7. Acceptance Criteria for Full Autonomous Production

Do not expand autonomous resolution beyond canary mode until **all 7 criteria** are formally satisfied:

- [ ] **1. Shadow-Mode Corpus Trial**: Evaluated against 50–100 multi-version documents; agreement rate $\ge 95\%$.
- [ ] **2. False-Positive Rate**: Compatible scope / exception false-positive rate $\le 2\%$.
- [ ] **3. Blast-Radius Calibration**: Logged $\ge 30$ human reviewer decisions via `BlastRadiusCalibrator` with false-critical rate $\le 10\%$.
- [ ] **4. Database Invariants**: 59/59 regression tests passing on live PostgreSQL.
- [ ] **5. Conservative Scope**: Autonomous mutations remain limited strictly to explicit supersession and temporal expiry.
- [ ] **6. Immutable Provenance**: Every resolution produces a `HumanReview` or `UserActivityLog` audit record and rollback reference.
- [ ] **7. Verified Kill Switch**: Operational kill switch tested and verified reachable without service restart.

