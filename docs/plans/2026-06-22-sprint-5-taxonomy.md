# Sprint 5 — Deep Taxonomy (2026-06-22)

## Goal
Shift from flat categories to N1-N4 deep taxonomy. Keep crosswalk as bonus.

## Outcome

### Step 1: Taxonomy design ✓
- **9 N1 categories**: 服装鞋帽, 家居日用, 户外运动, 五金工具, 电子数码, 美妆护肤, 母婴用品, 宠物用品, 文具办公
- **14 N2 subcategories**
- **16 N3 sub-subcategories**
- **35 N4 leaf categories**
- File: `data/taxonomy/n1_n4.json`

### Step 2: Re-tag 294 offers ✓
- All existing offers tagged with N1-N4 paths
- N1 distribution (5 covered):
  - 服装鞋帽: 150 (51%)
  - 户外运动: 59 (20%)
  - 五金工具: 50 (17%)
  - 电子数码: 20 (7%)
  - 家居日用: 15 (5%)
- 18 N4 leaves have data
- 4 N1 still empty: 美妆护肤, 母婴用品, 宠物用品, 文具办公

### Step 3: Add Beauty N1 ❌ (rate-limited)
- MTOP search succeeded (20 candidates found)
- SU enrichment failed: HTTP 429 Too Many Requests from Decodo SU
- Sprint 4 v2 had just completed 60 SU calls (~30 min earlier)
- Decodo SU is heavily rate-limited after bursts

## Key findings

1. **Taxonomy depth matters**: 35 N4 leaves give much more granular search/filter
2. **PT translations matter**: every N1/N2/N3/N4 has a PT name for BR marketplace relevance
3. **Decodo SU rate-limit**: after 60+ calls in 10 min, hits 429 for ~30 min
4. **MTOP works fine**: 20/20 candidates picked without rate limit

## Closing v2 status

| Dimension | Status |
|-----------|--------|
| Data (294 offers) | ✓ solid for current scope |
| Taxonomy depth (4 levels, 9 N1) | ✓ done |
| Quality (97.9% enriched, 72.4% matched) | ✓ good |
| Frontend | ✗ out of scope (data lake only) |
| 4 empty N1 (beauty/kids/pet/stationery) | ⚠️ pending scrape |

## What's pending to fully close

1. **Add 30+ offers for each empty N1** (4 cats × 30 = 120 more, $0.60, ~10 min when not rate-limited)
2. **Wait 30+ min before running new SU batches**
3. **Optional: crosswalk on Beauty to test if it matches Rakumart**

## Files
- `data/taxonomy/n1_n4.json` — taxonomy skeleton
- `scripts/sprint5_n1_beauty.py` — Beauty scraper (rate-limited)
- `data/silver/offers/*.json` — 294 offers with new `taxonomy` field
- `data/_manifest.json` — updated
