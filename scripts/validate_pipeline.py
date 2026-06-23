#!/usr/bin/env python3
"""
validate_pipeline.py — Sanity check the 4-stage pipeline end-to-end.

Usage:
  python3 scripts/validate_pipeline.py mtop       # test MTOP connectivity
  python3 scripts/validate_pipeline.py rakumart   # test Rakumart search
  python3 scripts/validate_pipeline.py su         # test Decodo SU detail page
  python3 scripts/validate_pipeline.py manifest   # check manifest consistency
  python3 scripts/validate_pipeline.py all        # run all checks

Replaces: strategy_matrix.py, test_3_categories.py, validate_mtop.py (archived 2026-06-17).
"""

import json
import sys
import time
import urllib.request
import ssl
from pathlib import Path

DATA = Path(__file__).parent.parent / 'data'

# MTOP
sys.path.insert(0, '/tmp/scrapers-test/ai-reverse/1688')

# Rakumart
sys.path.insert(0, '/mnt/ssd/1688-intel/scripts/arbitlens')

# Decodo SU credentials
SU_PASS = 'PW_17560792063f932882c0843ad92c0ed69'
SU_USER = 'U0000434457'
PROXY = f'http://{SU_USER}:{SU_PASS}@unblock.decodo.com:60000'


def check_mtop() -> bool:
    """Verify MTOP client returns results for a known query."""
    try:
        from client import Alibaba1688Client
        c = Alibaba1688Client()
        c.session.login()
        r = c.search_by_text('沙滩巾夹', page=1, page_size=5)
        items = r.data['data']['OFFER']['items']
        print(f'  ✓ MTOP: {len(items)} items for "沙滩巾夹"')
        return len(items) > 0
    except Exception as e:
        print(f'  ✗ MTOP: {e}')
        return False


def check_rakumart() -> bool:
    """Verify Rakumart search returns items."""
    try:
        from scrape_rakumart_br import search_rakumart_br
        results = search_rakumart_br('meias', source='1688', page=1)
        print(f'  ✓ Rakumart: {len(results)} items for "meias" (1688 source)')
        return len(results) > 0
    except Exception as e:
        print(f'  ✗ Rakumart: {e}')
        return False


def check_su() -> bool:
    """Verify Decodo SU detail page returns content."""
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    opener = urllib.request.build_opener(
        urllib.request.ProxyHandler({'http': PROXY, 'https': PROXY})
    )
    try:
        # Test with a known live offer (baiyite bestseller)
        req = urllib.request.Request(
            'https://detail.1688.com/offer/832247158134.html',
            headers={'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'}
        )
        req.add_header('X-SU-Geo', 'China')
        req.add_header('X-SU-Locale', 'zh-cn')
        body = opener.open(req, timeout=60).read().decode('utf-8', errors='ignore')
        ok = len(body) > 50000
        print(f'  ✓ Decodo SU: {len(body)/1024:.1f} KB for offer 832247158134')
        return ok
    except Exception as e:
        print(f'  ✗ Decodo SU: {e}')
        return False


def check_manifest() -> bool:
    """Verify manifest is consistent with on-disk state."""
    manifest_path = DATA / '_manifest.json'
    if not manifest_path.exists():
        print(f'  ✗ Manifest: {manifest_path} not found')
        return False
    manifest = json.loads(manifest_path.read_text())
    actual_offers = len(list((DATA / 'silver/offers').glob('*.json')))
    expected = manifest['totals']['silver_offers']
    ok = actual_offers == expected
    status = '✓' if ok else '✗'
    print(f'  {status} Manifest: silver_offers={actual_offers} (expected {expected})')
    return ok


def main():
    cmd = sys.argv[1] if len(sys.argv) > 1 else 'all'

    print('=' * 60)
    print(f'PIPELINE VALIDATION — {cmd}')
    print('=' * 60)

    results = {}
    if cmd in ('mtop', 'all'):
        print('\n[MTOP]')
        results['mtop'] = check_mtop()
    if cmd in ('rakumart', 'all'):
        print('\n[Rakumart]')
        results['rakumart'] = check_rakumart()
    if cmd in ('su', 'all'):
        print('\n[Decodo SU]')
        results['su'] = check_su()
        if results['su']:
            time.sleep(3)  # Respect rate limit
    if cmd in ('manifest', 'all'):
        print('\n[Manifest]')
        results['manifest'] = check_manifest()

    print('\n' + '=' * 60)
    if all(results.values()):
        print(f'PASSED: {len(results)} checks')
        sys.exit(0)
    else:
        failed = [k for k, v in results.items() if not v]
        print(f'FAILED: {failed}')
        sys.exit(1)


if __name__ == '__main__':
    main()