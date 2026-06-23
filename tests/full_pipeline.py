#!/usr/bin/env python3
"""
1688 trending pipeline:
1. Fetch trending pages to discover offer IDs
2. Use Decodo SU to fetch full product detail
3. Parse window.context JSON for structured data
4. Save to JSON output

This is the complete 1688-only pipeline.
"""
import os
import re
import sys
import json
import time
import subprocess
from urllib.parse import quote

# Load env
ENV_PATH = "/mnt/ssd/1688-only/.env"
env = {}
with open(ENV_PATH) as f:
    for line in f:
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        env[k.strip()] = v.strip()

SU_USER = env["DECODO_SU_USER"]
SU_PASS = env["DECODO_SU_PASS"]

# Trending pages
TRENDING_URLS = [
    "https://factory.1688.com/",
    "https://tongzhuang.1688.com/",
    "https://fuzhuang.1688.com/",
    "https://shipin.1688.com/",
    "https://321.1688.com/chengbiao.html",
    "https://321.1688.com/liangpin.html",
    "https://sale.1688.com/",
    "https://home.1688.com/",
    "https://food.1688.com/",
    "https://fangzhi.1688.com/",
    "https://suliao.1688.com/",
    "https://muying.1688.com/",
    "https://wanju.1688.com/",
    "https://gys.1688.com/",
    "https://sport.1688.com/",
]

OUTPUT_DIR = "/mnt/ssd/1688-only/data"

def curl_via_decodo(url, timeout=20):
    """Fetch URL through Decodo SU proxy"""
    cmd = [
        "curl", "-s", "-k", "-w", "\n%{http_code} %{size_download}",
        "-x", "https://unblock.decodo.com:60000",
        "-U", f"{SU_USER}:{SU_PASS}",
        "-H", f"X-SU-User: {SU_USER}",
        "-H", f"X-SU-Password: {SU_PASS}",
        "-H", "X-SU-Geo: China",
        "-H", "X-SU-Locale: zh-cn",
        url, "--max-time", str(timeout),
        "-o", "/tmp/pipeline_fetch.html"
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout+5)
    try:
        with open("/tmp/pipeline_fetch.html") as f:
            html = f.read()
        return html
    except FileNotFoundError:
        return ""

def discover_offer_ids(html):
    """Extract offer IDs from HTML"""
    patterns = [
        r'/offer/(\d+)\.html',
        r'"offerId":\s*"?(\d+)',
        r'data-offer-id="(\d+)"',
        r'"goodsId":\s*"?(\d+)',
    ]
    ids = set()
    for p in patterns:
        for m in re.findall(p, html):
            if 8 <= len(m) <= 12 and m.isdigit():
                ids.add(m)
    return ids

def parse_context(html):
    """Extract window.context JSON from 1688 detail page"""
    m = re.search(r"window\.contextPath,\s*", html)
    if not m:
        return None
    json_text = html[m.end():]
    try:
        decoder = json.JSONDecoder(strict=False)
        obj, end = decoder.raw_decode(json_text)
        return obj
    except json.JSONDecodeError:
        return None

def extract_product_data(offer_id, context_obj):
    """Extract key product fields from window.context"""
    try:
        data = context_obj.get("result", {}).get("data", {})

        # Get offer info
        offer = data.get("offerStructMap", {}).get(str(offer_id), {}) if isinstance(data.get("offerStructMap"), dict) else {}

        # Get gallery
        gallery = data.get("gallery", {})

        # Get title
        subject = data.get("subject", "") or gallery.get("subject", "")

        # Get images
        images = []
        for img_list_key in ["offerImgList", "images", "mainImages"]:
            img_list = gallery.get(img_list_key, [])
            if img_list:
                images = [img.get("url") if isinstance(img, dict) else img for img in img_list]
                break
        if not images:
            # Try the data directly
            for key in ["images", "mainImage", "mainImages"]:
                if key in data:
                    val = data[key]
                    if isinstance(val, list):
                        images = [v.get("url") if isinstance(v, dict) else v for v in val if v]
                    elif isinstance(val, str):
                        images = [val]
                    break

        # Get price
        price = None
        for price_key in ["price", "minPrice", "skuPrice", "currentPrice"]:
            for parent_key in ["skuModel", "priceModel", "skuCoreInfo"]:
                p = data.get(parent_key, {})
                if isinstance(p, dict):
                    v = p.get(price_key)
                    if v:
                        price = v
                        break
            if price:
                break

        return {
            "offer_id": offer_id,
            "title": subject,
            "images": images[:5],  # Limit to 5
            "price": price,
            "has_video": bool(data.get("video", {}).get("videoId")),
            "video_id": data.get("video", {}).get("videoId"),
            "raw_data": data,  # Keep raw for inspection
        }
    except Exception as e:
        return {"offer_id": offer_id, "error": str(e)}

# ==== MAIN PIPELINE ====
print("="*60)
print("1688 TRENDING PRODUCT PIPELINE")
print("="*60)

# Phase 1: Discover
print("\n[PHASE 1] Discovering trending offer IDs...")
all_offers = {}  # offer_id -> [sources]
for url in TRENDING_URLS:
    label = url.split("//")[1].split(".")[0] + "." + url.split("//")[1].split(".")[1]
    print(f"  Fetching {label}...", flush=True)
    html = curl_via_decodo(url)
    if not html:
        continue
    ids = discover_offer_ids(html)
    for oid in ids:
        all_offers.setdefault(oid, []).append(label)
    print(f"    Found {len(ids)} IDs", flush=True)
    time.sleep(0.8)

print(f"\n  Total unique: {len(all_offers)}")
offer_ids = list(all_offers.keys())

# Save discovered offer IDs
os.makedirs(OUTPUT_DIR, exist_ok=True)
with open(f"{OUTPUT_DIR}/trending_offer_ids.json", "w") as f:
    json.dump({
        "total": len(offer_ids),
        "sources_count": len(TRENDING_URLS),
        "offers": {oid: srcs for oid, srcs in all_offers.items()},
    }, f, ensure_ascii=False, indent=2)
print(f"  Saved to {OUTPUT_DIR}/trending_offer_ids.json")

# Phase 2: Fetch details
print(f"\n[PHASE 2] Fetching details for {len(offer_ids)} products...")
products = []
for i, oid in enumerate(offer_ids):
    if i > 0 and i % 20 == 0:
        print(f"  Progress: {i}/{len(offer_ids)}", flush=True)

    url = f"https://detail.1688.com/offer/{oid}.html"
    html = curl_via_decodo(url, timeout=25)
    if not html or "baxia" in html.lower() or "_____tmd_____" in html:
        products.append({"offer_id": oid, "sources": all_offers[oid], "status": "blocked"})
        continue

    # Check for window.context
    if "window.context" not in html:
        products.append({"offer_id": oid, "sources": all_offers[oid], "status": "no_context"})
        continue

    ctx = parse_context(html)
    if not ctx:
        products.append({"offer_id": oid, "sources": all_offers[oid], "status": "json_error"})
        continue

    # Extract product data
    data = extract_product_data(oid, ctx)
    if data:
        data["sources"] = all_offers[oid]
        data["status"] = "ok"
        products.append(data)
    else:
        products.append({"offer_id": oid, "sources": all_offers[oid], "status": "parse_error"})

    time.sleep(2.0)  # Rate limit

# Phase 3: Save
print(f"\n[PHASE 3] Saving {len(products)} products...")

# Save full results
with open(f"{OUTPUT_DIR}/trending_products.json", "w") as f:
    json.dump(products, f, ensure_ascii=False, indent=2)

# Save summary
ok = [p for p in products if p.get("status") == "ok"]
blocked = [p for p in products if p.get("status") == "blocked"]
no_ctx = [p for p in products if p.get("status") == "no_context"]
err = [p for p in products if p.get("status") in ("json_error", "parse_error")]

print(f"\n  Total: {len(products)}")
print(f"  OK:    {len(ok)} ({100*len(ok)//len(products)}%)")
print(f"  Blocked: {len(blocked)}")
print(f"  No context: {len(no_ctx)}")
print(f"  Errors:  {len(err)}")

# Save a simple CSV of OK products
csv_path = f"{OUTPUT_DIR}/trending_products.csv"
with open(csv_path, "w") as f:
    f.write("offer_id,title,price,images_count,has_video,sources_count,sources\n")
    for p in ok:
        f.write(f'"{p.get("offer_id","")}","{p.get("title","")[:80]}",{p.get("price","")},{len(p.get("images",[]))},{p.get("has_video",False)},{len(p.get("sources",[]))},"{",".join(p.get("sources",[]))}"\n')
print(f"\n  CSV saved to {csv_path}")

print(f"\nFull data saved to {OUTPUT_DIR}/trending_products.json")
