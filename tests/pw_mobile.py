#!/usr/bin/env python3
"""
Try mobile URLs and the homepage to find offers that don't need login.
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

QUERY = "无线领夹麦克风 K15"
ENCODED = urllib.parse.quote(QUERY)


with sync_playwright() as p:
    browser = p.chromium.launch(
        headless=True,
        proxy=PROXY,
        args=["--no-sandbox", "--disable-setuid-sandbox"]
    )
    # Mobile context
    context = browser.new_context(
        viewport={"width": 375, "height": 812},
        user_agent="Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.0 Mobile/15E148 Safari/604.1",
        locale="zh-CN",
        timezone_id="Asia/Hong_Kong",
    )
    page = context.new_page()

    urls = [
        # Mobile homepage (might have trending)
        ("m.1688.com home", "https://m.1688.com/"),
        # Mobile categories
        ("m.1688.com index", "https://m.1688.com/index.htm"),
        # 1688 mobile winport
        ("m.1688.com winport", "https://m.1688.com/winport/"),
        # 1688 mobile offer detail (try our known ID)
        ("m.1688.com offer detail", "https://m.1688.com/offer/740647797173.html"),
        # search.m.1688.com without keywords
        ("search.m.1688.com root", "https://search.m.1688.com/"),
        # 1688 homepage mobile
        ("m.1688.com home2", "https://m.1688.com/?src=desktop"),
        # 1688 main mobile (sale page)
        ("m.1688.com sale", "https://m.1688.com/sale/"),
        # 1688 offer list
        ("m.1688.com offerlist", "https://m.1688.com/offerlist.htm"),
        # 1688 h5api
        ("h5api.m.1688.com", "https://h5api.m.1688.com/h5/mtop.1688.ugc.service/1.0/"),
    ]

    results = []
    for label, url in urls:
        print(f"\n=== {label} ===", flush=True)
        print(f"URL: {url[:80]}", flush=True)
        try:
            response = page.goto(url, wait_until="domcontentloaded", timeout=25000)
            time.sleep(8)
            content = page.content()
            offers = list(set(re.findall(r'/offer/(\d+)\.html', content)))
            title = page.title()[:50]
            print(f"Status: {response.status if response else 'no'}", flush=True)
            print(f"Title: {title}", flush=True)
            print(f"Final URL: {page.url[:80]}", flush=True)
            print(f"Size: {len(content)}b", flush=True)
            print(f"Offers: {len(offers)}", flush=True)
            if offers:
                print(f"*** WORKS! First: {offers[:5]} ***", flush=True)
                results.append((label, offers, url))
        except Exception as e:
            print(f"Error: {str(e)[:200]}", flush=True)
        time.sleep(1)

    # Save best mobile result for inspection
    if results:
        best_label, best_offers, best_url = results[0]
        with open(f"/tmp/best_mobile.html", "w") as f:
            f.write(page.content())

    browser.close()

print(f"\n=== SUMMARY: {len(results)} URLs with offers ===", flush=True)
for label, offers, url in results:
    print(f"  {label}: {len(offers)} offers - {url}", flush=True)
