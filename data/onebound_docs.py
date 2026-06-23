#!/usr/bin/env python3
"""Get Onebound API docs and final pricing research"""
import os
import json
import subprocess
import re

with open("/mnt/ssd/1688-only/.env") as f:
    for line in f:
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        os.environ[k] = v

fc_key = os.environ["FIRECRAWL_API_KEY"]
BEARER = "Bearer " + fc_key
auth = "Authorization: " + BEARER

# Onebound docs - get the actual API endpoint, pricing, and request format
urls = [
    ("https://open.onebound.cn/help/api/1688.item_search_best.html", "Onebound-1688-Ranking"),
    ("https://open.onebound.cn/help/api/1688.item_search.html", "Onebound-1688-Search"),
    ("https://open.onebound.cn/help/api/1688.item_get.html", "Onebound-1688-Detail"),
    ("https://open.onebound.cn/console/", "Onebound-Console"),
    ("https://www.sorftime.com/en-US/pc?tag=MjAxODA5MTMyMzIwMzU1NzAwMDE~", "Sorftime-PC-Plan"),
    ("https://www.sorftime.com/en-US/plug?tag=MjAxODA5MTMyMzIwMzU1NzAwMDE~", "Sorftime-Plug-Plan"),
]

for url, label in urls:
    body = json.dumps({"url": url, "formats": ["markdown"], "onlyMainContent": True})
    result = subprocess.run(
        ["curl", "-s", "-X", "POST",
         "-H", auth,
         "-H", "Content-Type: application/json",
         "-d", body,
         "https://api.firecrawl.dev/v1/scrape", "--max-time", "60"],
        capture_output=True, text=True, timeout=70
    )
    if result.stdout:
        try:
            data = json.loads(result.stdout)
            md = data.get("data", {}).get("markdown", "")
            title = data.get("data", {}).get("metadata", {}).get("title", "")
            print("\n" + "="*80)
            print("[" + label + "] " + url)
            print("Title: " + title)
            print("Length: " + str(len(md)) + "b")
            print("="*80)

            # Find prices
            prices = re.findall(r'[¥￥$][\d.,]+', md)
            if prices:
                print("  Prices: " + str(prices[:10]))

            # Find API endpoints/params
            endpoints = re.findall(r'(GET|POST)\s+/[^\s]+', md)
            if endpoints:
                print("  Endpoints: " + str(endpoints[:5]))

            # Find key API parameters
            params = re.findall(r'`([a-z_]+)`\s*[\(:]', md)
            if params:
                print("  Params: " + str(list(set(params))[:15]))

            print(md[:2500])
        except json.JSONDecodeError:
            print("Error: " + result.stdout[:200])
