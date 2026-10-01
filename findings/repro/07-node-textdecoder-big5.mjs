// Node.js TextDecoder('big5') versus the WHATWG Big5 decoder. Run: node 07-node-textdecoder-big5.mjs
const show = (s) => [...s].map((c) => 'U+' + c.codePointAt(0).toString(16).toUpperCase().padStart(4, '0')).join(' ');
const cases = {
  '835C': 'U+FFFD U+005C',
  '8862': 'U+00CA U+0304',
  '80': 'U+FFFD',
  'FF': 'U+FFFD',
  'FEFE': 'U+79D4',
};
console.log(`Node ${process.versions.node}, ICU ${process.versions.icu}`);
for (const [hex, whatwg] of Object.entries(cases)) {
  const got = show(new TextDecoder('big5').decode(Buffer.from(hex, 'hex')));
  console.log(`${hex}: node ${got.padEnd(16)} WHATWG ${whatwg}`);
}
