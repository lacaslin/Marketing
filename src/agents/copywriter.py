"""Core Copywriter Agent — generates master brand storyline in English."""

import json
from typing import Any

from src.agents.base import BaseAgent
from src.models.content import BrandStoryline
from src.models.product import ProductProfile
from src.utils.logger import log


COPYWRITER_SYSTEM_PROMPT = """You are a world-class e-commerce copywriter specializing in cross-border brand storytelling. You create compelling, emotionally resonant product narratives that work across cultures.

**Your Task:**
Given a detailed product profile, craft a master brand storyline in English that will serve as the canonical source for all translations into 8 languages.

**Guidelines:**
- Write in clear, evocative English that translates well
- Avoid idioms that don't cross cultures (e.g., "knock it out of the park", "home run")
- Focus on universal human desires: quality, belonging, self-improvement, convenience
- Headlines should be short, punchy, and emotionally engaging
- The brand story paragraph should connect the product to a lifestyle aspiration
- Bullet points should highlight benefits, not just features
- Each USP angle should target a different customer pain point or desire

**Output Format:** Return ONLY valid JSON:
{
  "product_name": "Canonical English product name",
  "brand_voice": "e.g., warm and aspirational with a tech-forward edge",
  "headlines": ["headline 1", "headline 2", "headline 3", "headline 4", "headline 5"],
  "story_paragraph": "2-3 sentence brand story with emotional hook",
  "usp_angles": ["angle 1: feature + benefit + emotion", "angle 2", "angle 3"],
  "bullet_points": ["bullet 1 - benefit focused", "bullet 2", "bullet 3", "bullet 4", "bullet 5"],
  "call_to_action": "Compelling CTA text",
  "tone_notes": "Notes for localizers: which tone elements to preserve vs adapt"
}"""


class CopywriterAgent(BaseAgent):

    def system_prompt(self) -> str:
        return COPYWRITER_SYSTEM_PROMPT

    async def run(self, profile: ProductProfile, brand_guidelines: str = "") -> BrandStoryline:
        """Generate a master brand storyline from the product profile."""

        profile_json = profile.model_dump_json(indent=2, exclude_none=True)
        prompt = f"""**Product Profile:**
```json
{profile_json}
```

**Brand Guidelines:**
{brand_guidelines or "Use a premium, modern brand voice suitable for global e-commerce."}

Generate the master brand storyline based on this profile."""

        log.info(f"[Copywriter] Generating brand storyline for '{profile.name_en}'")
        response = await self._call_llm(prompt, max_tokens_override=4096)
        data = self._parse_json(response)
        storyline = BrandStoryline(**data)
        log.info(f"[Copywriter] Generated {len(storyline.headlines)} headlines, "
                 f"{len(storyline.bullet_points)} bullets, {len(storyline.usp_angles)} USP angles")
        return storyline

    @staticmethod
    def _parse_json(response: str) -> dict[str, Any]:
        response = response.strip()
        if response.startswith("```"):
            lines = response.split("\n")
            response = "\n".join(lines[1:-1])
        return json.loads(response)
