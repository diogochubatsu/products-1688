#!/usr/bin/env python3
"""
save_bronze.py — Save raw snapshots to bronze/ layer (immutable).

Usage:
  python3 scripts/save_bronze.py mtop '{"data": ...}' 沙滩巾夹 --page 1
  python3 scripts/save_bronze.py su_detail "<html>..." 641931920298
  python3 scripts/save_bronze.py rakumart '{"items": ...}' meias 1688 --page 1

Bronze layer is the immutable source of truth. Files are NEVER modified.
Re-running the same query creates a new file with today's date.
"""

import json
import re
import sys
from datetime import datetime
from pathlib import Path

DATA_ROOT = Path(__file__).parent.parent / 'data'
BRONZE = DATA_ROOT / 'bronze'


def _slug(s: str) -> str:
    """Convert query string to filesystem-safe slug."""
    s = s.replace('/', '_').replace(' ', '_')
    s = re.sub(r'[^\w\-_]', '', s)
    return s[:80]  # truncate very long queries


def save_mtop(query: str, page: int, data: dict) -> str:
    """Save raw MTOP search response to bronze/mtop/."""
    try:
        date = datetime.now().strftime('%Y-%m-%d')
        slug = _slug(query)
        out = BRONZE / 'mtop' / f'{date}_{slug}_p{page}.json'
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding='utf-8')
        return str(out.relative_to(DATA_ROOT))
    except Exception as e:
        print(f'ERROR save_mtop: {e}', file=sys.stderr)
        raise


def save_su_detail(offer_id: int, html: str) -> str:
    """Save raw Decodo SU detail HTML to bronze/su_detail/."""
    try:
        date = datetime.now().strftime('%Y-%m-%d')
        out = BRONZE / 'su_detail' / f'{date}_{offer_id}.html'
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(html, encoding='utf-8')
        return str(out.relative_to(DATA_ROOT))
    except Exception as e:
        print(f'ERROR save_su_detail: {e}', file=sys.stderr)
        raise


def save_rakumart(query: str, source: str, page: int, data: dict) -> str:
    """Save raw Rakumart search response to bronze/rakumart/."""
    try:
        date = datetime.now().strftime('%Y-%m-%d')
        slug = _slug(query)
        out = BRONZE / 'rakumart' / f'{date}_{slug}_{source}_p{page}.json'
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding='utf-8')
        return str(out.relative_to(DATA_ROOT))
    except Exception as e:
        print(f'ERROR save_rakumart: {e}', file=sys.stderr)
        raise


# ────────────────────────────────────────────────────────────────────
# Programmatic API (for use in scripts, not just CLI)
# ────────────────────────────────────────────────────────────────────

def save_mtop_data(query: str, page: int, data) -> str:
    """Save MTOP response (handles both dict and object with .data attr)."""
    if hasattr(data, 'data'):
        payload = data.data if isinstance(data.data, dict) else data.__dict__
    else:
        payload = data
    return save_mtop(query, page, payload)


def save_rakumart_results(query: str, source: str, page: int, items) -> str:
    """Save Rakumart search results (handles list of objects)."""
    serialized = []
    for item in items:
        if hasattr(item, '__dict__'):
            serialized.append(item.__dict__)
        elif isinstance(item, dict):
            serialized.append(item)
        else:
            serialized.append(str(item))
    return save_rakumart(query, source, page, {'items': serialized, 'count': len(serialized)})


# ────────────────────────────────────────────────────────────────────
# CLI
# ────────────────────────────────────────────────────────────────────

def main():
    try:
        layer = sys.argv[1]

        if layer == 'mtop':
            data = json.loads(sys.argv[2])
            query = sys.argv[3]
            page = int(sys.argv[4]) if len(sys.argv) > 4 else 1
            path = save_mtop(query, page, data)
            print(f'OK {path}')

        elif layer == 'su_detail':
            html = sys.argv[2]
            offer_id = int(sys.argv[3])
            path = save_su_detail(offer_id, html)
            print(f'OK {path}')

        elif layer == 'rakumart':
            data = json.loads(sys.argv[2])
            query = sys.argv[3]
            source = sys.argv[4]
            page = int(sys.argv[5]) if len(sys.argv) > 5 else 1
            path = save_rakumart(query, source, page, data)
            print(f'OK {path}')

        else:
            print(f'Usage:')
            print(f'  {sys.argv[0]} mtop <json> <query> [page]')
            print(f'  {sys.argv[0]} su_detail <html> <offer_id>')
            print(f'  {sys.argv[0]} rakumart <json> <query> <source> [page]')
            sys.exit(1)


    except IndexError:
        print(f'Usage: {sys.argv[0]} <layer> <args...>')
        sys.exit(1)
    except json.JSONDecodeError as e:
        print(f'ERROR: Invalid JSON: {e}', file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f'ERROR: {e}', file=sys.stderr)
        sys.exit(1)


if __name__ == '__main__':
    main()