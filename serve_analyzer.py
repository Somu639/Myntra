"""Local HTML viewer for Stage 4 discovery output.

Reads discovery_report.json and serves a one-page analyzer on localhost.
Does not change any analysis — it only renders the existing report.

Usage
-----
    python serve_analyzer.py              # http://127.0.0.1:8080
    python serve_analyzer.py --port 8765
"""

from __future__ import annotations

import argparse
import html
import json
import os
import sys
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

ROOT = Path(__file__).resolve().parent
REPORT = ROOT / "discovery_report.json"
OUT_HTML = ROOT / "analyzer.html"
DEFAULT_PORT = 8080


def load_report() -> dict:
    if not REPORT.exists():
        sys.exit(f"Missing {REPORT.name}. Run python discover.py first.")
    return json.loads(REPORT.read_text(encoding="utf-8"))


def esc(v) -> str:
    return html.escape("" if v is None else str(v))


def render(report: dict) -> str:
    cov = report.get("coverage", {})
    opps = report.get("opportunity_areas") or report.get("q2_purchase_blockers") or []
    q1 = report.get("q1_why_wishlist", {})
    q8 = report.get("q8_intent_vs_bookmark", {})
    q3 = report.get("q3_post_like_uncertainty", {})
    q4 = report.get("q4_postponement", {})
    q6 = report.get("q6_off_platform_research", {})
    q7 = report.get("q7_dimension_roles", {})
    q9 = report.get("q9_by_segment", [])

    opp_rows = []
    for i, o in enumerate(opps, 1):
        opp_rows.append(
            "<tr>"
            f"<td>{i}</td>"
            f"<td>{esc(o.get('blocker_type'))}</td>"
            f"<td>{esc(o.get('dimension'))}</td>"
            f"<td class='num'>{esc(o.get('mentions'))}</td>"
            f"<td class='num'>{esc(o.get('reach_pct_of_relevant'))}</td>"
            f"<td class='num'>{esc(o.get('frustration_rate_pct'))}</td>"
            f"<td class='num'><strong>{esc(o.get('opportunity_score'))}</strong></td>"
            "</tr>"
        )

    dim_rows = []
    for d in q7.get("by_dimension") or []:
        dim_rows.append(
            "<tr>"
            f"<td>{esc(d.get('dimension'))}</td>"
            f"<td class='num'>{esc(d.get('mentions'))}</td>"
            f"<td class='num'>{esc(d.get('share_pct'))}%</td>"
            "</tr>"
        )

    ch_rows = []
    for ch, n in q6.get("by_channel") or []:
        ch_rows.append(f"<tr><td>{esc(ch)}</td><td class='num'>{esc(n)}</td></tr>")

    seg_rows = []
    for s in q9:
        seg_rows.append(
            "<tr>"
            f"<td>{esc(s.get('blocker_type'))}</td>"
            f"<td class='num'>{esc(s.get('mentions'))}</td>"
            f"<td class='num'>{esc(s.get('known_segment_coverage_pct'))}</td>"
            f"<td>{esc(s.get('top_segment'))}</td>"
            f"<td class='num'>{esc(s.get('top_segment_concentration_pct'))}</td>"
            "</tr>"
        )

    reasons = q1.get("top_reasons") or []
    reason_html = (
        "<ul>"
        + "".join(f"<li>{esc(r)} ({esc(c)})</li>" for r, c in reasons)
        + "</ul>"
        if reasons
        else "<p class='muted'>No stated reasons extracted.</p>"
    )

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>Fashion review analyzer</title>
  <style>
    :root {{
      --bg: #111111;
      --panel: #1a1a1a;
      --text: #e8e8e8;
      --muted: #9a9a9a;
      --line: #2a2a2a;
      --accent: #c96442;
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0; font-family: Georgia, "Times New Roman", serif;
      background: var(--bg); color: var(--text); line-height: 1.5;
    }}
    main {{ max-width: 980px; margin: 0 auto; padding: 40px 24px 80px; }}
    h1 {{ font-size: 28px; font-weight: 600; margin: 0 0 8px; }}
    h2 {{ font-size: 20px; margin: 36px 0 12px; font-weight: 600; }}
    p, li {{ font-size: 15px; }}
    .muted {{ color: var(--muted); }}
    .stats {{ display: grid; grid-template-columns: repeat(4, 1fr); gap: 12px; margin: 24px 0; }}
    .stat {{ background: var(--panel); border: 1px solid var(--line); padding: 16px; }}
    .stat .v {{ font-size: 26px; font-weight: 600; }}
    .stat .l {{ color: var(--muted); font-size: 13px; }}
    table {{ width: 100%; border-collapse: collapse; font-size: 14px; }}
    th, td {{ text-align: left; padding: 8px 10px; border-bottom: 1px solid var(--line); }}
    th {{ color: var(--muted); font-weight: 600; font-size: 12px; text-transform: uppercase; }}
    td.num {{ text-align: right; font-variant-numeric: tabular-nums; }}
    .note {{ border: 1px solid var(--line); padding: 12px 16px; background: var(--panel); }}
    @media (max-width: 720px) {{ .stats {{ grid-template-columns: 1fr 1fr; }} }}
  </style>
</head>
<body>
<main>
  <h1>Fashion review analyzer</h1>
  <p class="muted">
    Local render of discovery_report.json — Myntra voice-of-customer.
    Directional ranking, not a statistically representative sample.
  </p>

  <div class="stats">
    <div class="stat"><div class="v">{esc(cov.get("extracted"))}/{esc(cov.get("total_records"))}</div><div class="l">Extracted</div></div>
    <div class="stat"><div class="v">{esc(cov.get("failed", 0))}</div><div class="l">Failed</div></div>
    <div class="stat"><div class="v">{esc(cov.get("relevant"))}</div><div class="l">Relevant</div></div>
    <div class="stat"><div class="v">{esc(opps[0].get("opportunity_score") if opps else "—")}</div><div class="l">Top score ({esc(opps[0].get("blocker_type") if opps else "")})</div></div>
  </div>

  <div class="note">
    Wishlist signals: {esc(q1.get("wishlist_mentions", 0))}.
    Q8 intent vs bookmark: genuine {esc(q8.get("genuine_intent"))},
    bookmarking {esc(q8.get("bookmarking"))},
    unclear {esc(q8.get("unclear"))}.
    People rarely review about wishlists — treat Q1/Q8 as under-sampled.
  </div>

  <h2>Opportunity areas (ranked)</h2>
  <p class="muted">Score = 50% reach + 50% frustration. Mentions among {esc(cov.get("relevant"))} relevant items.</p>
  <table>
    <thead><tr><th>#</th><th>Blocker</th><th>Dimension</th><th>Mentions</th><th>Reach %</th><th>Frustration %</th><th>Score</th></tr></thead>
    <tbody>{"".join(opp_rows)}</tbody>
  </table>

  <h2>Q1 — Why users wishlist</h2>
  {reason_html}

  <h2>Q3 — Uncertainty after liking a product</h2>
  <p>{esc(q3.get("mentions"))} mentions ({esc(q3.get("share_of_blockers_pct"))}% of blockers).</p>

  <h2>Q4 — What postpones a purchase</h2>
  <p>{esc(q4.get("mentions"))} mentions ({esc(q4.get("share_of_blockers_pct"))}% of blockers).</p>

  <h2>Q6 — Off-platform research</h2>
  <p>Off-platform: {esc(q6.get("off_platform_total"))} ({esc(q6.get("off_platform_pct_of_relevant"))}% of relevant).</p>
  <table>
    <thead><tr><th>Channel</th><th>Mentions</th></tr></thead>
    <tbody>{"".join(ch_rows)}</tbody>
  </table>

  <h2>Q7 — Role of fit, price, returns, etc.</h2>
  <table>
    <thead><tr><th>Dimension</th><th>Mentions</th><th>Share of blockers</th></tr></thead>
    <tbody>{"".join(dim_rows)}</tbody>
  </table>

  <h2>Q9 — Segment concentration</h2>
  <p class="muted">Segment labels are model-inferred, not verified.</p>
  <table>
    <thead><tr><th>Blocker</th><th>Mentions</th><th>Coverage %</th><th>Top segment</th><th>Concentration %</th></tr></thead>
    <tbody>{"".join(seg_rows)}</tbody>
  </table>
</main>
</body>
</html>
"""


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description="Serve the discovery report on localhost.")
    p.add_argument("--port", type=int, default=DEFAULT_PORT)
    args = p.parse_args(argv)

    html_out = render(load_report())
    OUT_HTML.write_text(html_out, encoding="utf-8")
    os.chdir(ROOT)

    class Handler(SimpleHTTPRequestHandler):
        def log_message(self, fmt, *a):
            print(f"  {self.address_string()}  {fmt % a}")

        def do_GET(self):
            if self.path in ("/", "/index.html"):
                self.path = "/analyzer.html"
            return super().do_GET()

    server = ThreadingHTTPServer(("127.0.0.1", args.port), Handler)
    url = f"http://127.0.0.1:{args.port}/"
    print(f"Review analyzer at {url}")
    print("Press Ctrl+C to stop.")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopped.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
