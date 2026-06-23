#!/usr/bin/env python3
"""
Exhaustive 1688 subdomain and URL pattern testing.
Find any path that doesn't trigger BaXia CAPTCHA.
"""
import subprocess
import os
import re
import time
import urllib.parse

with open("/mnt/ssd/1688-only/.env") as f:
    for line in f:
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        os.environ[k.strip()] = v.strip()

# Comprehensive list of 1688 subdomains and URL patterns
TEST_URLS = [
    # Category/channel pages (might not have BaXia)
    "https://air.1688.com/",
    "https://air.1688.com/zt_category/yVwbQTBH",
    "https://winport.1688.com/",
    "https://winport.1688.com/page/offer.htm",
    "https://cxt.1688.com/",
    "https://qjy.1688.com/",
    "https://qjy.1688.com/index.htm",
    # 1688 root variations
    "https://www.1688.com/",
    "https://1688.com/",
    # Topic/Channel pages
    "https://show.1688.com/zgc/channel/s0strmbp.html",
    "https://m.1688.com/zgc/",
    "https://sale.1688.com/",
    "https://sale.1688.com/ci_bb_group/",
    # Industry/specialized pages
    "https://yp.1688.com/",  # Yellow pages
    "https://index.1688.com/",  # 1688 index
    "https://huopin.1688.com/",  # Hot products
    "https://factory.1688.com/zgc/",  # Factory category
    "https://factory.1688.com/page/factorySearch.htm",
    # Mobile search variants
    "https://m.1688.com/company/companySearch.htm?keywords=无线麦克风",
    "https://m.1688.com/winport/company_search.htm?keywords=无线麦克风",
    # Desktop search variants
    "https://s.1688.com/winport/search.htm?keywords=无线麦克风",
    "https://s.1688.com/company/company_search.htm?keywords=无线麦克风",
    # API roots
    "https://h5api.m.1688.com/h5/mtop.1688.page.home/1.0/",
    "https://h5api.m.1688.com/h5/mtop.1688.selloffer.search/1.0/",
    "https://h5api.m.1688.com/h5/mtop.taobao.1688.data/1.0/",
    "https://h5api.m.1688.com/h5/mtop.ali1688.selloffer.search/1.0/",
    "https://h5api.m.1688.com/h5/mtop.ali1688.selloffer.search",
    "https://h5api.m.1688.com/h5/mtop.1688.search.selloffer/1.0/",
    # Specific known-working factories
    "https://factory.1688.com/zgc/page/2hlo2m80.html",
    "https://factory.1688.com/zgc/page/2dslr0o2.html",
    # Detail page (known working control)
    "https://detail.1688.com/offer/898549325479.html",
    "https://detail.1688.com/offer/740647797173.html",
]

results = []

for url in TEST_URLS:
    cmd = [
        "curl", "-s", "-k", "-w", "\n%{http_code} %{time_total}s %{size_download}",
        "-x", "https://unblock.decodo.com:60000",
        "-U", f"{os.environ['DECODO_SU_USER']}:{os.environ['DECODO_SU_PASS']}",
        "-H", f"X-SU-User: {os.environ['DECODO_SU_USER']}",
        "-H", f"X-SU-Password: {os.environ['DECODO_SU_PASS']}",
        "-H", "X-SU-Geo: China",
        "-H", "X-SU-Locale: zh-cn",
        "-H", "User-Agent: Mozilla/5.0 (iPhone; CPU iPhone OS 14_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.0 Mobile/15E148 Safari/604.1",
        url,
        "--max-time", "20",
        "-o", "/tmp/test1688_response.html"
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=25)
    last_line = result.stdout.strip().split("\n")[-1] if result.stdout else ""
    parts = last_line.split()
    status = parts[0] if parts else "?"
    elapsed = parts[1] if len(parts) > 1 else "?"
    size = parts[2] if len(parts) > 2 else "?"

    if os.path.exists("/tmp/test1688_response.html"):
        with open("/tmp/test1688_response.html") as f:
            content = f.read()
        has_baxia = "baxia" in content.lower() or "_____tmd_____" in content or "punish" in content.lower()
        has_window_context = "window.context" in content
        offers = len(set(re.findall(r'/offer/(\d+)\.html', content)))
        title_m = re.search(r'<title>(.*?)</title>', content)
        title = title_m.group(1)[:40] if title_m else ""
    else:
        has_baxia = has_window_context = False
        offers = 0
        title = ""

    status_label = "OK" if status == "200" and not has_baxia and int(size) > 5000 else \
                   "BAXIA" if has_baxia else \
                   "SMALL" if int(size) < 5000 else \
                   "ERR" if status != "200" else "?"

    results.append((url, status, elapsed, size, status_label, has_window_context, offers, title))
    print(f"  [{status_label:5}] {status} {elapsed:7} {size:>8}b  ctx={has_window_context} offers={offers:3}  {url[:60]}")

    time.sleep(1.5)

print("\n" + "="*100)
print("OK URLs (no BaXia, >5KB, 200 status):")
for url, status, elapsed, size, label, ctx, offers, title in results:
    if label == "OK":
        print(f"  {url}  (size={size}, offers={offers}, ctx={ctx}, title={title})")
