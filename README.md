# MIMO — Multilingual Marketing Content Factory

Cross-border e-commerce multi-agent system that transforms Chinese product data + images into SEO-optimized, culturally adapted marketing copy across 8 languages and 3 platforms.

## Architecture

A 5-stage Agent pipeline powered by Anthropic Claude:

```
Product Input (Chinese + Images)
    │
    ▼
[Stage 1] Understander Agent (Multimodal Vision)
    │  Extracts visual features + text specs → ProductProfile
    ▼
[Stage 2] Copywriter Agent (Brand Storyline)
    │  Generates canonical English brand narrative
    ▼
[Stage 3] Localize Agents (Parallel, N locales × M platforms)
    │  Native-tone translation + SEO keyword embedding
    ▼
[Stage 4] Review Agents (Parallel, Cultural QA)
    │  Taboo words, sensitive colors, compliance checks
    ▼
[Stage 5] CMS Publisher (Parallel, API Push)
    │  Format → Push to CMS / Save to files
    ▼
Output: Localized listings for Amazon, Shopify, TikTok
```

## Supported Languages & Platforms

| Code | Language  | Code | Language   |
|------|-----------|------|------------|
| fr   | French    | ko   | Korean     |
| de   | German    | pt   | Portuguese |
| es   | Spanish   | it   | Italian    |
| ja   | Japanese  | ar   | Arabic     |

Platforms: **Amazon**, **Shopify**, **TikTok/Instagram**

## Quick Start

### 1. Install

```bash
pip install -r requirements.txt
```

### 2. Configure

```bash
cp .env.example .env
# Edit .env — add your ANTHROPIC_API_KEY
```

### 3. Run

```bash
# Basic: text-only product, French + German, Amazon
python -m src.main run \
  --product "蓝牙降噪耳机" \
  --specs "主动降噪 ANC -35dB，蓝牙5.3，续航30小时" \
  --price "¥299-399" \
  --feature "主动降噪" \
  --feature "Hi-Fi音质" \
  --feature "低延迟游戏模式" \
  --category "electronics" \
  --brand "SoundMax" \
  --locales "fr,de" \
  --platform "amazon"

# With product images
python -m src.main run \
  --product "瑜伽运动 leggings" \
  --images ./samples/yoga-pants/ \
  --locales "fr,de,es,ja" \
  --platform "shopify,tiktok"

# Dry run (skip CMS publish)
python -m src.main run --product "test" --dry-run

# List supported locales
python -m src.main list-locales

# List supported platforms
python -m src.main list-platforms
```

### 4. View Output

Output files are saved to `./output/` by default:
- `pipeline_result_*.json` — full pipeline result with all agent outputs
- `amazon_fr.md` — formatted Amazon listing for French market
- `shopify_ja.md` — Shopify page for Japanese market
- etc.

## Project Structure

```
xiaomi-mimo/
├── src/
│   ├── main.py              # CLI entry point (Click + Rich)
│   ├── orchestrator.py      # 5-stage pipeline coordinator
│   ├── config.py            # YAML + env configuration
│   ├── agents/
│   │   ├── base.py          # Base agent (Anthropic client + retry)
│   │   ├── understander.py  # Multimodal vision agent
│   │   ├── copywriter.py    # Brand storyline agent
│   │   ├── localizer.py     # Per-locale adaptation agent
│   │   └── reviewer.py      # Cultural QA agent
│   ├── models/
│   │   ├── product.py       # Product data models
│   │   └── content.py       # Content asset models
│   ├── platforms/
│   │   ├── amazon.py        # Amazon listing template
│   │   ├── shopify.py       # Shopify product page template
│   │   └── tiktok.py        # TikTok script template
│   ├── seo/
│   │   └── keywords.py      # Locale-specific keyword DB
│   ├── cms/
│   │   └── publisher.py     # CMS API integration
│   └── utils/
│       ├── image.py         # Image encoding utilities
│       └── logger.py        # Structured logging
├── config/
│   └── settings.yaml        # Agent models, retry config, brand defaults
├── tests/
│   └── test_pipeline.py     # Unit + integration tests
├── requirements.txt
├── pyproject.toml
└── .env.example
```

## Configuration

### Agent Models

| Agent        | Default Model      | Purpose                        |
|--------------|--------------------|---------------------------------|
| Understander | claude-sonnet-4-6  | Multimodal product analysis    |
| Copywriter   | claude-opus-4-7    | Brand storyline (long-form)    |
| Localizer    | claude-sonnet-4-6  | 8-language parallel adaptation |
| Reviewer     | claude-sonnet-4-6  | Cultural compliance QA         |

Edit `config/settings.yaml` to customize models, temperature, and retry settings.

### CMS Integration

Set `CMS_WEBHOOK_URL` and `CMS_API_KEY` in `.env` to push content directly to your CMS. Otherwise, outputs are saved as local files.

## Testing

```bash
# Unit tests (no API key needed)
pytest tests/ -v -k "not integration"

# Full integration test (requires ANTHROPIC_API_KEY)
pytest tests/ -v
```

## License

MIT
