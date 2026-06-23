#!/usr/bin/env python3
"""
api_server.py — FastAPI server exposing the 1688 data lake.

Endpoints:
- GET  /                          service info
- GET  /manifest                  overall stats from _manifest.json
- GET  /categories                N1-N4 taxonomy tree
- GET  /offers                    list with filters (n1, n4, has_match, page, limit)
- GET  /offers/{offer_id}         single offer detail (silver JSON)
- GET  /search?q=...              search by CN/PT title (substring)
- GET  /stats/match-rate          per-category match rates
- GET  /stats/by-n1               distribution by N1
- GET  /stats/suppliers           supplier leaderboard
- GET  /opportunities             high-margin opportunities (top matches)

Run: /mnt/ssd/arbitlens/.venv/bin/python3 scripts/api_server.py
Default port: 3003
"""
import json
import re
import sys
import urllib.request
import urllib.error
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pathlib import Path as Pathlib

# ── Config ──────────────────────────────────────────────────
ROOT = Path('/mnt/ssd/1688-only')
DATA = ROOT / 'data'
HOST = '0.0.0.0'
PORT = 3003

app = FastAPI(
    title='1688 Data Lake API',
    description='Read-only API exposing Sprint 4/5 1688 scraping data: 294 offers, 9 N1 taxonomy, 92.9% Rakumart matched.',
    version='1.0.0',
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=['*'],
    allow_methods=['*'],
    allow_headers=['*'],
)


# ── Helpers ─────────────────────────────────────────────────
def _load_json(path: Path):
    if not path.exists():
        return None
    with open(path) as f:
        return json.load(f)


def _load_all_offers():
    """Load all 294 silver offers, returning list of dicts."""
    out = []
    for f in (DATA / 'silver/offers').glob('*.json'):
        try:
            o = json.loads(f.read_text())
            out.append(o)
        except Exception:
            pass
    return out


_OFFERS_CACHE = None


def _offers():
    global _OFFERS_CACHE
    if _OFFERS_CACHE is None:
        _OFFERS_CACHE = _load_all_offers()
    return _OFFERS_CACHE


# ── Routes ──────────────────────────────────────────────────
@app.get('/api')
def root():
    return {
        'service': '1688 Data Lake API',
        'version': '1.0.0',
        'data_root': str(DATA),
        'endpoints': [
            'GET /manifest',
            'GET /categories',
            'GET /offers?n1=...&n4=...&has_match=true&page=1&limit=50',
            'GET /offers/{offer_id}',
            'GET /search?q=...',
            'GET /stats/match-rate',
            'GET /stats/by-n1',
            'GET /stats/suppliers',
            'GET /opportunities?limit=20',
        ],
    }


@app.get('/api/manifest')
def get_manifest():
    """Overall project stats + bronze file listing."""
    m = _load_json(DATA / '_manifest.json') or {}
    
    # Add bronze file info dynamically
    bronze = DATA / 'bronze'
    sources = {}
    for src_name in ['mtop', 'rakumart', 'su_detail']:
        src_dir = bronze / src_name
        if src_dir.exists():
            files = list(src_dir.glob('*'))
            total_size = sum(f.stat().st_size for f in files if f.is_file())
            file_dates = sorted(set(f.name[:10] for f in files if f.is_file() and len(f.name) >= 10))
            sources[src_name] = {
                'files': len(files),
                'size_mb': round(total_size / 1024 / 1024, 1),
                'dates': ' to '.join(file_dates[:2]) if file_dates else 'unknown',
            }
    m['sources'] = sources
    
    # Add silver summary
    silver_offers = list((DATA / 'silver' / 'offers').glob('*.json')) if (DATA / 'silver' / 'offers').exists() else []
    matched = sum(1 for f in silver_offers if json.loads(f.read_text()).get('rakumart'))
    m['silver'] = {
        'offers': len(silver_offers),
        'matched': matched,
        'match_rate': f'{matched/len(silver_offers)*100:.1f}%' if silver_offers else '0%',
    }
    
    return m


@app.get('/api/categories')
def get_categories():
    """Full N1-N4 taxonomy."""
    tax = _load_json(DATA / 'taxonomy/n1_n4.json')
    if not tax:
        raise HTTPException(404, 'taxonomy not found')
    return tax


@app.get('/api/offers')
def list_offers(
    n1: Optional[str] = Query(None, description='Filter by N1 name (e.g., 服装鞋帽)'),
    n2: Optional[str] = Query(None, description='Filter by N2 subcategory'),
    n3: Optional[str] = Query(None, description='Filter by N3 subcategory'),
    n4: Optional[str] = Query(None, description='Filter by N4 leaf name'),
    category: Optional[str] = Query(None, description='Filter by flat category (e.g., socks)'),
    has_match: Optional[bool] = Query(None, description='True=only matched Rakumart, False=only unmatched'),
    min_score: Optional[float] = Query(None, description='Min match_score (0-100)'),
    page: int = Query(1, ge=1),
    limit: int = Query(50, ge=1, le=200),
):
    """List offers with filters. Paginated."""
    filtered = []
    for o in _offers():
        tax = o.get('taxonomy') or {}
        if n1 and tax.get('n1') != n1:
            continue
        if n2 and tax.get('n2') != n2:
            continue
        if n3 and tax.get('n3') != n3:
            continue
        if n4 and tax.get('n4') != n4:
            continue
        if category and o.get('category') != category:
            continue
        if has_match is True and not o.get('rakumart'):
            continue
        if has_match is False and o.get('rakumart'):
            continue
        if min_score is not None:
            score = (o.get('rakumart') or {}).get('match_score') or 0
            if score < min_score:
                continue
        filtered.append(o)

    # Apply pagination
    start = (page - 1) * limit
    end = start + limit
    page_data = filtered[start:end]

    return {
        'total': len(filtered),
        'page': page,
        'limit': limit,
        'returned': len(page_data),
        'offers': page_data,
    }


@app.get('/api/offers/{offer_id}')
def get_offer(offer_id: int):
    """Single offer detail."""
    for o in _offers():
        if o.get('offer_id') == offer_id:
            return o
    raise HTTPException(404, f'offer {offer_id} not found')


@app.get('/api/image/{offer_id}')
def get_image(offer_id: int):
    """Image proxy with disk cache. Fetches 1688 image, saves to disk, returns."""
    from fastapi.responses import Response

    CACHE_DIR = DATA / 'cache' / 'images'
    CACHE_DIR.mkdir(parents=True, exist_ok=True)

    cache_path = CACHE_DIR / f'{offer_id}.jpg'

    # Cache hit: serve from disk
    if cache_path.exists():
        return Response(
            content=cache_path.read_bytes(),
            media_type='image/jpeg',
            headers={
                'Cache-Control': 'public, max-age=86400',
                'Access-Control-Allow-Origin': '*',
                'X-Cache': 'HIT',
            },
        )

    # Find offer
    for o in _offers():
        if o.get('offer_id') == offer_id:
            url = ((o.get('mtop') or {}).get('image_url'))
            if not url:
                raise HTTPException(404, 'no image for this offer')
            try:
                req = urllib.request.Request(
                    url,
                    headers={
                        'User-Agent': 'Mozilla/5.0 (Linux; Android 10) AppleWebKit/537.36',
                        'Referer': 'https://m.1688.com/',
                        'Accept': 'image/avif,image/webp,image/apng,image/svg+xml,image/*,*/*;q=0.8',
                    },
                )
                with urllib.request.urlopen(req, timeout=10) as resp:
                    data = resp.read()
                    content_type = resp.headers.get('Content-Type', 'image/jpeg')
                    # Save to cache
                    cache_path.write_bytes(data)
                    return Response(
                        content=data,
                        media_type=content_type,
                        headers={
                            'Cache-Control': 'public, max-age=86400',
                            'Access-Control-Allow-Origin': '*',
                            'X-Cache': 'MISS',
                        },
                    )
            except urllib.error.HTTPError as e:
                raise HTTPException(e.code, f'upstream error: {e.reason}')
            except Exception as e:
                raise HTTPException(500, f'fetch failed: {e}')
    raise HTTPException(404, f'offer {offer_id} not found')


@app.get('/api/search')
def search(q: str = Query(..., min_length=2), limit: int = Query(50, ge=1, le=200)):
    """Substring search across CN titles, PT titles, supplier names."""
    q_lower = q.lower()
    matches = []
    for o in _offers():
        mtop = o.get('mtop') or {}
        su = o.get('su_detail') or {}
        rk = o.get('rakumart') or {}
        haystacks = [
            (mtop.get('title') or '').lower(),
            (rk.get('title_br') or '').lower(),
            (rk.get('title_pt') or '').lower(),
            (su.get('shop_name') or '').lower(),
        ]
        if any(q_lower in h for h in haystacks):
            matches.append({
                'offer_id': o.get('offer_id'),
                'category': o.get('category'),
                'title_cn': mtop.get('title'),
                'title_br': rk.get('title_br'),
                'price_cny': mtop.get('price_cny'),
                'price_brl': rk.get('price_brl'),
                'match_score': rk.get('match_score'),
                'has_match': bool(rk),
            })
    return {
        'query': q,
        'total': len(matches),
        'returned': min(len(matches), limit),
        'matches': matches[:limit],
    }


@app.get('/api/stats/match-rate')
def stats_match_rate():
    """Per-category match rates."""
    by_cat = {}
    for o in _offers():
        c = o.get('category', 'unknown')
        if c not in by_cat:
            by_cat[c] = {'offers': 0, 'matched': 0, 'suppliers': set()}
        by_cat[c]['offers'] += 1
        if o.get('rakumart'):
            by_cat[c]['matched'] += 1
        supplier = (o.get('su_detail') or {}).get('shop_name')
        if supplier:
            by_cat[c]['suppliers'].add(supplier)
    out = []
    for c, d in sorted(by_cat.items(), key=lambda x: -x[1]['offers']):
        rate = (d['matched'] / d['offers'] * 100) if d['offers'] else 0
        out.append({
            'category': c,
            'offers': d['offers'],
            'matched': d['matched'],
            'unmatched': d['offers'] - d['matched'],
            'match_rate_pct': round(rate, 1),
            'suppliers': len(d['suppliers']),
        })
    return {'categories': out}


@app.get('/api/stats/by-n1')
def stats_by_n1():
    """Distribution by N1 taxonomy."""
    by_n1 = {}
    for o in _offers():
        n1 = (o.get('taxonomy') or {}).get('n1', 'unknown')
        if n1 not in by_n1:
            by_n1[n1] = {'offers': 0, 'matched': 0}
        by_n1[n1]['offers'] += 1
        if o.get('rakumart'):
            by_n1[n1]['matched'] += 1
    out = []
    for n1, d in sorted(by_n1.items(), key=lambda x: -x[1]['offers']):
        rate = (d['matched'] / d['offers'] * 100) if d['offers'] else 0
        out.append({
            'n1': n1,
            'offers': d['offers'],
            'matched': d['matched'],
            'match_rate_pct': round(rate, 1),
        })
    return {'n1_distribution': out, 'total_n1': len(by_n1)}


@app.get('/api/stats/suppliers')
def stats_suppliers(limit: int = Query(20, ge=1, le=100)):
    """Supplier leaderboard (offers per supplier)."""
    sup = {}
    for o in _offers():
        s = (o.get('su_detail') or {}).get('shop_name') or 'unknown'
        if s not in sup:
            sup[s] = {'offers': 0, 'categories': set(), 'matched': 0}
        sup[s]['offers'] += 1
        sup[s]['categories'].add(o.get('category'))
        if o.get('rakumart'):
            sup[s]['matched'] += 1
    out = []
    for s, d in sorted(sup.items(), key=lambda x: -x[1]['offers'])[:limit]:
        out.append({
            'supplier': s,
            'offers': d['offers'],
            'categories': list(d['categories']),
            'matched': d['matched'],
        })
    return {'suppliers': out, 'total_unique': len(sup)}


@app.get('/api/opportunities')
def opportunities(limit: int = Query(20, ge=1, le=100)):
    """Top opportunities: matched offers with biggest 1688→BR margin."""
    out = []
    for o in _offers():
        rk = o.get('rakumart')
        mtop = o.get('mtop') or {}
        if not rk:
            continue
        try:
            price_cny = float(mtop.get('price_cny') or 0)
            price_brl = float(rk.get('price_brl') or 0)
        except (ValueError, TypeError):
            continue
        if price_cny <= 0 or price_brl <= 0:
            continue
        # Rough FX: 1 CNY ≈ 0.75 BRL; assume 30% landed cost
        cny_to_brl = price_cny * 0.75 * 1.30
        markup = price_brl / cny_to_brl if cny_to_brl else 0
        if markup < 1.5:  # skip non-opportunities
            continue
        out.append({
            'offer_id': o.get('offer_id'),
            'category': o.get('category'),
            'n4': (o.get('taxonomy') or {}).get('n4'),
            'title_cn': mtop.get('title'),
            'title_br': rk.get('title_br'),
            'price_cny': round(price_cny, 2),
            'price_brl': round(price_brl, 2),
            'est_landed_brl': round(cny_to_brl, 2),
            'markup_x': round(markup, 2),
            'match_score': rk.get('match_score'),
            'supplier': (o.get('su_detail') or {}).get('shop_name'),
        })
    out.sort(key=lambda x: -x['markup_x'])
    return {'opportunities': out[:limit], 'total_found': len(out)}


# ── Main ────────────────────────────────────────────────────
if __name__ == '__main__':
    import uvicorn
    # Mount static HTML at root so it serves alongside the API
    PUBLIC_DIR = ROOT / 'public'
    if PUBLIC_DIR.exists():
        app.mount('/', StaticFiles(directory=str(PUBLIC_DIR), html=True), name='public')
        print(f'Static files mounted at / from {PUBLIC_DIR}')
    print(f'Starting 1688 Data Lake API on http://{HOST}:{PORT}')
    print(f'Data root: {DATA}')
    print(f'Open browser: http://<host>:{PORT}/')
    uvicorn.run(app, host=HOST, port=PORT, log_level='info')