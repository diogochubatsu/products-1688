#!/usr/bin/env python3
"""
migrate_to_importa.py — Migrate silver offers to ImportaSimples bronze_products table.

Source: /mnt/ssd/1688-only/data/silver/offers/*.json
Destination: GCP Cloud SQL → importasimples_products.bronze_products

Usage:
  python3 scripts/migrate_to_importa.py              # migrate all 294
  python3 scripts/migrate_to_importa.py --dry-run    # preview SQL
  python3 scripts/migrate_to_importa.py --batch 50   # custom batch size
"""

import json
import sys
from pathlib import Path
from datetime import datetime
import argparse

DATA = Path(__file__).parent.parent.parent / 'data'

# ── ImportaSimples connection ──
DB_CONFIG = {
    'host': '34.170.210.220',
    'port': 5432,
    'dbname': 'importasimples_products',
    'user': 'importasimples',
    'password': 'R{[{f<VajbC{<kvU',
    'sslmode': 'require',
    'connect_timeout': 15,
}

UPSERT_SQL = """
INSERT INTO bronze_products (
    source, source_id, marketplace,
    title, title_cn,
    image_url, image_count,
    price, currency, price_cny, price_brl,
    url, product_url,
    category_raw, category_level,
    category_l1, category_l2, category_l3, category_l4,
    supplier_name,
    monthly_sales,
    raw_data,
    scraped_at, silver_processed, script_name
) VALUES (
    %s, %s, %s,
    %s, %s,
    %s, %s,
    %s, %s, %s, %s,
    %s, %s,
    %s, %s,
    %s, %s, %s, %s,
    %s,
    %s,
    %s,
    NOW(), FALSE, %s
)
ON CONFLICT (source, source_id)
DO UPDATE SET
    title = EXCLUDED.title,
    title_cn = EXCLUDED.title_cn,
    image_url = EXCLUDED.image_url,
    price_brl = EXCLUDED.price_brl,
    url = EXCLUDED.url,
    supplier_name = EXCLUDED.supplier_name,
    monthly_sales = EXCLUDED.monthly_sales,
    category_l1 = EXCLUDED.category_l1,
    category_l2 = EXCLUDED.category_l2,
    category_l3 = EXCLUDED.category_l3,
    category_l4 = EXCLUDED.category_l4,
    raw_data = EXCLUDED.raw_data,
    scraped_at = NOW()
"""


def load_offer(path: Path) -> dict:
    """Load silver offer and map to bronze_products columns."""
    o = json.loads(path.read_text())

    mtop = o.get('mtop') or {}
    rak = o.get('rakumart') or {}
    su = o.get('su_detail') or {}
    tax = o.get('taxonomy') or {}

    # title = Portuguese (primary display), fallback to Chinese
    title_br = rak.get('title_br', '')
    title_cn = mtop.get('title', '')
    title = title_br if title_br else title_cn

    # Category path
    cat_raw = o.get('category', '')
    n1 = tax.get('n1', '')
    n2 = tax.get('n2', '')
    n3 = tax.get('n3', '')
    n4 = tax.get('n4', '')

    # Count non-empty taxonomy levels
    cat_level = sum(1 for x in [n1, n2, n3, n4] if x)

    # Price
    price_cny = mtop.get('price_cny')
    price_brl = rak.get('price_brl')
    price = price_cny  # native price (CNY)

    # Image
    image_url = mtop.get('image_url')

    # URL
    source_url = rak.get('url', '')  # Rakumart preferred
    product_url = source_url if source_url else f'https://detail.1688.com/offer/{o["offer_id"]}.html'

    rd = o.get('raw_data') or {}

    # Raw data (audit trail)
    raw_data = {
        'title_br': title_br if title_br else None,
        'offer_id': o.get('offer_id'),
        'category': cat_raw,
        'shop': mtop.get('shop'),
        'match_score': rak.get('match_score'),
        'booked': rd.get('booked') if isinstance(rd, dict) else None,
    }

    return (
        'datalake',                    # source
        str(o['offer_id']),            # source_id
        '1688',                        # marketplace
        title,                         # title (PT or CN)
        title_cn,                      # title_cn (always CN)
        image_url,                     # image_url
        1 if image_url else None,      # image_count
        price,                         # price (native CNY)
        'CNY',                         # currency
        price_cny,                     # price_cny
        price_brl,                     # price_brl
        source_url,                    # url
        product_url,                   # product_url
        cat_raw,                       # category_raw
        cat_level,                     # category_level
        n1 or None,                    # category_l1
        n2 or None,                    # category_l2
        n3 or None,                    # category_l3
        n4 or None,                    # category_l4
        su.get('shop_name'),           # supplier_name
        (rd := o.get('raw_data') or {}).get('booked') if isinstance(rd, dict) else None,  # monthly_sales
        json.dumps(raw_data, ensure_ascii=False),  # raw_data
        'scrape_1688_mtop.py',             # script_name
    )


def main():
    parser = argparse.ArgumentParser(description='Migrate silver to ImportaSimples')
    parser.add_argument('--dry-run', action='store_true', help='Preview without writing')
    parser.add_argument('--batch', type=int, default=100, help='Batch size (default 100)')
    args = parser.parse_args()

    # Load all offers
    offers_dir = DATA / 'silver' / 'offers'
    offer_files = sorted(offers_dir.glob('*.json'))
    print(f'Found {len(offer_files)} silver offers')

    # Map all offers
    rows = []
    errors = 0
    for f in offer_files:
        try:
            row = load_offer(f)
            rows.append(row)
        except Exception as e:
            print(f'  ERROR: {f.name}: {e}')
            errors += 1

    print(f'Mapped: {len(rows)} rows, {errors} errors')

    if args.dry_run:
        print('\n=== DRY RUN — SQL Preview ===')
        print(UPSERT_SQL)
        print(f'\nFirst row values:')
        for i, v in enumerate(rows[0]):
            print(f'  {i}: {repr(v)[:80]}')
        return

    # Connect and migrate
    import psycopg2
    print(f'\nConnecting to {DB_CONFIG["host"]}...')
    conn = psycopg2.connect(**DB_CONFIG)
    cur = conn.cursor()

    # Check current count
    cur.execute("SELECT COUNT(*) FROM bronze_products WHERE source = 'datalake'")
    current = cur.fetchone()[0]
    print(f'Current datalake rows: {current}')

    # Batch insert
    inserted = 0
    updated = 0
    for i in range(0, len(rows), args.batch):
        batch = rows[i:i+args.batch]
        try:
            cur.execute('BEGIN')
            for row in batch:
                cur.execute(UPSERT_SQL, row)
                # Check if it was INSERT or UPDATE
                if cur.rowcount == 1:
                    inserted += 1
                else:
                    updated += 1
            cur.execute('COMMIT')
            print(f'  Batch {i//args.batch + 1}: {len(batch)} rows committed')
        except Exception as e:
            cur.execute('ROLLBACK')
            print(f'  Batch {i//args.batch + 1}: ERROR — {e}')
            break

    # Final count
    cur.execute("SELECT COUNT(*) FROM bronze_products WHERE source = 'datalake'")
    final = cur.fetchone()[0]
    print(f'\nFinal datalake rows: {final} (was {current})')
    print(f'Inserted: {inserted}, Updated: {updated}')

    cur.close()
    conn.close()
    print('Done!')


if __name__ == '__main__':
    main()
