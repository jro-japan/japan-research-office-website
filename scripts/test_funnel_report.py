from datetime import date
import unittest
from funnel_report import report

D = date.fromisoformat
def row(case, date, stage, origin="HOME"):
    return {"case_id":"JRO-C-"+case*16,"event_date":date,"stage":stage,"origin":origin}
def search(date, i, c):
    return {"date":date,"impressions":str(i),"clicks":str(c)}
def run(events=(), searches=()):
    return report(events,searches,D("2026-01-01"),D("2026-01-02"),D("2026-01-31"))
class FunnelTests(unittest.TestCase):
    def test_empty(self):
        r=run(); self.assertIsNone(r["search"]["clicks"]); self.assertIsNone(r["website"]["rates"]["INQUIRY_to_PAID_pct"])
    def test_cohort(self):
        e=[row("a","2026-01-01","INQUIRY"),row("a","2026-01-03","QUOTE"),row("a","2026-01-10","ORDER"),row("a","2026-01-20","PAID"),row("b","2026-01-02","INQUIRY","CONTACT"),row("c","2026-01-01","INQUIRY","OUTBOUND"),row("d","2026-01-03","INQUIRY")]
        r=run(e,[search("2026-01-01",100,5),search("2026-01-02",200,10)])
        self.assertEqual(r["website"]["counts"],{"INQUIRY":2,"QUOTE":1,"ORDER":1,"PAID":1})
        self.assertEqual(r["website"]["rates"]["INQUIRY_to_PAID_pct"],50)
        self.assertEqual(r["outbound"]["counts"]["INQUIRY"],1)
        self.assertEqual(r["search"]["ctr_pct"],5)
    def test_partial_search(self):
        self.assertIsNone(run([], [search("2026-01-01",1,1)])["search"]["ctr_pct"])
    def test_zero_search(self):
        self.assertEqual(run([], [search("2026-01-01",0,0),search("2026-01-02",0,0)])["search"]["clicks"],0)
    def test_duplicate(self):
        with self.assertRaises(ValueError): run([row("a","2026-01-01","INQUIRY")]*2)
    def test_invoice_not_paid(self):
        with self.assertRaises(ValueError): run([row("a","2026-01-01","INQUIRY"),row("a","2026-01-02","INVOICED")])
    def test_missing_stage(self):
        with self.assertRaises(ValueError): run([row("a","2026-01-01","INQUIRY"),row("a","2026-01-02","PAID")])
    def test_out_of_order(self):
        with self.assertRaises(ValueError): run([row("a","2026-01-02","INQUIRY"),row("a","2026-01-01","QUOTE")])
    def test_bad_id(self):
        r=row("a","2026-01-01","INQUIRY"); r["case_id"]="customer@example.org"
        with self.assertRaises(ValueError): run([r])
    def test_origin_conflict(self):
        with self.assertRaises(ValueError): run([row("a","2026-01-01","INQUIRY"),row("a","2026-01-02","QUOTE","CONTACT")])
    def test_duplicate_search(self):
        with self.assertRaises(ValueError): run([], [search("2026-01-01",1,0)]*2)
    def test_invalid_search(self):
        with self.assertRaises(ValueError): run([], [search("2026-01-01",1,2)])
    def test_future_event(self):
        with self.assertRaises(ValueError): run([row("a","2026-02-01","INQUIRY")])
if __name__=="__main__":
    unittest.main()
