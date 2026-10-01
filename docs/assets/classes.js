// Divergence classes, computed from the decode results exactly as big5matrix/analyze.py does
// (decode_classes, recovery_outcome, lone_lead_outcome). tests/test_site_js.py compares the
// counts with report/summary.json.
import { decodeArgs, results, normDecode, isClean, charMap, ERR, EMPTY } from './data.js';

const isTrail = (t) => (t >= 0x40 && t <= 0x7e) || (t >= 0xa1 && t <= 0xfe);

export function region(arg) {
  const b = arg.match(/../g).map((x) => parseInt(x, 16));
  if (b.length === 1) {
    if (b[0] < 0x80) return 'ascii';
    if (b[0] === 0x80 || b[0] === 0xff) return 'byte-80-ff';
    return 'lone-lead';
  }
  const [l, t] = b;
  if (l < 0x80) return 'ascii-first';
  if (l === 0x80 || l === 0xff) return 'byte-80-ff';
  if (t < 0x80 && !isTrail(t)) return 'ascii-after-lead';
  if (!isTrail(t)) return 'bad-trail';
  const c = l * 256 + t;
  if (l <= 0xa0) return 'eudc-8140';
  if (c <= 0xa3bf) return 'symbols';
  if (c <= 0xa3fe) return 'a3c0';
  if (c <= 0xc67e) return 'hanzi1';
  if (c <= 0xc8fe) return 'c6a1';
  if (c <= 0xf9d5) return 'hanzi2';
  if (c <= 0xf9fe) return 'f9d6';
  return 'eudc-fa40';
}

export const CODE_REGIONS = ['eudc-8140', 'symbols', 'a3c0', 'hanzi1', 'c6a1', 'hanzi2', 'f9d6', 'eudc-fa40'];

const toks = (n) => (n === EMPTY ? [] : n.split(' '));
const same = (a, b) => a.length === b.length && a.every((x, i) => x === b[i]);

export class Decoders {
  constructor(impls, raw) {
    this.impls = impls; // [{id, kind, error_model, ...}]
    this.raw = raw; // id -> array of raw results
    this.norm = {};
    this.chars = {};
    for (const im of impls) {
      this.norm[im.id] = raw[im.id].map((r) => normDecode(r));
      this.chars[im.id] = charMap(raw[im.id]);
    }
  }

  static async load(summary, onProgress = () => {}) {
    const impls = summary.site.impls.filter((i) => i.ops.includes('d'));
    let done = 0;
    const raw = {};
    await Promise.all(impls.map((im) => results(im.id, 'd').then((r) => {
      raw[im.id] = r;
      onProgress(++done, impls.length);
    })));
    return new Decoders(impls, raw);
  }

  partial(id) { return this.raw[id][0x80] === '*'; }

  errorParticipants() { return this.impls.filter((i) => i.kind === 'run' || i.id === 'ref.whatwg'); }

  value(id, i) { return this.norm[id][i]; }

  recovery(im, arg, i) {
    if (this.chars[im.id].has(arg)) return 'character';
    const r = toks(this.norm[im.id][i]);
    if (im.error_model === 'strict') return r.length && r[r.length - 1] === ERR ? 'stops' : 'other';
    const second = toks(this.norm[im.id][parseInt(arg.slice(2), 16)]);
    if (second.length && !second.includes(ERR) && same(r, [ERR, ...second])) return 'kept';
    if (same(r, [ERR])) return 'swallowed';
    if (same(r, [ERR, ERR])) return 'two errors';
    if (!r.length) return 'dropped';
    return 'other';
  }

  lone(im, i) {
    const r = this.norm[im.id][i];
    if (r === EMPTY) return 'dropped';
    if (r === ERR) return im.error_model === 'strict' ? 'stops' : 'error';
    if (isClean(r)) return 'character';
    return 'other';
  }

  /** The divergent cases of one class: [{case, groups: [[value, [ids]]]}], largest group first. */
  classRows(rid) {
    const args = decodeArgs();
    let cases;
    let kind;
    if (rid === 'ascii-after-lead') {
      cases = [];
      for (let l = 0x81; l <= 0xfe; l++) for (let t = 0; t < 0x80; t++) cases.push(256 + l * 256 + t);
      kind = 'recovery';
    } else {
      cases = [];
      for (let i = 0; i < args.length; i++) if (region(args[i]) === rid) cases.push(i);
      kind = rid === 'bad-trail' ? 'recovery' : rid === 'lone-lead' ? 'lone' : CODE_REGIONS.includes(rid) ? 'mapping' : 'full';
    }
    const errParts = this.errorParticipants();
    const rows = [];
    for (const i of cases) {
      const a = args[i];
      const view = new Map();
      const put = (v, id) => { if (!view.has(v)) view.set(v, []); view.get(v).push(id); };
      if (kind === 'mapping') {
        for (const im of this.impls) {
          if (this.raw[im.id][i] === '*') continue;
          put(this.chars[im.id].get(a) ?? ERR, im.id);
        }
      } else if (kind === 'recovery') {
        for (const im of errParts) put(this.recovery(im, a, i), im.id);
      } else if (kind === 'lone') {
        for (const im of errParts) put(this.lone(im, i), im.id);
      } else {
        const parts = rid === 'byte-80-ff' && a.length === 2 ? this.impls : errParts;
        for (const im of parts) {
          if (this.raw[im.id][i] === '*') continue;
          put(this.norm[im.id][i], im.id);
        }
      }
      if (view.size > 1) {
        rows.push({ case: a, groups: [...view.entries()].sort((x, y) => y[1].length - x[1].length) });
      }
    }
    return { cases: cases.length, kind, rows };
  }
}
