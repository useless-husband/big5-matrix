// Adapter for Node.js: the built-in WHATWG TextDecoder, and the iconv-lite package (the usual
// way to encode Big5 in Node, which has no built-in Big5 encoder). See big5matrix/protocol.py.
//
// Codecs: "textdecoder:big5" (decode only), "iconv-lite:big5", "iconv-lite:cp950".
import { createRequire } from 'node:module';
import { createInterface } from 'node:readline';

const require = createRequire(import.meta.url);

function codePoints(s) {
  if (s.length === 0) return '-';
  return [...s].map((c) => c.codePointAt(0).toString(16).toUpperCase().padStart(4, '0')).join(' ');
}

function hexBytes(buf) {
  if (buf.length === 0) return '-';
  return Buffer.from(buf).toString('hex').toUpperCase();
}

function fromCodePoints(arg) {
  return String.fromCodePoint(...arg.split(' ').map((x) => parseInt(x, 16)));
}

function codec(name) {
  if (name === 'textdecoder:big5') {
    // decode() without {stream: true} flushes and resets, so each call starts fresh.
    const td = new TextDecoder('big5');
    return {
      decode: (b) => td.decode(b),
      encode: () => {
        throw new Error('TextDecoder has no encoder');
      },
    };
  }
  if (name.startsWith('iconv-lite:')) {
    const iconv = require('iconv-lite');
    const enc = name.slice('iconv-lite:'.length);
    if (!iconv.encodingExists(enc)) throw new Error(`unknown iconv-lite encoding ${enc}`);
    return {
      decode: (b) => iconv.decode(Buffer.from(b), enc),
      // iconv-lite has no strict mode: it writes '?' (0x3F) for a character it cannot encode.
      // 0x3F is never a Big5 trail byte, so a 0x3F in the output for an input without '?' is
      // exactly such a substitution, and is reported as an error.
      encode: (s) => {
        const out = iconv.encode(s, enc);
        if (!s.includes('?') && out.includes(0x3f)) return null;
        return out;
      },
    };
  }
  throw new Error(`unknown codec ${name}`);
}

async function run(name) {
  const { decode, encode } = codec(name);
  const lines = [];
  const rl = createInterface({ input: process.stdin, crlfDelay: Infinity });
  for await (const line of rl) {
    const [op, a] = line.split('\t');
    let res;
    if (op === 'd') {
      res = codePoints(decode(Buffer.from(a, 'hex')));
    } else if (op === 'e') {
      const out = encode(fromCodePoints(a));
      res = out === null ? '!' : hexBytes(out);
    } else {
      throw new Error(`bad op ${op}`);
    }
    lines.push(`${op}\t${a}\t${res}\n`);
    if (lines.length >= 4096) process.stdout.write(lines.splice(0).join(''));
  }
  process.stdout.write(lines.join(''));
}

const arg = process.argv[2];
if (arg === '--version') {
  const iconvVersion = require('iconv-lite/package.json').version;
  console.log(`version=Node ${process.versions.node} (ICU ${process.versions.icu}), iconv-lite ${iconvVersion}`);
  // TextDecoder depends on Node (and its bundled ICU); iconv-lite is plain JavaScript.
  console.log(`key=node-${process.versions.node}`);
  console.log(`key.iconv-lite:big5=iconv-lite-${iconvVersion}`);
  console.log(`key.iconv-lite:cp950=iconv-lite-${iconvVersion}`);
} else {
  await run(arg);
}
