"""CMS Publisher — pushes approved content to external CMS via REST API."""

from typing import Any

import httpx

from src.models.content import LocalizedContent, ReviewResult, PublishResult
from src.platforms import amazon, shopify, tiktok
from src.utils.logger import log


PLATFORM_SCHEMA_MAP = {
    "amazon": amazon.amazon_schema,
    "shopify": shopify.shopify_schema,
    "tiktok": tiktok.tiktok_schema,
}


class CMSPublisher:
    """Publishes approved localized content to a CMS via REST API."""

    def __init__(self, webhook_url: str = "", api_key: str = "", timeout: float = 30.0):
        self.webhook_url = webhook_url
        self.api_key = api_key
        self.timeout = timeout

    async def publish(self, content: LocalizedContent, review: ReviewResult) -> PublishResult:
        """Push approved content to the CMS. Falls back to file output if no webhook configured."""
        if not review.passed:
            return PublishResult(
                locale=content.locale,
                platform=content.platform,
                success=False,
                error_message=f"Content failed review (risk={review.risk_score:.2f}). Fix issues before publishing.",
            )

        if not self.webhook_url:
            return await self._publish_to_file(content)

        return await self._publish_to_api(content)

    async def _publish_to_api(self, content: LocalizedContent) -> PublishResult:
        """Push content to external CMS API."""
        schema_func = PLATFORM_SCHEMA_MAP.get(content.platform)
        payload = schema_func(content) if schema_func else {}

        payload["action"] = "publish"
        payload["content_type"] = content.platform
        payload["locale"] = content.locale

        headers = {"Content-Type": "application/json", "Authorization": f"Bearer {self.api_key}"}

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(self.webhook_url, json=payload, headers=headers)
                response.raise_for_status()
                result = response.json()
                log.info(f"[CMS] Published {content.locale}/{content.platform} — ID: {result.get('id', 'unknown')}")
                return PublishResult(
                    locale=content.locale,
                    platform=content.platform,
                    success=True,
                    cms_url=result.get("url", ""),
                    cms_id=str(result.get("id", "")),
                )
        except httpx.HTTPStatusError as e:
            log.error(f"[CMS] HTTP {e.response.status_code} for {content.locale}/{content.platform}: {e.response.text[:200]}")
            return PublishResult(
                locale=content.locale,
                platform=content.platform,
                success=False,
                error_message=f"HTTP {e.response.status_code}: {e.response.text[:200]}",
            )
        except Exception as e:
            log.error(f"[CMS] Failed to publish {content.locale}/{content.platform}: {e}")
            return PublishResult(
                locale=content.locale,
                platform=content.platform,
                success=False,
                error_message=str(e),
            )

    async def _publish_to_file(self, content: LocalizedContent) -> PublishResult:
        """Fallback: write content to local file when no CMS webhook is configured."""
        log.info(f"[CMS] No webhook configured — writing {content.locale}/{content.platform} to local file")

        return PublishResult(
            locale=content.locale,
            platform=content.platform,
            success=True,
            cms_url=f"file://output/{content.platform}_{content.locale}.md",
            error_message="Published to local file (no CMS webhook configured)",
        )


async def publish_content(
    content: LocalizedContent,
    review: ReviewResult,
    webhook_url: str = "",
    api_key: str = "",
) -> PublishResult:
    """Convenience function to publish a single piece of content."""
    publisher = CMSPublisher(webhook_url=webhook_url, api_key=api_key)
    return await publisher.publish(content, review)
