"""Edge labels clear of borders (STYLE rule 15): measured on the rendered SVG, stdlib only.

label-on-node: an edge label (its text rows, step badges included) touches or overlaps an
element's outline, a frame's border line or a frame's title. label-on-edge: it touches or
overlaps a line that is not its own. "Touches" means closer than CLEARANCE px: at 1:1 a gap of
one or two pixels reads as sitting on the border. label-on-own-line: its own line runs inside
the ink box of one of its rows (ortho seats a label 0.2-1.0 px beside its line, so only a
crossing counts: Graphviz centres a label at the bend of a down-then-across line).
A link's own line is its unfilled path; a note on the link is drawn with filled paths. A note on
a link is measured as its own rows against nodes and lines like any label; its border is not an
obstacle for other links' labels.
Each row is measured on its own, never one box over the whole link: a row is the text runs on
one baseline that abut (PlantUML splits a badge and its caption at no-break spaces), so a head or
tail label ("1", "many") and each line of a note are rows of their own. The ink box of a row:
width from PlantUML's `textLength` (else characters x size x 0.55), from baseline - 0.75 x size
to baseline + 0.21 x size, the same for every word.
"""
from __future__ import annotations

import re
from dataclasses import dataclass

CLEARANCE = 2.0
CHAR_WIDTH = 0.55
ASCENT = 0.75
DESCENT = 0.21
SAME_BASELINE = 0.5  # px: runs closer than this in y sit on one baseline
ROW_JOIN_MIN_GAP = -1.0  # px: a run that starts further left than this behind a row is not more of it
NO_LINE = float("-inf")  # the depth when there is no line to measure against
GROUP = re.compile(r'<g\b([^>]*\bclass="(entity|cluster|link)"[^>]*)>(.*?)</g>', re.DOTALL)
TEXT = re.compile(r"<text\b([^>]*)>([^<]*)</text>")
ATTR = re.compile(r'([\w:-]+)="([^"]*)"')
NUM = re.compile(r"-?\d+(?:\.\d+)?")
SHAPE = re.compile(r"<(rect|path|polygon|ellipse)\b([^>]*)/?>")
PATH = re.compile(r"<path\b([^>]*)/?>")
PATH_TOKEN = re.compile(r"[A-Za-z]|-?\d+(?:\.\d+)?")


@dataclass(frozen=True)
class Box:
    x0: float
    y0: float
    x1: float
    y1: float

    def grow(self, d: float) -> "Box":
        return Box(self.x0 - d, self.y0 - d, self.x1 + d, self.y1 + d)

    def depth(self, o: "Box") -> float:
        """Overlap depth in px; negative values are the gap between the two boxes."""
        w = min(self.x1, o.x1) - max(self.x0, o.x0)
        h = min(self.y1, o.y1) - max(self.y0, o.y0)
        return min(w, h) if w > 0 and h > 0 else -max(-w, -h)

    def union(self, o: "Box") -> "Box":
        return Box(min(self.x0, o.x0), min(self.y0, o.y0), max(self.x1, o.x1), max(self.y1, o.y1))


@dataclass(frozen=True)
class Row:
    """One line of label text: its runs on one baseline, and their ink box."""
    text: str
    box: Box
    baseline: float
    size: float

    def continued_by(self, run: "Row") -> bool:
        """`run` is more of this row: the same baseline, and it starts where the row ends, no
        further than one character on and (ROW_JOIN_MIN_GAP) not back across the row's end."""
        gap = run.box.x0 - self.box.x1
        return (abs(run.baseline - self.baseline) < SAME_BASELINE
                and ROW_JOIN_MIN_GAP <= gap <= run.size * CHAR_WIDTH)

    def joined(self, run: "Row") -> "Row":
        return Row(self.text + run.text, self.box.union(run.box), self.baseline, max(self.size, run.size))


@dataclass(frozen=True)
class Finding:
    rule: str
    label: str
    target: str
    depth: float
    at: tuple[int, int] = (0, 0)  # the colliding row's top-left corner, to find it with crop.py

    def message(self) -> str:
        where = f'"{self.label}" at ({self.at[0]},{self.at[1]})'
        if self.rule == "label-on-own-line":
            return f"{self.rule}: {where} crossed by its own line by {self.depth:.1f} px"
        if self.depth > 0:
            return f"{self.rule}: {where} overlaps {self.target} by {self.depth:.1f} px"
        return f"{self.rule}: {where} touches {self.target} (gap {-self.depth:.1f} px, needs {CLEARANCE:.0f})"


def attrs(raw: str) -> dict[str, str]:
    return dict(ATTR.findall(raw))


def text_row(raw_attrs: str, content: str) -> Row | None:
    a = attrs(raw_attrs)
    if "x" not in a or "y" not in a:
        return None
    size = float(a.get("font-size", 12))
    width = float(a["textLength"]) if "textLength" in a else len(content) * size * CHAR_WIDTH
    x, y = float(a["x"]), float(a["y"])
    return Row(content, Box(x, y - size * ASCENT, x + width, y + size * DESCENT), y, size)


def label_rows(body: str) -> list[Row]:
    """A link's text rows, in order; no-break-space runs carry width, so they join the row."""
    rows: list[Row] = []
    for raw, content in TEXT.findall(body):
        run = text_row(raw, content) if content else None
        if run is None:
            continue
        if rows and rows[-1].continued_by(run):
            rows[-1] = rows[-1].joined(run)
        else:
            rows.append(run)
    return [Row(" ".join(r.text.split()), r.box, r.baseline, r.size) for r in rows if r.text.split()]


def path_points(d: str) -> list[tuple[float, float]]:
    """Absolute end points of a path, in order (arc radii and flags are not points)."""
    points: list[tuple[float, float]] = []
    cmd, buf = "", []
    for token in PATH_TOKEN.findall(d) + ["Z"]:
        if token.isalpha():
            nums = [float(n) for n in buf]
            if cmd and cmd in "MLCQST":
                points += list(zip(nums[0::2], nums[1::2]))
            elif cmd == "A":
                points += [(nums[i + 5], nums[i + 6]) for i in range(0, len(nums) - 6, 7)]
            elif cmd == "H" and points:
                points += [(n, points[-1][1]) for n in nums]
            elif cmd == "V" and points:
                points += [(points[-1][0], n) for n in nums]
            cmd, buf = token, []
        else:
            buf.append(token)
    return points


def outline(kind: str, raw: str) -> list[tuple[float, float]]:
    """The corner points of an element's outline, closed."""
    a = attrs(raw)
    try:
        if kind == "rect":
            x, y = float(a.get("x", 0)), float(a.get("y", 0))
            w, h = float(a["width"]), float(a["height"])
            return [(x, y), (x + w, y), (x + w, y + h), (x, y + h), (x, y)]
        if kind == "ellipse":
            cx, cy, rx, ry = (float(a[k]) for k in ("cx", "cy", "rx", "ry"))
            return [(cx - rx, cy - ry), (cx + rx, cy - ry), (cx + rx, cy + ry), (cx - rx, cy + ry),
                    (cx - rx, cy - ry)]
        if kind == "path":
            return path_points(a.get("d", ""))
        nums = [float(n) for n in NUM.findall(a.get("points") or "")]
        return list(zip(nums[0::2], nums[1::2]))
    except (KeyError, ValueError):
        return []


def bbox(points: list[tuple[float, float]]) -> Box | None:
    if not points:
        return None
    xs, ys = [p[0] for p in points], [p[1] for p in points]
    return Box(min(xs), min(ys), max(xs), max(ys))


def segments(points: list[tuple[float, float]]) -> list[Box]:
    """Successive points as thin boxes (ortho lines and frame sides are straight runs)."""
    return [Box(min(a[0], b[0]), min(a[1], b[1]), max(a[0], b[0]), max(a[1], b[1]))
            for a, b in zip(points, points[1:]) if a != b]


def line_segments(body: str) -> list[Box]:
    """A link's own line: its unfilled paths (a note on the link fills its body and fold)."""
    paths = [attrs(raw) for raw in PATH.findall(body)]
    return [s for a in paths if a.get("fill", "none") == "none" for s in segments(path_points(a.get("d", "")))]


def line_depth(label: Box, seg: Box) -> float:
    """How far a line runs inside the label box; negative values are its distance outside."""
    if seg.x1 - seg.x0 <= seg.y1 - seg.y0:  # vertical run
        across = min((seg.x0 + seg.x1) / 2 - label.x0, label.x1 - (seg.x0 + seg.x1) / 2)
        along = min(seg.y1, label.y1) - max(seg.y0, label.y0)
    else:
        across = min((seg.y0 + seg.y1) / 2 - label.y0, label.y1 - (seg.y0 + seg.y1) / 2)
        along = min(seg.x1, label.x1) - max(seg.x0, label.x0)
    return min(across, along) if across > 0 and along > 0 else -max(-across, -along)


def lines_depth(label: Box, segs: list[Box]) -> float:
    return max((line_depth(label, s) for s in segs), default=NO_LINE)


def name_of(body: str) -> str:
    words = [t.strip() for _, t in TEXT.findall(body) if t.strip()]
    return " ".join(words)[:40] or "element"


def parse(svg: str) -> tuple[list, list]:
    """Targets (name, box or None, border segments) and links (name, label, rows, line segments)."""
    targets, links = [], []
    for raw, kind, body in GROUP.findall(svg):
        name = name_of(body)
        if kind == "link":
            rows = label_rows(body)
            name = attrs(raw).get("id") or f"link {len(links) + 1}"
            links.append((name, " ".join(r.text for r in rows), rows, line_segments(body)))
            continue
        first = SHAPE.findall(body)[:1]  # the element's own outline (later shapes are icons, tabs)
        points = outline(*first[0]) if first else []
        if kind == "entity" and points:
            targets.append((name, bbox(points), []))
        elif kind == "cluster" and points:
            targets.append((f"border of {name}", None, segments(points)))
            for a, t in TEXT.findall(body):
                if t.strip() and (title := text_row(a, t)):
                    targets.append((f"title of {name}", title.box, []))
    return targets, links


def deepest(scored: list[tuple[float, Row]]) -> tuple[float, tuple[int, int]]:
    """The largest depth over a label's rows, and that row's top-left corner."""
    depth, row = max(scored, key=lambda pair: pair[0])
    return depth, (round(row.box.x0), round(row.box.y0))


def check(svg: str) -> list[Finding]:
    """Every label closer than CLEARANCE px to a node, frame border, frame title or other line,
    and every label its own line runs into. Links are told apart by position, not by id."""
    targets, links = parse(svg)
    found: list[Finding] = []
    for index, (_, label, rows, own) in enumerate(links):
        if not rows:
            continue
        for name, target, sides in targets:
            depth, at = deepest([(r.box.depth(target) if target else lines_depth(r.box, sides), r) for r in rows])
            if depth > -CLEARANCE:
                found.append(Finding("label-on-node", label, name, round(depth, 1), at))
        for other_index, (other_name, other, _, line) in enumerate(links):
            if other_index == index:
                continue
            depth, at = deepest([(lines_depth(r.box, line), r) for r in rows])
            if depth > -CLEARANCE:
                found.append(Finding("label-on-edge", label, f"the line of '{other or other_name}'",
                                     round(depth, 1), at))
        depth, at = deepest([(lines_depth(r.box, own), r) for r in rows])
        if depth > 0:  # the line runs inside a row's ink box
            found.append(Finding("label-on-own-line", label, "its own line", round(depth, 1), at))
    return found
