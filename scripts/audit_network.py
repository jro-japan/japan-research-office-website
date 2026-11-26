"""Read-only DNS/HTTPS diagnostics. No mail, forms, credentials or DNS edits."""
import json
import urllib.request
import urllib.parse
import urllib.error

DOMAIN = "japanresearchoffice.com"
PREVIEW = "https://deploy-preview-31--hiroaki-research-office.netlify.app"
def dns(name, kind, prefix=None):
    try:
        url = "https://dns.google/resolve?" + urllib.parse.urlencode({"name":name,"type":kind})
        with urllib.request.urlopen(url, timeout=10) as f:
            data = json.load(f)
        if data.get("Status") != 0:
            print(f"DNS {name} {kind}: status={data.get('Status')}; not verified")
            return
        rr = [str(a.get("data","")) for a in data.get("Answer",[]) if a.get("type")=={"TXT":16,"MX":15}[kind]]
        matches = [v for v in rr if prefix is None or prefix.lower() in v.lower()]
        print(f"DNS {name} {kind}: matching={len(matches)}" + (" (selector-specific; absent is not proof DKIM disabled)" if "._domainkey" in name else ""))
        if prefix in ("v=spf1","v=DMARC1","v=STSv1","v=TLSRPTv1") or kind=="MX":
            for v in matches:
                # These public records may contain mailboxes; avoid emitting them in logs.
                if prefix=="v=spf1" or kind=="MX":
                    print("  " + v[:300])
                else:
                    import re
                    print("  " + re.sub(r"(?i)(?:rua|ruf)=[^;\"]+", "report-address=REDACTED", v)[:300])
    except Exception as e:
        print(f"DNS {name} {kind}: UNVERIFIED ({type(e).__name__})")

def probe(url):
    try:
        request = urllib.request.Request(url, headers={"User-Agent":"JRO-Website-QA/1.0"})
        try:
            response = urllib.request.urlopen(request, timeout=12)
        except urllib.error.HTTPError as e:
            response = e
        with response as f:
            print(f"HTTP {url}: {f.status}, final={f.geturl()}")
            for key in ("Content-Type","Strict-Transport-Security","Content-Security-Policy","X-Content-Type-Options","X-Frame-Options","X-Robots-Tag"):
                v=f.headers.get(key)
                print(f"  {key}: {'present' if v else 'absent'}" + (f" ({v[:120]})" if v and key in ("Content-Type","X-Robots-Tag") else ""))
            body=f.read(65536).decode("utf-8",errors="replace")
            if url.endswith("/.well-known/mta-sts.txt"):
                print("  MTA-STS mode: " + next((x for x in body.splitlines() if x.startswith("mode:")), "unverified"))
            if url.endswith("/robots.txt"):
                print("  Google-Extended token present: "+str("Google-Extended" in body))
    except Exception as e:
        print(f"HTTP {url}: UNVERIFIED ({type(e).__name__})")

if __name__ == "__main__":
    dns(DOMAIN,"MX")
    dns(DOMAIN,"TXT","v=spf1")
    dns("_dmarc."+DOMAIN,"TXT","v=DMARC1")
    dns("google._domainkey."+DOMAIN,"TXT","v=DKIM1")
    dns("_mta-sts."+DOMAIN,"TXT","v=STSv1")
    dns("_smtp._tls."+DOMAIN,"TXT","v=TLSRPTv1")
    for url in ("https://"+DOMAIN+"/", "https://"+DOMAIN+"/robots.txt",
                "https://mta-sts."+DOMAIN+"/.well-known/mta-sts.txt",
                PREVIEW+"/", PREVIEW+"/pricing.html", PREVIEW+"/sample.html",
                PREVIEW+"/README_DEPLOY.txt"):
        probe(url)
