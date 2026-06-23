#!/usr/bin/env python3
"""
silver_to_gold.py — Transform silver offers into gold business-ready rankings.

Input:  silver/offers/*.json (one per offer)
        silver/categories/*.json (one per category)

Output:
  gold/by_category/{category}.json   top N per category, ranked by margin opportunity
  gold/rankings/ranked_by_margin.json  all offers ranked by margin%
  gold/to_source/{priority}.json       manually curated ML-ready lists

Margin calculation (without shipping cost - flag for future):
  CNY -> BRL: 1.07x (Rakumart markup observed)
  margin% = (price_brl - price_cny * 1.07) / price_brl * 100
  >0% = Rakumart price is HIGHER than source = opportunity to undercut
  <0% = Rakumart price is LOWER = Rakumart is competitive

NOTE: This is Naive Rakumart Margin, not real landed cost.
      Use with shipping cost module for production decisions.
"""

import json
import sys
from pathlib import Path
from datetime import datetime
import argparse

DATA_ROOT = Path(__file__).parent.parent / 'data'
SILVER = DATA_ROOT / 'silver'
GOLD = DATA_ROOT / 'gold'

# Approx CNY -> BRL market rate (real)
CNY_TO_BRL = 0.75  # June 2026 estimate


def calculate_margin(offer: dict) -> dict:
    """Calculate naive margin based on source CNY vs Rakumart BRL."""
    cny = offer.get('mtop', {}).get('price_cny') if offer.get('mtop') else None
    if isinstance(cny, str):
        try:
            cny = float(cny)
        except (ValueError, TypeError):
            cny = None
    brl = offer.get('rakumart', {}).get('price_brl') if offer.get('rakumart') else None
    if isinstance(brl, str):
        try:
            brl = float(brl)
        except (ValueError, TypeError):
            brl = None

    if not cny or not brl or brl <= 0:
        return {'naive_margin_brl': None, 'naive_margin_pct': None, 'opportunity': None}

    # Rakumart margin = how much MORE than source in BRL
    source_in_brl = cny * CNY_TO_BRL  # What it would cost to buy from CN
    rakumart_premium = brl - source_in_brl  # How much Rakumart charges over source
    naive_margin_pct = (rakumart_premium / brl) * 100 if brl > 0 else None

    # Opportunity scoring
    if naive_margin_pct and naive_margin_pct > 50:
        opportunity = 'HIGH'  # Rakumart markup is huge
    elif naive_margin_pct and naive_margin_pct > 20:
        opportunity = 'MEDIUM'
    elif naive_margin_pct and naive_margin_pct > 0:
        opportunity = 'LOW'
    else:
        opportunity = 'NONE'  # Rakumart price is at/below source

    return {
        'source_in_brl_est': round(source_in_brl, 2),
        'rakumart_premium_brl': round(rakumart_premium, 2),
        'naive_margin_pct': round(naive_margin_pct, 1) if naive_margin_pct else None,
        'opportunity': opportunity,
    }


def build_gold_rankings():
    """Build gold/rankings/ranked_by_margin.json — all offers ranked by margin."""
    offers = []
    for f in (SILVER / 'offers').glob('*.json'):
        o = json.loads(f.read_text())
        margins = calculate_margin(o)
        o['_margins'] = margins
        offers.append(o)

    # Rank by margin_pct descending (NULL last)
    offers_ranked = sorted(
        offers,
        key=lambda x: (x['_margins']['naive_margin_pct'] is not None, x['_margins']['naive_margin_pct'] or 0),
        reverse=True
    )

    # Build output
    out = {
        'generated_at': datetime.now().isoformat() + 'Z',
        'methodology': 'Naive Rakumart margin = (price_brl - cny*0.75) / price_brl. Does NOT include shipping, import tax, ML fees.',
        'total_offers': len(offers_ranked),
        'with_rakumart_match': sum(1 for o in offers_ranked if o.get('rakumart')),
        'rankings': []
    }

    for o in offers_ranked:
        _rk = o.get('rakumart') or {}
        _price_brl = _rk.get('price_brl')
        _match_score = _rk.get('match_score')
        _rakumart_url = (f"https://www.rakumart.com.br/product/{_rk.get('iid', '')}"
                         if _rk.get('iid') else _rk.get('url'))
        rank = {
            'rank': len(out['rankings']) + 1,
            'offer_id': o['offer_id'],
            'category': o['category'],
            'title': (o.get('mtop') or {}).get('title'),
            'shop': (o.get('mtop') or {}).get('shop'),
            'price_cny': (o.get('mtop') or {}).get('price_cny'),
            'price_brl_rakumart': _price_brl,
            'match_score': _match_score,
            'rakumart_url': _rakumart_url,
            'naive_margin_pct': (o.get('_margins') or {}).get('naive_margin_pct'),
            'opportunity': (o.get('_margins') or {}).get('opportunity'),
        }
        out['rankings'].append(rank)

    out_path = GOLD / 'rankings' / 'ranked_by_margin.json'
    out_path.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding='utf-8')
    print(f'Wrote {out_path} ({len(out["rankings"])} offers ranked)')

    # Summary stats
    high = sum(1 for r in out['rankings'] if r['opportunity'] == 'HIGH')
    medium = sum(1 for r in out['rankings'] if r['opportunity'] == 'MEDIUM')
    low = sum(1 for r in out['rankings'] if r['opportunity'] == 'LOW')
    none_op = sum(1 for r in out['rankings'] if r['opportunity'] == 'NONE')
    print(f'  HIGH opportunity: {high}')
    print(f'  MEDIUM opportunity: {medium}')
    print(f'  LOW opportunity: {low}')
    print(f'  NO opportunity (Rakumart competitive): {none_op}')


def build_gold_by_category():
    """Build gold/by_category/{category}.json — top N per category."""
    for cat_file in (SILVER / 'categories').glob('*.json'):
        cat = json.loads(cat_file.read_text())
        slug = cat['category_slug']
        offers = []
        for oid in cat['offer_ids']:
            o_path = SILVER / 'offers' / f'{oid}.json'
            if o_path.exists():
                o = json.loads(o_path.read_text())
                o['_margins'] = calculate_margin(o)
                offers.append(o)

        # Sort by margin opportunity (high first), then by booked count
        offers_sorted = sorted(offers, key=lambda x: (
            -({'HIGH': 3, 'MEDIUM': 2, 'LOW': 1, 'NONE': 0}.get(x['_margins']['opportunity'], 0)),
            -(int(x.get('mtop', {}).get('booked') or 0))
        ))

        # Top 20 per category for gold
        top = offers_sorted[:20]

        out = {
            'category': slug,
            'case_type': cat.get('case_type', 'CATEGORY'),
            'generated_at': datetime.now().isoformat() + 'Z',
            'methodology': 'Ranked by opportunity (HIGH>MEDIUM>LOW>NONE), then by booked count',
            'total_in_silver': len(offers),
            'top_count': len(top),
            'rankings': []
        }

        for o in top:
            r = {
                'offer_id': o['offer_id'],
                'title': o['mtop']['title'] if o.get('mtop') else None,
                'shop': o['mtop']['shop'] if o.get('mtop') else None,
                'price_cny': o['mtop']['price_cny'] if o.get('mtop') else None,
                'booked': o['mtop'].get('booked', 0) if o.get('mtop') else None,
                'price_brl_rakumart': o['rakumart']['price_brl'] if o.get('rakumart') else None,
                'naive_margin_pct': o['_margins']['naive_margin_pct'],
                'opportunity': o['_margins']['opportunity'],
            }
            out['rankings'].append(r)

        out_path = GOLD / 'by_category' / f'{slug}.json'
        out_path.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding='utf-8')
        print(f'  Wrote {out_path} ({len(top)} of {len(offers)} offers)')


def build_gold_to_source():
    """Build gold/to_source/priority.json — manual curated lists."""
    rankings_path = GOLD / 'rankings' / 'ranked_by_margin.json'
    if not rankings_path.exists():
        print('  SKIP: rankings not found, run --rankings first')
        return
    rankings = json.loads(rankings_path.read_text())
    high = [r for r in rankings['rankings'] if r['opportunity'] == 'HIGH' and r['match_score'] and r['match_score'] >= 80]

    # Manual priority list: top 10 HIGH opportunity with strong Rakumart match
    out = {
        'generated_at': datetime.now().isoformat() + 'Z',
        'description': 'Manual priority list — top 10 HIGH margin opportunities with Rakumart match >=80%. These are candidates for sourcing & ML listing.',
        'caveat': 'Naive margin only. Validate with shipping cost + ML fees before listing.',
        'priority_count': min(10, len(high)),
        'items': high[:10],
    }
    out_path = GOLD / 'to_source' / 'priority.json'
    out_path.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding='utf-8')
    print(f'  Wrote {out_path} ({out["priority_count"]} priority items)')


def main():
    parser = argparse.ArgumentParser(description='Transform silver offers to gold rankings')
    args = parser.parse_args()

    print('=== Building gold/rankings/ranked_by_margin.json ===')
    build_gold_rankings()

    print('\n=== Building gold/by_category/*.json ===')
    build_gold_by_category()

    print('\n=== Building gold/to_source/priority.json ===')
    build_gold_to_source()

    print('\nDONE')


if __name__ == '__main__':
    main()
