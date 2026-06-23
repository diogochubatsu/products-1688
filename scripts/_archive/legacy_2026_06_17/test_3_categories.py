#!/usr/bin/env python3
"""
test_3_categories.py — User-requested validation:
  1. Furadeira/parafusadeira elétrica (drill/screwdriver)
  2. Meias (socks)
  3. Beach towel clip — test if offer_id 863290574424 from
     https://detail.1688.com/offer/863290574424.html appears in MTOP results
"""
import json
import sys
import time
from pathlib import Path
from urllib.parse import unquote

sys.path.insert(0, '/tmp/scrapers-test/ai-reverse/1688')
from client import Alibaba1688Client

OUT_DIR = Path('/mnt/ssd/1688-only/data')
OUT_DIR.mkdir(exist_ok=True)


def mtop_search(client, query, pages=2, size=20):
    """Run MTOP search and return flat list of {offer_id, title, price_cny, ...}."""
    results = []
    seen = set()
    for page in range(1, pages + 1):
        r = client.search_by_text(query, page=page, page_size=size)
        if not r.success:
            break
        items = (r.data.get('data') or {}).get('OFFER', {}).get('items', [])
        if not items:
            break
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
                    'province': d.get('province', ''),
                    'city': d.get('city', ''),
                    'factory_inspection': d.get('factoryInspection', False),
                    'image_url': d.get('offerPicUrl', ''),
                })
        time.sleep(0.2)
    return results


def test_category(client, name, queries):
    """Try multiple CN keyword variants for a category, pick the one with most results."""
    print(f'\n=== {name} ===')
    best = None
    for q in queries:
        t0 = time.time()
        results = mtop_search(client, q, pages=1, size=20)
        elapsed = time.time() - t0
        prices = [r['price_cny'] for r in results if r['price_cny'] > 0]
        print(f'  "{q}" → {len(results)} results in {elapsed:.1f}s'
              + (f' | ¥{min(prices):.0f}-{max(prices):.0f}' if prices else ''))
        if not best or len(results) > len(best['products']):
            best = {'query': q, 'products': results, 'time_s': round(elapsed, 2)}
    # Re-run best with more pages
    if best:
        t0 = time.time()
        full = mtop_search(client, best['query'], pages=3, size=20)
        best['full_count'] = len(full)
        best['full_time_s'] = round(time.time() - t0, 2)
        best['products'] = full
        prices = [p['price_cny'] for p in full if p['price_cny'] > 0]
        if prices:
            best['price_min'] = min(prices)
            best['price_max'] = max(prices)
            best['price_median'] = sorted(prices)[len(prices)//2]
        print(f'  → Best: "{best["query"]}" × 3 pages = {len(full)} products'
              + (f' | ¥{best["price_min"]:.0f}-{best["price_max"]:.0f} (med ¥{best["price_median"]:.0f})' if 'price_min' in best else ''))
    return best


def test_specific_offer_id(client, target_oid):
    """Hunt for a specific 1688 offer_id across multiple beach-clip related queries."""
    print(f'\n=== HUNT for offer_id={target_oid} ===')
    queries = ['沙滩巾夹', '沙滩夹', '沙滩毛巾夹', '浴巾夹', '毛巾夹', '海滩夹', '沙滩扣', 'beach towel clip']
    found_in = []
    for q in queries:
        # Run 3 pages × 20 to scan top 60 results per query
        results = mtop_search(client, q, pages=3, size=20)
        match = [r for r in results if r['offer_id'] == target_oid]
        if match:
            m = match[0]
            print(f'  FOUND in "{q}" page results!')
            print(f'    title: {m["title"]}')
            print(f'    price: ¥{m["price_cny"]}')
            print(f'    shop: {m["shop"]}')
            print(f'    location: {m["province"]} / {m["city"]}')
            print(f'    factory_inspection: {m["factory_inspection"]}')
            found_in.append({'query': q, 'match': m})
        else:
            print(f'  "{q}" → 60 products scanned, target {target_oid} not in top 60')
        time.sleep(0.3)
    return found_in


def main():
    print('='*70)
    print('3-CATEGORY MTOP TEST — User-requested')
    print('='*70)

    client = Alibaba1688Client()
    if not client.session.login():
        print('LOGIN FAILED')
        return

    # 1. Drill / screwdriver
    drill = test_category(client, '1. Drill / Parafusadeira', [
        '电钻',                # electric drill
        '电动螺丝刀',          # electric screwdriver
        '电钻 电动螺丝刀',     # both
        '充电式电钻',          # cordless drill
    ])

    # 2. Socks
    socks = test_category(client, '2. Meias / Socks', [
        '袜子',
        '船袜',                # boat socks / no-show
        '运动袜',              # sport socks
        '棉袜',                # cotton socks
    ])

    # 3. Beach towel clip — HUNT FOR SPECIFIC offer_id
    clip_found = test_specific_offer_id(client, '863290574424')

    # Also do regular category test for clip with best keyword
    print('\n--- Beach clip broad test (separate from hunt) ---')
    clip = test_category(client, '3b. Beach Towel Clip (broad)', [
        '沙滩巾夹',
        '沙滩夹',
        '沙滩毛巾夹',
        '毛巾夹',
    ])

    # Final report
    print('\n' + '='*70)
    print('SUMMARY')
    print('='*70)
    print(f'1. Drill/Parafusadeira → {drill["full_count"]} products, ¥{drill.get("price_min",0):.0f}-{drill.get("price_max",0):.0f}')
    print(f'2. Meias (socks)        → {socks["full_count"]} products, ¥{socks.get("price_min",0):.0f}-{socks.get("price_max",0):.0f}')
    print(f'3. Beach clip (broad)   → {clip["full_count"]} products, ¥{clip.get("price_min",0):.0f}-{clip.get("price_max",0):.0f}')
    print()
    print(f'TARGET offer_id 863290574424 hunt: {"FOUND in MTOP!" if clip_found else "NOT in top results"}')
    if clip_found:
        print('   → Strongest possible validation: MTOP returns the EXACT same')
        print('     1688 product that the user navigated to via detail.1688.com')
    else:
        print('   → Either:')
        print('     a) product is deep in catalog (need more pages/different sort)')
        print('     b) MTOP search only returns active/promoted offers')
        print('     c) product is no longer listed on 1688')

    # Save full results
    output = {
        'drill': drill,
        'socks': socks,
        'clip_broad': clip,
        'hunt_for_863290574424': clip_found,
        'tested_at': time.strftime('%Y-%m-%d %H:%M:%S'),
    }
    out_file = OUT_DIR / 'mtop_3category_test.json'
    with open(out_file, 'w', encoding='utf-8') as f:
        json.dump(output, f, ensure_ascii=False, indent=2)
    print(f'\nFull results saved: {out_file}')


if __name__ == '__main__':
    main()
