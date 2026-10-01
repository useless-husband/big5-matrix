import tempfile
import unittest
from pathlib import Path

from big5matrix import cases, protocol


class ProtocolTest(unittest.TestCase):
    def test_round_trip_of_a_response_line(self):
        r = protocol.parse_response("d\tA140\t3000\n")
        self.assertEqual((r.op, r.arg, r.result), ("d", "A140", "3000"))

    def test_valid_decode_results(self):
        for res in ["3000", "00CA 0304", "FFFD 0030", "0041 !", "!", "-", "!001A 0030", "20086", "10FFFF"]:
            protocol.validate_result("d", res)

    def test_invalid_decode_results(self):
        for res in ["", "30", "3000 ", "! 0030", "GGGG", "110000", "1234567", "!GG", "3000  0030"]:
            with self.subTest(res=res), self.assertRaises(protocol.ProtocolError):
                protocol.validate_result("d", res)

    def test_encode_results(self):
        for res in ["A440", "41", "!", "-", "8BC5"]:
            protocol.validate_result("e", res)
        for res in ["A44", "a440", "! ", "A4 40", ""]:
            with self.subTest(res=res), self.assertRaises(protocol.ProtocolError):
                protocol.validate_result("e", res)

    def test_bad_lines(self):
        for line in ["d\tA140", "x\tA140\t3000", "d\tA140\t3000\textra"]:
            with self.subTest(line=line), self.assertRaises(protocol.ProtocolError):
                protocol.parse_response(line)

    def test_decode_tokens_treat_replacements_as_errors(self):
        self.assertEqual(protocol.decode_tokens("FFFD 0030"), ["!", "0030"])
        self.assertEqual(protocol.decode_tokens("!001A 001C"), ["!", "001C"])
        self.assertEqual(protocol.decode_tokens("-"), [])
        self.assertTrue(protocol.is_clean_decode("00CA 0304"))
        self.assertFalse(protocol.is_clean_decode("0041 !"))

    def test_version(self):
        info = protocol.parse_version("version=Go x/text v0.42.0\nkey=v0.42.0\nkey.other=1\n")
        self.assertEqual(info["key"], "v0.42.0")
        with self.assertRaises(protocol.ProtocolError):
            protocol.parse_version("version=only\n")

    def test_argument_formatting(self):
        self.assertEqual(protocol.bytes_arg(b"\xa1\x40"), "A140")
        self.assertEqual(protocol.cps_arg((0xCA, 0x304)), "00CA 0304")
        self.assertEqual(protocol.parse_cps_arg("00CA 0304"), (0xCA, 0x304))
        self.assertEqual(protocol.format_cps([]), "-")
        self.assertEqual(protocol.format_bytes(b""), "-")
        with self.assertRaises(ValueError):
            protocol.format_request("x", "00")


class CasesTest(unittest.TestCase):
    def test_decode_space(self):
        dc = cases.decode_cases()
        self.assertEqual(len(dc), 256 + 65536)
        self.assertEqual(dc[0], b"\x00")
        self.assertEqual(dc[255], b"\xff")
        self.assertEqual(dc[256], b"\x00\x00")
        self.assertEqual(dc[256 + 0xA1 * 256 + 0x40], b"\xa1\x40")
        self.assertEqual(len(set(dc)), len(dc))

    def test_encode_space(self):
        base = cases.base_encode_cases()
        self.assertEqual(len(base), 0x10000 - 0x800 + 0x10000)
        self.assertNotIn((0xD800,), base)
        self.assertIn((0x2A6DF,), base)

    def test_extras_are_deduplicated_and_sorted_after_the_base(self):
        extra = [(0x00EA, 0x030C), (0x00CA, 0x0304), (0x4E00,), (0x10000,), (0x00CA, 0x0304)]
        ec = cases.encode_cases(extra)
        tail = ec[len(cases.base_encode_cases()):]
        self.assertEqual(tail, [(0x10000,), (0x00CA, 0x0304), (0x00EA, 0x030C)])

    def test_extra_file_round_trip(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "extra.txt"
            cases.write_extra(p, [(0x00CA, 0x0304), (0x4E00,)])
            self.assertEqual(cases.read_extra(p), [(0x00CA, 0x0304)])
            self.assertEqual(cases.read_extra(Path(tmp) / "missing"), [])

    def test_digest_depends_on_order(self):
        self.assertNotEqual(cases.case_digest(["A", "B"]), cases.case_digest(["B", "A"]))


if __name__ == "__main__":
    unittest.main()
