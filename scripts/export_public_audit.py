"""Produce a plain-text independent audit packet from the exact public artifact."""
from pathlib import Path
import hashlib
import subprocess
from bs4 import BeautifulSoup
from build_public import ROOT, PAGES, build

dist = build()
out = ROOT / "audit-output"
out.mkdir(exist_ok=True)
sha = subprocess.check_output(["git","rev-parse","HEAD"],text=True).strip()
paths = (*PAGES,"404.html","styles.css","robots.txt","sitemap.xml","llms.txt","_headers","_redirects","site.webmanifest",".well-known/mta-sts.txt",".well-known/security.txt")
header = "JRO INDEPENDENT AUDIT PACKET\nGit checkout: " + sha + "\nSource: generated dist, not live deployment. No internal ledgers, credentials or candidate records included.\n"
groups = {"01-pages.txt": [p for p in paths if p.endswith(".html") and p not in ("terms.html","privacy.html","customer-support.html","ordering-payment.html","trust-center.html","pricing.html","research-products.html")],
          "02-commercial-and-trust.txt": ["terms.html","privacy.html","customer-support.html","ordering-payment.html","trust-center.html","pricing.html","research-products.html"],
          "03-public-technical.txt": [p for p in paths if not p.endswith(".html")]}
for name, entries in groups.items():
    blocks = [header]
    for rel in entries:
        raw = (dist / rel).read_bytes()
        s = raw.decode("utf-8")
        if rel.endswith(".html"):
            s = BeautifulSoup(s,"html.parser").prettify()
        blocks.append(f"\n=== {rel} | SHA256 of original bytes: {hashlib.sha256(raw).hexdigest()} ===\nLine numbers below refer to this audit view (HTML prettified).\n")
        blocks.extend(f"{i:04d} | {line}" for i,line in enumerate(s.splitlines(),1))
    (out / name).write_text("\n".join(blocks)+"\n", encoding="utf-8")
print("Public audit packet: 3 plain-text files")
