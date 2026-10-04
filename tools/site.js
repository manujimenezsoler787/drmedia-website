/* dr.media — scroll motion, live timecode and the idea form. */
(function () {
  var doc = document.documentElement;
  var raf = 0, motion = false, io = null;

  function timecode(ms) {
    var pad = function (n) { return String(n).padStart(2, '0'); };
    var s = Math.floor(ms / 1000);
    var f = Math.floor((ms % 1000) / (1000 / 24));
    return 'TC ' + pad(Math.floor(s / 3600)) + ':' + pad(Math.floor(s / 60) % 60) + ':' + pad(s % 60) + ':' + pad(f);
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
    if (!motion) {
      ['--p-open', '--p-prompter', '--p-fn', '--p-steps', '--sc', '--a-fn', '--drop', '--scene', '--cta-bar', '--page-p', '--hud'].forEach(function (k) { doc.style.removeProperty(k); });
      return;
    }
    var vh = window.innerHeight;
    document.querySelectorAll('[data-scrub]').forEach(function (el) {
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
      p = Math.min(1, Math.max(0, p));
      var key = el.getAttribute('data-scrub');
      doc.style.setProperty('--p-' + key, p.toFixed(4));
      if (key === 'open') {
        var lines = Math.max(1, el.querySelectorAll('.op-line').length);
        doc.style.setProperty('--sc', String(Math.min(lines - 1, Math.floor(p * lines))));
      }
      if (key === 'fn') {
        var a = r.top > vh * 0.2 ? -1 : Math.min(3, Math.floor(p * 4));
        doc.style.setProperty('--a-fn', String(a));
        doc.style.setProperty('--drop', a >= 3 ? '1' : '0');
      }
    });
    var max = Math.max(1, doc.scrollHeight - vh);
    doc.style.setProperty('--page-p', (window.scrollY / max).toFixed(4));
    var open = document.querySelector('.op-track');
    var idea = document.getElementById('idea');
    var past = open ? open.getBoundingClientRect().bottom < vh * 0.25 : false;
    var atForm = idea ? idea.getBoundingClientRect().top < vh * 0.9 : false;
    doc.style.setProperty('--cta-bar', past && !atForm ? '1' : '0');
    doc.style.setProperty('--hud', past ? '1' : '0');
    var scene = '';
    document.querySelectorAll('[data-scene]').forEach(function (el) {
      var r = el.getBoundingClientRect();
      if (r.top <= vh * 0.5 && r.bottom > vh * 0.5) scene = el.getAttribute('data-scene');
    });
    if (scene) doc.style.setProperty('--scene', '"' + scene.replace(/"/g, '') + '"');
  }

  function setup() {
    var reduce = window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches;
    doc.classList.remove('dr-motion');
    var scrolls = doc.scrollHeight > window.innerHeight * 2;
    motion = !reduce && scrolls;
    if (motion) doc.classList.add('dr-motion');
    tick();
  }

  function observe() {
    if (!io) return;
    document.querySelectorAll('[data-reveal], [data-drop], [data-count]').forEach(function (el) {
      if (!el.classList.contains('is-in')) io.observe(el);
    });
  }

  window.addEventListener('scroll', function () {
    if (!raf) raf = requestAnimationFrame(function () { raf = 0; tick(); });
  }, { passive: true });
  window.addEventListener('resize', setup);

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
  setInterval(function () {
    doc.style.setProperty('--tc', '"' + timecode(Date.now() - start) + '"');
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
      window.location.href = 'mailto:__CONTACT_EMAIL__?subject=' + encodeURIComponent('An idea from ' + d.get('name')) + '&body=' + encodeURIComponent(text);
      form.hidden = true;
      sent.hidden = false;
    });
  }
})();
