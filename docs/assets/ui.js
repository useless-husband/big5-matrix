// Page chrome and small rendering helpers shared by the pages.

export const REPO = 'https://github.com/useless-husband/big5-matrix';

export function header(active) {
  const links = [
    ['index.html', 'Overview'],
    ['lookup.html', 'Look up'],
    ['classes.html', 'Divergences'],
    ['pair.html', 'Writer → reader'],
    ['impl.html', 'Implementations'],
    [`${REPO}/blob/main/docs/divergences.md`, 'Report'],
    [REPO, 'Source'],
  ];
  const nav = links.map(([href, label]) => (label === active
    ? `<strong>${label}</strong>` : `<a href="${href}">${label}</a>`)).join('');
  const h = document.createElement('header');
  h.className = 'site';
  h.innerHTML = `<div class="inner"><nav><a class="name" href="index.html">big5-matrix</a>${nav}</nav></div>`;
  document.body.prepend(h);
}

export function esc(s) {
  return String(s).replace(/[&<>"']/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
}

export const fmt = (n) => (typeof n === 'number' ? n.toLocaleString('en-US') : String(n));

export function implLink(id) {
  return `<a class="chip" href="impl.html?id=${encodeURIComponent(id)}">${esc(id)}</a>`;
}

export function param(name) {
  return new URLSearchParams(location.search).get(name);
}

export function status(el, text) {
  el.textContent = text;
}

/** Render rows as an HTML table. cols: [{label, num?}], rows: arrays of HTML strings. */
export function table(cols, rows, cls = '') {
  const head = cols.map((c) => `<th class="${c.num ? 'num' : ''}">${esc(c.label)}</th>`).join('');
  const body = rows.map((r) => `<tr>${r.map((v, i) => `<td class="${cols[i] && cols[i].num ? 'num' : ''}">${v}</td>`).join('')}</tr>`).join('');
  return `<div class="scroll"><table class="${cls}"><thead><tr>${head}</tr></thead><tbody>${body}</tbody></table></div>`;
}

export function bytesLabel(hex) {
  return hex.match(/../g).join(' ');
}
