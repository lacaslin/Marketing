"""Pipeline orchestrator — coordinates the 5-stage Agent workflow."""

import asyncio
import json
import time
from pathlib import Path
from typing import Any

from src.agents.base import BaseAgent
from src.agents.understander import UnderstanderAgent
from src.agents.copywriter import CopywriterAgent
from src.agents.localizer import LocalizeAgent
from src.agents.reviewer import ReviewAgent
from src.cms.publisher import publish_content
from src.config import Config
from src.models.product import ProductInput, ProductProfile
from src.models.content import (
    BrandStoryline,
    LocalizedContent,
    ReviewResult,
    PublishResult,
    PipelineResult,
    ContentStatus,
)
from src.platforms import amazon, shopify, tiktok
from src.utils.logger import log


PLATFORM_FORMATTERS = {
    "amazon": amazon.format_amazon_listing,
    "shopify": shopify.format_shopify_page,
    "tiktok": tiktok.format_tiktok_content,
}


class PipelineOrchestrator:
    """Orchestrates the 5-stage content factory pipeline."""

    def __init__(self, cfg: Config):
        self.cfg = cfg
        self.retry = cfg.retry_config

    # ------------------------------------------------------------------ Stage 1

    async def stage_understand(self, product: ProductInput, image_paths: list[str] | None = None) -> ProductProfile:
        ac = self.cfg.agent_config("understander")
        agent = UnderstanderAgent(
            api_key=self.cfg.api_key,
            model=ac["model"],
            max_tokens=ac["max_tokens"],
            temperature=ac["temperature"],
            **self.retry,
        )
        return await agent.run(
            name=product.name,
            specs=product.specs,
            price=product.price,
            features=product.features,
            category=product.category,
            brand=product.brand,
            image_paths=image_paths or [],
        )

    # ------------------------------------------------------------------ Stage 2

    async def stage_copywrite(self, profile: ProductProfile) -> BrandStoryline:
        ac = self.cfg.agent_config("copywriter")
        agent = CopywriterAgent(
            api_key=self.cfg.api_key,
            model=ac["model"],
            max_tokens=ac["max_tokens"],
            temperature=ac["temperature"],
            **self.retry,
        )
        brand_guidelines = json.dumps(self.cfg.brand_defaults, ensure_ascii=False)
        return await agent.run(profile, brand_guidelines=brand_guidelines)

    # ------------------------------------------------------------------ Stage 3

    async def stage_localize(
        self,
        storyline: BrandStoryline,
        locales: list[str],
        platforms: list[str],
    ) -> list[LocalizedContent]:
        """Run all locale x platform combinations in parallel."""
        ac = self.cfg.agent_config("localizer")
        tasks = []
        for locale in locales:
            for platform in platforms:
                agent = LocalizeAgent(
                    locale=locale,
                    platform=platform,
                    api_key=self.cfg.api_key,
                    model=ac["model"],
                    max_tokens=ac["max_tokens"],
                    temperature=ac["temperature"],
                    **self.retry,
                )
                tasks.append(_safe_localize(agent, storyline, locale, platform))

        results = await asyncio.gather(*tasks, return_exceptions=True)
        localized = []
        for r in results:
            if isinstance(r, Exception):
                log.error(f"[Localize] Task failed: {r}")
            else:
                localized.append(r)
        return localized

    # ------------------------------------------------------------------ Stage 4

    async def stage_review(self, contents: list[LocalizedContent]) -> list[tuple[LocalizedContent, ReviewResult]]:
        """Review all localized content in parallel."""
        ac = self.cfg.agent_config("reviewer")
        tasks = []
        for c in contents:
            agent = ReviewAgent(
                api_key=self.cfg.api_key,
                model=ac["model"],
                max_tokens=ac["max_tokens"],
                temperature=ac["temperature"],
                **self.retry,
            )
            tasks.append(_safe_review(agent, c))

        results = await asyncio.gather(*tasks, return_exceptions=True)
        pairs = []
        for i, r in enumerate(results):
            if isinstance(r, Exception):
                log.error(f"[Review] Task failed: {r}")
                pairs.append((contents[i], ReviewResult(
                    locale=contents[i].locale,
                    platform=contents[i].platform,
                    passed=False,
                    reviewer_notes=f"Review agent error: {r}",
                )))
            else:
                pairs.append((contents[i], r))
        return pairs

    # ------------------------------------------------------------------ Stage 5

    async def stage_publish(self, reviewed: list[tuple[LocalizedContent, ReviewResult]]) -> list[PublishResult]:
        """Publish all approved content in parallel."""
        tasks = []
        for content, review in reviewed:
            if review.passed:
                content.status = ContentStatus.APPROVED
            else:
                content.status = ContentStatus.REJECTED
            tasks.append(publish_content(
                content, review,
                webhook_url=self.cfg.cms_webhook_url,
                api_key=self.cfg.cms_api_key,
            ))

        results = await asyncio.gather(*tasks, return_exceptions=True)
        published = []
        for i, r in enumerate(results):
            if isinstance(r, Exception):
                log.error(f"[Publish] Task failed: {r}")
                published.append(PublishResult(
                    locale=reviewed[i][0].locale,
                    platform=reviewed[i][0].platform,
                    success=False,
                    error_message=str(r),
                ))
            else:
                content = reviewed[i][0]
                if r.success:
                    content.status = ContentStatus.PUBLISHED
                else:
                    content.status = ContentStatus.FAILED
                published.append(r)
        return published

    # ------------------------------------------------------------------ Full Pipeline

    async def run(
        self,
        product: ProductInput,
        image_paths: list[str] | None = None,
        locales: list[str] | None = None,
        platforms: list[str] | None = None,
    ) -> PipelineResult:
        """Execute the full 5-stage pipeline."""
        locales = locales or list(self.cfg.languages.keys())
        platforms = platforms or list(self.cfg.platforms.keys())
        t0 = time.monotonic()
        errors: list[str] = []

        log.info(f"Starting pipeline for '{product.name}' → {len(locales)} locales × {len(platforms)} platforms")

        # Stage 1: Understand
        log.info("─" * 50)
        log.info("Stage 1/5: Multimodal Understanding")
        try:
            profile = await self.stage_understand(product, image_paths)
        except Exception as e:
            log.error(f"Stage 1 failed: {e}")
            return PipelineResult(product_name=product.name, errors=[f"Stage1: {e}"], total_time_seconds=time.monotonic() - t0)

        # Stage 2: Copywrite
        log.info("─" * 50)
        log.info("Stage 2/5: Brand Storyline Generation")
        try:
            storyline = await self.stage_copywrite(profile)
        except Exception as e:
            log.error(f"Stage 2 failed: {e}")
            return PipelineResult(product_name=product.name, profile=profile.model_dump(), errors=[f"Stage2: {e}"], total_time_seconds=time.monotonic() - t0)

        # Stage 3: Localize (parallel)
        log.info("─" * 50)
        log.info(f"Stage 3/5: Localization — {len(locales)} locales × {len(platforms)} platforms = {len(locales) * len(platforms)} tasks")
        localized = await self.stage_localize(storyline, locales, platforms)
        if not localized:
            errors.append("Stage3: All localization tasks failed")

        # Stage 4: Review (parallel)
        log.info("─" * 50)
        log.info(f"Stage 4/5: Cultural QA Review — {len(localized)} items")
        reviewed = await self.stage_review(localized)

        passed_count = sum(1 for _, r in reviewed if r.passed)
        log.info(f"Review complete: {passed_count}/{len(reviewed)} passed")

        # Stage 5: Publish (parallel)
        log.info("─" * 50)
        log.info(f"Stage 5/5: CMS Publishing — {passed_count} items")
        published = await self.stage_publish(reviewed)

        elapsed = time.monotonic() - t0
        pub_count = sum(1 for p in published if p.success)
        log.info(f"Pipeline complete in {elapsed:.1f}s — {pub_count}/{len(published)} published")

        return PipelineResult(
            product_name=product.name,
            profile=profile.model_dump(),
            storyline=storyline.model_dump(),
            localized=[c.model_dump() for c in localized],
            reviews=[r.model_dump() for _, r in reviewed],
            published=[p.model_dump() for p in published],
            errors=errors,
            total_time_seconds=elapsed,
        )


# ------------------------------------------------------------------ Helpers

async def _safe_localize(agent: LocalizeAgent, storyline: BrandStoryline, locale: str, platform: str) -> LocalizedContent:
    try:
        return await agent.run(storyline)
    except Exception as e:
        log.error(f"[Localize:{locale}:{platform}] Failed: {e}")
        raise


async def _safe_review(agent: ReviewAgent, content: LocalizedContent) -> ReviewResult:
    try:
        return await agent.run(content)
    except Exception as e:
        log.error(f"[Review:{content.locale}:{content.platform}] Failed: {e}")
        raise


# ------------------------------------------------------------------ Output helpers

def save_pipeline_output(result: PipelineResult, output_dir: Path) -> list[Path]:
    """Save all pipeline outputs to files. Returns list of file paths."""
    output_dir.mkdir(parents=True, exist_ok=True)
    files: list[Path] = []

    # Save full pipeline result as JSON
    result_path = output_dir / f"pipeline_result_{result.product_name[:30].replace(' ', '_')}.json"
    result_path.write_text(json.dumps(result.model_dump(), ensure_ascii=False, indent=2), encoding="utf-8")
    files.append(result_path)
    log.info(f"Saved pipeline result: {result_path}")

    # Save each localized content as formatted text
    for loc_data in result.localized:
        locale = loc_data.get("locale", "xx")
        platform = loc_data.get("platform", "unknown")

        # Reconstruct content object
        content = LocalizedContent(**loc_data)
        formatter = PLATFORM_FORMATTERS.get(platform)
        if formatter:
            formatted = formatter(content)
            file_path = output_dir / f"{platform}_{locale}.md"
            file_path.write_text(formatted, encoding="utf-8")
            files.append(file_path)

    return files
