#!/usr/bin/env python3
"""Publish a rendered PlantUML SVG as one self-contained, interactive HTML page (stdlib only).

  python scripts/publish.py diagram.svg                        # writes diagram.page.html
  python scripts/publish.py diagram.svg --title "EMI platform" --out page.html --puml diagram.puml

The page holds the diagram (tagged like exhibit.py: data-ref, data-from/to, <title> tooltips),
the hover CSS layer and the pan/zoom script, a light/dark page theme (follows the system, with
a toggle), a legend toggle and a PNG export button (canvas, 2x). Nothing is fetched or vendored:
no external script, style or font. For vault system notes that are not plans. Exit 0 on
success, 1 on failure.
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

import exhibit
import interactive

TITLE_GROUP = re.compile(r'<g\b[^>]*class="title"[^>]*>(.*?)</g>', re.DOTALL)


def diagram_title(svg: str, fallback: str) -> str:
    match = TITLE_GROUP.search(svg)
    words = exhibit.TEXT.findall(match.group(1)) if match else []
    return " ".join(w.strip() for w in words if w.strip()) or fallback


def publish(svg: str, title: str | None = None, puml: Path | None = None, fallback: str = "diagram") -> str:
    sid = interactive.svg_id(svg)
    name = title or diagram_title(svg, fallback)
    tagged, _, nodes, _ = exhibit.prepare(svg, sid, True, puml)
    tagged = tagged.replace(' style="width:100%;height:auto;display:block;background:#fff"', "", 1)
    return interactive.page(name, tagged, interactive.css_layer(sid, nodes), interactive.toolbar(sid),
                            interactive.js_layer(sid, wheel_needs_modifier=False))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Publish a PlantUML SVG as a self-contained interactive page.")
    parser.add_argument("svg", type=Path, help="rendered diagram (.svg)")
    parser.add_argument("--title", help="page title (default: the diagram's own title)")
    parser.add_argument("--out", type=Path, help="output page (default: <name>.page.html beside the SVG)")
    parser.add_argument("--puml", type=Path, help="the diagram's source, so tooltips can name its lines")
    args = parser.parse_args(argv)
    out = args.out or args.svg.with_name(args.svg.stem + ".page.html")
    try:
        html = publish(args.svg.read_text(encoding="utf-8"), args.title, args.puml, args.svg.stem)
    except (exhibit.ExhibitError, OSError) as exc:
        print(f"FAILED: {exc}", file=sys.stderr)
        return 1
    out.write_text(html, encoding="utf-8")
    print(f"wrote: {out} ({len(html)} bytes, self-contained)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
