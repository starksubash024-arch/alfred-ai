"""
components/assets_loader.py — Loads local graphic assets as Base64 data URIs
for offline, zero-dependency visual rendering in Streamlit.
"""

import base64
from pathlib import Path
from functools import lru_cache

ASSETS_DIR = Path(__file__).parent.parent / "assets"

_MIME_TYPES = {
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".webp": "image/webp",
    ".svg": "image/svg+xml",
}

@lru_cache(maxsize=32)
def get_asset_uri(asset_name: str) -> str:
    """Return base64 data URI for an asset file."""
    p = ASSETS_DIR / asset_name
    if not p.exists():
        return ""
    mime = _MIME_TYPES.get(p.suffix.lower(), "image/png")
    b64 = base64.b64encode(p.read_bytes()).decode("utf-8")
    return f"data:{mime};base64,{b64}"

