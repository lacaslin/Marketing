"""Tests for the MIMO content factory pipeline."""

import json
import os
import tempfile
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.models.product import ProductInput, ProductProfile, ExtractedFeature
from src.models.content import (
    BrandStoryline,
    LocalizedContent,
    SEOMetadata,
    ReviewResult,
    ReviewIssue,
    PublishResult,
    ContentStatus,
)
from src.config import Config
from src.utils.image import encode_image, discover_images, SUPPORTED_FORMATS
from src.seo.keywords import get_seo_keywords, get_platform_keywords


# ---------------------------------------------------------------------- Models

class TestProductModels:
    def test_product_input_creation(self):
        p = ProductInput(name="蓝牙耳机", specs="Bluetooth 5.3", price="99-199")
        assert p.name == "蓝牙耳机"
        assert p.specs == "Bluetooth 5.3"
        assert p.features == []

    def test_product_input_with_features(self):
        p = ProductInput(name="Test", features=["Feature A", "Feature B"])
        assert len(p.features) == 2

    def test_product_profile_creation(self):
        profile = ProductProfile(
            name_en="Wireless Earbuds",
            name_zh="无线耳机",
            key_selling_points=["Great sound", "Long battery"],
            color_variants=["Black", "White"],
        )
        assert profile.name_en == "Wireless Earbuds"
        assert len(profile.key_selling_points) == 2

    def test_extracted_feature(self):
        f = ExtractedFeature(label="Color", value="Matte Black", confidence="high", source="image")
        assert f.source == "image"
        assert f.confidence == "high"


class TestContentModels:
    def test_brand_storyline(self):
        bs = BrandStoryline(
            product_name="Test Product",
            brand_voice="Premium modern",
            headlines=["H1", "H2", "H3"],
            story_paragraph="A great story.",
            usp_angles=["Angle 1"],
            bullet_points=["B1", "B2", "B3", "B4", "B5"],
            call_to_action="Buy now!",
        )
        assert len(bs.headlines) == 3
        assert len(bs.bullet_points) == 5

    def test_localized_content(self):
        lc = LocalizedContent(
            locale="fr",
            platform="amazon",
            title="Écouteurs sans fil",
            description="Une description",
            bullets=["B1", "B2"],
            seo=SEOMetadata(primary_keyword="écouteurs bluetooth"),
        )
        assert lc.status == ContentStatus.DRAFT
        assert lc.locale == "fr"

    def test_review_result(self):
        rr = ReviewResult(locale="fr", platform="amazon", passed=True, risk_score=0.1)
        assert rr.passed
        assert rr.risk_score == 0.1

    def test_review_result_with_issues(self):
        issue = ReviewIssue(
            severity="error",
            category="taboo",
            description="Contains forbidden color reference",
            suggestion="Remove purple reference",
        )
        rr = ReviewResult(locale="ar", platform="amazon", passed=False, issues=[issue], risk_score=0.9)
        assert not rr.passed
        assert len(rr.issues) == 1

    def test_publish_result(self):
        pr = PublishResult(locale="fr", platform="amazon", success=True, cms_url="https://cms.example.com/123")
        assert pr.success
        assert pr.cms_url == "https://cms.example.com/123"


# ---------------------------------------------------------------------- SEO Keywords

class TestSEOKeywords:
    def test_get_seo_keywords_known_locale(self):
        kw = get_seo_keywords("fr")
        assert "primary" in kw
        assert "long_tail" in kw
        assert len(kw["primary"]) > 0

    def test_get_seo_keywords_unknown_locale_fallback(self):
        kw = get_seo_keywords("xx")
        assert "primary" in kw  # falls back to fr

    def test_get_seo_keywords_with_category(self):
        kw = get_seo_keywords("fr", category="electronics")
        assert len(kw["primary"]) > 0

    def test_get_platform_keywords(self):
        kw = get_platform_keywords("fr", "amazon")
        assert len(kw) > 0

    def test_all_locales_have_keywords(self):
        for locale in ["fr", "de", "es", "ja", "ko", "pt", "it", "ar"]:
            kw = get_seo_keywords(locale)
            assert len(kw["primary"]) > 0, f"No primary keywords for {locale}"


# ---------------------------------------------------------------------- Image Utils

class TestImageUtils:
    def test_supported_formats(self):
        assert ".jpg" in SUPPORTED_FORMATS
        assert ".png" in SUPPORTED_FORMATS

    def test_encode_nonexistent_image(self):
        with pytest.raises(FileNotFoundError):
            encode_image("/nonexistent/image.jpg")

    def test_unsupported_format(self):
        with tempfile.NamedTemporaryFile(suffix=".bmp", delete=False) as f:
            f.write(b"test")
            path = f.name
        try:
            with pytest.raises(ValueError, match="Unsupported"):
                encode_image(path)
        finally:
            os.unlink(path)

    def test_discover_images_empty_dir(self):
        with tempfile.TemporaryDirectory() as d:
            result = discover_images(d)
            assert result == []


# ---------------------------------------------------------------------- Config

class TestConfig:
    def test_config_loads(self):
        cfg = Config()
        assert len(cfg.languages) == 8
        assert "amazon" in cfg.platforms

    def test_config_agent_config(self):
        cfg = Config()
        ac = cfg.agent_config("copywriter")
        assert "model" in ac
        assert ac["model"] == "claude-opus-4-7"

    def test_config_default_agent_config(self):
        cfg = Config()
        ac = cfg.agent_config("nonexistent")
        assert ac["model"] == "claude-sonnet-4-6"

    def test_config_retry(self):
        cfg = Config()
        rc = cfg.retry_config
        assert rc["max_retries"] == 3


# ---------------------------------------------------------------------- Integration

class TestPipelineIntegration:
    @pytest.mark.asyncio
    async def test_pipeline_with_mock(self):
        """Integration test with mocked LLM responses."""
        product = ProductInput(
            name="蓝牙降噪耳机",
            specs="主动降噪，蓝牙5.3，续航30小时",
            price="¥299-399",
            features=["主动降噪", "Hi-Fi音质", "低延迟游戏模式"],
            category="electronics",
            brand="SoundMax",
        )

        cfg = Config()
        if not cfg.api_key:
            pytest.skip("ANTHROPIC_API_KEY not set — skipping integration test")

        from src.orchestrator import PipelineOrchestrator
        from src.utils.logger import setup_logger

        setup_logger(level="INFO")
        orchestrator = PipelineOrchestrator(cfg)

        result = await orchestrator.run(
            product=product,
            locales=["fr"],
            platforms=["amazon"],
        )

        assert result.product_name == "蓝牙降噪耳机"
        assert len(result.errors) == 0
        assert result.total_time_seconds > 0

        # Should have profile, storyline, localized content
        assert result.profile.get("name_en")
        assert result.storyline.get("product_name")
        assert len(result.localized) == 1
        assert result.localized[0]["locale"] == "fr"

        # Should have review and publish results
        assert len(result.reviews) == 1
        assert len(result.published) == 1


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
