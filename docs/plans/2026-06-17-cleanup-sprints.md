/usr/bin/bash: warning: setlocale: LC_ALL: cannot change locale (pt_BR.UTF-8)
/usr/bin/bash: warning: setlocale: LC_ALL: cannot change locale (pt_BR.UTF-8)
# Architecture Cleanup & Hardening — Sprint Plan

> **For Hermes:** Plan mode output. Do NOT execute — save to docs/plans/ and report.

**Goal:** Clean wasted data and scripts, populate empty bronze layer, validate architecture with a new 5th category, improve cross-walk quality. 5 sprints, ~10-15 hours total.

**Architecture (unchanged):** Bronze (raw) → Silver (joined) → Gold (ranked)

**Tech Stack:** Python 3.11, urllib (no extra deps), Decodo SU, MTOP, Rakumart

**Last updated:** 2026-06-17

---

## State Audit (before sprints)

```
DATA WASTE:
  Legacy data files: 11 files, 332 KB
    baiyite_line.json, baiyite_line_enriched.json
    youyazi_line.json, youyazi_line_enriched.json
    socks_category.json, socks_top15.json, socks_top15_enriched.json
    drill_category.json, drill_top15.json, drill_top15_enriched.json
    mtop_validation_report.json
  Top 15 full files (duplicated): drill_full.json, socks_full.json  (34 KB)
  Big stale files (670+605+95 KB): strategy_matrix_results, trending_products, decodo_scrape_factory_rank
  Research artifacts (early tests): chinese_tools_research.json, cifnews_article_1688_selection.json, etc.

CODE WASTE:
  Orphaned scripts (in /tmp/): enrich_drill.py, enrich_50_socks.py, enrich_50_drill.py
  Overlapping scripts:
    strategy_matrix.py (11 KB) — comparison results saved
    test_3_categories.py (7 KB) — early exploration
    validate_mtop.py (10 KB) — validation
    → these likely overlap; consolidate

ARCHITECTURE GAPS:
  bronze/mtop: 0 files
  bronze/su_detail: 0 files
  bronze/rakumart: 0 files
  → all migration was LEGACY (no raw snapshots saved)
  → manifest validation: none
  → bronze save: no helper script
```

---

## Sprint 1: Data + Scripts Cleanup (2 hours)

**Goal:** Remove redundant data, consolidate overlapping scripts, archive orphans.

### Task 1.1: Archive legacy case study files (15 min)

**Files to move** (not delete — keep for historical reference):
- `data/baiyite_line.json`
- `data/baiyite_line_enriched.json`
- `data/youyazi_line.json`
- `data/youyazi_line_enriched.json`
- `data/socks_category.json`
- `data/socks_top15.json`
- `data/socks_top15_enriched.json`
- `data/drill_category.json`
- `data/drill_top15.json`
- `data/drill_top15_enriched.json`
- `data/socks_full.json` (top-15 full, redundant)
- `data/drill_full.json` (top-15 full, redundant)
- `data/mtop_validation_report.json`

**Action:**
```bash
mkdir -p /mnt/ssd/1688-only/data/_archive/legacy_2026_06_17
mv [files above] /mnt/ssd/1688-only/data/_archive/legacy_2026_06_17/
echo "Files preserved in _archive/. Silver layer is single source of truth."
```

**Verify:** `ls data/*.json` shows only `_manifest.json` and the 4 `*_full*.json` files used by `bronze_to_silver.py --migrate-legacy`.

**Note:** Keep `baiyite_full_line.json`, `youyazi_full_line.json`, `socks_full_50.json`, `drill_full_50.json` — these are the LEGACY migration source.

### Task 1.2: Compress/remove big stale research files (10 min)

**Files to inspect** (decide based on content):
- `strategy_matrix_results.json` (670 KB) — likely one-time comparison output
- `trending_products.json` (605 KB) — likely one-time scrape
- `decodo_scrape_factory_rank.json` (95 KB) — likely one-time scrape
- `decodo_scrape_best_seller.json` (29 KB) — likely one-time scrape
- `decodo_scrape_ranking_pages.json` (55 KB) — likely one-time scrape
- `decodo_scrape_response.json` (25 KB) — likely one-time scrape
- `trending_offer_ids.json` (18 KB) — likely one-time scrape
- `crawl_k15_results.json` (8 KB) — early K15 exploration
- `chinese_tools_research.json` (3 KB) — research notes
- `cifnews_article_1688_selection.json` (60 KB) — scraped article
- `mtop_3category_test.json` (61 KB) — early MTOP test
- `mtop_k15_*.json` (3 files, ~119 KB total) — K15 mics exploration
- `onebound_test_response.json` (0.6 KB) — OneBound API test

**Action:**
```bash
# Inspect first — quick check
for f in strategy_matrix_results.json trending_products.json decodo_scrape_*.json; do
    echo "=== $f ==="
    python3 -c "import json; d=json.load(open('data/$f')); print('keys:', list(d.keys())[:5])"
done
```

**Decision matrix:**
| If file is... | Action |
|---------------|--------|
| One-time test result | Move to `_archive/legacy_2026_06_17/` |
| Still referenced by a script | Keep, but compress |
| Truly orphaned | Delete |

**Verify:** Run `git status` to see removed files. `du -sh data/` should drop significantly.

### Task 1.3: Consolidate validation scripts (30 min)

**Files:**
- `scripts/strategy_matrix.py` (11 KB)
- `scripts/test_3_categories.py` (7 KB)
- `scripts/validate_mtop.py` (10 KB)

**Analysis steps:**
1. Read each script's docstring/header
2. Identify overlapping functionality
3. Merge into a single `scripts/validate_pipeline.py`

**Action (template):**
```python
# scripts/validate_pipeline.py — consolidates 3 old scripts
"""
Validate the 4-stage pipeline end-to-end.
Replaces: strategy_matrix.py, test_3_categories.py, validate_mtop.py
"""
import sys, json
from pathlib import Path

def validate_mtop_connectivity():
    """Test MTOP client returns results for known query."""
    ...

def validate_su_enrichment():
    """Test SU detail page returns subject/company."""
    ...

def validate_rakumart_search():
    """Test Rakumart search returns items."""
    ...

def validate_end_to_end(category: str, top_n: int = 5):
    """Run full pipeline on one category."""
    ...

if __name__ == '__main__':
    cmd = sys.argv[1] if len(sys.argv) > 1 else 'all'
    # dispatch
```

**Archive old scripts:**
```bash
mkdir -p /mnt/ssd/1688-only/scripts/_archive/legacy_2026_06_17
mv scripts/strategy_matrix.py scripts/test_3_categories.py scripts/validate_mtop.py scripts/_archive/legacy_2026_06_17/
```

**Verify:** `python3 scripts/validate_pipeline.py mtop` returns OK status.

### Task 1.4: Archive orphaned /tmp/ scripts (5 min)

**Files:**
- `/tmp/enrich_drill.py`
- `/tmp/enrich_50_socks.py`
- `/tmp/enrich_50_drill.py`

**Action:**
```bash
mkdir -p /mnt/ssd/1688-only/scripts/_archive/legacy_2026_06_17
mv /tmp/enrich_*.py /mnt/ssd/1688-only/scripts/_archive/legacy_2026_06_17/
```

**Note:** The enrichment pattern is now in `scripts/bronze_to_silver.py` (legacy mode) and ready to be promoted in Sprint 2.

### Task 1.5: Update docs to reflect cleanup (15 min)

**Files:**
- `data/README.md` — add note about `_archive/` directory
- `docs/SESSION-HANDOVER.md` — update §6 file map (remove archived)
- `data/_manifest.json` — regenerate after cleanup

**Verify:** `data/_manifest.json` total counts unchanged (silver is unchanged), but file_count by layer is updated.

---

## Sprint 2: Populate Bronze Layer (3 hours)

**Goal:** Save raw snapshots to bronze/ on every pipeline run. End-to-end works with full lineage.

### Task 2.1: Create bronze save helper (30 min)

**New file:** `scripts/save_bronze.py`

```python
#!/usr/bin/env python3
"""
save_bronze.py — Save raw snapshots to bronze/ layer.

Usage:
  python3 scripts/save_bronze.py mtop '{"data": ...}' 沙滩巾夹 --page 1
  python3 scripts/save_bronze.py su_detail "<html>..." 641931920298
  python3 scripts/save_bronze.py rakumart '{"items": ...}' meias 1688 --page 1
"""
import json, sys
from pathlib import Path
from datetime import datetime

BRONZE = Path(__file__).parent.parent / 'data' / 'bronze'

def save_mtop(query: str, page: int, data: dict):
    date = datetime.now().strftime('%Y-%m-%d')
    safe_q = query.replace('/', '_').replace(' ', '_')
    out = BRONZE / 'mtop' / f'{date}_{safe_q}_p{page}.json'
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding='utf-8')
    return str(out.relative_to(out.parent.parent.parent))

def save_su_detail(offer_id: int, html: str):
    date = datetime.now().strftime('%Y-%m-%d')
    out = BRONZE / 'su_detail' / f'{date}_{offer_id}.html'
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(html, encoding='utf-8')
    return str(out.relative_to(out.parent.parent.parent))

def save_rakumart(query: str, source: str, page: int, data: dict):
    date = datetime.now().strftime('%Y-%m-%d')
    safe_q = query.replace('/', '_').replace(' ', '_')
    out = BRONZE / 'rakumart' / f'{date}_{safe_q}_{source}_p{page}.json'
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding='utf-8')
    return str(out.relative_to(out.parent.parent.parent))

if __name__ == '__main__':
    layer = sys.argv[1]
    if layer == 'mtop':
        data = json.loads(sys.argv[2])
        query = sys.argv[3]
        page = int(sys.argv[4]) if len(sys.argv) > 4 else 1
        print(save_mtop(query, page, data))
    elif layer == 'su_detail':
        html = sys.argv[2]
        offer_id = int(sys.argv[3])
        print(save_su_detail(offer_id, html))
    elif layer == 'rakumart':
        data = json.loads(sys.argv[2])
        query = sys.argv[3]
        source = sys.argv[4]
        page = int(sys.argv[5]) if len(sys.argv) > 5 else 1
        print(save_rakumart(query, source, page, data))
```

### Task 2.2: Modify scrape_1688_mtop.py to save bronze (15 min)

**Modify:** `scripts/scrape_1688_mtop.py`

Add at the end of `search_by_text()`:
```python
# Save bronze snapshot
from save_bronze import save_mtop
save_mtop(query, page, raw_response)
```

### Task 2.3: Create unified pipeline runner (1 hour)

**New file:** `scripts/run_pipeline.py`

```python
#!/usr/bin/env python3
"""
run_pipeline.py — Run full pipeline for a category, saving bronze + silver + gold.

Usage:
  python3 scripts/run_pipeline.py --category socks --queries 袜子,棉袜 --top-n 50

This is the production pipeline. Saves bronze snapshots, then runs bronze_to_silver,
then silver_to_gold. Idempotent: re-run rebuilds everything.
"""
import argparse, json, sys, time
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from save_bronze import save_mtop, save_su_detail, save_rakumart
from bronze_to_silver import build_silver_offer, migrate_legacy

# Import MTOP, SU, Rakumart helpers from existing modules
sys.path.insert(0, '/tmp/scrapers-test/ai-reverse/1688')
from client import Alibaba1688Client

SU_PASS = 'PW_17560792063f932882c0843ad92c0ed69'
SU_USER = 'U0000434457'
PROXY = f'http://{SU_USER}:{SU_PASS}@unblock.decodo.com:60000'

sys.path.insert(0, '/mnt/ssd/1688-intel/scripts/arbitlens')
from scrape_rakumart_br import search_rakumart_br

def run(category, queries, top_n, run_mtop=True, run_su=True, run_rak=True):
    """Full pipeline. Each stage saves bronze, then triggers silver/gold."""
    all_offers = []
    
    if run_mtop:
        c = Alibaba1688Client()
        c.session.login()
        for q in queries:
            for page in [1, 2]:  # 2 pages = up to 100 products
                resp = c.search_by_text(q, page=page, page_size=50)
                save_mtop(q, page, resp.to_dict() if hasattr(resp, 'to_dict') else resp.__dict__)
                items = resp.data['data']['OFFER']['items']
                all_offers.extend(items)
        # Dedup by offerId, take top_n by booked
        seen = set()
        unique = []
        for o in sorted(all_offers, key=lambda x: -x.get('bookedCount', 0)):
            if o['offerId'] not in seen:
                seen.add(o['offerId'])
                unique.append(o)
        top_offers = unique[:top_n]
    
    if run_su:
        import urllib.request, ssl
        ctx = ssl.create_default_context()
        ctx.check_hostname = False; ctx.verify_mode = ssl.CERT_NONE
        opener = urllib.request.build_opener(urllib.request.ProxyHandler({'http': PROXY, 'https': PROXY}))
        for o in top_offers:
            oid = o['offerId']
            req = urllib.request.Request(f'https://detail.1688.com/offer/{oid}.html',
                                          headers={'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'})
            req.add_header('X-SU-Geo', 'China')
            req.add_header('X-SU-Locale', 'zh-cn')
            try:
                body = opener.open(req, timeout=60).read().decode('utf-8', errors='ignore')
                if len(body) > 10000:
                    save_su_detail(oid, body)
            except Exception as e:
                print(f'  SU fail {oid}: {e}')
            time.sleep(3)
    
    if run_rak:
        # Cross-walk each top offer to Rakumart
        for o in top_offers:
            title_words = o['title'][:20]
            results = search_rakumart_br(title_words, source='1688', page=1)
            save_rakumart(title_words, '1688', 1, {'items': [r.__dict__ for r in results]})
    
    # Build silver
    silver_dir = Path('/mnt/ssd/1688-only/data/silver/offers')
    for o in top_offers:
        silver = build_silver_offer(o['offerId'], category)
        out = silver_dir / f'{o["offerId"]}.json'
        out.write_text(json.dumps(silver, ensure_ascii=False, indent=2), encoding='utf-8')
    
    # Build gold
    from silver_to_gold import build_gold_rankings, build_gold_by_category
    build_gold_rankings()
    build_gold_by_category()

if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('--category', required=True)
    p.add_argument('--queries', required=True, help='Comma-separated CN queries')
    p.add_argument('--top-n', type=int, default=50)
    p.add_argument('--no-mtop', action='store_true')
    p.add_argument('--no-su', action='store_true')
    p.add_argument('--no-rak', action='store_true')
    args = p.parse_args()
    
    queries = [q.strip() for q in args.queries.split(',')]
    run(args.category, queries, args.top_n,
        run_mtop=not args.no_mtop, run_su=not args.no_su, run_rak=not args.no_rak)
```

### Task 2.4: Run a test category end-to-end (45 min)

**Test:**
```bash
python3 scripts/run_pipeline.py --category organization --queries 收纳,收纳盒 --top-n 30
```

**Verify:**
- `data/bronze/mtop/` has new files
- `data/bronze/su_detail/` has new HTML files
- `data/bronze/rakumart/` has new files
- `data/silver/offers/` has new offer files
- `data/gold/by_category/organization.json` exists
- `data/_manifest.json` total counts increased

**Expected cost:** 30 × $0.005 = $0.15 for SU enrichment

---

## Sprint 3: Manifest Validation & Auto-sync (1.5 hours)

**Goal:** Single source of truth for data lineage. Auto-update on every pipeline run.

### Task 3.1: Create manifest builder script (45 min)

**New file:** `scripts/build_manifest.py`

```python
#!/usr/bin/env python3
"""
build_manifest.py — Build _manifest.json from current state of bronze/silver/gold.

Usage:
  python3 scripts/build_manifest.py    # rebuilds manifest from scratch

Run after every bronze_to_silver or silver_to_gold execution.
"""
import json
from pathlib import Path
from datetime import datetime

DATA = Path(__file__).parent.parent / 'data'

def count_files(path):
    return sum(1 for _ in Path(path).rglob('*.json') if _.is_file())

def build():
    bronze = DATA / 'bronze'
    silver = DATA / 'silver'
    gold = DATA / 'gold'
    
    # Read silver offers to compute stats
    offers = list((silver / 'offers').glob('*.json'))
    categories = {}
    rakumart_matched = 0
    enriched = 0
    for f in offers:
        o = json.loads(f.read_text())
        cat = o.get('category', 'unknown')
        categories.setdefault(cat, {'offers': 0, 'shops': set(), 'matched': 0, 'enriched': 0})
        categories[cat]['offers'] += 1
        categories[cat]['shops'].add(o.get('mtop', {}).get('shop', 'unknown'))
        if o.get('rakumart') and o['rakumart'].get('match_score', 0) > 50:
            categories[cat]['matched'] += 1
            rakumart_matched += 1
        if o.get('su_detail') and o['su_detail'].get('is_live'):
            categories[cat]['enriched'] += 1
            enriched += 1
    
    # Convert sets to lists for JSON
    for c in categories.values():
        c['unique_shops'] = len(c['shops'])
        del c['shops']
    
    manifest = {
        'generated_at': datetime.now().isoformat() + 'Z',
        'architecture': 'bronze / silver / gold',
        'layers': {
            'bronze': {
                'mtop_files': count_files(bronze / 'mtop'),
                'su_detail_files': count_files(bronze / 'su_detail'),
                'rakumart_files': count_files(bronze / 'rakumart'),
            },
            'silver': {
                'offers': len(offers),
                'suppliers': count_files(silver / 'suppliers'),
                'categories': count_files(silver / 'categories'),
            },
            'gold': {
                'by_category': count_files(gold / 'by_category'),
                'rankings': count_files(gold / 'rankings'),
                'to_source': count_files(gold / 'to_source'),
            },
        },
        'totals': {
            'silver_offers': len(offers),
            'rakumart_matched': rakumart_matched,
            'enriched': enriched,
            'match_rate_pct': round(rakumart_matched / len(offers) * 100, 1) if offers else 0,
            'enrichment_rate_pct': round(enriched / len(offers) * 100, 1) if offers else 0,
        },
        'by_category': categories,
    }
    
    out = DATA / '_manifest.json'
    out.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding='utf-8')
    print(f'Wrote {out}')
    print(f'  {len(offers)} silver offers, {enriched} enriched ({manifest["totals"]["enrichment_rate_pct"]}%), {rakumart_matched} matched ({manifest["totals"]["match_rate_pct"]}%)')

if __name__ == '__main__':
    build()
```

### Task 3.2: Auto-update manifest in transformation scripts (30 min)

**Modify:** `scripts/bronze_to_silver.py` — add at end of main():
```python
from build_manifest import build
build()  # Refresh manifest
```

**Modify:** `scripts/silver_to_gold.py` — add at end of main():
```python
from build_manifest import build
build()  # Refresh manifest
```

### Task 3.3: Add consistency check (15 min)

**New file:** `scripts/validate_manifest.py`

```python
#!/usr/bin/env python3
"""
validate_manifest.py — Check manifest consistency.

Returns non-zero exit code if drift detected.
"""
import json, sys
from pathlib import Path

DATA = Path(__file__).parent.parent / 'data'

def validate():
    manifest = json.loads((DATA / '_manifest.json').read_text())
    errors = []
    
    # Silver offers count
    silver_offers = list((DATA / 'silver/offers').glob('*.json'))
    if manifest['totals']['silver_offers'] != len(silver_offers):
        errors.append(f'silver_offers: manifest={manifest["totals"]["silver_offers"]} actual={len(silver_offers)}')
    
    # Suppliers count
    suppliers = list((DATA / 'silver/suppliers').glob('*.json'))
    if manifest['layers']['silver']['suppliers'] != len(suppliers):
        errors.append(f'suppliers: manifest={manifest["layers"]["silver"]["suppliers"]} actual={len(suppliers)}')
    
    # Categories coverage
    cat_files = list((DATA / 'silver/categories').glob('*.json'))
    cat_slugs = {json.loads(f.read_text())['category_slug'] for f in cat_files}
    manifest_cats = set(manifest['by_category'].keys())
    if cat_slugs != manifest_cats:
        errors.append(f'categories: manifest={manifest_cats} actual={cat_slugs}')
    
    if errors:
        for e in errors:
            print(f'❌ {e}')
        sys.exit(1)
    print('✓ Manifest is consistent')

if __name__ == '__main__':
    validate()
```

**Verify:** Run after any pipeline change. Should pass.

---

## Sprint 4: 3 New Categories End-to-End Test (2 hours)

**Goal:** Validate architecture works for 3 new categories. Populates bronze layer with real data.

**Categories (user selected 2026-06-17):**
- organization (收纳) — margin: HIGH (fragmented market)
- flashlight (手电筒) — margin: HIGH (niche tool market)
- webcams (摄像头) — margin: MEDIUM-HIGH (commodity but tech)

**Total SU details:** 3 × 50 = 150 × $0.005 = **$0.75**

### Task 4.1: Queries for each category (10 min)

**Organization (收纳):**
- Broad: `收纳`, `收纳盒`, `收纳箱`
- Specific: `桌面收纳`, `衣柜收纳`

**Flashlight (手电筒):**
- Broad: `手电筒`, `LED手电`, `强光手电筒`
- Specific: `充电手电筒`, `户外手电筒`

**Webcams (摄像头):**
- Broad: `摄像头`, `监控摄像头`, `无线摄像头`
- Specific: `WiFi摄像头`, `室外摄像头`

### Task 4.2: Run 3 pipelines in parallel (45 min)

```bash
# In 3 separate background processes
python3 scripts/run_pipeline.py --category organization --queries 收纳,收纳盒,收纳箱,桌面收纳,衣柜收纳 --top-n 50 &
python3 scripts/run_pipeline.py --category flashlight --queries 手电筒,LED手电,强光手电筒,充电手电筒,户外手电筒 --top-n 50 &
python3 scripts/run_pipeline.py --category webcams --queries 摄像头,监控摄像头,无线摄像头,WiFi摄像头,室外摄像头 --top-n 50 &
wait
```

**Verify:**
- Bronze layer populated (~15 mtop files + 150 su_detail + 15-30 rakumart)
- Silver has 150 new offers (50 per category)
- Gold has 3 new category files with rankings
- Manifest total counts: silver_offers 129 → 279, categories 4 → 7

### Task 4.3: Cross-walk + analyze (30 min)

```bash
python3 scripts/silver_to_gold.py
python3 scripts/build_manifest.py
cat data/gold/to_source/priority.json  # see if new opportunities appeared
```

**Verify:** `data/gold/rankings/ranked_by_margin.json` has 279 offers (129 + 150).

**Output:** Update `docs/SESSION-HANDOVER.md` §6 with 3 new case studies.

---

## Sprint 5: Improve Cross-Walk Quality (3 hours)

**Goal:** Reduce false-positive matches in cross-walk. Add price range and shop-name filters.

### Task 5.1: Add price range filter (45 min)

**Modify:** `scripts/silver_to_gold.py`

Add filter before cross-walk output:
```python
# Reject matches where Rakumart price is <2x source price (likely wrong product)
if rm.get('price_brl', 0) < cny * CNY_TO_BRL * 2:
    match_score = 0  # too cheap, probably different product
```

**Verify:** Recalculate gold rankings. Some "matches" will drop to 0%.

### Task 5.2: Add shop-name boost (30 min)

**Modify:** `scripts/silver_to_gold.py`

```python
# Boost match score if Rakumart shop mentions source shop name
if rm.get('title_pt') and shop.lower() in rm.get('title_pt', '').lower():
    match_score = min(100, match_score + 15)
```

### Task 5.3: Add cross-walk evaluation script (1 hour)

**New file:** `scripts/eval_cross_walk.py`

Sample 20 silver offers, manually check Rakumart matches, compute precision.

```python
#!/usr/bin/env python3
"""
eval_cross_walk.py — Manual evaluation of cross-walk quality.

Usage:
  python3 scripts/eval_cross_walk.py --sample 20

Loads 20 random silver offers with Rakumart match >50%, prints side-by-side,
user manually marks TP/FP. Saves results.
"""
import json, random, argparse
from pathlib import Path

SILVER = Path('/mnt/ssd/1688-only/data/silver/offers')

def main():
    p = argparse.ArgumentParser()
    p.add_argument('--sample', type=int, default=20)
    args = p.parse_args()
    
    offers = []
    for f in SILVER.glob('*.json'):
        o = json.loads(f.read_text())
        if o.get('rakumart') and o['rakumart'].get('match_score', 0) > 50:
            offers.append(o)
    
    sample = random.sample(offers, min(args.sample, len(offers)))
    
    for i, o in enumerate(sample, 1):
        print(f'\n[{i}/{len(sample)}] Offer {o["offer_id"]} ({o["category"]})')
        print(f'  CN: {o["mtop"]["title"][:80]}')
        print(f'  CNY: ¥{o["mtop"]["price_cny"]}')
        if o.get('rakumart'):
            print(f'  PT: {o["rakumart"]["title_pt"][:80] if o["rakumart"]["title_pt"] else "N/A"}')
            print(f'  BRL: R${o["rakumart"]["price_brl"]}')
            print(f'  Match score: {o["rakumart"]["match_score"]}%')
        print(f'  Verdict? (TP/FP/SKIP): ', end='')

if __name__ == '__main__':
    main()
```

### Task 5.4: Document findings (15 min)

**New file:** `data/_cross_walk_eval.md`

Document precision, common false positive patterns, recommended thresholds.

---

## Sprint Timeline & Dependencies

```
Sprint 1 (Cleanup)         [2h]     No deps
Sprint 2 (Bronze layer)    [3h]     After 1
Sprint 3 (Manifest)        [1.5h]   After 2
Sprint 4 (3 categories)    [2h]     After 3
Sprint 5 (Cross-walk)      [3h]     After 4

Total: ~11 hours = 4 sessions at 2.5h each
```

---

## Verification Checklist (after all sprints)

- [ ] `data/_archive/` has legacy files preserved
- [ ] No orphan files in `/tmp/`
- [ ] `data/bronze/` has at least 1 set of snapshots per source
- [ ] `data/silver/` has 5+ categories (129+ offers)
- [ ] `data/gold/` has rankings + priority list
- [ ] `scripts/` has 5 production scripts + 1 validation script
- [ ] `data/_manifest.json` auto-updates on every run
- [ ] Cross-walk precision documented (precision ≥ 80%)
- [ ] `docs/SESSION-HANDOVER.md` updated with new category

---

## Open Questions (RESOLVED 2026-06-17)

1. **Categories for Sprint 4:** organization (收纳), flashlight (手电筒), webcams (摄像头) — 3 categories in parallel
2. **Big stale files:** ARCHIVE to `data/_archive/legacy_2026_06_17/`
3. **Cross-walk target:** 80% precision, 60% recall — measure in Sprint 5

---

## Cost Estimate (updated)

| Sprint | SU Details | Cost |
|--------|-----------|------|
| 1 (cleanup) | 0 | $0.00 |
| 2 (bronze) | 0 | $0.00 (just script work) |
| 3 (manifest) | 0 | $0.00 |
| 4 (3 categories) | 150 | $0.75 |
| 5 (cross-walk) | 0 | $0.00 (just code) |
| **TOTAL** | **150** | **$0.75** |

---

## Plan Status

- [x] Plan written
- [ ] Sprint 1 executed
- [ ] Sprint 2 executed
- [ ] Sprint 3 executed
- [ ] Sprint 4 executed
- [ ] Sprint 5 executed