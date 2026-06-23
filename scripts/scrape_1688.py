#!/usr/bin/env python3
"""
1688-only scraper - clean, focused implementation.

Strategy:
- Decodo Site Unblocker bypasses BaXia CAPTCHA for detail pages
- window.context JSON contains all product data
- json.raw_decode for robust JSON extraction
- Search is NOT supported directly (use product IDs from any source)

Usage:
    from scrape_1688 import scrape_offer, parse_context

    html = scrape_offer("740647797173")
    ctx = parse_context(html)
    product = extract_product(ctx)
"""
import json
import re
import os
import subprocess
import time
from typing import Optional, Dict, Any
from pathlib import Path


# Load credentials from .env
ENV_PATH = Path(__file__).parent.parent / ".env"


def load_credentials() -> Dict[str, str]:
    """Load credentials from .env file."""
    env = {}
    if not ENV_PATH.exists():
        raise FileNotFoundError(f".env not found at {ENV_PATH}")
    with open(ENV_PATH) as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, v = line.split("=", 1)
            env[k.strip()] = v.strip()
    return env


# ============================================================
# HTTP LAYER - Decodo Site Unblocker
# ============================================================
class DecodoUnblocker:
    """Thin wrapper around Decodo Site Unblocker for 1688."""

    def __init__(self, credentials: Optional[Dict[str, str]] = None):
        self.creds = credentials or load_credentials()
        self.proxy = "https://unblock.decodo.com:60000"
        self.last_request_at = 0
        self.min_delay = 1.5  # seconds between requests

    def _throttle(self):
        """Ensure minimum delay between requests."""
        elapsed = time.time() - self.last_request_at
        if elapsed < self.min_delay:
            time.sleep(self.min_delay - elapsed)
        self.last_request_at = time.time()

    def get(self, url: str, geo: str = "China", locale: str = "zh-cn") -> str:
        """
        Fetch URL via Decodo Site Unblocker.

        Returns HTML body. Raises RuntimeError on block/error.
        """
        self._throttle()

        user = self.creds["DECODO_SU_USER"]
        pwd = self.creds["DECODO_SU_PASS"]

        cmd = [
            "curl", "-s", "-k",
            "-x", self.proxy,
            "-U", f"{user}:{pwd}",
            "-H", f"X-SU-Geo: {geo}",
            "-H", f"X-SU-Locale: {locale}",
            "-H", "User-Agent: Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36",
            "-H", "Accept-Language: zh-CN,zh;q=0.9",
            url,
            "--max-time", "30",
        ]

        result = subprocess.run(cmd, capture_output=True, text=True, timeout=35)

        if result.returncode != 0:
            raise RuntimeError(f"curl failed: {result.stderr[:200]}")

        html = result.stdout

        # Detect blocks
        if self._is_blocked(html):
            raise RuntimeError(f"Blocked by 1688 anti-bot ({len(html)} bytes)")

        return html

    def _is_blocked(self, html: str) -> bool:
        """Check if response is a CAPTCHA/block page."""
        if not html or len(html) < 1000:
            return True
        html_lower = html.lower()
        block_signals = [
            "baxia-punish",
            "_____tmd_____",
            "captchacapslide",
            "unusual traffic",
        ]
        return any(s in html_lower for s in block_signals)


# ============================================================
# PARSING LAYER - extract window.context
# ============================================================
def parse_context(html: str) -> Optional[Dict[str, Any]]:
    """
    Extract window.context JSON from 1688 detail page HTML.

    Uses json.raw_decode for accurate extraction.
    Falls back to field-by-field regex extraction if full parse fails.
    Returns None if no window.context found.
    """
    # Find the JSON start: )(window.contextPath, JSON);
    m = re.search(r"window\.contextPath,\s*", html)
    if not m:
        return None

    json_start = m.end()
    decoder = json.JSONDecoder()

    # Try full parse first
    try:
        data, _ = decoder.raw_decode(html, json_start)
        return data
    except json.JSONDecodeError as e:
        # Fallback: extract known fields with regex
        return _parse_context_fallback(html, json_start, e)


def _parse_context_fallback(html: str, json_start: int, error: json.JSONDecodeError) -> Dict[str, Any]:
    """
    Fallback parser: extract known fields with regex when full JSON parse fails.

    This is a degraded mode that still gets the most important fields.
    """
    result = {"result": {"data": {}, "meta": {}}, "error": str(error)}

    # Extract meta title
    title_match = re.search(r'"title"\s*:\s*"([^"]+)"', html[json_start:json_start+100000])
    if title_match:
        result["result"]["meta"]["title"] = title_match.group(1)

    # Extract subject (Chinese title from gallery)
    subject_match = re.search(r'"subject"\s*:\s*"([^"]+)"', html[json_start:json_start+200000])
    if subject_match:
        # Subject might be the first one which is usually the product title
        if not result["result"]["meta"].get("title"):
            result["result"]["meta"]["title"] = subject_match.group(1)

    # Extract images
    img_pattern = re.compile(r'https?://[^\s"]+\.(?:jpg|jpeg|png|webp)', re.IGNORECASE)
    images = list(set(img_pattern.findall(html[json_start:json_start+200000])))
    if images:
        # Filter out small icons
        images = [i for i in images if not any(s in i for s in ['16-16', '32-32', '64-64', 'logo', 'icon'])]
        # Filter to ibank/1688 product images
        product_imgs = [i for i in images if 'ibank' in i or 'cbu01' in i or 'imgextra' in i]
        if product_imgs:
            result["result"]["data"]["gallery"] = {
                "fields": {
                    "offerImgList": product_imgs[:10],
                    "mainImage": product_imgs[:5],
                }
            }

    # Extract offer ID
    offer_match = re.search(r'"offerId"\s*:\s*(\d+)', html[json_start:json_start+5000])
    if offer_match:
        result["offer_id"] = offer_match.group(1)

    return result


# ============================================================
# DATA EXTRACTION LAYER
# ============================================================
def extract_product(ctx: Dict[str, Any]) -> Dict[str, Any]:
    """
    Extract clean product data from window.context.

    Returns a flat dict with the most useful fields for an ML seller.
    """
    if not ctx or "result" not in ctx or "data" not in ctx["result"]:
        return {}

    components = ctx["result"]["data"]
    meta = ctx["result"].get("meta", {})

    product = {
        "offer_id": "",
        "title": "",
        "title_en": "",  # Will be filled by translation later
        "price": None,
        "currency": "CNY",
        "min_order_quantity": None,
        "sold_quantity": None,
        "monthly_sold": None,
        "images": [],
        "video_url": None,
        "specs": [],
        "weight_kg": None,
        "dimensions_cm": None,
        "company_name": "",
        "company_id": "",
        "company_url": "",
        "category_id": "",
        "raw": {},  # Full context for advanced use
    }

    # Title from meta
    if "title" in meta:
        product["title"] = meta["title"]
    elif "subject" in meta:
        product["title"] = meta["subject"]

    # Gallery: title, images, video
    gallery = components.get("gallery", {}).get("fields", {})
    if gallery:
        if "subject" in gallery and not product["title"]:
            product["title"] = gallery["subject"]
        imgs = gallery.get("offerImgList", []) or gallery.get("mainImage", [])
        product["images"] = imgs[:10]  # Cap at 10 images
        video = gallery.get("video", {})
        if video and isinstance(video, dict):
            product["video_url"] = video.get("videoUrl") or video.get("url")

    # SKU/Price
    sku = components.get("sku", {}).get("fields", {})
    if sku:
        sku_map = sku.get("skuInfoMap", {})
        if sku_map:
            first_sku = list(sku_map.values())[0]
            product["price"] = first_sku.get("price")
            product["currency"] = "CNY"
            product["sold_quantity"] = first_sku.get("saleCount")
            product["min_order_quantity"] = first_sku.get("canBookCount")
            # SKU attributes
            sku_attrs = sku.get("skuProps", [])
            for attr in sku_attrs:
                if isinstance(attr, dict) and "value" in attr:
                    product["specs"].append({
                        "name": attr.get("name", ""),
                        "values": [v.get("name", "") for v in attr.get("value", [])],
                    })

    # Price section
    for key in ["price", "priceSection", "trade"]:
        comp = components.get(key, {}).get("fields", {})
        if comp:
            if "price" in comp and not product["price"]:
                product["price"] = comp["price"]
            if "saleCount" in comp and not product["sold_quantity"]:
                product["sold_quantity"] = comp["saleCount"]
            if "monthSold" in comp and not product["monthly_sold"]:
                product["monthly_sold"] = comp["monthSold"]
            break

    # Trade info
    trade = components.get("trade", {}).get("fields", {})
    if trade:
        if "monthSold" in trade:
            product["monthly_sold"] = trade["monthSold"]
        if "saleCount" in trade:
            product["sold_quantity"] = trade["saleCount"]

    # Company/Seller
    for key in ["company", "sellerInfo", "shopInfo"]:
        comp = components.get(key, {}).get("fields", {})
        if comp:
            product["company_name"] = comp.get("companyName") or comp.get("name", "")
            product["company_id"] = str(comp.get("companyId") or comp.get("id", ""))
            product["company_url"] = comp.get("companyH5Url") or comp.get("url", "")
            break

    # Pack info (weight, dimensions)
    pack = components.get("productPackInfo", {}).get("fields", {})
    if pack:
        weight_g = pack.get("unitWeight")  # in grams
        if weight_g:
            product["weight_kg"] = float(weight_g) / 1000.0
        scale = pack.get("pieceWeightScale", {})
        if scale and scale.get("pieceWeightScaleInfo"):
            dims = scale["pieceWeightScaleInfo"][0]
            if dims.get("length") or dims.get("width") or dims.get("height"):
                product["dimensions_cm"] = {
                    "length": dims.get("length"),
                    "width": dims.get("width"),
                    "height": dims.get("height"),
                }

    # Category from URL
    product["category_id"] = str(components.get("description", {}).get("fields", {}).get("leafCategoryId", ""))

    # Offer ID
    if "offerId" in components.get("gallery", {}).get("fields", {}):
        product["offer_id"] = components["gallery"]["fields"]["offerId"]
    elif "id" in components.get("offerInfo", {}).get("fields", {}):
        product["offer_id"] = components["offerInfo"]["fields"]["id"]

    # Save raw for advanced use
    product["raw"] = {
        "component_count": len(components),
        "has_video": bool(product["video_url"]),
        "has_company": bool(product["company_name"]),
    }

    return product


# ============================================================
# HIGH-LEVEL API
# ============================================================
def scrape_offer(offer_id: str, client: Optional[DecodoUnblocker] = None) -> Optional[Dict[str, Any]]:
    """
    Scrape a single 1688 offer by ID.

    Returns a clean product dict, or None on failure.
    """
    if client is None:
        client = DecodoUnblocker()

    url = f"https://detail.1688.com/offer/{offer_id}.html"

    try:
        html = client.get(url)
    except RuntimeError as e:
        print(f"  Error fetching {offer_id}: {e}")
        return None

    try:
        ctx = parse_context(html)
    except ValueError as e:
        print(f"  Error parsing {offer_id}: {e}")
        return None

    if not ctx:
        print(f"  No window.context in {offer_id}")
        return None

    product = extract_product(ctx)
    if not product.get("offer_id"):
        product["offer_id"] = offer_id

    return product


def scrape_batch(offer_ids, output_path: Optional[str] = None, delay: float = 2.0):
    """
    Scrape multiple 1688 offers and save to JSON.
    """
    client = DecodoUnblocker()
    client.min_delay = delay

    results = []
    failed = []

    print(f"Scraping {len(offer_ids)} 1688 offers...")
    for i, offer_id in enumerate(offer_ids, 1):
        print(f"  [{i}/{len(offer_ids)}] {offer_id}...", end=" ", flush=True)
        product = scrape_offer(offer_id, client)
        if product:
            print(f"OK ({product.get('title', 'no title')[:40]})")
            results.append(product)
        else:
            print("FAIL")
            failed.append(offer_id)

    if output_path:
        with open(output_path, "w") as f:
            json.dump(results, f, ensure_ascii=False, indent=2)
        print(f"\nSaved {len(results)} products to {output_path}")

    if failed:
        print(f"\nFailed: {failed}")
        with open(output_path + ".failed", "w") as f:
            json.dump(failed, f, indent=2)

    return results, failed


# ============================================================
# CLI
# ============================================================
if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("Usage:")
        print("  python3 scrape_1688.py <offer_id>")
        print("  python3 scrape_1688.py --batch <file_with_ids> [output.json]")
        sys.exit(1)

    if sys.argv[1] == "--batch":
        ids_file = sys.argv[2]
        output = sys.argv[3] if len(sys.argv) > 3 else "data/batch.json"
        with open(ids_file) as f:
            ids = [line.strip() for line in f if line.strip()]
        scrape_batch(ids, output)
    else:
        offer_id = sys.argv[1]
        product = scrape_offer(offer_id)
        if product:
            print(json.dumps(product, ensure_ascii=False, indent=2))
        else:
            print("FAILED")
            sys.exit(1)
