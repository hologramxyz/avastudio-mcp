const fs = require('fs');
const os = require('os');
const path = require('path');
const puppeteer = (() => {
  const hf = (process.env.NODE_PATH || '').split(path.delimiter).filter(Boolean).map((d) => path.join(d, 'hyperframes', 'node_modules', 'puppeteer-core'));
  for (const p of [process.env.PUPPETEER, 'puppeteer-core', ...hf]) {
    if (!p) continue;
    try { return require(p); } catch (e) { if (e.code !== 'MODULE_NOT_FOUND') throw e; }
  }
  throw new Error('puppeteer-core not found: run with NODE_PATH=$(npm root -g) and a global hyperframes, or set PUPPETEER to its path');
})();
const CHROME = process.env.CHROME || ['/usr/bin/google-chrome', '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome'].find((p) => fs.existsSync(p)) || (() => {
  try { return require('child_process').execSync('npx --yes hyperframes@0.9.19 browser path', { encoding: 'utf8', stdio: ['ignore', 'pipe', 'ignore'] }).trim().split('\n').pop(); } catch (e) { return undefined; }
})();

const proj = path.resolve(process.argv[2]);
const src = fs.readFileSync(path.join(proj, 'compositions', 'film.html'), 'utf8');
const lost = [...src.matchAll(/<video\b[^>]*\ssrc="([^"]+)"/g)].map((m) => m[1].replace(/[?#].*$/, '')).filter((v) => !/^[a-z]+:/i.test(v) && !fs.existsSync(path.join(proj, decodeURIComponent(v))));
const inner = src.slice(src.indexOf('<template>') + 10, src.lastIndexOf('</template>'));
const mk = '<script>\n(function () {\n  const D = ', at = src.indexOf(mk) + mk.length;
const D = JSON.parse(src.slice(at, src.indexOf(';\n', at)));
const [W, H] = D.size;
const harness = `<!doctype html><html><head><meta charset="utf-8">
<script src="https://cdn.jsdelivr.net/npm/gsap@3.13.0/dist/gsap.min.js"></script>
<style>html,body{margin:0;background:#000;overflow:hidden}#root{position:relative;width:${W}px;height:${H}px;overflow:hidden}
#root *:not(.dof):not(#fog):not(#vig):not(#bloom):not(#dith){pointer-events:auto!important}</style></head>
<body><script>window.__timelines={};</script><div id="root">${inner}</div></body></html>`;
const TYPES = { '.css': 'text/css', '.js': 'text/javascript', '.json': 'application/json', '.png': 'image/png', '.jpg': 'image/jpeg', '.jpeg': 'image/jpeg', '.gif': 'image/gif', '.webp': 'image/webp', '.avif': 'image/avif', '.svg': 'image/svg+xml', '.mp4': 'video/mp4', '.webm': 'video/webm', '.mov': 'video/quicktime', '.woff': 'font/woff', '.woff2': 'font/woff2', '.ttf': 'font/ttf', '.otf': 'font/otf', '.mp3': 'audio/mpeg', '.wav': 'audio/wav' };
const server = require('http').createServer((req, res) => {
  const u = decodeURIComponent(new URL(req.url, 'http://x').pathname);
  if (u === '/__check.html') return res.writeHead(200, { 'content-type': 'text/html' }).end(harness);
  const f = path.join(proj, u);
  if (!f.startsWith(proj + path.sep) || !fs.existsSync(f) || !fs.statSync(f).isFile()) return res.writeHead(404).end();
  res.writeHead(200, { 'content-type': TYPES[path.extname(f).toLowerCase()] || 'application/octet-stream' });
  fs.createReadStream(f).pipe(res);
});

(async () => {
  await new Promise((r) => server.listen(0, '127.0.0.1', r));
  const noSandbox = process.env.CHROME_NO_SANDBOX === '1' || (process.getuid && process.getuid() === 0);
  const b = await puppeteer.launch({ executablePath: CHROME, headless: 'new', args: noSandbox ? ['--no-sandbox'] : [] });
  const g = await b.newPage();
  const errors = [];
  g.on('pageerror', (e) => errors.push(String(e.message || e).slice(0, 300)));
  await g.setViewport({ width: W, height: H });
  await g.goto(`http://127.0.0.1:${server.address().port}/__check.html`, { waitUntil: 'load', timeout: 300000 });
  let ready = false;
  for (let i = 0; i < 200 && !ready && !errors.length; i++) {
    ready = await g.evaluate(() => !!(window.__timelines && window.__timelines.film));
    if (!ready) await new Promise((r) => setTimeout(r, 300));
  }
  if (!ready) {
    console.log('the film does not start: ' + (errors[0] || 'no timeline'));
    const miss = await g.evaluate((D) => {
      const page = document.querySelector('#page'), out = [];
      D.shots.forEach((s, i) => [['focus', s.focus], ['focus_to', s.focus_to]].forEach(([k, f]) => {
        if (!f || Array.isArray(f)) return;
        let els = [...page.querySelectorAll(f.sel)];
        if (!els.length) els = [...document.querySelectorAll(f.sel)];
        if (f.text) els = els.filter((e) => e.textContent.includes(f.text));
        const el = els[f.nth || 0], r = el && el.getBoundingClientRect();
        if (!el) out.push(`shot ${i} ${k} ${JSON.stringify(f).slice(0, 90)}: no element`);
        else if (!r.width || !r.height) out.push(`shot ${i} ${k} ${JSON.stringify(f).slice(0, 90)}: the element has no size (hidden or display:none)`);
      }));
      return out;
    }, D).catch(() => []);
    if (miss.length) console.log(miss.join('\n'));
    await b.close();
    server.close();
    process.exit(1);
  }
  await g.evaluate(async () => {
    await document.fonts.ready;
    await Promise.all([...document.images].map((i) => i.decode().catch(() => {})));
    await Promise.all([...document.querySelectorAll('video')].map((v) => v.readyState >= 1 || new Promise((r) => { v.addEventListener('loadedmetadata', r, { once: true }); v.addEventListener('error', r, { once: true }); setTimeout(r, 8000); })));
  });
  const res = await g.evaluate((D) => {
    const page = document.querySelector('#page'), tl = window.__timelines.film, out = [], notes = [];
    const text = (page.textContent || '').replace(/\s+/g, ' ').trim().length;
    if (text < 100) (page.querySelector('img, video, canvas, svg') || [...page.querySelectorAll('*')].some((e) => /url\(/.test(getComputedStyle(e).backgroundImage)) ? notes : out).push(`the page holds only ${text} characters of text: the capture may be empty`);
    const broken = [...page.querySelectorAll('img')].filter((i) => i.complete && !i.naturalWidth && i.getAttribute('src'));
    if (broken.length) out.push(`${broken.length} images do not load: ${broken.slice(0, 4).map((i) => i.getAttribute('src').slice(-50)).join(', ')}`);
    const key = (f) => `${f.family} ${f.weight} ${f.style}`, loaded = new Set([...document.fonts].filter((f) => f.status === 'loaded').map(key));
    const failed = [...document.fonts].filter((f) => f.status === 'error'), name = (f) => `${f.family} ${f.weight}`;
    const chars = new Set(), walk = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT, { acceptNode: (n) => (n.parentElement && n.parentElement.closest('script,style') ? NodeFilter.FILTER_REJECT : NodeFilter.FILTER_ACCEPT) });
    for (let n = walk.nextNode(); n; n = walk.nextNode()) for (const c of n.data) chars.add(c.codePointAt(0));
    const used = (f) => f.unicodeRange.split(',').some((r) => {
      const [a, b = a] = r.trim().replace(/^u\+/i, '').split('-'), lo = parseInt(a.replace(/\?/g, '0'), 16), hi = parseInt(b.replace(/\?/g, 'f'), 16);
      for (const c of chars) if (c >= lo && c <= hi) return true;
      return false;
    });
    const fonts = failed.filter((f) => !loaded.has(key(f)) || used(f)).map(name), partial = failed.filter((f) => loaded.has(key(f)) && !used(f)).map(name);
    if (fonts.length) out.push(`fonts that failed to load: ${[...new Set(fonts)].slice(0, 6).join(', ')}`);
    if (partial.length) notes.push(`unused character subsets failed to load, other faces of the same font did: ${[...new Set(partial)].slice(0, 6).join(', ')}`);
    const find = (t) => {
      let els = [...page.querySelectorAll(t.sel)];
      if (!els.length) els = [...document.querySelectorAll(t.sel)];
      if (t.text) els = els.filter((e) => e.textContent.includes(t.text));
      return els[t.nth || 0];
    };
    const at = (t) => tl.seek(Math.min(Math.max(t - D.win[0], 0), D.win[1] - D.win[0] - 1e-3), false);
    D.shots.forEach((s, i) => {
      if (s.t1 <= D.win[0] || s.t0 >= D.win[1]) return;
      [['focus', s.focus, s.t0 + 0.02], ['focus_to', s.focus_to, s.t1 - 0.02]].forEach(([k, f, t]) => {
        if (!f || Array.isArray(f)) return;
        at(t);
        const el = find(f);
        const name = `shot ${i} ${k} ${JSON.stringify(f).slice(0, 90)}`;
        if (!el) return out.push(`${name}: no element`);
        const r = el.getBoundingClientRect(), cs = getComputedStyle(el);
        if (!r.width || !r.height) return out.push(`${name}: the element has no size (hidden or display:none)`);
        if (cs.visibility === 'hidden' || +cs.opacity === 0) notes.push(`${name}: the element is invisible at ${t.toFixed(2)} s, fine if it fades in during the shot`);
        const cx = r.left + r.width / 2, cy = r.top + r.height / 2;
        if (r.right <= 0 || r.bottom <= 0 || r.left >= innerWidth || r.top >= innerHeight) out.push(`${name}: it is off screen at ${t.toFixed(2)} s`);
        else if (cx < 0 || cy < 0 || cx > innerWidth || cy > innerHeight) notes.push(`${name}: its centre is off screen at ${t.toFixed(2)} s, fine for a close-up that uses ax, ay, dx or dy`);
      });
    });
    const AREA = 0.25, SPAN = 0.8, SPAN_AREA = 0.1, SHARE = 0.5, HOOK = 3, TEXT = 0.025, UP = 1.5, STEP = 0.1, W = innerWidth, H = innerHeight;
    const full = D.win[0] === 0 && D.win[1] >= D.dur - 1e-3;
    const clips = [...document.querySelectorAll('#root .clip[data-start]')];
    const go = (t) => {
      at(t);
      const r = Math.min(Math.max(t - D.win[0], 0), D.win[1] - D.win[0] - 1e-3);
      for (const c of clips) {
        if (!('v0' in c.dataset)) c.dataset.v0 = c.style.visibility;
        c.style.visibility = r >= +c.dataset.start && r < +c.dataset.start + +c.dataset.duration ? c.dataset.v0 : 'hidden';
      }
    };
    const alpha = (el) => {
      let o = 1;
      for (let e = el; e && e.nodeType === 1; e = e.parentElement) {
        const c = getComputedStyle(e);
        if (c.display === 'none') return 0;
        o *= +c.opacity;
      }
      return getComputedStyle(el).visibility === 'hidden' ? 0 : o;
    };
    const wild = (q) => q.width > 4 * W || q.height > 4 * H;
    const scale = (el, q) => (el.offsetWidth && el.offsetHeight ? Math.min(q.width / el.offsetWidth, q.height / el.offsetHeight) : null);
    const box = (el) => {
      const q0 = el.getBoundingClientRect();
      let [l, t, r, b] = [q0.left, q0.top, q0.right, q0.bottom];
      const all = q0.width * q0.height, k = scale(el, q0), own = k === null ? all : el.offsetWidth * el.offsetHeight * k * k;
      for (let e = el.parentElement; e && e !== document.body; e = e.parentElement) {
        const c = getComputedStyle(e), q = e.getBoundingClientRect(), cp = c.clipPath !== 'none';
        if (wild(q)) continue;
        if (cp || c.overflowX !== 'visible') [l, r] = [Math.max(l, q.left), Math.min(r, q.right)];
        if (cp || c.overflowY !== 'visible') [t, b] = [Math.max(t, q.top), Math.min(b, q.bottom)];
      }
      const sw = Math.max(0, Math.min(r, W) - Math.max(l, 0)), sh = Math.max(0, Math.min(b, H) - Math.max(t, 0));
      return { area: Math.min(sw * sh, own) / (W * H), span: Math.max(sw / W, sh / H), out: all ? 1 - (sw * sh) / all : 1, big: own > 2 * W * H };
    };
    const large = (b) => b.area >= AREA || (b.span >= SPAN && b.area >= SPAN_AREA);
    const opaque = (e) => {
      const c = getComputedStyle(e), m = c.backgroundColor.match(/[\d.]+/g);
      const solid = (s) => (s.match(/rgba?\([^)]*\)/g) || []).every((x) => { const v = x.match(/[\d.]+/g); return v.length < 4 || +v[3] >= 0.9; });
      const grad = /gradient\(/.test(c.backgroundImage) && !/url\(/.test(c.backgroundImage) && /rgba?\(/.test(c.backgroundImage) && solid(c.backgroundImage);
      return /^(IMG|VIDEO|CANVAS)$/.test(e.tagName) || /url\(/.test(c.backgroundImage) || grad || (m && (m.length < 4 || +m[3] >= 0.9));
    };
    const pos = (v, room, k) => (v.endsWith('%') ? (room * parseFloat(v)) / 100 : parseFloat(v) * k);
    const painted = (m, x, y) => {
      const nw = m.naturalWidth || m.videoWidth, nh = m.naturalHeight || m.videoHeight, ow = m.offsetWidth, oh = m.offsetHeight, fit = getComputedStyle(m).objectFit;
      if (!nw || !nh || !ow || !oh || !['contain', 'scale-down'].includes(fit)) return true;
      const k = Math.min(ow / nw, oh / nh, fit === 'scale-down' ? 1 : Infinity), q = m.getBoundingClientRect();
      const pw = (q.width * nw * k) / ow, ph = (q.height * nh * k) / oh, [px = '50%', py = '50%'] = getComputedStyle(m).objectPosition.split(' ');
      const l = q.left + pos(px, q.width - pw, q.width / ow), t = q.top + pos(py, q.height - ph, q.height / oh);
      return x >= l && x <= l + pw && y >= t && y <= t + ph;
    };
    const FX = new Set(['fog', 'vig', 'bloom', 'dith']);
    const GX = 48, GY = 27;
    const vis = (el) => {
      const q = el.getBoundingClientRect(), sx = W / GX, sy = H / GY;
      let n = 0, l = W, r = 0, t = H, bt = 0;
      for (let gx = Math.max(0, Math.floor(q.left / sx)); gx < GX && gx * sx < q.right; gx++) {
        for (let gy = Math.max(0, Math.floor(q.top / sy)); gy < GY && gy * sy < q.bottom; gy++) {
          const x = (gx + 0.5) * sx, y = (gy + 0.5) * sy;
          let w = 0;
          for (const e of document.elementsFromPoint(x, y)) {
            if (e === el || el.contains(e)) { w = alpha(e) < 0.5 || (/^(IMG|VIDEO)$/.test(e.tagName) && !painted(e, x, y)) ? 0 : 1; break; }
            if (e.contains(el) || FX.has(e.id) || e.classList.contains('dof')) continue;
            if (alpha(e) >= 0.5 && opaque(e) && !(/^(IMG|VIDEO)$/.test(e.tagName) && !painted(e, x, y))) break;
          }
          if (!w) continue;
          n += w; l = Math.min(l, x); r = Math.max(r, x); t = Math.min(t, y); bt = Math.max(bt, y);
        }
      }
      return n ? { area: n / (GX * GY), span: Math.max((r - l + sx) / W, (bt - t + sy) / H) } : { area: 0, span: 0 };
    };
    const shotAt = (t) => D.shots.findIndex((s) => s.t0 <= t && t < s.t1);
    const subj = (s, i) => {
      const k = s.subject;
      if (!k || !['product', 'proof', 'brand', 'other'].includes(k.kind)) return { err: `shot ${i}: no subject kind (product, proof, brand or other)` };
      const tg = k.sel ? k : s.focus && !Array.isArray(s.focus) ? s.focus : null;
      if (!tg) return { err: `shot ${i}: the subject needs a sel when the focus is a page point` };
      return { kind: k.kind, tg };
    };
    const fontPx = (p) => {
      const q = p.getBoundingClientRect(), k = wild(q) ? null : scale(p, q);
      return k === null ? 0 : parseFloat(getComputedStyle(p).fontSize) * k;
    };
    const texts = () => {
      const r = document.createRange(), res = [];
      const w = document.createTreeWalker(document.querySelector('#root') || document.body, NodeFilter.SHOW_TEXT, { acceptNode: (n) => (n.data.trim() && n.parentElement && !n.parentElement.closest('script,style') ? NodeFilter.FILTER_ACCEPT : NodeFilter.FILTER_REJECT) });
      for (let n = w.nextNode(); n; n = w.nextNode()) {
        r.selectNodeContents(n);
        const q = r.getBoundingClientRect();
        if (!q.width || !q.height || q.right <= 0 || q.bottom <= 0 || q.left >= W || q.top >= H) continue;
        if (alpha(n.parentElement) < 0.5) continue;
        const all = q.width * q.height, seen = (Math.min(q.right, W) - Math.max(q.left, 0)) * (Math.min(q.bottom, H) - Math.max(q.top, 0));
        res.push({ px: fontPx(n.parentElement), out: 1 - seen / all, text: n.data.trim().slice(0, 40) });
      }
      return res;
    };
    const textOf = (el) => Math.max(0, ...[el, ...el.querySelectorAll('*')].filter((e) => [...e.childNodes].some((n) => n.nodeType === 3 && n.data.trim())).map(fontPx)) / H;
    const svg = (m) => m.tagName === 'IMG' && /\.svg(\?|#|$)|^data:image\/svg/i.test(m.currentSrc || m.getAttribute('src') || '');
    const subs = D.shots.map(subj);
    const rows = [];
    D.shots.forEach((s, i) => {
      if (s.t1 <= D.win[0] || s.t0 >= D.win[1]) return;
      const sb = subs[i];
      if (sb.err) return out.push(sb.err);
      const row = { i, kind: sb.kind, area: [], text: 0, focus: null, media: 0, clipped: [], cut: 0, soft: new Map(), nometa: new Set(), noimg: new Set(), big: false };
      for (const f of [0.5, 0.85]) {
        const t = s.t0 + (s.t1 - s.t0) * f;
        go(t);
        const el = find(sb.tg);
        if (!el) {
          if (f === 0.5) out.push(`shot ${i}: the subject ${JSON.stringify(sb.tg).slice(0, 90)} matches no element`);
        } else {
          const b = box(el), a = alpha(el) >= 0.5 ? vis(el).area : 0;
          row.area.push(a);
          if (a > 0 && ['product', 'proof'].includes(sb.kind) && !s.bleed) row.cut = Math.max(row.cut, b.out);
          if (b.big && sb.kind === 'product') row.big = true;
        }
        const tx = texts();
        row.text = Math.max(row.text, ...tx.map((x) => x.px / H), 0);
        tx.filter((x) => x.px / H >= TEXT && x.out > 0.05 && x.out < 0.95).forEach((x) => row.clipped.push(`"${x.text}" ${Math.round(x.out * 100)}% out at ${t.toFixed(2)} s`));
        const fe = s.focus && !Array.isArray(s.focus) ? find(s.focus) : sb.kind === 'proof' ? el : null;
        if (f === 0.5 && el && [el, ...el.querySelectorAll('*')].slice(0, 500).some((e) => !/^(IMG|VIDEO)$/.test(e.tagName) && /url\(/.test(getComputedStyle(e).backgroundImage))) row.bg = true;
        if (fe && !/^(img|video|canvas|svg)$/i.test(fe.tagName) && fe.textContent.trim() && alpha(fe) >= 0.5) {
          const fp = textOf(fe);
          row.focus = row.focus === null ? fp : Math.min(row.focus, fp);
        }
        for (const m of document.querySelectorAll('img, video')) {
          if (alpha(m) < 0.5 || svg(m) || wild(m.getBoundingClientRect())) continue;
          const b = box(m);
          if (b.area < 0.01) continue;
          if (f === 0.5) row.media++;
          const nw = m.naturalWidth || m.videoWidth, nh = m.naturalHeight || m.videoHeight, src = (m.getAttribute('src') || '').slice(-40);
          if (b.area < 0.1 || !el || !(el === m || el.contains(m))) continue;
          if (!nw || !nh) { (m.tagName === 'VIDEO' ? row.nometa : row.noimg).add(src); continue; }
          const k = scale(m, m.getBoundingClientRect()), fit = getComputedStyle(m).objectFit;
          if (k === null) continue;
          const sc = k * (['contain', 'scale-down'].includes(fit) ? Math.min : Math.max)(m.offsetWidth / nw, m.offsetHeight / nh);
          const key = `${m.tagName.toLowerCase()} ${src}`;
          if (sc > UP) row.soft.set(key, { sc: Math.max(sc, (row.soft.get(key) || { sc: 0 }).sc), px: `${nw}x${nh}` });
        }
      }
      for (const [m, v] of row.soft) out.push(`shot ${i}: ${m} is drawn at ${v.sc.toFixed(1)}x its ${v.px} pixels and looks soft; zoom out, use a sharper file, or set its text as live type`);
      if (row.nometa.size) out.push(`shot ${i}: video ${[...row.nometa].slice(0, 3).join(', ')} has no pixel size: it did not load`);
      if (row.bg) notes.push(`shot ${i}: the subject holds a CSS background image, so its sharpness was not checked`);
      if (row.noimg.size) notes.push(`shot ${i}: no pixel size for ${[...row.noimg].slice(0, 3).join(', ')}, so its sharpness was not checked`);
      if (row.area.length && !row.area.some((a) => a > 0)) out.push(`shot ${i}: the subject is not visible at the middle or the end of the shot`);
      if (row.cut > 0.25) out.push(`shot ${i}: the subject is up to ${Math.round(row.cut * 100)}% outside the frame; frame it whole, or mark the shot "bleed": true if the reference cuts it too`);
      if (row.focus !== null && row.focus < TEXT) out.push(`shot ${i}: the focus text is ${(row.focus * 100).toFixed(1)}% of the frame height, under the ${TEXT * 100}% floor for a phone; zoom in, or focus the image or video itself if the text is not meant to be read`);
      if (row.text && row.text < TEXT) notes.push(`shot ${i}: the biggest text on screen is ${(row.text * 100).toFixed(1)}% of the frame height; nothing on screen is readable on a phone`);
      if (row.big) notes.push(`shot ${i}: the product subject is over twice the frame; pick the element that holds the product, not a section around it`);
      if (row.clipped.length) notes.push(`shot ${i}: readable text cut by the frame edge: ${row.clipped.slice(0, 3).join('; ')}`);
      rows.push(row);
    });
    const N = Math.round((D.win[1] - D.win[0]) / STEP);
    const isProd = (t) => {
      const i = shotAt(t), sb = i >= 0 && subs[i];
      if (!sb || sb.err || sb.kind !== 'product') return false;
      go(t);
      const el = find(sb.tg);
      return !!el && alpha(el) >= 0.5 && large(vis(el));
    };
    let hits = 0, first = null;
    for (let j = 0; j < N; j++) {
      const t = D.win[0] + (j + 0.5) * STEP;
      if (isProd(t)) {
        hits++;
        if (first === null) first = t - D.win[0];
      }
    }
    const prod = hits * STEP, len = N * STEP, share = N ? hits / N : 0;
    const table = rows.map((r) => `shot ${r.i} ${r.kind}: subject ${r.area.map((a) => Math.round(a * 100) + '%').join(' / ') || 'not found'} of the frame, biggest text ${(r.text * 100).toFixed(1)}%${r.focus !== null ? `, focus text ${(r.focus * 100).toFixed(1)}%` : ''}, ${r.media} images or videos on screen`);
    const summary = `product on screen at ${AREA * 100}% of the frame or more (or ${SPAN * 100}% of its height or width): ${prod.toFixed(1)} of ${len.toFixed(1)} s (${Math.round(share * 100)}%), first at ${first === null ? 'never' : first.toFixed(1) + ' s'}${full ? '' : ' (a window: the product floors apply to the whole film only)'}`;
    if (full) {
      if (hits < SHARE * N - 1e-9) out.push(`the product is on screen for ${Math.round(share * 100)}% of the film, under the ${SHARE * 100}% floor`);
      if (first !== null && first > HOOK && first < HOOK + STEP && isProd(D.win[0] + HOOK)) first = HOOK;
      if (first === null || first > HOOK) out.push(`the product is first on screen large at ${first === null ? 'no point' : first.toFixed(1) + ' s'}, later than ${HOOK} s`);
    }
    return { out, notes, table, summary, full };
  }, D);
  console.log(res.table.join('\n'));
  console.log(res.summary);
  if (res.notes.length) console.log(res.notes.map((n) => 'note: ' + n).join('\n'));
  const all = [...errors.map((e) => 'page error: ' + e), ...lost.map((v) => 'video file missing: ' + v), ...res.out];
  console.log(all.length ? all.join('\n') : `check ok: page, images, fonts, shot targets, ${res.full ? 'product time, ' : ''}text size, edges and sharpness`);
  await b.close();
  server.close();
  process.exit(all.length ? 1 : 0);
})().catch((e) => { console.error(e.message || e); process.exit(1); });
