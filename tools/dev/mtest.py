import json, subprocess, sys, time, os
sys.path.insert(0, os.path.dirname(__file__))
from cdp import launch, phone, shot
repo, out = sys.argv[1], sys.argv[2]
os.makedirs(out, exist_ok=True)
srv = subprocess.Popen([sys.executable, "-m", "http.server", "8767", "--directory", repo], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
chrome, ws = launch(os.path.join(out, "profile"))
try:
    phone(ws)
    ws.call("Page.enable"); ws.call("Page.navigate", url="http://127.0.0.1:8767/")
    time.sleep(2.5)
    REC = """
    window.__rec = {frames: [], err: [], cls: 0, shifts: [], slow: []};
    new PerformanceObserver(l => l.getEntries().forEach(e => { if (!e.hadRecentInput) { __rec.cls += e.value; __rec.shifts.push([Math.round(scrollY), +e.value.toFixed(4)]); } })).observe({type: 'layout-shift', buffered: false});
    (function () {
      const tr = document.querySelector('.op-track'); const range = (p, a, b) => Math.min(1, Math.max(0, (p - a) / (b - a)));
      const ease = t => t < 0.5 ? 4*t*t*t : 1 - Math.pow(-2*t+2, 3)/2; let last = performance.now();
      function loop(t) { const dt = t - last; __rec.frames.push(+dt.toFixed(1)); if (dt > 25 && __rec.frames.length > 3) __rec.slow.push([Math.round(scrollY), Math.round(dt)]); last = t; setTimeout(sample, 0); requestAnimationFrame(loop); }
      function sample() {
        const r = tr.getBoundingClientRect(); const inner = tr.firstElementChild.offsetHeight;
        const p = Math.min(1, Math.max(0, -r.top / Math.max(1, r.height - inner)));
        if (r.bottom > 0) __rec.err.push(Math.abs(ease(range(p, 0.40, 0.92)) - (+tr.style.getPropertyValue('--i') || 0)) + Math.abs(ease(range(p, 0.08, 0.54)) - (+tr.style.getPropertyValue('--o') || 0)));
      }
      requestAnimationFrame(loop);
    })(); 'ok'"""
    info = ws.js("JSON.stringify({w: innerWidth, h: innerHeight, cls: document.documentElement.className, page: document.documentElement.scrollHeight, coarse: matchMedia('(pointer: coarse)').matches, overflowX: document.documentElement.scrollWidth - innerWidth})")
    print("page", info)
    def stats(label):
        r = json.loads(ws.js("JSON.stringify(__rec)")); f = sorted(r["frames"][3:]) or [0]; e = r["err"] or [0]
        print("%-28s frames %4d  median %5.1fms  p95 %5.1fms  worst %6.1fms  >25ms: %3d | hero sync err mean %.3f max %.3f | layout shift %.4f %s" % (
            label, len(f), f[len(f)//2], f[int(len(f)*0.95)], f[-1], sum(1 for x in f if x > 25), sum(e)/len(e), max(e), r["cls"], r["shifts"][:6]) + "\n      slow frames (scrollY, ms): " + str(r["slow"][:24]))
    def gesture(dist, speed):
        ws.call("Input.synthesizeScrollGesture", x=195, y=560, yDistance=dist, speed=speed, gestureSourceType="touch", repeatCount=1)
    for label, speed in (("hero, slow swipe 500px/s", 500), ("hero, fast swipe 2500px/s", 2500)):
        ws.js("window.scrollTo(0,0)"); time.sleep(0.5); ws.js(REC)
        gesture(-1900, speed); time.sleep(0.6); stats(label)
        ws.js(REC); gesture(1900, speed); time.sleep(0.6); stats(label + " (back up)")
    ws.js("window.scrollTo(0,0)"); time.sleep(0.5); ws.js(REC)
    page = json.loads(info)["page"]; done = 0
    while done < page:
        gesture(-2400, 1600); done += 2400
    time.sleep(0.5); stats("whole page, 1600px/s")
    print("end", ws.js("JSON.stringify({y: Math.round(scrollY), max: document.documentElement.scrollHeight - innerHeight, cls: document.documentElement.className})"))
    # stills for visual review
    ws.call("Emulation.setDeviceMetricsOverride", width=390, height=844, deviceScaleFactor=1, mobile=True)
    ws.js("window.scrollTo(0,0)"); time.sleep(0.8)
    page = ws.js("document.documentElement.scrollHeight"); y = 0; n = 0
    while y < page - 844 + 1 and n < 40:
        ws.js("window.scrollTo(0,%d)" % y); time.sleep(0.9)
        shot(ws, os.path.join(out, "m%02d.jpg" % n)); n += 1; y += 760
    ws.js("window.scrollTo(0, document.documentElement.scrollHeight)"); time.sleep(0.9); shot(ws, os.path.join(out, "m%02d.jpg" % n))
    print("stills", n + 1, "page height", page)
finally:
    chrome.kill(); srv.kill()
