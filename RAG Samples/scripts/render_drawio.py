"""Render a .drawio file to PNG with the official draw.io viewer in headless Chromium.

Usage (from RAG Samples/):
  python -m pip install -r requirements-docs.txt && python -m playwright install chromium
  python scripts/render_drawio.py C4-Diagram-RAG.drawio C4-Diagram-RAG.png

The draw.io viewer script is downloaded once into .cache/ (gitignored).
"""

import sys
import urllib.request
from pathlib import Path

from playwright.sync_api import sync_playwright

VIEWER_URL = "https://raw.githubusercontent.com/jgraph/drawio/dev/src/main/webapp/js/viewer-static.min.js"
CACHE = Path(__file__).resolve().parents[1] / ".cache" / "viewer-static.min.js"


def main(source: Path, output: Path) -> None:
    if not CACHE.exists():
        CACHE.parent.mkdir(parents=True, exist_ok=True)
        urllib.request.urlretrieve(VIEWER_URL, CACHE)
    output = output.resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    page_file = output.with_suffix(".render.html")
    page_file.write_text(
        "<!doctype html><html><head><meta charset=utf-8><style>body{margin:0;background:#fff}"
        "#d{display:inline-block;padding:32px;background:#fff}</style></head>"
        f'<body><div id=d></div><script src="{CACHE.as_uri()}"></script></body></html>',
        encoding="utf-8",
    )
    try:
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch()
            page = browser.new_page(viewport={"width": 1600, "height": 1000}, device_scale_factor=2)
            page.goto(page_file.as_uri())
            page.wait_for_function("typeof GraphViewer !== 'undefined'")
            page.evaluate(
                """(xml) => {
                    const el = document.getElementById('d');
                    el.className = 'mxgraph';
                    el.setAttribute('data-mxgraph', JSON.stringify({xml, nav: false, toolbar: null, lightbox: false, resize: true}));
                    GraphViewer.processElements();
                }""",
                source.read_text(encoding="utf-8"),
            )
            page.wait_for_selector("#d svg", state="attached")
            page.wait_for_timeout(2000)
            page.locator("#d").screenshot(path=str(output))
            browser.close()
    finally:
        page_file.unlink(missing_ok=True)
    print(f"Wrote {output}")


if __name__ == "__main__":
    if len(sys.argv) != 3:
        sys.exit(__doc__)
    main(Path(sys.argv[1]), Path(sys.argv[2]))
