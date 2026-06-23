/usr/bin/bash: warning: setlocale: LC_ALL: cannot change locale (pt_BR.UTF-8)
/usr/bin/bash: warning: setlocale: LC_ALL: cannot change locale (pt_BR.UTF-8)
# 1688 Scraping Intelligence — Complete Strategy

**Last updated**: 2026-06-16
**Scope**: 1688.com product discovery, detail enrichment, BRL pricing
> **NEW SESSION?** Start with [`SESSION-HANDOVER.md`](SESSION-HANDOVER.md) (5 min).
> It has the file map, decision tree, scripts inventory, known issues, and open tasks.
> This STRATEGY doc is the deep dive — read it AFTER the handover.

---

**User**: Diogo Chubatsu (ImportaSimples) — BR ML seller, sources from China
**Stack**: Python 3.11, Node 20, Next.js, running on port 3001

**Related**:
- **README.md** (single source of truth for project state) — `1688-only/README.md`
- **Skill** `1688-mtop-search` (operational guide) — `~/.hermes/profiles/1688-intel/skills/data-acquisition/1688-mtop-search/SKILL.md`
- **Memory** (working state) — `~/.hermes/profiles/1688-intel/memories/MEMORY.md`

---

## TL;DR

1688 blocks 4 layers (BaXia): desktop search, desktop detail, mobile detail (partially), specific shop storefronts. **No single tool works for everything.** The strategy is a 3-stage pipeline combining:

1. **MTOP** (free SDK) → search 2000+ products per query
2. **Decodo SU + China geo** ($0.005/offer) → full detail page (SKU, 200 imgs, price ladder, supplier)
3. **Rakumart BR** (free) → BRL native, PT-BR titles in alibaba tab

Plus a **title-based cross-walk** because **3 different ID systems** are in play:
MTOP offerId (13-15 digits) ≠ Rakumart 1688 iid (12 digits) ≠ Rakumart alibaba IDs (13 digits, 1601...).

Total cost for 10 categories × 100 products = **$5** in Decodo detail enrichment.

---

## 1. Tools Inventory (verified 2026-06-16)

### Working tools (USE)

| Tool | Endpoint | Cost | Speed | What it does |
|------|----------|------|-------|--------------|
| **MTOP (ai-reverse SDK)** | h5api.m.1688.com/h5/mtop.* | FREE | 14 prod/s | Search by Chinese keyword. Returns offerId, title, price, shop, region, factory inspection, cover image. |
| **Decodo SU (Site Unblocker)** | unblock.decodo.com:60000 | ~$0.005/offer | 1 prod/3s | Full detail page (90-200KB). With `X-SU-Geo: China` header, bypasses BaXia on detail.1688.com + m.1688.com. |
| **Rakumart BR (1688 tab)** | rakumart.com.br | FREE | 5 prod/s | Search + BRL prices, raw Chinese title in `title_cn`. |
| **Rakumart BR (alibaba tab)** | rakumart.com.br | FREE | 5 prod/s | PT-BR translated titles, BRL, Alibaba catalog. |
| **Rakumart BR (taobao tab)** | rakumart.com.br | FREE | 5 prod/s | Taobao catalog, BRL. |
| **Decodo Mobile (4G)** | gate.decodo.com:10001 | TBD | TBD | Real 4G IP, returns US IPs. Useful for sites that detect datacenter. |
| **Decodo Residential** | gate.decodo.com:10001 | TBD | TBD | Real residential IP, random country. Can specify via username format. |
| **m.1688.com direct** (from cloud) | m.1688.com | FREE | 80% success | Mobile detail page. Works directly, no proxy needed ~80% of the time. |

### Dead/broken tools (DO NOT USE)

| Tool | Status | Why |
|------|--------|-----|
| Decodo SU U0000402799 (in .env) | ❌ 403 "User is disabled" | Account disabled by provider. |
| Decodo gate:10001 old creds (spvgqh3ebj) | ❌ 407 | Auth format changed. |
| Decodo ISP isp.decodo.com:10000 old format | ❌ 407 | Wrong format. Try sp2idylm9q at :10001. |
| Decodo Scraping API | ❌ Out of balance | Need top-up. |
| detail.1688.com direct (from cloud) | ❌ BaXia 4-layer | Blocked from cloud IPs. |
| s.1688.com search direct (from cloud) | ❌ Login redirect | Even via SU China, search needs login. |
| baiyite.1688.com (specific shop storefront) | ❌ BaXia protected | Even with CN IP via SU, shop-level BaXia. |
| alibaba.com EN storefront (from cloud) | ❌ BaXia | Blocked. |
| Yiwugo API | ❌ CSRF block | API requires browser session. |
| Parse.bot | ❌ Timeout 600s | Low value, signup friction. |
| ElimAPI | ❌ Phantom | Never existed. NXDOMAIN. |
| Chrome Extension 1688 | ❌ UI tool | For logged-in sellers, not programmatic. |
| English/PT queries on MTOP | ❌ Returns 0 items | MTOP is Chinese-only. |

### Future tools (PENDING)

| Tool | Status | Notes |
|------|--------|-------|
| Decodo ISP isp.decodo.com:10001 | Setup pending | Have creds sp2idylm9q. |
| Decodo MCP server | Setup pending | github.com/Decodo/mcp-server. Could automate. |
| Decodo Scraping API | Need top-up | Token in env. |
| Onebound 1688 API | ¥5K/yr (R$300/mo) | Last resort paid option. |

---

## 2. The 4-Phase Pipeline

### Phase 1: Discovery (MTOP — FREE)

```python
import sys
sys.path.insert(0, '/tmp/scrapers-test/ai-reverse/1688')
from client import Alibaba1688Client
from urllib.parse import unquote

client = Alibaba1688Client()
client.session.login()

# CN keyword — translate PT/EN to Chinese first
# drill → 电动螺丝刀 / socks → 袜子 / beach clip → 沙滩巾夹
all_results = []
for page in range(1, 4):  # 3 pages = 180 products
    r = client.search_by_text('沙滩巾夹', page=page, page_size=60)
    items = (r.data.get('data') or {}).get('OFFER', {}).get('items', [])
    for it in items:
        d = it.get('data', {})
        all_results.append({
            'offer_id': str(d.get('offerId') or ''),
            'title': unquote((d.get('title') or '').replace('<font color=red>','').replace('</font>','')),
            'price_cny': float(d.get('priceInfo',{}).get('price') or 0),
            'shop': unquote((d.get('shop') or {}).get('loginIdOfUtf8') or ''),
            'image_url': d.get('offerPicUrl', ''),
            'min_qty': int(d.get('beginAmount') or 1),
            'booked_count': int(d.get('bookedCount') or 0),
            'factory_inspected': d.get('factoryInspection') == 1,
            'province': d.get('province', ''),
            'city': d.get('city', ''),
        })
```

**MTOP limits**:
- 2000 products per query (cap)
- Returns "recommendation", not full search (endpoint is `mtop.relationrecommend.WirelessRecommend.recommend`)
- Chinese queries only (PT/EN returns 0)
- Top 100-200 are best quality; long tail may have inactive products

**Outputs**:
- `offer_id` (use for Phase 2 detail)
- `shop` (use for supplier filtering)
- `title` (use for Phase 4 cross-walk)
- `image_url` (use for sourcing decision)

### Phase 2: Detail Enrichment (Decodo SU + China geo — $0.005/offer)

```python
import urllib.request, ssl, re, time

ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

# SU with China geo (THE key header that makes it work)
proxy_handler = urllib.request.ProxyHandler({
    'http':  'http://U0000434457:***@unblock.decodo.com:60000',
    'https': 'http://U0000434457:***@unblock.decodo.com:60000',
})
opener = urllib.request.build_opener(proxy_handler, urllib.request.HTTPSHandler(context=ctx))

def fetch_detail(offer_id, geo='China', retries=2):
    for attempt in range(retries):
        try:
            url = f'https://detail.1688.com/offer/{offer_id}.html'
            req = urllib.request.Request(url, headers={
                'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15) AppleWebKit/537.36 Chrome/120'
            })
            req.add_header('X-SU-Geo', geo)
            req.add_header('X-SU-Locale', 'zh-cn')
            r = opener.open(req, timeout=30)
            body = r.read().decode(errors='ignore')
            if len(body) < 5000:
                raise Exception(f'Page too small ({len(body)}b) — likely blocked')
            return body
        except Exception as e:
            if attempt < retries - 1:
                time.sleep(3)
                continue
            return None

# CRITICAL: 3s delay between requests or 60% fail rate
for product in top_100_products:
    html = fetch_detail(product['offer_id'])
    if html:
        detail = parse_detail(html)
        save(detail)
    time.sleep(3)  # RATE LIMIT PROTECTION
```

**Detail.1688.com extracts**:
- `offerTitle` — Chinese product name
- `price` + `beginAmount` — wholesale price ladder
- `companyName` — full registered company (e.g., 台州市佰亿特塑业有限公司)
- `loginId` — shop name (e.g., `tzbaiyite`)
- `userId` — supplier memberId (use for winport)
- `skuProps` — color + size variants
- 200+ `cbu01.alicdn.com` images

**Geo options**:
- `X-SU-Geo: China` → CN IP (Jinan) — BEST for 1688
- `X-SU-Geo: HongKong` → HK IP — fallback for m.1688.com
- `X-SU-Geo: United States` → US IP (Los Angeles)

**When to skip Phase 2**:
- MTOP cover image is enough (cover image = first gallery image, often good enough)
- Cost-sensitive batch (Phase 2 = $0.005/offer × 1000 = $5)
- Time-sensitive (Phase 2 = 3s × 100 = 5min for 100 products)

### Phase 3: BRL Pricing (Rakumart BR — FREE)

```python
import sys
sys.path.insert(0, '/mnt/ssd/1688-intel/scripts/arbitlens')
from scrape_rakumart_br import search_rakumart_br

# Source options: '1688', 'alibaba', 'taobao'
# '1688' tab: has title_cn (raw Chinese) — best for cross-walk
# 'alibaba' tab: PT-BR translated titles (paraphrased, NOT direct)
# 'taobao' tab: PT-BR translated titles

results_1688 = search_rakumart_br('沙滩巾夹', source='1688', page=1)
# Returns: source_product_id (iid), product_name, price_low, price_high,
#          source_url, seller_name, raw_data (has title_cn, etc)

for r in results_1688:
    print(f'{r.source_product_id} | R${r.price_low}-{r.price_high} | {r.product_name[:50]}')
```

**Rakumart data quality**:
- 1688 tab: 50-150 products per query, raw Chinese title in `title_cn`
- alibaba tab: 50-150 products, PT-BR titles, different ID system
- taobao tab: 50-150 products, PT-BR titles

**When to use which tab**:
- Need cross-walk with MTOP → use 1688 tab (title_cn match)
- Need PT-BR display → use alibaba or taobao tab
- Best BRL coverage → use alibaba tab (largest catalog)

### Phase 4: Cross-walk (Title-based matching)

```python
# MTOP and Rakumart use DIFFERENT ID systems
# Cross-walk must use title similarity
from difflib import SequenceMatcher

def match_score(t1, t2):
    """Return 0-100 similarity score between two titles."""
    t1 = re.sub(r'[^\w]', '', t1.lower())
    t2 = re.sub(r'[^\w]', '', t2.lower())
    return round(SequenceMatcher(None, t1, t2).ratio() * 100, 1)

for mtop_product in mtop_results:
    for rak_product in rak_1688_results:  # MUST be 1688 tab for title_cn
        score = match_score(mtop_product['title'], rak_product.raw_data.get('title_cn', ''))
        if score > 60:
            print(f'MATCH {score}%: {mtop_product["offer_id"]} ↔ {rak_product.source_product_id}')
            print(f'  {mtop_product["title"][:50]}')
            print(f'  {rak_product.raw_data.get("title_cn", "")[:50]}')
            print(f'  BRL: R${rak_product.price_low}')
```

**Match thresholds** (empirical):
- 80%+ → same product, high confidence
- 60-80% → variant or similar, manual review
- 40-60% → same category, different product
- <40% → ignore

**Match rates observed**:
- K15 mics: 30/80 = 37.5% title overlap (MTOP side), 60% (Rakumart side)
- Beach clips: 24/92 = 26% overlap
- Socks: 2/120 = 1.7% (Rakumart had different catalog)
- Drill: 27/116 = 23% overlap

**To improve match rate**:
- Use Rakumart 1688 tab (has title_cn, not translated)
- Use SequenceMatcher on full title, not just keywords
- Strip HTML tags before matching
- Pre-filter by price range (±50%)

---

## 3. The 3 ID Systems (cross-walk challenge)

| System | Field | Length | Example | Found in |
|--------|-------|--------|---------|----------|
| **MTOP** | `offer_id` | 13-15 digits | `950187251807` | Phase 1 output |
| **Rakumart 1688 tab** | `iid` (source_product_id) | 12 digits | `758926082915` | Phase 3 output |
| **Rakumart alibaba tab** | (different field) | 13 digits, starts 1601 | `1601382618099` | Phase 3 output |
| **Rakumart taobao tab** | (different field) | 13 digits, varies | varies | Phase 3 output |

**Implication**: Same product from 1688 can have 3+ different IDs across the systems.
Cross-walk MUST be title-based, never ID-based.

**Rakumart `raw_data` fields** (1688 tab):
- `title_cn` — raw Chinese title (MOST IMPORTANT for cross-walk)
- `goods_link` — Rakumart storefront URL
- `price` — Rakumart's BRL price (may differ from MTOP CNY after conversion)
- `image_url` — cover image

---

## 4. Per-Page Behavior Matrix (the 7 critical 1688 pages)

| Page | What it is | Direct (cloud) | SU CN | SU HK | Notes |
|------|-----------|----------------|-------|-------|-------|
| `s.1688.com/selloffer/offer_search.htm` | Desktop search | ❌ Login redirect | ❌ Login redirect | ❌ Login redirect | Need 1688 login. **Use MTOP instead.** |
| `detail.1688.com/offer/{ID}.html` | Desktop detail | ❌ BaXia TMD | ✅ 93KB | ⚠️ Untested | **PRIMARY detail source.** |
| `m.1688.com/offer/{ID}.html` | Mobile detail | ⚠️ 80% success | ✅ 178KB | ✅ 178KB | Mobile lighter BaXia. Good fallback. |
| `m.1688.com/winport/page/index.html?memberId=...` | Shop winport | ⚠️ Mixed | ✅ 120KB | ⚠️ Untested | Lists all products from a supplier. |
| `baiyite.1688.com` | Specific shop storefront | ❌ BaXia | ❌ BaXia | ❌ BaXia | Shop-level BaXia. **Cannot bypass.** |
| `s.1688.com/company/company_search.htm` | Company search | ❌ | ⚠️ Loads but empty | ⚠️ Loads but empty | No memberIds in HTML, needs JS rendering. |
| `s.1688.com/winport.htm` | Winport search | ❌ | ⚠️ Untested | ⚠️ Untested | Alternative shop discovery. |

**Direct m.1688.com success rate**: ~80% from cloud IPs. ~95%+ with SU HK. Use SU for safety.

**Mobile = lighter BaXia** because:
1. Mobile site uses simpler anti-bot (no advanced fingerprinting)
2. Many cloud IPs are tagged as "mobile" by default
3. 1688 prioritizes mobile traffic (less strict)

**Desktop search login requirement**:
- Even with valid 1688 cookie, bulk search gets throttled
- MTOP is the workaround (uses mobile API)

---

## 5. Anti-BaXia Tactics (the hard-won lessons)

### What BaXia blocks (4 layers)

1. **TLS fingerprinting** — Python requests/urllib gets flagged
2. **IP reputation** — datacenter IPs (AWS, GCP, DO) are flagged
3. **Header analysis** — missing/incorrect User-Agent, Accept-Language
4. **Cookie/session** — no valid 1688 session = blocked

### What works (and why)

| Method | Why it works |
|--------|--------------|
| **m.1688.com** (mobile) | Mobile site has lighter BaXia. From cloud IPs, ~80% work. With Decodo HK: 100%. |
| **MTOP h5api endpoint** | Same mobile API the 1688 app uses. No cookies, no browser. |
| **Decodo SU + China geo** | Real China residential IP, looks like a Chinese user. |
| **Decodo SU + HK geo** | HK is "close enough" to CN for 1688 mobile. |
| **Decodo Mobile (4G)** | Real 4G IP, not datacenter. |

### What DOESN'T work

| Method | Why it fails |
|--------|--------------|
| **detail.1688.com direct** | Layer 1+2 — TLS + IP. |
| **s.1688.com direct** | Login redirect, even via SU. |
| **baiyite.1688.com specific shop** | Shop-level BaXia, harder to bypass. |
| **English/PT in MTOP** | API is Chinese-only, EN returns 0. |
| **No delay between requests** | Rate limit triggers BaXia on SU. |

### Rate limit protocol

- **MTOP**: no rate limit (14/s is safe, can go faster)
- **Decodo SU**: 3s delay MIN between requests, or 60% fail
- **Rakumart**: no rate limit observed
- **Direct 1688**: don't even try, BaXia wins

### Header cheat sheet

```python
# Mobile MTOP (search)
{'User-Agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 16_0) AppleWebKit/605.1.15'}

# Desktop detail via SU (most common)
{'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15) AppleWebKit/537.36 Chrome/120'}

# Mobile detail via SU
{'User-Agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 16_0) AppleWebKit/605.1.15'}

# Rakumart (no special headers needed)
{'User-Agent': 'python-requests/2.31'}  # default works
```

---

## 6. MTOP SDK Methods (not all in main pipeline)

The ai-reverse SDK has more methods than just `search_by_text`:

| Method | What it does | Tested? | Use case |
|--------|--------------|---------|----------|
| `search_by_text(query, page, size, sort_type)` | Search products | ✅ | Phase 1 |
| `get_offer_detail(offer_id)` | Get single product detail | ⚠️ Returns BaXia | Try with cookies |
| `get_offer_detail_from_html(url)` | Parse from URL | ⚠️ Untested | Could be useful for baiyite.1688.com via SU |
| `get_offer_recommendations(offer_id)` | Related products for a given offer | ✅ | **"Is this product alive?" check.** Returns 0 = delisted. |
| `get_shop_card(memberId)` | Shop basic info | ❌ Not tested | Use after Phase 2 to get shop badges. |
| `get_shop_certification(memberId)` | Shop verification | ❌ Not tested | Use to verify suppliers. |
| `search_by_image(image_url)` | Image search | ⚠️ Untested | Could find similar products to a user-uploaded image. |
| `search_similar_by_image(image_url)` | Similar to given image | ⚠️ Untested | Same as above. |
| `get_image_search_urls(offer_id)` | Get image URLs from search | ❌ Not tested | Could replace image extraction. |

**"Is this product alive?" check**:
```python
r = client.get_offer_recommendations('863290574424')
# If r.success and len(recommendations) > 0 → product is LIVE
# If r.success but empty → product is likely DELISTED
# If not r.success → MTOP error, retry

# Also: detail page size check
body = fetch_detail('863290574424')
if body and len(body) > 50000:  # >50KB = full page
    print("LIVE")
else:
    print("DELISTED OR BLOCKED")
```

---

## 7. Supplier Discovery Pattern (generic — baiyite was just the example)

**IMPORTANT**: baiyite (tzbaiyite) was used as the FIRST case study to validate the
strategy. The pattern below is generic and works for ANY supplier on 1688.

The pattern: `keyword search → filter by shop name → iterate queries → enrich → cross-walk`.

### Generic template (works for any supplier)

```python
def find_supplier_line(supplier_shop_name, supplier_queries, max_pages=3, page_size=60):
    """
    Find all products from a specific supplier on 1688.
    
    Args:
        supplier_shop_name: e.g., 'tzbaiyite' (the 1688 loginId, NOT the company name)
        supplier_queries: list of CN keywords the supplier likely uses
        max_pages: pages to iterate per query (3 = 180 products/query)
        page_size: 60 is MTOP default
    
    Returns: list of unique products from this supplier
    """
    results = {}  # dedup by offer_id
    
    for query in supplier_queries:
        for page in range(1, max_pages + 1):
            r = client.search_by_text(query, page=page, page_size=page_size)
            if not r.success:
                continue
            items = (r.data.get('data') or {}).get('OFFER', {}).get('items', [])
            for it in items:
                d = it.get('data', {})
                shop = unquote((d.get('shop') or {}).get('loginIdOfUtf8') or '')
                if shop == supplier_shop_name:
                    oid = str(d.get('offerId') or '')
                    if oid not in results:
                        results[oid] = {
                            'offer_id': oid,
                            'title': unquote((d.get('title') or '').replace('<font color=red>','').replace('</font>','')),
                            'price_cny': float(d.get('priceInfo',{}).get('price') or 0),
                            'shop': shop,
                            'image_url': d.get('offerPicUrl', ''),
                            'min_qty': int(d.get('beginAmount') or 1),
                            'booked_count': int(d.get('bookedCount') or 0),
                            'province': d.get('province', ''),
                            'city': d.get('city', ''),
                        }
            time.sleep(0.3)  # respect rate
    
    return list(results.values())


# Example 1: baiyite (beach clips)
baiyite_line = find_supplier_line(
    supplier_shop_name='tzbaiyite',
    supplier_queries=['沙滩巾夹', '沙滩夹', '沙滩毛巾夹', '沙滩地插夹',
                      '沙滩夹子', '沙滩帐篷夹', '塑料沙滩夹', '沙滩防风夹'],
)
# Result: 15 baiyite products

# Example 2: any other supplier (you only need the 1688 shop name)
# First, find the shop name by searching and picking from results
r = client.search_by_text('meias', page=1)
for it in r.data.get('data', {}).get('OFFER', {}).get('items', [])[:20]:
    shop = unquote((it.get('data', {}).get('shop') or {}).get('loginIdOfUtf8') or '')
    print(f'{shop}: {it.get("data", {}).get("title", "")[:50]}')

# Once you have a shop name, plug it in
socks_supplier_line = find_supplier_line(
    supplier_shop_name='that_shop_name',
    supplier_queries=['袜子', '短袜', '船袜'],
)
```

### How to find a supplier's 1688 shop name (the discovery step)

```python
# Method A: User gives you a name (e.g., "baiyite", "youyazi")
# → search MTOP for that name in CN transliteration
# baiyite → try 百亿特, 白亿特, tzbaiyite, 佰亿特
# youyazi → try 尤雅姿, 尤雅姿内衣厂
# Inspect the shop field in results to find the right 1688 loginId

# Method B: User gives you a 1688 URL
# https://baiyite.1688.com → loginId is "baiyite" or "tzbaiyite"
# https://detail.1688.com/offer/123.html → fetch detail via SU, get loginId

# Method C: User gives you an Alibaba EN URL
# https://baiyite.en.alibaba.com → search for "baiyite" on 1688 search,
# filter results to find which 1688 shop matches

# Method D: User wants "top suppliers for X category"
# Search MTOP, group results by shop, count products per shop
from collections import Counter
shop_counter = Counter()
r = client.search_by_text('沙滩巾夹', page=1, page_size=60)
for it in r.data.get('data', {}).get('OFFER', {}).get('items', []):
    shop = unquote((it.get('data', {}).get('shop') or {}).get('loginIdOfUtf8') or '')
    shop_counter[shop] += 1

top_shops = shop_counter.most_common(20)
# Returns: [('tzbaiyite', 5), ('some_other_shop', 4), ...]
```

### To get a supplier's 1688 userId (for winport)

- From any MTOP result: `shop.userId` field
- From SU detail page: `userId` in JSON
- Once you have userId, winport works via SU CN geo

### Suppliers found so far (just case studies)

- `tzbaiyite` (台州市佰亿特塑业有限公司) — 15 beach clip products ← baiyite case study
- `尤雅姿内衣厂` (汕头市潮阳区谷饶尤雅姿内衣厂) — shapewear (NOT baiyite, user mistake)
- Top 20 shops per category are in the data files

### Discovered shop name pattern (baiyite CN transliteration)

- The actual MTOP shop is `tzbaiyite`, NOT `百亿特` or `白亿特`
- 1688 shop names are Latin transliterations, often abbreviated
- "tz" prefix likely means "台州" (Taizhou) — a common abbreviation
- The pattern: `city_abbreviation + brand_name` or `brand_name + city_abbreviation`

### Why baiyite was the case study

1. User explicitly mentioned baiyite as a reference
2. Beach clip category was in the user's test set
3. Supplier is small/private (good test for "long tail" MTOP coverage)
4. Result: 15 products found, fully enrichable, supplier identified
5. Validates the pattern: small supplier × broad queries = complete coverage

The same pattern will work for ANY supplier name the user provides.

---

## 8. Categorization Findings (PT → CN translation)

The 3 categories tested, with PT-BR → CN keywords:

| Category | PT-BR query | CN queries to try | MTOP count | Price range (CNY) |
|----------|-------------|-------------------|------------|-------------------|
| Drill/driver | furadeira parafusadeira | 电动螺丝刀, 电钻, 充电式电钻 | 60 | ¥0-9500 |
| Socks | meias | 袜子, 船袜, 短袜, 棉袜 | 42-120 | ¥0-34 |
| Beach clip | clip toalha praia | 沙滩巾夹, 沙滩夹, 沙滩毛巾夹, 沙滩地插夹, 沙滩夹子, 沙滩帐篷夹, 塑料沙滩夹, 沙滩防风夹 | 44-181 | ¥0-50 |
| Shapewear (mistake) | calcinha modeladora | 收腹裤, 塑身裤, 产后收腹 | 80+ | ¥4-10 |

**Translation tips**:
- Use 1688's own CN keywords (look at top products in category to learn them)
- Try synonyms (clip = 夹, 夹子, 扣, 卡子)
- Plural vs singular doesn't matter in CN
- Specific modifiers matter (塑料 = plastic, 金属 = metal, 防风 = wind-proof)

**Best beach clip query** (most results, best quality):
1. `沙滩巾夹` — 44 products, narrow
2. `沙滩夹` — 200+ products, broad
3. `沙滩毛巾夹` — 100+ products, medium
4. `沙滩地插夹` — 50+ products, ground-stake clips specifically

**Why broader queries miss niche**:
- `沙滩夹` returns random "clip" products (pin, paper clip, etc.)
- `沙滩巾夹` filters to towel-specific clips
- Use both broad + narrow to get full picture

---

## 9. Cost Structure

### Per-product cost

| Operation | Cost | When needed |
|-----------|------|-------------|
| MTOP search | FREE | Always (Phase 1) |
| Decodo SU detail | $0.005 | When you need SKU/images/supplier full data |
| Rakumart BR BRL | FREE | Always (Phase 3) |
| Cross-walk | FREE | Always (Phase 4) |
| m.1688.com direct | FREE | When SU fails or budget tight |

### Per-category cost (100 products)

| Scenario | Cost |
|----------|------|
| Discovery only (Phase 1) | FREE |
| Discovery + BRL (Phase 1+3) | FREE |
| Discovery + Detail (Phase 1+2) | $0.50 |
| Full pipeline (all 4 phases) | $0.50 |
| Full pipeline × 10 categories | **$5.00** |

### Time per category (100 products)

| Phase | Time |
|-------|------|
| MTOP search (3 pages × 60) | ~25s |
| Decodo detail (with 3s delay) | ~5min |
| Rakumart search (3 tabs) | ~30s |
| Cross-walk (in-memory) | <1s |
| **Total** | **~6 min/category** |

### Time per product (Phase 2 only)

- 1 detail page = 3s (with delay) = 20 details/min
- 100 details = 5 min
- 1000 details = 50 min
- 10000 details = 8.3 hours (limit for 1-day batch)

---

## 10. Known Limitations

### Hard limits (cannot be solved today)

1. **Desktop search (s.1688.com) requires login** — no way around it for bulk search
2. **MTOP caps at 2000/q** — products past page 33 (with size=60) are inaccessible
3. **MTOP is recommendation engine** — 95%+ of 1688 catalog is in the long tail
4. **Cross-walk is title-based, not ID-based** — 3 different ID systems in play
5. **English/PT in MTOP returns 0** — must translate to Chinese first
6. **No real-time inventory** — products can delist between MTOP and detail fetch
7. **Decodo SU = $0.005/offer** — at scale (10K products) = $50, not free
8. **No image-based matching in production** — MTOP has `search_by_image` but unstable
9. **Supplier storefronts (baiyite.1688.com) are BaXia protected** — can only get products via MTOP search
10. **Detail page 60% fail without delay** — 3s delay is mandatory, not optional
11. **Alibaba tab titles are paraphrased** — direct cross-walk with MTOP is 0% (use 1688 tab instead)
12. **3 different Rakumart tabs = 3 different ID systems** — no unified view

### Soft limits (workable with effort)

- **Bulk enrichment** — 3s × 100 = 5min, 3s × 1000 = 50min, 3s × 10000 = 8.3 hours
- **Cross-walk accuracy** — could be improved with embedding similarity (CLIP), but that's overkill
- **Multiple suppliers per product** — would need title-based supplier matching

### Things I tried that didn't work

- ❌ `get_offer_recommendations(863290574424)` — returned 0 (delisted product)
- ❌ `search_by_image` via MTOP — unstable, not in pipeline
- ❌ `search_similar_by_image` via MTOP — same
- ❌ Direct m.1688.com from cloud IP — 80% hit rate, use Decodo for 100%
- ❌ Parsing baiyite.1688.com via SU CN — BaXia protected at shop level
- ❌ Decodo scraper API — out of balance
- ❌ Cross-walk MTOP titles to Rakumart alibaba tab — 0% match (paraphrased PT)

---

## 11. Future Work (when time/money available)

### Short term (1-2 weeks)

- [ ] **Test Decodo ISP isp.decodo.com:10001** — may have CN geo that we don't have
- [ ] **Top up Decodo Scraping API** — could simplify detail enrichment
- [ ] **Test Decodo Mobile (4G) for 1688** — 4G IPs may be best for BaXia bypass
- [ ] **Complete baiyite line** — enrich remaining 10 products
- [ ] **Cross-walk the 15 baiyite products with Rakumart** — get BRL for baiyite line
- [ ] **Run pipeline on 10+ categories** — build the catalog
- [ ] **Test `get_shop_card` and `get_shop_certification`** — supplier verification
- [ ] **Test `get_image_search_urls`** — replace image extraction

### Medium term (1 month)

- [ ] **Set up Decodo MCP server** — could automate the whole pipeline
- [ ] **Build a Next.js dashboard** — show search results with multi-source prices
- [ ] **Add CLIP image matching** — only if user explicitly asks for it
- [ ] **Cache Decodo detail pages** — avoid re-fetching same product
- [ ] **Build supplier reputation system** — booked count + factory inspection

### Long term (3+ months)

- [ ] **Onebound API as backup** — when Decodo fails, fallback to paid
- [ ] **Auto-translate MTOP titles to PT** — using user-friendly translation
- [ ] **Track price changes over time** — historical pricing for trend analysis
- [ ] **Multi-supplier product matching** — find which suppliers sell similar products

### NOT building (per principles)

- Automated product matching (user decides)
- Confidence scoring (misleading without real data)
- Feedback systems (need real users first)
- Demo pages (waste of time)
- Image-first matching (blocked cross-API)

---

## 12. Quick Reference: What to use when

| User asks | Action |
|-----------|--------|
| "Find me suppliers for X" | MTOP search, list unique shops |
| "What's the BRL price for product X" | Rakumart search, return R$ range |
| "Give me the full detail for offer 123" | Decodo SU China + detail.1688.com |
| "Is this product still live?" | Decodo SU China + check page size >50KB |
| "What does supplier X sell?" | MTOP search + filter by `shop == X` |
| "Show me all products from supplier X" | Iterate MTOP queries, filter by shop |
| "Match products across marketplaces" | Phase 4 cross-walk (title similarity) |
| "Get SKU/media for a product" | Phase 2 detail (with 3s delay) |
| "Show me baiyite's products" | Filter MTOP by `shop == "tzbaiyite"` |
| "Find similar to this image" | MTOP `search_similar_by_image` (unstable) |
| "Find products from a specific shop" | 1688 winport via SU CN (need userId) |

---

## 13. File Inventory (in this repo)

| File | Purpose |
|------|---------|
| `scripts/scrape_1688_mtop.py` | MTOP CLI wrapper |
| `scripts/validate_mtop.py` | MTOP validation (overlap with Rakumart) |
| `scripts/test_3_categories.py` | Drill/socks/beach clip MTOP test |
| `scripts/strategy_matrix.py` | Cross-source matrix (4 sources × 3 categories) |
| `data/mtop_k15_full.json` | 80 K15 mic products via MTOP |
| `data/mtop_3category_test.json` | 3-category test results |
| `data/mtop_validation_report.json` | Full validation report (this doc's source) |
| `data/baiyite_line.json` | 15 baiyite beach clip products (MTOP) |
| `data/baiyite_line_enriched.json` | 5 baiyite products with SU detail data |
| `docs/STRATEGY-1688-SCRAPING-INTEL.md` | This document |

---

## 14. Decision Flowchart

```
START: User wants product info from 1688
  │
  ├─ Has offerId? ──YES──> Phase 2 (Decodo SU detail) directly
  │                         │
  │                         ├─ Page > 50KB? ──YES──> LIVE
  │                         │                          │
  │                         │                          ├─ Need BRL? ──YES──> Phase 3 (Rakumart search by title)
  │                         │                          └─ No  ─────────────> DONE (have detail)
  │                         │
  │                         └─ Page < 5KB? ──YES──> DELISTED or BLOCKED
  │                                                       │
  │                                                       └─ Use MTOP `get_offer_recommendations` to find similar
  │
  └─ No offerId (search by keyword) ──> Phase 1 (MTOP search)
                                          │
                                          ├─ Need top suppliers? ──YES──> Filter by shop, group, sort by booked
                                          │
                                          ├─ Need full detail? ──YES──> Phase 2 (top 5-10)
                                          │                                 │
                                          │                                 └─ 3s delay between
                                          │
                                          ├─ Need BRL? ──YES──> Phase 3 (Rakumart search, all 3 tabs)
                                          │
                                          └─ Need cross-source? ──YES──> Phase 4 (title match)
                                                                              │
                                                                              └─ Score > 60% = match
                                                                              └─ Score 40-60% = manual review
```

---

## 15. The Creds (in .env + new)

```
# WORKING - use these
DECODO_SU_USER=U0000434457
DECODO_SU_PASS=PW_17560792063f932882c0843ad92c0ed69
DECODO_SU_HOST=unblock.decodo.com
DECODO_SU_PORT=60000

DECODO_MOBILE_USER=spraglxgvk
DECODO_MOBILE_PASS=Vd6qj0tqxk4B5Qg+dT
DECODO_MOBILE_HOST=gate.decodo.com
DECODO_MOBILE_PORT=10001

DECODO_RESIDENTIAL_USER=span5nxws5
DECODO_RESIDENTIAL_PASS=N_cCzf3txm12cn5HNj
DECODO_RESIDENTIAL_HOST=gate.decodo.com
DECODO_RESIDENTIAL_PORT=10001

DECODO_ISP_USER=sp2idylm9q
DECODO_ISP_PASS=J41Ytm9rgWofr=V2nr
DECODO_ISP_HOST=isp.decodo.com
DECODO_ISP_PORT=10001

# DEAD - do not use
# DECODO_SU_USER_OLD=U0000402799  # 403 disabled
# DECODO_RESIDENTIAL_OLD=spvgqh3ebj  # 407 dead

# OUT OF BALANCE - top up needed
DECODO_SCRAPING_API_KEY=VTAwMD...

# MCP - setup pending
DECODO_MCP_USER=U0000432181
DECODO_MCP_PASS=PW_18394bac315ef747efe9aa6179cc9e429
```
