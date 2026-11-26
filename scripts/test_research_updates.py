import copy
from datetime import datetime, timezone
import unittest
from research_updates import GATES, digest, render, render_page, validate, MARKER

def record():
    today = datetime.now(timezone.utc).date().isoformat()
    key = "a"*64
    r = {"id": "JRO-R-"+key[:16], "version": 1, "source_key": key,
         "title": "Fictional QA fixture & test", "category": "Market",
         "published_on": today, "checked_on": today,
         "source_url": "https://www.ndl.go.jp/test-fixture", "rights_url": "https://www.ndl.go.jp/sitepolicy/terms",
         "confirmed_facts": ["Synthetic value for test only."], "supported_inferences": ["Test inference."],
         "unknowns": ["Test unknown."], "change_note": "Initial test fixture.",
         "review": {g: True for g in GATES}}
    approve(r)
    return r

def approve(r):
    r["approval"] = {"status":"OWNER_APPROVED", "date":r["checked_on"],
                     "reference":"JRO-APPROVAL-TEST-ONLY", "sha256":digest(r)}

class UpdateTests(unittest.TestCase):
    def test_empty(self):
        self.assertIn("No owner-approved", render([]))
    def test_valid_escaped(self):
        self.assertIn("&amp;", render([record()]))
    def test_draft(self):
        r = record(); r["approval"]["status"] = "DRAFT"
        with self.assertRaises(ValueError): validate([r])
    def test_missing_gate(self):
        r = record(); r["review"]["publication_rights"] = False; approve(r)
        with self.assertRaises(ValueError): validate([r])
    def test_modified_after_approval(self):
        r = record(); r["title"] = "Changed"
        with self.assertRaises(ValueError): validate([r])
    def test_sensitive(self):
        r = record(); r["title"] = "Military research"; approve(r)
        with self.assertRaises(ValueError): validate([r])
    def test_email(self):
        r = record(); r["unknowns"] = ["abc@example.org"]; approve(r)
        with self.assertRaises(ValueError): validate([r])
    def test_injection(self):
        r = record(); r["title"] = "<script>alert(1)</script>"; approve(r)
        with self.assertRaises(ValueError): validate([r])
    def test_bad_url(self):
        r = record(); r["source_url"] = "javascript:alert(1)"; approve(r)
        with self.assertRaises(ValueError): validate([r])
    def test_future(self):
        r = record(); r["checked_on"] = "2999-01-01"; approve(r)
        with self.assertRaises(ValueError): validate([r])
    def test_duplicate_version(self):
        r = record()
        with self.assertRaises(ValueError): validate([r, copy.deepcopy(r)])
    def test_duplicate_source(self):
        a = record(); b = copy.deepcopy(a); b["source_key"] = "b"*64; b["id"]="JRO-R-"+"b"*16; approve(b)
        with self.assertRaises(ValueError): validate([a,b])
    def test_revision(self):
        a = record(); b = copy.deepcopy(a); b["version"] = 2; b["change_note"] = "Corrected test"; approve(b)
        html = render([a,b])
        self.assertIn("Version 2", html); self.assertIn("v1", html)
        self.assertEqual(html.count('<article id='), 1)
    def test_version_gap(self):
        r = record(); r["version"] = 2; approve(r)
        with self.assertRaises(ValueError): validate([r])
    def test_marker(self):
        with self.assertRaises(ValueError): render_page("missing", [])
        self.assertNotIn(MARKER, render_page(MARKER, []))

if __name__ == "__main__":
    unittest.main()
