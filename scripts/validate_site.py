#!/usr/bin/env python3
"""Validate the exact static artifact published by Netlify, not legacy source files."""
import json
import re
import sys
import xml.etree.ElementTree as ET
from pathlib import Path
from urllib.parse import unquote, urljoin, urlsplit
from bs4 import BeautifulSoup
from build_public import ROOT, PAGES, PUBLIC_FILES, build

BASE = "https://japanresearchoffice.com"
errors = []
def check(condition, message):
    if not condition:
        errors.append(message)

dist = build()
pages = {}
titles = set()
def page_url(rel):
    return BASE + ("/" if rel == "index.html" else "/ja/" if rel == "ja/index.html" else "/" + rel)

for rel in (*PAGES, "404.html"):
    soup = BeautifulSoup((dist / rel).read_text(encoding="utf-8"), "html.parser")
    pages[rel] = soup
    title = soup.title.get_text(" ", strip=True) if soup.title else ""
    check(bool(title) and title not in titles, f"{rel}: missing or duplicate title")
    titles.add(title)
    desc = soup.find("meta", attrs={"name": "description"})
    check(bool(desc and desc.get("content", "").strip()), f"{rel}: missing description")
    canon = soup.find("link", rel="canonical")
    check(bool(canon and canon.get("href") == page_url(rel)), f"{rel}: canonical mismatch")
    check(len(soup.find_all("h1")) == 1, f"{rel}: expected one H1")
    check(bool(soup.html and soup.html.get("lang") == ("ja" if rel == "ja/index.html" else "en")), f"{rel}: language mismatch")
    check(bool(soup.find("meta", attrs={"property": "og:image"})), f"{rel}: missing OG image")
    check(bool(soup.find("meta", attrs={"name": "twitter:card"})), f"{rel}: missing Twitter card")
    check(bool(soup.find("link", rel="manifest")), f"{rel}: missing manifest")
    robots = soup.find("meta", attrs={"name": "robots"})
    noindex = bool(robots and "noindex" in robots.get("content", "").lower())
    check(noindex == (rel == "404.html"), f"{rel}: unexpected indexing policy")
    scripts = soup.find_all("script", attrs={"type": "application/ld+json"})
    check(len(scripts) == 1, f"{rel}: expected one JSON-LD block")
    for script in scripts:
        try:
            check(isinstance(json.loads(script.get_text()).get("@graph"), list), f"{rel}: missing JSON-LD graph")
        except (ValueError, AttributeError) as exc:
            errors.append(f"{rel}: invalid JSON-LD: {exc}")
    check(not soup.find("form"), f"{rel}: unexpected public form")
    ids = [tag["id"] for tag in soup.find_all(id=True)]
    check(len(ids) == len(set(ids)), f"{rel}: duplicate IDs")
    visible = soup.get_text(" ", strip=True)
    check(not re.search(r"Industrial Signal Desk|Patent Intelligence|US\$\s*(69|150|490|1,250|2,900)\b", visible, re.I), f"{rel}: retired offer detected")

def resolve(raw, origin):
    u = urlsplit(urljoin(origin, raw))
    if u.scheme not in ("http", "https") or u.netloc != "japanresearchoffice.com":
        return None, None
    path = unquote(u.path).lstrip("/")
    if not path or path.endswith("/"):
        path += "index.html"
    elif path not in PUBLIC_FILES and path + ".html" in PUBLIC_FILES:
        path += ".html"
    return path, unquote(u.fragment)

def target(raw, origin, label):
    if not raw:
        return
    path, fragment = resolve(raw, origin)
    if path is None:
        return
    check(path in PUBLIC_FILES, f"{label}: missing public target {raw}")
    if fragment and path in pages:
        check(bool(pages[path].find(id=fragment) or pages[path].find("a", attrs={"name": fragment})), f"{label}: missing anchor {raw}")

for rel, soup in pages.items():
    for tag in soup.find_all(["a", "link", "script", "img"]):
        target(tag.get("href" if tag.name in ("a", "link") else "src"), page_url(rel), rel)
    for tag in soup.find_all("meta", attrs={"property": "og:image"}):
        target(tag.get("content"), page_url(rel), rel)

manifest = json.loads((dist / "site.webmanifest").read_text(encoding="utf-8"))
for icon in manifest.get("icons", []):
    target(icon.get("src"), BASE + "/", "manifest")
for rel in ("assets/img/apple-touch-icon.png", "assets/img/og-image.png"):
    check((dist / rel).read_bytes().startswith(b"\x89PNG\r\n\x1a\n"), f"{rel}: invalid PNG signature")
for rel in ("assets/img/favicon.svg", "assets/img/logo.svg"):
    check(ET.parse(dist / rel).getroot().tag.endswith("}svg"), f"{rel}: invalid SVG")

ns = {"s": "http://www.sitemaps.org/schemas/sitemap/0.9"}
locs = [e.text for e in ET.parse(dist / "sitemap.xml").findall("s:url/s:loc", ns)]
check(len(locs) == len(set(locs)) and set(locs) == {page_url(p) for p in PAGES}, "Sitemap does not match indexed public pages")
redirects = [line.split() for line in (dist / "_redirects").read_text().splitlines() if line.strip() and not line.startswith("#")]
check(bool(redirects and redirects[-1] == ["/*", "/404.html", "404"]), "404 fallback must be last")
active = {urlsplit(page_url(p)).path for p in PAGES}
retired = {"industrial-signal-desk", "patent-intelligence", "ai-research-service", "custom-research", "industries", "sample", "case-studies", "thank-you"}
routes = {row[0]: row for row in redirects}
check(len(routes) == len(redirects), "Duplicate redirect source")
for row in redirects:
    check(row[0] not in active, f"Active page redirected: {row[0]}")
    if row[0].startswith("/") and len(row) >= 2:
        target(row[1], BASE + "/", "_redirects")
for name in retired:
    for suffix in ("", ".html"):
        row = routes.get("/" + name + suffix, [])
        check(len(row) == 3 and row[-1] == "301!", f"Missing retired route: {name}{suffix}")
for rel in ("index.html", "pricing.html", "research-products.html"):
    check("US$400" in pages[rel].get_text(" ", strip=True), f"{rel}: proposed product price missing")
for rel in ("README_DEPLOY.txt", "GITHUB_OPERATIONS.md", "FINAL_REVIEW_REPORT.md", "scripts/validate_site.py", ".gitignore", "site.js", "site.css", "sample.html", "thank-you.html"):
    check(not (dist / rel).exists(), f"Nonpublic file leaked into artifact: {rel}")

config = (ROOT / "netlify.toml").read_text(encoding="utf-8")
check(re.findall(r'^\s*publish\s*=\s*"([^"]+)"', config, re.M) == ["dist"] * 4, "Netlify publish paths must all be dist")
check('command = "python3 scripts/build_public.py"' in config, "Netlify build command missing")
lh = json.loads((ROOT / "lighthouserc.json").read_text(encoding="utf-8"))["ci"]["collect"]
check(lh.get("staticDistDir") == "dist", "Lighthouse must target dist")
for u in lh.get("url", []):
    target(urlsplit(u).path, BASE + "/", "Lighthouse")

# Customer trust and buying-flow regression checks.
for rel in ("index.html", "pricing.html", "research-products.html", "contact.html"):
    links = {a.get("href") for a in pages[rel].find_all("a")}
    for url in ("/trust-center.html", "/ordering-payment.html"):
        check(url in links, f"{rel}: missing buyer review route {url}")
sample = pages["sample-tender-evidence.html"]
sample_text = sample.get_text(" ", strip=True)
for label in ("Confirmed facts", "Supported inference", "Unknowns", "JRO-SAMPLE-001", "v1.1", "Not assessed for any supplier"):
    check(label in sample_text, f"Sample missing evidence marker: {label}")
check(bool(sample.find("a", href="https://www.ndl.go.jp/supply/nyuusatsu/ippan/20260729_jitsumu2")), "Sample missing primary source")
check(bool(pages["research-library.html"].find("a", href="/sample-tender-evidence.html")), "Library missing sample")
check(bool(pages["ordering-payment.html"].find("a", href=lambda h: h and h.startswith("mailto:hiroaki@japanresearchoffice.com?"))), "Ordering missing email request")
check("No online checkout" in pages["ordering-payment.html"].get_text(" ", strip=True), "Ordering payment status must remain explicit")

# Static email CTA codes are not web tracking or payment evidence.
from urllib.parse import parse_qs
for rel, code in (("index.html","HOME"), ("ja/index.html","JA"), ("contact.html","CONTACT"), ("research-products.html","PRODUCT"), ("ordering-payment.html","ORDERING")):
    links = [a.get("href","") for a in pages[rel].find_all("a")]
    subjects = [parse_qs(urlsplit(h).query).get("subject", [""])[0] for h in links if h.startswith("mailto:hiroaki@japanresearchoffice.com?")]
    check(any(t.startswith(f"[JRO-WEB:{code}] ") for t in subjects), f"{rel}: inquiry origin code missing")
check(not (dist / "scripts/funnel_report.py").exists(), "Internal funnel tool leaked")
check(not (dist / "private-metrics").exists(), "Private measurement directory leaked")
if errors:
    print("\n".join("ERROR: " + error for error in errors))
    sys.exit(1)
print(f"Public artifact QA: PASS ({len(PAGES)} indexed pages, {len(PUBLIC_FILES)} files)")
