#!/usr/bin/env python3
"""
eval_cross_walk.py — Manual precision/recall evaluation of cross-walk matches.

Samples NEW crosswalk matches (those with title_br from search-based matching).
Legacy CN-vs-CN matches (title_pt only) are excluded — different scoring method.

Usage:
  python3 scripts/eval_cross_walk.py --sample 30  # creates _eval_cross_walk.json
  # ... edit _eval_cross_walk.json, set "label": "GOOD" or "BAD" ...
  python3 scripts/eval_cross_walk.py --stats-only
"""
import argparse
import json
import random
from collections import Counter
from pathlib import Path

DATA = Path(__file__).parent.parent / 'data'
SILVER = DATA / 'silver' / 'offers'
EVAL_FILE = DATA / '_eval_cross_walk.json'


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--sample', type=int, default=30, help='Number of offers to sample')
    p.add_argument('--seed', type=int, default=42, help='Random seed for reproducibility')
    p.add_argument('--min-score', type=float, default=30)
    p.add_argument('--max-score', type=float, default=100)
    p.add_argument('--category', help='Filter to category')
    p.add_argument('--stats-only', action='store_true',
                   help='Only print stats, do not save eval file')
    args = p.parse_args()

    random.seed(args.seed)

    # Only sample NEW crosswalk matches (have title_br)
    candidates = []
    for f in SILVER.glob('*.json'):
        o = json.loads(f.read_text())
        rk = o.get('rakumart')
        if not rk or not rk.get('title_br'):
            continue  # Skip legacy matches
        score = rk.get('match_score', 0)
        if not (args.min_score <= score <= args.max_score):
            continue
        if args.category and o.get('category') != args.category:
            continue
        candidates.append(f)

    print(f'NEW crosswalk candidates (score {args.min_score}-{args.max_score}, cat={args.category}): {len(candidates)}')

    # Stratified sampling: 10 from each score band
    bands = {'30-49': [], '50-69': [], '70-100': []}
    for f in candidates:
        o = json.loads(f.read_text())
        s = o['rakumart']['match_score']
        if 30 <= s < 50:
            bands['30-49'].append(f)
        elif 50 <= s < 70:
            bands['50-69'].append(f)
        elif 70 <= s <= 100:
            bands['70-100'].append(f)

    sampled = []
    for band, items in bands.items():
        random.shuffle(items)
        sampled.extend(items[:10])

    print(f'Total sampled (stratified): {len(sampled)}')
    print()

    eval_data = {
        'sample_size': len(sampled),
        'seed': args.seed,
        'note': 'NEW crosswalk matches only (have title_br). Legacy CN-vs-CN excluded.',
        'matches': [],
    }

    for i, f in enumerate(sampled, 1):
        o = json.loads(f.read_text())
        rk = o.get('rakumart', {})
        cn = (o.get('mtop') or {}).get('title', '')[:80]
        pt = rk.get('title_br', '')[:80]
        url = rk.get('url', '')

        print(f'[{i}/{len(sampled)}] {o.get("category")} score={rk.get("match_score")}')
        print(f'  CN: {cn}')
        print(f'  PT: {pt}')
        print(f'  URL: {url}')
        print()

        eval_data['matches'].append({
            'offer_id': f.stem,
            'category': o.get('category'),
            'cn_title': cn,
            'pt_title': pt,
            'url': url,
            'match_score': rk.get('match_score'),
            'label': None,  # User fills: 'GOOD' or 'BAD'
        })

    if not args.stats_only:
        EVAL_FILE.write_text(json.dumps(eval_data, ensure_ascii=False, indent=2))
        print(f'Wrote {EVAL_FILE}')
        print()
        print('NEXT STEPS:')
        print(f'  1. Verify each match by visiting the URL')
        print(f'  2. Edit {EVAL_FILE} and set each match "label" to "GOOD" or "BAD"')
        print(f'  3. Run: python3 scripts/eval_cross_walk.py --stats-only')


def stats():
    if not EVAL_FILE.exists():
        print(f'No eval file at {EVAL_FILE}')
        return
    eval_data = json.loads(EVAL_FILE.read_text())
    labels = [m['label'] for m in eval_data['matches'] if m.get('label')]
    n_labeled = len(labels)
    n_good = sum(1 for l in labels if l == 'GOOD')
    n_bad = sum(1 for l in labels if l == 'BAD')

    if n_labeled == 0:
        print('No labels yet. Edit _eval_cross_walk.json and set "label" field.')
        return

    precision = n_good / n_labeled if n_labeled else 0
    print('=' * 50)
    print('CROSSWALK PRECISION RESULTS')
    print('=' * 50)
    print(f'Total sampled: {eval_data["sample_size"]}')
    print(f'Labeled: {n_labeled}')
    print(f'GOOD: {n_good}')
    print(f'BAD: {n_bad}')
    print(f'Precision: {precision:.1%}')
    print()

    # By score band
    by_band = Counter()
    by_band_correct = Counter()
    for m in eval_data['matches']:
        score = m.get('match_score', 0)
        if score < 50:
            band = '30-49'
        elif score < 70:
            band = '50-69'
        else:
            band = '70-100'
        by_band[band] += 1
        if m.get('label') == 'GOOD':
            by_band_correct[band] += 1

    print('By score band:')
    for band in ['30-49', '50-69', '70-100']:
        if by_band[band]:
            correct = by_band_correct[band]
            total = by_band[band]
            pct = correct / total if total else 0
            print(f'  {band}: {correct}/{total} = {pct:.1%}')

    # By category
    by_cat = Counter()
    by_cat_correct = Counter()
    for m in eval_data['matches']:
        cat = m.get('category', 'unknown')
        by_cat[cat] += 1
        if m.get('label') == 'GOOD':
            by_cat_correct[cat] += 1

    print()
    print('By category:')
    for cat in sorted(by_cat.keys()):
        correct = by_cat_correct[cat]
        total = by_cat[cat]
        pct = correct / total if total else 0
        print(f'  {cat}: {correct}/{total} = {pct:.1%}')


if __name__ == '__main__':
    import sys
    if '--stats-only' in sys.argv:
        stats()
    else:
        main()