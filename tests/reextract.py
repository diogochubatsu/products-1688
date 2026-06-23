#!/usr/bin/env python3
"""
Re-extract product data using the real widget structure.
The new 1688 format uses widget-based structure with meta.scriptFileName hints.
"""
import os
import re
import sys
import json
import time
import subprocess

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

def curl_via_decodo(url, timeout=20):
    cmd = [
        "curl", "-s", "-k", "-w", "\n%{http_code} %{size_download}",
        "-x", "https://unblock.decodo.com:60000",
        "-U", f"{SU_USER}:{SU_PASS}",
        "-H", f"X-SU-User: {SU_USER}",
        "-H", f"X-SU-Password: {SU_PASS}",
        "-H", "X-SU-Geo: China",
        url, "--max-time", str(timeout),
        "-o", "/tmp/re_fetch.html"
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout+5)
    try:
        with open("/tmp/re_fetch.html") as f:
            return f.read()
    except FileNotFoundError:
        return ""

def parse_context(html):
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

def extract_clean(raw_data):
    """Extract real product fields from widget structure"""
    if not raw_data:
        return {}

    result = {}

    # Title from productTitle widget
    pt = raw_data.get("productTitle", {}).get("fields", {})
    result["title"] = pt.get("title", "")

    # Shop info
    shop = pt.get("shopInfo", {})
    if isinstance(shop, dict):
        result["shop_name"] = shop.get("shopName") or shop.get("name", "")
        result["shop_url"] = shop.get("shopUrl", "")

    # Gallery / images
    gallery = raw_data.get("gallery", {}).get("fields", {})
    result["subject"] = gallery.get("subject", "")
    img_list = gallery.get("offerImgList", [])
    images = []
    for img in img_list:
        if isinstance(img, dict):
            url = img.get("url") or img.get("imageUrl") or img.get("imgUrl")
            if url:
                images.append(url)
        elif isinstance(img, str):
            images.append(img)
    result["images"] = images
    result["image_count"] = len(images)

    # Video
    video = gallery.get("video", {})
    if isinstance(video, dict):
        result["video_id"] = video.get("videoId", "")
        result["has_video"] = bool(result["video_id"])
    else:
        result["has_video"] = False

    # Main price
    price_widget = raw_data.get("mainPrice", {}).get("fields", {})
    final_price = price_widget.get("finalPriceModel", {})
    if isinstance(final_price, dict):
        result["price_cny"] = final_price.get("price") or final_price.get("finalPrice")
    else:
        result["price_cny"] = None

    # Description widget has detail video
    desc = raw_data.get("description", {}).get("fields", {})
    detail_video = desc.get("detailVideoId", "")
    if detail_video and not result.get("video_id"):
        result["video_id"] = detail_video
        result["has_video"] = True

    # Category
    result["leaf_category_id"] = desc.get("leafCategoryId", "")

    # Attributes / specs - parse from productAttributes widget
    attrs_widget = raw_data.get("productAttributes", {}).get("fields", {})
    if isinstance(attrs_widget, dict):
        # Skip meta and find specs
        specs = []
        for k, v in attrs_widget.items():
            if k not in ("uiType", "label") and isinstance(v, list):
                for item in v:
                    if isinstance(item, dict):
                        specs.append({
                            "name": item.get("attrName") or item.get("name", ""),
                            "value": item.get("value") or item.get("attrValue", ""),
                        })
        result["specs"] = specs[:20]

    # SKU / variants - skuSelection
    sku = raw_data.get("skuSelection", {}).get("fields", {})
    if isinstance(sku, dict):
        result["sku_info"] = {k: v for k, v in sku.items() if k != "uiType" and k != "label"}

    # Root data has dataJson with main data
    root = raw_data.get("Root", {}).get("fields", {})
    data_json_str = root.get("dataJson", "")
    if data_json_str and isinstance(data_json_str, str) and len(data_json_str) > 100:
        try:
            dj = json.loads(data_json_str)
            result["root_data_keys"] = list(dj.keys())[:20] if isinstance(dj, dict) else []
            if isinstance(dj, dict):
                # Look for important data
                for k in ["offerId", "shopName", "categoryName", "subject"]:
                    if k in dj:
                        result[f"root_{k}"] = dj[k]
        except (json.JSONDecodeError, ValueError):
            pass

    return result

# ==== MAIN ====
print("Re-extracting 383 products with proper field extraction...")

# Load existing data
with open("/mnt/ssd/1688-only/data/trending_products.json") as f:
    products = json.load(f)

# Re-fetch and re-parse
re_processed = []
for i, p in enumerate(products):
    if i % 50 == 0:
        print(f"  Progress: {i}/{len(products)}", flush=True)

    # Use cached raw_data
    raw = p.get("raw_data")
    if not raw:
        re_processed.append(p)
        continue

    extracted = extract_clean(raw)
    # Merge with existing
    new_p = {**p}
    new_p.update(extracted)
    # Remove huge raw_data
    if "raw_data" in new_p:
        del new_p["raw_data"]
    re_processed.append(new_p)

# Save
with open("/mnt/ssd/1688-only/data/trending_products_v2.json", "w") as f:
    json.dump(re_processed, f, ensure_ascii=False, indent=2)

print(f"\nSaved to /mnt/ssd/1688-only/data/trending_products_v2.json")

# Stats
with_title = [p for p in re_processed if p.get("title")]
with_imgs = [p for p in re_processed if p.get("image_count", 0) > 0]
with_video = [p for p in re_processed if p.get("has_video")]
with_price = [p for p in re_processed if p.get("price_cny")]

print(f"\n=== EXTRACTION STATS ===")
print(f"With title: {len(with_title)}/{len(re_processed)}")
print(f"With images: {len(with_imgs)}/{len(re_processed)}")
print(f"With video: {len(with_video)}/{len(re_processed)}")
print(f"With price: {len(with_price)}/{len(re_processed)}")

# Sample
print(f"\n=== SAMPLE WITH FULL DATA ===")
samples = [p for p in re_processed if p.get("title") and p.get("image_count", 0) > 0][:5]
for s in samples:
    print(f"\n  Offer: {s['offer_id']}")
    print(f"  Title: {s.get('title','')[:60]}")
    print(f"  Subject: {s.get('subject','')[:60]}")
    print(f"  Images: {s.get('image_count',0)}, Video: {s.get('has_video',False)}")
    print(f"  Price: {s.get('price_cny')}")
    print(f"  Shop: {s.get('shop_name','')[:30]}")
    print(f"  Specs: {len(s.get('specs',[]))} items")
