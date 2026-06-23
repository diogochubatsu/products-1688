#!/usr/bin/env python3
"""
Re-extract with PROPER price and detail extraction.
"""
import json
import re

def extract_clean(raw_data):
    """Extract real product fields from widget structure"""
    if not raw_data:
        return {}

    result = {}

    # TITLE from productTitle widget
    pt = raw_data.get("productTitle", {}).get("fields", {})
    result["title"] = pt.get("title", "")

    # Shop info (rateInfo has star rating)
    rate = pt.get("rateInfo", {})
    if isinstance(rate, dict):
        result["shop_name"] = rate.get("shopName") or rate.get("name", "")
        result["shop_id"] = rate.get("shopId", "")
        # Star rating breakdown
        if "rateStars" in rate:
            result["rating_stars"] = rate.get("rateStars", "")
    shop_info = pt.get("shopInfo", {})
    if isinstance(shop_info, dict):
        result["shop_name_2"] = shop_info.get("shopName") or shop_info.get("name", "")

    # Tag list
    tag_list = pt.get("tagList", [])
    if isinstance(tag_list, list):
        tags = []
        for t in tag_list:
            if isinstance(t, dict):
                tags.append(t.get("text") or t.get("name") or "")
        result["shop_tags"] = [t for t in tags if t]

    # GALLERY: images and video
    gallery = raw_data.get("gallery", {}).get("fields", {})
    result["subject"] = gallery.get("subject", "")

    img_list = gallery.get("offerImgList", [])
    images = []
    for img in img_list:
        if isinstance(img, dict):
            url = img.get("url") or img.get("imageUrl") or img.get("imgUrl") or img.get("img")
            if url:
                images.append(url)
        elif isinstance(img, str):
            images.append(img)
    result["images"] = images
    result["image_count"] = len(images)

    video = gallery.get("video", {})
    if isinstance(video, dict):
        result["video_id"] = video.get("videoId", "")
        result["has_video"] = bool(result["video_id"])
    else:
        result["has_video"] = False

    # DESCRIPTION: detail video and category
    desc = raw_data.get("description", {}).get("fields", {})
    detail_video = desc.get("detailVideoId", "")
    if detail_video and not result.get("video_id"):
        result["video_id"] = detail_video
        result["has_video"] = True
    result["leaf_category_id"] = desc.get("leafCategoryId", "")
    result["detail_url"] = desc.get("detailUrl", "")

    # PRICE: from mainPrice widget
    mp = raw_data.get("mainPrice", {}).get("fields", {})
    final = mp.get("finalPriceModel", {})
    twp = final.get("tradeWithoutPromotion", {}) if isinstance(final, dict) else {}

    result["price_min_cny"] = twp.get("offerMinPrice")
    result["price_max_cny"] = twp.get("offerMaxPrice")
    result["price_display"] = twp.get("offerPriceDisplay", "")
    result["begin_amount"] = twp.get("offerBeginAmount")  # min order qty
    result["available_stock"] = twp.get("canBookedAmountOriginal")

    # SKU options
    sku_map = twp.get("skuMapOriginal", [])
    if isinstance(sku_map, list):
        skus = []
        for s in sku_map[:5]:
            if isinstance(s, dict):
                skus.append({
                    "spec_attrs": s.get("specAttrs", ""),
                    "price": s.get("price", ""),
                    "discount_price": s.get("discountPrice", ""),
                    "sale_count": s.get("saleCount", 0),
                    "can_book_count": s.get("canBookCount", 0),
                })
        result["skus"] = skus

    # currentPrices
    current_prices = mp.get("priceModel", {}).get("currentPrices", [])
    if isinstance(current_prices, list) and current_prices:
        result["current_prices"] = [
            {"price": p.get("price"), "begin_amount": p.get("beginAmount")}
            for p in current_prices if isinstance(p, dict)
        ]

    # SHIPPING: weight and logistics
    ss = raw_data.get("shippingServices", {}).get("fields", {})
    if isinstance(ss, dict):
        weight = ss.get("unitWeight")
        if weight:
            try:
                result["weight_kg"] = float(weight) / 1000  # g to kg
            except (ValueError, TypeError):
                result["weight_kg"] = None
        result["post_fee"] = ss.get("postFeeValue")
        result["min_weight"] = ss.get("minWeight")

    # OFFER ID from sceneKey
    sk = raw_data.get("sceneKey", {}).get("fields", {})
    result["offer_id_confirmed"] = sk.get("offerId", "")

    return result

# Main
print("Re-extracting with proper field paths...")

with open("/mnt/ssd/1688-only/data/trending_products.json") as f:
    products = json.load(f)

re_processed = []
for p in products:
    raw = p.get("raw_data")
    if not raw:
        re_processed.append(p)
        continue

    extracted = extract_clean(raw)
    new_p = {**p}
    new_p.update(extracted)
    if "raw_data" in new_p:
        del new_p["raw_data"]
    re_processed.append(new_p)

with open("/mnt/ssd/1688-only/data/trending_products_v3.json", "w") as f:
    json.dump(re_processed, f, ensure_ascii=False, indent=2)

print(f"Saved to trending_products_v3.json")

# Stats
print(f"\n=== EXTRACTION STATS ===")
print(f"Total: {len(re_processed)}")
print(f"With title: {sum(1 for p in re_processed if p.get('title'))}")
print(f"With images: {sum(1 for p in re_processed if p.get('image_count', 0) > 0)}")
print(f"With video: {sum(1 for p in re_processed if p.get('has_video'))}")
print(f"With price: {sum(1 for p in re_processed if p.get('price_min_cny'))}")
print(f"With weight: {sum(1 for p in re_processed if p.get('weight_kg'))}")
print(f"With SKU options: {sum(1 for p in re_processed if p.get('skus'))}")

# Sample
print(f"\n=== SAMPLE WITH FULL DATA ===")
samples = [p for p in re_processed if p.get("title") and p.get("price_min_cny")][:5]
for s in samples:
    print(f"\n  Offer: {s['offer_id']}")
    print(f"  Title: {s.get('title','')[:50]}")
    print(f"  Price: {s.get('price_min_cny')}-{s.get('price_max_cny')} CNY")
    print(f"  MOQ: {s.get('begin_amount')}, Stock: {s.get('available_stock')}")
    print(f"  Images: {s.get('image_count',0)}, Video: {s.get('has_video',False)}")
    print(f"  Weight: {s.get('weight_kg')} kg")
    print(f"  SKUs: {len(s.get('skus',[]))}")
    if s.get('skus'):
        for sku in s['skus'][:3]:
            print(f"    - {sku.get('spec_attrs')}: {sku.get('price')} CNY (stock: {sku.get('can_book_count')})")
