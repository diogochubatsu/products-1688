#!/usr/bin/env python3
"""Get Onebound ranking API doc details + Sorftime pricing"""
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

# Get the Onebound ranking API details (need to look at later sections of the page)
body = json.dumps({
    "url": "https://open.onebound.cn/help/api/1688.item_search_best.html",
    "formats": ["markdown"],
    "onlyMainContent": False,  # Get full content including later sections
    "includeTags": ["h1", "h2", "h3", "h4", "p", "code", "pre", "table", "th", "td"]
})
result = subprocess.run(
    ["curl", "-s", "-X", "POST",
     "-H", auth,
     "-H", "Content-Type: application/json",
     "-d", body,
     "https://api.firecrawl.dev/v1/scrape", "--max-time", "60"],
    capture_output=True, text=True, timeout=70
)
if result.stdout:
    data = json.loads(result.stdout)
    md = data.get("data", {}).get("markdown", "")
    # Show middle/late section
    print("=== Onebound 1688 Ranking API (middle section) ===\n")
    print(md[10000:18000])
    print("\n\n=== Onebound 1688 Ranking API (late section) ===\n")
    print(md[20000:28000])
