"""Minimal Chrome DevTools client (stdlib only): drives a headless Chrome as a phone and measures scroll."""
import base64, json, os, socket, struct, subprocess, sys, time, urllib.request
CHROME = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
class WS:
    def __init__(self, url):
        host, rest = url[5:].split("/", 1); h, p = host.split(":")
        self.s = socket.create_connection((h, int(p))); key = base64.b64encode(os.urandom(16)).decode()
        self.s.sendall(("GET /%s HTTP/1.1\r\nHost: %s\r\nUpgrade: websocket\r\nConnection: Upgrade\r\nSec-WebSocket-Key: %s\r\nSec-WebSocket-Version: 13\r\n\r\n" % (rest, host, key)).encode())
        buf = b""
        while b"\r\n\r\n" not in buf: buf += self.s.recv(4096)
        self.buf = buf.split(b"\r\n\r\n", 1)[1]; self.id = 0
    def _read(self, n):
        while len(self.buf) < n:
            d = self.s.recv(65536)
            if not d: raise EOFError
            self.buf += d
        out, self.buf = self.buf[:n], self.buf[n:]; return out
    def recv(self):
        data = b""
        while True:
            b0, b1 = self._read(2); n = b1 & 127
            if n == 126: n = struct.unpack(">H", self._read(2))[0]
            elif n == 127: n = struct.unpack(">Q", self._read(8))[0]
            data += self._read(n)
            if b0 & 0x80: return json.loads(data.decode()) if (b0 & 15) in (0, 1) else None
    def send(self, obj):
        p = json.dumps(obj).encode(); m = os.urandom(4); n = len(p)
        hdr = b"\x81" + (bytes([0x80 | n]) if n < 126 else bytes([0xFE]) + struct.pack(">H", n) if n < 65536 else bytes([0xFF]) + struct.pack(">Q", n))
        self.s.sendall(hdr + m + bytes(b ^ m[i % 4] for i, b in enumerate(p)))
    def call(self, method, **params):
        self.id += 1; i = self.id; self.send({"id": i, "method": method, "params": params})
        while True:
            r = self.recv()
            if r and r.get("id") == i:
                if "error" in r: raise RuntimeError(r["error"])
                return r["result"]
    def js(self, expr):
        r = self.call("Runtime.evaluate", expression=expr, awaitPromise=True, returnByValue=True)
        if "exceptionDetails" in r: raise RuntimeError(r["exceptionDetails"].get("exception", {}).get("description", str(r["exceptionDetails"])))
        return r["result"].get("value")
def launch(profile, port=9333):
    p = subprocess.Popen([CHROME, "--headless=new", "--remote-debugging-port=%d" % port, "--user-data-dir=" + profile, "--hide-scrollbars", "--no-first-run", "about:blank"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    for _ in range(50):
        try:
            tabs = json.load(urllib.request.urlopen("http://127.0.0.1:%d/json" % port))
            page = [t for t in tabs if t["type"] == "page"][0]
            return p, WS(page["webSocketDebuggerUrl"])
        except Exception: time.sleep(0.2)
    p.kill(); raise RuntimeError("chrome did not start")
def phone(ws, w=390, h=844):
    ws.call("Emulation.setDeviceMetricsOverride", width=w, height=h, deviceScaleFactor=3, mobile=True)
    ws.call("Emulation.setTouchEmulationEnabled", enabled=True, maxTouchPoints=5)
    ws.call("Emulation.setEmulatedMedia", features=[{"name": "pointer", "value": "coarse"}])
def shot(ws, path):
    open(path, "wb").write(base64.b64decode(ws.call("Page.captureScreenshot", format="jpeg", quality=70)["data"]))
