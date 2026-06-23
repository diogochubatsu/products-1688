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
    """Parse Decodo SU HTML to extract shop_name only (simplified schema)."""
    if not html_path.exists() or html_path.stat().st_size < 10000:
        return {}

    body = html_path.read_text(encoding='utf-8', errors='ignore')
    company = (re.search(r'"companyName"\s*:\s*"([^"]{2,100})"', body) or [None, None])[1]
    return {'shop_name': company} if company else {}


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
            }
        else:
            mtop_block = {
                'title': p.get('title'),
                'price_cny': p.get('price_cny'),
                'shop': p.get('shop', 'unknown'),
                'image_url': p.get('image_url'),
            }

        # Build SU detail block
        su_block = None
        if me:
            su_block = {'shop_name': me.get('company') or me.get('loginid')}

        # Build Rakumart block
        rak_block = None
        if rm and rm.get('match_score', 0) > 50:
            rak_block = {
                'title_br': rm.get('rak_title_pt') or rm.get('title_pt'),
                'price_brl': rm.get('rak_price_brl') or rm.get('price_brl'),
                'match_score': rm.get('match_score'),
                'url': rm.get('rak_url') or rm.get('url'),
            }

        silver = {
            'offer_id': offer_id,
            'mtop': mtop_block,
            'su_detail': su_block or {},
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
