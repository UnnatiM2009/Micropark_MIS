"""
Finds the logo to display.

Drop a file named logo.png (or .jpg, .svg, .webp) into app/static/img/ and the
dashboard uses it straight away. Nothing else needs changing. If no such file
is there, it falls back to the drawn version that ships with the project.
"""

from pathlib import Path

IMG_DIR = Path(__file__).resolve().parent / "static" / "img"

# checked in this order, so a PNG beats a JPG if both are present
PREFERRED = ["logo.png", "logo.svg", "logo.jpg", "logo.jpeg", "logo.webp", "logo.gif"]
FALLBACK = "logo-fallback.svg"

MIME = {
    ".png": "image/png",
    ".svg": "image/svg+xml",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".webp": "image/webp",
    ".gif": "image/gif",
}

ACCEPTED = tuple(MIME.keys())


def logo_path() -> Path:
    for name in PREFERRED:
        candidate = IMG_DIR / name
        if candidate.exists() and candidate.stat().st_size > 0:
            return candidate
    return IMG_DIR / FALLBACK


def logo_mime(path: Path | None = None) -> str:
    path = path or logo_path()
    return MIME.get(path.suffix.lower(), "application/octet-stream")


def using_fallback() -> bool:
    return logo_path().name == FALLBACK
