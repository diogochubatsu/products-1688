
Comprehensive documentation of 1688.com scraping research, BaXia bypass, discovery mechanisms, and Chinese aggregator tools research. 100% focused on 1688.

**Date**: 2026-06-23 (v2 CLOSED)

## 1. Status (2026-06-23 — v2 CLOSED at 95%)
**Workspace**: /mnt/ssd/1688-only/
**For**: Diogo Chubatsu / ImportaSimples

---

## TL;DR - One-Page Summary (UPDATED 2026-06-23 — v2 CLOSED at 95%)

**Sprint 4 v2 complete: 294 silver offers, 273 Rakumart matched (92.9%), 9 N1 cats with deep taxonomy.**

Sprint 4 progression:
- Sprint 1+2+3: 212 offers (5 cats: beach_clip, underwear, drill, socks, organization)
- Sprint 4 tiny: +30 (added flashlight, webcam, expanded organization) — $0.15, 5min
- Sprint 4 v2: +52 (added butt-lifting shapewear, seamless panties, no-show/sports/kids socks) — $0.30, 22min

**Key discoveries in Sprint 4**:
- SU+Headless+Markdown works (46s/page vs 3s baseline) — useful as fallback for hard targets, NOT bulk
- Flashlight + webcam were "0% matched" earlier — FALSE NEGATIVE. After crosswalk --source 1688: flashlight 90%, webcam 60% matched
- Crosswalk via --source 1688 is more effective than --source alibaba for 1688 data
- 6 subcategories of underwear/socks have ~60% match rate (varying by subcategory)

**GAME CHANGER: 1688 search works via MTOP API (QuoVadis86/ai-reverse SDK).**
No proxy, no cookies, no browser, no BaXia. Calls `h5api.m.1688.com/h5/mtop.relationrecommend.wirelessrecommend.recommend/1.0/` with auto-fetched `_m_h5_tk` token. Login is one POST that returns 200 OK — no captcha.

**What works NOW**:
- ✅ **MTOP API search** (ai-reverse SDK) — keyword search, 2000+ results per query, returns offerId/title/price/shop/region/factoryInspection. Validated with K15 mic (60 products), 蓝牙耳机, 智能手表, 充电宝.
- ✅ Decodo SU/SCRAPE for detail pages (100%)
- ✅ 13 trending verticals (factory, 321, tongzhuang, fuzhuang, etc) = 470+ products
- ✅ m.1688.com mobile crawler via BFS = 15+ K15 mics in 3.6 min
- ✅ Chinese free tools: 1688 Chrome Extension, 店小秘 ERP

**What doesn't**:
- ❌ Desktop search (4-layer BaXia block) — BYPASSED via MTOP
- ❌ Baidu search (captcha)
- ❌ 240+ user pinyin subdomains (all blocked) — UNNECESSARY now via MTOP
- ❌ Onebound "free tier" — ¥5K/year (R$300/mo), use MTOP instead
- ❌ ElimAPI — **PHANTOM, does not exist** (NXDOMAIN, no archives, 0 GitHub repos)
- ⚠️ Yiwugo 义乌购 — works but API needs CSRF/cookies (browser-only)
- ⚠️ Parse.bot — 100 cr/mo free, signup friction unknown (test timed out)

**Best opportunity**: **MTOP API via ai-reverse SDK** is the new 4th data source. Already producing real offers with offerId/title/price/shop/region for any Chinese keyword query.## Table of Contents

1. [Status (2026-06-16)](#status)
2. [BaXia Anti-Bot Deep Dive](#baxia)
3. [Discovery Mechanisms](#discovery)
4. [Chinese Tools Research (NEW)](#chinese-tools)
5. [Blocked Subdomains List](#blocked)
6. [Widget Structure](#widget)
7. [Working Pipelines](#pipelines)
8. [Data Files](#data)
9. [Proxy Configurations](#proxy)
10. [Lessons Learned](#lessons)
11. [Next Steps](#next)
12. [Appendix: Test Logs](#appendix)



### Proxies
| Proxy | Status | Use |
|-------|--------|-----|
| Decodo SU (datacenter) | OK | Detail pages (3s/page) |
| Decodo SU + Headless + Markdown | OK (slow) | Fallback for hard targets (46s/page) |
| Decodo Residential (US/BR/CN) | OK (unused) | Geo-specific scraping |
| Decodo Mobile (4G/5G) | OK (unused) | Strictest anti-bot |
| Decodo ISP (static) | OK (unused) | Session consistency |
| Firecrawl | OK (MCP) | Last-resort fallback |

### Data Collected (Sprint 1+2+3+4)
- **294 silver offers** (vs 212 before Sprint 4)
- **288 enriched** (97.9%)
- **273 Rakumart matched** (92.9%)
- **9 N1 categories with deep N1-N4 taxonomy** (35 N4 leaves). 5 N1 have data: 服装鞋帽, 户外运动, 五金工具, 电子数码, 家居日用
- **171 SU detail HTML files** in bronze/su_detail/ + N1-N4 taxonomy in data/taxonomy/
- **25 MTOP search JSON files** in bronze/mtop/
- **Rakumart crosswalk data** in bronze/rakumart/ (searches only)

### Files
- `data/bronze/mtop/{date}_*.json` — MTOP search responses (25 files)
- `data/bronze/su_detail/{date}_*.html` — SU enriched product pages (171 files)
- `data/bronze/rakumart/{date}_*.json` — Rakumart crosswalk searches (2 files)
- `data/silver/offers/{offer_id}.json` — silver layer (294 files)
- `data/silver/categories/*.json` — category metadata
- `data/gold/{rankings,by_category,to_source}/*.json` — gold layer rankings
- `data/_manifest.json` — aggregate stats

---

## 2. BaXia Anti-Bot Deep Dive

1688 uses 4-layer detection (discovered by analyzing JS in BaXia pages):

### Layer 1: IP Reputation
- Datacenter IPs (Decodo SU/SCRAPE) = BLOCKED for search
- HK Residential (Decodo trial) = bypassed for mobile
- Real HK VPS with Playwright = bypassed for mobile
- Solution: residential proxy ($5-15/GB) or HK VPS ($5-30/mo)

### Layer 2: User-Agent Spider Detection
Decodo default UA is "X11; Ubuntu; Linux; rv:122.0" = Linux+Spider pattern.
1688 JS code: `if (ua.indexOf('Spider') !== -1) { block }`
Solution: use real Chrome UA, Playwright = real browser fingerprint

### Layer 3: AWSC Captcha (Alibaba Web Security Captcha)
Active JS-based captcha similar to reCAPTCHA.
Libraries detected: awsc.js, baxiaCommon.js, um.js, collina.js, fireyejs.js
Page has window.__baxia__ namespace with getUIDisplay()
Solution: captcha solver (2captcha $3/1000, 10-30s latency)

### Layer 4: Session/Cookie Validation
- 1688 wants logged-in session for search
- Mobile m.1688.com does NOT require login (key insight!)
- Solution: scrape mobile site, or use logged-in account cookies

### The Login Wall (NEW DISCOVERY)
Even with HK residential + real browser fingerprint:
- Search page redirects to login.1688.com
- Mobile search redirects to mobile homepage (no products)
- 218KB desktop page = login page, 0 products in body
- 192KB mobile page = homepage, 0 products in body

The data is loaded via authenticated XHR after page load. Without session, products never render.

---

## 3. Discovery Mechanisms (4 working)

### 3.1 Trending Verticals (13 working, 470+ products)

13 trending verticals that work without search (verified 2026-06-16):

| Vertical | URL | Offers |
|----------|-----|--------|
| factory | factory.1688.com | 320 |
| 321 chengbiao | 321.1688.com/chengbiao | 40 |
| 321 liangpin | 321.1688.com/liangpin | 16 |
| tongzhuang | tongzhuang.1688.com | 110 |
| fuzhuang | fuzhuang.1688.com | 53 |
| muying | muying.1688.com | 48 |
| fushi | fushi.1688.com | 48 |
| shipin | shipin.1688.com | 30 |
| fangzhi | fangzhi.1688.com | 17 |
| sale | sale.1688.com | 21 |
| home | home.1688.com | 10 |
| suliao | suliao.1688.com | 10 |
| food | food.1688.com | 5 |
| jiagong | jiagong.1688.com | 155 |

Total: 470+ offer IDs across 13 verticals.

### 3.2 m.1688.com Mobile Crawler (BREAKTHROUGH)
Mobile m.1688.com does NOT require login. m.1688.com/offer/ID.html returns 20-27 related products in HTML. BFS chain discovers hundreds of products from 1-2 seed IDs.

**Verified**: 2 seed IDs (carrot toy + K15 mic) -> 15 unique products in 3.6 min. All K15 mics with real prices.

**Implementation**: tests/crawler.py uses Playwright + HK residential + BeautifulSoup regex on /offer/ID.html links.

**Status**: WORKED. HK residential proxy died after 15 products. Need to retry with new residential proxy.

### 3.3 Detail Page Scraping (100% works)
detail.1688.com/offer/ID via Decodo SU returns 104KB with window.context containing:
- widgets.productTitle.data.title
- widgets.gallery.data.images[]
- widgets.mainPrice.data.price.df.defaultPrice
- widgets.shippingServices.data.weight
- widgets.skuContainer.data.skuMap

Decodo SCRAPE API returns 114KB JS-rendered page (3.3s, 200 OK).

### 3.4 Official 1688 Ranking API (NEW - not yet tested)
1688 has official ranking API at developer.aliyun.com/article/1677848:
- Method: alibaba.item.search.best
- Endpoint: 1688/item_search_best/
- Returns: offerId, title, price, saleCount (30d), 40+ fields
- Update: hourly
- Response: <=300ms enterprise
- Categories: 20+
- Filters: rankid, rank_type (complex|hot|goodPrice), language, region

**STATUS**: Not yet accessed. Need to register as developer at open.1688.com.

---

## 4. Chinese Tools Research (NEW - 2026-06-16)

Researched 47 unique URLs of Chinese 1688 tools. See data/chinese_tools_research.json for full structured summary.

### 4.1 APIs (Best for automation)

#### 1688 Official Ranking API (developer.aliyun.com)
```python
# Example: get hot products in category
url = "1688/item_search_best/?key=YOUR_KEY&rankid=1031918&rank_type=hot&language=en"
# rank_type: complex (综合) | hot (热卖) | goodPrice (好价)
# Returns: offerId, title, price, saleCount, evaluateScore, categoryId, sellerId
# Update: hourly, 300ms response
# Cost: NOT free for production. See Section 4.6 for real pricing.
```
**Access**: Register at open.1688.com -> Apply for ranking API. Requires 1688 account (Chinese phone) as ISV.

#### 1688 Open Platform (open.1688.com)
Official Alibaba 1688 developer platform. API categories:
- 商品 (Products) - https://open.1688.com/api/apidocdetail.htm?aopApiCategory=product_new
- 订单 (Orders)
- 支付 (Payment)
- 物流 (Logistics)
- 跨境铺货 (Cross-border listing)
- 一键铺货 (Bulk listing)

For ISVs, ERPs, cross-border tool providers. Registration required.

#### Onebound (open.onebound.cn)
3rd party API aggregator. 20+ marketplaces. Has:
- 1688.item_get (product detail)
- 1688.item_search (search)
- 1688.item_search_best (ranking)

#### Open Claw 1688 (3rd party)
Fast keyword search API:
- 0.3s response, no CAPTCHA, no IP limit
- Fields: title, price, sales, num_iid, area, detail_url
- Filters: price range, sales sort, location, free shipping, 48h delivery
- Python SDK
- Pay per call

### 4.2 Selection/Analysis Tools (Web UI)

#### 店雷达 (Dianleida) - https://www.dianleida.net
- 5 official 1688 ranking lists:
  - 热销商品榜 (Hot Products)
  - 飙升商品榜 (Soaring Products)
  - 上新商品榜 (New Products)
  - 复购率商品榜 (Repurchase Rate)
  - 1688好货榜 (Quality Goods)
- 1688-focused, deep supplier analysis
- Free tier + paid ($5-30/mo estimated)

#### Sorftime - https://www.sorftime.com
- AI-driven selection
- Released 1688 plugin Dec 2025
- MCP workflow for Amazon/1688 cross-platform
- Profit calculation
- Paid (pricing not found on website)

#### 电霸 (Dianba)
- Multi-platform (Amazon, Shopee, TikTok)
- Less 1688 depth
- Free tier + paid

#### 1688 Official Chrome Extension - https://chajian.1688.com
- Name: 1688采购助手 (1688 Purchasing Assistant)
- FREE
- Features:
  - 以图搜同款 (Image search same product)
  - AI assist
  - Product info enhancement
  - Material downloads
  - Sales/price trends
  - Order/message notifications
- Available: Chrome, Edge, 360, Quark, QQ

### 4.3 ERPs (Full management)

| ERP | Cost | Users | 1688 |
|-----|------|-------|------|
| 店小秘 ERP (dianxiaomi.com) | FREE | 1.8M+ | Yes |
| 妙手 ERP (erp.91miaoshou.com) | Free tier | - | Yes, scraping |
| 领星 ERP | Paid | - | Official partner |
| 斑马 ERP | Paid | - | Official partner |
| 1688货源宝 (eccang.com) | Free + paid | - | Sourcing compare |

### 4.4 Tool Comparison

| Tool | Cost | Best For | Limitation |
|------|------|----------|------------|
| 店雷达 | ~R$35/mo | 1688 depth | Limited cross-platform |
| Sorftime | Free trial + paid | AI selection | New (Dec 2025) |
| 电霸 | Free + paid | Multi-platform | Less 1688 depth |
| 1688 Official Extension | FREE | Browsing | Browser-based |
| 1688 Open Platform API | Free for ISV (needs Chinese phone) | Programmatic, official | Registration blocked |
| Onebound 1688 API | **NOT FREE** (¥5,000/yr ~ R$300/mo) | 20+ marketplaces, ranking | 3rd party, paid |
| Open Claw | $0.003/call (~R$0.015) | Quick integration | 3rd party |
| 店小秘 ERP | FREE | General ERP | Less specialized |
| **Parse.bot** | **100 credits/mo FREE** | Product detail API | Limited free tier |
| ~~**ElimAPI**~~ | PHANTOM — does not exist (NXDOMAIN, no archives, no repos) | - | removed 2026-06-16 |



### 4.6 Free vs Paid — TABELA CORRIGIDA (2026-06-16)

**PITFALL CORRIGIDO #1 (Onebound)**: Earlier this session, the `api_info: today:0 max:50` field from Onebound test account was misinterpreted as "free tier 100 calls/day". WRONG. `max:N` is the test/demo account limit, NOT production free tier. Always verify on the provider's pricing page.

**PITFALL CORRIGIDO #2 (ElimAPI) — REMOVED 2026-06-16**: The "ElimAPI 200 req/mo free" reference in our notes was a **phantom**. elimapi.com = NXDOMAIN, zero Wayback archives, zero GitHub repos. The reference had no source URL and appears to have been hallucinated. Lesson: **always verify a service exists (DNS + Wayback) before adding it to a comparison table**.

**Real pricing** (verified via pricing pages, not marketing copy):

| Provider | Free tier | Paid | Real cost |
|----------|-----------|------|-----------|
| **Parse.bot** | 100 credits/mo | $0-100/mo | $0 to test |
| ~~**ElimAPI**~~ | PHANTOM | - | removed 2026-06-16 (was hallucinated source) |
| **OTCommerce** | none | **$0.003-0.006/call** | R$0.015/call |
| **Apify 1688 actor** | none | $30/mo + usage | $30+/mo |
| **Oxylabs 1688** | 2K results trial | $49-249/mo | $49+/mo |
| **Onebound 1688 API** | **NOT FREE** | **¥5,000/year** (1688 only) | **~R$300/mo** |
| **Onebound full system** | none | ¥28,000-798,000 | $4K-$110K |
| **Onebound image search** | none | ¥14,400/year | extra |
| **Dianleida 店雷达** | trial | **~49元/mo (~$7 / R$35)** | R$35/mo |
| **Sorftime** | free trial | varies | check website |
| **Dianxiaomi 店小秘 ERP** | **FREE** | - | 1.8M users |
| **1688 Chrome Extension** | **FREE** | - | official |
| **Yiwugo 义乌购** | **NOT TESTED** | - | 1688 ecosystem, less anti-bot |
| **Alibaba.com GGS API** | free beta for GGS | pay-per-call | only if GGS member |

**Low budget recommendation** (by ROI):

1. **Yiwugo (义乌购)** — test 30s with curl, no credential. Same 1688 ecosystem.
2. **Parse.bot** — 1 min signup, 100 credits free, real product detail API.
3. ~~**ElimAPI**~~ — REMOVED 2026-06-16, phantom reference (NXDOMAIN).
4. **1688 Chrome Extension** — install locally for manual browsing.
5. **OTCommerce** — only if true pay-per-use needed ($0.003/call).
6. **Onebound** — only if budget allows (R$300+/mo).
7. **Open 1688 Platform** — only if Diogo has 1688 account + Chinese phone.

## 5. Blocked Subdomains (240+ tested, ALL BAXIA)

User asked for 7 categories (tools, socks, scooters, kitchen, garden, underwear, etc). 240+ pinyin subdomains tested. ALL blocked by BaXia.

**Tools (gongju, wujin, dianqi, jixie, dianli, famen, shougong, luosi, diandong)** - all BaXia

**Socks (wazi, wason, tongxie, nvxie, nanxie)** - all BaXia

**Scooters (dianche, diandongche, zixingche, pinghengche, motuo)** - all BaXia

**Kitchen (chufang, canyin, cangui, daogui, chuju, cajing)** - all BaXia

**Garden (yuanlin, huayuan, nongye, nongzi, nongji)** - all BaXia

**Underwear (neiyi, neiku, wenchong, sleepwear, pajama, yurong, mianyi)** - all BaXia

**fushi.1688.com** is the only one that worked (48 offers).

The reason: these are niche categories that 1688 doesn't promote. 1688 only protects popular URLs in its trending pages. Niche subdomains are BaXia-gated.

---

## 6. Widget Structure (2024+)

Modern 1688 detail pages use a widget-based architecture. Data is in window.context as a JSON object with widgets:

```javascript
window.context = {
  widgets: {
    productTitle: {
      data: {
        title: "K15 无线麦克风 蓝牙...",
        subject: "...",
        categoryId: ...
      }
    },
    gallery: {
      data: {
        images: [
          {url: "https://cbu01.alicdn.com/...", size: "300x300"},
          ...
        ]
      }
    },
    mainPrice: {
      data: {
        price: {
          df: {
            defaultPrice: "15.50",
            priceRange: [{price: "15.50", begin: 1, end: 99}, ...]
          }
        }
      }
    },
    shippingServices: {
      data: {
        weight: "0.5",
        toCountries: [...]
      }
    },
    skuContainer: {
      data: {
        skuMap: [
          {skuId: "...", price: "...", specs: {...}},
          ...
        ]
      }
    },
    videoInfo: {
      data: {
        videoUrl: "https://cloud.video.taobao.com/..."
      }
    }
  }
}
```

Extractor: tests/reextract_v3.py uses this structure. 63% success rate (244/383 products).

---

## 7. Working Pipelines

### 7.1 Trending Discovery Pipeline
1. Fetch 13 trending pages via Decodo SU
2. Extract /offer/ID.html links with regex
3. Save to data/trending_offer_ids.json (422 IDs)
4. Pipeline: tests/discover_all_trending.py (3510 bytes)

### 7.2 Detail Scraping Pipeline
1. Read offer IDs from trending_offer_ids.json
2. For each, fetch detail.1688.com/offer/ID via Decodo SU
3. Extract widgets from window.context IIFE
4. Save to data/trending_products.json (244 products)
5. Pipeline: tests/full_pipeline.py (8427 bytes), tests/reextract_v3.py (6361 bytes)

### 7.3 Mobile Crawler Pipeline (experimental)
1. Seed with 1-2 offer IDs (e.g., K15 mic, carrot toy)
2. Fetch m.1688.com/offer/ID via Playwright + HK residential
3. Extract 20-27 related product IDs from HTML
4. Add to queue, BFS repeat depth 3
5. Pipeline: tests/crawler.py (5507 bytes)
6. Result: 15 K15 products in 3.6 min from 2 seeds

### 7.4 SCRAPE API Pipeline
Decodo SCRAPE API (different creds from SU) does JS rendering:
- Endpoint: decodo.com/api/scrape (varies)
- Params: url, render=true, geo=...
- Returns: 114KB HTML with window.context
- Use when SU doesn't render JS (e.g., dynamic content)

---

## 8. Data Files

```
data/
├── trending_products.json      # 605KB, 244 final products
├── trending_products.csv       # Summary CSV
├── trending_offer_ids.json     # 422 IDs + sources
├── crawl_k15_results.json      # 15 K15 mics from BFS
├── chinese_tools_research.json # 4.6KB, this research
├── mobile_home_2026_06_16.html # 242KB, m.1688.com home
├── mobile_detail_740647797173.html # 715KB, 27 related
├── decodo_scrape_response.json # 25KB AWSC captcha page
└── research_tools.py           # Research script
```

---

## 9. Proxy Configurations

### 9.1 Decodo SU (Site Unblocker) — BREAKTHROUGH 2026-06-16

**Working credentials (NEW)**:
```
SU_USER=U0000434457
SU_PASSWORD=***
Endpoint: unblock.decodo.com:60000
```

**CRITICAL HEADERS (without these, auth fails with 401):**
```
X-SU-Geo: China
X-SU-Locale: zh-cn
```

**What it works for**:
- `detail.1688.com/offer/{ID}.html` → 90-100KB full detail (SKU, 200+ images, price ladder, supplier)
- `m.1688.com/offer/{ID}.html` → 178KB mobile detail
- `m.1688.com/winport/page/index.html?memberId=...` → 120KB shop catalog
- 1688 company search (loads but empty)

**Rate limit**: 3s delay MIN between requests (without delay, 60% fail).

**Geo options**:
- `X-SU-Geo: China` → CN IP (Jinan) — BEST for 1688
- `X-SU-Geo: HongKong` → HK IP
- `X-SU-Geo: United States` → US IP (Los Angeles)

**DEAD credentials** (do not use, was in old .env):
- U0000402799 — account disabled ("User is disabled, please contact support")

### 9.2 Decodo Mobile (4G) — working 2026-06-16
```
MOBILE_USER=spraglxgvk
MOBILE_PASSWORD=***
Endpoint: gate.decodo.com:10001
Returns: US IPs (Jacksonville, FL)
Use: Sites that detect datacenter proxies
```

### 9.3 Decodo Residential — working 2026-06-16
```
RESIDENTIAL_USER=span5nxws5
RESIDENTIAL_PASSWORD=***
Endpoint: gate.decodo.com:10001
Returns: Random country IPs
Use: For sites that need varied residential IPs
```

### 9.4 Decodo ISP (Static Residential) — not tested
```
ISP_USER=sp2idylm9q
ISP_PASSWORD=***
Endpoint: isp.decodo.com:10001
Note: Have creds but not tested yet. May have CN geo that SU lacks.
```

### 9.5 Decodo Scraping API — out of balance
```
API_KEY=*** (Basic auth)
Endpoint: scraper-api.decodo.com/v2/scrape
Status: needs top-up
```

### 9.6 Decodo MCP Server — setup pending
```
MCP_USER=U0000432181
MCP_PASSWORD=PW_18394bac315ef747efe9aa6179cc9e429
github.com/Decodo/mcp-server
Status: setup pending, could automate the whole pipeline
```

**DEAD old Residential (was working 2026-06-16, expired)**:
- spvgqh3ebj (auth) / FHi=nhAzktkrO71q78 (pass) at gate.decodo.com:10001-10010

**DEAD old ISP (was working 2026-06-16, expired)**:
- sp2idylm9q at isp.decodo.com:10000 in old format (returns 407)
- **New format: sp2idylm9q (no prefix) at isp.decodo.com:10001** (not tested)

### 9.7 Complete Decodo Pipeline (2026-06-16)

```
Discovery  → MTOP (free, 14/s, 2000/q, Chinese queries only)
Detail     → Decodo SU China (~$0.005, 3s delay, X-SU-Geo: China header)
BRL        → Rakumart BR (free, 3 sources: 1688/alibaba/taobao)
Cross-walk → Title-based matching (3 ID systems, no ID match)
```

**Cost**: 10 categories × 100 products = **$5** in Decodo detail enrichment.
**Time**: ~6 min per category (with 3s delay).

**Full strategy doc**: `docs/STRATEGY-1688-SCRAPING-INTEL.md` (33KB, 16 sections, complete reference).


---

## 10. Lessons Learned

1. **IP reputation is the #1 BaXia filter** - datacenter IPs always blocked
2. **Mobile m.1688.com is the backdoor** - no login, no captcha, related products in HTML
3. **JS-rendered shells reveal 0 products** - even SCRAPE API doesn't render authenticated XHR
4. **Widget structure > legacy extraction** - 2024+ pages use widgets.productTitle, etc
5. **Search engines can't help 1688** - Baidu captcha, Google no results, Bing limited
6. **24-hour residential trial = enough for proof of concept** - 15 products in 3.6 min
7. **1688 has official ranking API** - developer.aliyun.com has the docs (just need access)
8. **Best sellers pages exist but require login** - kj.1688.com/best_seller.html is public URL
9. **The user was right** - Amazon/ML best sellers are public, 1688 best sellers are gated
10. **Chinese aggregator tools exist for every need** - Dianleida, Open Claw, Sorftime, ERPs
11. **FREE options exist** - 1688 Official Chrome Extension, 店小秘 ERP (1.8M users)
12. **PCP (Picture Compare Price) is hard** - 1688 official extension is the best free option
13. **BFS chain of related products = infinite discovery** - start with 1 seed, get 100+ via 3-4 hops
14. **Trending verticals are pure gold** - 13 verticals = 470+ offers, no search needed
15. **Always test the proxy after time** - residential proxies die, datacenter SU keeps working
16. **Don't trust `api_info:max:N` as free tier** - it's test/demo account limit. Always verify pricing on provider's pricing page (Onebound 1688 = ¥5K/year, NOT free).

---

## 11. Next Steps (Priority Order)

### Immediate (no cost)
- [x] Save all learnings to memory
- [x] Update README with complete research
- [ ] Install 1688 Official Chrome Extension locally
- [ ] Test 店雷达 free tier signup

### Short term (1-3 days, $0-50)
- [ ] Register on open.1688.com as developer
- [ ] Apply for Ranking API access
- [ ] Integrate 1688 Official API in our pipeline
- [ ] Replace trending discovery with API calls

### Medium term (1-2 weeks, $0-50)
- [ ] Test Yiwugo (义乌购) — 30s, free, no creds
- [ ] Sign up Parse.bot — 1 min, 100 free credits/mo
- [ ] Install 1688 Chrome Extension locally for manual browsing
- [ ] Sign up 店雷达 paid tier (R$35/mo) only if free options insufficient
- [ ] Build cron for daily hot products refresh
- [ ] Build BFS crawler (if proxy renewed)

### Long term (1+ month)
- [ ] Build Next.js app (port 3001)
- [ ] Hot products dashboard
- [ ] Match against Mercado Livre / Amazon BR
- [ ] Image search (reconsider if API allows)
- [ ] Profit calculation (1688 price -> BR price)

---

## 12. Appendix: Test Logs

### A. Decodo SU Detail Test
```
URL: https://detail.1688.com/offer/564915071391.html
Status: 200
Size: 104KB
Time: 5s
Headers: User-Agent, X-SU-User, X-SU-Password via curl
Body: HTML with window.context IIFE containing widgets
```

### B. Decodo SCRAPE Detail Test
```
URL: https://detail.1688.com/offer/564915071391.html
Status: 200
Size: 114KB
Time: 3.3s
Method: POST to decodo.com/api/scrape with render=true
Body: JS-rendered HTML, same window.context structure
```

### C. Decodo SCRAPE Search Test (BLOCKED)
```
URL: https://s.1688.com/selloffer/offer_search.htm?keywords=wireless+mic
Status: 200
Size: 3.2KB
Body: "Captcha Interstiction" - AWSC challenge page (246KB when JS rendered)
```

### D. HK Residential IP Check
```
IP: 108.165.220.0
Country: Hong Kong
City: Hong Kong
ISP: Lumen
Timezone: Asia/Hong_Kong
```

### E. Mobile Crawler Test (CACTUS SEED)
```
Seed: 740647797173 (carrot toy) + 729247767603 (K15 mic)
Result: 15 unique products in 3.6 min
Products: 12 K15 mics, 2 TWS earphones, 1 megaphone
Prices: ¥0.83 to ¥55.00
Method: BFS depth 2, Playwright + HK residential
```

### F. m.1688.com Home Test
```
URL: https://m.1688.com/
Status: 200
Size: 226KB
Title: 1688阿里巴巴
Offers: 8 in HTML (mobile)
```

### G. m.1688.com Offer Detail Test
```
URL: https://m.1688.com/offer/740647797173.html
Status: 200
Size: 715KB
Offers: 27 in HTML (related products)
Title: contains product name from <title> tag
```

### H. BaXia Page Analysis
```
Title: "Captcha Interstiction" (sic)
JS libs: awsc.js, baxiaCommon.js, um.js, collina.js, fireyejs.js, et_f.js
Namespace: window.__baxia__
Function: getUIDisplay()
Spider check: if (ua.indexOf('Spider') !== -1) { block }
```

---

**End of Document**

Generated by Hermes Agent. Last update: 2026-06-16 (TL;DR + 4.4 + 4.6 + 14 + 15 corrected for Onebound pricing).


---

## 13. Tasks 2-4: Registration, Extension, Pricing (NEW)

### Task 2: open.1688.com Registration Research

**Status**: Cannot register without 1688 account (requires Chinese phone).

**What we found**:
- 1688 Open Platform has **跨境综合解决方案（自用）** (Cross-border Comprehensive Solution - Self-use)
- Version 16.9, updated 2026-6-1
- Audience: 采购服务商 (Procurement Service Provider)
- APIs available:
  - **product.topList.query** (ranking: complex|hot|goodPrice|anchorHot|anchorNew|anchorRecommend|VNHot|VNTrend)
  - **product.search.keywordQuery** (multi-language keyword search)
  - **product.search.imageQuery** (multi-language image search)
  - **product.search.queryProductDetail** (with repeatPurchasePercent, tradeScore, isOnePsaleFreePostage)
  - **product.search.keywordSNQuery** (search nav filter)
  - **pool.product.pull** (batch pull up to 500K products)
- Need 1688 account (Chinese phone) to register as ISV

**Real test**: Console URL returns blank/0b (login required). Work platform shows login page with slider captcha.

### Task 3: 1688 Official Chrome Extension - DOWNLOADED

**Files**:
- `/mnt/ssd/1688-only/data/1688_official_extension.zip` (9.2MB)
- Direct from 1688's Aliyun OSS

**Extension details (from manifest.json)**:
- Version: 1.1.3, Manifest V3, built with Plasmo
- 145 files, 30+ language locales (en, zh, pt, es, de, fr, etc)
- Main JS: 4.8MB (FloatingAssistant.d52f9211.js)

**Content scripts (where it operates)**:
1. **s.1688.com/selloffer/offer_search.htm** - 1688 search page, runs **aiFindInMainSearch.js** (AI-enhanced search results!)
2. **<all_urls>** - FloatingAssistant on every website
3. **Cross-border seller platforms**: seller.shopee.cn, seller.ozon.ru, seller.tiktokshopglobalselling.com, seller.kuajingmaihuo.com
4. <all_urls> - another script (probably for 1688 detail)

**Permissions**: storage, cookies, webRequest, webNavigation, scripting, contextMenus, declarativeNetRequest

**Key insight**: The extension injects an AI search enhancement into 1688's search page. This means: install extension -> search works with AI features -> get more product data.

### Task 4: Specific Pricing Research

**店雷达 (Dianleida)**: ~49元/mo (~$7 / R$35) per AMZ123 review

**Sorftime**:
- 5.0 version
- New user free trial (限时免费)
- 21 global sites, 500K users, 48 countries
- 5 products: PC software, Web plugin, WeChat mini-program, **API/CLI**, **MCP service**
- Pricing page: https://www.sorftime.com/en-US/price/index?platform=amz
- 1688 跨境选品助手 is a feature in both PC and plugin versions

**Onebound** (CORRECTED 2026-06-16 — NOT FREE):
- 40,000+ clients, 30+ countries
- "立即注册，获取 1688跨境 & 淘宝海外 API 免费政策详情" — marketing copy, but real pricing:
  - **1688 API only**: ¥5,000/year (~$700, ~R$3,500/year, ~R$300/mo)
  - **Full system**: ¥28,000-798,000 ($4K-$110K)
  - **Image search add-on**: ¥14,400/year
  - **Reviews add-on**: ¥14,400/year
- PITFALL: "max:50" in test account response is demo limit, NOT free tier
- Contact: QQ 3142401606 / WeChat onebound1997
- **REAL API TEST**: 200 OK in 1.9s with fake key. Returns proper 4016 error for invalid key. Endpoint works, but no real free access.

**店小秘 ERP**: FREE, 1.8M users

**1688 Official Chrome Extension**: FREE

**Open Claw**: Pay per call, 0.3s response

---

## 14. The Onebound Myth (CORRECTED 2026-06-16)

**Original claim (WRONG)**: Onebound 1688 API is "free" and bypasses BaXia. User correctly corrected this. Reality:

The user asked if 1688 best sellers work like Amazon/ML. The answer is:
- **URLs exist publicly** (kj.1688.com/best_seller.html etc)
- **But content is login-gated** (no programmatic access)

**The "free" myth**:
- Onebound registration page says "立即注册，获取 1688跨境 & 淘宝海外 API 免费政策详情"
- Test account returns `api_info: today:0 max:50` — interpreted as "100 free calls/day"
- **WRONG**: `max:50` is the test/demo account limit, not production free tier
- **Real production cost**: ¥5,000/year (~R$300/mo) for 1688 API alone
- **Full system**: ¥28,000-798,000 ($4K-$110K)
- Endpoint DOES work (200 OK, 1.9s response, 4016 error for fake key)

**The real solution at our budget**:
1. **Yiwugo (义乌购)** — test now, free, no creds
2. **Parse.bot** — 100 free credits/mo, register in 1 min
3. ~~**ElimAPI**~~ — REMOVED 2026-06-16, phantom reference
4. **1688 Chrome Extension** — install locally, free
5. **What we have (470+ products)** — keep using it

**The endpoint still works** (if you have a real paid key):
```bash
curl "https://api-gw.onebound.cn/1688/item_search_best/?key=YOUR_KEY&secret=YOUR_SECRET&rankid=1031918&rank_type=hot&language=en"
```
Returns 20 products per call with title, pic_url, sales (30-day), num_iid, sort, goods_Score, detail_url.

Bypasses BaXia (Onebound handles scraping). But you pay for it.

---


---

## Data Browser UI (added 2026-06-23)

**Access:** `http://<host>:3003/` (table browser) and `http://<host>:3003/api/*` (JSON)

```
Server:    FastAPI on port 3003 (single port for HTML + API, same-origin)
Start:     cd /mnt/ssd/1688-only && /mnt/ssd/arbitlens/.venv/bin/python3 scripts/api_server.py
Endpoints: 11 total (manifest, categories, offers, search, stats/*, opportunities, image proxy)
Frontend:  public/index.html — table view with filters, sorting, image gallery
Image:    /api/image/{offer_id} — proxy with disk cache (bypasses Alibaba CDN hotlink)
```

### Current N1-N4 Taxonomy (2026-06-23)

```
服装鞋帽 (N1) 76 + 36 + 23 + 15 = 150 products
├─ 内衣 (N2)
│  ├─ 塑身衣 (N3) — 36 products (Modeladores)
│  │  ├─ 提臀塑身 (N4) 19 — Modelador levanta-bumbum
│  │  ├─ 连体塑身 (N4) 5  — Modelador corpo inteiro
│  │  └─ 收腹塑身 (N4) 1  — Modelador controle abdominal
│  ├─ 内裤 (N3) — 23 products (Cuecas/Calcínhas)
│  │  ├─ 无痕内裤 (N4) 13  — Calcinha sem costura
│  │  ├─ 女士内裤 (N4) 2   — Calcinha feminina
│  │  └─ 男士内裤 (N4) 8   — Cueca masculina
│  └─ 塑身裤 (N3) — 15 products (Calças modeladoras) [NEW 2026-06-23]
│     ├─ 提臀塑裤 (N4) 9   — Calça modeladora levanta-bumbum
│     ├─ 打底塑裤 (N4) 3   — Calça legging modeladora [NEW]
│     ├─ 收腹塑裤 (N4) 2   — Calça modeladora abdominal
│     └─ 安全塑裤 (N4) 1   — Short anti-luz modelador [NEW]
└─ 袜子 (N2)
   └─ 通用袜子 (N3) — 76 products (Meias)

其他 N1: 户外运动 (59), 五金工具 (50), 家居日用 (15), 电子数码 (20)
Total: 294 silver products across 9 N1 / 14 N2 / 16 N3 / 35 N4

## Recent Refactors (2026-06-23)

1. **Taxonomy: split 内裤 into 内裤 + 塑身裤** (commit dc2f12c)
   - 15 products reclassified based on title keywords (塑身/收腹/束腰/提臀)
   - 2 new N4 leaves: 打底塑裤, 安全塑裤
   - Total shapewear: 51 products (was 40 mixed in 内裤)

2. **API server deployed on port 3003**
   - Single port serves HTML + JSON (same-origin, no CORS)
   - 11 endpoints including image proxy with disk cache
   - Frontend: filters, sorting, pagination, image gallery, click-to-enlarge

3. **Git initialized** in /mnt/ssd/1688-only/ (separate from 1688-intel V3.0)
   - 609 files committed, 386K insertions
   - This is the local data lake, not the production GCP-deployed app

---

## 16. MTOP API BREAKTHROUGH (NEW - 2026-06-16 18:30)

### The Discovery

**QuoVadis86/ai-reverse** (https://github.com/QuoVadis86/ai-reverse, 9★, last commit 2026-05-15)
is a Python SDK that reverse-engineers 1688's mobile MTOP API gateway:
`https://h5api.m.1688.com/h5/{api_name}/{version}/`

The MTOP protocol signs each request:
```
sign = MD5(token & timestamp & appKey & data)
```

The SDK auto-fetches `_m_h5_tk` token by sending an "undefined"-signed probe
(no browser, no cookies). Server returns a real token via Set-Cookie.
Subsequent signed requests succeed — **bypassing BaXia entirely** for
the search endpoint.

### Validation Results (2026-06-16, 60+ products real)

| Query | Found | Returned | Price Range | Notes |
|-------|-------|----------|-------------|-------|
| K15 无线麦克风 | 2000 | 20/pg | ¥10-259 | Multiple K15 hits, factory inspection flags visible |
| 蓝牙耳机 | 2000 | 20/pg | ¥2.6-29.8 | Real CN earphone offers |
| 智能手表 | TBD | TBD | TBD | Tested, works |
| 充电宝 | TBD | TBD | TBD | Tested, works |

### Fields Returned Per Offer

- `offerId` — unique product ID
- `title` — Chinese title (with HTML highlight tags stripped)
- `priceInfo.price` — CNY price
- `shop.loginIdOfUtf8` — Chinese shop name (URL-encoded UTF-8, decode with urllib)
- `province` / `city` — supplier location (e.g. 广东/深圳市)
- `bizType` — business type (生产加工 / 经销批发)
- `factoryInspection: true` — Alibaba verified factory flag
- `isTp` — TP member (trusted supplier) flag
- `bookedCount` — 30-day booking count (sales signal)
- `offerRepurchaseRate` — repurchase rate %
- `offerPicUrl` — main image (cbu01.alicdn.com)
- `linkUrl` — detail page (sometimes 1688, sometimes P4P ad URL)

### Known Limitations

- **Search only.** Detail endpoint (`mtop.1688.laputa.miniod`) hits BaXia TMD
  challenge for anonymous sessions → need a real browser `_m_h5_tk` cookie
  for deep SKU/media fetches. Workaround: use search metadata + existing
  Decodo SU detail scraper.
- **English queries return 0 items** even when "found > 0". MTOP is
  Chinese-only. Use Chinese keywords (translate PT → ZH via dict).
- **No login required** for search, but no user account features (no order
  tracking, no chat). Just discovery + pricing + supplier info.

### How to Use

```bash
# Clone SDK once
git clone https://github.com/QuoVadis86/ai-reverse /tmp/scrapers-test/ai-reverse
cd /tmp/scrapers-test/ai-reverse && python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

# Run our wrapper
cd /mnt/ssd/1688-only/scripts
PYTHONPATH=/tmp/scrapers-test/ai-reverse/1688 python3 scrape_1688_mtop.py \
  "K15 无线麦克风" --pages 3 --size 20 \
  --json /tmp/k15_results.json
```

Output: flat JSON list of 60 unique offers with all fields above.

### Cost Comparison

| Source | Cost | Search Works | Detail Works |
|--------|------|--------------|--------------|
| **MTOP (ai-reverse)** | FREE | ✅ | ⚠️ partial |
| Rakumart BR | FREE (BRL prices) | ✅ | ✅ |
| Decodo SU | ~$0.001/page | ❌ blocked | ✅ |
| Onebound 1688 API | ¥5K/yr (R$300/mo) | ✅ | ✅ |
| 1688 Official open.1688.com | Free if ISV | ✅ | ✅ (needs Chinese phone) |

**Recommendation:** MTOP for **search** (FREE, instant, bypasses BaXia).
Decodo SU for **detail enrichment** of selected offer IDs.

## 15. Decision Tree - What to Do Now (CORRECTED)

```
Q: Budget zero?
  YES -> Yiwugo test (30s, no creds) -> Parse.bot signup (1 min, 100 free/mo)
       -> Use what we have (470+ products) + 1688 Chrome Extension
  NO, willing to spend ~R$35/mo -> Dianleida (店雷达) for deep 1688 ranking
  NO, willing to spend ~R$300/mo -> Onebound 1688 API (¥5K/year)
  NO, has 1688 account + Chinese phone -> open.1688.com ISV (free, official)

Q: Need real-time best sellers?
  - Free: 1688 Chrome Extension (browsing) + what we have (470+ products)
  - Free API: Parse.bot (limited but real); ElimAPI REMOVED (phantom)
  - Paid: Onebound or Dianleida

Q: Just need discovery now?
  - Use our 470+ products dataset (already validated)
  - 13 trending verticals keep producing new IDs
  - 1688 Chrome Extension for manual exploration
```

**Recommended action TODAY (in order)**:
1. **Me**: Test Yiwugo (义乌购) with curl (30s, no creds) — if 1688 ecosystem works without BaXia, big win
2. **Diogo**: Sign up Parse.bot (1 min) if Yiwugo blocked — get 100 free credits/mo immediately
3. **Me**: Test Parse.bot with K15 mic offer ID — confirm data quality
4. **Either**: Install 1688 Chrome Extension locally for manual browsing
5. **Skip for now**: Onebound (R$300/mo), open.1688 (needs Chinese phone)

If Parse.bot or Yiwugo works, we add a 4th data source to our pipeline (currently: trending verticals + mobile BFS + detail scraper).

## 9.8 Data Architecture (Bronze/Silver/Gold)

Implemented 2026-06-17. Layers:

```
data/
├── bronze/                         raw snapshots (immutable)
│   ├── mtop/{date}_{query}_p{page}.json
│   ├── su_detail/{date}_{offer_id}.html
│   └── rakumart/{date}_{query}_{source}_p{page}.json
├── silver/                         1 file per entity (joined)
│   ├── offers/{offer_id}.json       129 files
│   ├── suppliers/{loginId}.json     90 files
│   └── categories/{slug}.json       4 files
└── gold/                           ranked, actionable
    ├── by_category/{slug}.json      top 20 per category
    ├── rankings/ranked_by_margin.json  129 offers ranked
    └── to_source/priority.json      4 actionable items
```

**Transformation scripts** (in `scripts/`):
- `bronze_to_silver.py` — raw → cleaned/joined
- `silver_to_gold.py` — silver → ranked

**Run order**:
```bash
python3 scripts/bronze_to_silver.py --migrate-legacy all
python3 scripts/silver_to_gold.py
```

See `data/README.md` for full schema. Lineage in `data/_manifest.json`.
