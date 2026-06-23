#!/usr/bin/env python3
"""
1688 trending product discovery - extract all offer IDs from known working URLs.
"""
import subprocess
import os
import re
import time
import json

with open("/mnt/ssd/1688-only/.env") as f:
    for line in f:
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        os.environ[k.strip()] = v.strip()

# All known working 1688 URLs that have product listings
URLS = [
    ("factory_root", "https://factory.1688.com/"),
    ("tongzhuang", "https://tongzhuang.1688.com/"),
    ("fuzhuang", "https://fuzhuang.1688.com/"),
    ("shipin", "https://shipin.1688.com/"),
    ("chengbiao", "https://321.1688.com/chengbiao.html"),
    ("liangpin", "https://321.1688.com/liangpin.html"),
    ("sale", "https://sale.1688.com/"),
    ("home", "https://home.1688.com/"),
    ("food", "https://food.1688.com/"),
    ("fangzhi", "https://fangzhi.1688.com/"),
    ("suliao", "https://suliao.1688.com/"),
    ("wanju", "https://wanju.1688.com/"),
    ("gys", "https://gys.1688.com/"),
    ("sport", "https://sport.1688.com/"),
    ("muying", "https://muying.1688.com/"),
]

all_offers = {}  # offer_id -> source list

for label, url in URLS:
    print(f"Fetching {label}...", flush=True)
    cmd = [
        "curl", "-s", "-k", "-w", "\n%{http_code} %{size_download}",
        "-x", "https://unblock.decodo.com:60000",
        "-U", f"{os.environ['DECODO_SU_USER']}:{os.environ['DECODO_SU_PASS']}",
        "-H", f"X-SU-User: {os.environ['DECODO_SU_USER']}",
        "-H", f"X-SU-Password: {os.environ['DECODO_SU_PASS']}",
        "-H", "X-SU-Geo: China",
        url, "--max-time", "20",
        "-o", "/tmp/disc.html"
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=25)
    try:
        with open("/tmp/disc.html") as f:
            html = f.read()
    except FileNotFoundError:
        print(f"  Failed: no file", flush=True)
        continue

    # Find offer IDs in different patterns
    offer_patterns = [
        (r'/offer/(\d+)\.html', "direct"),
        (r'"offerId":\s*"?(\d+)', "json"),
        (r'data-offer-id="(\d+)"', "data-attr"),
        (r'"goodsId":\s*"?(\d+)', "goodsId"),
        (r'/(\d+)\.html', "naked-id"),
    ]

    found_ids = set()
    for pattern, ptype in offer_patterns:
        ids = re.findall(pattern, html)
        for i in ids:
            if 8 <= len(i) <= 12 and i.isdigit():  # Valid 1688 offer IDs are 8-12 digits
                found_ids.add(i)

    print(f"  {len(found_ids)} unique offer IDs", flush=True)
    for oid in found_ids:
        all_offers.setdefault(oid, []).append(label)

    time.sleep(1.0)

# Save results
print(f"\n\n=== TOTAL UNIQUE OFFER IDS: {len(all_offers)} ===\n", flush=True)

# Show cross-referenced
all_sources = set()
for oid, srcs in all_offers.items():
    for s in srcs:
        all_sources.add(s)

print(f"Found in {len(all_sources)} sources: {sorted(all_sources)}\n", flush=True)

# Save full list
with open("/tmp/discovered_offers.json", "w") as f:
    json.dump({
        "total_unique": len(all_offers),
        "sources": sorted(all_sources),
        "offers": {oid: srcs for oid, srcs in all_offers.items()},
    }, f, ensure_ascii=False, indent=2)

print(f"Saved to /tmp/discovered_offers.json", flush=True)

# Print first 30 with sources
print(f"\nSample (first 30):", flush=True)
for i, (oid, srcs) in enumerate(list(all_offers.items())[:30]):
    print(f"  {oid}: {srcs}", flush=True)
