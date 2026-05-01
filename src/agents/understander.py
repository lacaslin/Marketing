"""Multimodal Understanding Agent — extracts product features from images + Chinese text."""

import json
from typing import Any

from src.agents.base import BaseAgent
from src.models.product import ProductProfile, ExtractedFeature
from src.utils.image import load_images
from src.utils.logger import log


UNDERSTANDER_SYSTEM_PROMPT = """You are a senior product analyst for a global e-commerce company. Your role is to analyze product images and Chinese text descriptions, then produce a comprehensive, structured product profile in English.

**Your Task:**
1. Analyze the product images carefully — identify colors, materials, textures, shape, size cues, packaging, and use context
2. Read the Chinese product specifications and extract key technical details
3. Merge visual and textual insights into unified selling points
4. Identify the design style, target use scenarios, and aesthetic
5. Generate seed SEO keywords in both English and Chinese

**Output Format:** Return ONLY valid JSON matching this schema:
{
  "name_en": "English product name",
  "name_zh": "original Chinese name",
  "category": "product category",
  "visual_features": [{"label": "feature name", "value": "description", "confidence": "high|medium|low", "source": "image"}],
  "text_features": [{"label": "feature name", "value": "description", "confidence": "high|medium|low", "source": "text"}],
  "key_selling_points": ["point 1", "point 2", "point 3", "point 4", "point 5"],
  "color_variants": ["color1", "color2"],
  "use_scenarios": ["scenario 1", "scenario 2"],
  "material_notes": "material and build quality description",
  "design_style": "design aesthetic description",
  "seed_keywords_en": ["keyword1", "keyword2", "keyword3", "keyword4", "keyword5"],
  "seed_keywords_zh": ["关键词1", "关键词2", "关键词3", "关键词4", "关键词5"]
}

Be specific and factual. Do not hallucinate features not visible in the images or mentioned in the text.
If you cannot determine something, use an empty string or empty list."""


class UnderstanderAgent(BaseAgent):

    def system_prompt(self) -> str:
        return UNDERSTANDER_SYSTEM_PROMPT

    async def run(
        self,
        name: str = "",
        specs: str = "",
        price: str = "",
        features: list[str] | None = None,
        category: str = "",
        brand: str = "",
        image_paths: list[str] | None = None,
    ) -> ProductProfile:
        """Extract product profile from Chinese text + product images."""
        features = features or []
        image_paths = image_paths or []

        text_block = f"""**Product Name (Chinese):** {name}
**Category:** {category}
**Brand:** {brand}
**Specifications:** {specs}
**Price:** {price}
**Key Features:** {", ".join(features) if features else "N/A"}"""

        if image_paths:
            log.info(f"[Understander] Analyzing {len(image_paths)} image(s) for '{name}'")
            image_blocks = load_images(image_paths)
            content = [*image_blocks, {"type": "text", "text": text_block}]
        else:
            log.info(f"[Understander] Text-only analysis for '{name}' (no images provided)")
            content = text_block

        response = await self._call_llm(content)
        data = self._parse_json(response)
        profile = ProductProfile(**data)
        log.info(f"[Understander] Extracted {len(profile.key_selling_points)} selling points, "
                 f"{len(profile.visual_features)} visual features, {len(profile.text_features)} text features")
        return profile

    @staticmethod
    def _parse_json(response: str) -> dict[str, Any]:
        response = response.strip()
        if response.startswith("```"):
            lines = response.split("\n")
            response = "\n".join(lines[1:-1])
        return json.loads(response)
