#!/usr/bin/env python3
"""Build the static dr.media site from the Claude Design canvas files.

usage: python3 tools/build.py <project_dir> <blobs_dir> [--accept-script]

  project_dir  the canvas's project/ folder (the board .dc.html, its css, ds/…)
  blobs_dir    folder holding the uploaded assets the board references, named <32-hex-id>.<ext>

Writes index.html, css, fonts, images and site.js into the repo root.
Exit codes: 0 ok · 2 missing blobs (ids listed) · 3 the board's script changed (port it to tools/site.js) · 1 anything else.
"""
import hashlib, html, json, os, re, shutil, sys

TOOLS = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(TOOLS)
CFG = json.load(open(os.path.join(TOOLS, "config.json"), encoding="utf-8"))


def die(msg, code=1):
    print("build: " + msg, file=sys.stderr)
    sys.exit(code)


# ---------- renderVals(): a tolerant reader for the JS object literal it returns ----------
RAW = object()  # a value that is not plain data (functions, variables, booleans)


def _ws(s, i):
    while i < len(s):
        if s[i].isspace():
            i += 1
        elif s.startswith("//", i):
            i = s.index("\n", i)
        else:
            break
    return i


def _string(s, i):
    q, out, i = s[i], [], i + 1
    while s[i] != q:
        if s[i] == "\\":
            i += 1
            out.append({"n": "\n", "t": "\t"}.get(s[i], s[i]))
        else:
            out.append(s[i])
        i += 1
    return "".join(out), i + 1


def _raw(s, i):
    depth = 0
    while i < len(s):
        c = s[i]
        if c in "'\"`":
            _, i = _string(s, i)
            continue
        if c in "([{":
            depth += 1
        elif c in ")]}":
            if depth == 0:
                break
            depth -= 1
        elif c == "," and depth == 0:
            break
        i += 1
    return RAW, i


def _value(s, i):
    i = _ws(s, i)
    if s[i] == "{":
        out, i = {}, _ws(s, i + 1)
        while s[i] != "}":
            if s[i] in "'\"":
                key, i = _string(s, i)
            else:
                m = re.compile(r"[\w$]+").match(s, i)
                key, i = m.group(0), m.end()
            i = _ws(s, i)
            if s[i] == ":":
                out[key], i = _value(s, i + 1)
            else:
                out[key] = RAW
            i = _ws(s, i)
            if s[i] == ",":
                i = _ws(s, i + 1)
        return out, i + 1
    if s[i] == "[":
        out, i = [], _ws(s, i + 1)
        while s[i] != "]":
            v, i = _value(s, i)
            out.append(v)
            i = _ws(s, i)
            if s[i] == ",":
                i = _ws(s, i + 1)
        return out, i + 1
    if s[i] in "'\"":
        j = _string(s, i)
        k = _ws(s, j[1])
        if k < len(s) and s[k] in ",}]":
            return j
    return _raw(s, i)


def render_vals(src):
    at = src.index("renderVals()")
    at = src.index("return {", at) + len("return ")
    return _value(src, at)[0]


def lookup(vals, path):
    cur = vals
    for part in path.split("."):
        if not isinstance(cur, dict) or part not in cur:
            die("the board uses {{%s}} but renderVals() does not return it as plain data" % path)
        cur = cur[part]
    return cur


# ---------- the design system's components (ds/drmedia/components/bundle.js), as static HTML ----------
E = html.escape


def dot(size=None):
    if size:
        return '<span class="dr-dot dr-dot--px" style="width: %dpx; height: %dpx" aria-hidden="true"></span>' % (size, size)
    return '<span class="dr-dot" aria-hidden="true"></span>'


def _group(items):
    out = []
    for i, it in enumerate(items):
        if i:
            out.append('<span class="dr-slate__sep" aria-hidden="true">—</span>')
        out.append("<span>%s</span>" % E(str(it)))
    return "".join(out)


def slate(p, children=""):
    left = ('<span class="dr-slate__rec">%sREC</span>' % dot(8) if p.get("rec") else "") + _group(p.get("items") or [])
    end = p.get("end") or []
    cls = "dr-slate" + (" dr-slate--ruled" if p.get("ruled") or end else "")
    inner = '<span class="dr-slate__group">%s</span><span class="dr-slate__group">%s</span>' % (left, _group(end)) if end else left
    style = ' style="%s"' % E(p["style"]) if p.get("style") else ""
    return '<div class="%s"%s>%s</div>' % (cls, style, inner)


def button(p, children=""):
    cls = "dr-btn dr-btn--%s" % (p.get("variant") or "primary") + (" dr-btn--sm" if p.get("size") == "sm" else "")
    arrow = '<span class="dr-btn__arrow" aria-hidden="true">→</span>' if p.get("arrow") else ""
    if p.get("href"):
        return '<a class="%s" href="%s">%s%s</a>' % (cls, E(p["href"]), children, arrow)
    return '<button class="%s" type="%s">%s%s</button>' % (cls, p.get("type") or "button", children, arrow)


def navbar(p, children=""):
    if p.get("logoSrc"):
        logo = '<img class="dr-nav__logo%s" src="%s" alt="dr.media">' % (" dr-on-bone" if p.get("logoSrcOnInk") else "", E(p["logoSrc"]))
    else:
        logo = '<span class="dr-nav__link">dr.media</span>'
    if p.get("logoSrcOnInk"):
        logo += '<img class="dr-nav__logo dr-on-ink" src="%s" alt="dr.media">' % E(p["logoSrcOnInk"])
    links = "".join('<li><a class="dr-nav__link" href="%s">%s</a></li>' % (E(l.get("href") or "#"), E(l["label"])) for l in p.get("links") or [])
    cta = p.get("cta")
    end = button({"variant": "signal", "size": "sm", "href": cta["href"], "arrow": True}, E(cta["label"])) if cta else ""
    return ('<header class="dr-nav"><a href="%s" aria-label="dr.media home">%s</a><nav aria-label="Main"><ul class="dr-nav__links">%s</ul></nav>'
            '<div class="dr-nav__end">%s</div></header>') % (E(p.get("homeHref") or "#top"), logo, links, end)


def frame(p, children=""):
    ratio = "var(--aspect-%s)" % (p.get("ratio") or "wide")
    media = ""
    if p.get("videoSrc"):
        media = '<video src="%s"%s muted playsinline loop%s></video>' % (E(p["videoSrc"]), ' poster="%s"' % E(p["src"]) if p.get("src") else "", " autoplay" if p.get("autoPlay") else "")
    elif p.get("src"):
        media = '<img src="%s" alt="%s">' % (E(p["src"]), E(p.get("alt") or ""))
    out = '<div class="dr-frame%s" style="aspect-ratio: %s%s">%s' % (" dr-frame--on-media" if media else "", ratio, "; " + E(p["style"]) if p.get("style") else "", media)
    if p.get("corners") is not False:
        out += '<span class="dr-frame__corners" aria-hidden="true"><i></i></span>'
    if p.get("topLeft") or p.get("topRight") or p.get("rec"):
        out += '<div class="dr-frame__overlay">%s%s</div>' % (slate({"rec": p.get("rec"), "items": p.get("topLeft") or []}), slate({"items": p["topRight"]}) if p.get("topRight") else "<span></span>")
    if p.get("bottomLeft") or p.get("bottomRight"):
        out += '<div class="dr-frame__overlay dr-frame__overlay--bottom">%s%s</div>' % (slate({"items": p.get("bottomLeft") or []}), slate({"items": p["bottomRight"]}) if p.get("bottomRight") else "<span></span>")
    return out + "</div>"


COMPONENTS = {"Slate": slate, "Button": button, "NavBar": navbar, "Frame": frame, "Dot": lambda p, c="": dot(p.get("size"))}


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    if len(args) != 2:
        die(__doc__)
    project, blobs = args
    board = os.path.join(project, CFG["board"])
    src = open(board, encoding="utf-8").read()
    vals = render_vals(src)
    vals.update({"yes": True, "true": True, "false": False})

    # The board's own logic is hand-ported to tools/site.js: stop when the source logic changes.
    logic = src[src.index("class Component"):src.index("renderVals()")]
    digest = hashlib.sha256(logic.encode("utf-8")).hexdigest()
    sha_file = os.path.join(TOOLS, "script.sha256")
    known = open(sha_file).read().strip() if os.path.exists(sha_file) else ""
    if digest != known:
        if "--accept-script" not in sys.argv:
            die("the board's script (motion/scroll logic) changed. Port the change to tools/site.js, then rerun with --accept-script.", 3)
        open(sha_file, "w").write(digest + "\n")

    body = re.search(r"<x-dc>\s*(?:<helmet>.*?</helmet>)?(.*)</x-dc>", src, re.S).group(1).strip()

    def x_import(m):
        attrs, children = dict(re.findall(r'([\w-]+)="([^"]*)"', m.group(1))), m.group(2)
        name = attrs.pop("component-from-global-scope", "").split(".")[-1]
        if name not in COMPONENTS:
            die("the board uses the component %r, which tools/build.py does not render yet" % name)
        props = {}
        for k, v in attrs.items():
            key = re.sub(r"-(\w)", lambda g: g.group(1).upper(), k)
            hole = re.fullmatch(r"\{\{([\w.]+)\}\}", v)
            props[key] = lookup(vals, hole.group(1)) if hole else html.unescape(v)
        return COMPONENTS[name](props, children)

    body = re.sub(r"<x-import\s+([^>]*)>(.*?)</x-import>", x_import, body, flags=re.S)

    # The idea form: the canvas mocks "sent"; the live site opens the visitor's email app (tools/site.js).
    body = re.sub(r'<sc-if value="\{\{notSent\}\}"[^>]*>\s*', "", body)
    body = re.sub(r'<sc-if value="\{\{sent\}\}"[^>]*>\s*<div role="status"', '<div role="status" id="idea-sent" hidden', body)
    body = re.sub(r"\s*</sc-if>", "", body)
    body = body.replace(' onSubmit="{{send}}"', ' id="idea-form"')
    body = body.replace("We’ll reach out at the email you gave us.", "Your email app just opened with the idea — hit send and we’ll reach out.")
    left = sorted(set(re.findall(r"<(?:x-import|sc-if|sc-for|dc-import)\b|\{\{[^}]*\}\}", body)))
    if left:
        die("the board uses markup tools/build.py does not handle yet: " + ", ".join(left))

    generated, missing = [], []

    def put(name, data):
        mode = "w" if isinstance(data, str) else "wb"
        with open(os.path.join(ROOT, name), mode, **({"encoding": "utf-8"} if mode == "w" else {})) as f:
            f.write(data)
        generated.append(name)

    def blob(m):
        found = [f for f in os.listdir(blobs) if f.startswith(m.group(1) + ".")] if os.path.isdir(blobs) else []
        if not found:
            missing.append(m.group(1))
            return m.group(0)
        name = "asset-%s%s" % (m.group(1)[:8], os.path.splitext(found[0])[1])
        put(name, open(os.path.join(blobs, found[0]), "rb").read())
        return name

    def stylesheet(href):
        path = os.path.join(project, href)
        css = open(path, encoding="utf-8").read()

        def url(m):
            ref = m.group(2)
            if re.match(r"(data:|https?:|#|/_blob/)", ref):
                return m.group(0)
            target = os.path.normpath(os.path.join(os.path.dirname(path), ref))
            if not os.path.exists(target):
                die("%s references %s, which is not in the canvas files" % (href, ref))
            put(os.path.basename(ref), open(target, "rb").read())
            return "url(%s%s%s)" % (m.group(1), os.path.basename(ref), m.group(1))

        css = re.sub(r"url\((['\"]?)([^)'\"]+)\1\)", url, css)
        css = re.sub(r"/_blob/([0-9a-f]{32})", blob, css)
        put(os.path.basename(href), css)
        return os.path.basename(href)

    head = src[:src.index("<body")]
    sheets = [stylesheet(h) for h in re.findall(r'<link rel="stylesheet" href="([^"]+)"', head)]
    body = re.sub(r"/_blob/([0-9a-f]{32})", blob, body)
    if missing:
        die("missing blobs — save each as <id>.<ext> in %s:\n%s" % (blobs, "\n".join(sorted(set(missing)))), 2)

    page = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>%s</title>
<meta name="description" content="%s">
<meta property="og:title" content="%s">
<meta property="og:description" content="%s">
<meta property="og:type" content="website">
<meta property="og:url" content="https://%s/">
%s
</head>
<body>
%s
<script src="site.js"></script>
</body>
</html>
""" % (E(CFG["title"]), E(CFG["description"]), E(CFG["title"]), E(CFG["description"]), CFG["domain"],
       "\n".join('<link rel="stylesheet" href="%s">' % s for s in sheets), body)
    put("index.html", page)
    put("site.js", open(os.path.join(TOOLS, "site.js"), encoding="utf-8").read().replace("__CONTACT_EMAIL__", CFG["contact_email"]))
    put("CNAME", CFG["domain"])

    # Drop files a previous build wrote that this one no longer does.
    manifest = os.path.join(TOOLS, "generated.txt")
    old = open(manifest).read().split("\n") if os.path.exists(manifest) else []
    for name in old:
        if name and name not in generated and os.path.exists(os.path.join(ROOT, name)):
            os.remove(os.path.join(ROOT, name))
    open(manifest, "w").write("\n".join(sorted(set(generated))) + "\n")
    print("build: wrote %d files from %s" % (len(set(generated)), CFG["board"]))


if __name__ == "__main__":
    main()
