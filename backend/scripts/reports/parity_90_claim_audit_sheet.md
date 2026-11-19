# Pass 2: Benchmark vs Live Parity Audit Sheet (64 Difference Claims)

**Audit Summary:** 64 Differing Claims Audited • Verified Verdict Scale

- **Verified in Live:** 295 / 359 (82.2%)
- **Audited Differences:** 64 Claims
  - **Safe Normalization Promotable (VALID):** 40 claims
  - **Correctly Blocked / Rejected:** 24 claims

| ID | Document | Subject | Raw Predicate | Normalized Predicate | Live Status | Classification | Verdict |
|---|---|---|---|---|:---:|:---:|:---:|
| `04da7406` | Mcaps Msft Gsa Commercial Su... | Customers | `has_permitted_use_scop` | `has_permitted_use_scop` | `candidate` | `NORMALIZATION_GAP` | **VALID** |
| `051e7a3d` | Migrate Ea To Microsoft Cust... | InstanceId | `has_billing_schedule` | `has_billing_schedule` | `rejected` | `BENCHMARK_FALSE_POSITIVE` | **SCHEMA_FRAGMENT** |
| `0dd0b475` | Mcaps Msft Gsa Commercial Su... | Company | `has_permitted_use_scop` | `has_permitted_use_scop` | `candidate` | `NORMALIZATION_GAP` | **VALID** |
| `137e7c85` | Mcaps Msft Gsa Commercial Su... | Customers | `has_permitted_use_scop` | `has_permitted_use_scop` | `candidate` | `NORMALIZATION_GAP` | **VALID** |
| `16c718d6` | Mcaps Msft Gsa Commercial Su... | Customers | `has_permitted_use_scop` | `has_permitted_use_scop` | `rejected` | `NORMALIZATION_GAP` | **VALID** |
| `18d53c92` | Migrate Ea To Microsoft Cust... | MeterSubCategory | `has_stage_duration` | `has_col3` | `candidate` | `BENCHMARK_FALSE_POSITIVE` | **SCHEMA_FRAGMENT** |
| `1a81f59b` | Migrate Ea To Microsoft Cust... | Invoices | `has_billing_schedule` | `has_col3` | `candidate` | `BENCHMARK_FALSE_POSITIVE` | **SCHEMA_FRAGMENT** |
| `1a8da445` | Microsoft Partner Agreement ... | Microsoft | `has_permitted_use_scop` | `has_permitted_use_scop` | `candidate` | `NORMALIZATION_GAP` | **VALID** |
| `1cc1279f` | Mcaps Msft Gsa Commercial Su... | Notice | `requires_written_notic` | `requires_written_notic` | `rejected` | `SUBJECT_BLOCKED` | **INVALID_SUBJECT** |
| `210301b5` | Microsoft Partner Agreement ... | Company | `has_permitted_use_scop` | `has_permitted_use_scop` | `candidate` | `NORMALIZATION_GAP` | **VALID** |
| `30bd1d30` | Privacy In Microsoft Cloud S... | Data Controller | `prohibited_from_using` | `prohibited_from_using` | `candidate` | `LIVE_FALSE_NEGATIVE` | **VALID** |
| `30da192f` | Migrate Ea To Microsoft Cust... | Subscription | `has_example_value` | `has_example_value` | `rejected` | `BENCHMARK_FALSE_POSITIVE` | **SCHEMA_FRAGMENT** |
| `321f42ef` | Human Rights Transparency Re... | Employee | `has_permitted_use_scop` | `has_permitted_use_scop` | `candidate` | `NORMALIZATION_GAP` | **VALID** |
| `328e5a8f` | Mcaps Msft Gsa Commercial Su... | Company | `has_permitted_use_scop` | `has_permitted_use_scop` | `candidate` | `NORMALIZATION_GAP` | **VALID** |
| `373abf6b` | Migrate Ea To Microsoft Cust... | PartNumber | `has_stage_duration` | `has_stage_duration` | `rejected` | `BENCHMARK_FALSE_POSITIVE` | **SCHEMA_FRAGMENT** |
| `38e07a22` | Mcaps Msft Gsa Commercial Su... | Customers | `has_permitted_use_scop` | `has_permitted_use_scop` | `candidate` | `NORMALIZATION_GAP` | **VALID** |
| `3c8c68a8` | Microsoft Partner Agreement ... | Company | `remains_liable_for` | `remains_liable_for` | `rejected` | `NORMALIZATION_GAP` | **VALID** |
| `4bc6226a` | Migrate Ea To Microsoft Cust... | Billing subscription | `has_billing_schedule` | `has_billing_schedule` | `rejected` | `BENCHMARK_FALSE_POSITIVE` | **SCHEMA_FRAGMENT** |
| `51e9d15d` | Migrate Ea To Microsoft Cust... | ProductId | `has_stage_duration` | `has_stage_duration` | `rejected` | `BENCHMARK_FALSE_POSITIVE` | **SCHEMA_FRAGMENT** |
| `55e01e06` | Migrate Ea To Microsoft Cust... | Offer Name | `has_stage_duration` | `has_stage_duration` | `rejected` | `BENCHMARK_FALSE_POSITIVE` | **SCHEMA_FRAGMENT** |
| `57aaea8a` | Migrate Ea To Microsoft Cust... | ServiceTier | `has_stage_duration` | `has_col3` | `candidate` | `BENCHMARK_FALSE_POSITIVE` | **SCHEMA_FRAGMENT** |
| `5db3bc86` | Migrate Ea To Microsoft Cust... | ResourceGuid | `has_stage_duration` | `has_stage_duration` | `rejected` | `BENCHMARK_FALSE_POSITIVE` | **SCHEMA_FRAGMENT** |
| `5e985e0d` | Mcaps Msft Gsa Commercial Su... | Customers | `has_permitted_use_scop` | `has_permitted_use_scop` | `candidate` | `NORMALIZATION_GAP` | **VALID** |
| `61439d87` | Mcaps Msft Gsa Commercial Su... | Customers | `applies_to_contract_or` | `applies_to_contract_or` | `missing` | `NORMALIZATION_GAP` | **VALID** |
| `644c1002` | Microsoft Partner Agreement ... | Company | `has_permitted_use_scop` | `has_permitted_use_scop` | `candidate` | `NORMALIZATION_GAP` | **VALID** |
| `6af3aa7e` | Microsoftproductandservicesd... | Customers | `remains_liable_for` | `remains_liable_for` | `rejected` | `NORMALIZATION_GAP` | **VALID** |
| `76e15da9` | Mcaps Msft Gsa Commercial Su... | Customers | `remains_liable_for` | `remains_liable_for` | `rejected` | `NORMALIZATION_GAP` | **VALID** |
| `7c883cf2` | Migrate Ea To Microsoft Cust... | MeterName | `has_stage_duration` | `has_col3` | `candidate` | `BENCHMARK_FALSE_POSITIVE` | **SCHEMA_FRAGMENT** |
| `8115dfdb` | Migrate Ea To Microsoft Cust... | ServiceName | `has_stage_duration` | `has_col3` | `candidate` | `BENCHMARK_FALSE_POSITIVE` | **SCHEMA_FRAGMENT** |
| `86c577b3` | Mcaps Msft Gsa Commercial Su... | User | `has_permitted_use_scop` | `has_permitted_use_scop` | `candidate` | `NORMALIZATION_GAP` | **VALID** |
| `8a8ce2ba` | Mcaps Msft Gsa Commercial Su... | Auditor | `has_permitted_use_scop` | `has_permitted_use_scop` | `candidate` | `NORMALIZATION_GAP` | **VALID** |
| `8bdb18d6` | Privacy In Microsoft Cloud S... | Data Controller | `prohibited_from_using` | `prohibited_from_using` | `candidate` | `LIVE_FALSE_NEGATIVE` | **VALID** |
| `8fc1b726` | Mcaps Msft Gsa Commercial Su... | Company | `has_permitted_use_scop` | `has_permitted_use_scop` | `candidate` | `NORMALIZATION_GAP` | **VALID** |
| `902fc664` | Migrate Ea To Microsoft Cust... | Invoice | `has_billing_schedule` | `has_billing_schedule` | `rejected` | `BENCHMARK_FALSE_POSITIVE` | **SCHEMA_FRAGMENT** |
| `906f48ca` | Migrate Ea To Microsoft Cust... | MeterRegion | `has_stage_duration` | `has_col3` | `candidate` | `BENCHMARK_FALSE_POSITIVE` | **SCHEMA_FRAGMENT** |
| `909bd3ae` | Microsoft Customer Agreement... | Customers | `applies_to_contract_or` | `applies_to_contract_or` | `missing` | `NORMALIZATION_GAP` | **VALID** |
| `999ceb1b` | Mcaps Msft Gsa Commercial Su... | Customers | `has_permitted_use_scop` | `has_permitted_use_scop` | `candidate` | `NORMALIZATION_GAP` | **VALID** |
| `9aa57e81` | Mcaps Msft Gsa Commercial Su... | Customers | `has_permitted_use_scop` | `has_permitted_use_scop` | `candidate` | `NORMALIZATION_GAP` | **VALID** |
| `9c22e194` | Mcaps Msft Gsa Commercial Su... | Customers | `prohibited_from_using` | `prohibited_from_using` | `rejected` | `NORMALIZATION_GAP` | **VALID** |
| `a07363ef` | Migrate Ea To Microsoft Cust... | AccountId | `has_stage_duration` | `has_stage_duration` | `rejected` | `BENCHMARK_FALSE_POSITIVE` | **SCHEMA_FRAGMENT** |
| `a2081def` | Privacy In Microsoft Cloud S... | Data Controller | `has_permitted_use_scop` | `has_permitted_use_scop` | `candidate` | `NORMALIZATION_GAP` | **VALID** |
| `a4a24508` | Microsoft Customer Agreement... | Each party | `has_permitted_use_scop` | `has_permitted_use_scop` | `candidate` | `NORMALIZATION_GAP` | **VALID** |
| `a906c89d` | Mcaps Msft Gsa Commercial Su... | Customers | `has_permitted_use_scop` | `has_permitted_use_scop` | `candidate` | `NORMALIZATION_GAP` | **VALID** |
| `ad0b06ae` | Microsoft Business And Servi... | Each party | `has_permitted_use_scop` | `has_permitted_use_scop` | `candidate` | `NORMALIZATION_GAP` | **VALID** |
| `afee0553` | Mcaps Msft Gsa Commercial Su... | User | `has_permitted_use_scop` | `has_permitted_use_scop` | `rejected` | `NORMALIZATION_GAP` | **VALID** |
| `b6a773ba` | Migrate Ea To Microsoft Cust... | Resource group | `has_example_value` | `has_example_value` | `rejected` | `BENCHMARK_FALSE_POSITIVE` | **SCHEMA_FRAGMENT** |
| `bb852232` | Migrate Ea To Microsoft Cust... | MeterId | `has_stage_duration` | `has_stage_duration` | `rejected` | `BENCHMARK_FALSE_POSITIVE` | **SCHEMA_FRAGMENT** |
| `beb00796` | Migrate Ea To Microsoft Cust... | billingPeriodId | `has_stage_duration` | `has_stage_duration` | `rejected` | `BENCHMARK_FALSE_POSITIVE` | **SCHEMA_FRAGMENT** |
| `c6c603b2` | Microsoft Customer Agreement... | Parties | `must_be_in_writing` | `must_be_in_writing` | `missing` | `ENTAILMENT_BLOCKED` | **NON_ENTAILED** |
| `c8068f4d` | Mcaps Msft Gsa Commercial Su... | Customers | `remains_liable_for` | `remains_liable_for` | `rejected` | `NORMALIZATION_GAP` | **VALID** |
| `ccfd2553` | Mcaps Msft Gsa Commercial Su... | Customers | `has_permitted_use_scop` | `has_permitted_use_scop` | `candidate` | `NORMALIZATION_GAP` | **VALID** |
| `d2b1d807` | Mcaps Msft Gsa Commercial Su... | Customers | `has_permitted_use_scop` | `has_permitted_use_scop` | `candidate` | `NORMALIZATION_GAP` | **VALID** |
| `d437512c` | Mcaps Msft Gsa Commercial Su... | Company | `has_permitted_use_scop` | `has_permitted_use_scop` | `missing` | `ENTAILMENT_BLOCKED` | **NON_ENTAILED** |
| `d6b258a2` | Mcaps Msft Gsa Commercial Su... | Customers | `has_permitted_use_scop` | `has_permitted_use_scop` | `candidate` | `NORMALIZATION_GAP` | **VALID** |
| `dbfefa9c` | Mcaps Msft Gsa Commercial Su... | Customers | `has_permitted_use_scop` | `has_permitted_use_scop` | `candidate` | `NORMALIZATION_GAP` | **VALID** |
| `e1101b64` | Mcaps Msft Gsa Commercial Su... | Customers | `has_permitted_use_scop` | `has_permitted_use_scop` | `candidate` | `NORMALIZATION_GAP` | **VALID** |
| `e55f7930` | Mcaps Msft Gsa Commercial Su... | User | `has_permitted_use_scop` | `has_permitted_use_scop` | `candidate` | `NORMALIZATION_GAP` | **VALID** |
| `e6060134` | Migrate Ea To Microsoft Cust... | Month | `has_stage_duration` | `has_stage_duration` | `rejected` | `BENCHMARK_FALSE_POSITIVE` | **SCHEMA_FRAGMENT** |
| `e67cba9e` | Mcaps Msft Gsa Commercial Su... | User | `has_permitted_use_scop` | `has_permitted_use_scop` | `candidate` | `NORMALIZATION_GAP` | **VALID** |
| `efb4232b` | Mcaps Msft Gsa Commercial Su... | Customers | `has_permitted_use_scop` | `has_permitted_use_scop` | `candidate` | `NORMALIZATION_GAP` | **VALID** |
| `f5badc39` | Migrate Ea To Microsoft Cust... | MeterCategory | `has_stage_duration` | `has_col3` | `candidate` | `BENCHMARK_FALSE_POSITIVE` | **SCHEMA_FRAGMENT** |
| `fd80943c` | Mcaps Msft Gsa Commercial Su... | Parties | `must_be_in_writing` | `must_be_in_writing` | `missing` | `ENTAILMENT_BLOCKED` | **NON_ENTAILED** |
| `fe245df0` | Microsoft Partner Agreement ... | Microsoft | `has_permitted_use_scop` | `has_permitted_use_scop` | `candidate` | `NORMALIZATION_GAP` | **VALID** |
| `fecacc6e` | Mcaps Msft Gsa Commercial Su... | Customers | `has_permitted_use_scop` | `has_permitted_use_scop` | `candidate` | `NORMALIZATION_GAP` | **VALID** |
