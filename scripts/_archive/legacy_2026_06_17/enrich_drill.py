import json, time, urllib.request, ssl, re, sys

ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

SU_PASS = 'PW_17560792063f932882c0843ad92c0ed69'
SU_USER = 'U0000434457'
proxy_url = f'http://{SU_USER}:{SU_PASS}@unblock.decodo.com:60000'
opener = urllib.request.build_opener(
    urllib.request.ProxyHandler({'http': proxy_url, 'https': proxy_url}),
    urllib.request.HTTPSHandler(context=ctx)
)

with open('/mnt/ssd/1688-only/data/drill_top15.json') as f:
    d = json.load(f)
products = d['top15']
print(f'Starting drill enrichment ({len(products)} products)...', flush=True)
enriched = []
for i, p in enumerate(products, 1):
    offer_id = p['offer_id']
    url = f'https://detail.1688.com/offer/{offer_id}.html'
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'})
        req.add_header('X-SU-Geo', 'China')
        req.add_header('X-SU-Locale', 'zh-cn')
        r = opener.open(req, timeout=30)
        body = r.read().decode(errors='ignore')
        size = len(body)
        title = re.search(r'"subject"\s*:\s*"([^"]{5,200})"', body)
        company = re.search(r'"companyName"\s*:\s*"([^"]{2,100})"', body)
        if size > 10000:
            p['enriched_detail'] = {
                'size_bytes': size,
                'subject': title.group(1) if title else None,
                'company': company.group(1) if company else None,
                'is_live': True,
            }
            enriched.append(p)
            print(f'  [{i}/{len(products)}] {offer_id} | {size}b OK', flush=True)
        else:
            p['enriched_detail'] = {'size_bytes': size, 'is_live': False}
            print(f'  [{i}/{len(products)}] {offer_id} | {size}b BLOCKED', flush=True)
    except Exception as e:
        p['enriched_detail'] = {'error': str(e)[:50], 'is_live': False}
        print(f'  [{i}/{len(products)}] {offer_id} | ERR {e}', flush=True)
    time.sleep(3)

with open('/mnt/ssd/1688-only/data/drill_top15_enriched.json', 'w', encoding='utf-8') as f:
    json.dump({'category': d['category'], 'enriched_count': len(enriched), 'products': products}, f, ensure_ascii=False, indent=2)
print(f'Done: {len(enriched)}/{len(products)}', flush=True)
