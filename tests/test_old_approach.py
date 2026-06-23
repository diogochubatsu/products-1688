#!/usr/bin/env python3
"""
Test the OLD 1688 search approach with NEW Decodo credentials.
This was working before, just needs the new SU creds.
"""
import sys
import os
import json
import time
import subprocess

# Set env vars from our .env file
ENV_PATH = "/mnt/ssd/1688-only/.env"
env = {}
with open(ENV_PATH) as f:
    for line in f:
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        env[k.strip()] = v.strip()

os.environ["SU_USER"] = env["DECODO_SU_USER"]
os.environ["SU_PASS"] = env["DECODO_SU_PASS"]

# Now import the old scraper
sys.path.insert(0, "/mnt/ssd/1688-intel/scripts/arbitlens")
from scrape_1688_direct import scrape_1688_direct

print("="*70)
print("TESTING OLD APPROACH: Playwright + Decodo on 1688 search")
print("="*70)
print(f"User: {os.environ['SU_USER']}")
print()

query = "无线领夹麦克风 K15"
print(f"Query: {query}")
print(f"Starting scrape...")
start = time.time()
try:
    products = scrape_1688_direct(query, limit=10)
    elapsed = time.time() - start
    print(f"\nCompleted in {elapsed:.1f}s")
    print(f"Got {len(products)} products\n")

    for i, p in enumerate(products[:5], 1):
        print(f"  [{i}] {p.product_name[:60]}")
        print(f"      Price: {p.price_low} {p.price_currency}")
        print(f"      Image: {p.image_url[:80] if p.image_url else 'none'}")
        print(f"      ID: {p.source_product_id}")
        print(f"      URL: {p.source_url[:80]}")
        print()

    # Save for use
    output = []
    for p in products:
        output.append({
            "product_name": p.product_name,
            "price": p.price_low,
            "currency": p.price_currency,
            "image_url": p.image_url,
            "offer_id": p.source_product_id,
            "url": p.source_url,
            "source": p.source_platform,
        })

    with open("/mnt/ssd/1688-only/data/old_approach_results.json", "w") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)
    print(f"Saved {len(output)} to data/old_approach_results.json")
except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()
