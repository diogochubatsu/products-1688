#!/usr/bin/env python3
"""
sprint4_tiny2.py — Tiny Sprint 4 runner v2 (6 subcategories × 10 = 60).

Goal: expand underwear + socks with subcategories, including butt-lifting shapewear.

Subcategories (mapped to existing parent categories):
  underwear: 提臀塑身衣 (butt-lifting), 收腹塑身衣 (tummy-control), 无痕内裤 (seamless)
  socks:     船袜 (no-show), 运动袜 (sports), 童袜 (kids)

Phases:
  1. MTOP search (6 queries, 1 page each, size 20)
  2. Pick top 10 by price per query
  3. SU detail enrichment (60 calls × ~3s = ~3 min)
  4. Silver + Gold rebuild
  5. Report

Usage:
  python3 scripts/sprint4_tiny2.py [--dry-run]

Cost: ~$0.30 (60 SU calls × $0.005)
Time: ~3 minutes
"""
import argparse
import json
import sys
import time
import urllib.request
from pathlib import Path

ROOT = Path('/mnt/ssd/1688-only')
sys.path.insert(0, str(ROOT / 'scripts'))

# === Sprint 4 v2 config ===
# list of (parent_category, CN query) — list not dict because parent repeats
SPRINT4_QUERIES = [
    ('underwear', '提臀塑身衣'),   # butt-lifting shapewear (user requested)
    ('underwear', '收腹塑身衣'),   # tummy-control shapewear
    ('underwear', '无痕内裤'),     # seamless panties
    ('socks',     '船袜'),          # no-show / ankle socks
    ('socks',     '运动袜'),        # sports socks
    ('socks',     '童袜'),          # children's socks
]

PER_QUERY = 10  # tiny batch


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--dry-run', action='store_true',
                    help='Show what would be scraped without actually scraping')
    args = ap.parse_args()

    print('=' * 60)
    print('SPRINT 4 TINY v2 — 6 subcategories × 10 candidates = 60 SU calls')
    print('=' * 60)
    print(f'Cost: ~$0.30 (60 × $0.005)')
    print(f'Time: ~3 minutes')
    print()

    for cat, query in SPRINT4_QUERIES:
        print(f'  {cat:12} query="{query}"')

    print()
    if args.dry_run:
        print('DRY RUN — no scraping performed')
        return

    # Load SU creds from .env
    env_lines = (ROOT / '.env').read_text().split('\n')
    SU_USER = SU_PASS = None
    for line in env_lines:
        if line.startswith('DECODO_SU_USER='):
            SU_USER = line.split('=', 1)[1].strip()
        if line.startswith('DECODO_SU_PASS='):
            SU_PASS = line.split('=', 1)[1].strip()
    SU_PROXY = f'http://{SU_USER}:{SU_PASS}@unblock.decodo.com:60000'

    # Phase 1+2: MTOP + pick top 10 per query
    from scrape_1688_mtop import scrape
    from save_bronze import save_mtop_data, save_su_detail

    candidates = []

    for cat, query in SPRINT4_QUERIES:
        print(f'\n[1] MTOP search: {cat} ("{query}")')
        products = scrape(query, pages=1, size=20, save_bronze=True)

        if not products:
            print(f'  WARN: no products returned for {cat}/{query}')
            continue

        # Filter & sort: lowest price first
        valid = [p for p in products if p.get('offer_id') and p.get('price_cny')]
        valid.sort(key=lambda p: float(p['price_cny']))

        top_n = valid[:PER_QUERY]
        print(f'  Found {len(products)}, picked top {len(top_n)} by price')
        for i, p in enumerate(top_n, 1):
            print(f'    {i:2}. {p["offer_id"]} ¥{p["price_cny"]:>7} {p["title"][:50]}')

        for p in top_n:
            candidates.append({'category': cat, 'sub_query': query, **p})

    print(f'\n[1+2] Total candidates: {len(candidates)}')

    # Phase 3: SU enrichment
    print(f'\n[3] SU detail enrichment — {len(candidates)} calls')
    print(f'    Estimated time: ~{len(candidates) * 3}s')

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
        if i % 10 == 0 or i == len(candidates):
            elapsed = time.time() - t0
            rate = i / elapsed if elapsed > 0 else 0
            eta = (len(candidates) - i) / rate if rate > 0 else 0
            print(f'  Progress: {i}/{len(candidates)} enriched={enriched} failed={failed} elapsed={elapsed:.0f}s eta={eta:.0f}s')
        time.sleep(0.5)

    print(f'\n[3] SU enrichment complete: enriched={enriched}, failed={failed}')

    # Phase 4: rebuild silver + gold
    print(f'\n[4] Rebuilding silver + gold...')
    from build_silver_from_bronze import build as build_silver
    from silver_to_gold import build_gold_rankings, build_gold_by_category, build_gold_to_source
    from build_manifest import build as build_manifest
    from validate_manifest import main as validate

    build_silver()
    build_gold_rankings()
    build_gold_by_category()
    build_gold_to_source()
    build_manifest()
    validate()

    print(f'\n[done] Sprint 4 v2 complete')
    print(f'  Total runtime: {time.time() - t0:.0f}s')
    print(f'  Cost: ~${enriched * 0.005:.3f}')


if __name__ == '__main__':
    main()
