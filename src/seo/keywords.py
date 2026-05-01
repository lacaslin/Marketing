"""SEO keyword database — provides locale-specific long-tail keywords for product categories."""

# Keyword map: locale -> category -> {primary: [], long_tail: []}
# These are curated seed keywords; LLM will naturally integrate and expand them.

KEYWORD_DB = {
    "fr": {
        "default": {
            "primary": ["acheter en ligne", "meilleur prix", "livraison rapide"],
            "long_tail": [
                "pas cher livraison gratuite",
                "meilleur rapport qualité prix",
                "avis clients France",
                "promo code reduc",
                "nouveau produit tendance",
            ],
        },
        "electronics": {
            "primary": ["high-tech pas cher", "gadget innovant"],
            "long_tail": ["test et avis 2026", "comparatif meilleur", "guide d'achat complet"],
        },
        "fashion": {
            "primary": ["mode tendance", "vetement stylé"],
            "long_tail": ["look du jour", "tenue de soirée", "mode française boutique en ligne"],
        },
    },
    "de": {
        "default": {
            "primary": ["online kaufen", "bester preis", "schnelle lieferung"],
            "long_tail": [
                "günstig kaufen",
                "preis-leistungs-verhältnis",
                "kundenbewertungen",
                "angebote und deals",
                "neuheiten 2026",
            ],
        },
        "electronics": {
            "primary": ["elektronik günstig", "technik neuheiten"],
            "long_tail": ["testbericht deutsch", "vergleich testsieger", "kaufberatung 2026"],
        },
    },
    "es": {
        "default": {
            "primary": ["comprar online", "mejor precio", "envío rápido"],
            "long_tail": [
                "barato envío gratis",
                "mejor calidad precio",
                "opiniones clientes",
                "ofertas y descuentos",
                "nuevo producto 2026",
            ],
        },
        "electronics": {
            "primary": ["electrónica barata", "gadget innovador"],
            "long_tail": ["análisis y review", "comparativa mejores", "guía de compra"],
        },
    },
    "ja": {
        "default": {
            "primary": ["オンライン購入", "最安値", "即日配送"],
            "long_tail": [
                "口コミ評価",
                "コスパ最強",
                "ランキング上位",
                "おすすめ人気",
                "2026年最新",
            ],
        },
        "electronics": {
            "primary": ["最新ガジェット", "テクノロジー"],
            "long_tail": ["レビュー評価", "比較おすすめ", "購入ガイド"],
        },
    },
    "ko": {
        "default": {
            "primary": ["온라인 구매", "최저가", "빠른 배송"],
            "long_tail": [
                "가성비 최고",
                "후기 좋은",
                "인기 순위",
                "할인 정보",
                "2026년 신상품",
            ],
        },
        "electronics": {
            "primary": ["전자기기 추천", "가성비 가젯"],
            "long_tail": ["리뷰 비교", "사용 후기", "구매 가이드"],
        },
    },
    "pt": {
        "default": {
            "primary": ["comprar online", "melhor preço", "entrega rápida"],
            "long_tail": [
                "barato frete grátis",
                "melhor custo benefício",
                "avaliações clientes",
                "promoção desconto",
                "lançamento 2026",
            ],
        },
    },
    "it": {
        "default": {
            "primary": ["acquista online", "miglior prezzo", "spedizione veloce"],
            "long_tail": [
                "economico spedizione gratuita",
                "miglior rapporto qualità prezzo",
                "recensioni clienti",
                "offerte e sconti",
                "novità 2026",
            ],
        },
    },
    "ar": {
        "default": {
            "primary": ["شراء اون لاين", "أفضل سعر", "توصيل سريع"],
            "long_tail": [
                "رخيص توصيل مجاني",
                "أفضل جودة وسعر",
                "تقييمات العملاء",
                "عروض وخصومات",
                "منتج جديد 2026",
            ],
        },
    },
}


# Platform-specific keyword modifiers
PLATFORM_KEYWORDS = {
    "amazon": {
        "fr": ["amazon france", "prime livraison", "meilleure vente amazon"],
        "de": ["amazon deutschland", "prime versand", "amazon Bestseller"],
        "es": ["amazon españa", "envío prime", "más vendido amazon"],
        "ja": ["amazon japan", "プライム配送", "ベストセラー"],
        "ko": ["아마존 직구", "프라임 배송", "베스트셀러"],
        "pt": ["amazon brasil", "envio prime", "mais vendidos"],
        "it": ["amazon italia", "spedizione prime", "bestseller amazon"],
        "ar": ["امازون", "توصيل برايم", "الاكثر مبيعاً"],
    },
    "shopify": {
        "fr": ["boutique en ligne", "e-commerce france", "site de vente"],
        "de": ["online shop", "e-commerce deutschland", "webshop"],
        "es": ["tienda online", "ecommerce españa", "compra online"],
        "ja": ["オンラインショップ", "通販サイト", "公式ストア"],
        "ko": ["온라인 스토어", "공식 쇼핑몰", "직구 사이트"],
    },
    "tiktok": {
        "fr": ["tiktok made me buy it", "tiktok france", "viral"],
        "de": ["tiktok germany", "tiktok made me buy it", "viral video"],
        "es": ["tiktok españa", "tiktok me compró", "viral"],
        "ja": ["tiktok japan", "tiktok購入品", "バイラル"],
        "ko": ["틱톡 추천", "틱톡 핫템", "바이럴"],
    },
}


def get_seo_keywords(locale: str, product_name: str = "", category: str = "default") -> dict:
    """Get SEO keywords for a specific locale and product category."""
    locale_data = KEYWORD_DB.get(locale, KEYWORD_DB.get("fr", {}))
    cat_data = locale_data.get(category, locale_data.get("default", {}))

    return {
        "primary": cat_data.get("primary", []),
        "long_tail": cat_data.get("long_tail", []),
    }


def get_platform_keywords(locale: str, platform: str, product_name: str = "") -> list[str]:
    """Get platform-specific keywords for a locale."""
    platform_data = PLATFORM_KEYWORDS.get(platform, {})
    return platform_data.get(locale, platform_data.get("fr", []))
