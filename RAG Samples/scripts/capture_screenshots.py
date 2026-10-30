"""Capture the README screenshots for POC 1 into docs/screenshots/.

Two modes:

  --offline   No OpenAI key or database needed. Captures the Streamlit input
              screen and renders the deterministic part of the pipeline
              (report -> marker tags -> safety-filtered candidate pool) using
              the real parser and safety rules from src/.

  (default)   Full run. Requires OPENAI_API_KEY, the database seeded and
              ingested, and Streamlit running on port 8501. Clicks
              "Run recommendation" for R1, R2 and R3 and saves full-page
              screenshots of the real results.

Usage (from RAG Samples/):
  python -m pip install -r requirements-docs.txt && python -m playwright install chromium
  python scripts/capture_screenshots.py --offline
  streamlit run src/streamlit_app.py --server.headless true &
  python scripts/capture_screenshots.py
"""

import argparse
import html
import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from playwright.sync_api import Page, sync_playwright  # noqa: E402

from src.config import SAMPLE_DATA_ROOT  # noqa: E402
from src.models import Article  # noqa: E402
from src.pipeline import load_report  # noqa: E402
from src.report_parser import parse_report  # noqa: E402
from src.retriever import is_safe_candidate  # noqa: E402

OUT_DIR = PROJECT_ROOT / "docs" / "screenshots"
APP_URL = "http://localhost:8501"
REPORTS = {
    "R1": ("R1 — Happy path", "report1_happy_path.json"),
    "R2": ("R2 — Safety trap", "report2_safety_trap.json"),
    "R3": ("R3 — Content gap (postpartum)", "report3_content_gap.json"),
}
HIDE_CHROME = (
    "[data-testid=stToolbar],[data-testid=stDecoration],"
    "[data-testid=stStatusWidget],header{display:none!important}"
)


def _open_app(page: Page) -> None:
    page.goto(APP_URL)
    page.wait_for_selector("text=Run recommendation", timeout=60_000)
    page.add_style_tag(content=HIDE_CHROME)
    page.wait_for_timeout(1500)


def _choose_report(page: Page, label: str) -> None:
    page.locator("[data-testid=stSelectbox]").click()
    page.get_by_role("option", name=label).click()
    page.wait_for_timeout(1500)


def capture_input_screen(page: Page) -> None:
    _open_app(page)
    page.screenshot(path=str(OUT_DIR / "01-streamlit-input.png"), full_page=True)


def capture_full_runs(page: Page) -> None:
    _open_app(page)
    for number, (report_id, (label, _)) in enumerate(REPORTS.items(), start=3):
        _choose_report(page, label)
        page.get_by_role("button", name="Run recommendation").click()
        page.wait_for_selector("text=Grounded summary", timeout=180_000)
        page.wait_for_timeout(1500)
        # Open the article snapshots so readers can see what was retrieved.
        for expander in page.locator("[data-testid=stExpander] summary").all():
            expander.click()
        page.wait_for_timeout(800)
        page.screenshot(path=str(OUT_DIR / f"0{number}-result-{report_id}.png"), full_page=True)


def _load_articles() -> list[Article]:
    raw = json.loads((SAMPLE_DATA_ROOT / "articles.json").read_text(encoding="utf-8"))
    items = raw if isinstance(raw, list) else raw["articles"]
    return [Article.model_validate(item) for item in items]


def _exclusion_reason(article: Article, markers: list[str]) -> str:
    if article.is_default:
        return "generic default"
    if not article.approved:
        return "not approved"
    clash = sorted(set(article.contraindications).intersection(markers))
    if clash:
        return f"contraindicated: {', '.join(clash)}"
    return "high intensity + hypertension"


def _walkthrough_html() -> str:
    articles = [a for a in _load_articles() if a.category in ("physical", "mental")]
    cards = []
    for report_id, (label, filename) in REPORTS.items():
        report = load_report(SAMPLE_DATA_ROOT / "reports" / filename)
        markers = parse_report(report)
        columns = []
        for category in ("physical", "mental"):
            pool = [a for a in articles if a.category == category]
            eligible = [a for a in pool if is_safe_candidate(a, markers)]
            excluded = [a for a in pool if not is_safe_candidate(a, markers)]
            rows = "".join(
                f"<li class=out><code>{a.id}</code> {html.escape(a.title)}"
                f"<span>{html.escape(_exclusion_reason(a, markers))}</span></li>"
                for a in excluded
            )
            columns.append(
                f"<div class=col><h4>{category.title()}</h4>"
                f"<p class=count><b>{len(eligible)}</b> of {len(pool)} articles eligible for ranking</p>"
                f"<ul>{rows or '<li class=none>Nothing excluded</li>'}</ul></div>"
            )
        tags = "".join(f"<span class=tag>{m}</span>" for m in markers) or "<i>none</i>"
        cards.append(
            f"<section><h3>{html.escape(label)}</h3>"
            f"<p class=note>Report note: “{html.escape(report.notes)}”</p>"
            f"<p><b>Marker tags</b> {tags}</p><div class=cols>{''.join(columns)}</div></section>"
        )
    return f"""<!doctype html><html><head><meta charset=utf-8><style>
body{{font-family:-apple-system,Segoe UI,Roboto,sans-serif;margin:0;padding:32px;background:#f6f7f9;color:#1f2328;width:1100px}}
h2{{margin:0 0 4px}} .sub{{color:#57606a;margin:0 0 20px}}
section{{background:#fff;border:1px solid #d0d7de;border-radius:10px;padding:18px 22px;margin-bottom:16px}}
h3{{margin:0 0 6px}} .note{{color:#57606a;margin:0 0 8px;font-style:italic}}
.tag{{display:inline-block;background:#ddf4ff;color:#0550ae;border-radius:12px;padding:2px 10px;margin:0 4px;font-size:13px;font-family:monospace}}
.cols{{display:grid;grid-template-columns:1fr 1fr;gap:18px;margin-top:10px}}
h4{{margin:0 0 4px}} .count{{margin:0 0 6px;color:#1a7f37}}
ul{{margin:0;padding-left:18px;font-size:13px}} li{{margin:3px 0}} li span{{color:#cf222e;margin-left:6px}}
li.none{{color:#57606a;list-style:none;margin-left:-18px}} code{{font-size:12px;color:#57606a}}
.foot{{color:#57606a;font-size:13px;margin-top:6px}}
</style></head><body>
<h2>Deterministic stage: report → markers → safety-filtered candidate pool</h2>
<p class=sub>Computed with <code>src/report_parser.py</code> and <code>src/retriever.is_safe_candidate</code> against the bundled synthetic data.
Vector ranking (top 3 per category) and the cited summary need the OpenAI API; capture those with a full run of this script.</p>
{''.join(cards)}
<p class=foot>Note R3: only <code>poor_sleep</code> is marked — “postpartum” lives in the free-text note and no article covers it, so plain RAG will still rank the nearest eligible articles.</p>
</body></html>"""


def capture_walkthrough(page: Page) -> None:
    page.set_content(_walkthrough_html())
    page.wait_for_timeout(300)
    page.locator("body").screenshot(path=str(OUT_DIR / "02-pipeline-safety-filter.png"))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--offline", action="store_true", help="capture only what runs without an API key")
    args = parser.parse_args()
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        page = browser.new_page(viewport={"width": 1280, "height": 900}, device_scale_factor=2)
        if args.offline:
            capture_walkthrough(page)
            capture_input_screen(page)
        else:
            capture_full_runs(page)
        browser.close()
    print(f"Screenshots saved to {OUT_DIR}")


if __name__ == "__main__":
    main()
