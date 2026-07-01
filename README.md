# products-1688

Scraping 1688.com to collect product catalog for ImportaSimples platform.

**Date**: 2026-07-02 (Sprint 6)

## Status

**Products:** 1,899 | **Source:** 1688 | **Categories:** 9 L1, 30+ L2, 100+ L3
**DB:** 1,899 in ImportaSimples (source='1688') | **Images:** 100% | **Translations:** 99.7%

## Architecture

```
MTOP API → Bronze Products (1688) → Silver Categories → ImportaSimples DB
```

## Data Flow

1. **Scrape**: MTOP API searches 1688.com
2. **Store**: Products saved to `bronze_products` (source='1688')
3. **Translate**: Chinese titles → Portuguese
4. **Categorize**: Map to silver_categories
5. **Sync**: Upload to ImportaSimples DB

## Categories

| L1 (CN) | L1 (PT) | Products |
|---------|---------|----------|
| 家居日用 | Casa | 425 |
| 电子数码 | Eletrônicos | 415 |
| 户外运动 | Esportes | 299 |
| 服装鞋帽 | Vestuário | 243 |
| 五金工具 | Ferramentas | 222 |
| 美妆护肤 | Beleza | 118 |
| 宠物用品 | Pets | 60 |
| 文具办公 | Escritório | 60 |
| 母婴用品 | Infantil | 57 |

## Files

- `scripts/production/scrape_1688_mtop.py` — MTOP scraper
- `scripts/production/save_bronze.py` — Save to bronze
- `scripts/production/translate_titles.py` — Translation
- `docs/translation_progress.md` — Translation status
- `docs/translation_quality_audit.md` — Quality audit

## Sprint 6 Status

- ✅ Source renamed: datalake → 1688
- ✅ 1,899 products translated (99.7%)
- ✅ HTML tags removed (234)
- ✅ Categories L1/L2/L3: 100%
- ⏳ Quality audit: 23 translation errors fixed
- ⏳ Mappings: need to verify silver_categories_map works
