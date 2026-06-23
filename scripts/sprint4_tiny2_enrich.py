#!/usr/bin/env python3
"""
sprint4_tiny2_enrich.py — Just the SU enrichment phase for the 60 candidates already picked.
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

# Load existing MTOP bronze files
MTOP_DIR = ROOT / 'data/bronze/mtop'
queries = ['提臀塑身衣', '收腹塑身衣', '无痕内裤', '船袜', '运动袜', '童袜']
DATE = '2026-06-22'

from save_bronze import save_su_detail

# Phase 2: pick top 10 from each bronze mtop
candidates = []
for q in queries:
    f = MTOP_DIR / f'{DATE}_{q}_p1.json'
    if not f.exists():
        print(f'MISSING: {f}')
        continue
    data = json.loads(f.read_text())
    items = data.get('data', {}).get('OFFER', {}).get('items', [])
    # extract offer_id + price
    candidates_q = []
    for it in items:
        d = it.get('data', {})
        oid = d.get('offerId')
        price = (d.get('priceInfo') or {}).get('price') if isinstance(d.get('priceInfo'), dict) else None
        title = d.get('title', '')[:50]
        if oid and price is not None:
            try:
                candidates_q.append({'offer_id': str(oid), 'price_cny': float(price), 'title': title, 'query': q})
            except ValueError:
                pass
    candidates_q.sort(key=lambda x: x['price_cny'])
    top10 = candidates_q[:10]
    print(f'{q}: {len(items)} items, picked top 10 (cheapest)')
    for i, c in enumerate(top10, 1):
        print(f'  {i:2}. {c["offer_id"]} ¥{c["price_cny"]:>7} {c["title"]}')
    candidates.extend(top10)

print(f'\nTotal candidates: {len(candidates)}')

# Phase 3: SU enrichment
print(f'\n[3] SU enrichment — {len(candidates)} calls, ~3 min')
proxy_handler = urllib.request.ProxyHandler({'http': SU_PROXY, 'https': SU_PROXY})
opener = urllib.request.build_opener(proxy_handler)

enriched = failed = 0
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
    time.sleep(0.4)

print(f'\n[3] SU enrichment done: enriched={enriched}, failed={failed}')
print(f'Cost: ~${enriched * 0.005:.3f}')
print(f'Time: {time.time() - t0:.0f}s')
