#!/usr/bin/env python3
"""
Test alternative 1688 navigation/discovery paths.
User categories (tools, screwdrivers, socks, scooters, kitchen, garden, underwear) are all BAXIA.
Try: brand venues, daily specials, industry clusters, app pages, supply pages, channel pages.
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

SU_USER = os.environ["DECODO_SU_USER"]
SU_PASS = os.environ["DECODO_SU_PASS"]

CANDIDATES = [
    # ========== 1688 Brand/Market pages ==========
    "https://pinpai.1688.com/",         # 品牌 (brands)
    "https://brand.1688.com/",
    "https://mingpin.1688.com/",        # 名品 (famous brand)
    "https://sijin.1688.com/",          # 四金 (?)
    "https://city.1688.com/",           # city
    # ========== 1688 Promotion/Venue pages ==========
    "https://juhui.1688.com/",          # 聚会 (gather)
    "https://tejia.1688.com/",          # 特价 (special price)
    "https://miaosha.1688.com/",        # 秒杀 (flash sale)
    "https://chaozhi.1688.com/",        # 超值 (super value)
    "https://liucheng.1688.com/",       # 流程 (process)
    "https://jiage.1688.com/",          # 价格 (price)
    "https://hui.1688.com/",            # 惠 (discount)
    "https://yin.1688.com/",            # 音
    "https://kefu.1688.com/",           # 客服 (service)
    "https://shang.1688.com/",          # 商 (business)
    "https://maimai.1688.com/",         # 买卖 (buy/sell)
    "https://jiagong.1688.com/",        # 加工 (process)
    "https://lailong.1688.com/",        # 来龙 (?)
    "https://tongxun.1688.com/",        # 通讯 (comm)
    "https://jie.1688.com/",            # 街
    # ========== 1688 mobile specific ==========
    "https://m.1688.com/industrialPark/page/index.htm",
    "https://m.1688.com/industrialPark/",
    "https://m.1688.com/factory/",
    "https://m.1688.com/page/offerSearch.htm",
    "https://m.1688.com/page/buyoffer.htm",
    "https://m.1688.com/selloffer/offer_search.htm",
    "https://m.1688.com/buyoffer/buyoffer_search.htm",
    "https://m.1688.com/index.htm",
    # ========== 1688 winport / cxt ==========
    "https://winport.1688.com/",
    "https://winport.1688.com/page/index.htm",
    "https://winport.1688.com/page/buyoffer_search.htm",
    "https://winport.1688.com/page/offer_search.htm",
    "https://cxt.1688.com/",
    "https://cxt.1688.com/page/index.htm",
    "https://cxt.1688.com/page/offer_search.htm",
    # ========== 1688 b2b / sourcing ==========
    "https://sourcing.1688.com/",
    "https://buy.1688.com/",
    "https://sell.1688.com/",
    "https://s.1688.com/buyoffer/buyoffer_search.htm",
    "https://s.1688.com/buyer/buyer_search.htm",
    # ========== 1688 knowledge/forum ==========
    "https://114.1688.com/",
    "https://114.1688.com/index.htm",
    "https://114.1688.com/km/list/11108609.html",
    "https://club.1688.com/threadlist/1096101.htm",
    # ========== 1688 air / app ==========
    "https://air.1688.com/",
    "https://air.1688.com/page/offerlist.htm",
    "https://air.1688.com/page/marketlist.htm",
    "https://air.1688.com/page/categorylist.htm",
    "https://air.1688.com/page/buysearch.htm",
    "https://air.1688.com/page/offersearch.htm",
    # ========== 1688 specific marketing pages ==========
    "https://321.1688.com/",
    "https://321.1688.com/page/index.htm",
    "https://321.1688.com/page/list.htm",
    "https://321.1688.com/page/marketlist.htm",
    "https://321.1688.com/page/category.htm",
    "https://321.1688.com/liangpin-p2.html",  # possible pagination
    "https://321.1688.com/liangpin_p2.html",
    "https://321.1688.com/liangpin_2.html",
    "https://321.1688.com/chengbiao-p2.html",  # pagination
    "https://321.1688.com/chengbiao_p2.html",
    "https://321.1688.com/chengbiao_2.html",
    # ========== Other 1688 known subdomains ==========
    "https://peixun.1688.com/",         # 培训 (training)
    "https://peixun.1688.com/page/index.htm",
    "https://peixun.1688.com/page/list.htm",
    "https://ff.1688.com/",             # 1688 ff
    "https://ll.1688.com/",
    "https://b2b.1688.com/",
    "https://work.1688.com/",
    "https://buyagent.1688.com/",
    "https://cgs.1688.com/",
    "https://gt.1688.com/",
    "https://gtb.1688.com/",
    "https://gtc.1688.com/",
    "https://factory.1688.com/page/factorySearch.htm",
    "https://factory.1688.com/zgc/",
    "https://factory.1688.com/zgc/list.htm",
    "https://factory.1688.com/zgc/page/index.htm",
    "https://factory.1688.com/zt/",
    "https://factory.1688.com/zt/page/index.htm",
    "https://factory.1688.com/offer/",
    "https://factory.1688.com/offerlist.htm",
    "https://factory.1688.com/list.htm",
    "https://factory.1688.com/category.htm",
    # ========== 1688 mobile offer search variants ==========
    "https://m.1688.com/buyoffer/buyoffer_search.htm",
    "https://m.1688.com/selloffer/buyoffer.htm",
    "https://m.1688.com/page/index.htm",
    "https://m.1688.com/winport/offerlist.htm",
    "https://m.1688.com/selloffer/offer_list.htm",
    "https://m.1688.com/winport/",
    # ========== 1688 bbs/club ==========
    "https://bbs.1688.com/",
    "https://club.1688.com/threadview/47692042.htm",
    "https://post.1688.com/",
    # ========== Industry/Region pages ==========
    "https://cy.1688.com/yiqifa.html",  # industrial
    "https://sale.1688.com/yiqifa.html",
    "https://sh.1688.com/yiqifa.html",  # 上海
    "https://sz.1688.com/yiqifa.html",  # 深圳
    # ========== Misc 1688 ==========
    "https://qyy.1688.com/",
    "https://sxy.1688.com/",
    "https://sale.1688.com/winport.htm",
    "https://sale.1688.com/ctrip.htm",
    "https://sale.1688.com/jinri.htm",  # 今日 (today)
    "https://sale.1688.com/jinri/market.htm",
    "https://jinri.1688.com/",          # 今日
    "https://today.1688.com/",
    "https://daily.1688.com/",
    "https://new.1688.com/",
    "https://xin.1688.com/",
    "https://hot.1688.com/",
    "https://tuijian.1688.com/",
    "https://sale.1688.com/tuijian.htm",
    "https://recommend.1688.com/",
]

print(f"Testing {len(CANDIDATES)} alternative 1688 paths...\n", flush=True)

results = []
for i, url in enumerate(CANDIDATES):
    cmd = [
        "curl", "-s", "-k", "-w", "%{http_code}|%{size_download}",
        "-x", "https://unblock.decodo.com:60000",
        "-U", f"{SU_USER}:{SU_PASS}",
        "-H", f"X-SU-User: {SU_USER}",
        "-H", f"X-SU-Password: {SU_PASS}",
        "-H", "X-SU-Geo: China",
        url, "--max-time", "5",
        "-o", "/tmp/cat4_test.html"
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=8)
    parts = result.stdout.strip().split("|")
    status, size = parts[0], parts[1] if len(parts) > 1 else "?"

    try:
        with open("/tmp/cat4_test.html") as f:
            content = f.read()
    except FileNotFoundError:
        content = ""

    has_baxia = "baxia" in content.lower() or "_____tmd_____" in content
    offers = len(set(re.findall(r'/offer/(\d+)\.html', content)))
    title_m = re.search(r'<title>(.*?)</title>', content)
    title = title_m.group(1)[:50] if title_m else ""

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
    print(f"  [{i+1:2}] [{label:5}] {size:>8}b  off={offers:3}  {url[:55]:55}  {title[:25]}", flush=True)
    time.sleep(0.2)

print(f"\n\n*** NEW OK PAGES (ranked by offers): ***\n", flush=True)
for url, offers, size, title in sorted(results, key=lambda x: -x[1]):
    print(f"  {offers:3} offers  {size:>8}b  {url}  -- {title}", flush=True)

print(f"\nTotal new OK pages: {len(results)}", flush=True)
