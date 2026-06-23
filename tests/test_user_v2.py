#!/usr/bin/env python3
"""
Final attempt: 1688 subdomains for user's categories + more aggressive pinyin variations.
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

# More aggressive pinyin + compound words + related
CANDIDATES = [
    # ========== Tools (ferramentas) ==========
    "https://shougong.1688.com/",         # 手工 (handcraft)
    "https://shougongju.1688.com/",       # 手工锯
    "https://dianji.1688.com/",           # 电机 (electric motor)
    "https://luoding.1688.com/",          # 螺钉 (screws)
    "https://luomu.1688.com/",            # 螺母 (nuts)
    "https://qianzi.1688.com/",           # 钳子 (pliers)
    "https://bazi.1688.com/",             # 扳子 (wrench)
    "https://chizi.1688.com/",            # 尺子 (ruler)
    "https://dianzichui.1688.com/",       # 电子锤
    "https://dianzu.1688.com/",           # 电阻 (resistor)
    "https://daodian.1688.com/",          # 导电
    "https://beng.1688.com/",             # 泵 (pump)
    "https://famen.1688.com/",            # 法兰 (flange)
    "https://kaiguan.1688.com/",          # 开关 (switch)
    "https://chazuo.1688.com/",           # 插座 (socket)
    "https://fanglei.1688.com/",          # 阀类 (valves)
    "https://peijian.1688.com/",          # 配件 (parts)
    "https://dianyuan.1688.com/",         # 电源 (power supply)
    "https://diandonggongju.1688.com/",  # 电动工具
    "https://qiazi.1688.com/",            # 卡子

    # ========== Socks/Meias ==========
    "https://wazi.1688.com/",             # 袜子
    "https://wason.1688.com/",            # English-sounding
    "https://nvtongxie.1688.com/",        # 女童袜
    "https://nantongxie.1688.com/",       # 男童袜
    "https://jiwai.1688.com/",            # 寄卖
    "https://fangzhi.1688.com/",          # 纺织 (textile) - tested, 17
    "https://wenzi.1688.com/",            # 文字
    "https://wa.1688.com/",               # 袜
    "https://fushi.1688.com/",            # 服饰 (clothing) - already tested
    "https://fuzhuang.1688.com/",         # 服装 (clothing) - already tested
    "https://hufu.1688.com/",             # 护肤 (skincare)

    # ========== Electric scooters ==========
    "https://dianche.1688.com/",          # 电动车 - already
    "https://pinghengche.1688.com/",      # 平衡车 - already
    "https://dianping.1688.com/",         # 电平 (?)
    "https://e-bike.1688.com/",
    "https://dunch.1688.com/",            # 蹲车 (?)
    "https://fadian.1688.com/",           # 发电 (power gen)
    "https://chongdian.1688.com/",        # 充电 (charging)
    "https://dianji.1688.com/",           # 电机 (motor)
    "https://dianbeng.1688.com/",         # 电泵
    "https://qiche.1688.com/",            # 汽车
    "https://jiadian.1688.com/",          # 家电 (home appliances) - already
    "https://kongtiao.1688.com/",         # 空调 (AC)
    "https://bingxiang.1688.com/",        # 冰箱 (fridge) - already
    "https://dianshi.1688.com/",          # 电视 (TV)
    "https://dianyuan.1688.com/",         # 电源 (power)
    "https://shouji.1688.com/",           # 手机 (mobile phone)
    "https://diannao.1688.com/",          # 电脑 (computer)

    # ========== Kitchen items ==========
    "https://chufang.1688.com/",          # 厨房
    "https://cangui.1688.com/",           # 餐具 (already 361b)
    "https://daogui.1688.com/",           # 刀具 (already)
    "https://kettle.1688.com/",           # already
    "https://chuju.1688.com/",            # 厨具
    "https://cayin.1688.com/",            # 茶饮
    "https://cajing.1688.com/",           # 茶具
    "https://yueqi.1688.com/",            # 餐具
    "https://cha.1688.com/",              # 茶
    "https://jiushui.1688.com/",          # 酒水 (drinks)
    "https://chaohuo.1688.com/",          # 潮货
    "https://zhubo.1688.com/",            # 竹帛
    "https://shicai.1688.com/",           # 石材
    "https://banchai.1688.com/",          # 板材
    "https://bamboo.1688.com/",           # 竹制品
    "https://mucai.1688.com/",            # 木材
    "https://zaocan.1688.com/",           # 早餐
    "https://shiwu.1688.com/",            # 食物
    "https://jinkou.1688.com/",           # 进口
    "https://jiushui.1688.com/",          # 酒水
    "https://yinliao.1688.com/",          # 饮料

    # ========== Garden tools ==========
    "https://yuanlin.1688.com/",          # 园林
    "https://huayuan.1688.com/",          # 花园
    "https://nongye.1688.com/",           # 农业
    "https://nongzi.1688.com/",           # 农资
    "https://nongji.1688.com/",           # 农机
    "https://penya.1688.com/",            # 喷雾
    "https://shuisheng.1688.com/",        # 水生
    "https://shuiguan.1688.com/",         # 水管
    "https://diaopeng.1688.com/",         # 雕棚
    "https://geng.1688.com/",             # 耕
    "https://chucao.1688.com/",           # 除草 (weed)
    "https://shifei.1688.com/",           # 施肥 (fertilizer)
    "https://shuiwu.1688.com/",           # 睡物

    # ========== Underwear ==========
    "https://neiyi.1688.com/",            # 内衣
    "https://neiku.1688.com/",            # 内裤
    "https://wenchong.1688.com/",         # 文胸 (bra)
    "https://sleepwear.1688.com/",        # 睡衣 (pajama)
    "https://pijuan.1688.com/",           # 皮卷
    "https://yurong.1688.com/",           # 羽绒 (down)
    "https://yurongfu.1688.com/",         # 羽绒服 (down jacket)
    "https://mianyi.1688.com/",           # 棉衣 (cotton clothing)
    "https://chenyi.1688.com/",           # 衬衣
    "https://nui.1688.com/",              # 衤
    "https://waiyi.1688.com/",            # 外衣
    "https://pajama.1688.com/",           # 睡衣

    # ========== Misc that might work ==========
    "https://jiage.1688.com/",            # 价格 (price)
    "https://dijia.1688.com/",            # 底价
    "https://taobao.1688.com/",           # 淘宝
    "https://chongwu.1688.com/",          # 宠物 (pet)
    "https://wanju.1688.com/",            # 玩具 (toys) - tested 0
    "https://ertong.1688.com/",           # 儿童
    "https://qinzi.1688.com/",            # 亲子
    "https://yinshua.1688.com/",          # 印刷
    "https://bangong.1688.com/",          # 办公 (office)
    "https://fanyi.1688.com/",            # 翻译
    "https://lvyou.1688.com/",            # 旅游 (travel)
    "https://lv.1688.com/",               # 旅
    "https://yao.1688.com/",              # 药 (medicine)
    "https://yaopin.1688.com/",           # 药品
    "https://yiyao.1688.com/",            # 医药
    "https://yaoxiang.1688.com/",         # 药箱
    "https://jian.1688.com/",             # 建
    "https://jianzhu.1688.com/",          # 建筑 (construction)
    "https://fangwu.1688.com/",           # 房屋 (housing)
    "https://fangchan.1688.com/",         # 房产 (real estate)
    "https://car.1688.com/",              # 车 (car) - already
    "https://moto.1688.com/",             # 摩托
    "https://tie.1688.com/",              # 铁 (iron)
    "https://gang.1688.com/",             # 钢
    "https://su.1688.com/",               # 塑
    "https://gang.1688.com/",             # 钢
    "https://gangsi.1688.com/",           # 钢丝 (steel wire)
    "https://gangguo.1688.com/",          # 钢锅
    "https://tie.1688.com/",              # 铁
    "https://tong.1688.com/",             # 铜
    "https://lvse.1688.com/",             # 绿色 (green)
    "https://lvhua.1688.com/",            # 绿化
    "https://hua.1688.com/",              # 花
    "https://jian.1688.com/",             # 减
    "https://shouji.1688.com/",           # 手机
    "https://shuma.1688.com/",            # 数码 - already BAXIA
    "https://dianzhi.1688.com/",          # 滴汁
    "https://hudie.1688.com/",            # 蝴蝶
    "https://zhu.1688.com/",              # 猪 (pig - food)
    "https://niu.1688.com/",              # 牛 (cow - food)
    "https://yang.1688.com/",             # 羊 (sheep)
    "https://ji.1688.com/",               # 鸡 (chicken)
    "https://rou.1688.com/",              # 肉 (meat)
    "https://dian.1688.com/",             # 店 (shop)
    "https://jie.1688.com/",              # 街 (street)
    "https://xi.1688.com/",               # 洗 (wash)
    "https://xidi.1688.com/",             # 洗涤
    "https://xifu.1688.com/",             # 西服 (suit)
    "https://guan.1688.com/",             # 关/馆
    "https://jiuk.1688.com/",             # 久客
    "https://yifu.1688.com/",             # 衣服 (clothes)
    "https://yongju.1688.com/",           # 用具
    "https://yiqi.1688.com/",             # 仪器 (instrument)
    "https://qicai.1688.com/",            # 器材
    "https://qixie.1688.com/",            # 器械
    "https://shebei.1688.com/",           # 设备 (equipment)
    "https://jixie.1688.com/",            # 机械 (machinery)
    "https://jiagong.1688.com/",          # 加工 (already 155)
    "https://wuliao.1688.com/",           # 物料 (materials)
    "https://liao.1688.com/",             # 料
    "https://yu.1688.com/",               # 鱼 (fish)
    "https://yu.1688.com/wujin/",         # 五金 (hardware)
    "https://wujin.1688.com/",            # 五金
    "https://gongcheng.1688.com/",        # 工程 (engineering)
    "https://gong.1688.com/",             # 工
    "https://gongyepin.1688.com/",        # 工业品 (industrial)
    "https://jianzhucai.1688.com/",       # 建材 (building materials)
    "https://jiancai.1688.com/",          # 建材
    "https://cailiao.1688.com/",          # 材料
    "https://cailiao.1688.com/jiagong/",  # 加工材料
]

print(f"Testing {len(CANDIDATES)} candidates...\n", flush=True)

results = []
for i, url in enumerate(CANDIDATES):
    cmd = [
        "curl", "-s", "-k", "-w", "%{http_code}|%{size_download}",
        "-x", "https://unblock.decodo.com:60000",
        "-U", f"{SU_USER}:{SU_PASS}",
        "-H", f"X-SU-User: {SU_USER}",
        "-H", f"X-SU-Password: {SU_PASS}",
        "-H", "X-SU-Geo: China",
        url, "--max-time", "4",
        "-o", "/tmp/cat5_test.html"
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=6)
    parts = result.stdout.strip().split("|")
    status, size = parts[0], parts[1] if len(parts) > 1 else "?"

    try:
        with open("/tmp/cat5_test.html") as f:
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

    if label == "OK" and offers > 0:
        results.append((url, offers, size, title))
    if label in ("OK", "BAXIA") and offers > 0:
        print(f"  [{i+1:2}] [{label:5}] {size:>8}b  off={offers:3}  {url[:55]:55}  {title[:25]}", flush=True)
    time.sleep(0.15)

print(f"\n\n*** PAGES WITH OFFERS: ***\n", flush=True)
for url, offers, size, title in sorted(results, key=lambda x: -x[1]):
    print(f"  {offers:3} offers  {size:>8}b  {url}  -- {title}", flush=True)
