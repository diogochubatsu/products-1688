#!/usr/bin/env python3
"""Robust 1688 window.context extraction using raw_decode"""
import os
import json
import subprocess
import re

ENV_PATH = "/mnt/ssd/1688-only/.env"

def load_env():
    env = {}
    with open(ENV_PATH) as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, v = line.split("=", 1)
            env[k.strip()] = v.strip()
    return env

ENV = load_env()


def curl_decodo(url, user, pwd):
    """Fetch 1688 page via Decodo Site Unblocker"""
    cmd = [
        "curl", "-s", "-k",
        "-x", "https://unblock.decodo.com:60000",
        "-U", f"{user}:{pwd}",
        "-H", "X-SU-Geo: China",
        "-H", "X-SU-Locale: zh-cn",
        "-H", "User-Agent: Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36",
        url,
        "--max-time", "30",
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=35)
    return result.stdout


def extract_window_context(html):
    """Extract window.context JSON using json.raw_decode for accuracy"""
    # Find the IIFE call: )(window.contextPath, JSON);
    # The JSON starts right after the comma+space following window.contextPath
    m = re.search(r"window\.contextPath,\s*", html)
    if not m:
        return None
    
    json_start = m.end()
    
    # Use raw_decode to find the actual JSON end
    decoder = json.JSONDecoder()
    try:
        data, end = decoder.raw_decode(html, json_start)
        return data
    except json.JSONDecodeError as e:
        # Debug: show what's at the error position
        pos = e.pos
        snippet = html[json_start+pos-50:json_start+pos+50]
        print(f"  JSON decode error at pos {pos}: {snippet!r}")
        return None


def summarize_product(data):
    """Extract key product fields"""
    summary = {}
    
    # The actual structure: data.result.data.<components>
    components = data.get("result", {}).get("data", {})
    
    # Title from meta
    meta = data.get("result", {}).get("meta", {})
    if meta:
        summary["title"] = meta.get("title", "")
        summary["keywords"] = meta.get("keywords", "")
    
    # Look for title in gallery
    gallery = components.get("gallery", {}).get("fields", {})
    if gallery:
        summary["image_count"] = len(gallery.get("images", []))
        if gallery.get("images"):
            summary["first_image"] = gallery["images"][0].get("url", "")
    
    # Look for SKU/pricing in skuProps
    sku_props = components.get("sku", {}).get("fields", {})
    if sku_props:
        sku_map = sku_props.get("skuInfoMap", {})
        if sku_map:
            summary["sku_count"] = len(sku_map)
            first = list(sku_map.values())[0]
            summary["first_sku_price"] = first.get("price")
            summary["first_sku_canBookCount"] = first.get("canBookCount")
    
    # Look for price/sales in priceSection or similar
    for key, val in components.items():
        if "price" in key.lower() and isinstance(val, dict):
            fields = val.get("fields", {})
            if "price" in fields:
                summary["price"] = fields["price"]
                if "saleCount" in fields:
                    summary["saleCount"] = fields["saleCount"]
                if "monthSold" in fields:
                    summary["monthSold"] = fields["monthSold"]
                break
    
    # Look for trade info
    trade = components.get("trade", {}).get("fields", {})
    if trade:
        for k, v in trade.items():
            if k not in summary:
                summary[f"trade_{k}"] = v
    
    return summary


if __name__ == "__main__":
    user = ENV["DECODO_SU_USER"]
    pwd = ENV["DECODO_SU_PASS"]
    
    products = [
        ("740647797173", "Carrot toy"),
        ("898549325479", "K15 lavalier mic"),
    ]
    
    print("="*60)
    print("EXTRACTING REAL 1688 PRODUCT DATA (fixed)")
    print("="*60)
    
    for offer_id, label in products:
        url = f"https://detail.1688.com/offer/{offer_id}.html"
        print(f"\n>>> {offer_id} ({label})")
        print(f"  URL: {url}")
        
        html = curl_decodo(url, user, pwd)
        print(f"  Response: {len(html)} bytes")
        
        if "window.context" not in html:
            print("  NO window.context - possibly blocked")
            continue
        
        ctx = extract_window_context(html)
        if not ctx:
            continue
        
        ctx_str = json.dumps(ctx, ensure_ascii=False)
        print(f"  window.context: {len(ctx_str)} bytes")
        
        summary = summarize_product(ctx)
        for k, v in summary.items():
            v_str = str(v)[:120] if v else "(empty)"
            print(f"  {k}: {v_str}")
        
        # Show top-level structure
        print(f"  Top keys: {list(ctx.keys())}")
        if "result" in ctx:
            r = ctx["result"]
            print(f"  result keys: {list(r.keys())}")
            if "data" in r:
                d = r["data"]
                print(f"  data has {len(d)} components: {list(d.keys())[:10]}")
    
    # Save full sample
    print("\n" + "="*60)
    print("SAVING FULL SAMPLE")
    print("="*60)
    html = curl_decodo("https://detail.1688.com/offer/898549325479.html", user, pwd)
    ctx = extract_window_context(html)
    if ctx:
        with open("/tmp/1688_k15_full.json", "w") as f:
            json.dump(ctx, f, ensure_ascii=False, indent=2)
        print(f"  Saved: {os.path.getsize('/tmp/1688_k15_full.json')} bytes")
        # Map out the structure
        if "result" in ctx and "data" in ctx["result"]:
            components = ctx["result"]["data"]
            print(f"\n  All {len(components)} components in data:")
            for comp_name, comp_data in components.items():
                if isinstance(comp_data, dict):
                    f = comp_data.get("fields", {})
                    print(f"    {comp_name}: {list(f.keys())[:8]}")
