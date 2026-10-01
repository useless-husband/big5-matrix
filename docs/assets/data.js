// Reading the committed data in the browser (or in Node for the tests).
//
// The site has no data of its own: it reads data/<op>/<impl>.txt.gz (decompressed here with
// DecompressionStream) and report/summary.json, so it cannot disagree with them. The logic below
// mirrors big5matrix/cases.py, protocol.py and analyze.py; tests/test_site_js.py checks that the
// two give the same numbers.

const BASE = new URL('../../', import.meta.url);
const cache = new Map();

async function fetchBytes(path) {
  const res = await fetch(new URL(path, BASE));
  if (!res.ok) throw new Error(`${path}: HTTP ${res.status}`);
  return res;
}

export async function loadSummary() {
  if (!cache.has('summary')) {
    cache.set('summary', fetchBytes('report/summary.json').then((r) => r.json()));
  }
  return cache.get('summary');
}

async function gunzipText(res) {
  const stream = res.body.pipeThrough(new DecompressionStream('gzip'));
  return new Response(stream).text();
}

// ---------------------------------------------------------------------------------------------
// Case lists (same order as big5matrix/cases.py)

const hex2 = (n) => n.toString(16).toUpperCase().padStart(2, '0');
const hex4 = (n) => n.toString(16).toUpperCase().padStart(4, '0');

let decodeArgsCache = null;
export function decodeArgs() {
  if (!decodeArgsCache) {
    const out = [];
    for (let b = 0; b < 256; b++) out.push(hex2(b));
    for (let l = 0; l < 256; l++) for (let t = 0; t < 256; t++) out.push(hex2(l) + hex2(t));
    decodeArgsCache = out;
  }
  return decodeArgsCache;
}

/** Index of a decode case given as hex ("A1" or "A140"). */
export function decodeIndex(arg) {
  if (arg.length === 2) return parseInt(arg, 16);
  return 256 + parseInt(arg.slice(0, 2), 16) * 256 + parseInt(arg.slice(2, 4), 16);
}

export function parseExtra(text) {
  return text.split('\n').map((l) => l.trim()).filter((l) => l && !l.startsWith('#'))
    .map((l) => l.split(/\s+/).map((x) => parseInt(x, 16)));
}

export function encodeArgsFrom(extra) {
  const out = [];
  for (let c = 0; c < 0x10000; c++) if (c < 0xd800 || c > 0xdfff) out.push(hex4(c));
  for (let c = 0x20000; c < 0x30000; c++) out.push(hex4(c));
  const inBase = (s) => s.length === 1 && (s[0] < 0x10000 || (s[0] >= 0x20000 && s[0] < 0x30000));
  const more = extra.filter((s) => !inBase(s));
  more.sort((a, b) => {
    if (a.length !== b.length) return a.length - b.length;
    for (let i = 0; i < a.length; i++) if (a[i] !== b[i]) return a[i] - b[i];
    return 0;
  });
  const seen = new Set();
  for (const s of more) {
    const k = s.map(hex4).join(' ');
    if (!seen.has(k)) { seen.add(k); out.push(k); }
  }
  return out;
}

export async function encodeArgs() {
  if (!cache.has('eargs')) {
    cache.set('eargs', fetchBytes('data/encode-extra.txt').then((r) => r.text())
      .then((t) => encodeArgsFrom(parseExtra(t))));
  }
  return cache.get('eargs');
}

export async function encodeIndex() {
  if (!cache.has('eindex')) {
    cache.set('eindex', encodeArgs().then((args) => new Map(args.map((a, i) => [a, i]))));
  }
  return cache.get('eindex');
}

// ---------------------------------------------------------------------------------------------
// Result files

const OPS = { d: 'decode', e: 'encode' };

/** All results of one implementation for one operation, in case order; '*' = outside scope. */
export async function results(implId, op) {
  const key = `${op}:${implId}`;
  if (!cache.has(key)) {
    cache.set(key, (async () => {
      const text = await gunzipText(await fetchBytes(`data/${OPS[op]}/${implId}.txt.gz`));
      const lines = text.split('\n');
      if (lines[lines.length - 1] === '') lines.pop();
      const header = lines.shift();
      const m = /^#big5-matrix v1 op=(\w+) cases=(\d+) /.exec(header);
      const expected = op === 'd' ? decodeArgs().length : (await encodeArgs()).length;
      if (!m || m[1] !== OPS[op] || Number(m[2]) !== expected || lines.length !== expected) {
        throw new Error(`${implId} ${OPS[op]}: data does not match the case list`);
      }
      return lines;
    })());
  }
  return cache.get(key);
}

// ---------------------------------------------------------------------------------------------
// Normalisation (big5matrix/protocol.py decode_tokens, model.norm_decode)

export const ERR = '!';
export const EMPTY = '-';

export function normDecode(r) {
  if (r === EMPTY || r === '*') return r;
  return r.split(' ').map((t) => (t === 'FFFD' || t.startsWith('!') ? ERR : t)).join(' ');
}

export function isClean(n) {
  return n !== EMPTY && n !== '*' && !n.split(' ').includes(ERR);
}

export function isSubstitution(arg, bytes) {
  if (!bytes || bytes === ERR || bytes === EMPTY || bytes.length % 2) return false;
  for (let i = 0; i < bytes.length; i += 2) if (bytes.slice(i, i + 2) !== '3F') return false;
  return !arg.split(' ').includes('003F');
}

/** The character map of a decoder: non-ASCII single bytes and two-byte sequences that decode,
 * without error, as one character (model.Model.chars). Returns Map(bytes hex -> normalised). */
export function charMap(dec) {
  const norm = (i) => normDecode(dec[i]);
  const leads = new Set();
  for (let x = 0x80; x < 0x100; x++) {
    const r = dec[x];
    if (r === '*' || !isClean(norm(x))) leads.add(x);
  }
  const map = new Map();
  for (let x = 0x80; x < 0x100; x++) if (!leads.has(x) && dec[x] !== '*') map.set(hex2(x), norm(x));
  for (const l of [...leads].sort((a, b) => a - b)) {
    for (let t = 0; t < 256; t++) {
      const i = 256 + l * 256 + t;
      if (dec[i] === '*') continue;
      const n = norm(i);
      if (isClean(n)) map.set(hex2(l) + hex2(t), n);
    }
  }
  return map;
}

// ---------------------------------------------------------------------------------------------
// Round trips (analyze.interchange / analyze.transcode)

const isPua = (h) => {
  const c = parseInt(h.split(' ')[0], 16);
  return (c >= 0xe000 && c <= 0xf8ff) || (c >= 0xf0000 && c <= 0x10fffd);
};

/** Text -> bytes with the writer -> text with the reader. */
export function interchange(eargs, enc, dec, { rows = false } = {}) {
  const c = { same: 0, changed: 0, error: 0, changed_pua: 0, error_pua: 0, substituted: 0, untested: 0 };
  const out = [];
  for (let i = 0; i < eargs.length; i++) {
    const a = eargs[i];
    const b = enc[i];
    if (b === ERR || b === EMPTY) continue;
    if (isSubstitution(a, b)) { c.substituted++; continue; }
    if (b.length > 4) { c.untested++; continue; }
    const raw = dec[decodeIndex(b)];
    if (raw === '*') { c.untested++; continue; }
    const back = normDecode(raw);
    if (back === a) { c.same++; continue; }
    const k = isClean(back) ? 'changed' : 'error';
    c[k]++;
    if (isPua(a)) c[`${k}_pua`]++;
    if (rows) out.push([a, b, back, k]);
  }
  return rows ? { ...c, rows: out } : c;
}

/** Bytes -> text with the reader -> bytes with the writer. */
export function transcode(chars, eindex, enc, { rows = false } = {}) {
  const c = { same: 0, changed: 0, lost: 0, changed_pua: 0, lost_pua: 0, untested: 0 };
  const out = [];
  for (const [code, text] of chars) {
    const i = eindex.get(text);
    if (i === undefined) { c.untested++; continue; }
    const b = enc[i];
    if (b === code) { c.same++; continue; }
    const k = b !== ERR && b !== EMPTY && !isSubstitution(text, b) ? 'changed' : 'lost';
    c[k]++;
    if (isPua(text)) c[`${k}_pua`]++;
    if (rows) out.push([code, text, b, k]);
  }
  return rows ? { ...c, rows: out } : c;
}

// ---------------------------------------------------------------------------------------------
// Presentation helpers shared by the pages

/** A code point sequence as text, when it is safe to show it. */
export function glyph(hexes) {
  if (!hexes || hexes === ERR || hexes === EMPTY || hexes === '*') return '';
  const cps = hexes.split(' ').filter((t) => t !== ERR).map((t) => parseInt(t, 16));
  if (cps.some((c) => c < 0x20 || (c >= 0x7f && c < 0xa0) || (c >= 0xd800 && c <= 0xdfff) || c === 0xad
    || (c >= 0xe000 && c <= 0xf8ff))) return '';
  return String.fromCodePoint(...cps);
}

export function cpLabel(hexes) {
  if (hexes === ERR) return 'error';
  if (hexes === EMPTY) return 'nothing';
  if (hexes === '*') return 'outside this table';
  return hexes.split(' ').map((t) => (t === ERR ? 'error' : `U+${t}`)).join(' ');
}

/** Parse what a visitor typed: hex bytes ("A1 45", "0xA145", "a145"), "U+2027", or a character. */
export function parseQuery(q) {
  const s = q.trim();
  let m = /^(?:U\+|u\+)([0-9a-fA-F]{4,6})$/.exec(s);
  if (m) return { op: 'e', arg: hex4(parseInt(m[1], 16)) };
  const h = s.replace(/^0x/i, '').replace(/[\s,]+/g, '');
  if (/^([0-9a-fA-F]{2}|[0-9a-fA-F]{4})$/.test(h)) return { op: 'd', arg: h.toUpperCase() };
  const chars = [...s];
  if (chars.length === 1) return { op: 'e', arg: hex4(chars[0].codePointAt(0)) };
  return null;
}
