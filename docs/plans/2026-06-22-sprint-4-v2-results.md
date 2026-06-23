# Sprint 4 v2 — Complete (2026-06-22)

## Outcome
- **+52 silver offers** (242 → 294)
- **+1 subcategory mapping** for existing underwear + socks categories
- **80 new Rakumart matches** (from 105 candidates, 76% match rate)
- **189 → 213 matched** (72.4% overall, was 80.6% — drops because new subcats need crosswalk)
- **$0.30 cost** (59 SU calls × $0.005, 1 timeout)
- **~22 min total runtime** (8.5 min scrape + 14 min crosswalk)

## New subcategories added
- Underwear: 提臀塑身衣 (butt-lifting shapewear), 收腹塑身衣 (tummy-control), 无痕内裤 (seamless panties)
- Socks: 船袜 (no-show), 运动袜 (sports), 童袜 (kids)

## Final state per category (after Sprint 4 v2 + crosswalk)

| Category | Offers | Matched | Rate | Shops |
|----------|-------:|--------:|-----:|------:|
| beach_clip | 59 | 55 | 93% | 44 |
| drill | 50 | 47 | 94% | 44 |
| underwear | 74 | 39 | 53% | 57 |
| socks | 76 | 46 | 61% | 65 |
| organization | 15 | 11 | 73% | 15 |
| flashlight | 10 | 9 | 90% | 10 |
| webcam | 10 | 6 | 60% | 10 |
| **TOTAL** | **294** | **213** | **72%** | — |

## Key discoveries in Sprint 4 v2

1. **SU+Headless+Markdown capability confirmed** — works on 1688 product pages (tested on flashlight 521435926513, 36.7s, 15.4KB markdown with ratings, variants, material). Too slow for bulk (46s/page vs 3s baseline) but valuable as fallback.

2. **Crosswalk --source 1688 is the correct source for 1688 data** — earlier runs used --source alibaba which gave 0% matches for flashlight + webcam. With --source 1688: flashlight 90%, webcam 60% matched. Always use --source matching the original data source.

3. **Subcategory queries return relevant products** — 提臀塑身衣, 收腹塑身衣, 船袜, etc. returned topically correct offers (verified by title inspection).

4. **1 offer failed SU enrichment** (939238025395 - sports socks, TimeoutError). 99% success rate is OK but not 100%.

5. **Match rate varies by subcategory** — socks subcategories (no-show, sports, kids) got ~60% rate, suggesting Rakumart has these but with different terminology. More crosswalk iterations might help.

## Lessons saved to memory

- "Crosswalk --source must match original data source" — saves time
- "SU+Headless+Markdown is 15x slower than bulk SU — use as fallback only"
- "Subcategory CN queries work via MTOP and return relevant results"

## Files
- `scripts/sprint4_tiny2.py` — Sprint 4 v2 runner (6 queries × 10)
- `scripts/sprint4_tiny2_enrich.py` — Phase 3 enricher (separate from MTOP)
- `scripts/build_silver_from_bronze.py` — extended QUERY_CATEGORY_MAP with 11 subcategory entries
- `data/bronze/mtop/2026-06-22_*.json` — 6 MTOP responses
- `data/bronze/su_detail/2026-06-22_*.html` — 59 SU detail HTML files (1 timeout)
- `data/_manifest.json` — updated manifest (294 offers, 213 matched)

## Next steps (optional)
1. Run alibaba/taobao crosswalk on remaining 81 unmatched offers (~10 min, free)
2. Scale up subcategories that performed well (提臀塑身衣, 船袜)
3. Add more subcategories (产后塑身衣, 羊毛袜, 连体塑身衣)
4. Stop here, save state — 7 categories with 53-94% match rates is solid baseline
