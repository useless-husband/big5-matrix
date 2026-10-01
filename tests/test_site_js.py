"""The site's JavaScript (docs/assets) must compute the same numbers as the Python analysis."""

import json
import shutil
import subprocess
import unittest

from big5matrix import report, store
from big5matrix.registry import ROOT


@unittest.skipUnless(shutil.which("node"), "node is not installed")
class SiteParityTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        r = subprocess.run(["node", str(ROOT / "tests" / "js" / "parity.mjs")], capture_output=True, text=True,
                           timeout=900)
        if r.returncode != 0:
            raise AssertionError(f"parity.mjs failed: {r.stderr[-2000:]}")
        cls.js = json.loads(r.stdout)
        cls.summary = json.loads(report.SUMMARY.read_text())

    def test_case_list(self):
        self.assertEqual(self.js["eargs"], len(store.case_args("e")))

    def test_divergence_classes(self):
        for c in self.summary["site"]["classes"]:
            with self.subTest(cls=c["id"]):
                self.assertEqual(self.js["classes"][c["id"]], c["divergent"])

    def test_character_maps(self):
        for impl, rep in self.summary["site"]["repertoire"].items():
            if "decode_chars" in rep:
                with self.subTest(impl=impl):
                    self.assertEqual(self.js["chars"][impl], rep["decode_chars"])

    def test_by_name_pairs(self):
        for key in ("big5", "cp950"):
            for p in self.summary["site"]["by_name"][key]["pairs"]:
                with self.subTest(key=key, writer=p["writer"], reader=p["reader"]):
                    self.assertEqual(self.js["by_name"][key][f"{p['writer']}|{p['reader']}"],
                                     [p["same"], p["changed"], p["error"]])

    def test_round_trips(self):
        for e, w in self.summary["site"]["within"].items():
            with self.subTest(impl=e):
                self.assertEqual(self.js["within"][e], [w["btb"]["same"], w["btb"]["changed"], w["btb"]["lost"],
                                                        w["tbt"]["same"], w["tbt"]["changed"], w["tbt"]["error"]])

    def test_query_parsing(self):
        self.assertEqual(self.js["queries"], [
            {"op": "d", "arg": "A145"}, {"op": "d", "arg": "A145"}, {"op": "e", "arg": "2027"},
            {"op": "e", "arg": "5140"}, {"op": "d", "arg": "A1"}, None])


if __name__ == "__main__":
    unittest.main()
