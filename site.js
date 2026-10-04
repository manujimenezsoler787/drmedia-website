/* dr.media — scroll motion, live timecode and the idea form. */
(function () {
  var doc = document.documentElement;
  var raf = 0, motion = false, io = null;
  var open = { el: null, target: 0, cur: 0, raf: 0, last: 0 };
  var coarse = !!(window.matchMedia && window.matchMedia('(pointer: coarse)').matches);
  var lastW = 0;

  function timecode(ms) {
    var pad = function (n) { return String(n).padStart(2, '0'); };
    var s = Math.floor(ms / 1000);
    var f = Math.floor((ms % 1000) / (1000 / 24));
    return 'TC ' + pad(Math.floor(s / 3600)) + ':' + pad(Math.floor(s / 60) % 60) + ':' + pad(s % 60) + ':' + pad(f);
  }

  /* Only touch a custom property when its value changes, and set it on the element that uses it,
     so a scroll frame restyles one section instead of the whole page. */
  function setVar(el, k, v) { if (el && el.style.getPropertyValue(k) !== v) el.style.setProperty(k, v); }
  function range(p, a, b) { return Math.min(1, Math.max(0, (p - a) / (b - a))); }
  function ease(t) { return t < 0.5 ? 4 * t * t * t : 1 - Math.pow(-2 * t + 2, 3) / 2; }

  /* The cold open is scrubbed: the headline follows the scroll position, eased toward it each frame. */
  function glideOpen(now) {
    open.raf = 0;
    var dt = open.last ? Math.min(64, now - open.last) : 16;
    open.last = now;
    var d = open.target - open.cur;
    /* A finger already scrolls smoothly, so touch screens follow it exactly; a mouse wheel gets some glide. */
    open.cur = coarse || Math.abs(d) < 0.0006 ? open.target : open.cur + d * (1 - Math.exp(-dt / 110));
    /* One scroll position drives the whole cold open: the feed flies and brakes (f), line 01 leaves (o),
       one post lights up (l) and takes over the screen (k), line 02 lands on it (i). */
    var p = open.cur;
    setVar(open.el, '--f', (1 - Math.pow(1 - range(p, 0, 0.46), 3)).toFixed(4));
    setVar(open.el, '--o', ease(range(p, 0.24, 0.50)).toFixed(4));
    setVar(open.el, '--l', range(p, 0.42, 0.52).toFixed(4));
    setVar(open.el, '--k', ease(range(p, 0.50, 0.72)).toFixed(4));
    setVar(open.el, '--i', ease(range(p, 0.70, 0.94)).toFixed(4));
    open.el.classList.toggle('is-held', p > 0.2);
    if (open.cur !== open.target) open.raf = requestAnimationFrame(glideOpen);
    else open.last = 0;
  }

  function countUp(el) {
    if (!motion) return;
    var to = parseFloat(el.getAttribute('data-count')) || 0;
    var dec = parseInt(el.getAttribute('data-decimals') || '0', 10);
    var suffix = el.getAttribute('data-suffix') || '';
    var t0 = performance.now();
    function step(now) {
      var p = Math.min(1, (now - t0) / 1600);
      el.textContent = (to * (1 - Math.pow(1 - p, 3))).toFixed(dec) + suffix;
      if (p < 1) requestAnimationFrame(step);
    }
    requestAnimationFrame(step);
  }

  function tick() {
    var scrubs = document.querySelectorAll('[data-scrub]');
    var prog = document.querySelector('.prog');
    var hud = document.querySelector('.hud');
    var mbar = document.querySelector('.mbar');
    if (!motion) {
      scrubs.forEach(function (el) { ['--p-' + el.getAttribute('data-scrub'), '--sc', '--f', '--o', '--l', '--k', '--i', '--a-fn', '--drop'].forEach(function (k) { el.style.removeProperty(k); }); });
      if (prog) prog.style.removeProperty('--page-p');
      if (hud) { hud.style.removeProperty('--hud'); hud.style.removeProperty('--scene'); }
      if (mbar) mbar.style.removeProperty('--cta-bar');
      return;
    }
    /* Read everything first, then write, so a frame never forces layout twice. */
    var vh = window.innerHeight;
    var reads = [];
    scrubs.forEach(function (el) {
      var r = el.getBoundingClientRect();
      var mode = el.getAttribute('data-mode');
      var p;
      if (mode === 'sticky') {
        var inner = el.firstElementChild ? el.firstElementChild.offsetHeight : vh;
        p = -r.top / Math.max(1, r.height - inner);
      } else if (mode === 'line') {
        p = (vh * 0.6 - r.top) / Math.max(1, r.height);
      } else {
        p = (vh - r.top) / (vh + r.height);
      }
      reads.push({ el: el, key: el.getAttribute('data-scrub'), top: r.top, p: Math.min(1, Math.max(0, p)) });
    });
    var max = Math.max(1, doc.scrollHeight - vh);
    var pageP = window.scrollY / max;
    var openTrack = document.querySelector('.op-track');
    var idea = document.getElementById('idea');
    var past = openTrack ? openTrack.getBoundingClientRect().bottom < vh * 0.25 : false;
    var atForm = idea ? idea.getBoundingClientRect().top < vh * 0.9 : false;
    var scene = '';
    document.querySelectorAll('[data-scene]').forEach(function (el) {
      var r = el.getBoundingClientRect();
      if (r.top <= vh * 0.5 && r.bottom > vh * 0.5) scene = el.getAttribute('data-scene');
    });

    reads.forEach(function (m) {
      setVar(m.el, '--p-' + m.key, m.p.toFixed(4));
      if (m.key === 'open') {
        var lines = Math.max(1, m.el.querySelectorAll('.op-line').length);
        setVar(m.el, '--sc', String(Math.min(lines - 1, Math.floor(m.p * lines))));
        open.el = m.el;
        open.target = m.p;
        if (!open.raf) glideOpen(performance.now());
      }
      if (m.key === 'fn') {
        var a = m.top > vh * 0.2 ? -1 : Math.min(3, Math.floor(m.p * 4));
        setVar(m.el, '--a-fn', String(a));
        setVar(m.el, '--drop', a >= 3 ? '1' : '0');
      }
    });
    setVar(prog, '--page-p', pageP.toFixed(4));
    setVar(mbar, '--cta-bar', past && !atForm ? '1' : '0');
    setVar(hud, '--hud', past ? '1' : '0');
    if (scene) setVar(hud, '--scene', '"' + scene.replace(/"/g, '') + '"');
  }

  function setup() {
    var reduce = window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches;
    var next = !reduce && doc.scrollHeight > window.innerHeight * 2;
    if (next !== motion) { motion = next; doc.classList.toggle('dr-motion', motion); }
    lastW = window.innerWidth;
    tick();
  }

  function observe() {
    if (!io) return;
    document.querySelectorAll('[data-reveal], [data-drop], [data-count]').forEach(function (el) {
      if (!el.classList.contains('is-in')) io.observe(el);
    });
  }

  function onScroll() { if (!raf) raf = requestAnimationFrame(function () { raf = 0; tick(); }); }
  window.addEventListener('scroll', onScroll, { passive: true });
  /* Phones fire resize whenever the browser bar slides in or out mid-scroll: only a width change is a real resize. */
  window.addEventListener('resize', function () { if (window.innerWidth === lastW) onScroll(); else setup(); });

  if ('IntersectionObserver' in window) {
    io = new IntersectionObserver(function (entries) {
      entries.forEach(function (e) {
        if (e.isIntersecting) { e.target.classList.add('is-in'); if (e.target.hasAttribute('data-count')) countUp(e.target); io.unobserve(e.target); }
      });
    }, { threshold: 0.12, rootMargin: '0px 0px -6% 0px' });
  }

  setup();
  observe();

  var start = Date.now();
  var clocks = document.querySelectorAll('.tc');
  setInterval(function () {
    if (document.hidden) return;
    var tc = '"' + timecode(Date.now() - start) + '"';
    clocks.forEach(function (el) { el.style.setProperty('--tc', tc); });
  }, 84);

  /* The idea form has no backend yet: it opens the visitor's email app with the idea filled in. */
  var form = document.getElementById('idea-form');
  var sent = document.getElementById('idea-sent');
  if (form && sent) {
    form.addEventListener('submit', function (e) {
      e.preventDefault();
      var d = new FormData(form);
      var kind = d.get('kind') ? 'What I need: ' + d.get('kind') + '\n\n' : '';
      var text = kind + (d.get('idea') || '') + '\n\n— ' + d.get('name') + '\n' + d.get('email');
      window.location.href = 'mailto:hello@drmediacreativeinc.com?subject=' + encodeURIComponent('An idea from ' + d.get('name')) + '&body=' + encodeURIComponent(text);
      form.hidden = true;
      sent.hidden = false;
    });
  }
})();
