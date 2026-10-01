// Recompute numbers with the site's JavaScript (docs/assets) and print them as JSON, so that
// tests/test_site_js.py can compare them with report/summary.json (computed by Python).
import { readFile } from 'node:fs/promises';

const realFetch = globalThis.fetch;
globalThis.fetch = async (url) => {
  const u = new URL(url);
  if (u.protocol !== 'file:') return realFetch(url);
  try {
    return new Response(await readFile(u));
  } catch {
    return new Response(null, { status: 404 });
  }
};

const data = await import('../../docs/assets/data.js');
const { Decoders } = await import('../../docs/assets/classes.js');

const S = await data.loadSummary();
const out = { classes: {}, by_name: {}, within: {}, chars: {}, eargs: (await data.encodeArgs()).length };

const D = await Decoders.load(S);
for (const c of S.site.classes) out.classes[c.id] = D.classRows(c.id).rows.length;
for (const [id, m] of Object.entries(D.chars)) out.chars[id] = m.size;

const eargs = await data.encodeArgs();
const eindex = await data.encodeIndex();
for (const key of ['big5', 'cp950']) {
  out.by_name[key] = {};
  for (const p of S.site.by_name[key].pairs) {
    const enc = await data.results(p.writer_impl, 'e');
    const r = data.interchange(eargs, enc, D.raw[p.reader_impl]);
    out.by_name[key][`${p.writer}|${p.reader}`] = [r.same, r.changed, r.error];
  }
}
for (const e of Object.keys(S.site.within)) {
  const dec = e === 'dotnet.950-default' ? 'dotnet.950' : e;
  const enc = await data.results(e, 'e');
  const b = data.transcode(D.chars[dec], eindex, enc);
  const t = data.interchange(eargs, enc, D.raw[dec]);
  out.within[e] = [b.same, b.changed, b.lost, t.same, t.changed, t.error];
}
// Query parsing used by the lookup page.
out.queries = ['A1 45', '0xa145', 'U+2027', '兀', 'A1', 'xyz'].map((q) => data.parseQuery(q));
console.log(JSON.stringify(out));
