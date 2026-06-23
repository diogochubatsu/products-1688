# Sprint 4 Tiny — Complete (2026-06-21)

## Outcome
- **+30 silver offers** (212 → 242)
- **+2 new categories**: flashlight (10), webcam (10)
- **organization** grew: 5 → 15
- **100% SU enrichment success** (30/30)
- **$0.15 cost** (Decodo SU)
- **~5 min runtime**

## New queries added
- `手电筒` → flashlight (10 offers)
- `摄像头` → webcam (10 offers)
- `化妆品收纳` → organization (10 new)

## Key learnings

1. **Decodo SU is reliable** — 100% success on 30 calls, ~3s/page
2. **SU + Headless + Markdown** works (tested on 1 page, 46s, returned rich markdown)
3. **Flashlight + webcam have 0 Rakumart matches** — these products may be on Rakumart under different terminology, or not at all

## Next steps (optional)
1. Crosswalk flashlight + webcam via alibaba (free, ~5 min)
2. Test SU + Headless + Markdown on flashlight pages for richer data
3. Scale up Sprint 4 (run another 30-60 candidates)
4. Stop here — save state, 7 categories

## Files
- `scripts/sprint4_tiny.py` — tiny runner
- `scripts/build_silver_from_bronze.py` — patched with flashlight + webcam mapping
- `data/bronze/mtop/2026-06-21_*.json` — 3 new MTOP responses
- `data/bronze/su_detail/2026-06-21_*.html` — 30 new SU detail HTML files
