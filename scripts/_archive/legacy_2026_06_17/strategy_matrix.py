#!/usr/bin/env python3
"""
strategy_matrix.py — comprehensive cross-source validation.

For 3 categories (drill, socks, beach clip), test 4 sources:
  1. MTOP (ai-reverse SDK)
  2. Rakumart BR 1688 tab
  3. Rakumart BR alibaba tab
  4. Rakumart BR taobao tab

For top 1 product per category, also try:
  5. Decodo SU detail enrichment
  6. Cross-source overlap analysis

For specific baiyite product (863290574424):
  7. Try alibaba.com EN storefront, supplier search
"""
import json
import re
import subprocess
import sys
import time
from pathlib import Path
from urllib.parse import unquote

# MTOP
sys.path.insert(0, '/tmp/scrapers-test/ai-reverse/1688')
from client import Alibaba1688Client

# Rakumart
sys.path.insert(0, '/mnt/ssd/1688-intel/scripts/arbitlens')
from scrape_rakumart_br import search_rakumart_br

OUT_DIR = Path('/mnt/ssd/1688-only/data')


def mtop_search(client, query, pages=2, size=60):
    results = []
    seen = set()
    for page in range(1, pages + 1):
        r = client.search_by_text(query, page=page, page_size=size)
        if not r.success:
            break
        items = (r.data.get('data') or {}).get('OFFER', {}).get('items', [])
        for it in items:
            d = it.get('data', {})
            oid = str(d.get('offerId') or '')
            if oid and oid not in seen:
                seen.add(oid)
                results.append({
                    'offer_id': oid,
                    'title': unquote((d.get('title') or '').replace('<font color=red>', '').replace('</font>', '')),
                    'price_cny': float(d.get('priceInfo', {}).get('price') or 0),
                    'shop': unquote((d.get('shop') or {}).get('loginIdOfUtf8') or ''),
                    'image_url': d.get('offerPicUrl', ''),
                })
        time.sleep(0.2)
    return results


def rakumart_search(query, source, page=1):
    """Returns list of {iid, name, price_brl, image, source}"""
    try:
        items = search_rakumart_br(query, source=source, page=page)
    except Exception as e:
        print(f'    Rakumart {source} error: {e}')
        return []
    out = []
    for p in items:
        out.append({
            'iid': p.source_product_id,
            'name': p.product_name,
            'name_cn': p.raw_data.get('title_cn', ''),
            'price_brl': p.price_low,
            'image_url': p.image_url,
            'source_url': p.source_url,
            'shop': p.seller_name,
        })
    return out


def normalize_title(t):
    if not t:
        return ''
    t = re.sub(r'<[^>]+>', '', t)
    t = re.sub(r'[^\w\s\u4e00-\u9fff]', ' ', t)
    t = re.sub(r'\s+', ' ', t).strip().lower()
    return t


def overlap(a_titles, b_titles):
    """Count titles that match after normalization."""
    a = {normalize_title(t) for t in a_titles if t}
    b = {normalize_title(t) for t in b_titles if t}
    return len(a & b), len(a), len(b)


def decodo_detail_check(offer_id):
    """Try Decodo SU to hit detail page."""
    # Check if Decodo is set up
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        return {'status': 'no_playwright'}
    try:
        pw = sync_playwright().start()
        browser = pw.chromium.connect_over_cdp('http://unblock.decodo.com:60000') if False else None
        # Use direct connection
        browser = pw.chromium.launch(proxy={'server': 'http://unblock.decodo.com:60000'})
        page = browser.new_page()
        page.goto(f'https://detail.1688.com/offer/{offer_id}.html', timeout=20000)
        html = page.content()
        browser.close()
        pw.stop()
        baxia = 'tmd' in html.lower() or 'baxia' in html.lower()
        return {
            'status': 'ok' if not baxia else 'baxia',
            'size': len(html),
            'has_offer': 'offer' in html.lower(),
        }
    except Exception as e:
        return {'status': 'error', 'error': str(e)[:100]}


def test_category(name, mtop_query, pt_queries, mtop_pages=2):
    """Run all 4 sources on a category, compute overlap."""
    print(f'\n{"="*70}')
    print(f'CATEGORY: {name}')
    print(f'  MTOP query: {mtop_query!r}')
    print(f'  PT queries: {pt_queries}')
    print('='*70)

    client = Alibaba1688Client()
    client.session.login()

    # 1. MTOP
    t0 = time.time()
    mtop = mtop_search(client, mtop_query, pages=mtop_pages, size=60)
    mtop_time = time.time() - t0
    mtop_titles = [p['title'] for p in mtop]
    mtop_prices = [p['price_cny'] for p in mtop if p['price_cny'] > 0]
    print(f'\n[MTOP] {len(mtop)} products in {mtop_time:.1f}s'
          + (f' | ¥{min(mtop_prices):.0f}-{max(mtop_prices):.0f}' if mtop_prices else ''))

    # 2-4. Rakumart
    rak_results = {}
    for src in ['1688', 'alibaba', 'taobao']:
        # Use both PT and CN queries
        all_items = []
        for q in pt_queries + [mtop_query]:
            items = rakumart_search(q, source=src, page=1)
            for it in items:
                if it['iid'] not in {x['iid'] for x in all_items}:
                    all_items.append(it)
            time.sleep(0.3)
        rak_results[src] = all_items
        prices = [it['price_brl'] for it in all_items if it['price_brl']]
        print(f'[Rakumart-{src}] {len(all_items)} products'
              + (f' | R${min(prices):.2f}-R${max(prices):.2f}' if prices else ''))

    # Overlap analysis
    print(f'\n  OVERLAP MATRIX:')
    print(f'  {"" :15} {"MTOP":>8} {"Rak-1688":>10} {"Rak-ali":>10} {"Rak-tao":>10}')
    sources = {
        'MTOP': mtop_titles,
        'Rak-1688': [r['name_cn'] or r['name'] for r in rak_results['1688']],
        'Rak-ali': [r['name_cn'] or r['name'] for r in rak_results['alibaba']],
        'Rak-tao': [r['name_cn'] or r['name'] for r in rak_results['taobao']],
    }
    for sk, sv in sources.items():
        row = f'  {sk:15} '
        for ok, ov in sources.items():
            n, a, b = overlap(sv, ov)
            row += f' {n:>5}/{min(a,b):<3}'
        print(row)

    # Top 3 products from MTOP (to enrich with Decodo)
    print(f'\n  Top 3 MTOP products (for Decodo detail test):')
    for p in mtop[:3]:
        print(f'    {p["offer_id"]} ¥{p["price_cny"]:>5.0f} | {p["title"][:55]}')

    return {
        'category': name,
        'mtop': mtop,
        'rakumart_1688': rak_results['1688'],
        'rakumart_alibaba': rak_results['alibaba'],
        'rakumart_taobao': rak_results['taobao'],
        'sources_for_overlap': {k: v for k, v in sources.items()},
    }


def test_baiyite_specific():
    """Try to find the specific baiyite beach clip product or supplier."""
    print(f'\n{"="*70}')
    print('SPECIFIC PRODUCT: baiyite beach clip 863290574424')
    print('='*70)

    TARGET = '863290574424'
    findings = {}

    # 1. Try alibaba.com EN storefront (often not blocked)
    print('\n[A] alibaba.com EN storefront (baiyite):')
    r = subprocess.run(['curl', '-s', '-L', '-A', 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36',
                        '--max-time', '12',
                        f'https://baiyite.en.alibaba.com/productgrouplist-944827669/Beach_Towel_Clips.html'],
                       capture_output=True, text=True)
    html = r.stdout
    print(f'  size: {len(html)} bytes')
    # Look for offer IDs
    ids_1688 = re.findall(r'/offer/(\d{10,15})\.html', html)
    ids_alibaba = re.findall(r'/product/(\d{10,15})\.html', html)
    titles = re.findall(r'"title":"([^"]+)"', html)
    if ids_1688:
        print(f'  Found 1688 offer IDs: {ids_1688[:5]}')
    if ids_alibaba:
        print(f'  Found alibaba product IDs: {ids_alibaba[:5]}')
    if titles:
        print(f'  Found titles: {titles[:3]}')
    if not ids_1688 and not ids_alibaba and not titles:
        print(f'  BaXia or empty. First 300 chars:')
        print(f'  {html[:300]}')
    findings['alibaba_en_storefront'] = {
        'size': len(html),
        'has_ids': bool(ids_1688 or ids_alibaba),
        'has_titles': bool(titles),
    }

    # 2. Try alibaba.com search for baiyite
    print('\n[B] alibaba.com search "baiyite beach towel clip":')
    r = subprocess.run(['curl', '-s', '-A', 'Mozilla/5.0',
                        '--max-time', '10',
                        'https://www.alibaba.com/trade/search?SearchText=baiyite+beach+towel+clip'],
                       capture_output=True, text=True)
    html = r.stdout
    products = re.findall(r'"productId":"(\d+)"', html)
    print(f'  size: {len(html)} bytes, productIds found: {len(products)}')
    if products:
        print(f'  Sample IDs: {products[:5]}')
    findings['alibaba_search'] = {'size': len(html), 'product_ids': products[:10]}

    # 3. Try MTOP with shop-member search (if any)
    client = Alibaba1688Client()
    client.session.login()
    print('\n[C] MTOP search for "沙滩巾夹 baiyite":')
    r = mtop_search(client, '沙滩巾夹 baiyite', pages=1, size=20)
    print(f'  {len(r)} results')
    findings['mtop_with_brand'] = len(r)

    # 4. Search for similar products (any beach clip under ¥2 that could be baiyite)
    print('\n[D] MTOP cheap beach clips (¥0-2) — find baiyite tier:')
    r = mtop_search(client, '沙滩巾夹', pages=1, size=60)
    cheap = [p for p in r if 0 < p['price_cny'] <= 2]
    print(f'  {len(cheap)} cheap results out of {len(r)}')
    for p in cheap[:5]:
        print(f'    {p["offer_id"]} ¥{p["price_cny"]:.2f} | {p["title"][:50]} | shop:{p["shop"][:20]}')
    findings['cheap_beach_clips_count'] = len(cheap)

    return findings


def main():
    print('='*70)
    print('STRATEGY MATRIX — 3 categories × 4 sources + baiyite hunt')
    print('='*70)

    results = {}

    # Test 1: Drill / Parafusadeira
    results['drill'] = test_category(
        'Drill / Parafusadeira Elétrica',
        mtop_query='电动螺丝刀',
        pt_queries=['parafusadeira eletrica', 'furadeira eletrica', 'chave de impacto'],
        mtop_pages=2,
    )

    # Test 2: Socks / Meias
    results['socks'] = test_category(
        'Meias / Socks',
        mtop_query='袜子',
        pt_queries=['meias', 'meia', 'sock'],
        mtop_pages=2,
    )

    # Test 3: Beach clip
    results['beach_clip'] = test_category(
        'Clip de Toalha de Praia',
        mtop_query='沙滩巾夹',
        pt_queries=['prendedor toalha', 'clip toalha', 'prendedor toalha praia'],
        mtop_pages=2,
    )

    # Test 4: Specific baiyite
    results['baiyite_specific'] = test_baiyite_specific()

    # Save
    out_file = OUT_DIR / 'strategy_matrix_results.json'
    with open(out_file, 'w', encoding='utf-8') as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    print(f'\n\nFull results: {out_file}')

    # Final summary
    print('\n' + '='*70)
    print('STRATEGY RECOMMENDATION MATRIX')
    print('='*70)
    print()
    print('  Use case                         → Best source combination')
    print('  ' + '-'*60)
    print('  High-volume category discovery   → MTOP (free, 2000+ results)')
    print('  PT-BR product names + BRL price  → Rakumart alibaba (translated)')
    print('  BRL price + Rakumart product pg  → Rakumart 1688 (BRL + shop info)')
    print('  Taobao-specific products         → Rakumart taobao')
    print('  Detail enrichment (top 5)        → Decodo SU (only as needed)')
    print('  Specific 1688 offer_id lookup    → Rakumart BR (cached) — MTOP fails')
    print('  Supplier enumeration             → baiyite.1688.com (BLOCKED), alibaba.com EN')


if __name__ == '__main__':
    main()
