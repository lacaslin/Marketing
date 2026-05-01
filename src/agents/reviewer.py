"""Cultural QA Review Agent — checks localized content for taboos and sensitivities."""

import json
from typing import Any

from src.agents.base import BaseAgent
from src.models.content import LocalizedContent, ReviewResult, ReviewIssue
from src.utils.logger import log


# Cultural taboo rules per locale for the system prompt
CULTURAL_RULES = {
    "fr": """
- No literal translations of English idioms (French consumers find this off-putting)
- Avoid overly aggressive sales language (French market prefers understated elegance)
- Check for correct use of tu/vous form (use "vous" for e-commerce)
- No references to competitor brands
- Verify product claims comply with DGCCRF (French consumer protection) norms
- Colors: purple can be associated with mourning in some regions""",
    "de": """
- Strict truth-in-advertising compliance (German law is very strict)
- Avoid superlatives without proof ("best", "number one" require evidence)
- No exaggerated marketing claims (Germans value factual accuracy)
- Data privacy references must be careful (GDPR sensitivity)
- Colors: avoid overuse of red (political association)
- Numbers: 88 is taboo (neo-Nazi association)""",
    "es": """
- Avoid religious references or imagery in marketing
- Be mindful of regional variations (Castilian vs. Latin American Spanish)
- Time references: "mañana" culture stereotype is offensive
- Family-centric messaging resonates well, but avoid stereotypes
- Colors: no strong taboos, but yellow associated with bad luck in theater
- Check for bullfighting references (controversial in modern Spain)""",
    "ja": """
- Honorific language (keigo) must be appropriate for the product category
- Number 4 (shi) and 9 (ku) are unlucky — avoid in pricing and quantities
- Colors: white is for funerals, avoid in celebratory contexts
- No direct comparisons to competitors (considered rude)
- Check for correct use of katakana for foreign loanwords
- Seasonal references must match current Japanese season precisely""",
    "ko": """
- Honorific levels must be consistent (-합니다 style for e-commerce)
- Number 4 is unlucky (sa = death)
- Avoid red names (associated with death)
- No references to Japan that could be politically sensitive
- Check for proper measurement units (metric system)
- Korean consumers value detailed specs and social proof""",
    "pt": """
- Distinguish between Brazilian vs. European Portuguese based on target market
- Avoid religious references in marketing
- Colors: avoid purple for non-luxury products (funeral association in some regions)
- Brazilian market: informal tone acceptable; Portugal: more formal
- Check for false friends with Spanish (do not mix languages)
- Soccer/football references: avoid club rivalries""",
    "it": """
- Avoid stereotypes about Italian culture (mafia, gestures, "mamma mia")
- Number 17 is unlucky (XVII anagram = VIXI = "I lived" = death)
- Food products: Italians are very protective of culinary tradition
- Fashion/apparel: avoid comparing to luxury brands unless warranted
- Check for correct use of formal Lei vs. informal tu
- Colors: no strong taboos, but purple associated with funerals in some regions""",
    "ar": """
- CRITICAL: No references to alcohol, pork, gambling, or dating
- Respect Islamic values throughout all content
- Images showing women must respect hijab/modesty norms
- Avoid the "evil eye" hand gesture or references
- Numbers: be mindful of lucky/unlucky number associations by region
- Right-to-left text layout considerations
- Use Hijri calendar references alongside Gregorian where relevant
- Family-centric messaging is highly valued
- Avoid political references to sensitive regional conflicts""",
}

REVIEWER_SYSTEM_PROMPT = """You are a cultural compliance expert for global e-commerce. Your job is to review localized marketing content for the {locale_name} market ({locale}) and flag any issues.

**Cultural Rules for {locale_name} Market:**
{cultural_rules}

**Review Checklist:**
1. **Taboo Check**: Any forbidden words, symbols, numbers, colors in the copy?
2. **Cultural Sensitivity**: Any stereotypes, offensive generalizations, or politically sensitive references?
3. **Compliance**: Does the content comply with local advertising regulations?
4. **Tone**: Does the tone match local consumer expectations for this platform?
5. **SEO**: Are keywords natural-sounding (not stuffed)?
6. **Translation Quality**: Any awkward phrasing that reveals it's AI-translated?

**Output Format:** Return ONLY valid JSON:
{{
  "passed": true or false,
  "issues": [
    {{
      "severity": "error" or "warning" or "suggestion",
      "category": "taboo" or "sensitivity" or "compliance" or "tone" or "seo",
      "description": "What the issue is",
      "location": "Where in the content (title/description/bullets/story)",
      "suggestion": "How to fix it"
    }}
  ],
  "risk_score": 0.0 to 1.0,
  "reviewer_notes": "Overall assessment in 1-2 sentences"
}}

Risk score: 0.0 = perfectly clean, 0.3 = minor suggestions, 0.6 = concerning issues, 0.8+ = do not publish.

Only flag real issues. Do not be overly strict — minor tone preferences are "suggestions", not "errors"."""


class ReviewAgent(BaseAgent):

    def system_prompt(self) -> str:
        return "You are a cultural compliance expert. See instructions in the user message."

    async def run(self, content: LocalizedContent) -> ReviewResult:
        """Review localized content for cultural and compliance issues."""
        locale = content.locale
        cultural_rules = CULTURAL_RULES.get(locale, "No specific cultural rules defined for this locale. Apply general cross-cultural marketing best practices.")
        locale_name = _locale_name(locale)

        system_prompt = REVIEWER_SYSTEM_PROMPT.format(
            locale=locale,
            locale_name=locale_name,
            cultural_rules=cultural_rules,
        )

        content_json = content.model_dump_json(indent=2, exclude_none=True)
        prompt = f"""Review this localized content for the {locale_name} market:

**Content to Review:**
```json
{content_json}
```

Perform a thorough cultural compliance check and return the review result."""

        log.info(f"[Review:{locale}:{content.platform}] Reviewing content for cultural compliance")
        response = await self._call_llm(prompt, system_override=system_prompt, max_tokens_override=1500)
        data = self._parse_json(response)
        result = ReviewResult(locale=locale, platform=content.platform, **data)
        status = "PASSED" if result.passed else "FAILED"
        log.info(f"[Review:{locale}:{content.platform}] {status} — risk={result.risk_score:.2f}, issues={len(result.issues)}")
        return result

    @staticmethod
    def _parse_json(response: str) -> dict[str, Any]:
        response = response.strip()
        if response.startswith("```"):
            lines = response.split("\n")
            response = "\n".join(lines[1:-1])
        return json.loads(response)


def _locale_name(locale: str) -> str:
    names = {"fr": "French", "de": "German", "es": "Spanish", "ja": "Japanese", "ko": "Korean", "pt": "Portuguese", "it": "Italian", "ar": "Arabic"}
    return names.get(locale, locale.upper())
