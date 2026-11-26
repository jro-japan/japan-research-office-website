"""Offline funnel report: use private, pseudonymous case events and aggregate search metrics.
No network, email sending, tracking cookies, customer identities or payment credentials.
"""
import argparse
import csv
import json
import re
from datetime import date
from pathlib import Path

STAGES = ("INQUIRY", "QUOTE", "ORDER", "PAID")
ORIGINS = {"HOME", "JA", "CONTACT", "PRODUCT", "ORDERING", "WEB_UNTAGGED", "OUTBOUND", "OTHER", "UNKNOWN"}
WEB = {"HOME", "JA", "CONTACT", "PRODUCT", "ORDERING", "WEB_UNTAGGED"}
EVENT_FIELDS = ("case_id", "event_date", "stage", "origin")
SEARCH_FIELDS = ("date", "impressions", "clicks")
def require(condition, message):
    if not condition:
        raise ValueError(message)
def day(s):
    require(bool(re.fullmatch(r"\d{4}-\d{2}-\d{2}", s)), "Date must be YYYY-MM-DD")
    return date.fromisoformat(s)
def read_csv(path, fields):
    with Path(path).open(encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        require(tuple(reader.fieldnames or ()) == fields, f"Invalid CSV schema: {Path(path).name}")
        rows = list(reader)
        require(all(None not in r and all(v is not None for v in r.values()) for r in rows), "Malformed CSV row")
        return rows
def ratio(n,d):
    return round(n/d*100, 2) if d else None
def report(events, search, start, end, as_of):
    require(start <= end <= as_of, "Invalid cohort dates")
    cases = {}
    for r in events:
        require(set(r) == set(EVENT_FIELDS), "Invalid event columns")
        cid, stage, origin = r["case_id"], r["stage"], r["origin"]
        require(bool(re.fullmatch(r"JRO-C-[0-9a-f]{16}", cid)), "Use nonidentifying case IDs only")
        require(stage in STAGES and origin in ORIGINS, "Unknown stage or origin")
        d = day(r["event_date"])
        require(d <= as_of, "Event after report cutoff")
        case = cases.setdefault(cid, {"origin": origin, "dates": {}})
        require(case["origin"] == origin, "Inconsistent case origin")
        require(stage not in case["dates"], "Duplicate stage; record first confirmed date only")
        case["dates"][stage] = d
    for case in cases.values():
        dates = case["dates"]
        require("INQUIRY" in dates, "Missing initial inquiry")
        present = [s for s in STAGES if s in dates]
        require(present == list(STAGES[:len(present)]), "Missing earlier stage; resolve evidence gap before reporting")
        require([dates[s] for s in present] == sorted(dates[s] for s in present), "Out-of-order dates")
    def cohort(group):
        selected = [c for c in cases.values() if c["origin"] in group and start <= c["dates"]["INQUIRY"] <= end]
        counts = {s:sum(s in c["dates"] for c in selected) for s in STAGES}
        rates = {f"{a}_to_{b}_pct":ratio(counts[b], counts[a]) for a,b in zip(STAGES, STAGES[1:])}
        rates["INQUIRY_to_PAID_pct"] = ratio(counts["PAID"], counts["INQUIRY"])
        return {"counts":counts, "rates":rates}
    seen = set(); impressions = clicks = 0
    for r in search:
        require(set(r) == set(SEARCH_FIELDS), "Invalid search columns")
        d = day(r["date"])
        require(d <= as_of and d not in seen, "Duplicate or future search date")
        seen.add(d)
        require(all(re.fullmatch(r"\d+", r[k]) for k in ("impressions","clicks")), "Search metrics must be nonnegative integers")
        i,c = int(r["impressions"]),int(r["clicks"])
        require(c <= i, "Clicks exceed impressions")
        if start <= d <= end:
            impressions += i; clicks += c
    covered = sum(start <= d <= end for d in seen)
    days = (end-start).days+1
    complete = covered == days
    return {"cohort_start":str(start),"cohort_end":str(end),"as_of":str(as_of),
            "search":{"days_covered":covered,"days_expected":days,"complete":complete,
                      "impressions":impressions if complete else None,"clicks":clicks if complete else None,
                      "ctr_pct":ratio(clicks,impressions) if complete else None},
            "website":cohort(WEB),"outbound":cohort({"OUTBOUND"}),"other":cohort({"OTHER"}),"unknown":cohort({"UNKNOWN"}),
            "website_by_cta":{o:cohort({o}) for o in sorted(WEB)},
            "notes":["Counts are based on recorded evidence; completeness of case input is not verified.",
                     "Stage counts refer to inquiry cohorts followed through the as-of date; recent cohorts may be immature.",
                     "PAID means confirmed full receipt against the agreed amount, not an invoice or verbal acceptance.",
                     "Static email subject codes identify an inquiry CTA, not the preceding acquisition channel.",
                     "Search clicks are not unique visitors; organic inquiry conversion is not measured by these inputs.",
                     "Missing search dates are unknown, not zero. Null rates mean denominator unavailable or zero."]}
def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--events",required=True); p.add_argument("--search",required=True)
    p.add_argument("--start",required=True); p.add_argument("--end",required=True); p.add_argument("--as-of",required=True)
    a=p.parse_args()
    result=report(read_csv(a.events,EVENT_FIELDS),read_csv(a.search,SEARCH_FIELDS),day(a.start),day(a.end),day(a.as_of))
    print(json.dumps(result,ensure_ascii=False,indent=2))
if __name__ == "__main__":
    main()
