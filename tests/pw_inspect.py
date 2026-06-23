#!/usr/bin/env python3
"""
Look at actual mobile HTML to see how offers are embedded.
"""
import os
import re
import time
import urllib.parse
import sys

from playwright.sync_api import sync_playwright

PROXY = {
    "server": "isp.decodo.com:10001",
    "username": "user-sp2idylm9q-country-hk",
    "password": "J41Ytm9rgWofr=V2nr",
}

with sync_playwright() as p:
    browser = p.chromium.launch(
        headless=True,
        proxy=PROXY,
        args=["--no-sandbox", "--disable-setuid-sandbox"]
    )
    context = browser.new_context(
        viewport={"width": 375, "height": 812},
        user_agent="Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.0 Mobile/15E148 Safari/604.1",
        locale="zh-CN",
        timezone_id="Asia/Hong_Kong",
    )
    page = context.new_page()

    # Mobile homepage
    print("=== MOBILE HOMEPAGE ===\n", flush=True)
    page.goto("https://m.1688.com/", wait_until="domcontentloaded", timeout=25000)
    time.sleep(12)

    # Save the HTML
    with open("/tmp/mobile_home.html", "w") as f:
        f.write(page.content())
    print(f"Size: {os.path.getsize('/tmp/mobile_home.html')}\n", flush=True)

    # Get all offer IDs
    with open("/tmp/mobile_home.html") as f:
        content = f.read()

    # Find all offer contexts
    offers = list(set(re.findall(r'/offer/(\d+)\.html', content)))
    print(f"Total offer IDs: {len(offers)}", flush=True)
    print(f"Offers: {offers[:20]}\n", flush=True)

    # Look for each offer's context
    for oid in offers[:5]:
        # Find a small window around the offer
        idx = content.find(f"/offer/{oid}.html")
        if idx > 0:
            window = content[max(0, idx-300):idx+500]
            # Strip script/style
            window = re.sub(r'<script[^>]*>.*?</script>', '', window, flags=re.DOTALL)
            print(f"--- Offer {oid} context ---", flush=True)
            print(f"  {window[:500]}\n", flush=True)

    # Mobile offer detail
    print("\n=== MOBILE OFFER DETAIL (related products) ===\n", flush=True)
    page.goto("https://m.1688.com/offer/740647797173.html", wait_until="domcontentloaded", timeout=30000)
    time.sleep(15)
    content = page.content()
    offers = list(set(re.findall(r'/offer/(\d+)\.html', content)))
    print(f"Total offer IDs on detail: {len(offers)}", flush=True)
    print(f"Offers: {offers[:20]}\n", flush=True)

    # Save for inspection
    with open("/tmp/mobile_detail.html", "w") as f:
        f.write(content)
    print(f"Size: {os.path.getsize('/tmp/mobile_detail.html')}", flush=True)

    # Find the section with related products
    related_idx = content.find("看了又看")
    if related_idx < 0:
        related_idx = content.find("为你推荐")
    if related_idx < 0:
        related_idx = content.find("猜你喜欢")
    if related_idx < 0:
        related_idx = content.find("相似")
    if related_idx < 0:
        # Just look for the second batch of offer IDs
        for oid in offers:
            if oid != "740647797173":
                idx = content.find(f"/offer/{oid}.html")
                if idx > 0:
                    print(f"\nFirst related product '{oid}' at position {idx}", flush=True)
                    window = content[max(0, idx-200):idx+400]
                    print(window[:600], flush=True)
                    break

    browser.close()
