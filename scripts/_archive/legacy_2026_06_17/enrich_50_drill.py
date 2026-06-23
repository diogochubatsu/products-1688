import json, time, urllib.request, ssl, re

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

with open('/mnt/ssd/1688-only/data/drill_top50.json') as f:
    top50 = json.load(f)['top50']
with open('/mnt/ssd/1688-only/data/drill_top15_enriched.json') as f:
    t15 = json.load(f)
t15_ids = set(p['offer_id'] for p in t15['products'])
print(f'DRILL top 50: {len(top50)}, already enriched: {len(t15_ids)}', flush=True)

new = [p for p in top50 if p['offer_id'] not in t15_ids]
print(f'New to enrich: {len(new)}', flush=True)

for i, p in enumerate(new, 1):
    offer_id = p['offer_id']
    url = f'https://detail.1688.com/offer/{offer_id}.html'
    for attempt in range(2):
        try:
            req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'})
            req.add_header('X-SU-Geo', 'China')
            req.add_header('X-SU-Locale', 'zh-cn')
            r = opener.open(req, timeout=60)
            body = r.read().decode(errors='ignore')
            size = len(body)
            if size > 10000:
                title = re.search(r'"subject"\s*:\s*"([^"]{5,200})"', body)
                company = re.search(r'"companyName"\s*:\s*"([^"]{2,100})"', body)
                p['enriched_detail'] = {
                    'size_bytes': size,
                    'subject': title.group(1) if title else None,
                    'company': company.group(1) if company else None,
                    'is_live': True,
                }
                print(f'  [{i}/{len(new)}] {offer_id} | {size}b OK', flush=True)
                break
            else:
                p['enriched_detail'] = {'size_bytes': size, 'is_live': False}
                print(f'  [{i}/{len(new)}] {offer_id} | {size}b BLOCKED', flush=True)
                break
        except Exception as e:
            print(f'  [{i}/{len(new)}] {offer_id} | ERR {e} (attempt {attempt+1})', flush=True)
            if attempt == 0:
                time.sleep(5)
    time.sleep(3)

all_products = t15['products'] + new
with open('/mnt/ssd/1688-only/data/drill_top50_enriched.json', 'w', encoding='utf-8') as f:
    json.dump({'category': t15['category'], 'enriched_count': len(new), 'products': all_products}, f, ensure_ascii=False, indent=2)
n = sum(1 for p in all_products if p.get('enriched_detail', {}).get('is_live'))
print(f'Done. Total: {n}/{len(all_products)} enriched', flush=True)
