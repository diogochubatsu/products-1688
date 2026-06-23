#!/usr/bin/env python3
"""
Try multiple strategies with Playwright + HK residential:
1. Visit homepage first to get cookies, then search
2. Wait longer for JS to load products
3. Try different search URL patterns
"""
import os
import re
import time
import urllib.parse
import json
import sys

from playwright.sync_api import sync_playwright

PROXY = {
    "server": "isp.decodo.com:10001",
    "username": "user-sp2idylm9q-country-hk",
    "password": "J41Ytm9rgWofr=V2nr",
}

QUERY = "无线领夹麦克风 K15"
ENCODED = urllib.parse.quote(QUERY)


def try_search(page, url, label, wait_seconds=10):
    print(f"\n=== {label} ===", flush=True)
    print(f"URL: {url[:80]}", flush=True)
    try:
        response = page.goto(url, wait_until="domcontentloaded", timeout=30000)
        print(f"Initial status: {response.status if response else 'none'}", flush=True)
        # Wait for JS to load products
        time.sleep(wait_seconds)
        content = page.content()
        url_after = page.url
        offers = list(set(re.findall(r'/offer/(\d+)\.html', content)))
        title = page.title()[:60]
        print(f"After {wait_seconds}s - Title: {title}", flush=True)
        print(f"Final URL: {url_after[:80]}", flush=True)
        print(f"Content size: {len(content)}b", flush=True)
        print(f"Offers: {len(offers)}", flush=True)
        if offers:
            print(f"*** WORKS! First offers: {offers[:5]} ***", flush=True)
            return offers
        # Check what we got
        if "login.taobao.com" in url_after or "login.1688.com" in url_after:
            print(f"  Status: LOGIN REDIRECT", flush=True)
        elif "_____tmd_____" in content:
            print(f"  Status: BaXia block", flush=True)
        else:
            print(f"  Status: Loaded but no products", flush=True)
    except Exception as e:
        print(f"  Error: {e}", flush=True)
    return []


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

    # ===== Strategy 1: Homepage first, then search =====
    print("=" * 60)
    print("STRATEGY 1: Warmup with homepage, then search")
    print("=" * 60, flush=True)
    try:
        page.goto("https://www.1688.com/", wait_until="domcontentloaded", timeout=30000)
        time.sleep(5)
        # Get cookies
        cookies = context.cookies()
        print(f"Cookies after homepage: {len(cookies)}", flush=True)
        for c in cookies[:5]:
            print(f"  {c['name']} on {c['domain']}", flush=True)

        # Now try search
        try_search(page, f"https://s.1688.com/selloffer/offer_search.htm?keywords={ENCODED}", "Search after homepage", 15)
    except Exception as e:
        print(f"Strategy 1 error: {e}", flush=True)

    # ===== Strategy 2: Try m.1688.com mobile =====
    print("\n" + "=" * 60)
    print("STRATEGY 2: Mobile search with proper UA")
    print("=" * 60, flush=True)
    # Set mobile UA
    context.close()
    context = browser.new_context(
        viewport={"width": 375, "height": 812},
        user_agent="Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.0 Mobile/15E148 Safari/604.1",
        locale="zh-CN",
        timezone_id="Asia/Hong_Kong",
    )
    page = context.new_page()
    try_search(page, f"https://m.1688.com/page/offerSearch.htm?keywords={ENCODED}", "Mobile search", 20)

    # ===== Strategy 3: s.1688.com with offer detail as target =====
    print("\n" + "=" * 60)
    print("STRATEGY 3: Search with desktop, wait 30s")
    print("=" * 60, flush=True)
    context.close()
    context = browser.new_context(
        viewport={"width": 1280, "height": 720},
        user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        locale="zh-CN",
        timezone_id="Asia/Hong_Kong",
    )
    page = context.new_page()
    # Try with longer wait
    try_search(page, f"https://s.1688.com/selloffer/offer_search.htm?keywords={ENCODED}", "Search wait 30s", 30)

    # ===== Strategy 4: Try the search.m.1688.com mobile =====
    print("\n" + "=" * 60)
    print("STRATEGY 4: search.m.1688.com")
    print("=" * 60, flush=True)
    try_search(page, f"https://search.m.1688.com/index.htm?keywords={ENCODED}", "search.m.1688.com", 20)

    # ===== Strategy 5: Try with explicit Accept-Language and Referer =====
    print("\n" + "=" * 60)
    print("STRATEGY 5: Search with Referer from 1688.com")
    print("=" * 60, flush=True)
    page.set_extra_http_headers({
        "Referer": "https://www.1688.com/",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
    })
    try_search(page, f"https://s.1688.com/selloffer/offer_search.htm?keywords={ENCODED}", "Search with referer", 15)

    browser.close()

print("\n=== Done ===", flush=True)
