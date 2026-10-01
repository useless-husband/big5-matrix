import unittest

from big5matrix import analyze
from big5matrix.model import Model, is_clean, norm_decode, region
from big5matrix.registry import Impl


def model(decoders: dict, encoders: dict | None = None, strict=()) -> Model:
    """A tiny model: decoders maps id -> {case: raw result}; encoders id -> {code points: bytes}."""
    m = Model()
    ids = list(decoders) + [e for e in (encoders or {}) if e not in decoders]
    m.impls = [Impl(i, i.split(".")[0], "c", i, ops=("d" if i in decoders else "") + ("e" if encoders and i in encoders else ""),
                    error_model="strict" if i in strict else "replace") for i in ids]
    m.dec = {i: {a: norm_decode(r) for a, r in d.items()} for i, d in decoders.items()}
    m.enc = dict(encoders or {})
    m.dargs = sorted({a for d in decoders.values() for a in d}, key=lambda a: (len(a), a))
    m.eargs = sorted({a for e in (encoders or {}).values() for a in e})
    m.manifest = {"impls": {}}
    return m


class NormaliseTest(unittest.TestCase):
    def test_norm_and_clean(self):
        self.assertEqual(norm_decode("FFFD 0030"), "! 0030")
        self.assertEqual(norm_decode("-"), "-")
        self.assertTrue(is_clean("3000"))
        self.assertFalse(is_clean("-"))
        self.assertFalse(is_clean("! 0030"))

    def test_regions(self):
        expect = {"41": "ascii", "80": "byte-80-ff", "A1": "lone-lead", "4141": "ascii-first", "8041": "byte-80-ff",
                  "A130": "ascii-after-lead", "A17F": "ascii-after-lead", "A180": "bad-trail", "A1FF": "bad-trail",
                  "8140": "eudc-8140", "A0FE": "eudc-8140", "A140": "symbols", "A3BF": "symbols", "A3E1": "a3c0",
                  "A440": "hanzi1", "C67E": "hanzi1", "C6A1": "c6a1", "C8FE": "c6a1", "C940": "hanzi2",
                  "F9D5": "hanzi2", "F9D6": "f9d6", "F9FE": "f9d6", "FA40": "eudc-fa40", "FEFE": "eudc-fa40"}
        for a, r in expect.items():
            with self.subTest(a=a):
                self.assertEqual(region(a), r)


class RecoveryTest(unittest.TestCase):
    def setUp(self):
        singles = {"30": "0030", "41": "0041", "A1": "FFFD", "80": "FFFD"}
        self.m = model({
            "keep.x": {**singles, "A130": "FFFD 0030", "A141": "FF0C", "A180": "FFFD FFFD"},
            "swallow.x": {**singles, "A130": "FFFD", "A141": "FFFD", "A180": "FFFD"},
            "strict.x": {**singles, "A1": "!", "A130": "!", "A141": "FF0C", "A180": "!"},
            "drop.x": {**singles, "A1": "-", "A130": "FFFD 0030", "A141": "FF0C", "A180": "FFFD 0030"},
        }, strict=("strict.x",))

    def test_outcomes(self):
        o = analyze.recovery_outcome
        self.assertEqual(o(self.m, "keep.x", "A130"), "kept")
        self.assertEqual(o(self.m, "keep.x", "A141"), "character")
        self.assertEqual(o(self.m, "keep.x", "A180"), "two errors")
        self.assertEqual(o(self.m, "swallow.x", "A130"), "swallowed")
        self.assertEqual(o(self.m, "swallow.x", "A141"), "swallowed")
        self.assertEqual(o(self.m, "strict.x", "A130"), "stops")
        self.assertEqual(o(self.m, "drop.x", "A180"), "other")

    def test_lone_lead(self):
        o = analyze.lone_lead_outcome
        self.assertEqual(o(self.m, "keep.x", "A1"), "error")
        self.assertEqual(o(self.m, "strict.x", "A1"), "stops")
        self.assertEqual(o(self.m, "drop.x", "A1"), "dropped")


class CharacterMapTest(unittest.TestCase):
    def test_lead_bytes_and_character_map(self):
        m = model({
            "w.x": {"80": "0080", "A1": "FFFD", "8041": "0080 0041", "A140": "3000", "A130": "FFFD 0030"},
            "v.x": {"80": "FFFD", "A1": "FFFD", "8041": "FFFD 0041", "A140": "3001", "A130": "FFFD 0030"},
        })
        self.assertEqual(m.chars["w.x"], {"80": "0080", "A140": "3000"})  # 80 41 is two characters
        self.assertEqual(m.chars["v.x"], {"A140": "3001"})
        self.assertEqual(analyze.char_distance(m, "w.x", "v.x"), 2)  # 80 and A140

    def test_families_use_single_linkage(self):
        d = {"a": {"a": 0, "b": 10, "c": 500}, "b": {"a": 10, "b": 0, "c": 300}, "c": {"a": 500, "b": 300, "c": 0},
             "z": {"a": 900, "b": 900, "c": 900, "z": 0}}
        for k in ("a", "b", "c"):
            d[k]["z"] = 900
        m = model({k + ".x": {} for k in "abcz"})
        m.scope = lambda i: None
        fam = analyze.families(m, d, threshold=400)
        self.assertEqual(fam, [["a", "b", "c"], ["z"]])


class EncodingTest(unittest.TestCase):
    def test_substitution(self):
        self.assertTrue(analyze.is_substitution("00AD", "3F"))
        self.assertTrue(analyze.is_substitution("20000", "3F3F"))
        self.assertFalse(analyze.is_substitution("003F", "3F"))
        self.assertFalse(analyze.is_substitution("00CA 0304", "453F"))

    def test_oneway_kinds(self):
        k = analyze.oneway_kind
        self.assertEqual(k("00AD", "2D", "002D"), "to-ascii")
        self.assertEqual(k("E000", "FA40", "20547"), "pua-input")
        self.assertEqual(k("02CD", "A1C5", "!"), "undecodable")
        self.assertEqual(k("2022", "A145", "2027"), "other")
        self.assertEqual(k("4E02", "3F", "003F"), "substituted")

    def test_interchange_and_transcode(self):
        m = model(
            {"r.x": {"A1": "FFFD", "A145": "2027", "A140": "3000", "88": "FFFD", "8862": "FFFD 0062", "2D": "002D", "3F": "003F"}},
            {"w.x": {"2022": "A145", "3000": "A140", "00CA 0304": "8862", "00AD": "2D", "4E02": "3F", "2027": "!"}},
        )
        r = analyze.interchange(m, "w.x", "r.x", detail=True)
        self.assertEqual((r["same"], r["changed"], r["error"], r["substituted"]), (1, 2, 1, 1))
        self.assertEqual(sorted(x[0] for x in r["rows"]), ["00AD", "00CA 0304", "2022"])
        m.enc["r.x"] = m.enc.pop("w.x")
        t = analyze.transcode(m, "r.x", "r.x", detail=True)
        self.assertEqual((t["same"], t["changed"], t["lost"]), (1, 0, 1))  # A140 same, A145 -> U+2027 lost


if __name__ == "__main__":
    unittest.main()
