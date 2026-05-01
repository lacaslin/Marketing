"""Product-related data models for the content factory pipeline."""

from pydantic import BaseModel, Field


class ProductInput(BaseModel):
    """Raw product input from the user (Chinese)."""
    name: str = Field(..., description="Product name in Chinese")
    specs: str = Field(default="", description="Product specifications/parameters")
    price: str = Field(default="", description="Price range or MSRP")
    features: list[str] = Field(default_factory=list, description="Key product features/bullet points")
    category: str = Field(default="", description="Product category")
    brand: str = Field(default="", description="Brand name")
    target_audience: str = Field(default="", description="Target audience description")


class ExtractedFeature(BaseModel):
    """A single extracted product feature from multimodal analysis."""
    label: str = Field(..., description="Feature name (English)")
    value: str = Field(..., description="Feature value/description")
    confidence: str = Field(default="high", description="Extraction confidence: high/medium/low")
    source: str = Field(default="text", description="Source: text or image")


class ProductProfile(BaseModel):
    """Enriched product profile after multimodal understanding."""
    name_en: str = Field(..., description="Product name translated to English")
    name_zh: str = Field(..., description="Original Chinese product name")
    category: str = Field(default="", description="Product category")

    # Visual attributes extracted from images
    visual_features: list[ExtractedFeature] = Field(default_factory=list)
    # Text-based features from specs
    text_features: list[ExtractedFeature] = Field(default_factory=list)

    # Unified selling points (merged from visual + text)
    key_selling_points: list[str] = Field(default_factory=list, description="Top 5 selling points in English")
    color_variants: list[str] = Field(default_factory=list, description="Available colors")
    use_scenarios: list[str] = Field(default_factory=list, description="Suggested use scenarios")
    material_notes: str = Field(default="", description="Material and build quality notes")
    design_style: str = Field(default="", description="Design aesthetic description")

    # SEO seeds
    seed_keywords_en: list[str] = Field(default_factory=list, description="English seed keywords for SEO")
    seed_keywords_zh: list[str] = Field(default_factory=list, description="Chinese seed keywords for SEO")
