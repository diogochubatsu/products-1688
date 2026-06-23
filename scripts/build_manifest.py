#!/usr/bin/env python3
"""
build_manifest.py — Build _manifest.json from current state of bronze/silver/gold.

Usage:
  python3 scripts/build_manifest.py

Run after every bronze_to_silver or silver_to_gold execution.
This is the single source of truth for data lineage.
"""

import json
from pathlib import Path
from datetime import datetime

DATA = Path(__file__).parent.parent / 'data'


def count_files(path: Path) -> int:
    """Count JSON files in path (recursive)."""
    return sum(1 for _ in Path(path).rglob('*.json') if _.is_file())


def build():
    """Build manifest from current disk state."""
    bronze = DATA / 'bronze'
    silver = DATA / 'silver'
    gold = DATA / 'gold'

    silver_offers = list((silver / 'offers').glob('*.json'))
    silver_suppliers = list((silver / 'suppliers').glob('*.json'))
    silver_categories = list((silver / 'categories').glob('*.json'))

    # Per-category breakdown
    categories = {}
    total_matched = 0
    total_enriched = 0
    for f in silver_offers:
        try:
            o = json.loads(f.read_text(encoding='utf-8'))
        except Exception:
            continue
        cat = o.get('category', 'unknown')
        if cat not in categories:
            categories[cat] = {
                'offers': 0, 'shops': set(),
                'matched': 0, 'enriched': 0, 'high_confidence': 0
            }
        categories[cat]['offers'] += 1
        categories[cat]['shops'].add(o.get('mtop', {}).get('shop', 'unknown'))
        if o.get('rakumart'):
            score = o['rakumart'].get('match_score', 0)
            if score >= 50:
                categories[cat]['high_confidence'] = categories[cat].get('high_confidence', 0) + 1
            if score >= 30:
                categories[cat]['matched'] += 1
                total_matched += 1
        if o.get('su_detail') and o['su_detail'].get('is_live'):
            categories[cat]['enriched'] += 1
            total_enriched += 1

    # Convert sets to ints
    for c in categories.values():
        c['unique_shops'] = len(c['shops'])
        del c['shops']

    # Gold rankings breakdown
    rankings = []
    rankings_path = gold / 'rankings' / 'ranked_by_margin.json'
    if rankings_path.exists():
        try:
            rdata = json.loads(rankings_path.read_text(encoding='utf-8'))
            rankings = rdata.get('rankings', [])
        except Exception:
            pass

    tiers = {}
    for r in rankings:
        t = r.get('opportunity_tier', 'unknown')
        tiers[t] = tiers.get(t, 0) + 1

    # Priority list
    priority = []
    priority_path = gold / 'to_source' / 'priority.json'
    if priority_path.exists():
        try:
            pdata = json.loads(priority_path.read_text(encoding='utf-8'))
            priority = pdata.get('items', [])
        except Exception:
            pass

    # Bronze mtop dates (track unique scrape dates)
    bronze_mtop_files = list((bronze / 'mtop').glob('*.json'))
    bronze_su_files = list((bronze / 'su_detail').glob('*.html'))
    bronze_rak_files = list((bronze / 'rakumart').glob('*.json'))

    # Read existing manifest for sprint_notes preservation
    existing = {}
    manifest_path = DATA / '_manifest.json'
    if manifest_path.exists():
        try:
            existing = json.loads(manifest_path.read_text(encoding='utf-8'))
        except Exception:
            pass

    manifest = {
        'generated_at': datetime.now().isoformat() + 'Z',
        'architecture': 'bronze / silver / gold',
        'sprint_notes': existing.get('sprint_notes', {}),
        'layers': {
            'bronze': {
                'description': 'Raw, untouched data from sources (immutable)',
                'mtop_files': len(bronze_mtop_files),
                'su_detail_files': len(bronze_su_files),
                'rakumart_files': len(bronze_rak_files),
                'mtop_size_kb': sum(f.stat().st_size for f in bronze_mtop_files) // 1024,
                'su_detail_size_kb': sum(f.stat().st_size for f in bronze_su_files) // 1024,
                'rakumart_size_kb': sum(f.stat().st_size for f in bronze_rak_files) // 1024,
            },
            'silver': {
                'description': 'Cleaned, joined, 1 file per entity',
                'offers': len(silver_offers),
                'suppliers': len(silver_suppliers),
                'categories': len(silver_categories),
            },
            'gold': {
                'description': 'Business-ready, ranked, actionable',
                'by_category': len(list((gold / 'by_category').glob('*.json'))),
                'rankings': len(list((gold / 'rankings').glob('*.json'))),
                'to_source': len(list((gold / 'to_source').glob('*.json'))),
                'priority_count': len(priority),
                'opportunity_tiers': tiers,
            },
        },
        'totals': {
            'silver_offers': len(silver_offers),
            'silver_suppliers': len(silver_suppliers),
            'silver_categories': len(silver_categories),
            'rakumart_matched': total_matched,
            'enriched': total_enriched,
            'match_rate_pct': round(total_matched / len(silver_offers) * 100, 1) if silver_offers else 0,
            'enrichment_rate_pct': round(total_enriched / len(silver_offers) * 100, 1) if silver_offers else 0,
        },
        'by_category': categories,
        'production_scripts': {
            'save_bronze': 'scripts/save_bronze.py',
            'run_pipeline': 'scripts/run_pipeline.py',
            'bronze_to_silver': 'scripts/bronze_to_silver.py',
            'silver_to_gold': 'scripts/silver_to_gold.py',
            'scrape_1688_mtop': 'scripts/scrape_1688_mtop.py',
            'scrape_1688': 'scripts/scrape_1688.py',
            'validate_pipeline': 'scripts/validate_pipeline.py',
            'build_manifest': 'scripts/build_manifest.py',
        },
    }

    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding='utf-8')
    print(f'Wrote {manifest_path}')
    print(f'  {len(silver_offers)} silver offers, {total_enriched} enriched ({manifest["totals"]["enrichment_rate_pct"]}%), {total_matched} matched ({manifest["totals"]["match_rate_pct"]}%)')
    print(f'  Categories: {list(categories.keys())}')
    return manifest


if __name__ == '__main__':
    build()