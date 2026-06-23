#!/usr/bin/env python3
"""
Test 1688 pinyin subdomains for the categories user requested.
"""
import subprocess
import os
import re
import time
import sys

with open("/mnt/ssd/1688-only/.env") as f:
    for line in f:
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        os.environ[k.strip()] = v.strip()

SU_USER = os.environ["DECODO_SU_USER"]
SU_PASS = os.environ["DECODO_SU_PASS"]

# Categories requested + variations
CANDIDATES = [
    # 1. General tools (ferramentas em geral)
    "https://gongju.1688.com/",          # 工具 (tools)
    "https://wujin.1688.com/",            # 五金 (hardware)
    "https://dianqi.1688.com/",          # 电气 (electric)
    "https://jixie.1688.com/",           # 机械 (machinery)
    "https://dianli.1688.com/",          # 电力 (electricity)
    "https://famen.1688.com/",           # 法兰 (flange)
    "https://huatong.1688.com/",         # 套筒 (socket)

    # 2. Parafusadeiras bateria (cordless screwdrivers)
    "https://luosi.1688.com/",           # 螺丝 (screw)
    "https://dianliulu.1688.com/",       # 电动螺丝 (electric screw)
    "https://lulu.1688.com/",            # 撸撸 (informal)
    "https://diandong.1688.com/",        # 电动 (electric)
    "https://diandonggongju.1688.com/",  # 电动工具 (electric tools)
    "https://dianliulu.1688.com/",
    "https://diaobo.1688.com/",          # 电钻 (electric drill)
    "https://dianzuan.1688.com/",        # 电钻
    "https://shouyonggongju.1688.com/",  # 手用工具 (hand tools)
    "https://dianpiao.1688.com/",        # 钣金 (sheet metal)
    "https://luosiding.1688.com/",       # 螺丝钉 (screws)

    # 3. Meias (socks)
    "https://wazi.1688.com/",            # 袜子 (socks)
    "https://wawazi.1688.com/",          # 袜
    "https://shortsocks.1688.com/",
    "https://socks.1688.com/",
    "https://tongxie.1688.com/",         # 童袜 (children socks)
    "https://nvxie.1688.com/",           # 女袜 (women socks)
    "https://nanxie.1688.com/",          # 男袜 (men socks)
    "https://wuyongpin.1688.com/",       # 袜用品 (sock supplies)
    "https://wamao.1688.com/",           # 袜帽

    # 4. Scooters eletricas (electric scooters)
    "https://dianche.1688.com/",         # 电动车 (electric vehicles)
    "https://diandongche.1688.com/",     # 电动车辆
    "https://zixingche.1688.com/",       # 自行车 (bicycles)
    "https://dundongche.1688.com/",      # 电动车 motorbike
    "https://dundongping.1688.com/",     # 电动平 (electric flat)
    "https://lunhua.1688.com/",          # 轮滑 (roller skating)
    "https://pinghengche.1688.com/",     # 平衡车 (balance car)
    "https://motuo.1688.com/",           # 摩托 (motorcycle)
    "https://moto.1688.com/",

    # 5. Itens de cozinha (kitchen items)
    "https://chufang.1688.com/",         # 厨房 (kitchen)
    "https://canyin.1688.com/",          # 餐饮 (catering)
    "https://cangui.1688.com/",          # 餐具 (tableware)
    "https://bingxiang.1688.com/",       # 冰箱 (refrigerator)
    "https://guo.1688.com/",             # 锅 (pot)
    "https://shaoguo.1688.com/",         # 烧锅 (pot)
    "https://daogui.1688.com/",          # 刀具 (cutlery)
    "https://chuju.1688.com/",           # 厨具 (kitchenware)
    "https://cajing.1688.com/",          # 茶具 (tea set)
    "https://kettle.1688.com/",

    # 6. Ferramentas de jardim (garden tools)
    "https://yuanlin.1688.com/",         # 园林 (garden)
    "https://huayuan.1688.com/",         # 花园 (garden)
    "https://huahui.1688.com/",          # 花卉 (flowers)
    "https://nongye.1688.com/",          # 农业 (agriculture)
    "https://nongzi.1688.com/",          # 农资 (agricultural supplies)
    "https://zhongzhi.1688.com/",        # 种植 (planting)
    "https://penyuan.1688.com/",         # 喷灌 (sprinkler)
    "https://caoping.1688.com/",         # 草坪 (lawn)
    "https://zhiwu.1688.com/",           # 植物 (plants)
    "https://garden.1688.com/",

    # 7. Roupa intima feminina (women's underwear)
    "https://neiyi.1688.com/",           # 内衣 (underwear)
    "https://nvyi.1688.com/",            # 女衣
    "https://nvxie.1688.com/",           # 女鞋 (women shoes)
    "https://underwear.1688.com/",
    "https://underpants.1688.com/",
    "https://bra.1688.com/",
    "https://kuzhuang.1688.com/",        # 裤装 (pants)
    "https://neiku.1688.com/",           # 内裤 (underpants)
    "https://wenchong.1688.com/",        # 文胸 (bra)
    "https://sleepwear.1688.com/",
    "https://pajama.1688.com/",
    "https://piji.1688.com/",            # 皮具 (leather)
    "https://yurong.1688.com/",          # 羽绒 (down)
]

print(f"Testing {len(CANDIDATES)} candidate subdomains...\n", flush=True)

results = []
for i, url in enumerate(CANDIDATES):
    cmd = [
        "curl", "-s", "-k", "-w", "%{http_code}|%{size_download}",
        "-x", "https://unblock.decodo.com:60000",
        "-U", f"{SU_USER}:{SU_PASS}",
        "-H", f"X-SU-User: {SU_USER}",
        "-H", f"X-SU-Password: {SU_PASS}",
        "-H", "X-SU-Geo: China",
        url, "--max-time", "6",
        "-o", "/tmp/cat3_test.html"
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
    parts = result.stdout.strip().split("|")
    status, size = parts[0], parts[1] if len(parts) > 1 else "?"

    try:
        with open("/tmp/cat3_test.html") as f:
            content = f.read()
    except FileNotFoundError:
        content = ""

    has_baxia = "baxia" in content.lower() or "_____tmd_____" in content
    offers = len(set(re.findall(r'/offer/(\d+)\.html', content)))
    title_m = re.search(r'<title>(.*?)</title>', content)
    title = title_m.group(1)[:40] if title_m else ""

    if has_baxia:
        label = "BAXIA"
    elif status == "200" and int(size) > 5000:
        label = "OK"
    elif status != "200":
        label = "ERR"
    else:
        label = "SMALL"

    if label == "OK":
        results.append((url, offers, size, title))
    print(f"  [{i+1:2}] [{label:5}] {size:>8}b  off={offers:3}  {url[:48]:48}  {title[:25]}", flush=True)
    time.sleep(0.3)

print(f"\n\n*** NEW OK PAGES (ranked by offers): ***\n", flush=True)
for url, offers, size, title in sorted(results, key=lambda x: -x[1]):
    print(f"  {offers:3} offers  {size:>8}b  {url}  -- {title}", flush=True)

print(f"\nTotal new OK pages: {len(results)}", flush=True)
