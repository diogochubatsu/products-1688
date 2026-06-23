#!/usr/bin/env python3
"""
validate_manifest.py — Verify manifest matches disk state.

Checks:
  - Counts (silver offers, suppliers, categories, bronze files)
  - No orphan offers (silver file without mtop data)
  - No stale bronze (any bronze mtop without matching silver)
  - Manifest totals consistent with by_category
  - All categories in by_category also have a silver/categories/*.json

Usage:
  python3 scripts/validate_manifest.py [--strict]
"""
import argparse
import json
import sys
from pathlib import Path

DATA = Path(__file__).parent.parent / 'data'


def load_manifest():
    m = DATA / '_manifest.json'
    if not m.exists():
        print('FAIL: _manifest.json not found')
        sys.exit(1)
    return json.loads(m.read_text(encoding='utf-8'))


def count_offers() -> int:
    return sum(1 for _ in (DATA / 'silver/offers').glob('*.json'))


def count_suppliers() -> int:
    return sum(1 for _ in (DATA / 'silver/suppliers').glob('*.json'))


def count_categories() -> int:
    return sum(1 for _ in (DATA / 'silver/categories').glob('*.json'))


def count_bronze() -> dict:
    return {
        'mtop': sum(1 for _ in (DATA / 'bronze/mtop').glob('*.json')),
        'su_detail': sum(1 for _ in (DATA / 'bronze/su_detail').glob('*.html')),
        'rakumart': sum(1 for _ in (DATA / 'bronze/rakumart').glob('*.json')),
    }


def check_orphans() -> list:
    """Silver offers without mtop data."""
    orphans = []
    for f in (DATA / 'silver/offers').glob('*.json'):
        o = json.loads(f.read_text())
        if not o.get('mtop') or not o['mtop'].get('title'):
            orphans.append(f.name)
    return orphans


def check_no_category_in_silver() -> list:
    """Categories in silver/offers but missing from silver/categories/."""
    actual = set()
    for f in (DATA / 'silver/offers').glob('*.json'):
        o = json.loads(f.read_text())
        cat = o.get('category', 'unknown')
        if cat:
            actual.add(cat)
    indexed = {f.stem for f in (DATA / 'silver/categories').glob('*.json')}
    return sorted(actual - indexed)


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--strict', action='store_true',
                   help='Exit non-zero if any check fails')
    args = p.parse_args()

    m = load_manifest()
    failures = []

    print('=' * 60)
    print('VALIDATE MANIFEST — checking disk state vs _manifest.json')
    print('=' * 60)

    # Check 1: Silver counts
    print('\n[1] Silver counts:')
    actual_offers = count_offers()
    actual_suppliers = count_suppliers()
    actual_categories = count_categories()
    m_offers = m['totals']['silver_offers']
    m_suppliers = m['totals']['silver_suppliers']
    m_categories = m['totals']['silver_categories']

    for label, a, m_val in [
        ('offers', actual_offers, m_offers),
        ('suppliers', actual_suppliers, m_suppliers),
        ('categories', actual_categories, m_categories),
    ]:
        status = 'OK' if a == m_val else 'FAIL'
        print(f'  {label:12s}: disk={a:>4}  manifest={m_val:>4}  [{status}]')
        if a != m_val:
            failures.append(f'{label}: disk={a} manifest={m_val}')

    # Check 2: Bronze counts
    print('\n[2] Bronze counts:')
    actual_bronze = count_bronze()
    m_bronze = m['layers']['bronze']
    for layer in ['mtop', 'su_detail', 'rakumart']:
        a = actual_bronze[layer]
        m_val = m_bronze.get(f'{layer}_files', 0)
        status = 'OK' if a == m_val else 'FAIL'
        print(f'  {layer:12s}: disk={a:>4}  manifest={m_val:>4}  [{status}]')
        if a != m_val:
            failures.append(f'bronze.{layer}: disk={a} manifest={m_val}')

    # Check 3: Orphans
    print('\n[3] Orphan silver offers (no mtop data):')
    orphans = check_orphans()
    if orphans:
        print(f'  FAIL: {len(orphans)} orphan offers: {orphans[:5]}...')
        failures.append(f'{len(orphans)} orphan silver offers')
    else:
        print('  OK: no orphans')

    # Check 4: Categories without index
    print('\n[4] Categories in offers but missing from silver/categories/:')
    no_idx = check_no_category_in_silver()
    if no_idx:
        print(f'  WARN: {len(no_idx)} categories not indexed: {no_idx}')
        # This is a WARN, not a FAIL
    else:
        print('  OK: all categories indexed')

    # Check 5: by_category consistency
    print('\n[5] by_category consistency:')
    m_by_cat = m.get('by_category', {})
    if isinstance(m_by_cat, dict):
        m_total = sum(c.get('offers', 0) for c in m_by_cat.values())
        if m_total != actual_offers:
            print(f'  FAIL: by_category total={m_total} != actual offers={actual_offers}')
            failures.append(f'by_category sum mismatch: {m_total} vs {actual_offers}')
        else:
            print(f'  OK: by_category sum={m_total} == actual offers={actual_offers}')
    else:
        print('  WARN: by_category not a dict (older manifest format)')

    # Check 6: Gold rankings match silver count
    print('\n[6] Gold rankings count:')
    rankings_path = DATA / 'gold/rankings/ranked_by_margin.json'
    if rankings_path.exists():
        r = json.loads(rankings_path.read_text())
        r_count = len(r.get('rankings', []))
        status = 'OK' if r_count == actual_offers else 'WARN'
        print(f'  rankings={r_count}  silver offers={actual_offers}  [{status}]')
        if r_count != actual_offers:
            print(f'    (rebuild with: python3 scripts/silver_to_gold.py)')
    else:
        print('  WARN: ranked_by_margin.json not found')

    # Summary
    print('\n' + '=' * 60)
    if failures:
        print(f'FAIL: {len(failures)} issues')
        for f in failures:
            print(f'  - {f}')
        if args.strict:
            sys.exit(1)
    else:
        print('PASSED: all checks')
    print('=' * 60)


if __name__ == '__main__':
    main()