#!/usr/bin/env python3
"""
upload_images.py — Download images from alicdn.com and upload to GCS bucket.

Usage:
  python3 scripts/upload_images.py              # upload all 530
  python3 scripts/upload_images.py --limit 10   # upload first 10
  python3 scripts/upload_images.py --dry-run    # preview without uploading
"""

import os
import sys
import json
import requests
from pathlib import Path
import argparse

os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = str(Path(__file__).parent.parent.parent / '.gcp-service-account.json')

from google.cloud import storage

DATA = Path(__file__).parent.parent.parent / 'data'
BUCKET_NAME = 'importasimples-intel-images'
PUBLIC_URL = f'https://storage.googleapis.com/{BUCKET_NAME}'

def upload_images(limit=None, dry_run=False):
    client = storage.Client(project='project-18ce40b8-a806-441c-9c4')
    bucket = client.bucket(BUCKET_NAME)
    
    offers_dir = DATA / 'silver' / 'offers'
    offer_files = sorted(offers_dir.glob('*.json'))
    if limit:
        offer_files = offer_files[:limit]
    
    print(f'Processing {len(offer_files)} offers')
    
    uploaded = 0
    skipped = 0
    errors = 0
    
    for f in offer_files:
        o = json.loads(f.read_text())
        oid = o.get('offer_id')
        image_url = (o.get('mtop') or {}).get('image_url')
        
        if not image_url:
            skipped += 1
            continue
        
        # GCS path: datalake/1688/{offer_id}/img-0.jpg
        gcs_path = f'datalake/1688/{oid}/img-0.jpg'
        
        # Check if already uploaded
        blob = bucket.blob(gcs_path)
        if blob.exists():
            skipped += 1
            continue
        
        if dry_run:
            print(f'  Would upload: {oid} -> {gcs_path}')
            uploaded += 1
            continue
        
        try:
            # Download from alicdn
            r = requests.get(image_url, timeout=10, headers={
                'User-Agent': 'Mozilla/5.0',
                'Referer': 'https://m.1688.com/'
            })
            if r.status_code != 200:
                print(f'  SKIP {oid}: HTTP {r.status_code}')
                errors += 1
                continue
            
            # Upload to GCS
            blob.upload_from_string(r.content, content_type='image/jpeg')
            uploaded += 1
            
            if uploaded % 50 == 0:
                print(f'  Progress: {uploaded} uploaded')
                
        except Exception as e:
            print(f'  ERROR {oid}: {e}')
            errors += 1
    
    print(f'\nDone: {uploaded} uploaded, {skipped} skipped, {errors} errors')
    
    # Update database with new image URLs
    if uploaded > 0 and not dry_run:
        update_database(offer_files)

def update_database(offer_files):
    """Update image_url in bronze_products with GCS URLs."""
    import psycopg2
    
    conn = psycopg2.connect(
        host='34.170.210.220', port=5432,
        dbname='importasimples_products', user='importasimples',
        password='R{[{f<VajbC{<kvU', sslmode='require'
    )
    cur = conn.cursor()
    
    updated = 0
    for f in offer_files:
        o = json.loads(f.read_text())
        oid = o.get('offer_id')
        image_url = (o.get('mtop') or {}).get('image_url')
        
        if not image_url:
            continue
        
        gcs_url = f'{PUBLIC_URL}/datalake/1688/{oid}/img-0.jpg'
        
        cur.execute(
            "UPDATE bronze_products SET image_url = %s WHERE source = 'datalake' AND source_id = %s",
            (gcs_url, str(oid))
        )
        updated += cur.rowcount
    
    conn.commit()
    print(f'Updated {updated} image_url in database')
    
    cur.close()
    conn.close()

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--limit', type=int, help='Limit number of uploads')
    parser.add_argument('--dry-run', action='store_true')
    args = parser.parse_args()
    upload_images(limit=args.limit, dry_run=args.dry_run)
