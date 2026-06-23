#!/usr/bin/env python3
"""Task 3 & 4: Download Chrome extension + check pricing"""
import os
import json
import subprocess
import urllib.request
import urllib.error

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

print("=== Task 3: 1688 Chrome Extension download ===\n", flush=True)

# Try to download the 1688 official Chrome extension
# Direct URL from chajian.1688.com (Aliyun OSS)
extension_urls = [
    ("https://1688smartassistant.oss-cn-beijing.aliyuncs.com/1688-extension.zip?d=1781587292288", "1688-Official-Extension-Direct"),
    ("https://chromewebstore.google.com/detail/1688%E9%87%87%E8%B4%AD%E5%8A%A9%E6%89%8B%E6%8F%92%E4%BB%B6%E7%89%88/kphldkppgfpjadpabfkghmjbhpcmgpdg", "1688-Ext-Chrome-Store"),
]

downloads_dir = "/tmp/1688_extensions"
os.makedirs(downloads_dir, exist_ok=True)

for url, label in extension_urls:
    print(f"\nTrying: {label}")
    print(f"URL: {url}")
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=30) as resp:
            content = resp.read()
            ext = ".zip" if "zip" in url.lower() else ".crx"
            fname = f"{downloads_dir}/{label}{ext}"
            with open(fname, "wb") as f:
                f.write(content)
            print(f"  Downloaded: {len(content)} bytes -> {fname}")
    except urllib.error.HTTPError as e:
        print(f"  HTTP Error: {e.code} {e.reason}")
    except Exception as e:
        print(f"  Error: {e}")

# Check what we have
print("\n=== Files in downloads dir ===")
for f in os.listdir(downloads_dir):
    fp = os.path.join(downloads_dir, f)
    print(f"  {f}: {os.path.getsize(fp)} bytes")

# Try the 店雷达 download page
print("\n=== Task 4: Pricing research ===\n", flush=True)

# Pricing pages - all in one query
pricing_queries = [
    ("https://www.dianleida.net/buy/monitorBuy", "Dianleida-Pricing"),
    ("https://www.dianleida.net/1688/competeShop/category/library/", "Dianleida-Library"),
    ("https://www.zhihu.com/p/2028485434703922411", "Tools-Comparison-2026"),
    ("https://m.amz123.com/dianleida", "AMZ123-Dianleida-Page"),
    ("https://www.sorftime.com/", "Sorftime-Main"),
    ("https://open.onebound.cn/help/api/1688.item_search_best.html", "Onebound-1688-API"),
    ("https://www.feikua.net/plugins/1574.html", "Dianleida-Feikua-Page"),
]

for url, label in pricing_queries:
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
            price_patterns = [
                r'[¥￥$][\d.,]+',
                r'\d+[\s]*元',
                r'USD[\s]*\d+',
                r'CNY[\s]*\d+',
                r'月/\d+',
                r'\d+/月',
            ]
            import re
            for pat in price_patterns:
                prices = re.findall(pat, md[:5000])
                if prices:
                    print("  Prices found: " + str(prices[:5]))
            print(md[:2000])
        except json.JSONDecodeError:
            print("Error: " + result.stdout[:200])
