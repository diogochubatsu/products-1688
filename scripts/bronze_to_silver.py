#!/usr/bin/env python3
"""
bronze_to_silver.py — Transform raw MTOP/Rakumart/SU data into silver offers.

Inputs (bronze):
  bronze/mtop/{date}_{query}_p{page}.json     (raw MTOP API response)
  bronze/su_detail/{date}_{offer_id}.html    (raw Decodo SU HTML)
  bronze/rakumart/{date}_{query}_{src}_p{page}.json  (raw Rakumart response)

Output (silver):
  silver/offers/{offer_id}.json    (one file per offer, joined across sources)

Usage:
  python3 scripts/bronze_to_silver.py --date 2026-06-17 --offer 641931920298

For batch migration (LEGACY data without bronze snapshots):
  python3 scripts/bronze_to_silver.py --migrate-legacy baiyite
  python3 scripts/bronze_to_silver.py --migrate-legacy all

This script is idempotent: re-running overwrites silver files.
"""

import json
import re
import sys
from pathlib import Path
from datetime import datetime
import argparse

DATA_ROOT = Path(__file__).parent.parent / 'data'
BRONZE = DATA_ROOT / 'bronze'
SILVER = DATA_ROOT / 'silver'

CATEGORIES = {
    'beach_clip': {'zh': '沙滩巾夹', 'queries': ['沙滩巾夹', '沙滩夹', '沙滩毛巾夹']},
    'socks': {'zh': '袜子', 'queries': ['袜子', '棉袜', '运动袜', '船袜']},
    'drill': {'zh': '电动螺丝刀', 'queries': ['电动螺丝刀', '充电式电钻', '手电钻']},
    'underwear': {'zh': '内衣', 'queries': ['塑身衣', '收腹裤', '内裤', '内衣']},
}


def parse_su_detail(html_path: Path) -> dict:
    """Parse Decodo SU HTML to extract subject, company, sku, images."""
    if not html_path.exists() or html_path.stat().st_size < 10000:
        return {'is_live': False, 'size_bytes': html_path.stat().st_size if html_path.exists() else 0}

    body = html_path.read_text(encoding='utf-8', errors='ignore')
    return {
        'subject': (re.search(r'"subject"\s*:\s*"([^"]{5,200})"', body) or [None, None])[1],
        'company': (re.search(r'"companyName"\s*:\s*"([^"]{2,100})"', body) or [None, None])[1],
        'loginid': (re.search(r'"loginId"\s*:\s*"([^"]{2,50})"', body) or [None, None])[1],
        'is_live': True,
        'size_bytes': len(body),
        'image_count': len(re.findall(r'"imageUrl"', body)),
    }


def migrate_legacy(case: str, category: str):
    """Migrate a LEGACY case study file to silver/offers/."""
    legacy_map = {
        'baiyite': 'baiyite_full_line.json',
        'youyazi': 'youyazi_full_line.json',
        'socks': 'socks_full_50.json',
        'drill': 'drill_full_50.json',
    }
    legacy_path = DATA_ROOT / legacy_map[case]
    if not legacy_path.exists():
        return 0
    data = json.loads(legacy_path.read_text(encoding='utf-8'))
    migrated = 0

    for p in data['products']:
        # Baiyite uses mtop_offer_id, others use offer_id
        oid_str = p.get('mtop_offer_id') or p.get('offer_id')
        if not oid_str:
            continue
        offer_id = int(oid_str)

        # Baiyite uses mtop_enriched, others use enriched_detail
        me = p.get('mtop_enriched') or p.get('enriched_detail', {})
        rm = p.get('rak_match')

        # Build MTOP block — baiyite has different field names
        if case == 'baiyite':
            mtop_block = {
                'title': p.get('mtop_title'),
                'price_cny': p.get('mtop_price_cny'),
                'shop': me.get('loginid', 'unknown'),
                'booked': p.get('mtop_booked', 0),
                'category': category,
            }
        else:
            mtop_block = {
                'title': p.get('title'),
                'price_cny': p.get('price_cny'),
                'shop': p.get('shop', 'unknown'),
                'shop_text': p.get('shop_text'),
                'province': p.get('province'),
                'city': p.get('city'),
                'image_url': p.get('image_url'),
                'booked': p.get('booked', 0),
                'category': category,
            }

        # Build SU detail block
        su_block = None
        if me:
            if case == 'baiyite':
                su_block = {
                    'subject': me.get('title'),
                    'company': me.get('company'),
                    'loginid': me.get('loginid'),
                    'is_live': True,
                    'image_count': me.get('image_count', 0),
                    'page_kb': me.get('page_kb', 0),
                    'has_sku': bool(me.get('sku')),
                }
            else:
                su_block = {
                    'subject': me.get('subject'),
                    'company': me.get('company'),
                    'loginid': me.get('loginid'),
                    'is_live': me.get('is_live', False),
                    'size_bytes': me.get('size_bytes', 0),
                }

        # Build Rakumart block
        rak_block = None
        if rm and rm.get('match_score', 0) > 50:
            if case == 'baiyite':
                rak_block = {
                    'iid': rm.get('rak_iid'),
                    'title_cn': rm.get('rak_title_cn'),
                    'title_pt': rm.get('rak_title_pt'),
                    'price_brl': rm.get('rak_price_brl'),
                    'match_score': rm.get('match_score'),
                    'url': rm.get('rak_url'),
                }
            else:
                rak_block = {
                    'iid': rm.get('iid'),
                    'title_cn': rm.get('title_cn'),
                    'title_pt': rm.get('title_pt'),
                    'price_brl': rm.get('price_brl'),
                    'match_score': rm.get('match_score'),
                }

        silver = {
            'offer_id': offer_id,
            'bronze_refs': {
                'mtop': f'LEGACY: {case}_*.json (2026-06-17, pre-architecture)',
                'su_detail': f'LEGACY: {case}_*_enriched.json' if su_block and su_block.get('is_live') else None,
                'rakumart': f'LEGACY: {case}_full_*.json rak_match' if rak_block else None,
            },
            'mtop': mtop_block,
            'su_detail': su_block,
            'rakumart': rak_block,
            'enriched_at': '2026-06-17T00:00:00Z',
            'category': category,
        }

        out = SILVER / 'offers' / f'{offer_id}.json'
        out.write_text(json.dumps(silver, ensure_ascii=False, indent=2), encoding='utf-8')
        migrated += 1
    return migrated


def main():
    parser = argparse.ArgumentParser(description='Transform bronze raw data to silver offers')
    parser.add_argument('--date', default='2026-06-17', help='Date of bronze snapshots (YYYY-MM-DD)')
    parser.add_argument('--migrate-legacy', choices=['baiyite', 'youyazi', 'socks', 'drill', 'all'])
    args = parser.parse_args()

    if args.migrate_legacy:
        cat_map = {'baiyite': 'beach_clip', 'youyazi': 'underwear', 'socks': 'socks', 'drill': 'drill'}
        cases = ['baiyite', 'youyazi', 'socks', 'drill'] if args.migrate_legacy == 'all' else [args.migrate_legacy]
        total = 0
        for case in cases:
            n = migrate_legacy(case, cat_map[case])
            print(f'  Migrated {n} {case} offers to silver/')
            total += n
        print(f'\nTOTAL: {total} offers migrated to silver/offers/')


if __name__ == '__main__':
    main()
