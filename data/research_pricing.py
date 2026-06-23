#!/usr/bin/env python3
"""Final research: get pricing for the main 1688 tools"""
import os
import json
import subprocess

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

# Pricing pages
urls = [
    ("https://open.1688.com/", "1688-Open-Platform"),
    ("https://www.dianleida.net/buy/monitorBuy", "Dianleida-Pricing-Full"),
    ("https://www.dianxiaomi.com/pricing", "Dianxiaomi-Pricing"),
    ("https://www.sorftime.com/pricing", "Sorftime-Pricing"),
    ("https://open.onebound.cn/data-market", "Onebound-Data-Market"),
    ("https://www.amz520.com/", "Amz520-Main"),
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
            print(md[:2500])
        except json.JSONDecodeError:
            print("Error: " + result.stdout[:200])
