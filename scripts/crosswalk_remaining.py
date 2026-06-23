#!/usr/bin/env python3
"""
crosswalk_remaining.py — Cross-walk silver offers that don't have a Rakumart match.

Improved with CN->PT translation via cn_pt_dict for better match rates.

Usage:
  python3 scripts/crosswalk_remaining.py [--limit N] [--threshold 40]
"""
import argparse
import json
import re
import sys
import time
from pathlib import Path
from difflib import SequenceMatcher
from urllib.parse import quote
from urllib.request import Request, urlopen

DATA = Path(__file__).parent.parent / 'data'
SILVER = DATA / 'silver' / 'offers'

# CN->PT translation
sys.path.insert(0, '/mnt/ssd/1688-intel/scripts/arbitlens')
from cn_pt_dict import cn_to_pt


def search_rakumart_br(query: str, source: str = '1688'):
    """Search Rakumart BR via their JSON API (form-encoded body)."""
    url = 'https://api.rakumart.com.br/index.php?mod=inc&act=ordersysPc&str=searchGoods'
    body = f'q={quote(query)}&type={source}&filter=&sort=&priceStart=&priceEnd=&snId=&page=1'.encode()
    headers = {
        'User-Agent': 'Mozilla/5.0',
        'Content-Type': 'application/x-www-form-urlencoded',
        'Origin': 'https://www.rakumart.com.br',
        'Referer': 'https://www.rakumart.com.br/commoditysearch',
    }
    try:
        req = Request(url, data=body, headers=headers)
        with urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read().decode('utf-8', errors='ignore'))
    except Exception as e:
        return []
    items = data.get('data', {}).get('content', [])
    out = []
    for item in items:
        title = item.get('title', '')[:200]
        price = item.get('price')
        if isinstance(price, str):
            nums = re.findall(r'[\d.]+', price)
            price = float(nums[0]) if nums else None
        if not price:
            continue
        iid = str(item.get('iid', ''))
        goods_link = item.get('goods_link', '')
        product_url = goods_link or f'https://www.rakumart.com.br/product/{iid}'
        out.append({
            'title': title,
            'price_brl': price,
            'url': product_url,
            'iid': iid,
        })
    return out


def crosswalk_title(cn_title: str, rakumart_items: list) -> tuple:
    """Find best Rakumart match for a CN title.

    Scoring (max 100):
      - PT keyword overlap (substring match, max 60)
      - SequenceMatcher on cleaned PT titles (max 30)
      - Title length sanity (max 10)
    """
    from difflib import SequenceMatcher

    # Translate CN to PT
    pt_title_raw = cn_to_pt(cn_title)

    # Extract ONLY latin PT keywords (filter out CN chars)
    pt_keywords = []
    for w in re.split(r'[^a-zA-Zà-ú]+', pt_title_raw.lower()):
        if len(w) >= 3 and w not in {'para', 'com', 'sem', 'casa', 'roupa', 'ideal'}:
            pt_keywords.append(w)
    pt_keywords = list(set(pt_keywords))  # dedupe

    best_score = 0
    best_match = None

    for item in rakumart_items:
        item_title_lower = item['title'].lower()

        # Strategy 1: PT keyword overlap (substring match, max 60)
        if pt_keywords:
            hits = sum(1 for kw in pt_keywords if kw in item_title_lower)
            keyword_score = (hits / len(pt_keywords)) * 60
        else:
            keyword_score = 0

        # Strategy 2: SequenceMatcher (max 30) — clean PT only
        pt_clean = ' '.join(pt_keywords) if pt_keywords else pt_title_raw.lower()
        sm = SequenceMatcher(None, pt_clean[:100], item_title_lower[:100])
        seq_score = sm.ratio() * 30

        # Strategy 3: Title length sanity (max 10)
        len_min = min(len(cn_title), len(item['title']))
        len_max = max(len(cn_title), len(item['title']))
        len_ratio = len_min / len_max if len_max > 0 else 0
        length_score = len_ratio * 10

        score = keyword_score + seq_score + length_score

        if score > best_score:
            best_score = score
            best_match = item

    return best_match, round(best_score, 1)



def build_queries(cn_title: str) -> list:
    """Build queries optimized for Rakumart (titles are PT-translated server-side)."""
    queries = []

    # Strategy 1: Full CN title (Rakumart auto-translates)
    queries.append(cn_title[:50])

    # Strategy 2: PT translation of full title (if has good coverage)
    pt_full = cn_to_pt(cn_title)
    if pt_full and pt_full != cn_title:
        queries.append(pt_full[:60])

    # Strategy 3: First 1-2 CN words
    cn_words = re.findall(r'[一-鿿]+', cn_title)
    if cn_words:
        queries.append(cn_words[0])
        if len(cn_words) > 1:
            queries.append(' '.join(cn_words[:2]))

    return queries



def main():
    p = argparse.ArgumentParser()
    p.add_argument('--limit', type=int, default=0, help='Limit N offers (0=all)')
    p.add_argument('--threshold', type=float, default=40, help='Min match score (0-100)')
    p.add_argument('--category', help='Only cross-walk this category')
    p.add_argument('--source', choices=['1688', 'alibaba', 'taobao'], default='alibaba',
                   help='Rakumart source to search (default=alibaba)')
    args = p.parse_args()

    offers = list(SILVER.glob('*.json'))
    need_crosswalk = []
    for f in offers:
        o = json.loads(f.read_text())
        if not o.get('rakumart'):
            if args.category and o.get('category') != args.category:
                continue
            need_crosswalk.append(f)

    if args.limit:
        need_crosswalk = need_crosswalk[:args.limit]

    print(f'Total offers needing cross-walk: {len(need_crosswalk)}')

    matched = 0
    failed = 0
    start_time = time.time()

    for i, f in enumerate(need_crosswalk):
        o = json.loads(f.read_text())
        cn_title = o.get('mtop', {}).get('title', '')
        if not cn_title:
            failed += 1
            continue

        queries = build_queries(cn_title)
        items = []
        for q in queries:
            items = search_rakumart_br(q, source=args.source)
            if items:
                break
            time.sleep(0.3)

        match, score = crosswalk_title(cn_title, items)

        if match and score >= args.threshold:
            o['rakumart'] = {
                'match_score': score,
                'price_brl': match['price_brl'],
                'title_br': match['title'],
                'url': match['url'],
                'crosswalked_at': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
            }
            f.write_text(json.dumps(o, ensure_ascii=False, indent=2), encoding='utf-8')
            matched += 1
        else:
            failed += 1

        if (i + 1) % 20 == 0:
            elapsed = time.time() - start_time
            rate = (i + 1) / elapsed if elapsed > 0 else 0
            eta = (len(need_crosswalk) - i - 1) / rate if rate > 0 else 0
            print(f'  [{i+1}/{len(need_crosswalk)}] matched={matched} failed={failed} '
                  f'rate={rate:.1f}/s ETA={eta:.0f}s')
        time.sleep(0.5)

    elapsed = time.time() - start_time
    print(f'\nFinal: matched={matched} failed={failed} (of {len(need_crosswalk)}) '
          f'in {elapsed:.1f}s ({len(need_crosswalk)/elapsed:.1f}/s)')


if __name__ == '__main__':
    main()