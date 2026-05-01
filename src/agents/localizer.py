"""Localization Agent — adapts brand storyline for a specific locale and platform."""

import json
from typing import Any

from src.agents.base import BaseAgent
from src.models.content import BrandStoryline, LocalizedContent, SEOMetadata
from src.seo.keywords import get_seo_keywords, get_platform_keywords
from src.utils.logger import log


def _locale_name(locale: str) -> str:
    names = {"fr": "French", "de": "German", "es": "Spanish", "ja": "Japanese", "ko": "Korean", "pt": "Portuguese", "it": "Italian", "ar": "Arabic"}
    return names.get(locale, locale.upper())


def _platform_context(platform: str) -> str:
    contexts = {
        "amazon": "Amazon product listing. Optimize title for A9 algorithm, use benefit-rich bullet points, include backend search terms.",
        "shopify": "Shopify independent store product page. Focus on conversion-optimized description, brand storytelling, meta description for SEO.",
        "tiktok": "TikTok/Instagram social media campaign. Write a short video script (30-60 seconds) with hook, body, and CTA. Include trending-style caption and hashtags.",
    }
    return contexts.get(platform, f"{platform} product content")


LOCALIZER_SYSTEM_PROMPT = """You are a native {language} e-commerce copywriter and SEO specialist. Your task is to localize English product content into {language} for {platform_name}.

**Critical Requirements:**
1. Write like a NATIVE {language} internet user — use natural expressions, local slang where appropriate, and the tone real locals use online
2. NEVER produce literal translations — adapt idioms, cultural references, and emotional hooks for the {language}-speaking market
3. Embed the provided SEO keywords naturally into the copy (do NOT stuff them)
4. Follow the platform-specific format requirements exactly
5. Maintain the brand voice but adapt the expression style
6. For Arabic (ar): use Modern Standard Arabic with a warm, conversational tone suitable for Gulf market

**Platform-Specific Notes:**
{platform_notes}

**Output Format:** Return ONLY valid JSON:
{{
  "title": "Localized title with primary keyword",
  "description": "Full localized product description with natural keyword integration",
  "bullets": ["bullet 1", "bullet 2", "bullet 3", "bullet 4", "bullet 5"],
  "brand_story": "Localized brand story paragraph",
  "amazon_search_terms": "Backend search terms (only for amazon platform, otherwise empty)",
  "tiktok_script": "30-60 second video script with HOOK-BODY-CTA structure (only for tiktok platform, otherwise empty)",
  "tiktok_caption": "Engaging social caption (only for tiktok platform, otherwise empty)",
  "shopify_meta": "SEO meta description (only for shopify platform, otherwise empty)",
  "seo": {{
    "primary_keyword": "The single most important keyword for this locale",
    "secondary_keywords": ["keyword2", "keyword3", "keyword4", "keyword5"],
    "search_terms": ["backend term 1", "backend term 2", "backend term 3"],
    "hashtags": ["#tag1", "#tag2", "#tag3", "#tag4", "#tag5"],
    "meta_title": "SEO-optimized meta title",
    "meta_description": "SEO meta description for search engines"
  }},
  "hashtags": ["#Hashtag1", "#Hashtag2", "#Hashtag3"]
}}

The "hashtags" top-level field should contain platform-appropriate hashtags. For Amazon, use no hashtags (empty list)."""


class LocalizeAgent(BaseAgent):

    def __init__(self, locale: str, platform: str, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.locale = locale
        self.platform = platform

    def system_prompt(self) -> str:
        return LOCALIZER_SYSTEM_PROMPT.format(
            language=_locale_name(self.locale),
            platform_name=self.platform.upper(),
            platform_notes=_platform_context(self.platform),
        )

    async def run(self, storyline: BrandStoryline) -> LocalizedContent:
        """Localize the brand storyline for this agent's locale and platform."""
        seo_keywords = get_seo_keywords(self.locale, storyline.product_name)
        platform_kw = get_platform_keywords(self.locale, self.platform, storyline.product_name)

        storyline_json = storyline.model_dump_json(indent=2, exclude_none=True)
        prompt = f"""**Source Brand Storyline (English):**
```json
{storyline_json}
```

**Target Locale:** {self.locale} ({_locale_name(self.locale)})
**Target Platform:** {self.platform}

**SEO Keywords to embed naturally:**
- Primary: {", ".join(seo_keywords["primary"])}
- Long-tail: {", ".join(seo_keywords["long_tail"])}
- Platform-specific: {", ".join(platform_kw)}

Localize this content. Make it sound like it was written by a native {_locale_name(self.locale)} speaker who understands the local internet culture."""

        log.info(f"[Localize:{self.locale}:{self.platform}] Localizing '{storyline.product_name}'")
        response = await self._call_llm(prompt, max_tokens_override=3000)
        data = self._parse_json(response)
        content = LocalizedContent(locale=self.locale, platform=self.platform, **data)
        content.source_storyline_hash = self._hash_content(storyline.model_dump_json())
        log.info(f"[Localize:{self.locale}:{self.platform}] Done — title: '{content.title[:60]}...'")
        return content

    @staticmethod
    def _parse_json(response: str) -> dict[str, Any]:
        response = response.strip()
        if response.startswith("```"):
            lines = response.split("\n")
            response = "\n".join(lines[1:-1])
        return json.loads(response)
