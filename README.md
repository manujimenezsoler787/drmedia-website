# dr.media website

The live site at https://drmediacreative.com, served by GitHub Pages from this branch.

The page is generated from the Claude Design canvas named in `tools/config.json` (the `board` entry picks which artboard is published). Don't edit `index.html` or the css by hand: change the design, then rebuild.

    python3 tools/build.py <canvas project folder> <folder with the canvas's uploaded images>

- `tools/build.py` turns the artboard into plain HTML and copies its css, fonts and images.
- `tools/site.js` is the scroll motion and the idea form (which opens the visitor's email app). It is a hand port of the artboard's script; the build stops if that script changes so the port can be updated.

## Checking it on a phone-sized screen

`tools/dev/mtest.py <repo folder> <output folder>` drives a headless Chrome as a 390×844 touch phone: it swipes through the page, reports frame times and layout shifts, and saves a still of each screen. It needs Google Chrome installed and nothing else.
