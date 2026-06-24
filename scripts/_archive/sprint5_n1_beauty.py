#!/usr/bin/env python3
"""
sprint5_n1_beauty.py — Tiny Sprint 5 scraper for 美妆护肤 (Beauty) N1.

Goal: add first data for 4 new N1 categories (currently 0 offers).
Target this run: 美妆护肤 (Beauty), 10 offers × 2 subcategories = 20 total.
"""
import json
import sys
import time
import urllib.request
from pathlib import Path

ROOT = Path('/mnt/ssd/1688-only')
sys.path.insert(0, str(ROOT / 'scripts'))

# Load SU creds
env_lines = (ROOT / '.env').read_text().split('\n')
SU_USER = SU_PASS = None
for line in env_lines:
    if line.startswith('DECODO_SU_USER='):
        SU_USER = line.split('=', 1)[1].strip()
    if line.startswith('DECODO_SU_PASS='):
        SU_PASS = line.split('=', 1)[1].strip()
SU_PROXY = f'http://{SU_USER}:{SU_PASS}@unblock.decodo.com:60000'

from save_bronze import save_su_detail
from scrape_1688_mtop import scrape as mtop_search

# === Sprint 5 config ===
# Target: 美妆护肤 (Beauty) — first 2 N4 subcategories
SPRINT5_QUERIES = [
    ('化妆刷',     '美妆护肤/美妆工具/化妆工具/化妆刷'),    # makeup brushes
    ('美甲工具',   '美妆护肤/美妆工具/化妆工具/美甲工具'),  # manicure tools
]
DATE = '2026-06-22'
PER_QUERY = 10  # tiny

MTOP_DIR = ROOT / 'data/bronze/mtop'

# Phase 1: MTOP search
print(f'[1] MTOP search — {len(SPRINT5_QUERIES)} queries × {PER_QUERY} = {len(SPRINT5_QUERIES) * PER_QUERY} candidates')
all_results = []
for query, n4_path in SPRINT5_QUERIES:
    print(f'  Query: {query}')
    items = mtop_search(query, pages=1, size=PER_QUERY, save_bronze=False)
    # Save raw bronze separately
    out_file = MTOP_DIR / f'{DATE}_{query}_p1.json'
    out_file.write_text(json.dumps({'items': items}, ensure_ascii=False))
    # Sort by price, pick top N
    cands = []
    for it in items:
        oid = it.get('offer_id') or it.get('offerId')
        price = it.get('price_cny') or it.get('price')
        title = (it.get('title') or '')[:50]
        if oid and price is not None:
            try:
                cands.append({'offer_id': str(oid), 'price_cny': float(price), 'title': title,
                              'query': query, 'n4_path': n4_path})
            except ValueError:
                pass
    cands.sort(key=lambda x: x['price_cny'])
    picked = cands[:PER_QUERY]
    print(f'    {len(items)} items → picked {len(picked)} cheapest')
    for c in picked:
        print(f'      {c["offer_id"]} ¥{c["price_cny"]:>5} {c["title"]}')
    all_results.extend(picked)

print(f'\nTotal candidates: {len(all_results)}')

# Phase 2: SU enrichment
print(f'\n[2] SU enrichment — {len(all_results)} calls, ~{len(all_results) * 3 // 60} min')
proxy_handler = urllib.request.ProxyHandler({'http': SU_PROXY, 'https': SU_PROXY})
opener = urllib.request.build_opener(proxy_handler)

enriched = failed = 0
t0 = time.time()
for i, c in enumerate(all_results, 1):
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
            failed += 1
    except Exception:
        failed += 1
    if i % 5 == 0 or i == len(all_results):
        elapsed = time.time() - t0
        rate = i / elapsed if elapsed > 0 else 0
        eta = (len(all_results) - i) / rate if rate > 0 else 0
        print(f'  Progress: {i}/{len(all_results)} enriched={enriched} failed={failed} elapsed={elapsed:.0f}s eta={eta:.0f}s')
    time.sleep(0.4)

print(f'\n[2] SU enrichment done: enriched={enriched}, failed={failed}')
print(f'Cost: ~${enriched * 0.005:.3f}')
print(f'Time: {time.time() - t0:.0f}s')

# Phase 3: Crosswalk (bonus)
print(f'\n[3] Crosswalk — {enriched} offers against Rakumart (1688 source)')

# Write candidates to a file for crosswalk script to pick up
(Path('/tmp/sprint5_candidates.json')).write_text(json.dumps(all_results, ensure_ascii=False))
print(f'  Wrote {len(all_results)} candidates to /tmp/sprint5_candidates.json')