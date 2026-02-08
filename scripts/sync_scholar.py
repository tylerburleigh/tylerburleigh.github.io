#!/usr/bin/env python3
"""Fetch Google Scholar citation stats and generate a styled HTML chart.

Uses the `scholarly` library to pull citation-per-year data, h-index,
i10-index, and total citations, then writes a self-contained HTML snippet
that replicates the Google Scholar profile widget.

Usage:
    python scripts/sync_scholar.py              # Fetch and generate
    python scripts/sync_scholar.py --dry-run    # Print data, don't write
    python scripts/sync_scholar.py --verbose    # Show raw API data
"""

import argparse
import json
import math
import os
from datetime import datetime
from pathlib import Path

from scholarly import scholarly

SCHOLAR_ID = "FOsvdhUAAAAJ"
OUTPUT_DIR = Path("_static")
OUTPUT_HTML = OUTPUT_DIR / "scholar-chart.html"
OUTPUT_DATA = OUTPUT_DIR / "scholar-data.json"


def fetch_scholar_data(verbose: bool = False) -> dict:
    """Fetch author profile from Google Scholar."""
    print(f"Fetching Google Scholar profile for {SCHOLAR_ID}...")
    author = scholarly.search_author_id(SCHOLAR_ID)
    author = scholarly.fill(author, sections=["indices", "counts"])

    if verbose:
        keys = ("name", "citedby", "citedby5y", "hindex", "hindex5y",
                "i10index", "i10index5y", "cites_per_year")
        print(json.dumps({k: v for k, v in author.items() if k in keys},
                         indent=2, default=str))

    return {
        "name": author.get("name", ""),
        "citations": author.get("citedby", 0),
        "citations5y": author.get("citedby5y", 0),
        "h_index": author.get("hindex", 0),
        "h_index5y": author.get("hindex5y", 0),
        "i10_index": author.get("i10index", 0),
        "i10_index5y": author.get("i10index5y", 0),
        "cites_per_year": author.get("cites_per_year", {}),
        "fetched": datetime.now().isoformat(timespec="seconds"),
    }


def _nice_ticks(max_val: int, num_ticks: int = 5) -> list[int]:
    """Generate clean axis tick values (e.g. 0, 85, 170, 255, 340)."""
    if max_val <= 0:
        return [0]
    raw_step = max_val / (num_ticks - 1)
    # Round step up to a "nice" number
    magnitude = 10 ** math.floor(math.log10(raw_step))
    nice_steps = [1, 2, 2.5, 5, 10]
    step = magnitude
    for ns in nice_steps:
        candidate = ns * magnitude
        if candidate >= raw_step:
            step = int(candidate)
            break
    ticks = [step * i for i in range(num_ticks)]
    # Trim ticks that overshoot by too much
    while len(ticks) > 2 and ticks[-1] > max_val * 1.3:
        ticks.pop()
    return ticks


def generate_html(data: dict) -> str:
    """Build HTML that replicates the Google Scholar citation widget."""
    cites = data["cites_per_year"]
    if not cites:
        return "<p>No citation data available.</p>"

    years = sorted(cites.keys())
    max_val = max(cites.values()) if cites else 1
    ticks = _nice_ticks(max_val)
    chart_max = ticks[-1] if ticks[-1] >= max_val else max_val

    # Since-year label (scholarly gives 5y stats)
    since_year = datetime.now().year - 5

    # --- Stats table ---
    stats_html = f"""  <table class="gs-table">
    <thead>
      <tr>
        <th></th>
        <th>All</th>
        <th>Since {since_year}</th>
      </tr>
    </thead>
    <tbody>
      <tr>
        <td class="gs-row-label">Citations</td>
        <td>{data['citations']}</td>
        <td>{data['citations5y']}</td>
      </tr>
      <tr>
        <td class="gs-row-label">h-index</td>
        <td>{data['h_index']}</td>
        <td>{data['h_index5y']}</td>
      </tr>
      <tr>
        <td class="gs-row-label">i10-index</td>
        <td>{data['i10_index']}</td>
        <td>{data['i10_index5y']}</td>
      </tr>
    </tbody>
  </table>"""

    # --- Bar chart ---
    bars = []
    for year in years:
        count = cites[year]
        pct = (count / chart_max) * 100 if chart_max else 0
        bars.append(
            f'        <div class="gs-col">\n'
            f'          <div class="gs-bar" style="height: {pct:.1f}%"></div>\n'
            f'          <span class="gs-year">{year}</span>\n'
            f'        </div>'
        )
    bars_html = "\n".join(bars)

    # --- Y-axis tick labels (right side, evenly spaced) ---
    tick_labels = []
    for tick in reversed(ticks):
        tick_labels.append(f'        <span class="gs-tick">{tick}</span>')
    ticks_html = "\n".join(tick_labels)

    # --- Gridlines ---
    gridlines = []
    for tick in ticks:
        pct = (tick / chart_max) * 100 if chart_max else 0
        gridlines.append(
            f'        <div class="gs-gridline" style="bottom: {pct:.1f}%"></div>'
        )
    gridlines_html = "\n".join(gridlines)

    chart_html = f"""  <div class="gs-chart-wrap">
    <div class="gs-chart-area">
{gridlines_html}
      <div class="gs-bars">
{bars_html}
      </div>
    </div>
    <div class="gs-y-axis">
{ticks_html}
    </div>
  </div>"""

    footer_html = (
        f'  <p class="gs-footer">'
        f'Data from <a href="https://scholar.google.com/citations?user={SCHOLAR_ID}">'
        f'Google Scholar</a>'
        f' · Updated {datetime.fromisoformat(data["fetched"]).strftime("%b %Y")}'
        f'</p>'
    )

    return f'<div class="gs-widget">\n{stats_html}\n{chart_html}\n{footer_html}\n</div>\n'


def run(dry_run: bool = False, verbose: bool = False) -> None:
    data = fetch_scholar_data(verbose=verbose)

    print(f"\n  Citations:       {data['citations']}  (5y: {data['citations5y']})")
    print(f"  h-index:         {data['h_index']}  (5y: {data['h_index5y']})")
    print(f"  i10-index:       {data['i10_index']}  (5y: {data['i10_index5y']})")
    print(f"  Years:           {sorted(data['cites_per_year'].keys())}")
    print(f"  Per year:        {data['cites_per_year']}\n")

    if dry_run:
        print("[DRY RUN] Would write to:")
        print(f"  {OUTPUT_HTML}")
        print(f"  {OUTPUT_DATA}")
        return

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    html = generate_html(data)
    OUTPUT_HTML.write_text(html, encoding="utf-8")
    print(f"  Wrote {OUTPUT_HTML}")

    OUTPUT_DATA.write_text(json.dumps(data, indent=2), encoding="utf-8")
    print(f"  Wrote {OUTPUT_DATA}")

    print("\nDone!")


def main():
    parser = argparse.ArgumentParser(
        description="Fetch Google Scholar stats and generate citation chart")
    parser.add_argument("--dry-run", action="store_true",
                        help="Preview without writing files")
    parser.add_argument("--verbose", action="store_true",
                        help="Show raw API data")
    args = parser.parse_args()

    # Ensure we run from repo root
    if not OUTPUT_DIR.exists():
        script_dir = Path(__file__).resolve().parent
        repo_root = script_dir.parent
        os.chdir(repo_root)

    run(dry_run=args.dry_run, verbose=args.verbose)


if __name__ == "__main__":
    main()
