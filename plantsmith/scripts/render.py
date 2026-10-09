#!/usr/bin/env python3
"""Render a PlantUML diagram to SVG and PNG with the local PlantUML, then verify the PNG.

Stdlib only. Runs the PlantUML installed on this machine; never uploads the source.
"""
from __future__ import annotations

import argparse
import os
import re
import shlex
import shutil
import struct
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

import labels

SKILL_NAME = "plantsmith"
ENV_VAR = f"{SKILL_NAME.upper()}_PLANTUML"

PNG_MAGIC = b"\x89PNG\r\n\x1a\n"
MIN_PNG_BYTES = 1024
MIN_PNG_SIDE_PX = 16
ASPECT_MIN = 0.5  # 1:2 (W:H)
ASPECT_MAX = 2.0  # 2:1 (W:H)
PLANTUML_LIMIT_SIZE = "8192"
RENDER_TIMEOUT_S = 180
HEADLESS = "-Djava.awt.headless=true"
MERGE_PX = 3.0  # arrow ends closer than this share one point on the target's border
ASPECT_WARN = "WARN outside 1:2-2:1: split, or apply a layout move (reference/plantuml-features.md, Layout moves)"

SOURCE_EXTS = {".puml", ".plantuml", ".pu", ".iuml"}
WINDOWS_NATIVE_EXTS = {".exe", ".bat", ".cmd", ".com"}

PNG_IEND = b"\x00\x00\x00\x00IEND\xaeB`\x82"

# Directives that read a file or a URL; the target is whichever group matched.
REF_TARGET = re.compile(
    r"^\s*!(?:include\w*|import)\s+(\S+)"
    r"|^\s*!theme\s+\S+\s+from\s+(\S+)"
    r"|%load_?json\s*\(\s*\"([^\"]+)\""
    r"|<img:\s*([^>{\s]+)",
    re.IGNORECASE | re.MULTILINE,
)
URL_SCHEME = re.compile(r"^[a-z][a-z0-9+.-]*://", re.IGNORECASE)
ABSOLUTE = re.compile(r"^(?:[\\/]|[a-z]:)", re.IGNORECASE)
PARENT = re.compile(r"(?:^|[\\/])\.\.(?:[\\/]|$)")
SECURITY_PROPS = re.compile(r"-D(?:plantuml[._]security|plantuml[._]allowlist)\S*", re.IGNORECASE)

HELP_EPILOG = f"""\
Local only: this script NEVER contacts the network. It runs the PlantUML
installed on this machine and refuses sources that reference a URL, an absolute
path or a `..` path (!include, !import, !theme ... from, %load_json, <img:...>).
PlantUML always runs in its SANDBOX security profile, or in ALLOWLIST confined to
the diagram's folder when the source reads local files; inherited profile
settings are overridden.

PlantUML lookup (first hit wins):
  1. env {ENV_VAR}: a command, an executable path, or a plantuml.jar path
     (a jar runs as `java {HEADLESS} -jar <jar>`)
  2. `plantuml` on PATH (shell-script wrappers run through bash on Windows)
PlantUML itself needs Graphviz for most non-sequence layouts; set GRAPHVIZ_DOT
if it cannot find `dot`.

Exit codes: 0 rendered and verified (WARN lines do not fail), 1 failure.
"""


class RenderError(Exception):
    """A failure the user must see; the message is printed as-is."""


@dataclass(frozen=True)
class Renderer:
    command: tuple[str, ...]
    location: str
    version: str


# ---------------------------------------------------------------- lookup


def find_on_path(name: str) -> str | None:
    """shutil.which, plus extensionless wrapper scripts on Windows."""
    hit = shutil.which(name)
    if hit:
        return hit
    if os.name != "nt":
        return None
    for folder in os.environ.get("PATH", "").split(os.pathsep):
        candidate = Path(folder.strip('"')) / name
        if candidate.is_file():
            return str(candidate)
    return None


def _is_script(path: str) -> bool:
    try:
        with open(path, "rb") as handle:
            return handle.read(2) == b"#!"
    except OSError:
        return False


def _find_bash() -> str | None:
    bash = shutil.which("bash")
    if bash and "system32" not in bash.lower():  # skip the WSL launcher
        return bash
    for root in (os.environ.get("ProgramFiles", ""), os.environ.get("ProgramW6432", "")):
        candidate = Path(root) / "Git" / "bin" / "bash.exe"
        if root and candidate.is_file():
            return str(candidate)
    return None


def command_for_path(path: str) -> list[str]:
    """Turn a jar or executable path into an argv prefix that runs on this OS."""
    if Path(path).is_file():  # absolute, because PlantUML runs with cwd = the diagram's folder
        path = str(Path(path).resolve())
    if path.lower().endswith(".jar"):
        java = find_on_path("java") or "java"
        return [java, HEADLESS, "-jar", path]
    if os.name == "nt" and Path(path).suffix.lower() not in WINDOWS_NATIVE_EXTS and _is_script(path):
        bash = _find_bash()
        if not bash:
            raise RenderError(f"{path} is a shell script and no bash was found to run it")
        return [bash, path]
    return [path]


def command_for_spec(spec: str) -> list[str]:
    """An env-var value: a jar, an executable path, or a command line."""
    bare = spec.strip().strip('"')
    if Path(bare).is_file():
        return command_for_path(bare)
    parts = [p.strip('"') for p in shlex.split(spec.strip(), posix=(os.name != "nt"))]
    if not parts:
        raise RenderError("empty PlantUML command")
    resolved = find_on_path(parts[0]) or parts[0]
    args = [str(Path(p).resolve()) if Path(p).is_file() else p for p in parts[1:]]
    return command_for_path(resolved) + args


def resolve_command() -> tuple[list[str], str]:
    spec = os.environ.get(ENV_VAR, "").strip()
    if spec:
        return command_for_spec(spec), f"{spec} (from ${ENV_VAR})"
    path = find_on_path("plantuml")
    if not path:
        raise RenderError(
            f"plantuml not found: put `plantuml` on PATH or set {ENV_VAR} "
            "(a command, an executable path, or a plantuml.jar path)"
        )
    return command_for_path(path), path


def headless_env(base: dict[str, str]) -> dict[str, str]:
    """Wrappers cannot take JVM flags, so pass headless mode through the JVM's own variable."""
    env = dict(base)
    opts = SECURITY_PROPS.sub("", env.get("JAVA_TOOL_OPTIONS", "")).strip()  # never inherit a looser profile
    if HEADLESS not in opts:
        env["JAVA_TOOL_OPTIONS"] = f"{opts} {HEADLESS}".strip()
    return env


def clean_stderr(raw: bytes) -> str:
    lines = raw.decode("utf-8", "replace").splitlines()
    return "\n".join(line for line in lines if not line.startswith("Picked up JAVA_TOOL_OPTIONS")).strip()


def _run(argv: list[str], **kwargs) -> subprocess.CompletedProcess:
    try:
        return subprocess.run(argv, capture_output=True, timeout=RENDER_TIMEOUT_S, **kwargs)
    except OSError as exc:
        raise RenderError(f"cannot run {' '.join(argv)}: {exc}") from exc
    except subprocess.TimeoutExpired as exc:
        raise RenderError(f"PlantUML timed out after {RENDER_TIMEOUT_S}s") from exc


def resolve_renderer(env: dict[str, str]) -> Renderer:
    command, location = resolve_command()
    proc = _run(command + ["-version"], env=env)
    text = (proc.stdout.decode("utf-8", "replace") + "\n" + clean_stderr(proc.stderr)).strip()
    version = text.splitlines()[0] if text else "version unknown"
    return Renderer(tuple(command), location, version)


# ---------------------------------------------------------------- checks


def png_size(data: bytes) -> tuple[int, int]:
    """Width and height from the PNG IHDR chunk; RenderError if not a PNG."""
    if not data.startswith(PNG_MAGIC):
        raise RenderError("output is not a PNG (magic bytes missing)")
    if len(data) < 24 or data[12:16] != b"IHDR":
        raise RenderError("PNG has no IHDR header")
    width, height = struct.unpack(">II", data[16:24])
    return width, height


def verify_png(path: Path) -> tuple[int, int]:
    if not path.is_file():
        raise RenderError(f"{path} was not written")
    data = path.read_bytes()
    width, height = png_size(data)
    if not data.endswith(PNG_IEND):
        raise RenderError(f"{path} is truncated or padded (no IEND chunk at the end)")
    if len(data) < MIN_PNG_BYTES or min(width, height) < MIN_PNG_SIDE_PX:
        raise RenderError(f"{path} is trivially small ({len(data)} bytes, {width}x{height} px)")
    return width, height


def verify_svg(path: Path) -> None:
    if not path.is_file() or path.stat().st_size == 0:
        raise RenderError(f"{path} was not written")
    if "<svg" not in path.read_bytes()[:4096].decode("utf-8", "replace"):
        raise RenderError(f"{path} does not look like SVG")


def format_aspect(width: int, height: int) -> tuple[str, bool]:
    """Return ('1.27:1' style text, within 1:2-2:1)."""
    ratio = width / height
    text = f"{ratio:.2f}:1" if ratio >= 1 else f"1:{1 / ratio:.2f}"
    return text, ASPECT_MIN <= ratio <= ASPECT_MAX


def check_source(text: str) -> bool:
    """Refuse URL, absolute and `..` references; True when the source reads local files."""
    if re.search(r"^\s*!includeurl\b", text, re.IGNORECASE | re.MULTILINE):
        raise RenderError("remote reference refused (local-only renderer): !includeurl")
    reads_files = False
    for match in REF_TARGET.finditer(text):
        target = next(group for group in match.groups() if group)
        if target.startswith("<"):  # PlantUML's bundled stdlib, e.g. <C4/C4_Context>
            continue
        line = text[: match.start()].count("\n") + 1
        if URL_SCHEME.match(target):
            raise RenderError(f"line {line}: remote reference refused (local-only renderer): {target}")
        if ABSOLUTE.match(target) or PARENT.search(target):
            raise RenderError(f"line {line}: only files inside the diagram's folder may be read: {target}")
        reads_files = True
    return reads_files


LINK_GROUP = re.compile(r'<g\b[^>]*class="(?:link|edge)"[^>]*>(.*?)</g>', re.DOTALL)
POLYGON_POINTS = re.compile(r'<polygon\b[^>]*\bpoints="([^"]+)"')
PATH_DATA = re.compile(r'<path\b[^>]*\bd="([^"]+)"')
NUMBER = re.compile(r"-?\d+(?:\.\d+)?")


def link_endpoints(svg: str) -> list[tuple[float, float]]:
    """Where each link ends: the tip of its arrowhead (first polygon point), else its path's last point."""
    points = []
    for body in LINK_GROUP.findall(svg):
        polygon = POLYGON_POINTS.search(body)
        source = polygon.group(1) if polygon else (PATH_DATA.search(body) or [None, ""])[1]
        numbers = [float(n) for n in NUMBER.findall(source or "")]
        if len(numbers) >= 2:
            points.append((numbers[0], numbers[1]) if polygon else (numbers[-2], numbers[-1]))
    return points


def merged_endpoints(points: list[tuple[float, float]], tolerance: float = MERGE_PX) -> list[tuple[int, tuple[float, float]]]:
    """Clusters of two or more link ends within `tolerance` px of each other: (count, first point)."""
    clusters: list[list[tuple[float, float]]] = []
    for point in points:
        for cluster in clusters:
            if abs(cluster[0][0] - point[0]) <= tolerance and abs(cluster[0][1] - point[1]) <= tolerance:
                cluster.append(point)
                break
        else:
            clusters.append([point])
    return [(len(cluster), cluster[0]) for cluster in clusters if len(cluster) >= 2]


# ---------------------------------------------------------------- render


def render(src: Path, out_dir: Path) -> int:
    if src.suffix.lower() not in SOURCE_EXTS:
        raise RenderError(f"unsupported file type {src.suffix!r}: use .puml")
    if not src.is_file():
        raise RenderError(f"{src} not found")
    text = src.read_text(encoding="utf-8")
    reads_files = check_source(text)

    env = headless_env(dict(os.environ))
    env.setdefault("PLANTUML_LIMIT_SIZE", PLANTUML_LIMIT_SIZE)
    # Forced, never inherited: SANDBOX reads no files at all; ALLOWLIST reads only this folder.
    env["PLANTUML_SECURITY_PROFILE"] = "ALLOWLIST" if reads_files else "SANDBOX"
    env["PLANTUML_ALLOWLIST_PATH"] = str(src.parent)
    env.pop("PLANTUML_ALLOWLIST_URL", None)
    renderer = resolve_renderer(env)

    out_dir.mkdir(parents=True, exist_ok=True)
    outputs = {fmt: out_dir / f"{src.stem}.{fmt}" for fmt in ("svg", "png")}
    for fmt, out in outputs.items():
        argv = list(renderer.command) + [f"-t{fmt}", "-pipe", "-charset", "UTF-8"]
        proc = _run(argv, input=text.encode("utf-8"), cwd=str(src.parent), env=env)
        if proc.returncode != 0:  # PlantUML still writes an error image here
            raise RenderError(f"plantuml exited {proc.returncode} rendering {fmt}:\n{clean_stderr(proc.stderr)}")
        out.write_bytes(proc.stdout)

    verify_svg(outputs["svg"])
    width, height = verify_png(outputs["png"])
    aspect, aspect_ok = format_aspect(width, height)
    print(f"renderer: {renderer.version} | {renderer.location} | local, no network")
    print(f"wrote: {outputs['svg']}")
    print(f"wrote: {outputs['png']} (PNG ok, {outputs['png'].stat().st_size} bytes)")
    status = "OK" if aspect_ok else ASPECT_WARN
    svg = outputs["svg"].read_text(encoding="utf-8", errors="replace")
    merged = merged_endpoints(link_endpoints(svg))
    found = labels.check(svg)
    counts = {rule: sum(1 for f in found if f.rule == rule)
              for rule in ("label-on-node", "label-on-edge", "label-on-own-line")}
    print(f"size: {width}x{height} px, aspect {aspect} (W:H) {status}, merged endpoints: {len(merged)}, "
          + ", ".join(f"{rule}: {n}" for rule, n in counts.items()))
    for count, (x, y) in merged:
        print(f"WARN merged-endpoints: {count} arrows share a point within {MERGE_PX:g} px at ({x:.0f},{y:.0f})")
    for finding in found:
        print(f"WARN {finding.message()}")
    return 0


def main(argv: list[str] | None = None) -> int:
    if hasattr(sys.stdout, "reconfigure"):  # WARN lines carry SVG text; a cp874 console cannot encode «»
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    parser = argparse.ArgumentParser(
        description="Render a PlantUML diagram to SVG + PNG with the local PlantUML, then verify the PNG.",
        epilog=HELP_EPILOG,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("source", type=Path, help="diagram source (.puml, .plantuml, .pu)")
    parser.add_argument("--out-dir", type=Path, help="where to write .svg/.png (default: beside the source)")
    args = parser.parse_args(argv)
    src = args.source.resolve()
    try:
        return render(src, (args.out_dir or src.parent).resolve())
    except RenderError as exc:
        print(f"FAILED: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
