import os
import random
import tempfile
import unittest
from pathlib import Path

from big5matrix import reference as ref

SEED = int(os.environ.get("B5M_SEED", "20261001"))


def dec(w, hexbytes):
    return " ".join(t if t == "!" else f"{t:04X}" for t in w.decode(bytes.fromhex(hexbytes)))


class WhatwgDecoderTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.w = ref.Whatwg(ref.load_whatwg_index())

    def test_spec_examples(self):
        cases = {
            "A140": "3000",  # ideographic space
            "A145": "2027",
            "8862": "00CA 0304",  # the four two-code-point pointers
            "8864": "00CA 030C",
            "88A3": "00EA 0304",
            "88A5": "00EA 030C",
            "A3E1": "20AC",
            "F9FE": "FFED",
            "8740": "43F0",
            "41": "0041",
        }
        for h, want in cases.items():
            with self.subTest(h=h):
                self.assertEqual(dec(self.w, h), want)

    def test_ascii_byte_after_a_lead_is_restored(self):
        # "If byte is an ASCII byte, restore byte to ioQueue": also for 0x40-0x7E when unmapped.
        self.assertEqual(dec(self.w, "A130"), "! 0030")
        self.assertEqual(dec(self.w, "8140"), "! 0040")
        self.assertEqual(dec(self.w, "835C"), "! 005C")
        self.assertEqual(dec(self.w, "A17F"), "! 007F")

    def test_non_ascii_bad_trail_consumes_both_bytes(self):
        self.assertEqual(dec(self.w, "A180"), "!")
        self.assertEqual(dec(self.w, "A1FF"), "!")

    def test_end_of_input_and_single_bytes(self):
        self.assertEqual(dec(self.w, "A1"), "!")
        self.assertEqual(dec(self.w, "80"), "!")
        self.assertEqual(dec(self.w, "FF"), "!")
        self.assertEqual(dec(self.w, "41A1"), "0041 !")

    def test_ascii_prefix_never_changes_the_rest(self):
        """Property: decode(a + x) == decode(a) + decode(x) for an ASCII byte a."""
        rng = random.Random(SEED)
        for _ in range(3000):
            a = bytes([rng.randrange(0x80)])
            x = bytes(rng.randrange(256) for _ in range(rng.randrange(1, 6)))
            with self.subTest(seed=SEED, a=a.hex(), x=x.hex()):
                self.assertEqual(self.w.decode(a + x), self.w.decode(a) + self.w.decode(x))

    def test_every_ascii_byte_survives_or_completes_a_character(self):
        """Property: an ASCII byte is either output as itself or used as the trail of a mapped pair."""
        rng = random.Random(SEED + 1)
        for _ in range(3000):
            x = bytes(rng.choice([rng.randrange(0x80), rng.randrange(0x81, 0xFF)]) for _ in range(rng.randrange(1, 8)))
            out = self.w.decode(x)
            ascii_out = sum(1 for t in out if t != "!" and t < 0x80)
            ascii_in = sum(1 for b in x if b < 0x80)
            with self.subTest(seed=SEED, x=x.hex()):
                self.assertLessEqual(ascii_out, ascii_in)
                # every error stands for at least one input byte
                self.assertLessEqual(out.count("!"), len(x))


class WhatwgEncoderTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.w = ref.Whatwg(ref.load_whatwg_index())

    def test_spec_rules(self):
        self.assertEqual(self.w.encode((0x41,)), b"A")
        self.assertEqual(self.w.encode((0x3000,)), bytes.fromhex("A140"))
        # last pointer for these six code points
        self.assertEqual(self.w.encode((0x5341,)), bytes.fromhex("A451"))
        self.assertEqual(self.w.encode((0x2550,)), bytes.fromhex("F9F9"))
        # HKSCS rows (pointers below (0xA1 - 0x81) * 157) are never written
        self.assertIsNone(self.w.encode((0x43F0,)))
        self.assertIsNone(self.w.encode((0x00CA,)))
        self.assertEqual(self.w.encode((0x20AC,)), bytes.fromhex("A3E1"))
        self.assertIsNone(self.w.encode((0x00CA, 0x0304)))

    def test_every_encodable_code_point_round_trips(self):
        """Property of the WHATWG encoder: what it writes decodes back to the same code point."""
        for cp in sorted(set(self.w.index.values())):
            b = self.w.encode((cp,))
            if b is None:
                continue
            with self.subTest(cp=f"U+{cp:04X}"):
                self.assertEqual(self.w.decode(b), [cp])


class TableTest(unittest.TestCase):
    def test_table_sizes(self):
        self.assertEqual(len(ref.load_unicode_big5().pairs), 13703)
        self.assertEqual(len(ref.load_ms_cp950().pairs), 13503)
        bf = ref.load_ms_bestfit950()
        self.assertEqual(len(bf.pairs), 19720)
        self.assertEqual(len(bf.singles), 130)
        hk = ref.load_hkscs_2016()
        self.assertEqual(len(hk.pairs), 5005 + 4)

    def test_big5txt_unmapped_entries_are_errors(self):
        t = ref.load_unicode_big5()
        self.assertEqual(t.decode(bytes.fromhex("A1C3")), ["!"])
        self.assertEqual(t.decode(bytes.fromhex("A145")), [0x2022])

    def test_bestfit(self):
        bf = ref.load_ms_bestfit950()
        self.assertEqual(bf.encode((0x00AD,)), b"-")  # the soft hyphen best fit
        self.assertEqual(bf.decode(b"\x80"), [0x80])
        self.assertEqual(bf.decode(bytes.fromhex("8140")), [0xEEB8])

    def test_strict_model_stops(self):
        t = ref.load_ms_cp950()
        self.assertEqual(t.decode(bytes.fromhex("41A1")), [0x41, "!"])
        self.assertEqual(t.decode(bytes.fromhex("A130")), ["!"])

    def test_partial_scope(self):
        hk = ref.load_hkscs_2016()
        self.assertTrue(hk.in_scope(bytes.fromhex("8862")))
        self.assertFalse(hk.in_scope(bytes.fromhex("A140")))
        out = ref.run_reference("ref.hkscs-2016", "d", ["A140", "8862"])
        self.assertEqual(out, {"8862": "00CA 0304"})

    def test_decode_only_tables_refuse_to_encode(self):
        with self.assertRaises(ValueError):
            ref.load_ms_cp950().encode((0x41,))

    def test_bestfit_parser_rejects_truncated_sections(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "bad.txt"
            p.write_text("CODEPAGE 950\nMBTABLE 3\n0x00 0x0000\n0x01 0x0001\n")
            with self.assertRaises(ValueError):
                ref.load_ms_bestfit950(p)


if __name__ == "__main__":
    unittest.main()
