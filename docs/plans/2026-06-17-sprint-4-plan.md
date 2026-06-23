# Sprint 4 Plan — 3 New Categories (NO SCRAPING YET)

## Goal
Add 3 new categories to silver layer. Pure category-focused (per user scope).
Each category: 50 top offers from MTOP → enrich with Decodo SU → cross-walk to Rakumart.

## Categories + CN queries

### 1. organization_deep — expand beyond current 5
**Why**: current organization = 5 offers (smallest category). Need breadth.
**Queries (4)**:
- `化妆品收纳` (cosmetics organizer) — narrow, high-intent
- `首饰收纳盒` (jewelry organizer) — narrow, high-margin
- `衣柜收纳` (closet organizer) — broad
- `厨房收纳` (kitchen organizer) — broad
**Expected**: 200+ MTOP results → top 50

### 2. flashlight — NEW category
**Why**: high-margin, simple product, good for cross-walk testing.
**Queries (3)**:
- `手电筒` (flashlight) — broad, exact term
- `LED强光手电筒` (LED bright flashlight) — specific
- `头灯` (headlamp) — variant
**Expected**: 150+ MTOP results → top 50

### 3. webcam — NEW category
**Why**: growing market, B2B potential for security companies.
**Queries (3)**:
- `摄像头` (camera/webcam) — broad
- `监控摄像头` (surveillance camera) — specific
- `网络摄像机` (IP camera) — specific
**Expected**: 150+ MTOP results → top 50

## Pipeline estimate

```
Stage 1: MTOP (free, fast)     10 queries × 50 results = 500 candidates
Stage 2: SU detail ($0.005/each) 150 offers × $0.005 = $0.75
Stage 3: Rakumart cross-walk (free) 150 × ~10s = 25 min
Stage 4: Silver + Gold rebuild (free) ~30s
Total time: ~30 min
Total cost: $0.75
```

## Decodo SU cost analysis

- Current: 206 enriched offers, ~$1.03 spent
- After Sprint 4: +150 enriched = 356 total, ~$1.78 spent
- Still under $2. Budget OK.

## Quality targets

- Cross-walk precision: maintain ≥95% (currently 96.6%)
- Match rate: ≥85% per category (currently 92% overall)
- New suppliers per category: ≥30 (not 1 supplier dominating)
- HIGH opportunities per category: ≥10

## Risks

- Webcam may have many "out of stock" or "login required" pages on Rakumart
- Flashlight may overlap with "drill" (handheld power tools)
- Organization deep may match existing 5 offers (dedup needed)

## Mitigation

- Use bronze_to_silver.py dedup logic (offer_id unique key)
- Cross-check category by MTOP query filename
- If overlap > 30%, narrow queries

## Files needed

- `scripts/run_pipeline.py` — already supports --category, --queries, --top-n
- No new scripts needed
- Update `data/_manifest.json` after run

## Cost-conscious execution

1. Run MTOP first (free) — see actual result counts
2. If top-50 per category, that's 150 candidates → $0.75 SU
3. If under 30/category, expand queries before SU spend
4. Cache MTOP results in bronze — can re-run later
