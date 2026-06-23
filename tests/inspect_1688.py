#!/usr/bin/env python3
"""
Test 1688 search with Playwright + Decodo - inspect what page shows.
"""
import os
import sys
import time
from playwright.sync_api import sync_playwright

# Load env
with open("/mnt/ssd/1688-only/.env") as f:
    for line in f:
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        os.environ[k.strip()] = v.strip()

SU_USER = os.environ["DECODO_SU_USER"]
SU_PASS = os.environ["DECODO_SU_PASS"]

proxy_url = f"http://{SU_USER}:{SU_PASS}@unblock.decodo.com:60000"

query = "无线领夹麦克风 K15"
encoded = query.replace(' ', '+')
url = f'https://s.1688.com/selloffer/offer_search.htm?keywords={encoded}'

print(f"Query: {query}")
print(f"URL: {url}")
print(f"Proxy: unblock.decodo.com:60000")
print()

with sync_playwright() as p:
    browser = p.chromium.launch(
        headless=True,
        proxy={"server": proxy_url},
        args=[
            '--disable-blink-features=AutomationControlled',
            '--disable-web-security',
        ]
    )
    context = browser.new_context(
        user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        locale='zh-CN',
        timezone_id='Asia/Shanghai',
        viewport={'width': 1920, 'height': 1080},
    )
    page = context.new_page()
    
    print("Navigating...")
    try:
        page.goto(url, timeout=60000, wait_until='domcontentloaded')
    except Exception as e:
        print(f"Goto error: {e}")
    
    # Wait a bit for any JS to load
    page.wait_for_timeout(5000)
    
    # Take screenshot
    page.screenshot(path="/tmp/1688_search_test.png", full_page=True)
    print("Screenshot: /tmp/1688_search_test.png")
    
    # Save HTML
    html = page.content()
    with open("/tmp/1688_search_test.html", "w") as f:
        f.write(html)
    print(f"HTML: {len(html)} bytes")
    
    # Check what's on the page
    title = page.title()
    print(f"\nTitle: {title}")
    
    # Check for various 1688 product selectors
    selectors = [
        '.sm-offer-item',
        '.offer-list-row',
        '.sm-offer-list',
        '.offer-item',
        '[data-aplus-report]',
        'div[data-content="offer"]',
        '.baxia-container',
        'a[href*="detail.1688.com"]',
        'a[href*="offer/"]',
    ]
    
    for sel in selectors:
        try:
            count = page.query_selector_all(sel)
            print(f"  {sel}: {len(count)} elements")
        except:
            pass
    
    # Check for captcha
    body_text = page.inner_text("body")
    captcha_keywords = ['baxia', 'slider', 'verify', 'captcha', '滑块', '拖动', 'unusual traffic', '访问频次']
    print(f"\nBody text length: {len(body_text)}")
    print(f"First 300 chars: {body_text[:300]}")
    print(f"\nCaptcha signals:")
    for kw in captcha_keywords:
        if kw.lower() in body_text.lower():
            print(f"  !! {kw}")
    
    # Check URL (might have redirected)
    print(f"\nFinal URL: {page.url}")
    
    browser.close()

print("\nDone!")
