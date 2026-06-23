# Data Architecture (Bronze / Silver / Gold)

**Last updated**: 2026-06-17 (post Sprint 1 cleanup)

## Layer Definitions

```
bronze/   = Raw, untouched data from source. Immutable. Auditable.
silver/   = Cleaned, enriched, deduplicated. Joined across sources.
gold/     = Business-ready. Ranked. Filtered. Actionable.
_archive/ = Legacy data, archived 2026-06-17. Not used in production.
```

## Why 3 layers?

- **bronze** lets us re-process without losing original data
- **silver** is the source of truth (1 row per offer)
- **gold** is what we ACT on (sourcing decisions, ML listings)

## Current State (post Sprint 1)

| Layer | Count | Notes |
|-------|-------|-------|
| bronze/mtop | 0 files | Empty (legacy data didn't save raw snapshots) |
| bronze/su_detail | 0 files | Will populate starting next pipeline run |
| bronze/rakumart | 0 files | |
| silver/offers | 129 files | 4 case studies migrated |
| silver/suppliers | 90 files | |
| silver/categories | 4 files | |
| gold/by_category | 4 files | |
| gold/rankings | 1 file | 129 offers ranked by margin |
| gold/to_source | 1 file | 4 actionable items |
| **_archive/legacy_2026_06_17/** | **32 files, 2.3MB** | Archived Sprint 1 |

## Naming Conventions

### Bronze (raw snapshots)
```
bronze/mtop/{YYYY-MM-DD}_{query_slug}_p{page}.json
bronze/su_detail/{YYYY-MM-DD}_{offer_id}.html
bronze/rakumart/{YYYY-MM-DD}_{query_slug}_{source}_p{page}.json
```

### Silver (cleaned, joined)
```
silver/offers/{offer_id}.json              1 file per offer
silver/suppliers/{loginId}.json            1 file per supplier
silver/categories/{category_slug}.json     1 file per category
```

### Gold (business-ready)
```
gold/by_category/{category_slug}.json     top N by margin opportunity
gold/rankings/ranked_by_margin.json       all offers sorted by margin%
gold/to_source/{priority}.json            manually curated for ML listing
```

## Transformations

```
bronze → silver:  scripts/bronze_to_silver.py
silver → gold:    scripts/silver_to_gold.py
manifest:         scripts/build_manifest.py (Sprint 3)
```

Both idempotent and re-runnable.

## Archive Contents (data/_archive/legacy_2026_06_17/)

32 files (2.3 MB), archived Sprint 1 (2026-06-17):

**Case study intermediates (13 files)**:
- baiyite/youyazi: `*_line.json`, `*_line_enriched.json`
- socks/drill: `*_category.json`, `*_top15.json`, `*_top15_enriched.json`, `*_full.json`
- `mtop_validation_report.json` (replaced by `_manifest.json`)

**Stale research/test (14 files)**:
- `strategy_matrix_results.json` (670KB), `trending_products.json` (606KB)
- 4× `decodo_scrape_*.json` (one-time scrape outputs)
- `cifnews_article_1688_selection.json`, `chinese_tools_research.json`
- `crawl_k15_results.json`, 3× `mtop_k15_*.json` (K15 mics case study)
- `mtop_3category_test.json`, `onebound_test_response.json`
- `trending_offer_ids.json`

**Scripts (6 files)**:
- 3 validation scripts (strategy_matrix.py, test_3_categories.py, validate_mtop.py) — replaced by `validate_pipeline.py`
- 3 /tmp/ orphan enrichment scripts (enrich_drill.py, enrich_50_socks.py, enrich_50_drill.py) — pattern now in `bronze_to_silver.py`

**Top 50 intermediates (4 files)**:
- `socks_top50.json`, `socks_top50_enriched.json` (intermediate state, full data in silver/)
- `drill_top50.json`, `drill_top50_enriched.json` (same)

## Recovery

If you need any archived file:
```bash
mv data/_archive/legacy_2026_06_17/{filename} data/
```

If you need to revert Sprint 1 entirely:
```bash
mv data/_archive/legacy_2026_06_17/*.{json,py} data/ scripts/
# Remove scripts/_archive/ if you want
```

## Next Sessions

Sprint 2 will populate bronze by saving raw snapshots in every pipeline run.
Sprint 4 will add 3 new categories (organization, flashlight, webcams).
See `docs/plans/2026-06-17-cleanup-sprints.md` for the full plan.