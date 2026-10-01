import shutil
import sys
import tempfile
import textwrap
import unittest
from pathlib import Path

from big5matrix import cases, protocol, store
from big5matrix.run import AdapterError, extras_from_decodes, run_adapter


class StoreTest(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        shutil.copy(store.DATA / "encode-extra.txt", self.tmp / "encode-extra.txt")

    def tearDown(self):
        shutil.rmtree(self.tmp)

    def test_round_trip_with_partial_scope(self):
        args = store.case_args("d", self.tmp)
        res = {"A140": "3000", "8862": "00CA 0304"}
        digest = store.write_results("x", "d", res, args, self.tmp)
        self.assertEqual(store.read_results("x", "d", self.tmp), res)
        self.assertEqual(store.content_digest(store.read_raw("x", "d", self.tmp)), digest)

    def test_files_are_deterministic(self):
        args = store.case_args("d", self.tmp)
        res = {a: "0041" for a in args[:300]}
        store.write_results("x", "d", res, args, self.tmp)
        first = store.result_path("x", "d", self.tmp).read_bytes()
        store.write_results("x", "d", res, args, self.tmp)
        self.assertEqual(store.result_path("x", "d", self.tmp).read_bytes(), first)

    def test_a_file_for_another_case_list_is_rejected(self):
        args = store.case_args("e", self.tmp)
        store.write_results("x", "e", {args[0]: "00"}, args, self.tmp)
        cases.write_extra(self.tmp / "encode-extra.txt", [(0x00CA, 0x0304)])  # a different case list
        with self.assertRaises(store.StaleData):
            store.read_results("x", "e", self.tmp)

    def test_manifest(self):
        self.assertEqual(store.read_manifest(self.tmp), {"cases": {}, "impls": {}})
        store.write_manifest({"cases": {}, "impls": {"b": {}, "a": {}}}, self.tmp)
        self.assertEqual(list(store.read_manifest(self.tmp)["impls"]), ["a", "b"])


def fake_adapter(tmp: Path, body: str) -> list[str]:
    p = tmp / "adapter.py"
    p.write_text(textwrap.dedent(body))
    return [sys.executable, str(p)]


class RunAdapterTest(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())

    def tearDown(self):
        shutil.rmtree(self.tmp)

    def test_a_well_behaved_adapter(self):
        cmd = fake_adapter(self.tmp, """
            import sys
            for line in sys.stdin:
                op, arg = line.rstrip("\\n").split("\\t")
                print(f"{op}\\t{arg}\\t{'0041' if op == 'd' else '41'}")
        """)
        self.assertEqual(run_adapter(cmd, "c", "d", ["41", "42"]), {"41": "0041", "42": "0041"})

    def test_missing_lines_are_an_error(self):
        cmd = fake_adapter(self.tmp, """
            import sys
            sys.stdin.read()
            print("d\\t41\\t0041")
        """)
        with self.assertRaisesRegex(AdapterError, "2 requests but 1 responses"):
            run_adapter(cmd, "c", "d", ["41", "42"])

    def test_answers_out_of_order_are_an_error(self):
        cmd = fake_adapter(self.tmp, """
            import sys
            lines = [l.rstrip("\\n").split("\\t") for l in sys.stdin]
            for op, arg in reversed(lines):
                print(f"{op}\\t{arg}\\t0041")
        """)
        with self.assertRaisesRegex(AdapterError, "does not answer"):
            run_adapter(cmd, "c", "d", ["41", "42"])

    def test_malformed_results_are_an_error(self):
        cmd = fake_adapter(self.tmp, """
            import sys
            for line in sys.stdin:
                op, arg = line.rstrip("\\n").split("\\t")
                print(f"{op}\\t{arg}\\tnot-hex")
        """)
        with self.assertRaises(protocol.ProtocolError):
            run_adapter(cmd, "c", "d", ["41"])

    def test_a_crash_is_reported(self):
        cmd = fake_adapter(self.tmp, "import sys; sys.stderr.write('boom'); sys.exit(3)\n")
        with self.assertRaisesRegex(AdapterError, "exited 3: boom"):
            run_adapter(cmd, "c", "d", ["41"])


class ExtrasTest(unittest.TestCase):
    def test_multi_code_point_output_counts_only_for_a_lead_byte(self):
        res = {
            "88": "FFFD", "8862": "00CA 0304",  # 0x88 is a lead byte: a real two-code-point character
            "80": "0080", "8041": "0080 0041",  # 0x80 decodes alone: two characters, not one
            "FE": "FFFD", "FEFE": "0093 DF04",  # a lone surrogate is never an encode case
            "A1": "FFFD", "A140": "1F600",  # outside the BMP and plane 2
        }
        self.assertEqual(extras_from_decodes([res]), [(0x1F600,), (0x00CA, 0x0304)])


if __name__ == "__main__":
    unittest.main()
