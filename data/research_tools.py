#!/usr/bin/env python3
"""Deep dive on 1688 tools pricing & APIs"""
import os
import json
import re
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

urls_to_scrape = [
    ("https://www.dianleida.net/buy/monitorBuy", "Dianleida-Pricing"),
    ("https://open.onebound.cn/", "Onebound-Pricing"),
    ("https://developer.aliyun.com/article/1677848", "1688-Ranking-API-Detailed"),
    ("https://www.163.com/dy/article/KS92FK7H05564TOE.html", "2026-Tools-Comparison"),
    ("https://m.amz123.com/dianleida", "AMZ123-Dianleida"),
    ("https://www.sohu.com/a/1006961554_121735696", "Sohu-2026-Tools-Guide"),
]

for url, label in urls_to_scrape:
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
