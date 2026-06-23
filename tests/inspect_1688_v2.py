#!/usr/bin/env python3
"""
Test 1688 with Playwright + Decodo - simpler approach.
"""
import os
import time
from playwright.sync_api import sync_playwright

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

# Test 1: Detail page (known to work via curl)
DETAIL_URL = "https://detail.1688.com/offer/898549325479.html"

# Test 2: Search
SEARCH_URL = "https://s.1688.com/selloffer/offer_search.htm?keywords=无线领夹麦克风+K15"

# Test 3: Try alternative search URL  
ALT_SEARCH_URL = "https://s.1688.com/page/offer_search.htm?keywords=无线领夹麦克风+K15"

with sync_playwright() as p:
    browser = p.chromium.launch(
        headless=True,
        proxy={"server": proxy_url},
        args=['--disable-blink-features=AutomationControlled']
    )
    context = browser.new_context(
        user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36',
        locale='zh-CN',
        viewport={'width': 1366, 'height': 768},
    )
    page = context.new_page()
    
    # === Test 1: Detail page (quick test) ===
    print("\n[1] DETAIL PAGE (should work)")
    try:
        page.goto(DETAIL_URL, timeout=30000, wait_until='commit')
        page.wait_for_timeout(5000)
        title = page.title()
        print(f"  Title: {title}")
        has_window_context = page.evaluate("typeof window.context !== 'undefined'")
        print(f"  Has window.context: {has_window_context}")
        if "window.context" in page.content():
            print(f"  SUCCESS - real 1688 page loaded")
    except Exception as e:
        print(f"  Error: {e}")
    
    # === Test 2: Search page (try with commit) ===
    print("\n[2] SEARCH PAGE (try /selloffer/)")
    try:
        page.goto(SEARCH_URL, timeout=30000, wait_until='commit')
        page.wait_for_timeout(10000)  # Wait for JS
        title = page.title()
        print(f"  Title: {title}")
        print(f"  URL: {page.url}")
        
        # Check selectors
        for sel in ['.sm-offer-item', '[data-content]', 'a[href*="detail.1688.com"]', '.baxia-container']:
            try:
                count = page.query_selector_all(sel)
                if count:
                    print(f"  {sel}: {len(count)} elements")
            except:
                pass
        
        # Check body for captcha
        body = page.inner_text("body")[:500]
        print(f"  Body preview: {body[:200]}")
        if any(kw in body.lower() for kw in ['baxia', 'slider', 'verify', '滑块']):
            print("  !! CAPTCHA detected")
    except Exception as e:
        print(f"  Error: {e}")
    
    # === Test 3: Try /page/ search URL ===
    print("\n[3] SEARCH PAGE (try /page/)")
    try:
        page.goto(ALT_SEARCH_URL, timeout=30000, wait_until='commit')
        page.wait_for_timeout(10000)
        title = page.title()
        print(f"  Title: {title}")
        print(f"  URL: {page.url}")
        body = page.inner_text("body")[:300]
        print(f"  Body: {body[:200]}")
    except Exception as e:
        print(f"  Error: {e}")
    
    # === Test 4: s.1688.com root (landing) ===
    print("\n[4] S.1688.COM ROOT (landing page)")
    try:
        page.goto("https://s.1688.com/", timeout=30000, wait_until='commit')
        page.wait_for_timeout(8000)
        title = page.title()
        print(f"  Title: {title}")
        print(f"  URL: {page.url}")
    except Exception as e:
        print(f"  Error: {e}")
    
    browser.close()

print("\nDone!")
