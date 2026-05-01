"""Image utilities: encoding, validation, and preprocessing for vision API."""

import base64
from pathlib import Path


SUPPORTED_FORMATS = {".jpg", ".jpeg", ".png", ".webp", ".gif"}
MAX_IMAGES = 5


def encode_image(image_path: str | Path) -> tuple[str, str]:
    """Read an image file and return (base64_string, media_type)."""
    path = Path(image_path)
    if not path.exists():
        raise FileNotFoundError(f"Image not found: {image_path}")

    suffix = path.suffix.lower()
    if suffix not in SUPPORTED_FORMATS:
        raise ValueError(f"Unsupported image format: {suffix}. Supported: {SUPPORTED_FORMATS}")

    media_type_map = {".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".png": "image/png", ".webp": "image/webp", ".gif": "image/gif"}
    media_type = media_type_map[suffix]

    data = path.read_bytes()
    b64 = base64.b64encode(data).decode("utf-8")
    return b64, media_type


def load_images(image_paths: list[str | Path]) -> list[dict]:
    """Load and encode multiple images for the vision API.

    Returns a list of dicts with keys: type, source (base64 data + media_type).
    Limits to MAX_IMAGES (5) images.
    """
    images = []
    for p in image_paths[:MAX_IMAGES]:
        b64, media_type = encode_image(p)
        images.append({
            "type": "image",
            "source": {
                "type": "base64",
                "media_type": media_type,
                "data": b64,
            },
        })
    return images


def discover_images(directory: str | Path) -> list[Path]:
    """Find all supported image files in a directory, sorted by name."""
    path = Path(directory)
    if not path.is_dir():
        raise NotADirectoryError(f"Not a directory: {directory}")

    images = []
    for ext in SUPPORTED_FORMATS:
        images.extend(path.glob(f"*{ext}"))
        images.extend(path.glob(f"*{ext.upper()}"))
    return sorted(images)
