#!/usr/bin/env python3
"""
run_pipeline.py — Run full 4-stage pipeline for a category.

Stages:
  1. MTOP discovery (queries → top N by booked)
  2. Decodo SU detail enrichment (per offer)
  3. Rakumart BR cross-walk (per offer title)
  4. Build silver + gold layers

Usage:
  python3 scripts/run_pipeline.py --category organization \\
       --queries 收纳,收纳盒,收纳箱 --top-n 50

This is the PRODUCTION pipeline. Saves bronze snapshots, then runs
bronze_to_silver + silver_to_gold. Idempotent.

Cost: ~$0.005/offer SU detail enrichment. 50 products = $0.25.
"""

import argparse
import json
import re
import ssl
import sys
import time
import urllib.request
from urllib.parse import unquote
from datetime import datetime
from pathlib import Path

# Add SDK paths
sys.path.insert(0, '/tmp/scrapers-test/ai-reverse/1688')
sys.path.insert(0, '/mnt/ssd/1688-intel/scripts/arbitlens')
sys.path.insert(0, str(Path(__file__).parent))

from save_bronze import save_mtop_data, save_su_detail, save_rakumart_results  # noqa: E402
from client import Alibaba1688Client  # noqa: E402
from scrape_rakumart_br import search_rakumart_br  # noqa: E402

# Decodo SU credentials
SU_PASS = 'PW_17560792063f932882c0843ad92c0ed69'
SU_USER = 'U0000434457'
SU_PROXY = f'http://{SU_USER}:{SU_PASS}@unblock.decodo.com:60000'

# ────────────────────────────────────────────────────────────────────
# Stage 1: MTOP Discovery
# ────────────────────────────────────────────────────────────────────

def stage_mtop(queries: list, top_n: int) -> list:
    """Run MTOP searches, dedup by offer_id, return top N by booked_count."""
    print(f'\n[STAGE 1] MTOP Discovery — queries: {queries}, top_n: {top_n}')

    client = Alibaba1688Client()
    if not client.session.login():
        print('ERROR: MTOP login failed')
        return []

    all_items = []
    seen_ids = set()

    for query in queries:
        # 2 pages × 50 = up to 100 per query
        for page in [1, 2]:
            try:
                resp = client.search_by_text(query, page=page, page_size=50)
                # Save bronze snapshot
                save_mtop_data(query, page, resp)
                if not resp.success:
                    print(f'  WARN: {query} p{page} ret={resp.ret}')
                    continue
                items = resp.data.get('data', {}).get('OFFER', {}).get('items', [])
                if not items:
                    break
                for it in items:
                    d = it.get('data', {})
                    oid = d.get('offerId')
                    if oid and oid not in seen_ids:
                        seen_ids.add(oid)
                        all_items.append({
                            'offer_id': oid,
                            'title': re.sub(r'<[^>]+>', '', d.get('title', ''))[:200],
                            'price_cny': (d.get('priceInfo') or {}).get('price'),
                            'shop': unquote((d.get('shop') or {}).get('loginIdOfUtf8') or d.get('loginId') or ''),
                            'province': d.get('province'),
                            'city': d.get('city'),
                            'booked_count': d.get('bookedCount') or 0,
                            'image_url': d.get('offerPicUrl'),
                            'query': query,
                        })
            except Exception as e:
                print(f'  ERROR: {query} p{page}: {e}')
            time.sleep(0.5)

    print(f'  Found {len(all_items)} unique offers across {len(queries)} queries')

    # Sort by booked_count, take top N
    top = sorted(all_items, key=lambda x: -int(x.get('booked_count') or 0))[:top_n]
    print(f'  Top {len(top)} by booked_count')
    return top


# ────────────────────────────────────────────────────────────────────
# Stage 2: Decodo SU Detail Enrichment
# ────────────────────────────────────────────────────────────────────

def stage_su(offers: list) -> list:
    """Fetch SU detail page for each offer, save bronze HTML."""
    print(f'\n[STAGE 2] Decodo SU Enrichment — {len(offers)} offers')

    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    https_handler = urllib.request.HTTPSHandler(context=ctx)
    opener = urllib.request.build_opener(
        urllib.request.ProxyHandler({'http': SU_PROXY, 'https': SU_PROXY}),
        https_handler
    )

    enriched = 0
    failed = 0

    for i, offer in enumerate(offers, 1):
        oid = offer['offer_id']
        url = f'https://detail.1688.com/offer/{oid}.html'
        try:
            req = urllib.request.Request(url, headers={
                'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
            })
            req.add_header('X-SU-Geo', 'China')
            req.add_header('X-SU-Locale', 'zh-cn')
            body = opener.open(req, timeout=60).read().decode('utf-8', errors='ignore')
            if len(body) > 50000:
                save_su_detail(oid, body)
                enriched += 1
            else:
                failed += 1
        except Exception as e:
            failed += 1
            print(f'  [{i}/{len(offers)}] FAIL {oid}: {str(e)[:80]}')
        # Rate limit
        time.sleep(3)
        if i % 10 == 0:
            print(f'  [{i}/{len(offers)}] enriched={enriched} failed={failed}')

    print(f'  Total: enriched={enriched}, failed={failed}')
    return [o for o in offers if True]  # all offers kept, SU may have failed


# ────────────────────────────────────────────────────────────────────
# Stage 3: Rakumart BR Cross-walk
# ────────────────────────────────────────────────────────────────────

def stage_rakumart(offers: list, category: str) -> list:
    """Cross-walk each offer title to Rakumart, save bronze + return matches."""
    print(f'\n[STAGE 3] Rakumart Cross-walk — {len(offers)} offers')

    # Map category to Rakumart search language
    RAK_QUERIES = {
        'beach_clip': ['prendedor toalha', 'clipe praia'],
        'socks': ['meias'],
        'drill': ['parafusadeira', 'furadeira'],
        'underwear': ['cueca', 'calcinha', 'shapewear'],
        'organization': ['organizador', 'caixa organizadora'],
        'flashlight': ['lanterna'],
        'webcams': ['camera', 'webcam'],
    }
    queries = RAK_QUERIES.get(category, [category])

    matched_offers = []

    for i, offer in enumerate(offers, 1):
        # Extract first meaningful Chinese keyword for Rakumart search
        title = offer['title']
        # Try the category queries first (best match)
        best_match = None
        for q in queries:
            try:
                results = search_rakumart_br(q, source='1688', page=1)
                # Save bronze
                save_rakumart_results(q, '1688', 1, results)
                # Look for title overlap
                from difflib import SequenceMatcher
                for r in results:
                    rk_title = getattr(r, 'raw_data', {}).get('title', '') or ''
                    if not rk_title:
                        continue
                    score = SequenceMatcher(None, title[:30].lower(), rk_title[:30].lower()).ratio() * 100
                    if score > 50 and (best_match is None or score > best_match[1]):
                        best_match = (r, score, q)
            except Exception as e:
                print(f'  [{i}/{len(offers)}] RAK fail {q}: {e}')
            time.sleep(0.5)

        if best_match:
            r, score, q = best_match
            rd = r.raw_data if hasattr(r, 'raw_data') else {}
            offer['rakumart'] = {
                'iid': getattr(r, 'id', None) or rd.get('iid'),
                'title_cn': rd.get('title_cn') or rd.get('title', ''),
                'title_pt': rd.get('title_pt') or rd.get('subtitle', ''),
                'price_brl': float(rd.get('price', 0) or 0),
                'match_score': round(score, 1),
                'query_used': q,
            }
            matched_offers.append(offer)
        else:
            offer['rakumart'] = None

        if i % 10 == 0:
            print(f'  [{i}/{len(offers)}] matched={len(matched_offers)}')

    print(f'  Total matched: {len(matched_offers)}/{len(offers)}')
    return offers


# ────────────────────────────────────────────────────────────────────
# Stage 4: Build Silver Offers
# ────────────────────────────────────────────────────────────────────

def stage_silver(offers: list, category: str, date_str: str):
    """Build silver offer files from enriched + matched data."""
    print(f'\n[STAGE 4] Build Silver Offers — {len(offers)} offers')

    SILVER = Path(__file__).parent.parent / 'data' / 'silver' / 'offers'
    BRONZE = Path(__file__).parent.parent / 'data' / 'bronze'

    built = 0
    for offer in offers:
        oid = offer['offer_id']

        # Find bronze refs
        su_html = list((BRONZE / 'su_detail').glob(f'{date_str}_{oid}.html'))
        mtop_files = list((BRONZE / 'mtop').glob(f'{date_str}_*_p*.json'))

        # Parse SU detail if exists
        su_block = None
        if su_html:
            html = su_html[0].read_text(encoding='utf-8', errors='ignore')
            if len(html) > 50000:
                company = (re.search(r'"companyName"\s*:\s*"([^"]{2,100})"', html) or [None, None])[1]
                su_block = {'shop_name': company} if company else {}

        silver = {
            'offer_id': oid,
            'mtop': {
                'title': offer['title'],
                'price_cny': offer['price_cny'],
                'shop': offer.get('shop'),
                'image_url': offer.get('image_url'),
            },
            'su_detail': su_block or {},
            'rakumart': offer.get('rakumart'),
            'enriched_at': datetime.now().isoformat() + 'Z',
            'category': category,
        }

        out = SILVER / f'{oid}.json'
        out.write_text(json.dumps(silver, ensure_ascii=False, indent=2), encoding='utf-8')
        built += 1

    print(f'  Built {built} silver offers')
    return built


# ────────────────────────────────────────────────────────────────────
# Main
# ────────────────────────────────────────────────────────────────────

def main():
    p = argparse.ArgumentParser(description='Run full 4-stage pipeline for a category')
    p.add_argument('--category', required=True, help='Category slug (e.g. socks, drill, organization)')
    p.add_argument('--queries', required=True, help='Comma-separated CN queries for MTOP discovery')
    p.add_argument('--top-n', type=int, default=50, help='Top N by booked count (default 50)')
    p.add_argument('--skip-su', action='store_true', help='Skip SU enrichment (faster, less cost)')
    p.add_argument('--skip-rak', action='store_true', help='Skip Rakumart cross-walk')
    p.add_argument('--no-silver', action='store_true', help='Skip silver build (bronze only)')
    args = p.parse_args()

    queries = [q.strip() for q in args.queries.split(',') if q.strip()]
    date_str = datetime.now().strftime('%Y-%m-%d')

    print('=' * 70)
    print(f'PIPELINE RUN — {args.category}')
    print(f'  Queries: {queries}')
    print(f'  Top N: {args.top_n}')
    print(f'  Date: {date_str}')
    print('=' * 70)

    # Stage 1
    offers = stage_mtop(queries, args.top_n)
    if not offers:
        print('Pipeline aborted: no MTOP results')
        sys.exit(1)

    # Stage 2
    if not args.skip_su:
        offers = stage_su(offers)

    # Stage 3
    if not args.skip_rak:
        offers = stage_rakumart(offers, args.category)

    # Stage 4
    if not args.no_silver:
        n = stage_silver(offers, args.category, date_str)

    # Stage 5: rebuild gold
    print('\n[STAGE 5] Rebuild Gold Rankings')
    sys.path.insert(0, str(Path(__file__).parent))
    from silver_to_gold import build_gold_rankings, build_gold_by_category, build_gold_to_source
    build_gold_rankings()
    build_gold_by_category()
    build_gold_to_source()
    print('  Gold rebuilt')

    print('\n' + '=' * 70)
    print('PIPELINE COMPLETE')
    print(f'  Bronze: data/bronze/')
    print(f'  Silver: data/silver/offers/ (added {len(offers)})')
    print(f'  Gold: data/gold/')
    print('=' * 70)


if __name__ == '__main__':
    main()