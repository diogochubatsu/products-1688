#!/usr/bin/env python3
"""
build_silver_from_bronze.py — Build silver offers from existing bronze files.

Derives category per offer by:
  1. Finding which bronze/mtop/ file contains the offer_id
  2. Mapping the query (from filename) to category via QUERY_CATEGORY_MAP

Usage:
  python3 scripts/build_silver_from_bronze.py [--date YYYY-MM-DD]
"""
import argparse
import json
import re
import sys
from datetime import datetime
from pathlib import Path
from urllib.parse import unquote

DATA = Path(__file__).parent.parent / 'data'
BRONZE = DATA / 'bronze'
SILVER = DATA / 'silver' / 'offers'

# Query → category mapping
QUERY_CATEGORY_MAP = {
    # beach_clip
    '沙滩巾夹': 'beach_clip', '沙滩夹': 'beach_clip', '沙滩毛巾夹': 'beach_clip',
    'clipe_praia_1688': 'beach_clip', 'prendedor_toalha_1688': 'beach_clip',
    # organization
    '收纳': 'organization', '收纳盒': 'organization', '收纳箱': 'organization',
    'caixa_organizadora_1688': 'organization', 'organizador_1688': 'organization',
    # underwear
    '内衣': 'underwear', '塑身衣': 'underwear', '内裤': 'underwear', '收腹裤': 'underwear',
    'roupa_intima_1688': 'underwear', 'modelador_1688': 'underwear',
    # socks (no new queries yet, kept for future)
    'meias': 'socks', 'sock': 'socks', 'meia_1688': 'socks',
    # drill
    '电钻': 'drill', 'furadeira': 'drill', 'parafusadeira': 'drill', 'drill_1688': 'drill',
    # flashlight (Sprint 4)
    '手电筒': 'flashlight', 'LED强光手电筒': 'flashlight', '头灯': 'flashlight',
    'lanterna': 'flashlight', 'lanterna_led': 'flashlight',
    # webcam (Sprint 4)
    '摄像头': 'webcam', '监控摄像头': 'webcam', '网络摄像机': 'webcam',
    'camera_ip': 'webcam', 'camera_wifi': 'webcam',

    # underwear subcategories (Sprint 4 v2)
    '提臀塑身衣': 'underwear', '收腹塑身衣': 'underwear', '无痕内裤': 'underwear',
    '连体塑身衣': 'underwear', '产后塑身衣': 'underwear',
    # socks subcategories (Sprint 4 v2)
    '船袜': 'socks', '运动袜': 'socks', '童袜': 'socks',
    '女士丝袜': 'socks', '棉袜': 'socks', '羊毛袜': 'socks',
}


def category_for_query(query: str) -> str:
    """Map a query to its category."""
    if query in QUERY_CATEGORY_MAP:
        return QUERY_CATEGORY_MAP[query]
    # Fallback: contains match
    for q, c in QUERY_CATEGORY_MAP.items():
        if q in query or query in q:
            return c
    return 'unknown'


def build_mtop_index(date_str: str) -> dict:
    """Build offer_id → mtop_data, derived from all bronze mtop files for the date."""
    mtop_data = {}  # offer_id -> {title, price_cny, shop, image_url, category}
    query_to_category = {}

    for mf in sorted((BRONZE / 'mtop').glob(f'{date_str}_*.json')):
        # Filename: YYYY-MM-DD_<query>_p<page>.json
        # Query may contain underscores (like 'clipe_praia_1688')
        stem = mf.stem  # YYYY-MM-DD_<query>_p<page>
        # Strip date prefix and _pX.json suffix
        m = re.match(r'\d{4}-\d{2}-\d{2}_(.+)_p\d+$', stem)
        if not m:
            continue
        query = m.group(1)
        category = category_for_query(query)
        query_to_category[query] = category

        try:
            data = json.loads(mf.read_text(encoding='utf-8'))
        except Exception:
            continue
        items = data.get('data', {}).get('OFFER', {}).get('items', [])
        for it in items:
            d = it.get('data', {})
            oid = d.get('offerId')
            if not oid or oid in mtop_data:
                continue
            shop = d.get('shop', {})
            loginid = shop.get('loginIdOfUtf8') or shop.get('loginId') if isinstance(shop, dict) else ''
            mtop_data[oid] = {
                'title': re.sub(r'<[^>]+>', '', d.get('title', ''))[:200],
                'price_cny': (d.get('priceInfo') or {}).get('price'),
                'shop': unquote(loginid) if loginid else '',
                'image_url': d.get('offerPicUrl'),
                'category': category,
            }

    return mtop_data, query_to_category


def parse_su_html(html_path: Path) -> dict:
    """Extract shop_name from raw SU HTML (simplified schema)."""
    if not html_path.exists():
        return {}
    html = html_path.read_text(encoding='utf-8', errors='ignore')
    if len(html) < 50000:
        return {}
    company = (re.search(r'"companyName"\s*:\s*"([^"]{2,100})"', html) or [None, None])[1]
    return {'shop_name': company} if company else {}


def build(date_str: str = None, target_category: str = None):
    """Build silver for ALL bronze offer_ids (or specific category if given)."""
    if not date_str:
        date_str = datetime.now().strftime('%Y-%m-%d')

    mtop_data, query_to_category = build_mtop_index(date_str)
    print(f'  MTOP data: {len(mtop_data)} offers, queries: {list(query_to_category.keys())}')

    # Find all SU bronze files
    su_files = sorted((BRONZE / 'su_detail').glob(f'{date_str}_*.html'))
    print(f'  SU bronze files: {len(su_files)}')

    built = 0
    skipped = 0
    by_category = {}

    for su_path in su_files:
        # Filename: YYYY-MM-DD_<offer_id>.html
        parts = su_path.stem.split('_')
        if len(parts) != 2 or not parts[1].isdigit():
            continue
        oid = int(parts[1])
        m = mtop_data.get(oid, {})
        category = m.get('category', 'unknown')

        # Skip if target_category filter and not matching
        if target_category and category != target_category:
            skipped += 1
            continue

        su_block = parse_su_html(su_path)

        silver = {
            'offer_id': oid,
            'mtop': {
                'title': m.get('title', ''),
                'price_cny': m.get('price_cny'),
                'shop': m.get('shop'),
                'image_url': m.get('image_url'),
            },
            'su_detail': su_block or {},
            'rakumart': None,
            'enriched_at': datetime.now().isoformat() + 'Z',
            'category': category,
        }

        out = SILVER / f'{oid}.json'
        out.write_text(json.dumps(silver, ensure_ascii=False, indent=2), encoding='utf-8')
        built += 1
        by_category[category] = by_category.get(category, 0) + 1

    print(f'  Built {built} silver offers (skipped {skipped})')
    print(f'  By category: {by_category}')
    return built


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--date', help='Date (YYYY-MM-DD), default today')
    p.add_argument('--category', help='Only build for this category (filter)')
    p.add_argument('--clean-bogus', action='store_true',
                   help='Remove 2026-06-18 bronze files (leftover from test runs)')
    args = p.parse_args()

    if args.clean_bogus:
        # Remove 2026-06-18 bronze leftovers
        for sub in ['mtop', 'su_detail', 'rakumart']:
            for f in (BRONZE / sub).glob('2026-06-18_*.json') if sub != 'su_detail' else (BRONZE / sub).glob('2026-06-18_*.html'):
                f.unlink()
                print(f'  Removed {f.name}')
        # Also remove any 2026-06-18 silver offers
        removed = 0
        for f in (SILVER).glob('*.json'):
            o = json.loads(f.read_text())
            # Remove if enriched_at starts with 2026-06-18
            if o.get('enriched_at', '').startswith('2026-06-18'):
                f.unlink()
                removed += 1
        print(f'  Removed {removed} 2026-06-18 silver offers')
        return

    date_str = args.date or datetime.now().strftime('%Y-%m-%d')
    build(date_str, args.category)

    # Rebuild gold
    sys.path.insert(0, str(Path(__file__).parent))
    from silver_to_gold import build_gold_rankings, build_gold_by_category, build_gold_to_source
    print('\nRebuilding gold...')
    build_gold_rankings()
    build_gold_by_category()
    build_gold_to_source()

    from build_manifest import build as build_manifest
    print('\nRebuilding manifest...')
    build_manifest()
    print('Done.')


if __name__ == '__main__':
    main()