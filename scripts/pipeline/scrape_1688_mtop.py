#!/usr/bin/env python3
"""
scrape_1688_mtop.py — 1688 search via MTOP API (QuoVadis86/ai-reverse SDK)

Bypasses BaXia 4-layer anti-bot by calling the same MTOP gateway the
1688 mobile app uses (h5api.m.1688.com). Login is automatic — no
proxy, no cookies, no browser needed.

Tested 2026-06-16: K15 无线麦克风 → 2000 found, 20 returned with
real offerId, title, price (¥), shop, province, city, factoryInspection,
bookedCount, image URL. Pagination works without overlap.

Usage:
  python3 scrape_1688_mtop.py "K15 无线麦克风" --pages 3 --size 20
  python3 scrape_1688_mtop.py "蓝牙耳机" --pages 5 --size 20 --json out.json
  python3 scrape_1688_mtop.py "袜子" --pages 2 --size 50 --save-bronze

Dependencies: requests>=2.28.0, plus ai-reverse SDK cloned to /tmp/scrapers-test/ai-reverse/1688
"""

import argparse
import json
import sys
import time
from pathlib import Path
from urllib.parse import unquote

# Add ai-reverse SDK to path
SDK_PATH = Path("/tmp/scrapers-test/ai-reverse/1688")
if not SDK_PATH.exists():
    print(f"ERROR: ai-reverse SDK not found at {SDK_PATH}", file=sys.stderr)
    print("Clone with: git clone https://github.com/QuoVadis86/ai-reverse /tmp/scrapers-test/ai-reverse", file=sys.stderr)
    sys.exit(1)
sys.path.insert(0, str(SDK_PATH))

from client import Alibaba1688Client  # type: ignore


def extract_item(item: dict) -> dict:
    """Normalize ai-reverse SDK item to flat dict with usable fields."""
    d = item.get("data", {})
    price_info = d.get("priceInfo", {})
    shop = d.get("shop") or {}
    return {
        "offer_id": d.get("offerId"),
        "title": d.get("title", "")
            .replace("<font color=red>", "")
            .replace("<font color>", "")
            .replace("</font>", "")
            .strip()[:200],
        "price_cny": price_info.get("price") if isinstance(price_info, dict) else None,
        "shop": unquote(shop.get("loginIdOfUtf8") or d.get("loginId") or ""),
        "province": d.get("province"),
        "city": d.get("city"),
        "biz_type": d.get("bizType"),
        "factory_inspection": d.get("factoryInspection"),
        "is_tp_member": d.get("isTp"),
        "booked_count": d.get("bookedCount"),
        "repurchase_rate": d.get("offerRepurchaseRate"),
        "image_url": d.get("offerPicUrl"),
        "detail_url": d.get("linkUrl"),
    }


def scrape(query: str, pages: int = 1, size: int = 20, save_bronze: bool = False) -> list[dict]:
    """Search 1688 and return flat list of products.

    If save_bronze=True, also save raw MTOP responses to data/bronze/mtop/.
    """
    client = Alibaba1688Client()
    if not client.session.login():
        print("ERROR: login failed", file=sys.stderr)
        return []

    # Lazy import save_bronze to avoid circular imports
    if save_bronze:
        from save_bronze import save_mtop_data

    results = []
    seen_ids = set()
    for page in range(1, pages + 1):
        resp = client.search_by_text(query, page=page, page_size=size)
        # Save bronze snapshot BEFORE filtering — preserves raw response
        if save_bronze:
            try:
                path = save_mtop_data(query, page, resp)
                # Only print on first page to avoid spam
                if page == 1:
                    print(f"  Saved bronze: {path}")
            except Exception as e:
                print(f"  WARN: failed to save bronze: {e}", file=sys.stderr)
        if not resp.success:
            print(f"WARN: page {page} returned {resp.ret}", file=sys.stderr)
            continue
        offer = (resp.data.get("data") or {}).get("OFFER") or {}
        items = offer.get("items") or []
        if not items:
            break  # no more results
        for it in items:
            flat = extract_item(it)
            if flat["offer_id"] and flat["offer_id"] not in seen_ids:
                seen_ids.add(flat["offer_id"])
                results.append(flat)
        # Be nice to the server
        time.sleep(0.3)
    return results


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("query", help="Search query (Chinese works best)")
    ap.add_argument("--pages", type=int, default=3, help="Number of pages to fetch (default 3)")
    ap.add_argument("--size", type=int, default=20, help="Items per page (default 20)")
    ap.add_argument("--json", help="Output JSON file path")
    ap.add_argument("--save-bronze", action="store_true",
                    help="Save raw MTOP responses to data/bronze/mtop/")
    args = ap.parse_args()

    print(f"Query: {args.query}")
    print(f"Pages: {args.pages}, Size: {args.size}")
    print(f"Save bronze: {args.save_bronze}")
    print()

    products = scrape(args.query, pages=args.pages, size=args.size, save_bronze=args.save_bronze)
    print(f"Total unique products: {len(products)}")
    print()

    # Print summary
    for i, p in enumerate(products[:10]):
        print(f"  {i+1}. offerId={p['offer_id']} ¥{p['price_cny']} {p['title'][:60]}")
        print(f"     shop={p['shop']} | {p['province']}/{p['city']} | factory={p['factory_inspection']} | booked={p['booked_count']}")
    if len(products) > 10:
        print(f"  ... and {len(products)-10} more")

    if args.json:
        out = {
            "query": args.query,
            "scraped_at": time.strftime("%Y-%m-%d %H:%M:%S"),
            "total": len(products),
            "products": products,
        }
        with open(args.json, "w", encoding="utf-8") as f:
            json.dump(out, f, ensure_ascii=False, indent=2)
        print(f"\nSaved to {args.json}")


if __name__ == "__main__":
    main()