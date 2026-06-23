#!/usr/bin/env python3
"""
Test 4 strategies to bypass 1688 BaXia search:
1. Decodo SU with browser-like fingerprint
2. Decodo SU with session warmup (visit homepage first)
3. Decodo SU with different geo
4. Decodo SCRAPE API (JS rendering - heavy artillery)
"""
import subprocess
import os
import re
import time

with open("/mnt/ssd/1688-only/.env") as f:
    for line in f:
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        os.environ[k.strip()] = v.strip()

# Get all credentials
SU_USER = os.environ["DECODO_SU_USER"]
SU_PASS = os.environ["DECODO_SU_PASS"]
SCRAPE_USER = os.environ["DECODO_SCRAPE_USER"]
SCRAPE_PASS = os.environ["DECODO_SCRAPE_PASS"]

TEST_URL = "https://s.1688.com/selloffer/offer_search.htm?keywords=%E7%84%A1%E7%B7%9A%E9%A0%98%E5%A4%BE%E9%BA%A6%E5%85%8B%E9%A2%88+K15"
# Mobile alternative
TEST_URL_M = "https://m.1688.com/page/offerSearch.htm?keywords=%E7%84%A1%E7%B7%9A%E9%A0%98%E5%A4%BE%E9%BA%A6%E5%85%8B%E9%A2%88+K15"

print(f"Test target: 1688 search for K15 mic\n")
print(f"Test URL: {TEST_URL}\n", flush=True)

# ========== STRATEGY 1: Decodo SU with full browser fingerprint ==========
print("=" * 60)
print("STRATEGY 1: SU + browser fingerprint headers")
print("=" * 60, flush=True)
cmd = [
    "curl", "-s", "-k", "-w", "STATUS=%{http_code} SIZE=%{size_download}",
    "-x", "https://unblock.decodo.com:60000",
    "-U", f"{SU_USER}:{SU_PASS}",
    "-H", f"X-SU-User: {SU_USER}",
    "-H", f"X-SU-Password: {SU_PASS}",
    "-H", "X-SU-Geo: China",
    # Browser-like fingerprint
    "-H", "User-Agent: Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.0 Mobile/15E148 Safari/604.1",
    "-H", "Accept: text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "-H", "Accept-Language: zh-CN,zh;q=0.9,en;q=0.8",
    "-H", "Accept-Encoding: gzip, deflate, br",
    "-H", "Sec-Fetch-Dest: document",
    "-H", "Sec-Fetch-Mode: navigate",
    "-H", "Sec-Fetch-Site: none",
    "-H", "Sec-Fetch-User: ?1",
    "-H", "Upgrade-Insecure-Requests: 1",
    TEST_URL_M,
    "--max-time", "15",
    "-o", "/tmp/strat1.html"
]
result = subprocess.run(cmd, capture_output=True, text=True)
print(f"  {result.stdout.strip()}", flush=True)
if os.path.exists("/tmp/strat1.html"):
    with open("/tmp/strat1.html") as f:
        c = f.read()
    offers = len(set(re.findall(r'/offer/(\d+)\.html', c)))
    is_baxia = "baxia" in c.lower() or "_____tmd_____" in c
    title_m = re.search(r'<title>(.*?)</title>', c)
    title = title_m.group(1)[:40] if title_m else "(no title)"
    print(f"  BaXia: {is_baxia}, Offers: {offers}, Title: {title}", flush=True)
    if offers > 0:
        print(f"  *** STRATEGY 1 WORKS! ***", flush=True)

# ========== STRATEGY 2: SU with session warmup ==========
print()
print("=" * 60)
print("STRATEGY 2: SU + session warmup (homepage first)")
print("=" * 60, flush=True)

# Step 1: visit homepage to get cookies
cmd1 = [
    "curl", "-s", "-k", "-c", "/tmp/warmup_cookies.txt",
    "-x", "https://unblock.decodo.com:60000",
    "-U", f"{SU_USER}:{SU_PASS}",
    "-H", f"X-SU-User: {SU_USER}",
    "-H", f"X-SU-Password: {SU_PASS}",
    "-H", "X-SU-Geo: China",
    "https://www.1688.com/", "--max-time", "10",
    "-o", "/tmp/strat2_home.html"
]
subprocess.run(cmd1, capture_output=True, text=True)
print(f"  Homepage fetch done", flush=True)

# Step 2: visit search with warm cookies
cmd2 = [
    "curl", "-s", "-k", "-w", "STATUS=%{http_code} SIZE=%{size_download}",
    "-b", "/tmp/warmup_cookies.txt",
    "-c", "/tmp/warmup_cookies.txt",
    "-x", "https://unblock.decodo.com:60000",
    "-U", f"{SU_USER}:{SU_PASS}",
    "-H", f"X-SU-User: {SU_USER}",
    "-H", f"X-SU-Password: {SU_PASS}",
    "-H", "X-SU-Geo: China",
    "-H", "User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "-H", "Referer: https://www.1688.com/",
    TEST_URL_M,
    "--max-time", "15",
    "-o", "/tmp/strat2.html"
]
result = subprocess.run(cmd2, capture_output=True, text=True)
print(f"  {result.stdout.strip()}", flush=True)
if os.path.exists("/tmp/strat2.html"):
    with open("/tmp/strat2.html") as f:
        c = f.read()
    offers = len(set(re.findall(r'/offer/(\d+)\.html', c)))
    is_baxia = "baxia" in c.lower() or "_____tmd_____" in c
    title_m = re.search(r'<title>(.*?)</title>', c)
    title = title_m.group(1)[:40] if title_m else "(no title)"
    print(f"  BaXia: {is_baxia}, Offers: {offers}, Title: {title}", flush=True)
    if offers > 0:
        print(f"  *** STRATEGY 2 WORKS! ***", flush=True)

# ========== STRATEGY 3: SU with different China geos ==========
print()
print("=" * 60)
print("STRATEGY 3: SU with different China geo (Shanghai, Shenzhen, Beijing)")
print("=" * 60, flush=True)

for geo in ["Shanghai", "Shenzhen", "Beijing", "Guangzhou", "Hangzhou"]:
    cmd = [
        "curl", "-s", "-k", "-w", "STATUS=%{http_code} SIZE=%{size_download}",
        "-x", "https://unblock.decodo.com:60000",
        "-U", f"{SU_USER}:{SU_PASS}",
        "-H", f"X-SU-User: {SU_USER}",
        "-H", f"X-SU-Password: {SU_PASS}",
        "-H", f"X-SU-Geo: {geo}",
        TEST_URL_M,
        "--max-time", "10",
        "-o", "/tmp/strat3.html"
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    status = result.stdout.strip()
    with open("/tmp/strat3.html") as f:
        c = f.read()
    offers = len(set(re.findall(r'/offer/(\d+)\.html', c)))
    is_baxia = "baxia" in c.lower() or "_____tmd_____" in c
    print(f"  {geo:12} {status}  baxia={is_baxia} off={offers}", flush=True)
    if offers > 0:
        print(f"  *** STRATEGY 3 WORKS for {geo}! ***", flush=True)
    time.sleep(0.5)

# ========== STRATEGY 4: Decodo SCRAPE API (JS rendering) ==========
print()
print("=" * 60)
print("STRATEGY 4: Decodo SCRAPE API (JS rendering - heavy artillery)")
print("=" * 60, flush=True)

# Different SCRAPE API endpoints to try
SCRAPE_URLS = [
    # Real Browser - desktop
    f"https://scraper-api.decodo.com/v2/scrape?url={TEST_URL_M}&geo=cn&headless=chrome-desktop",
    # Real Browser - mobile
    f"https://scraper-api.decodo.com/v2/scrape?url={TEST_URL_M}&geo=cn&headless=chrome-mobile",
    # Headless
    f"https://scraper-api.decodo.com/v2/scrape?url={TEST_URL_M}&geo=cn",
    # Universal
    f"https://scraper-api.decodo.com/scraping/v1.0/tasks?url={TEST_URL_M}&geo=cn",
]

for i, url in enumerate(SCRAPE_URLS):
    print(f"  Trying variant {i+1}: {url[:80]}...", flush=True)
    cmd = [
        "curl", "-s", "-k", "-w", "STATUS=%{http_code} SIZE=%{size_download}",
        "-x", f"https://unblock.decodo.com:60000",
        "-U", f"{SCRAPE_USER}:{SCRAPE_PASS}",
        "-H", f"X-SU-User: {SCRAPE_USER}",
        "-H", f"X-SU-Password: {SCRAPE_PASS}",
        url, "--max-time", "30",
        "-o", "/tmp/strat4.html"
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    status = result.stdout.strip()
    print(f"    {status}", flush=True)
    if os.path.exists("/tmp/strat4.html"):
        with open("/tmp/strat4.html") as f:
            c = f.read()
        offers = len(set(re.findall(r'/offer/(\d+)\.html', c)))
        is_baxia = "baxia" in c.lower() or "_____tmd_____" in c
        print(f"    BaXia: {is_baxia}, Offers: {offers}, Size: {len(c)}", flush=True)
        if offers > 0:
            print(f"  *** STRATEGY 4 VARIANT {i+1} WORKS! ***", flush=True)
            print(f"  First 500 chars: {c[:500]}", flush=True)
    time.sleep(1)

# Check if SCRAPE API auth works
print()
print("=" * 60)
print("STRATEGY 4b: Direct SCRAPE API auth test")
print("=" * 60, flush=True)
cmd = [
    "curl", "-s", "-k", "-w", "STATUS=%{http_code} SIZE=%{size_download}",
    "-x", "https://unblock.decodo.com:60000",
    "-U", f"{SCRAPE_USER}:{SCRAPE_PASS}",
    "https://api.decodo.com/", "--max-time", "10",
]
result = subprocess.run(cmd, capture_output=True, text=True)
print(f"  Auth test: {result.stdout.strip()}", flush=True)

# Try SCRAPE API with direct basic auth (no proxy)
print("  Direct SCRAPE API (no proxy):", flush=True)
cmd = [
    "curl", "-s", "-k", "-w", "STATUS=%{http_code} SIZE=%{size_download}",
    "-x", f"https://customer-{SCRAPE_USER}:{SCRAPE_PASS}@unblock.decodo.com:60001",
    "https://www.1688.com/", "--max-time", "10",
    "-o", "/tmp/strat4b.html"
]
result = subprocess.run(cmd, capture_output=True, text=True)
print(f"    {result.stdout.strip()}", flush=True)
if os.path.exists("/tmp/strat4b.html"):
    with open("/tmp/strat4b.html") as f:
        c = f.read()
    print(f"    Size: {len(c)}, BaXia: {'baxia' in c.lower()}", flush=True)

print()
print("=" * 60)
print("SUMMARY")
print("=" * 60, flush=True)
