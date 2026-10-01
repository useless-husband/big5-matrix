// Adapter for a browser's TextDecoder('big5'): headless Chromium driven by playwright-core.
// See big5matrix/protocol.py. Decode only (browsers expose no Big5 encoder to scripts).
//
// playwright-core never downloads a browser; it uses one installed by `npx playwright install
// chromium` for the same Playwright version. All requests are decoded in one page call.
import { createInterface } from 'node:readline';
import { chromium } from 'playwright-core';

async function withBrowser(fn) {
  const browser = await chromium.launch();
  try {
    return await fn(browser);
  } finally {
    await browser.close();
  }
}

const arg = process.argv[2];
if (arg === '--version') {
  const v = await withBrowser(async (b) => b.version());
  console.log(`version=Chromium ${v} (headless, Playwright)`);
  console.log(`key=chromium-${v}`);
} else if (arg === 'chromium') {
  const reqs = [];
  const rl = createInterface({ input: process.stdin, crlfDelay: Infinity });
  for await (const line of rl) {
    const [op, a] = line.split('\t');
    if (op !== 'd') throw new Error('the browser adapter only decodes');
    reqs.push(a);
  }
  const results = await withBrowser(async (browser) => {
    const page = await browser.newPage();
    return page.evaluate((hexes) => {
      const out = [];
      for (const h of hexes) {
        const bytes = new Uint8Array(h.length / 2);
        for (let i = 0; i < bytes.length; i++) bytes[i] = parseInt(h.slice(2 * i, 2 * i + 2), 16);
        // A fresh decoder per case; decode() without {stream: true} flushes at the end.
        const s = new TextDecoder('big5').decode(bytes);
        const cps = [...s].map((c) => c.codePointAt(0).toString(16).toUpperCase().padStart(4, '0'));
        out.push(cps.length ? cps.join(' ') : '-');
      }
      return out;
    }, reqs);
  });
  process.stdout.write(reqs.map((a, i) => `d\t${a}\t${results[i]}\n`).join(''));
} else {
  throw new Error(`unknown codec ${arg}`);
}
