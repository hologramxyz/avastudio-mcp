const fs = require('fs');
const path = require('path');
const crypto = require('crypto');
const puppeteer = (() => {
  const hf = (process.env.NODE_PATH || '').split(path.delimiter).filter(Boolean).map((d) => path.join(d, 'hyperframes', 'node_modules', 'puppeteer-core'));
  for (const p of [process.env.PUPPETEER, 'puppeteer-core', ...hf]) {
    if (!p) continue;
    try { return require(p); } catch (e) { if (e.code !== 'MODULE_NOT_FOUND') throw e; }
  }
  throw new Error('puppeteer-core not found: run with NODE_PATH=$(npm root -g) and a global hyperframes, or set PUPPETEER to its path');
})();

const [url, out, W = '1440', H = '900'] = process.argv.slice(2);
const CHROME = process.env.CHROME || ['/usr/bin/google-chrome', '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome'].find((p) => fs.existsSync(p)) || (() => {
  try { return require('child_process').execSync('npx --yes hyperframes@0.9.19 browser path', { encoding: 'utf8', stdio: ['ignore', 'pipe', 'ignore'] }).trim().split('\n').pop(); } catch (e) { return undefined; }
})();
const wait = (ms) => new Promise((r) => setTimeout(r, ms));
const AS = path.join(out, 'assets/cap');
fs.mkdirSync(AS, { recursive: true });

function scopeSelectors(css) {
  return css.replace(/[^{}]*[{}]/g, (chunk) => {
    if (!chunk.endsWith('{')) return chunk;
    const cut = chunk.lastIndexOf(';') + 1;
    const pre = chunk.slice(cut).replace(/(^|[\s,>+~(}])(html|body)(?=[\s.#:[,>+~{)])/g, (m, a, t) => a + (t === 'html' ? '.cap-html' : '.cap-body'));
    return chunk.slice(0, cut) + pre;
  });
}

function viewportUnits(css, w, h) {
  return css.replace(/(-?\d*\.?\d+)(dvh|svh|lvh|vh|dvw|svw|lvw|vw|vmin|vmax)\b/g, (m, v, u) => {
    const base = u.endsWith('h') ? h : u.endsWith('w') ? w : u === 'vmin' ? Math.min(w, h) : Math.max(w, h);
    return +(parseFloat(v) * base / 100).toFixed(3) + 'px';
  });
}

(async () => {
  const b = await puppeteer.launch({ executablePath: CHROME, headless: 'new', args: ['--no-sandbox', '--hide-scrollbars', '--disable-gpu'] });
  const g = await b.newPage();
  await g.setViewport({ width: +W, height: +H, deviceScaleFactor: 1 });
  await g.goto(url, { waitUntil: 'domcontentloaded', timeout: 90000 });
  for (let i = 0; i < 60 && (await g.evaluate(() => document.readyState)) !== 'complete'; i++) await wait(500);
  await g.waitForNetworkIdle({ idleTime: 800, concurrency: 2, timeout: 20000 }).catch(() => {});
  await wait(2000);
  const sh = await g.evaluate(() => document.documentElement.scrollHeight);
  for (let y = 0; y < sh; y += Math.round(+H * 0.8)) { await g.evaluate((v) => window.scrollTo(0, v), y); await wait(150); }
  await g.evaluate(() => window.scrollTo(0, 0));
  await wait(1200);

  await g.evaluate(() => { for (const a of document.getAnimations()) { try { a.finish(); } catch (e) {} } });
  await wait(300);
  await g.evaluate(() => {
    for (const el of document.querySelectorAll('body *')) {
      const cs = getComputedStyle(el);
      if (cs.animationName && cs.animationName !== 'none') {
        el.style.opacity = cs.opacity;
        if (cs.transform !== 'none') el.style.transform = cs.transform;
      }
      if (cs.position === 'fixed' || cs.position === 'sticky') el.setAttribute('data-cap-pos', cs.position);
    }
    for (const el of document.querySelectorAll('input')) {
      if (el.type === 'checkbox' || el.type === 'radio') { if (el.checked) el.setAttribute('checked', ''); } else el.setAttribute('value', el.value);
    }
    for (const el of document.querySelectorAll('textarea')) el.textContent = el.value;
  });

  const media = await g.evaluate(() => {
    let i = 0;
    const out = [];
    for (const el of document.querySelectorAll('body canvas, body video, body iframe')) {
      const r = el.getBoundingClientRect();
      if (r.width < 3 || r.height < 3 || getComputedStyle(el).visibility === 'hidden') { el.setAttribute('data-cap-drop', ''); continue; }
      el.setAttribute('data-cap-shot', String(i));
      const cs = getComputedStyle(el), lay = ['position', 'top', 'right', 'bottom', 'left', 'z-index', 'margin', 'float', 'flex', 'align-self', 'order', 'grid-area'].map((k) => `${k}:${cs.getPropertyValue(k)}`).join(';');
      out.push({ i, w: r.width, h: r.height, lay, tag: el.tagName.toLowerCase(), src: el.tagName === 'VIDEO' ? el.currentSrc || el.src || undefined : undefined, fit: `object-fit:${cs.objectFit};object-position:${cs.objectPosition}` });
      i++;
    }
    return out;
  });
  const soloTag = await g.addStyleTag({ content: 'body.cap-solo * { visibility: hidden !important; } body.cap-solo [data-cap-on] { visibility: visible !important; }' });
  for (const m of media) {
    const h = await g.$(`[data-cap-shot="${m.i}"]`);
    if (!h) { m.err = 'gone'; continue; }
    const file = `shot-${m.i}.png`;
    await h.evaluate((el) => { for (let e = el; e && e !== document.body; e = e.parentElement) e.setAttribute('data-cap-on', ''); document.body.classList.add('cap-solo'); });
    try { await h.screenshot({ path: path.join(AS, file) }); m.file = file; } catch (e) { m.err = String(e.message).slice(0, 120); }
    await h.evaluate(() => { document.querySelectorAll('[data-cap-on]').forEach((e) => e.removeAttribute('data-cap-on')); document.body.classList.remove('cap-solo'); });
  }
  await soloTag.evaluate((el) => el.remove());
  await g.evaluate(() => window.scrollTo(0, 0));
  await g.evaluate((list) => {
    for (const el of document.querySelectorAll('[data-cap-drop]')) el.remove();
    for (const m of list) {
      const el = document.querySelector(`[data-cap-shot="${m.i}"]`);
      if (!el) continue;
      if (!m.file) { el.remove(); continue; }
      const img = document.createElement('img');
      img.className = el.className && typeof el.className === 'string' ? el.className : '';
      if (el.id) img.id = el.id;
      img.setAttribute('src', '__CAP__/' + m.file);
      img.setAttribute('style', (el.getAttribute('style') || '') + `;${m.lay};width:${m.w}px;height:${m.h}px;display:block;object-fit:fill`);
      if (el.hasAttribute('data-cap-pos')) img.setAttribute('data-cap-pos', el.getAttribute('data-cap-pos'));
      img.setAttribute('data-cap-was', m.tag);
      if (m.src) { img.setAttribute('data-cap-video', m.src); img.setAttribute('data-cap-fit', m.fit); }
      el.replaceWith(img);
    }
  }, media);

  const unrolled = await g.evaluate(() => {
    if (document.body.scrollHeight > innerHeight + 10) return false;
    let main = null;
    for (const e of document.querySelectorAll('*')) {
      if (e.scrollHeight > e.clientHeight + 10 && /(auto|scroll)/.test(getComputedStyle(e).overflowY) && (!main || e.scrollHeight > main.scrollHeight)) main = e;
    }
    if (!main) return false;
    main.scrollTop = 0;
    main.style.setProperty('height', 'auto', 'important');
    main.style.setProperty('overflow', 'visible', 'important');
    window.scrollTo(0, 0);
    return true;
  });
  if (unrolled) await wait(1500);

  const sheets = await g.evaluate(() => {
    const abs = (text, base) => text.replace(/url\((['"]?)([^'")]+)\1\)/g, (m, q, u) => {
      if (/^(data:|blob:|#)/.test(u)) return m;
      try { return `url("${new URL(u, base).href}")`; } catch (e) { return m; }
    });
    const ser = (rules) => {
      let s = '';
      for (const r of rules) {
        const base = (r.parentStyleSheet && r.parentStyleSheet.href) || location.href;
        if (r instanceof CSSMediaRule) { if (matchMedia(r.conditionText || r.media.mediaText).matches) s += ser(r.cssRules); }
        else if (r instanceof CSSSupportsRule) { if (CSS.supports(r.conditionText)) s += ser(r.cssRules); }
        else if (r instanceof CSSImportRule) { try { s += ser(r.styleSheet.cssRules); } catch (e) { s += abs(r.cssText, base) + '\n'; } }
        else if (typeof CSSLayerBlockRule !== 'undefined' && r instanceof CSSLayerBlockRule) s += `@layer ${r.name}{${ser(r.cssRules)}}\n`;
        else if (r instanceof CSSStyleRule && (r.style.getPropertyValue('background-clip') || r.style.getPropertyValue('-webkit-background-clip'))) {
          const bc = r.style.getPropertyValue('background-clip') || r.style.getPropertyValue('-webkit-background-clip');
          const t = abs(r.cssText, base), k = t.lastIndexOf('}');
          s += t.slice(0, k) + ` background-clip: ${bc}; -webkit-background-clip: ${bc}; }` + '\n';
        } else s += abs(r.cssText, base) + '\n';
      }
      return s;
    };
    window.__capSer = ser;
    const out = [];
    for (const sh of [...document.styleSheets, ...(document.adoptedStyleSheets || [])]) {
      if (sh.media && sh.media.mediaText && !matchMedia(sh.media.mediaText).matches) continue;
      try { out.push({ href: sh.href, text: ser(sh.cssRules) }); } catch (e) { out.push({ href: sh.href, text: null }); }
    }
    return out;
  });
  const dec = (v) => v.replace(/\\(?:\r\n|[\n\r\f])/g, '').replace(/\\([0-9a-f]{1,6})\s?|\\(.)/gi, (x, h, c) => { if (!h) return c; const n = parseInt(h, 16); return !n || (n >= 0xd800 && n <= 0xdfff) || n > 0x10ffff ? '\ufffd' : String.fromCodePoint(n); });
  const inline = async (text, base, chain) => {
    const out = [];
    let rest = text.replace(/^\s*(?:@charset[^;]*;\s*)?/, '');
    for (;;) {
      const lst = rest.match(/^(?:\s|\/\*[\s\S]*?\*\/)*(@layer\s+[^;{]+;)/i);
      if (lst) { out.push(lst[1]); rest = rest.slice(lst[0].length); continue; }
      const kw = rest.match(/^((?:\s|\/\*[\s\S]*?\*\/)*)@((?:\\[0-9a-f]{1,6}\s?|\\[^\n0-9a-f]|[\w-])+)/i);
      if (kw && kw[2].includes('\\') && dec(kw[2]).toLowerCase() === 'import') rest = kw[1] + '@import' + rest.slice(kw[0].length);
      const m = rest.match(/^(?:\s|\/\*[\s\S]*?\*\/)*@import(?:\s|\/\*[\s\S]*?\*\/)*(?:url\((?:\s|\/\*[\s\S]*?\*\/)*(?:(['"])((?:\\[\s\S]|(?!\1)[^\\])*)\1|((?:\\[0-9a-f]{1,6}\s?|\\[^0-9a-f]|[^'")\s\\])+))(?:\s|\/\*[\s\S]*?\*\/)*\)|(['"])((?:\\[\s\S]|(?!\4)[^\\])*)\4)/i);
      if (!m) break;
      let e = m[0].length, dp = 0, q = '';
      for (; e < rest.length; e++) {
        const ch = rest[e];
        if (q) { if (ch === '\\') e++; else if (ch === q) q = ''; } else if (ch === '\\') e++; else if (rest.startsWith('/*', e)) { const c = rest.indexOf('*/', e + 2); e = c < 0 ? rest.length : c + 1; } else if (ch === '"' || ch === "'") q = ch; else if (ch === '(') dp++; else if (ch === ')') dp--; else if (ch === ';' && dp <= 0) break;
      }
      let u = null;
      try { u = new URL(dec(m[2] ?? m[3] ?? m[5]), base).href; } catch (e) {}
      let cond = rest.slice(m[0].length, e).replace(/\/\*[\s\S]*?\*\//g, ' ').trim(), layer = null, sup = null;
      const lm = cond.match(/^layer(?:\(([^)]*)\))?\s*/i);
      if (lm) { layer = lm[1] || ''; cond = cond.slice(lm[0].length); }
      if (/^supports\(/i.test(cond)) {
        let d = 0, k = 9, sq = '';
        for (; k < cond.length; k++) {
          const ch = cond[k];
          if (sq) { if (ch === '\\') k++; else if (ch === sq) sq = ''; } else if (ch === '\\') k++; else if (ch === '"' || ch === "'") sq = ch; else if (ch === '(') d++; else if (ch === ')' && d-- === 0) break;
        }
        sup = cond.slice(9, k); cond = cond.slice(k + 1).trim();
      }
      let t = '';
      try { if (u && !chain.includes(u)) { const r = await fetch(u, { signal: AbortSignal.timeout(20000) }); t = await inline(await r.text(), r.url || u, [...chain, u]); } } catch (e) {}
      if (cond.trim()) t = `@media ${cond.trim()}{${t}}`;
      if (sup) t = `@supports (${sup}){${t}}`;
      out.push(layer === null ? t : `@layer ${layer}{${t}}`);
      rest = rest.slice(e + 1);
    }
    out.push(rest.replace(/url\((['"]?)([^'")]+)\1\)/g, (m, q, v) => (/^(data:|blob:|#)/.test(v) ? m : `url("${new URL(v, base).href}")`)));
    return out.join('\n');
  };
  for (const s of sheets) {
    if (s.text !== null || !s.href) continue;
    try {
      const r = await fetch(s.href, { signal: AbortSignal.timeout(20000) }), base = r.url || s.href;
      const t = (await inline(await r.text(), base, [s.href])).replace(/url\((['"]?)([^'")]+)\1\)/g, (m, q, u) => (/^(data:|blob:|#)/.test(u) ? m : `url("${new URL(u, base).href}")`));
      s.text = await g.evaluate((t) => { try { const sh = new CSSStyleSheet(); sh.replaceSync(t); return window.__capSer(sh.cssRules); } catch (e) { return t; } }, t);
    } catch (e) { s.text = ''; s.err = String(e.message).slice(0, 120); }
  }

  const page = await g.evaluate(() => {
    for (const el of document.querySelectorAll('img')) {
      const ss = el.getAttribute('srcset') || '';
      let best = null, bv = 0;
      if (ss && !ss.includes('data:')) for (const part of ss.split(/,\s+/)) { const [u, d] = part.trim().split(/\s+/); const v = d ? parseFloat(d) : 1; if (u && v >= bv) { bv = v; best = new URL(u, location.href).href; } }
      const pic = el.parentElement && el.parentElement.tagName === 'PICTURE' && el.parentElement.querySelector('source');
      const src = (pic && el.currentSrc) || best || el.currentSrc || el.src;
      if (src && !(el.getAttribute('src') || '').startsWith('__CAP__')) el.setAttribute('src', src);
      el.removeAttribute('srcset'); el.removeAttribute('sizes'); el.removeAttribute('loading');
    }
    for (const el of document.querySelectorAll('picture source')) el.remove();
    for (const el of document.querySelectorAll('image, use')) {
      for (const a of ['href', 'xlink:href']) {
        const v = el.getAttribute(a);
        if (v && !v.startsWith('#')) { try { el.setAttribute(a, new URL(v, location.href).href); } catch (e) {} }
      }
    }
    for (const el of document.querySelectorAll('[style*="url("]')) {
      el.setAttribute('style', el.getAttribute('style').replace(/url\((['"]?)([^'")]+)\1\)/g, (m, q, u) => (/^(data:|blob:|#)/.test(u) ? m : `url("${new URL(u, location.href).href}")`)));
    }
    const body = document.body.cloneNode(true);
    for (const el of body.querySelectorAll('script, noscript, link, style, template, meta')) el.remove();
    for (const el of body.querySelectorAll('*')) {
      for (const a of [...el.attributes]) if (/^on/i.test(a.name) || /^\s*javascript:/i.test(a.value)) el.removeAttribute(a.name);
    }
    const attrs = (el) => Object.fromEntries([...el.attributes].filter((a) => !/^on/i.test(a.name) && !/^\s*javascript:/i.test(a.value)).map((a) => [a.name, a.value]));
    const fonts = [...new Set([...document.fonts].filter((f) => f.status === 'loaded').map((f) => `${f.family} ${f.weight} ${f.style}`))];
    return { html: body.innerHTML, htmlAttrs: attrs(document.documentElement), bodyAttrs: attrs(document.body), title: document.title, fonts, height: document.documentElement.scrollHeight };
  });

  const sel = 'h1,h2,h3,h4,p,button,a,input,textarea,select,table,thead,tbody,tr,th,td,section,header,nav,footer,form,img,svg,li,[id],[role]';
  const boxes = await g.evaluate((sel) => {
    const pathOf = (el) => {
      const parts = [];
      for (let e = el; e && e !== document.body; e = e.parentElement) {
        if (e.id && /^[A-Za-z][\w-]*$/.test(e.id)) { parts.unshift('#' + e.id); break; }
        const sib = [...e.parentElement.children].filter((x) => x.tagName === e.tagName);
        parts.unshift(e.tagName.toLowerCase() + (sib.length > 1 ? `:nth-of-type(${sib.indexOf(e) + 1})` : ''));
      }
      return parts.join(' > ');
    };
    const out = [];
    for (const el of document.body.querySelectorAll(sel)) {
      const r = el.getBoundingClientRect();
      if (r.width < 2 || r.height < 2) continue;
      out.push({ path: pathOf(el), tag: el.tagName.toLowerCase(), cls: typeof el.className === 'string' ? el.className.slice(0, 80) : '', box: [r.x + scrollX, r.y + scrollY, r.width, r.height].map(Math.round), text: (el.innerText || el.getAttribute('placeholder') || '').trim().replace(/\s+/g, ' ').slice(0, 80) });
      if (out.length >= 5000) break;
    }
    return out;
  }, sel);
  await g.screenshot({ path: path.join(out, 'page.png'), fullPage: true });
  await b.close();

  let css = sheets.map((s) => s.text || '').join('\n');
  let html = page.html;
  const urls = new Set();
  for (const m of css.matchAll(/url\("([^"]+)"\)/g)) urls.add(m[1]);
  for (const m of html.matchAll(/(?:src|href|poster|data-cap-video)="(https?:[^"]+)"/g)) urls.add(m[1].replace(/&amp;/g, '&'));
  for (const m of html.matchAll(/url\(&quot;(https?:[^&]+)&quot;\)/g)) urls.add(m[1]);
  const EXT = { 'font/woff2': '.woff2', 'font/woff': '.woff', 'font/ttf': '.ttf', 'image/png': '.png', 'image/jpeg': '.jpg', 'image/webp': '.webp', 'image/svg+xml': '.svg', 'image/gif': '.gif', 'image/avif': '.avif', 'video/mp4': '.mp4', 'video/webm': '.webm', 'video/quicktime': '.mov' };
  const failed = [];
  const local = {};
  const links = [...html.matchAll(/<a\b[^>]*href="(https?:[^"]+)"/g)].map((m) => m[1]);
  const todo = [...urls].filter((u) => /^https?:/.test(u) && !(links.includes(u) && !/\.(png|jpe?g|webp|svg|gif|avif|woff2?|ttf)(\?|$)/i.test(u)));
  const got = [];
  let next = 0;
  await Promise.all(Array.from({ length: 6 }, async () => {
    while (next < todo.length) {
      const j = next++, u = todo[j];
      try {
        const r = await fetch(u, { signal: AbortSignal.timeout(20000) });
        if (!r.ok) throw new Error('http ' + r.status);
        const type = (r.headers.get('content-type') || '').split(';')[0].trim();
        const ext = EXT[type] || (path.extname(new URL(u).pathname).slice(0, 6) || '.bin');
        const name = crypto.createHash('sha1').update(u).digest('hex').slice(0, 12) + ext;
        fs.writeFileSync(path.join(AS, name), Buffer.from(await r.arrayBuffer()));
        got[j] = { p: 'assets/cap/' + name + new URL(u).hash };
      } catch (e) { got[j] = { err: String(e.message).slice(0, 80) }; }
    }
  }));
  todo.forEach((u, j) => { if (got[j].err) failed.push({ url: u, err: got[j].err }); else local[u] = got[j].p; });
  for (const [u, p] of Object.entries(local)) {
    css = css.split(`url("${u}")`).join(`url("${p}")`);
    html = html.split(`"${u}"`).join(`"${p}"`).split(`"${u.replace(/&/g, '&amp;')}"`).join(`"${p}"`).split(`url(&quot;${u}&quot;)`).join(`url(&quot;${p}&quot;)`);
  }
  html = html.split('__CAP__/').join('assets/cap/');
  css = viewportUnits(scopeSelectors(css), +W, +H);
  html = html.replace(/(\sstyle=")([^"]*)"/g, (m, a, v) => a + viewportUnits(v, +W, +H) + '"');

  fs.writeFileSync(path.join(out, 'page.html'), html);
  fs.writeFileSync(path.join(out, 'page.css'), css);
  fs.writeFileSync(path.join(out, 'boxes.json'), JSON.stringify(boxes));
  const meta = { url, width: +W, height: +H, title: page.title, html_attrs: page.htmlAttrs, body_attrs: page.bodyAttrs, fonts: page.fonts, page_height: page.height, media,
    css_kb: Math.round(css.length / 1024), html_kb: Math.round(html.length / 1024), assets: Object.keys(local).length, failed, unreadable_sheets: sheets.filter((s) => s.err).map((s) => s.href) };
  fs.writeFileSync(path.join(out, 'meta.json'), JSON.stringify(meta, null, 1));
  console.log(JSON.stringify({ title: meta.title, html_kb: meta.html_kb, css_kb: meta.css_kb, assets: meta.assets, failed: failed.length, media: media.length, boxes: boxes.length, fonts: meta.fonts.length, page_height: meta.page_height }));
})().catch((e) => { console.error('ERR', e.message); process.exit(1); });
