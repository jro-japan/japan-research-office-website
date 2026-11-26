"""Validate and render explicitly approved public research updates; no network or writes."""
from datetime import date, datetime, timezone
from hashlib import sha256
from html import escape
import json
import re
from urllib.parse import urlsplit

MARKER = "<!-- APPROVED_RESEARCH_UPDATES -->"
GATES = ("primary_source", "claim_verification", "publication_rights",
         "civilian_scope", "no_confidential_data", "english_review")
FIELDS = {"id", "version", "source_key", "title", "category", "published_on",
          "checked_on", "source_url", "rights_url", "confirmed_facts",
          "supported_inferences", "unknowns", "change_note", "review", "approval"}
CATEGORIES = {"Corporate", "Financial", "Industrial", "Market", "Civilian procurement", "Technical"}
# Supplemental warning only; never a substitute for subject/end-use review.
DENY = re.compile(r"\b(defen[cs]e|military|weapon[s]?|munition[s]?|dual[- ]use|economic security|classified|missile[s]?)\b|防衛|国防|軍事|経済安全保障|機密", re.I)
SECRET = re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----|(?:sk-|ghp_|github_pat_)[A-Za-z0-9_-]{10,}|[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}", re.I)

def require(ok, message):
    if not ok:
        raise ValueError(message)

def valid_date(value):
    require(isinstance(value, str) and bool(re.fullmatch(r"\d{4}-\d{2}-\d{2}", value)), "Invalid date")
    return date.fromisoformat(value)

def checked_url(value):
    require(isinstance(value, str) and len(value) <= 1500, "Invalid URL")
    u = urlsplit(value)
    require(u.scheme == "https" and bool(u.hostname) and not u.username and not u.password
            and not u.query and not u.fragment and not u.port
            and bool(re.fullmatch(r"[a-z0-9.-]+\.[a-z]{2,}", u.hostname))
            and not u.hostname.endswith((".local", ".internal", ".localhost", ".test", ".invalid", ".example"))
            and u.hostname not in {"example.com", "example.net", "example.org"}
            and not re.search(r"[\s<>\\]", value), "Only clean public HTTPS source URLs")
    return value

def digest(row):
    return sha256(json.dumps({k: v for k,v in row.items() if k != "approval"}, sort_keys=True,
                             ensure_ascii=False, separators=(",", ":")).encode("utf-8")).hexdigest()

def plain(value, limit):
    require(isinstance(value, str) and 0 < len(value.strip()) <= limit, "Missing or oversized text")
    require(not DENY.search(value) and not SECRET.search(value), "Publication screening warning")
    require(not re.search(r"<[^>]*>|[\x00-\x08\x0b-\x1f]", value), "Markup or control character not allowed")

def validate(rows):
    require(isinstance(rows, list) and len(rows) <= 1000, "Invalid registry")
    identities, source_keys, source_urls = {}, {}, {}
    today = datetime.now(timezone.utc).date()
    for r in rows:
        require(isinstance(r, dict) and set(r) == FIELDS, "Invalid record fields")
        require(isinstance(r["id"], str) and bool(re.fullmatch(r"JRO-R-[a-f0-9]{16}", r["id"])), "Invalid ID")
        require(type(r["version"]) is int and r["version"] >= 1, "Invalid version")
        require(isinstance(r["source_key"], str) and bool(re.fullmatch(r"[a-f0-9]{64}", r["source_key"])), "Invalid source key")
        require(r["id"] == "JRO-R-" + r["source_key"][:16], "ID must match source key")
        require(r["category"] in CATEGORIES, "Unapproved category")
        pub, chk = valid_date(r["published_on"]), valid_date(r["checked_on"])
        require(pub <= chk <= today, "Invalid date order")
        checked_url(r["source_url"]); checked_url(r["rights_url"])
        plain(r["title"], 180); plain(r["change_note"], 500)
        for field in ("confirmed_facts", "supported_inferences", "unknowns"):
            values = r[field]
            require(isinstance(values, list) and 1 <= len(values) <= 12, "Evidence fields required")
            for value in values:
                plain(value, 900)
        review = r["review"]
        require(isinstance(review, dict) and set(review) == set(GATES)
                and all(review[g] is True for g in GATES), "All review gates must explicitly pass")
        approval = r["approval"]
        require(isinstance(approval, dict) and set(approval) == {"status", "date", "reference", "sha256"}
                and approval["status"] == "OWNER_APPROVED", "Owner approval required")
        require(chk <= valid_date(approval["date"]) <= today, "Invalid approval date")
        require(isinstance(approval["reference"], str) and bool(re.fullmatch(r"JRO-APPROVAL-[A-Za-z0-9-]{6,80}", approval["reference"])), "Invalid approval reference")
        require(approval["sha256"] == digest(r), "Approval/content hash mismatch")
        versions = identities.setdefault(r["id"], {})
        require(r["version"] not in versions, "Duplicate ID and version")
        versions[r["version"]] = r
        key = r["source_key"]
        require(source_keys.setdefault(key, r["id"]) == r["id"], "Duplicate source identity")
        source_identity = (r["source_url"].rstrip("/"), r["published_on"])
        require(source_urls.setdefault(source_identity, r["id"]) == r["id"], "Duplicate source URL/date")
    for versions in identities.values():
        require(sorted(versions) == list(range(1, len(versions) + 1)), "Version sequence has gaps")
        ordered = [versions[i] for i in sorted(versions)]
        for older, newer in zip(ordered, ordered[1:]):
            require(older["published_on"] == newer["published_on"] and
                    older["checked_on"] <= newer["checked_on"], "Invalid version chronology")
    return identities

def render(rows):
    identities = validate(rows)
    if not identities:
        return "<p>No owner-approved daily research updates are published yet.</p>"
    out = []
    for key, versions in sorted(identities.items(), key=lambda item: (item[1][max(item[1])]["checked_on"], item[0]), reverse=True):
        r = versions[max(versions)]
        e = escape
        out += [f'<article id="{e(key)}"><h2>{e(r["title"])}</h2>',
                f'<p>{e(key)} · Version {r["version"]} · {e(r["category"])} · Source date {e(r["published_on"])} · Checked {e(r["checked_on"])}</p>',
                f'<p><a href="{e(r["source_url"], quote=True)}">Official primary source</a> · <a href="{e(r["rights_url"], quote=True)}">Source use terms</a></p>']
        for field, title in (("confirmed_facts", "Confirmed facts"), ("supported_inferences", "Supported inferences"), ("unknowns", "Unknowns")):
            out.append(f"<h3>{title}</h3><ul>" + "".join(f"<li>{e(v)}</li>" for v in r[field]) + "</ul>")
        out.append("<details><summary>Version history</summary><ul>" + "".join(f'<li>v{i} · {e(versions[i]["checked_on"])} · {e(versions[i]["change_note"])}</li>' for i in sorted(versions, reverse=True)) + "</ul></details></article>")
    return "\n".join(out)

def render_page(template, rows):
    require(template.count(MARKER) == 1, "Missing or duplicate updates marker")
    return template.replace(MARKER, render(rows))
