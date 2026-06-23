#!/usr/bin/env python3
"""Task 2: Try to register on open.1688.com as developer"""
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

print("=== Task 2: 1688 Open Platform Registration Research ===\n", flush=True)

# Key URLs to understand registration process
urls = [
    ("https://open.1688.com/console", "1688-Console-Login"),
    ("https://open.1688.com/portal/enterApp.htm", "1688-EnterApp"),
    ("https://open.1688.com/api/apidocdetail.htm?aopApiCategory=product_new", "1688-Product-API-Docs"),
    ("https://open.1688.com/solution/solutionDetail.htm?solutionKey=1697014160788", "1688-Cross-border-Solution"),
    ("https://work.1688.com/", "1688-Work-Platform"),
    ("https://developer.aliyun.com/article/1686000", "1688-API-Auth-Guide"),
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
            print(md[:3000])
        except json.JSONDecodeError:
            print("Error: " + result.stdout[:200])
