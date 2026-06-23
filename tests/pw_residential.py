#!/usr/bin/env python3
"""
Test 1688 search with REAL browser (Playwright) through HK residential proxy.
Maybe BaXia only flags curl TLS fingerprint, not real Chrome.
"""
import os
import re
import time
import sys
from playwright.sync_api import sync_playwright

# Proxy config
PROXY = {
    "server": "isp.decodo.com:10001",
    "username": "user-sp2idylm9q-country-hk",
    "password": "J41Ytm9rgWofr=V2nr",
}

# Use the venv that has playwright
sys.path.insert(0, "/mnt/ssd/1688-intel/scripts/arbitlens")

# Search query (URL-encoded)
QUERY = "无线领夹麦克风 K15"
import urllib.parse
ENCODED = urllib.parse.quote(QUERY)

URLS = [
    f"https://s.1688.com/selloffer/offer_search.htm?keywords={ENCODED}",
    f"https://m.1688.com/page/offerSearch.htm?keywords={ENCODED}",
    f"https://s.1688.com/selloffer/offer_search.htm",
]

print(f"Search query: {QUERY}")
print(f"Proxy: {PROXY['server']}\n", flush=True)

with sync_playwright() as p:
    browser = p.chromium.launch(
        headless=True,
        proxy=PROXY,
        args=[
            "--no-sandbox",
            "--disable-setuid-sandbox",
            "--disable-blink-features=AutomationControlled"
        ]
    )
    context = browser.new_context(
        viewport={"width": 1280, "height": 720},
        user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        locale="zh-CN",
        timezone_id="Asia/Hong_Kong",
    )
    page = context.new_page()

    for i, url in enumerate(URLS):
        print(f"=== Test {i+1}: {url[:60]} ===", flush=True)
        try:
            response = page.goto(url, wait_until="domcontentloaded", timeout=20000)
            print(f"  Status: {response.status if response else 'no response'}", flush=True)
            time.sleep(3)
            content = page.content()
            offers = len(set(re.findall(r'/offer/(\d+)\.html', content)))
            title = page.title()[:60]
            print(f"  Title: {title}", flush=True)
            print(f"  URL after redirects: {page.url[:80]}", flush=True)
            print(f"  Content size: {len(content)}b", flush=True)
            print(f"  Offers: {offers}", flush=True)

            if offers > 0:
                print(f"  *** BROWSE WORKS! ***", flush=True)
                found = list(set(re.findall(r'/offer/(\d+)\.html', content)))[:5]
                for o in found:
                    print(f"    - {o}", flush=True)
            else:
                # Save content for inspection
                with open(f"/tmp/pw_test_{i+1}.html", "w") as f:
                    f.write(content)
                # Check what's there
                if "_____tmd_____" in content:
                    print(f"  Status: BaXia block", flush=True)
                elif "login" in content.lower():
                    print(f"  Status: Login redirect", flush=True)
                elif "captcha" in content.lower() or "verify" in content.lower():
                    print(f"  Status: Captcha challenge", flush=True)
                else:
                    print(f"  Status: Other (check /tmp/pw_test_{i+1}.html)", flush=True)
                    # Show first 200 chars
                    print(f"  Body preview: {content[:200]}", flush=True)
        except Exception as e:
            print(f"  Error: {e}", flush=True)
        time.sleep(2)

    browser.close()

print("\nDone!", flush=True)
