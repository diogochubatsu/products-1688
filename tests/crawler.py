#!/usr/bin/env python3
"""
1688 product graph crawler.
Strategy: Start with seed offer IDs, fetch mobile detail (which returns
~27 related products), chain to get hundreds of products.
No login required. Uses HK residential proxy + Playwright.
"""
import os
import re
import time
import json
import sys
import urllib.parse
import argparse
from playwright.sync_api import sync_playwright


PROXY = {
    "server": "isp.decodo.com:10001",
    "username": "user-sp2idylm9q-country-hk",
    "password": "J41Ytm9rgWofr=V2nr",
}

# Seed offer IDs (K15 mic, carrot toy, etc)
SEEDS = [
    "740647797173",  # Carrot toy
    "898549325479",  # K15 mic
]


def fetch_offer_related(page, offer_id, retries=2):
    """Fetch mobile detail page and extract related offer IDs"""
    url = f"https://m.1688.com/offer/{offer_id}.html"
    for attempt in range(retries):
        try:
            page.goto(url, wait_until="domcontentloaded", timeout=25000)
            time.sleep(8)  # Wait for JS to load
            content = page.content()

            # Extract all offer IDs
            all_ids = list(set(re.findall(r'/offer/(\d+)\.html', content)))

            # Find the title of THIS product
            title_m = re.search(r'<title>(.*?)</title>', content)
            title = title_m.group(1) if title_m else ""

            # Get the product image (first one)
            img_match = re.search(r'src="([^"]*cbu01\.alicdn\.com[^"]+)"', content)
            img = img_match.group(1) if img_match else None

            # Get price (look for ¥ symbol)
            price_m = re.search(r'¥\s*(\d+(?:\.\d+)?)', content)
            price = price_m.group(1) if price_m else None

            return {
                "offer_id": offer_id,
                "title": title[:100],
                "price": price,
                "image": img,
                "related_offers": [oid for oid in all_ids if oid != offer_id],
                "url": url,
                "fetched_at": time.time(),
            }
        except Exception as e:
            if attempt < retries - 1:
                time.sleep(3)
                continue
            return {"offer_id": offer_id, "error": str(e)[:200]}
    return {"offer_id": offer_id, "error": "max retries"}


def crawl(seeds, max_depth=3, max_products=200):
    """BFS crawl from seeds following related offers"""
    visited = set()
    queue = [(s, 0) for s in seeds]  # (offer_id, depth)
    results = {}

    print(f"Starting crawl with {len(seeds)} seeds, max_depth={max_depth}, max_products={max_products}", flush=True)
    print(f"Queue size: {len(queue)}\n", flush=True)

    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=True,
            proxy=PROXY,
            args=["--no-sandbox", "--disable-setuid-sandbox"]
        )
        context = browser.new_context(
            viewport={"width": 375, "height": 812},
            user_agent="Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.0 Mobile/15E148 Safari/604.1",
            locale="zh-CN",
            timezone_id="Asia/Hong_Kong",
        )
        page = context.new_page()

        while queue and len(visited) < max_products:
            offer_id, depth = queue.pop(0)
            if offer_id in visited:
                continue
            if depth > max_depth:
                continue

            visited.add(offer_id)
            data = fetch_offer_related(page, offer_id)

            if "error" in data:
                print(f"  [{len(visited):3}] {offer_id} d={depth} ERROR: {data['error'][:50]}", flush=True)
                continue

            related_count = len(data.get("related_offers", []))
            print(f"  [{len(visited):3}] {offer_id} d={depth} title={data['title'][:30]:30} price={data.get('price')} related={related_count}", flush=True)

            results[offer_id] = data

            # Add related to queue
            for rel_id in data.get("related_offers", []):
                if rel_id not in visited and len(visited) + len(queue) < max_products * 2:
                    queue.append((rel_id, depth + 1))

            time.sleep(0.5)  # Polite delay

        browser.close()

    return results


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--max-depth", type=int, default=3)
    parser.add_argument("--max-products", type=int, default=100)
    parser.add_argument("--output", default="/mnt/ssd/1688-only/data/crawl_results.json")
    args = parser.parse_args()

    results = crawl(SEEDS, max_depth=args.max_depth, max_products=args.max_products)

    # Save
    os.makedirs(os.path.dirname(args.output), exist_ok=True)
    with open(args.output, "w") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)

    # Summary
    print(f"\n=== CRAWL COMPLETE ===", flush=True)
    print(f"Total products: {len(results)}", flush=True)
    with_title = sum(1 for r in results.values() if r.get("title"))
    with_price = sum(1 for r in results.values() if r.get("price"))
    print(f"  With title: {with_title}", flush=True)
    print(f"  With price: {with_price}", flush=True)
    print(f"  Saved to: {args.output}", flush=True)

    # Show sample titles
    print(f"\n=== Sample products (first 10) ===", flush=True)
    for r in list(results.values())[:10]:
        print(f"  {r.get('offer_id')}: {r.get('title', '(no title)')[:50]} - {r.get('price')} - {len(r.get('related_offers', []))} related", flush=True)
