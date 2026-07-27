#!/usr/bin/env python3
from pathlib import Path
import json
import sys
import xml.etree.ElementTree as ET
from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parents[1]
errors = []

required = [
    "index.html", "404.html", "robots.txt", "sitemap.xml",
    "site.webmanifest", "_headers", "_redirects", "netlify.toml",
    "llms.txt", ".well-known/mta-sts.txt", ".well-known/security.txt",
    "assets/css/site.css", "assets/js/site.js",
    "assets/img/logo.svg", "assets/img/favicon.svg",
    "assets/img/apple-touch-icon.png", "assets/img/og-image.png"
]

for rel in required:
    if not (ROOT / rel).exists():
        errors.append(f"Missing required file: {rel}")

html_files = sorted(ROOT.glob("*.html"))
if len(html_files) < 20:
    errors.append(f"Expected at least 20 HTML pages, found {len(html_files)}")

titles = {}
canonicals = {}

for path in html_files:
    soup = BeautifulSoup(path.read_text(encoding="utf-8"), "html.parser")
    title = soup.title.get_text(" ", strip=True) if soup.title else ""
    desc = soup.find("meta", attrs={"name": "description"})
    canonical = soup.find("link", rel="canonical")
    h1s = soup.find_all("h1")

    if not title:
        errors.append(f"{path.name}: missing title")
    if not desc or not desc.get("content", "").strip():
        errors.append(f"{path.name}: missing meta description")
    if not canonical or not canonical.get("href", "").strip():
        errors.append(f"{path.name}: missing canonical")
    if len(h1s) != 1:
        errors.append(f"{path.name}: expected one H1, found {len(h1s)}")
    if not soup.html or soup.html.get("lang") != "en":
        errors.append(f"{path.name}: html lang must be en")
    if not soup.find("meta", attrs={"property": "og:image"}):
        errors.append(f"{path.name}: missing og:image")
    if not soup.find("meta", attrs={"name": "twitter:card"}):
        errors.append(f"{path.name}: missing twitter:card")
    if not soup.find("link", rel="manifest"):
        errors.append(f"{path.name}: missing manifest")

    titles.setdefault(title, []).append(path.name)
    if canonical:
        canonicals.setdefault(canonical.get("href"), []).append(path.name)

    scripts = soup.find_all("script", attrs={"type": "application/ld+json"})
    if len(scripts) != 1:
        errors.append(f"{path.name}: expected one JSON-LD block, found {len(scripts)}")
    for script in scripts:
        try:
            payload = json.loads(script.string or script.get_text())
            if "@graph" not in payload:
                errors.append(f"{path.name}: JSON-LD does not contain @graph")
        except Exception as exc:
            errors.append(f"{path.name}: invalid JSON-LD: {exc}")

    for tag in soup.find_all(["a", "link", "script", "img"]):
        attr = "href" if tag.name in {"a", "link"} else "src"
        ref = tag.get(attr)
        if not ref or not ref.startswith("/") or ref.startswith("//"):
            continue
        clean = ref.split("#", 1)[0].split("?", 1)[0]
        target = ROOT / ("index.html" if clean == "/" else clean.lstrip("/"))
        if not target.exists():
            errors.append(f"{path.name}: missing local target {ref}")

    for form in soup.find_all("form"):
        if form.get("data-netlify") != "true":
            errors.append(f"{path.name}: form missing data-netlify=true")
        if form.get("netlify-honeypot") != "bot-field":
            errors.append(f"{path.name}: form missing honeypot")
        if not form.find("input", attrs={"name": "bot-field"}):
            errors.append(f"{path.name}: form missing bot-field")
        if not form.find("input", attrs={"name": "privacy-consent", "required": True}):
            errors.append(f"{path.name}: form missing required privacy consent")

for title, pages in titles.items():
    if title and len(pages) > 1:
        errors.append(f"Duplicate title: {title} -> {pages}")

for canonical, pages in canonicals.items():
    if canonical and len(pages) > 1:
        errors.append(f"Duplicate canonical: {canonical} -> {pages}")

for name in ("404.html", "thank-you.html"):
    soup = BeautifulSoup((ROOT / name).read_text(encoding="utf-8"), "html.parser")
    robots = soup.find("meta", attrs={"name": "robots"})
    if not robots or "noindex" not in robots.get("content", ""):
        errors.append(f"{name}: missing noindex")

json.loads((ROOT / "site.webmanifest").read_text(encoding="utf-8"))
json.loads((ROOT / "lighthouserc.json").read_text(encoding="utf-8"))
ET.parse(ROOT / "sitemap.xml")

expected = [
    "version: STSv1",
    "mode: testing",
    "mx: smtp.google.com",
    "max_age: 86400",
]
actual = (ROOT / ".well-known/mta-sts.txt").read_text(encoding="utf-8").strip().splitlines()
if actual != expected:
    errors.append(f"MTA-STS mismatch: {actual}")

print(f"HTML pages: {len(html_files)}")

if errors:
    print(f"Errors: {len(errors)}")
    for error in errors:
        print(f"ERROR: {error}")
    sys.exit(1)

print("Repository QA: PASS")
