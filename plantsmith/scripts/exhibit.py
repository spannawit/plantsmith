#!/usr/bin/env python3
"""Wrap a rendered PlantUML SVG as an html-plan `doc-mock` exhibit (stdlib only).

  python scripts/exhibit.py diagram.svg                       # fragment to stdout
  python scripts/exhibit.py diagram.svg --out diagram.exhibit.html --puml diagram.puml
  python scripts/exhibit.py diagram.svg --no-interactive      # the plain SVG only

It strips the XML prolog, DOCTYPE and processing instructions, drops the width/height that
would fight the frame (the viewBox stays), and tags every element, group and link PlantUML
drew with `data-ref="<slug>"` (slug from its first text, deduplicated), so a plan can pin
them with `<doc-pin ref="...">`; links also get `data-from` / `data-to`. Interactive (the
default): a scoped `<style>` (hover highlights an element and its lines, the rest dims),
`<title>` tooltips, a small toolbar and an inline script (pan, zoom, sticky highlight,
legend toggle; wheel zoom needs Ctrl/Cmd so the plan still scrolls). The width is the SVG's
own, capped at --w (480, html-plan's "smallest region" rule); a wider diagram is marked
`thumbnail`. The SVG must stay self-contained: an `<image>` is allowed only as a `data:` URI
(the icon libraries embed their icons that way), and any remote URL is refused.
Exit 0 on success, 1 on failure.
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

import interactive

MAX_W = 480
SLUG_MAX = 40
FRAMES = ("none", "browser", "phone", "desktop", "terminal")
PROLOG = re.compile(r"<\?xml[^>]*\?>|<!DOCTYPE[^>]*>|<\?plantuml[^>]*\?>", re.IGNORECASE)
GROUP = re.compile(r'<g\b([^>]*\bclass="(?:entity|cluster|link)"[^>]*)>')
TEXT = re.compile(r"<text\b[^>]*>([^<]*)</text>")
REMOTE = re.compile(r"""(?:href|src)\s*=\s*["']\s*(?:https?:)?//|url\(\s*["']?\s*(?:https?:)?//""", re.IGNORECASE)
IMAGE_HREF = re.compile(r"""<image\b[^>]*?\b(?:xlink:)?href\s*=\s*["']\s*([^"']*)""", re.IGNORECASE)
IMAGE = re.compile(r"<image\b", re.IGNORECASE)
SVG_OPEN = re.compile(r"<svg\b[^>]*>", re.IGNORECASE)


class ExhibitError(Exception):
    """A failure the user must see; the message is printed as-is."""


def slugify(text: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")
    if len(slug) > SLUG_MAX:  # cut at a word boundary, never mid-word
        slug = slug[:SLUG_MAX + 1].rsplit("-", 1)[0]
    return slug or "item"


def svg_width(svg_open: str) -> int:
    match = re.search(r'\bviewBox="[\d.\-]+\s+[\d.\-]+\s+([\d.]+)', svg_open) or re.search(r'\bwidth="([\d.]+)', svg_open)
    if not match:
        raise ExhibitError("the SVG has neither a viewBox nor a width")
    return int(float(match.group(1)))


def clean_svg_open(svg_open: str, sid: str | None) -> str:
    """Keep viewBox and namespaces; drop the fixed size that would fight the frame."""
    tag = re.sub(r'\s(?:width|height)="[^"]*"', "", svg_open)
    tag = re.sub(r'\s(?:style|preserveAspectRatio|id)="[^"]*"', "", tag)
    ident = f' id="{sid}"' if sid else ""
    return tag.replace("<svg", f'<svg{ident} style="width:100%;height:auto;display:block;background:#fff"', 1)


def group_text(svg: str, start: int, is_cluster: bool) -> str:
    """The words PlantUML drew for one group: its own <text> runs up to the group's end (a
    cluster: up to its first nested group, which is where its title stops)."""
    end = svg.find("</g>", start)
    if is_cluster:
        nested = svg.find("<g ", start)
        end = nested if 0 <= nested < end or end < 0 else end
    return " ".join(part.strip() for part in TEXT.findall(svg[start:end if end >= 0 else None]) if part.strip())


def tag_groups(svg: str, titles: bool = False, puml_lines: int = 0, puml_name: str = "") -> tuple[str, list[str], list[str]]:
    """Add data-ref to every entity, cluster and link group (links also data-from / data-to,
    and a <title> tooltip when asked). Returns the SVG, every ref, and the element refs."""
    refs: list[str] = []
    by_id: dict[str, str] = {}
    matches = list(GROUP.finditer(svg))

    def unique(base: str) -> str:
        slug, n = base, 2
        while slug in refs:
            slug, n = f"{base}-{n}", n + 1
        refs.append(slug)
        return slug

    slugs: list[str] = []
    words: list[str] = []
    for match in matches:  # elements first, so links can name both ends
        attrs = match.group(1)
        text = group_text(svg, match.end(), 'class="cluster"' in attrs)
        words.append(text)
        if 'class="link"' in attrs:
            slugs.append("")
            continue
        slug = unique(slugify(text) if text else "item")
        element_id = re.search(r'\bid="([^"]*)"', attrs)
        if element_id:
            by_id[element_id.group(1)] = slug
        slugs.append(slug)
    nodes = [s for s in slugs if s]
    ends: list[tuple[str, str] | None] = []
    for index, match in enumerate(matches):
        if slugs[index]:
            ends.append(None)
            continue
        names = [by_id.get(end, "item") for end in re.findall(r'data-entity-[12]="([^"]*)"', match.group(1))]
        slugs[index] = unique("link-" + "-to-".join(names) if names else "link")
        ends.append((names[0], names[1]) if len(names) == 2 else None)
    out, last = [], 0
    for index, match in enumerate(matches):
        attrs = match.group(1)
        extra = f' data-from="{ends[index][0]}" data-to="{ends[index][1]}"' if ends[index] else ""
        out.append(svg[last:match.start()])
        out.append(f'<g data-ref="{slugs[index]}"{extra}{attrs}>')
        if titles:
            kind = "link" if 'class="link"' in attrs else "element"
            line = re.search(r'data-source-line="(\d+)"', attrs)
            tip = interactive.title_for(words[index] or slugs[index], kind, ends[index],
                                        line.group(1) if line else None, puml_lines, puml_name)
            out.append(f"<title>{tip}</title>")
        last = match.end()
    out.append(svg[last:])
    return "".join(out), refs, nodes


def check_self_contained(svg: str) -> None:
    for href in IMAGE_HREF.findall(svg):
        if not href.lower().startswith("data:"):
            raise ExhibitError(f"the SVG embeds an <image> from {href[:60]!r}: only data: URIs keep it self-contained")
    if IMAGE.search(svg) and not IMAGE_HREF.search(svg):
        raise ExhibitError("the SVG embeds an <image> without an inline data: URI")
    if REMOTE.search(svg):
        raise ExhibitError("the SVG references a remote URL (href/src/url): refused, the page must not fetch anything")


def prepare(svg: str, sid: str | None, titles: bool, puml: Path | None) -> tuple[str, list[str], list[str], int]:
    """Clean, check and tag an SVG; returns (svg, refs, element refs, its width)."""
    check_self_contained(svg)
    svg = PROLOG.sub("", svg).strip()
    opening = SVG_OPEN.search(svg)
    if not opening:
        raise ExhibitError("no <svg> element found")
    width = svg_width(opening.group(0))
    svg = svg[:opening.start()] + clean_svg_open(opening.group(0), sid) + svg[opening.end():]
    lines = len(puml.read_text(encoding="utf-8").splitlines()) if puml else 0
    svg, refs, nodes = tag_groups(svg, titles, lines, puml.name if puml else "")
    return svg, refs, nodes, width


def exhibit(svg: str, max_w: int = MAX_W, frame: str = "none", interactive_layer: bool = True,
            puml: Path | None = None) -> tuple[str, list[str]]:
    if frame not in FRAMES:
        raise ExhibitError(f"--frame must be one of {', '.join(FRAMES)}")
    sid = interactive.svg_id(svg) if interactive_layer else None
    svg, refs, nodes, width = prepare(svg, sid, interactive_layer, puml)
    if interactive_layer:
        body = (interactive.css_layer(sid, nodes) + "\n" + interactive.toolbar(sid) + "\n" + svg + "\n<script>\n"
                + interactive.js_layer(sid, wheel_needs_modifier=True) + "\n</script>")
    else:
        body = svg
    w = min(width, max_w)
    thumbnail = " thumbnail" if width > max_w else ""
    fragment = f'<doc-mock frame="{frame}" w="{w}"{thumbnail}><template>\n{body}\n</template></doc-mock>\n'
    return fragment, refs


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Wrap a PlantUML SVG as an html-plan doc-mock exhibit.")
    parser.add_argument("svg", type=Path, help="rendered diagram (.svg)")
    parser.add_argument("--w", type=int, default=MAX_W, help=f"width cap in px (default {MAX_W})")
    parser.add_argument("--frame", default="none", help="doc-mock frame (default none)")
    parser.add_argument("--out", type=Path, help="write the fragment here (default: stdout)")
    parser.add_argument("--puml", type=Path, help="the diagram's source, so tooltips can name its lines")
    parser.add_argument("--no-interactive", dest="interactive", action="store_false",
                        help="the plain SVG, without the hover style, tooltips, toolbar and script")
    args = parser.parse_args(argv)
    try:
        fragment, refs = exhibit(args.svg.read_text(encoding="utf-8"), args.w, args.frame, args.interactive, args.puml)
    except (ExhibitError, OSError) as exc:
        print(f"FAILED: {exc}", file=sys.stderr)
        return 1
    if args.out:
        args.out.write_text(fragment, encoding="utf-8")
        print(f"wrote: {args.out}")
    else:
        sys.stdout.write(fragment)
    print(f"data-ref ({len(refs)}): {' '.join(refs)}", file=sys.stderr if not args.out else sys.stdout)
    return 0


if __name__ == "__main__":
    sys.exit(main())
