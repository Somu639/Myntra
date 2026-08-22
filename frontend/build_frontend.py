"""Copy Stitch HTML screens into a navigable static site."""
from __future__ import annotations

import re
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parent
EXTRACT = ROOT.parent / "_stitch_extract" / "stitch_myntra_discovery_engine"

PAGES = [
    ("home_myntra_discovery_engine", "index.html", "Home"),
    ("discovery_lab", "discovery_lab.html", "Discovery Lab"),
    ("search_and_library", "search_and_library.html", "Search and Library"),
    ("segments", "segments.html", "Segments"),
    ("raw_data", "raw_data.html", "Raw Data"),
    ("ai_roadmap", "ai_roadmap.html", "AI Roadmap"),
]
LABEL_TO_FILE = {label: dest for _, dest, label in PAGES}

NAV_RE = re.compile(r"<a\b[^>]*>.*?</a>", re.DOTALL | re.IGNORECASE)
HREF_RE = re.compile(r'href="#"', re.IGNORECASE)


def rewrite_nav(html: str) -> str:
    def repl(match: re.Match) -> str:
        block = match.group(0)
        for label, dest in LABEL_TO_FILE.items():
            if re.search(rf">\s*{re.escape(label)}\s*<", block) or re.search(
                rf">\s*{re.escape(label)}\s*</a>", block
            ):
                return HREF_RE.sub(f'href="{dest}"', block, count=1)
        return block

    return NAV_RE.sub(repl, html)


BACKEND_SNIPPET = """
<script src="config.js"></script>
<script>
(function () {
  var url = (window.STREAMLIT_BACKEND_URL || "").replace(/\\/$/, "");
  if (!url) return;
  document.querySelectorAll("a[href='#']").forEach(function () {});
  var link = document.getElementById("streamlit-backend-link");
  if (link) link.href = url;
})();
</script>
"""


def inject_backend_link(html: str) -> str:
    extra = """
<a id="streamlit-backend-link" href="https://share.streamlit.io/deploy?repository=Somu639/Myntra&amp;branch=master&amp;mainModule=streamlit_app.py" target="_blank" rel="noopener"
   class="mt-3 block w-full text-center py-2 rounded-DEFAULT font-button text-button"
   style="background:#FF3F6C;color:#fff;text-decoration:none;">Open Streamlit backend</a>
"""
    if "Open Streamlit backend" not in html:
        html = html.replace("</aside>", extra + "\n</aside>", 1)
        if extra.strip() not in html:
            html = html.replace("</nav>", extra + "\n</nav>", 1)
    if "</body>" in html:
        html = html.replace("</body>", BACKEND_SNIPPET + "\n</body>")
    return html


def main() -> None:
    if not EXTRACT.exists():
        raise SystemExit(f"Stitch extract not found: {EXTRACT}")
    for src_dir, dest, _label in PAGES:
        src = EXTRACT / src_dir / "code.html"
        html = src.read_text(encoding="utf-8")
        html = rewrite_nav(html)
        html = inject_backend_link(html)
        (ROOT / dest).write_text(html, encoding="utf-8")
        print("wrote", dest)


if __name__ == "__main__":
    main()
