#!/usr/bin/env python3
"""Static house-style checks for PlantUML sources (stdlib only, no rendering).

Rules (STYLE.md numbers in brackets):
  no-title           ERROR  every diagram has a `title`                      [title rule]
  colour-no-legend   ERROR  a colour is used but there is no legend          [9]
  dashed-unmarked    ERROR  a dashed edge exists but no "not stated"/"inferred" [5]
  preamble-fence     ERROR  preamble markers missing, repeated or out of order
  long-label         WARN   a label line is over 40 characters, or a line inside an
                            element body `[ ... ]` is over 48                [4]
  long-field         WARN   an entity/class/object field (name, type, mark) is over
                            48 characters, so it wraps under wrapWidth 300   [4]
  creole-in-label    WARN   an unescaped `__` or `**` in a label, caption or field
                            (Creole underline/bold eats identifiers; write `~__`)
  inline-colour      WARN   #colour / skinparam colour outside the preamble while
                            a preamble or <style> exists                     [9]
  no-ortho           ERROR  a line-routing diagram without `skinparam linetype ortho`
                            (sequence and Gantt are exempt)           [No noodle lines]
  curved-lines       ERROR  `skinparam linetype` set to anything but ortho, or `splines=`
                            in a @startdot block that is not ortho/polyline [No noodle lines]
  legend-background  WARN   a legend without a transparent background        [house]
C4 sources (`!include <C4/...>`) also get the c4-* rules, and icon sources (`<awslib...>`,
`<azure...>`, `<gcp...>`) the icon-* rules, both in lint_c4.py. C4 style macros are exempt
from inline-colour. Every line-routing diagram, C4 and icon files included, needs ortho.
Exit 1 when any ERROR is found, else 0.
"""
from __future__ import annotations

import argparse
import re
import sys
from dataclasses import dataclass
from pathlib import Path

import lint_c4

MAX_LABEL = 40
MAX_BODY = 48  # an entity field or a `[ ... ]` body line stays on one line under wrapWidth 300
PREAMBLE_BEGIN = "house-preamble-begin"
PREAMBLE_END = "house-preamble-end"

COLOUR_TOKEN = re.compile(r"(?<![<\w&])#(?:[0-9A-Fa-f]{6}|[0-9A-Fa-f]{3}|[A-Za-z]{3,})\b")
RELATION = re.compile(
    r"^\s*[\w\"\[\](). ]+?\s*(<?[-.]+(?:\[[^\]]*\])?[-.]*>?)\s*[\w\"\[\]()]"
)
# A dotted arrow WITH an arrowhead (`..>`, `<..`, `.right.>`, `.>`) or a [dashed]/[dotted] style;
# a plain `..` link has no arrowhead and is not an inference.
DIRECTION = r"(?:(?:up|down|left|right|u|d|l|r)\.+)?"
DASHED_ARROW = re.compile(
    rf"<\.+{DIRECTION}|\.+{DIRECTION}>|\[[^\]]*\b(?:dashed|dotted)\b[^\]]*\]", re.IGNORECASE
)
KEYWORDS = (
    r"(?:actor|participant|boundary|control|entity|database|collections|queue|rectangle|"
    r"component|node|cloud|package|frame|folder|file|card|artifact|storage|hexagon|usecase|"
    r"agent|stack|person|process|action|label|interface|class|object|state|box|partition)"
)
ELEMENT = re.compile(rf"^\s*{KEYWORDS}\b\s+\"([^\"]+)\"")
BRACKET_LABEL = re.compile(rf"^\s*{KEYWORDS}\b\s+[^\[\]\"]*\[([^\]]+)\]")
STYLE_COLOUR = re.compile(r"\b(?:BackgroundColor|LineColor)\b", re.IGNORECASE)
ALIAS_LABEL = re.compile(r"\bas\s+\"([^\"]+)\"")
TASK = re.compile(r"^\s*\[([^\]]+)\]")
SEQ_SEPARATOR = re.compile(r"^\s*(?:\.{3}|\|\|\d*\|\||==.*==|--.*--|\.\..*\.\.)\s*$")
MARKUP = re.compile(r"\*\*|//|__|<[^>]+>")
STYLE_CLASS = re.compile(r"^\s*\.(\w+)\s*\{([^}]*)\}", re.MULTILINE)
CREOLE_PAIR = re.compile(r"(?<!~)(?:__|\*\*)")
BODY_OPENER = re.compile(
    r"^\s*(?:entity|class|object|abstract|interface|enum|struct|annotation)\b[^{]*\{\s*$", re.IGNORECASE
)
BODY_SEPARATOR = re.compile(r"^\s*(?:--|\.\.|==|__)(?:.*(?:--|\.\.|==|__))?\s*$")
FIELD_MODIFIER = re.compile(r"^\s*(?:\{(?:field|method|static|abstract|classifier)\}\s*)*\*?\s*")

BLOCK_OPENERS = (  # (block name or None for the first word, opener, closer)
    ("note", re.compile(r"^\s*(?:floating\s+)?note\b(?!.*:)"), re.compile(r"^\s*end\s*note\b")),
    (None, re.compile(r"^\s*(?:legend(?:\s+(?:left|right|center|top|bottom)){0,2}|title|header|footer|caption)\s*$",
                      re.IGNORECASE),  # `legend`, `legend right`, `legend top left`
     re.compile(r"^\s*end\s*(?:legend|title|header|footer|caption)\b", re.IGNORECASE)),
    ("style", re.compile(r"^\s*<style>"), re.compile(r"^\s*</style>")),
    ("bracket", re.compile(rf"^\s*{KEYWORDS}\b[^\[\]]*\[\s*$", re.IGNORECASE), re.compile(r"^\s*\]")),
)


@dataclass(frozen=True)
class Finding:
    line: int
    severity: str
    rule: str
    message: str


@dataclass(frozen=True)
class Line:
    number: int
    text: str
    in_preamble: bool
    block: str  # "", "note", "legend", "style", "json", "body"


def classify(text: str) -> list[Line]:
    """Tag each line with its region so rules can skip preamble, notes, legends and styles."""
    lines: list[Line] = []
    in_preamble = False
    block = ""
    closer: re.Pattern | None = None
    json_depth = 0
    for number, raw in enumerate(text.splitlines(), start=1):
        stripped = raw.strip()
        if PREAMBLE_BEGIN in stripped:
            in_preamble = True
        if json_depth:
            json_depth += raw.count("{") - raw.count("}")
            lines.append(Line(number, raw, in_preamble, "json"))
            continue
        if closer is not None:
            lines.append(Line(number, raw, in_preamble, block))
            if closer.search(raw):
                closer, block = None, ""
            if PREAMBLE_END in stripped:
                in_preamble = False
            continue
        if re.match(r"^\s*json\b", raw):
            json_depth = max(raw.count("{") - raw.count("}"), 0)
            lines.append(Line(number, raw, in_preamble, "json"))
            continue
        for name, opener, end in BLOCK_OPENERS:
            if opener.search(raw):
                block = name or raw.split()[0].lower()
                closer = end
                break
        kind = block or ("comment" if stripped.startswith("'") else "")
        lines.append(Line(number, raw, in_preamble, kind))
        if PREAMBLE_END in stripped:
            in_preamble = False
    return lines


def label_segments(label: str) -> list[str]:
    parts = re.split(r"\\n|<br\s*/?>|\n", label)
    return [MARKUP.sub("", part).strip() for part in parts]


DIRECTIVE = re.compile(r"^\s*(?:title|header|footer|caption|legend|note|skinparam)\b", re.IGNORECASE)


def labels_on(line: str) -> list[str]:
    if DIRECTIVE.match(line):  # a title or note line is not a relation, whatever hyphens it holds
        return []
    found = []
    for pattern in (ELEMENT, TASK, BRACKET_LABEL):
        match = pattern.search(line)
        if match:
            found.append(match.group(1))
    found += ALIAS_LABEL.findall(line)
    arrow = RELATION.search(line)
    if arrow and ":" in line[arrow.end():]:
        found.append(line[arrow.end():].split(":", 1)[1])
    return found


def is_dashed(line: str) -> bool:
    """A relation whose arrow is dotted with an arrowhead (`..>`, `.right.>`) or [dashed]/[dotted]."""
    if SEQ_SEPARATOR.match(line) or re.match(r"^\s*[-.=]{2,}", line) or not RELATION.search(line):
        return False
    head = re.sub(r'"[^"]*"', '""', line.split(":", 1)[0])  # the arrow, not its caption or names
    return bool(DASHED_ARROW.search(head))


def is_comment(ln: Line) -> bool:
    return ln.text.strip().startswith("'")


def directives(lines: list[Line]) -> tuple[bool, bool]:
    """(has title, has legend): top-level directives only, never inside notes, styles,
    comments or element bodies (an entity column called `title` is not a title)."""
    depth = 0
    has_title = has_legend = False
    for ln in lines:
        if ln.block not in ("", "title", "legend") or is_comment(ln):
            continue
        if depth == 0:
            has_title = has_title or bool(re.match(r"^\s*title\b", ln.text, re.I))
            has_legend = has_legend or bool(
                re.match(r"^\s*(?:legend\b|SHOW_LEGEND\s*\(|SHOW_FLOATING_LEGEND\s*\()", ln.text, re.I)
            )
        if ln.block == "":
            depth = max(depth + ln.text.count("{") - ln.text.count("}"), 0)
    return has_title, has_legend


def style_colour_line(lines: list[Line]) -> int:
    """First line where a general <style> selector outside the preamble sets a colour
    (class selectors count where an element uses them; legend styling never counts)."""
    selectors: list[str] = []
    for ln in lines:
        if ln.block != "style" or ln.in_preamble:
            continue
        pending = ""
        for piece in re.split(r"([{}])", ln.text):
            if piece == "{":
                selectors.append(pending.strip().lower())
            elif piece == "}":
                if selectors:
                    selectors.pop()
            else:
                pending = piece
                general = selectors and not any(s.startswith((".", "legend")) for s in selectors)
                if general and STYLE_COLOUR.search(piece):
                    return ln.number
    return 0


def fence_findings(lines: list[Line]) -> list[Finding]:
    begins = [ln.number for ln in lines if PREAMBLE_BEGIN in ln.text]
    ends = [ln.number for ln in lines if PREAMBLE_END in ln.text]
    if (not begins and not ends) or (len(begins) == len(ends) == 1 and begins[0] < ends[0]):
        return []
    return [Finding(
        (begins or ends)[0], "ERROR", "preamble-fence",
        f"{PREAMBLE_BEGIN} and {PREAMBLE_END} must each appear once, begin first: checks skip what they fence",
    )]


def line_labels(ln: Line) -> list[str]:
    if ln.block == "bracket" and not re.search(r"\[\s*$|^\s*\]", ln.text):
        return [ln.text]  # a line of a multi-line `component C [ ... ]` description
    return labels_on(ln.text)


def field_lines(lines: list[Line]) -> list[Line]:
    """Member lines inside `entity`/`class`/`object` bodies (not separators, not table rows)."""
    stack: list[str] = []
    fields: list[Line] = []
    for ln in lines:
        if ln.in_preamble or ln.block != "" or is_comment(ln):
            continue
        inside = bool(stack) and stack[-1] == "fields"
        if inside and not re.match(r"^\s*\}", ln.text) and ln.text.strip():
            if not BODY_SEPARATOR.match(ln.text) and not ln.text.strip().startswith("|"):
                fields.append(ln)
        if BODY_OPENER.match(ln.text):
            stack.append("fields")
            continue
        for char in ln.text:
            if char == "{":
                stack.append("other")
            elif char == "}" and stack:
                stack.pop()
    return fields


def field_text(raw: str) -> str:
    """What a field prints: modifiers dropped, `<<FK>>` as `«FK»`, Creole and escapes removed."""
    text = FIELD_MODIFIER.sub("", raw.strip(), count=1)
    text = re.sub(r"<<([^>]*)>>", r"«\1»", text)
    return MARKUP.sub("", text).replace("~", "").strip()


def creole_findings(lines: list[Line], fields: list[Line]) -> list[Finding]:
    message = "unescaped Creole pair `__` / `**` prints as underline/bold: escape identifiers as `~__`"
    findings = []
    for ln in lines:
        if ln.in_preamble or ln.block not in ("", "bracket") or is_comment(ln):
            continue
        if any(CREOLE_PAIR.search(label) for label in line_labels(ln)):
            findings.append(Finding(ln.number, "WARN", "creole-in-label", message))
    seen = {f.line for f in findings}
    findings += [
        Finding(ln.number, "WARN", "creole-in-label", message)
        for ln in fields
        if ln.number not in seen and CREOLE_PAIR.search(ln.text)
    ]
    return findings


SEQUENCE = re.compile(r"^\s*(?:participant|actor|autonumber|lifeline|activate)\b", re.IGNORECASE | re.MULTILINE)
LINETYPE = re.compile(r"^\s*skinparam\s+linetype\s+(\w+)", re.IGNORECASE)
SPLINES = re.compile(r"\bsplines\s*=\s*\"?(\w+)", re.IGNORECASE)


def line_findings(lines: list[Line], code: str, is_gantt: bool) -> list[Finding]:
    """No noodle lines: ortho on every line-routing diagram; no curved or spline line types."""
    findings = []
    for ln in lines:
        if is_comment(ln):
            continue
        linetype = LINETYPE.match(ln.text)
        if linetype and linetype.group(1).lower() != "ortho":
            findings.append(Finding(ln.number, "ERROR", "curved-lines",
                                    f"`linetype {linetype.group(1)}` draws curves or diagonals: use ortho"))
        splines = SPLINES.search(ln.text)
        if splines and splines.group(1).lower() not in ("ortho", "polyline"):
            findings.append(Finding(ln.number, "ERROR", "curved-lines",
                                    f"`splines={splines.group(1)}` draws curves: use splines=ortho"))
    routes_lines = "@startuml" in code.lower() and not is_gantt and not SEQUENCE.search(code)
    if routes_lines and not re.search(r"skinparam\s+linetype\s+ortho", code, re.I):
        findings.append(Finding(1, "ERROR", "no-ortho",
                                "add `skinparam linetype ortho`: lines are straight with right-angle elbows"))
    return findings


def edge_style(line: str) -> str:
    """The style word a relation is drawn in: a bracket style (`-[dotted]->`), else dashed for a
    dotted arrow (`..>`, `.right.>`), else solid."""
    head = re.sub(r'"[^"]*"', '""', line.split(":", 1)[0])
    named = EDGE_STYLE.search(head)
    if named:
        return "solid" if named.group(1).lower() == "plain" else named.group(1).lower()
    arrow = RELATION.search(head)
    return "dashed" if arrow and "." in arrow.group(1) else "solid"


def icon_edge_findings(body: list[Line], has_legend: bool, legend_text: str = "") -> list[Finding]:
    """C4 relationship rules on AWS-style diagrams: every visible edge has an intent label with
    its protocol in parentheses, `intent (protocol)`; the diagram has a legend (STYLE rule 14).
    An unlabelled edge passes after a junction, or when a legend row names its dashed, dotted or
    bold line style."""
    findings = []
    junctions = {m.group(1) for ln in body if (m := JUNCTION.match(ln.text))}
    legend_styles = {word.lower() for word in LINE_ROW.findall(legend_text)} & LEGEND_EXEMPT_STYLES
    for ln in body:
        if ln.block != "" or is_comment(ln) or "hidden" in ln.text or not RELATION.search(ln.text):
            continue
        if MACRO_CALL.match(ln.text):
            continue
        caption = ln.text.split(":", 1)[1].strip() if ":" in ln.text else ""
        if not caption and ln.text.split()[0] in junctions:  # the line continues from a junction, labelled once
            continue
        if not caption and edge_style(ln.text) in legend_styles:  # the legend row says what the line means
            continue
        if not caption:
            findings.append(Finding(ln.number, "ERROR", "icon-edge-unlabelled",
                                    "every line says what it does: `a --> b : publishes extracts (S3 PUT)`"))
        elif not re.search(r"\([^)]+\)\s*$", caption):
            findings.append(Finding(ln.number, "WARN", "icon-edge-no-protocol",
                                    "end the label with its protocol in parentheses: `(SQL)`, `(HTTPS)`"))
    if not has_legend:
        findings.append(Finding(1, "ERROR", "icon-no-legend", "an icon diagram has a legend: icons, frames, line styles"))
    return findings


MACRO_CALL = re.compile(r"^\s*\w+\s*\(")
JUNCTION = re.compile(r'^\s*circle\s+"\s*"\s+as\s+(\w+)\s*$')  # STYLE rule 15: a junction, no text
LINE_ROW = re.compile(r"^\s*\|\s*(\w+)\s+lines?\s*\|", re.MULTILINE | re.IGNORECASE)  # STYLE rule 15: `| dashed line | ... |`
LEGEND_EXEMPT_STYLES = {"dashed", "dotted", "bold"}  # a solid or plain line keeps its intent label (rule 16)
EDGE_STYLE = re.compile(r"\[[^\]]*\b(dashed|dotted|bold|plain)\b[^\]]*\]", re.IGNORECASE)
DASHED_GROUP_MACRO = re.compile(
    r"^\s*(?:AvailabilityZoneGroup|GenericGroup|GenericAltGroup|RegionGroup|AutoScalingGroupGroup|Grouping)\s*\("
    r"|^\s*AWSGroupColoring\s*\([^)]*,\s*(?:dashed|dotted)\s*\)",
    re.IGNORECASE | re.MULTILINE,
)
STYLED_CLASS = re.compile(r"^\s*\.(\w+)\s*\{[^}]*\bLineStyle\b", re.IGNORECASE | re.MULTILINE)


def frame_style_findings(text: str, body_text: str, legend_text: str) -> list[Finding]:
    """STYLE rule 21: a dashed or dotted frame kind is explained by a legend row."""
    dashed_classes = set(STYLED_CLASS.findall(text))
    uses_class = any(re.search(rf"<<{re.escape(name)}>>", body_text) for name in dashed_classes)
    if not (uses_class or DASHED_GROUP_MACRO.search(body_text)):
        return []
    if re.search(r"(?:dashed|dotted)[^|\n]*frame|frame[^|\n]*(?:dashed|dotted)", legend_text, re.IGNORECASE):
        return []
    return [Finding(1, "WARN", "frame-style-unlegended",
                    "a dashed or dotted frame is used but no legend row says what that border means")]


def lint_text(text: str) -> list[Finding]:
    lines = classify(text)
    findings = fence_findings(lines)
    lower = text.lower()
    code = "\n".join(ln.text for ln in lines if not is_comment(ln))  # comments never satisfy a check
    is_gantt = "@startgantt" in lower
    has_preamble = PREAMBLE_BEGIN in text
    has_style = "<style>" in code.lower()
    has_title, has_legend = directives(lines)
    style_colour_classes = {
        name for name, body in STYLE_CLASS.findall(text) if "color" in body.lower()
    }
    body = [ln for ln in lines if not ln.in_preamble and ln.block in ("", "json")]
    is_c4 = lint_c4.is_c4(code)

    if not has_title:
        findings.append(Finding(1, "ERROR", "no-title", "add a `title` line: no diagram without a title"))

    colour_line = style_colour_line(lines)
    for ln in body:
        if ln.block == "json":
            continue
        uses_class = any(f"<<{name}>>" in ln.text for name in style_colour_classes)
        if COLOUR_TOKEN.search(ln.text) or uses_class or re.match(r"^\s*skinparam\b.*colou?r", ln.text, re.I):
            colour_line = colour_line or ln.number
        inline = COLOUR_TOKEN.search(ln.text) or re.match(r"^\s*skinparam\b.*colou?r", ln.text, re.I)
        library_style = (is_c4 or lint_c4.is_icon_lib(code)) and lint_c4.is_style_macro(ln.text)
        if inline and (has_preamble or has_style) and not library_style:
            findings.append(Finding(
                ln.number, "WARN", "inline-colour",
                "colour set outside the preamble: define it once as a <<stereotype>> in <style>",
            ))
    if colour_line and not has_legend:
        findings.append(Finding(
            colour_line, "ERROR", "colour-no-legend",
            "colour used without a legend: no colour without a legend entry",
        ))

    dashed = [ln for ln in body if ln.block == "" and is_dashed(ln.text)]
    marked = code.lower()
    if dashed and "not stated" not in marked and "inferred" not in marked:
        findings.append(Finding(
            dashed[0].number, "ERROR", "dashed-unmarked",
            'dashed edge without "not stated" or "inferred" in its label or the legend',
        ))

    for ln in lines:
        if ln.in_preamble or ln.block not in ("", "bracket") or is_comment(ln):
            continue
        limit = MAX_BODY if ln.block == "bracket" and not re.search(r"\[\s*$|^\s*\]", ln.text) else MAX_LABEL
        for label in line_labels(ln):
            for segment in label_segments(label):
                if len(segment) > limit:
                    findings.append(Finding(
                        ln.number, "WARN", "long-label",
                        f"label line has {len(segment)} chars (max {limit}); move detail to a note: {segment[:50]}...",
                    ))

    fields = field_lines(lines)
    for ln in fields:
        shown = field_text(ln.text)
        if len(shown) > MAX_BODY:
            findings.append(Finding(
                ln.number, "WARN", "long-field",
                f"field prints {len(shown)} chars (max {MAX_BODY}): it wraps; shorten or move detail out: {shown[:50]}...",
            ))
    findings += creole_findings(lines, fields)

    macro_lines = [(ln.number, ln.text) for ln in lines
                   if not ln.in_preamble and ln.block in ("", "legend") and not is_comment(ln)]
    is_icons = lint_c4.is_icon_lib(code)
    legend_text = "\n".join(ln.text for ln in lines if ln.block == "legend")
    if is_c4:
        findings += [Finding(*found) for found in lint_c4.c4_findings(macro_lines)]
    if is_icons:
        findings += [Finding(*found) for found in lint_c4.icon_findings(macro_lines)]
        findings += icon_edge_findings(body, has_legend, legend_text)
        named = "\n".join(ln.text for ln in lines if not ln.in_preamble and not is_comment(ln)
                          and (ln.block == "legend" or re.match(r"^\s*title\b", ln.text, re.I)))
        findings += [Finding(*found) for found in lint_c4.provider_findings(text, named)]
    findings += line_findings(lines, code, is_gantt)
    if not is_c4:  # C4's SHOW_LEGEND() explains its own boundaries
        body_text = "\n".join(ln.text for ln in lines if not ln.in_preamble and not is_comment(ln))
        findings += frame_style_findings(code, body_text, legend_text)

    transparent = re.search(r"legendBackgroundColor\s+transparent", code, re.I) or re.search(
        r"legend\s*\{[^}]*BackgroundColor\s+transparent", code, re.I
    )
    if has_legend and not transparent:
        findings.append(Finding(
            1, "WARN", "legend-background",
            "set `skinparam legendBackgroundColor transparent` (or legend { BackgroundColor transparent })",
        ))
    return sorted(findings, key=lambda f: (f.line, f.rule))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="House-style lint for PlantUML sources.")
    parser.add_argument("sources", nargs="+", type=Path, help=".puml files")
    args = parser.parse_args(argv)
    errors = warnings = 0
    for src in args.sources:
        for f in lint_text(src.read_text(encoding="utf-8")):
            print(f"{src}:{f.line}: {f.severity} [{f.rule}] {f.message}")
            errors += f.severity == "ERROR"
            warnings += f.severity == "WARN"
    print(f"lint: {errors} error(s), {warnings} warning(s)")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
