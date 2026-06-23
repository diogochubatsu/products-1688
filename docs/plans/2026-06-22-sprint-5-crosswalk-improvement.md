# Sprint 5 follow-up: Crosswalk Improvement (2026-06-22)

## Goal
Improve match rate on socks/underwear (was 53-61%).

## Method
Ran crosswalk with --source alibaba on 81 unmatched, then --source taobao on remaining 22.

## Outcome

### Before vs After

| Category | Before | After | Change |
|----------|-------:|------:|-------:|
| socks | 61% (46/76) | **100% (76/76)** | +39pp |
| underwear | 53% (39/74) | 91% (67/74) | +38pp |
| beach_clip | 93% (55/59) | 93% (55/59) | unchanged |
| drill | 94% (47/50) | 94% (47/50) | unchanged |
| organization | 73% (11/15) | 87% (13/15) | +14pp |
| webcam | 60% (6/10) | 60% (6/10) | unchanged |
| flashlight | 90% (9/10) | 90% (9/10) | unchanged |
| **TOTAL** | **72.4% (213/294)** | **92.9% (273/294)** | **+20.5pp** |

### Source effectiveness (for unmatched)
- --source 1688: 76% rate (Sprint 4 v2 baseline)
- --source alibaba: 73% rate (this run) — DIFFERENT coverage than 1688
- --source taobao: 5% rate (this run) — weak

The 3 sources hit DIFFERENT Rakumart products. Combining all 3 gives much better coverage.

### Remaining 21 unmatched
Mostly niche/specialty products Rakumart doesn't carry:
- 6 specialty underwear (sports bras, silicone, teen)
- 4 specialty webcams (automotive, lightbulb, sport)
- 3 specialty drills (drill bits, mini tools)
- 3 beach_clip (kids toys)
- 2 specialty organization
- 1 flashlight (mini clip-on)
- 2 misc

**Conclusion: 21/294 = 7.1% unmatched is acceptable.** These are products Rakumart likely doesn't carry.

## Files
- No new scripts — used existing crosswalk_remaining.py
- `data/silver/offers/*.json` — 273 have rakumart block now
- `data/_manifest.json` — updated
