(function () {
  const D = __DATA__;
  const $ = (s, r = document) => r.querySelector(s);
  const page = $('#page');
  const clamp = (x, a, b) => Math.min(b, Math.max(a, x));
  const eo = (x) => 1 - Math.pow(1 - x, 4);
  const sm = (x) => x * x * (3 - 2 * x);
  const NS = 'http://www.w3.org/2000/svg';
  const defs = $('#film-defs');

  for (const f of document.fonts) if (f.status === 'unloaded') f.load().catch(() => {});
  for (const s of D.page.drop || []) page.querySelectorAll(s).forEach((e) => e.remove());
  for (const s of D.page.hide || []) page.querySelectorAll(s).forEach((e) => [e, ...e.querySelectorAll('*')].forEach((x) => x.style.setProperty('visibility', 'hidden', 'important')));
  function shell(el) {
    let outer = null, cur = null;
    const chain = [];
    for (let e = el.parentElement; e && e !== page; e = e.parentElement) chain.unshift(e);
    for (const a of chain) {
      const c = document.createElement(a.tagName);
      for (const at of a.attributes) if (at.name !== 'id' && at.name !== 'style') c.setAttribute(at.name, at.value);
      c.style.display = 'contents';
      c.setAttribute('data-shell', '');
      if (cur) cur.appendChild(c); else outer = c;
      cur = c;
    }
    return [outer, cur];
  }
  for (const o of D.overlays || []) {
    const host = $('#' + o.id), [outer, inner] = shell(page.querySelector('.cap-body > *') || page.firstElementChild);
    while (host.firstChild) inner.appendChild(host.firstChild);
    for (const s of [].concat(o.clone || [])) {
      const el = page.querySelector(s);
      if (!el) throw new Error('no element to clone for ' + s);
      const [co, ci] = shell(el);
      ci.appendChild(el.cloneNode(true));
      inner.appendChild(co);
    }
    host.appendChild(outer);
  }
  const root = $('#stage').parentNode;

  function find(t) {
    let els = [...page.querySelectorAll(t.sel)];
    if (!els.length) els = [...document.querySelectorAll(t.sel)];
    if (t.text) els = els.filter((e) => e.textContent.includes(t.text));
    if (!els.length) throw new Error('no element for ' + JSON.stringify(t));
    return els[t.nth || 0];
  }
  function offset(el) {
    let x = 0, y = 0;
    for (let e = el; e && e !== page; e = e.offsetParent) { x += e.offsetLeft; y += e.offsetTop; }
    return [x, y, el.offsetWidth, el.offsetHeight];
  }
  const fcache = new Map();
  function focusPoint(f) {
    if (Array.isArray(f)) return f;
    if (fcache.has(f)) return fcache.get(f);
    const [x, y, w, h] = offset(find(f));
    return [x + w * (f.ax ?? 0.5) + (f.dx || 0), y + h * (f.ay ?? 0.5) + (f.dy || 0)];
  }

  const pos = $('#pos'), pitch = $('#pitch'), yaw = $('#yaw'), roll = $('#roll');
  const L = D.look;
  const dof = [...document.querySelectorAll('.dof')], fog = $('#fog'), vig = $('#vig'), expo = $('#expo');
  dof.forEach((e, i) => { e.style.backdropFilter = 'blur(' + L.dof.blurs[i] + 'px)'; e.style.webkitBackdropFilter = e.style.backdropFilter; });
  const shot = (t) => D.shots.find((s) => t < s.t1) || D.shots[D.shots.length - 1];
  let last = null;
  const mask = (c, w, off, a) => 'linear-gradient(' + a + 'deg,#000 ' + (c - w - off - L.dof.ramp) + '%,transparent ' + (c - w - off) + '%,transparent ' + (c + w + off) + '%,#000 ' + (c + w + off + L.dof.ramp) + '%)';
  let soloOf = null;
  function solo(s) {
    if (soloOf === s) return;
    page.querySelectorAll('[data-solo]').forEach((e) => e.removeAttribute('data-solo'));
    page.classList.toggle('solo', !!s.solo);
    for (const q of s.solo || []) page.querySelectorAll(q).forEach((e) => e.setAttribute('data-solo', ''));
    soloOf = s;
  }
  function camera(t) {
    const s = shot(t), u = t - s.t0, n = u / (s.t1 - s.t0);
    solo(s);
    let dx = s.v[0] * u, dy = s.v[1] * u, rz = s.rot[2];
    if (s.v0) {
      const k = s.tau * (1 - Math.exp(-u / s.tau));
      dx += (s.v0[0] - s.v[0]) * k; dy += (s.v0[1] - s.v[1]) * k; rz += (s.rv || 0) * k;
    }
    const ne = EASE[s.ease || 'linear'](clamp(s.move_d ? u / s.move_d : n, 0, 1));
    const z = s.zoom[0] + (s.zoom[1] - s.zoom[0]) * ne;
    pos.style.transform = 'translate3d(' + (s.at[0] + dx) + 'px,' + (s.at[1] + dy) + 'px,0)';
    pitch.style.transform = 'rotateX(' + s.rot[0] + 'deg)';
    yaw.style.transform = 'rotateY(' + s.rot[1] + 'deg)';
    roll.style.transform = 'rotateZ(' + rz + 'deg) scale(' + z + ')';
    let f = focusPoint(s.focus);
    if (s.focus_to) { const g = focusPoint(s.focus_to); f = [f[0] + (g[0] - f[0]) * ne, f[1] + (g[1] - f[1]) * ne]; }
    page.style.transform = 'translate(' + -f[0] + 'px,' + -f[1] + 'px)';
    const d = s.dof, kf = d.rack ? sm(clamp((t - d.rack[0]) / (d.rack[1] - d.rack[0]), 0, 1)) : sm(n);
    const c = d.center[0] + (d.center[1] - d.center[0]) * kf, w = d.width, a = d.angle;
    dof.forEach((e, i) => { const m = mask(c, w, L.dof.offsets[i], a); e.style.maskImage = m; e.style.webkitMaskImage = m; });
    const F = L.fog;
    fog.style.background = 'linear-gradient(' + a + 'deg,rgba(0,0,0,' + F.far + ') ' + (c - w - F.far_at) + '%,rgba(0,0,0,' + F.near + ') ' + (c - w - F.near_at) + '%,rgba(0,0,0,0) ' + (c - w) + '%,rgba(0,0,0,0) ' + (c + w) + '%,rgba(0,0,0,' + F.near + ') ' + (c + w + F.near_at) + '%,rgba(0,0,0,' + F.far + ') ' + (c + w + F.far_at) + '%)';
    vig.style.background = 'radial-gradient(ellipse ' + L.vignette.size[0] + '% ' + L.vignette.size[1] + '% at ' + s.vignette[0] + '% ' + s.vignette[1] + '%,rgba(0,0,0,0) ' + L.vignette.inner + '%,rgba(0,0,0,' + L.vignette.dark + ') 100%)';
    expo.style.opacity = s.expo[0] + (s.expo[1] - s.expo[0]) * clamp(u / L.expo_s, 0, 1);
    last = s;
  }

  function dustFilter(i) {
    const f = document.createElementNS(NS, 'filter');
    f.setAttribute('id', 'df' + i);
    for (const [k, v] of Object.entries({ x: '-30%', y: '-90%', width: '160%', height: '280%', 'color-interpolation-filters': 'sRGB' })) f.setAttribute(k, v);
    f.innerHTML = '<feGaussianBlur in="SourceGraphic" stdDeviation="6" result="b"/><feComponentTransfer in="b" result="g"><feFuncA type="linear" slope="5"/></feComponentTransfer>' +
      '<feTurbulence type="fractalNoise" baseFrequency="' + L.dust.grain + '" numOctaves="1" seed="' + (i + 3) + '" result="n"/>' +
      '<feColorMatrix in="n" type="matrix" values="0 0 0 0 1 0 0 0 0 1 0 0 0 0 1 0 0 0 9 -7" result="m"/><feComposite in="g" in2="m" operator="in"/>';
    defs.appendChild(f);
    return { b: f.querySelector('feGaussianBlur'), a: f.querySelector('feFuncA'), m: f.querySelector('feColorMatrix') };
  }
  const G = [];
  function wrapDust(nodes, parent, before, t, ev) {
    const w = document.createElement('x-dp');
    w.className = 'dp';
    parent.insertBefore(w, before);
    nodes.forEach((n) => w.appendChild(n));
    const i = G.length;
    G.push(Object.assign({ t, d: ev.d ?? L.dust.d, bl: ev.blur ?? 1, el: w, p: -1, url: 'url(#df' + i + ')' }, dustFilter(i)));
  }
  function dustInit(ev) {
    let els = [...page.querySelectorAll(ev.sel)];
    if (!els.length) els = [...document.querySelectorAll(ev.sel)];
    els.forEach((el, i) => {
      if (ev.split === 'word') {
        let k = 0;
        for (const n of [...el.childNodes]) {
          if (n.nodeType !== 3) { wrapDust([n], el, n.nextSibling, ev.t + (i + k++) * (ev.step || 0), ev); continue; }
          for (const p of n.textContent.split(/(\s+)/)) {
            if (!p) continue;
            const tn = document.createTextNode(p);
            el.insertBefore(tn, n);
            if (p.trim()) wrapDust([tn], el, tn.nextSibling, ev.t + (i + k++) * (ev.step || 0), ev);
          }
          n.remove();
        }
      } else if (ev.split === 'br') {
        let run = [], k = 0;
        const flush = (before) => { if (run.length) wrapDust(run, el, before, ev.t + (i + k++) * (ev.step || 0), ev); run = []; };
        for (const n of [...el.childNodes]) { if (n.nodeName === 'BR') flush(n); else run.push(n); }
        flush(null);
      } else if (ev.cells) {
        [...el.querySelectorAll(ev.cells)].forEach((c, j) => wrapDust([...c.childNodes], c, null, ev.t + i * (ev.step || 0) + j * (ev.cell_step || 0), ev));
      } else wrapDust([...el.childNodes], el, null, ev.t + i * (ev.step || 0), ev);
    });
  }
  function dust(t) {
    for (const g of G) {
      const p = clamp((t - g.t) / g.d, 0, 1);
      if (p === g.p) continue;
      g.p = p;
      if (p >= 1) { g.el.style.filter = 'none'; g.el.style.opacity = 1; continue; }
      if (p <= 0) { g.el.style.filter = 'none'; g.el.style.opacity = 0; continue; }
      g.el.style.filter = g.url;
      const q = 1 - p, tau = 0.82 - 0.74 * Math.pow(p, 1.5), K = 7;
      g.b.setAttribute('stdDeviation', (7 * g.bl * q * q).toFixed(3));
      g.a.setAttribute('slope', (1 + 6 * q).toFixed(3));
      g.m.setAttribute('values', '0 0 0 0 1 0 0 0 0 1 0 0 0 0 1 0 0 0 ' + K + ' ' + (-K * tau).toFixed(3));
      g.el.style.opacity = (0.55 + 0.45 * sm(p)).toFixed(3);
    }
  }

  function typeInit(ev) {
    let el = find(ev.target);
    const tag = el.tagName;
    const host = tag === 'TEXTAREA' || tag === 'INPUT' ? document.createElement('div') : el;
    const ph = document.createElement('x-ph');
    if (host !== el) {
      for (const a of el.attributes) if (a.name !== 'style') host.setAttribute(a.name, a.value);
      const cs = getComputedStyle(el);
      for (const k of ['padding', 'font', 'line-height', 'letter-spacing', 'color', 'min-height', 'box-sizing', 'width']) host.style.setProperty(k, cs.getPropertyValue(k));
      ph.textContent = el.getAttribute('placeholder') || '';
      ph.style.color = getComputedStyle(el, '::placeholder').color;
      el.replaceWith(host);
    } else { ph.textContent = el.textContent; host.textContent = ''; }
    host.appendChild(ph);
    host.style.whiteSpace = 'pre-wrap';
    const chars = [...ev.text].map((c) => { const s = document.createElement('x-ch'); s.className = 'tw-ch'; s.textContent = c; host.appendChild(s); return s; });
    const caret = document.createElement('x-caret');
    caret.className = 'tw-caret';
    host.appendChild(caret);
    return (t) => {
      let n = 0;
      chars.forEach((c, i) => { const on = t >= ev.times[i]; c.style.display = on ? 'inline' : 'none'; if (on) n++; });
      ph.style.display = n || ev.placeholder === false ? 'none' : 'inline';
      const done = ev.times[ev.times.length - 1];
      const blink = t > done + 0.1 || t < ev.times[0] ? Math.floor(t / ev.blink) % 2 === 0 : true;
      caret.style.visibility = t >= ev.caret_from && blink ? '' : 'hidden';
    };
  }

  const PRESS = new Map();
  function pressInit(ev) {
    const el = find(ev.target);
    if (PRESS.has(el)) { PRESS.get(el).push(ev); return null; }
    const list = [ev], b = getComputedStyle(el).transform, base = b && b !== 'none' ? b + ' ' : '';
    PRESS.set(el, list);
    return (t) => {
      let e = null;
      for (const p of list) if (t >= p.t && (!e || p.t >= e.t)) e = p;
      const u = e ? t - e.t : -1, k0 = e ? (e.depth ?? 0.035) : 0;
      const k = u < 0 ? 1 : u < 0.08 ? 1 - k0 * (u / 0.08) : 1 - k0 + k0 * clamp((u - 0.08) / 0.2, 0, 1);
      el.style.transform = base + 'scale(' + k + ')';
    };
  }

  function lineEndInit(ev) {
    const w1 = $('#w1'), w2 = $('#w2'), line = $('#line');
    return (t) => {
      const u = t - ev.t;
      if (u < 0) return;
      const inn = clamp(u / 0.55, 0, 1), b = 16 * (1 - eo(inn));
      w1.style.filter = b > 0.05 ? 'blur(' + b.toFixed(2) + 'px)' : 'none';
      w1.style.opacity = sm(inn);
      const sx = -20 + 150 * clamp((u - 0.25) / 1.1, 0, 1);
      w1.style.setProperty('--a', sx - 16 + '%'); w1.style.setProperty('--b', sx + '%'); w1.style.setProperty('--c', sx + 16 + '%');
      const m = clamp((u - 1.4) / 1.05, 0, 1), e = 1 - Math.pow(1 - m, 3);
      line.style.transform = 'translateX(' + (1 - e) * w2.offsetWidth / 2 + 'px)';
      const rev = e * 112 - 6;
      const mi = 'linear-gradient(90deg,#000 ' + rev + '%,transparent ' + (rev + 6) + '%)';
      w2.style.maskImage = mi; w2.style.webkitMaskImage = mi;
    };
  }

  const ID = { opacity: 1, scale: 1, x: 0, y: 0, blur: 0 };
  const EASE = { out: (x) => 1 - Math.pow(1 - x, 3), in: (x) => x * x * x, inout: (x) => (x < 0.5 ? 4 * x * x * x : 1 - Math.pow(-2 * x + 2, 3) / 2), linear: (x) => x,
    expo: (x) => (x >= 1 ? 1 : 1 - Math.pow(2, -10 * x)), back: (x) => 1 + 2.7 * Math.pow(x - 1, 3) + 1.7 * Math.pow(x - 1, 2),
    expo_in: (x) => (x <= 0 ? 0 : Math.pow(2, 10 * x - 10)),
    whip: (x) => 0.6 * (x >= 1 ? 1 : (1 - Math.pow(2, -10 * x)) / (1 - Math.pow(2, -10))) + 0.4 * x };
  const FADES = new Map();
  const targets = (ev) => (ev.target ? [find(ev.target)] : [...page.querySelectorAll(ev.sel)].concat(page.querySelector(ev.sel) ? [] : [...document.querySelectorAll(ev.sel)]));
  const BASE = new WeakMap();
  function fadeInit(ev) {
    targets(ev).forEach((el, i) => {
      if (!FADES.has(el)) { FADES.set(el, []); const b = getComputedStyle(el).transform; BASE.set(el, b && b !== 'none' ? b + ' ' : ''); }
      FADES.get(el).push({ t: ev.t + i * (ev.step || 0), d: ev.d || 0.5, from: Object.assign({}, ID, ev.from), to: Object.assign({}, ID, ev.to), ease: EASE[ev.ease || 'out'] });
      FADES.get(el).sort((a, b) => a.t - b.t);
    });
    return null;
  }
  function fades(t) {
    for (const [el, list] of FADES) {
      let cur = null;
      for (const f of list) if (t >= f.t) cur = f;
      let st = list[0].from;
      if (cur) { const p = cur.ease(clamp((t - cur.t) / cur.d, 0, 1)); st = {}; for (const k in ID) st[k] = cur.from[k] + (cur.to[k] - cur.from[k]) * p; }
      el.style.opacity = st.opacity;
      el.style.transform = BASE.get(el) + (st.x || st.y ? 'translate(' + st.x + 'px,' + st.y + 'px) ' : '') + (st.scale !== 1 ? 'scale(' + st.scale + ')' : '');
      el.style.filter = st.blur > 0.05 ? 'blur(' + st.blur.toFixed(2) + 'px)' : 'none';
    }
  }

  const SETS = new Map(), INIT = new Map();
  function setInit(ev) {
    const fresh = [];
    for (const el of targets(ev)) {
      if (!SETS.has(el)) { SETS.set(el, []); INIT.set(el, {}); fresh.push([el, SETS.get(el), {}]); }
      const init = INIT.get(el);
      for (const k of Object.keys(Object.assign({}, ev.before, ev.after))) if (!(k in init)) init[k] = el.getAttribute(k);
      SETS.get(el).push(ev);
      SETS.get(el).sort((a, b) => a.t - b.t);
    }
    if (!fresh.length) return null;
    return (t) => {
      for (const [el, list, last] of fresh) {
        const st = {};
        for (const e of list) for (const [k, v] of Object.entries(e.before || {})) if (!(k in st)) st[k] = v;
        for (const [k, v] of Object.entries(INIT.get(el))) if (!(k in st)) st[k] = v;
        for (const e of list) if (t >= e.t) Object.assign(st, e.after || {});
        for (const [k, v] of Object.entries(st)) if (last[k] !== v) { if (v === null) el.removeAttribute(k); else el.setAttribute(k, v); last[k] = v; }
      }
    };
  }

  function filmPoint(to) {
    if (Array.isArray(to)) return to;
    const r = find(to).getBoundingClientRect(), f = root.getBoundingClientRect(), k = D.size[0] / f.width;
    return [(r.left - f.left + r.width * (to.ax ?? 0.5)) * k + (to.dx || 0), (r.top - f.top + r.height * (to.ay ?? 0.5)) * k + (to.dy || 0)];
  }
  function cursorInit(ev) {
    const c = document.createElement('x-cursor'), size = ev.size || 44;
    c.innerHTML = '<svg viewBox="0 0 24 24" width="' + size + '" height="' + size + '"><path d="M4 2.5 L4 19.5 L8.6 15.2 L11.7 22 L14.6 20.7 L11.6 14 L18 13.6 Z" fill="' + (ev.fill || '#fff') + '" stroke="' + (ev.stroke || '#111') + '" stroke-width="1.4" stroke-linejoin="round"/></svg>';
    root.appendChild(c);
    const K = ev.path, tip = [4 * size / 24, 2.5 * size / 24];
    return (t) => {
      if (t < K[0].t || (ev.hide != null && t >= ev.hide + 0.2)) { c.style.opacity = 0; return; }
      let x, y;
      const i = K.findIndex((k, j) => j + 1 < K.length && t >= k.t && t < K[j + 1].t);
      if (i < 0) [x, y] = filmPoint(K[K.length - 1].to);
      else {
        const a = filmPoint(K[i].to), b = filmPoint(K[i + 1].to), u = EASE.inout(clamp((t - K[i].t) / (K[i + 1].t - K[i].t), 0, 1));
        const dx = b[0] - a[0], dy = b[1] - a[1], arc = Math.sin(Math.PI * u) * (K[i + 1].arc ?? ev.arc ?? 0.12);
        x = a[0] + dx * u - dy * arc; y = a[1] + dy * u + dx * arc;
      }
      let s = 1;
      for (const k of ev.clicks || []) { const u = t - k; if (u >= 0 && u < 0.06) s = 1 - 0.18 * u / 0.06; else if (u >= 0.06 && u < 0.21) s = 0.82 + 0.18 * (u - 0.06) / 0.15; }
      const fin = clamp((t - K[0].t) / 0.15, 0, 1), fout = ev.hide != null ? clamp((ev.hide + 0.2 - t) / 0.2, 0, 1) : 1;
      c.style.opacity = Math.min(fin, fout);
      c.style.transform = 'translate(' + (x - tip[0]) + 'px,' + (y - tip[1]) + 'px) scale(' + s + ')';
    };
  }

  const scroller = $('#scroll'), view = $('#view');
  const stickies = scroller ? [...scroller.querySelectorAll('[data-cap-pos=sticky]')] : [];
  const yIn = (el) => offset(el)[1] - offset(scroller)[1];
  function scrollInit(ev) {
    const val = (k) => (typeof k.y === 'number' ? k.y : yIn(find(k.y)) - (k.y.at ?? 0));
    ev.keys.forEach(val);
    const at = (t) => {
      const K = ev.keys;
      if (t <= K[0].t) return val(K[0]);
      for (let i = 0; i + 1 < K.length; i++) {
        if (t >= K[i + 1].t) continue;
        const a = val(K[i]), u = EASE[K[i + 1].ease || ev.ease || 'inout']((t - K[i].t) / (K[i + 1].t - K[i].t));
        return a + (val(K[i + 1]) - a) * u;
      }
      return val(K[K.length - 1]);
    };
    const f = document.createElementNS(NS, 'filter');
    f.setAttribute('id', 'mb');
    for (const [k, v] of Object.entries({ x: '0', y: '-5%', width: '100%', height: '110%' })) f.setAttribute(k, v);
    f.innerHTML = '<feGaussianBlur stdDeviation="0 0"/>';
    defs.appendChild(f);
    const g = f.firstChild;
    return (t) => {
      const y = at(t);
      scroller.style.transform = 'translateY(' + -y + 'px)';
      for (const el of stickies) { const k = Math.max(0, y - yIn(el)); el.style.transform = k ? 'translateY(' + k + 'px)' : ''; }
      const s = Math.min(ev.blur_max ?? 40, (ev.blur ?? 0.35) * Math.abs(at(t + 0.004) - at(t - 0.004)) / 0.008 / D.fps);
      g.setAttribute('stdDeviation', '0 ' + s.toFixed(2));
      view.style.filter = s > 0.3 ? 'url(#mb)' : 'none';
    };
  }

  const PROPS = new Map();
  function propInit(ev) {
    const name = ev.name || '--p', fresh = [];
    for (const el of targets(ev)) {
      if (!PROPS.has(el)) PROPS.set(el, new Map());
      const m = PROPS.get(el);
      if (!m.has(name)) { m.set(name, []); fresh.push([el, m.get(name)]); }
      m.get(name).push(ev);
      m.get(name).sort((a, b) => a.t - b.t);
    }
    if (!fresh.length) return null;
    return (t) => {
      for (const [el, list] of fresh) {
        let e = list[0];
        for (const f of list) if (t >= f.t) e = f;
        const a = e.from ?? 0, v = a + ((e.to ?? 1) - a) * EASE[e.ease || 'linear'](clamp((t - e.t) / (e.d || 1), 0, 1));
        el.style.setProperty(name, v.toFixed(4));
      }
    };
  }

  const EVENTS = { type: typeInit, press: pressInit, end_line: lineEndInit, dust: (ev) => { dustInit(ev); return null; }, fade: fadeInit, set: setInit, cursor: cursorInit, scroll: scrollInit, prop: propInit };
  const draws = [], late = [];
  for (const ev of D.events) {
    if (!EVENTS[ev.type]) throw new Error('unknown event ' + ev.type);
    const d = EVENTS[ev.type](ev);
    if (d) (ev.type === 'cursor' ? late : draws).push(d);
  }
  for (const s of D.shots) for (const f of [s.focus, s.focus_to]) if (f && !Array.isArray(f)) find(f);
  function state(t) { for (const d of draws) d(t); dust(t); fades(t); }
  let measured = false;
  function draw(t) {
    if (!measured && document.fonts.status === 'loaded') {
      for (const s of D.shots) { for (const v of smil) v.setCurrentTime(s.t0); state(s.t0); for (const f of [s.focus, s.focus_to]) if (f && !Array.isArray(f) && !f.live) fcache.set(f, focusPoint(f)); }
      measured = true;
    }
    for (const s of smil) s.setCurrentTime(t);
    state(t); camera(t); for (const d of late) d(t);
  }
  const [W0, W1] = D.win;
  const smil = [...root.querySelectorAll('svg')].filter((s) => s.querySelector('animate,animateTransform,animateMotion,set') && !s.parentElement.closest('svg'));
  smil.forEach((s) => s.pauseAnimations());
  const P = { t: W0 };
  draw(W0);
  const tl = gsap.timeline({ paused: true });
  tl.to(P, { t: W1, duration: W1 - W0, ease: 'none', onUpdate: () => draw(P.t) }, 0);
  window.__timelines['film'] = tl;
})();
