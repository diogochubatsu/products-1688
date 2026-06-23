#!/usr/bin/env python3
"""
Verify mobile offers and try mobile search.
"""
import os
import re
import time
import urllib.parse
import sys
import json

from playwright.sync_api import sync_playwright

PROXY = {
    "server": "isp.decodo.com:10001",
    "username": "user-sp2idylm9q-country-hk",
    "password": "J41Ytm9rgWofr=V2nr",
}

QUERY = "无线领夹麦克风 K15"
ENCODED = urllib.parse.quote(QUERY)


def get_offers_with_context(page):
    """Extract offers with surrounding context (titles, images)"""
    content = page.content()
    # Find each offer and its surrounding HTML
    offer_pattern = re.compile(r'href="(//detail\.1688\.com/offer/(\d+)\.html[^"]*)"[^>]*>(.*?)</a>', re.DOTALL)
    matches = offer_pattern.findall(content)
    results = []
    for href, oid, inner in matches:
        # Try to extract title
        title_match = re.search(r'<[^>]*title="([^"]+)"', inner)
        title = title_match.group(1) if title_match else ""
        if not title:
            text_match = re.search(r'>([^<]+)<', inner)
            title = text_match.group(1).strip() if text_match else ""
        img_match = re.search(r'src="([^"]+)"', inner)
        img = img_match.group(1) if img_match else ""
        results.append({
            "offer_id": oid,
            "href": href,
            "title": title[:80],
            "img": img[:100] if img else None
        })
    return results


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

    # Test 1: Verify mobile homepage offers
    print("=== MOBILE HOMEPAGE (full data) ===\n", flush=True)
    page.goto("https://m.1688.com/", wait_until="domcontentloaded", timeout=25000)
    time.sleep(10)
    offers = get_offers_with_context(page)
    print(f"Found {len(offers)} offers with context\n", flush=True)
    for o in offers[:15]:
        print(f"  ID: {o['offer_id']}", flush=True)
        print(f"    Title: {o['title']}", flush=True)
        if o['img']:
            print(f"    Img: {o['img']}", flush=True)
        print(flush=True)

    # Test 2: Mobile search
    print("\n=== MOBILE SEARCH ===\n", flush=True)
    page.goto(f"https://m.1688.com/page/offerSearch.htm?keywords={ENCODED}",
              wait_until="domcontentloaded", timeout=30000)
    time.sleep(15)
    content = page.content()
    offers = get_offers_with_context(page)
    print(f"Final URL: {page.url}", flush=True)
    print(f"Title: {page.title()[:60]}", flush=True)
    print(f"Content size: {len(content)}b", flush=True)
    print(f"Offers with context: {len(offers)}", flush=True)
    for o in offers[:10]:
        print(f"  {o['offer_id']}: {o['title'][:60]}", flush=True)
    if not offers:
        # Check if it's the homepage
        home_offers = re.findall(r'/offer/(\d+)\.html', content)
        print(f"Raw offer IDs: {len(set(home_offers))}", flush=True)

    # Test 3: Try different mobile search URLs
    print("\n=== MOBILE SEARCH VARIATIONS ===\n", flush=True)
    urls = [
        f"https://m.1688.com/selloffer/offer_search.htm?keywords={ENCODED}",
        f"https://m.1688.com/search/offer_search.htm?keywords={ENCODED}",
        f"https://m.1688.com/offerSearch.htm?keywords={ENCODED}",
        f"https://search.m.1688.com/page/offerSearch.htm?keywords={ENCODED}",
    ]
    for url in urls:
        try:
            page.goto(url, wait_until="domcontentloaded", timeout=20000)
            time.sleep(10)
            content = page.content()
            offer_count = len(set(re.findall(r'/offer/(\d+)\.html', content)))
            title = page.title()[:50]
            final_url = page.url[:80]
            print(f"  {url[:60]}", flush=True)
            print(f"    -> title={title}, url={final_url}, offers={offer_count}", flush=True)
        except Exception as e:
            print(f"  Error: {e}", flush=True)
        time.sleep(1)

    # Test 4: Mobile offer detail with related products
    print("\n=== MOBILE OFFER DETAIL (related products) ===\n", flush=True)
    page.goto("https://m.1688.com/offer/740647797173.html",
              wait_until="domcontentloaded", timeout=30000)
    time.sleep(15)
    content = page.content()
    offers = get_offers_with_context(page)
    print(f"Related offers: {len(offers)}", flush=True)
    for o in offers[:10]:
        print(f"  {o['offer_id']}: {o['title'][:60]}", flush=True)

    browser.close()
