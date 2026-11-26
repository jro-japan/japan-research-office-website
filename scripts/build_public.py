#!/usr/bin/env python3
"""Build a static deploy artifact from an explicit public-file allowlist."""
from pathlib import Path
import shutil

ROOT = Path(__file__).resolve().parents[1]
DIST = ROOT / "dist"
PAGES = (
    "index.html", "ja/index.html", "services.html", "methodology.html",
    "quality.html", "faq.html", "about.html", "contact.html", "privacy.html",
    "terms.html", "accessibility.html", "research-products.html",
    "research-library.html", "pricing.html",
)
PUBLIC_FILES = PAGES + (
    "404.html", "styles.css", "robots.txt", "sitemap.xml", "llms.txt",
    "site.webmanifest", "_headers", "_redirects",
    ".well-known/security.txt", ".well-known/mta-sts.txt",
    "assets/img/favicon.svg", "assets/img/apple-touch-icon.png",
    "assets/img/og-image.png", "assets/img/logo.svg",
)

def build():
    # Fail before touching the output if any input is absent or is a symlink.
    for rel in PUBLIC_FILES:
        src = ROOT / rel
        if not src.is_file() or src.resolve() != src:
            raise ValueError(f"Missing or unsafe public file: {rel}")
    if DIST.is_symlink():
        raise ValueError("Refusing symlink dist")
    if DIST.exists():
        shutil.rmtree(DIST)
    DIST.mkdir()
    for rel in PUBLIC_FILES:
        dest = DIST / rel
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ROOT / rel, dest)
    actual = {p.relative_to(DIST).as_posix() for p in DIST.rglob("*") if p.is_file()}
    if actual != set(PUBLIC_FILES):
        raise ValueError(f"Unexpected artifact contents: {actual ^ set(PUBLIC_FILES)}")
    print(f"Public build: {len(actual)} allowlisted files, {len(PAGES)} indexed pages")
    return DIST

if __name__ == "__main__":
    build()
