#!/usr/bin/env python3
"""
Test multiple 1688 direct scraping approaches.
Goal: find at least ONE working search/discovery path.
"""
import subprocess
import json
import urllib.request
import urllib.error
import base64
import re
import os
import sys

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


def curl_decodo(url, user, pwd, extra_headers=None, timeout=30):
    """Fetch via Decodo Site Unblocker (curl)."""
    cmd = [
        "curl", "-s", "-k",
        "-x", "https://unblock.decodo.com:60000",
        "-U", f"{user}:{pwd}",
        "-H", "X-SU-Geo: China",
        "-H", "X-SU-Locale: zh-cn",
        "-H", "User-Agent: Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36",
        "-H", "Accept-Language: zh-CN,zh;q=0.9",
    ]
    if extra_headers:
        for h in extra_headers:
            cmd.extend(["-H", h])
    cmd.extend([url, "--max-time", str(timeout)])
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout+5)
    return result.stdout, result.returncode


def curl_firecrawl(url, api_key, formats=None, wait=False):
    """Fetch via Firecrawl v2 API."""
    formats = formats or ["markdown"]
    payload = {
        "url": url,
        "formats": formats,
    }
    if wait:
        payload["waitFor"] = 3000
    req = urllib.request.Request(
        "https://api.firecrawl.dev/v2/scrape",
        data=json.dumps(payload).encode(),
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return json.loads(resp.read())
    except Exception as e:
        return {"error": str(e)}


def decodo_scraping_api(url, user, pwd, headless="html", geo="China"):
    """Fetch via Decodo Scraping API (JS rendering)."""
    auth_b64 = base64.b64encode(f"{user}:{pwd}".encode()).decode()
    payload = json.dumps({
        "url": url,
        "proxy_pool": "standard",
        "headless": headless,
        "geo": geo,
        "locale": "zh-cn",
    }).encode()
    req = urllib.request.Request(
        "https://scraper-api.decodo.com/v2/scrape",
        data=payload,
        headers={
            "Authorization": f"Basic {auth_b64}",
            "Content-Type": "application/json",
        }
    )
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            return json.loads(resp.read())
    except urllib.error.HTTPError as e:
        return {"error": f"HTTP {e.code}: {e.read().decode()[:200]}"}
    except Exception as e:
        return {"error": str(e)}


def check_block(text):
    if not text:
        return "empty"
    text_lower = text.lower() if isinstance(text, str) else ""
    for kw in ["baxia", "_____tmd_____", "unusual traffic", "拖动到最右边", "captcha", "verify", "滑块"]:
        if kw in text_lower:
            return kw
    return None


def report(label, text_or_result, is_html=True):
    """Print status of a fetch result."""
    if isinstance(text_or_result, dict):
        if "error" in text_or_result:
            print(f"  [{label}] ERROR: {text_or_result['error'][:100]}")
            return
        text = text_or_result.get("data", {}).get("markdown", "") or text_or_result.get("data", {}).get("content", "")
        title = text_or_result.get("data", {}).get("metadata", {}).get("title", "")
    else:
        text = text_or_result
        title = ""

    block = check_block(text)
    if block:
        print(f"  [{label}] BLOCKED ({block}) - {len(text)} bytes")
        return
    print(f"  [{label}] OK - {len(text)} bytes" + (f" - title: {title[:50]}" if title else ""))
    return text


if __name__ == "__main__":
    print("="*70)
    print("1688 DIRECT - TRY EVERYTHING")
    print("="*70)

    su_user = ENV["DECODO_SU_USER"]
    su_pass = ENV["DECODO_SU_PASS"]
    fc_key = ENV["FIRECRAWL_API_KEY"]
    api_user = ENV["DECODO_SCRAPE_USER"]
    api_pass = ENV["DECODO_SCRAPE_PASS"]

    # =========================================================
    # TEST 1: 1688 mobile API endpoints
    # =========================================================
    print("\n[1] 1688 MOBILE API ENDPOINTS")
    mobile_urls = [
        "https://h5api.m.1688.com/h5/mtop.1688.searchoffer.search/1.0/?appKey=portalsite&t=1737000000&jsv=2.5.1&v=1.0&type=jsonp&dataType=jsonp&data=%7B%22keywords%22%3A%22%E9%A2%86%E5%A4%B9%E9%BA%A6%E5%85%8B%E9%A3%8E+K15%22%2C%22page%22%3A1%7D",
        "https://m.1688.com/offer_search/-C9CFD3B4A1A4D3A3C2A6.html?keywords=%E9%A2%86%E5%A4%B9%E9%BA%A6%E5%85%8B%E9%A3%8E",
    ]
    for url in mobile_urls:
        text, code = curl_decodo(url, su_user, su_pass)
        report("Decodo-SU", text)

    # =========================================================
    # TEST 2: Decodo Scraping API with JS rendering
    # =========================================================
    print("\n[2] DECODO SCRAPING API (JS rendering, slower)")
    search_urls = [
        "https://s.1688.com/page/offer_search.htm?keywords=无线领夹麦克风+K15",
        "https://s.1688.com/selloffer/offer_search.htm?keywords=无线领夹麦克风+K15",
    ]
    for url in search_urls:
        result = decodo_scraping_api(url, api_user, api_pass, headless="html")
        report("Decodo-API", result)

    # =========================================================
    # TEST 3: 1688 factory pages (different subdomain)
    # =========================================================
    print("\n[3] 1688 FACTORY / CXT SUBDOMAINS")
    factory_urls = [
        "https://cxt.1688.com/factory/search.html?keywords=无线领夹麦克风",
        "https://qjy.1688.com/",
        "https://winport.1688.com/page/searchoffer.htm?keywords=无线领夹麦克风",
        "https://sale.1688.com/factory/factorySearch.htm?keywords=无线领夹麦克风",
    ]
    for url in factory_urls:
        text, code = curl_decodo(url, su_user, su_pass)
        report("Decodo-SU", text)

    # =========================================================
    # TEST 4: Taobao as proxy (find 1688 items via Taobao)
    # =========================================================
    print("\n[4] TAOBAO SEARCH (K15 mic)")
    taobao_urls = [
        "https://s.taobao.com/search?q=无线领夹麦克风+K15",
        "https://h5api.m.taobao.com/h5/mtop.relationrecommend.wirelessrecommend.recommend/2.0/?appKey=12574478&t=1737000000&jsv=2.5.1&v=2.0&type=jsonp&dataType=jsonp&data=%7B%22pageSize%22%3A20%2C%22pageNum%22%3A1%7D",
    ]
    for url in taobao_urls:
        text, code = curl_decodo(url, su_user, su_pass)
        report("Decodo-SU", text)

    # =========================================================
    # TEST 5: Bing search for 1688 URLs
    # =========================================================
    print("\n[5] BING / DUCKDUCKGO FOR 1688 URLS")
    search_urls = [
        "https://www.bing.com/search?q=site%3Adetail.1688.com+%E9%A2%86%E5%A4%B9%E9%BA%A6%E5%85%8B%E9%A3%8E+K15",
        "https://duckduckgo.com/html/?q=site%3Adetail.1688.com+K15+microphone",
    ]
    for url in search_urls:
        result = curl_firecrawl(url, fc_key)
        report("Firecrawl", result)

    # =========================================================
    # TEST 6: Firecrawl with waitFor on 1688 factory search
    # =========================================================
    print("\n[6] FIRECRAWL WITH WAIT ON FACTORY SEARCH")
    fc_urls = [
        "https://sale.1688.com/factory/index.html?keywords=无线领夹麦克风",
    ]
    for url in fc_urls:
        result = curl_firecrawl(url, fc_key, wait=True)
        report("Firecrawl-wait", result)

    # =========================================================
    # TEST 7: Try mobile factory URL with Firecrawl
    # =========================================================
    print("\n[7] FIRECRAWL MOBILE FACTORY")
    fc_urls = [
        "https://m.1688.com/factorySearch.html?keywords=无线领夹麦克风",
    ]
    for url in fc_urls:
        result = curl_firecrawl(url, fc_key)
        report("Firecrawl", result)

    print("\n" + "="*70)
    print("DONE - check above for any OK results")
    print("="*70)
