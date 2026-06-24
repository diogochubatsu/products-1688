#!/usr/bin/env python3
"""
sprint4_tiny.py — Tiny Sprint 4 runner (3 categories × 10 candidates = 30).

Goal: extend the data lake with 3 new categories at minimal cost.

Phases:
  1. MTOP search (3 queries, 1 page each, size 20)
  2. Pick top 10 by price per category
  3. SU detail enrichment (30 calls × ~3s = ~1.5 min)
  4. Silver + Gold rebuild
  5. Report

Usage:
  python3 scripts/sprint4_tiny.py [--dry-run]

Cost: ~$0.15 (30 SU calls × $0.005)
Time: ~2 minutes
"""
import argparse
import json
import sys
import time
from pathlib import Path

ROOT = Path('/mnt/ssd/1688-only')
sys.path.insert(0, str(ROOT / 'scripts'))

# === Sprint 4 tiny config ===
SPRINT4_QUERIES = {
    'organization_deep': '化妆品收纳',  # cosmetics storage
    'flashlight': '手电筒',              # flashlight
    'webcam': '摄像头',                  # camera/webcam
}

PER_CATEGORY = 10  # tiny batch


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--dry-run', action='store_true',
                    help='Show what would be scraped without actually scraping')
    args = ap.parse_args()

    print('=' * 60)
    print('SPRINT 4 TINY — 3 categories × 10 candidates = 30 SU calls')
    print('=' * 60)
    print(f'Cost: ~$0.15 (30 × $0.005)')
    print(f'Time: ~2 minutes')
    print()

    for cat, query in SPRINT4_QUERIES.items():
        print(f'  {cat:20} query="{query}"')

    print()
    if args.dry_run:
        print('DRY RUN — no scraping performed')
        return

    # Phase 1+2: MTOP + pick top 10 per category
    from scrape_1688_mtop import scrape
    from save_bronze import save_mtop_data

    candidates = []  # list of {category, offer_id, title, price_cny, shop, ...}

    for cat, query in SPRINT4_QUERIES.items():
        print(f'\n[1] MTOP search: {cat} ("{query}")')
        products = scrape(query, pages=1, size=20, save_bronze=True)

        if not products:
            print(f'  WARN: no products returned for {cat}')
            continue

        # Filter & sort: lowest price first (more interesting for sourcing)
        valid = [p for p in products if p.get('offer_id') and p.get('price_cny')]
        valid.sort(key=lambda p: float(p['price_cny']))

        top_n = valid[:PER_CATEGORY]
        print(f'  Found {len(products)}, picked top {len(top_n)} by price')
        for i, p in enumerate(top_n, 1):
            print(f'    {i:2}. {p["offer_id"]} ¥{p["price_cny"]:>7} {p["title"][:50]}')

        for p in top_n:
            candidates.append({'category': cat, **p})

    print(f'\n[1+2] Total candidates: {len(candidates)}')

    # Phase 3: SU enrichment
    print(f'\n[3] SU detail enrichment — {len(candidates)} calls')
    print(f'    Estimated time: ~{len(candidates) * 3}s')

    from save_bronze import save_su_detail
    import urllib.request

    SU_PASS = open('/mnt/ssd/1688-only/.env').read()
    # extract SU_PASS from .env (avoid import)
    for line in SU_PASS.split('\n'):
        if line.startswith('DECODO_SU_PASS='):
            SU_PASS = line.split('=', 1)[1].strip()
        if line.startswith('DECODO_SU_USER='):
            SU_USER = line.split('=', 1)[1].strip()
    SU_PROXY = f'http://{SU_USER}:{SU_PASS}@unblock.decodo.com:60000'

    proxy_handler = urllib.request.ProxyHandler({
        'http': SU_PROXY,
        'https': SU_PROXY,
    })
    opener = urllib.request.build_opener(proxy_handler)

    enriched = 0
    failed = 0
    t0 = time.time()
    for i, c in enumerate(candidates, 1):
        oid = c['offer_id']
        url = f'http://detail.1688.com/offer/{oid}.html'
        try:
            req = urllib.request.Request(url, headers={
                'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36',
                'Accept-Language': 'zh-CN,zh;q=0.9',
            })
            with opener.open(req, timeout=30) as resp:
                body = resp.read().decode('utf-8', errors='ignore')
            if len(body) > 5000 and '1688' in body:
                save_su_detail(oid, body)
                enriched += 1
            else:
                print(f'  [{i}/{len(candidates)}] {oid}: too small ({len(body)} bytes)')
                failed += 1
        except Exception as e:
            print(f'  [{i}/{len(candidates)}] {oid}: FAILED {type(e).__name__}')
            failed += 1
        if i % 5 == 0 or i == len(candidates):
            elapsed = time.time() - t0
            rate = i / elapsed if elapsed > 0 else 0
            eta = (len(candidates) - i) / rate if rate > 0 else 0
            print(f'  Progress: {i}/{len(candidates)} enriched={enriched} failed={failed} elapsed={elapsed:.0f}s eta={eta:.0f}s')
        time.sleep(0.5)

    print(f'\n[3] SU enrichment complete: enriched={enriched}, failed={failed}')

    # Phase 4: rebuild silver + gold
    print(f'\n[4] Rebuilding silver + gold...')
    from bronze_to_silver import build_silver_from_bronze
    from silver_to_gold import build_gold_rankings, build_gold_by_category, build_gold_to_source
    from build_manifest import build_manifest

    build_silver_from_bronze()
    build_gold_rankings()
    build_gold_by_category()
    build_gold_to_source()
    build_manifest()

    # Phase 5: report
    print(f'\n[5] Final report')
    from validate_manifest import validate_manifest
    validate_manifest()

    print(f'\n[done] Sprint 4 tiny complete')
    print(f'  Total runtime: {time.time() - t0:.0f}s')
    print(f'  Cost: ~${enriched * 0.005:.3f}')


if __name__ == '__main__':
    main()
