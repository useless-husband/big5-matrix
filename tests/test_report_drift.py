import gzip
import json
import platform
import shutil
import tempfile
import unittest
from pathlib import Path

from big5matrix import drift, protocol, report, store
from big5matrix.registry import ROOT


class RenderTest(unittest.TestCase):
    S = {"numbers": {"a.b": 1234, "name": "x"}, "tables": {"t": "| h |\n| --- |\n| 1 |"}}

    def test_numbers_and_tables_are_refreshed(self):
        text = "We saw <!--n:a.b-->0<!--/n--> cases of <!--n:name-->?<!--/n-->.\n<!--t:t-->\nold\n<!--/t-->\n"
        out = report.render(text, self.S)
        self.assertIn("<!--n:a.b-->1,234<!--/n-->", out)
        self.assertIn("<!--n:name-->x<!--/n-->", out)
        self.assertIn("<!--t:t-->\n| h |\n| --- |\n| 1 |\n<!--/t-->", out)
        self.assertEqual(report.render(out, self.S), out)  # idempotent

    def test_unknown_keys_are_errors(self):
        with self.assertRaises(report.UnknownKey):
            report.render("<!--n:missing-->1<!--/n-->", self.S)
        with self.assertRaises(report.UnknownKey):
            report.render("<!--t:missing-->\n<!--/t-->", self.S)

    def test_a_marker_never_swallows_prose(self):
        text = "Write markers like `<!--n:…-->` in prose.\nLater: <!--n:a.b-->1<!--/n-->"
        self.assertEqual(report.render(text, self.S).count("1,234"), 1)
        self.assertIn("`<!--n:…-->` in prose", report.render(text, self.S))

    def test_committed_documents_are_up_to_date(self):
        summary = json.loads(report.SUMMARY.read_text())
        for doc in report.DOCUMENTS:
            if doc.exists():
                with self.subTest(doc=doc.name):
                    text = doc.read_text()
                    self.assertEqual(report.render(text, summary), text,
                                     "run `python3 -m big5matrix report`")


class CommittedDataTest(unittest.TestCase):
    def test_every_result_file_is_valid_and_small(self):
        manifest = store.read_manifest()
        for impl_id, entry in manifest["impls"].items():
            for op in ("d", "e"):
                if op not in entry["ops"]:
                    continue
                with self.subTest(impl=impl_id, op=op):
                    path = store.result_path(impl_id, op)
                    self.assertLess(path.stat().st_size, 1024 * 1024)
                    raw = gzip.decompress(path.read_bytes())
                    self.assertEqual(store.content_digest(raw), entry[store.OPS[op]]["sha256"])
                    for r in store.read_results(impl_id, op).values():
                        protocol.validate_result(op, r)


class DriftTest(unittest.TestCase):
    """The drift check against a copy of the committed data, with the real Python adapter."""

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        for name in ("manifest.json", "encode-extra.txt"):
            shutil.copy(store.DATA / name, self.tmp / name)
        for op in ("decode", "encode"):
            (self.tmp / op).mkdir()
            shutil.copy(store.DATA / op / "python.big5.txt.gz", self.tmp / op / "python.big5.txt.gz")
        self.manifest = json.loads((self.tmp / "manifest.json").read_text())
        if self.manifest["impls"]["python.big5"]["key"] != platform.python_version():
            self.skipTest("the committed Python data is for another Python version")

    def tearDown(self):
        shutil.rmtree(self.tmp)

    def _tamper(self):
        args = store.case_args("d", self.tmp)
        res = store.read_results("python.big5", "d", self.tmp)
        res["A145"] = "2027"
        digest = store.write_results("python.big5", "d", res, args, self.tmp)
        self.manifest["impls"]["python.big5"]["decode"]["sha256"] = digest
        (self.tmp / "manifest.json").write_text(json.dumps(self.manifest))

    def test_identical_data_passes(self):
        outcomes, skipped = drift.run_check(["python.big5"], base=self.tmp, log=lambda s: None)
        self.assertEqual({(o.op, o.status) for o in outcomes}, {("d", "same"), ("e", "same")})
        self.assertEqual(drift.report(outcomes, skipped, log=lambda s: None), 0)

    def test_changed_data_with_the_same_version_fails(self):
        self._tamper()
        outcomes, skipped = drift.run_check(["python.big5"], base=self.tmp, log=lambda s: None)
        bad = [o for o in outcomes if o.status != "same"]
        self.assertEqual(len(bad), 1)
        self.assertEqual((bad[0].status, bad[0].differing), ("changed", 1))
        self.assertEqual(bad[0].examples[0], ("A145", "2027", "2022"))
        self.assertEqual(drift.report(outcomes, skipped, log=lambda s: None), 1)

    def test_a_version_bump_is_reported_not_failed(self):
        self._tamper()
        self.manifest["impls"]["python.big5"]["key"] = "0.0.1"
        (self.tmp / "manifest.json").write_text(json.dumps(self.manifest))
        outcomes, skipped = drift.run_check(["python.big5"], base=self.tmp, log=lambda s: None)
        self.assertIn("drift", {o.status for o in outcomes})
        self.assertEqual(drift.report(outcomes, skipped, log=lambda s: None), 0)


class ToolsTest(unittest.TestCase):
    def test_reference_files_match_their_pinned_digests(self):
        import hashlib
        import importlib.util

        spec = importlib.util.spec_from_file_location("fetch_reference", ROOT / "tools" / "fetch_reference.py")
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        for name, (_, want) in mod.SOURCES.items():
            with self.subTest(name=name):
                self.assertEqual(hashlib.sha256((ROOT / "reference" / name).read_bytes()).hexdigest(), want)


if __name__ == "__main__":
    unittest.main()
