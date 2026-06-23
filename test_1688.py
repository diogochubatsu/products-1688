#!/usr/bin/env python3
"""1688-only scraper - Firecrawl + Decodo SU with proper auth"""
import os
import sys
import json
import base64
import subprocess
import urllib.request
import urllib.error

def load_env(path="/mnt/ssd/1688-only/.env"):
    env = {}
    with open(path) as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, v = line.split("=", 1)
            env[k.strip()] = v.strip()
    return env

ENV = load_env()
print(f"Loaded {len(ENV)} credentials\n")


def check_block(text):
    """Check if response is a CAPTCHA block"""
    if not text:
        return "empty"
    text_lower = text.lower()
    for kw in ["baxia", "_____tmd_____", "unusual traffic", "拖动到最右边", "滑块"]:
        if kw in text_lower:
            return kw
    return None


# ============================================================
# SCRAPER 1: Decodo Site Unblocker (via curl subprocess)
# ============================================================
def scrape_decodo_su(url, label):
    """Use curl to handle proxy auth properly"""
    print(f"\n{'='*60}")
    print(f"[DECODO-SU] {label}")
    print(f"  URL: {url[:80]}")
    
    user = ENV["DECODO_SU_USER"]
    pwd = ENV["DECODO_SU_PASS"]
    
    cmd = [
        "curl", "-s", "-k",
        "-x", "https://unblock.decodo.com:60000",
        "-U", f"{user}:{pwd}",
        "-H", "X-SU-Geo: China",
        "-H", "X-SU-Locale: zh-cn",
        "-H", "User-Agent: Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36",
        "-o", "/tmp/decodo_response.html",
        "-w", "%{http_code} %{size_download}",
        url,
        "--max-time", "30",
    ]
    
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=35)
        output = result.stdout.strip()
        parts = output.split()
        http_code = parts[0] if parts else "?"
        size = int(parts[1]) if len(parts) > 1 else 0
        
        print(f"  HTTP: {http_code}  Size: {size} bytes")
        
        if os.path.exists("/tmp/decodo_response.html"):
            with open("/tmp/decodo_response.html") as f:
                html = f.read()
            block = check_block(html)
            if block:
                print(f"  !! BLOCKED: {block}")
                return None, html
            
            # Check for real product data
            if "window.context" in html:
                print(f"  OK: Real product page (has window.context)")
            return html, html
        
        return None, ""
    except subprocess.TimeoutExpired:
        print("  TIMEOUT")
        return None, ""
    except Exception as e:
        print(f"  ERROR: {e}")
        return None, ""


# ============================================================
# SCRAPER 2: Decodo Scraping API
# ============================================================
def scrape_decodo_api(url, label, headless="html"):
    print(f"\n{'='*60}")
    print(f"[DECODO-API] {label}")
    print(f"  URL: {url[:80]}")
    
    user = ENV["DECODO_SCRAPE_USER"]
    pwd = ENV["DECODO_SCRAPE_PASS"]
    auth_b64 = base64.b64encode(f"{user}:{pwd}".encode()).decode()
    
    payload = json.dumps({
        "url": url,
        "proxy_pool": "standard",
        "headless": headless,
        "geo": "China",
        "locale": "zh-cn",
    }).encode()
    
    req = urllib.request.Request(
        "https://scraper-api.decodo.com/v2/scrape",
        data=payload,
        headers={
            "Authorization": f"Basic {auth_b64}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        }
    )
    
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            result = json.loads(resp.read())
        success = result.get("success", False)
        print(f"  Success: {success}  Status: {result.get('status', '?')}")
        
        if not success:
            err = result.get("error") or result.get("message") or "unknown"
            print(f"  Error: {err}")
            return None
        
        d = result.get("data", {})
        md = d.get("markdown", "") or d.get("content", "")
        print(f"  Content: {len(md)} chars")
        
        block = check_block(md)
        if block:
            print(f"  !! BLOCKED: {block}")
            return None
        
        return result
    except urllib.error.HTTPError as e:
        print(f"  HTTP {e.code}: {e.read().decode()[:200]}")
        return None
    except Exception as e:
        print(f"  ERROR: {e}")
        return None


# ============================================================
# SCRAPER 3: Firecrawl v2
# ============================================================
def scrape_firecrawl(url, label, formats=None):
    print(f"\n{'='*60}")
    print(f"[FIRECRAWL] {label}")
    print(f"  URL: {url[:80]}")
    
    formats = formats or ["markdown"]
    payload = json.dumps({
        "url": url,
        "formats": formats,
        "onlyMainContent": False,
    }).encode()
    
    req = urllib.request.Request(
        "https://api.firecrawl.dev/v2/scrape",
        data=payload,
        headers={
            "Authorization": f"Bearer {ENV['FIRECRAWL_API_KEY']}",
            "Content-Type": "application/json",
        }
    )
    
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            result = json.loads(resp.read())
        success = result.get("success", False)
        print(f"  Success: {success}")
        
        if not success:
            err = result.get("error", "unknown")
            print(f"  Error: {err}")
            return None
        
        d = result.get("data", {})
        md = d.get("markdown", "")
        title = d.get("metadata", {}).get("title", "")
        print(f"  Title: {title[:80]}")
        print(f"  Content: {len(md)} chars")
        
        block = check_block(md)
        if block:
            print(f"  !! BLOCKED: {block}")
            return None
        
        return result
    except urllib.error.HTTPError as e:
        print(f"  HTTP {e.code}: {e.read().decode()[:200]}")
        return None
    except Exception as e:
        print(f"  ERROR: {e}")
        return None


# ============================================================
# Parse 1688 window.context from HTML
# ============================================================
import re

def extract_window_context(html):
    """Extract window.context JSON from 1688 detail page HTML"""
    # Pattern: window.context=(function(...)(window.contextPath, {...JSON...}))
    m = re.search(r"window\.context=\(function\([^)]*\)\([^)]*,\s*", html)
    if not m:
        return None
    
    start = m.end() - 1  # at the {
    depth = 0
    in_string = False
    escape = False
    end = start
    for i in range(start, min(start + 500000, len(html))):
        c = html[i]
        if escape:
            escape = False
            continue
        if c == "\\":
            escape = True
            continue
        if c == '"':
            in_string = not in_string
            continue
        if in_string:
            continue
        if c == "{":
            depth += 1
        elif c == "}":
            depth -= 1
            if depth == 0:
                end = i + 1
                break
    
    json_str = html[start:end]
    try:
        return json.loads(json_str)
    except:
        return None


# ============================================================
# MAIN
# ============================================================
if __name__ == "__main__":
    print("="*60)
    print("1688-ONLY SCRAPER - Detailed test")
    print("="*60)
    
    URL_DETAIL = "https://detail.1688.com/offer/740647797173.html"
    URL_DETAIL_2 = "https://detail.1688.com/offer/898549325479.html"  # K15 mic
    URL_SEARCH = "https://s.1688.com/page/offer_search.htm?keywords=无线领夹麦克风+K15"
    URL_FACTORY = "https://sale.1688.com/factory/index.html"
    
    # 1) Decodo SU - detail
    html, _ = scrape_decodo_su(URL_DETAIL, "Detail 740647797173 (carrot toy)")
    if html:
        ctx = extract_window_context(html)
        if ctx:
            print(f"  EXTRACTED window.context: {len(json.dumps(ctx))} bytes")
            # Show some key fields
            try:
                data = ctx.get("result", {}).get("data", {})
                title = data.get("title", "N/A")
                price = data.get("price", "N/A")
                print(f"  Title: {title[:80]}")
                print(f"  Price: {price}")
                if "skuModel" in data:
                    print(f"  SKU models: {len(data['skuModel'].get('skuInfoMap', {}))}")
                if "gallery" in data:
                    print(f"  Gallery images: {len(data['gallery'].get('images', []))}")
            except Exception as e:
                print(f"  Error reading context: {e}")
    
    # 2) Firecrawl - detail (mic product)
    result = scrape_firecrawl(URL_DETAIL_2, "Detail 898549325479 (K15 mic)")
    
    # 3) Firecrawl - search
    result = scrape_firecrawl(URL_SEARCH, "Search wireless lapel K15")
    
    # 4) Firecrawl - factory search by URL
    result = scrape_firecrawl(
        "https://sale.1688.com/factory/index.html?keywords=无线领夹麦克风",
        "Factory with search"
    )
    
    print("\n" + "="*60)
    print("DONE")
