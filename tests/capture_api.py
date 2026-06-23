#!/usr/bin/env python3
"""
Use Playwright to load search.m.1688.com and capture all API calls.
This will tell us which mtop API the search page uses.
"""
import os
import json
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

# Track all network requests
api_calls = []

with sync_playwright() as p:
    browser = p.chromium.launch(
        headless=True,
        proxy={"server": proxy_url},
    )
    context = browser.new_context(
        user_agent='Mozilla/5.0 (iPhone; CPU iPhone OS 14_0 like Mac OS X) AppleWebKit/605.1.15',
        locale='zh-CN',
        viewport={'width': 375, 'height': 812},  # iPhone size
    )
    page = context.new_page()
    
    # Capture all network requests
    def handle_request(request):
        url = request.url
        if any(kw in url for kw in ['1688.com', 'alicdn.com', 'mtop', 'h5api', 'search']):
            api_calls.append({
                "url": url[:200],
                "method": request.method,
            })
    
    def handle_response(response):
        url = response.url
        if any(kw in url for kw in ['h5api', 'mtop', 'search']):
            try:
                body = response.text()
                api_calls.append({
                    "response_url": url[:200],
                    "status": response.status,
                    "body_preview": body[:200] if body else None,
                })
            except:
                pass
    
    page.on("request", handle_request)
    page.on("response", handle_response)
    
    # Navigate
    query = "无线领夹麦克风"
    url = f"https://search.m.1688.com/index.htm?keywords={query}"
    print(f"Navigating to: {url}")
    
    try:
        page.goto(url, timeout=60000, wait_until='commit')
        print("Initial load OK, waiting for JS...")
        page.wait_for_timeout(15000)  # Wait for React to load
        
        # Try to type in search box and submit
        try:
            # Find search input
            search_input = page.query_selector('input[type="search"], input.search-input, .search-input')
            if search_input:
                search_input.fill(query)
                page.wait_for_timeout(1000)
                page.keyboard.press("Enter")
                print(f"Submitted search for: {query}")
                page.wait_for_timeout(10000)  # Wait for results
        except Exception as e:
            print(f"Search submit error: {e}")
        
    except Exception as e:
        print(f"Goto error: {e}")
    
    print(f"\nTotal network calls captured: {len(api_calls)}")
    
    # Filter for API-like calls
    api_only = [c for c in api_calls if 'h5api' in str(c) or 'mtop' in str(c) or '/api/' in str(c)]
    print(f"API calls: {len(api_only)}")
    
    for c in api_only[:30]:
        print(f"  {c}")
    
    # Save all calls
    with open("/tmp/api_calls.json", "w") as f:
        json.dump(api_calls, f, ensure_ascii=False, indent=2)
    print(f"\nSaved {len(api_calls)} calls to /tmp/api_calls.json")
    
    browser.close()

print("Done!")
