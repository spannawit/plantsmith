"""Plain-Python tests for exhibit.py. Run: python tests/test_exhibit.py"""
from __future__ import annotations

import re
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SCRIPTS = next(ROOT.glob("*/scripts/exhibit.py")).parent
EXAMPLE = SCRIPTS.parent / "examples" / "pipeline-dag" / "pipeline-dag.svg"
sys.path.insert(0, str(SCRIPTS))

import exhibit  # noqa: E402

SVG = EXAMPLE.read_text(encoding="utf-8")


def test_fragment_shape_prolog_and_size() -> None:
    fragment, _ = exhibit.exhibit('<?xml version="1.0"?>\n' + SVG, interactive_layer=False)
    assert fragment.startswith('<doc-mock frame="none" w="480" thumbnail><template>\n<svg'), fragment[:80]
    assert fragment.rstrip().endswith("</template></doc-mock>")
    assert "<?xml" not in fragment and "<?plantuml" not in fragment
    opening = re.search(r"<svg\b[^>]*>", fragment).group(0)
    assert 'viewBox="0 0 578 1077"' in opening
    assert not re.search(r'\s(?:width|height)="', opening) and "preserveAspectRatio" not in opening


def test_data_refs_are_present_unique_and_named_from_text() -> None:
    fragment, refs = exhibit.exhibit(SVG, interactive_layer=False)
    assert len(refs) > 0 and len(refs) == len(set(refs)), refs
    assert "till-csv-export" in refs and "link-row-counts-match-to-alert-shop-manager" in refs, refs
    assert fragment.count('data-ref="') == len(refs)
    assert all(len(ref) <= exhibit.SLUG_MAX for ref in refs if not ref.startswith("link-"))


def test_width_cap_and_thumbnail() -> None:
    small = SVG.replace('viewBox="0 0 578 1077"', 'viewBox="0 0 400 300"')
    fragment, _ = exhibit.exhibit(small, interactive_layer=False)
    assert fragment.startswith('<doc-mock frame="none" w="400"><template>'), fragment[:60]
    wide, _ = exhibit.exhibit(SVG, max_w=300, frame="browser")
    assert wide.startswith('<doc-mock frame="browser" w="300" thumbnail>')


def test_remote_refs_and_images_are_refused() -> None:
    bad = [
        SVG.replace("<defs/>", '<defs/><image href="logo.png" width="10" height="10"/>'),
        SVG.replace("<defs/>", '<defs/><a href="https://example.invalid/x"><text>x</text></a>'),
        SVG.replace("<defs/>", '<defs/><style>g { fill: url("//cdn.example.invalid/p.svg") }</style>'),
    ]
    for svg in bad:
        try:
            exhibit.exhibit(svg)
        except exhibit.ExhibitError:
            continue
        raise AssertionError("not refused: " + svg[:0])


def test_interactive_layer_style_dim_rules_tooltips_and_script() -> None:  # phase 2
    fragment, refs = exhibit.exhibit(SVG)
    style = re.search(r"<style>(.*?)</style>", fragment, re.S).group(1)
    sid = re.search(r'<svg id="(ps-[0-9a-f]{8})"', fragment).group(1)
    assert all(line.startswith((f"#{sid}", ".ps-bar")) for line in style.strip().splitlines()), "every rule scoped"
    assert f"#{sid}:hover g[data-ref]{{opacity:0.35}}" in style, "everything dims to 35 %"
    nodes = [r for r in refs if not r.startswith("link-")]
    per_node = re.findall(r'g\[data-ref="([^"]+)"\]:hover ~ g\[data-from=', style)
    assert sorted(per_node) == sorted(nodes), (len(per_node), len(nodes))
    assert ":has(" not in style
    assert fragment.count("<title>") == len(refs), "one tooltip per element, group and line"
    links = re.findall(r'<g data-ref="link-[^"]+" data-from="([^"]+)" data-to="([^"]+)"', fragment)
    assert links and all(a in nodes and b in nodes for a, b in links)
    script = fragment.split("<script>")[1].split("</script>")[0]
    assert script.count("\n") <= 150 and "fetch(" not in script and "http" not in script
    assert 'data-act="legend"' in fragment and "WHEEL_NEEDS_MODIFIER = true" in script
    assert "background:#fff" in re.search(r"<svg\b[^>]*>", fragment).group(0)


def test_icon_diagrams_with_inline_data_images_are_accepted() -> None:  # phase 2: awslib/C4 icons
    icon_svg = SVG.replace("<defs/>", '<defs/><image href="data:image/png;base64,iVBORw0KGgo=" width="4" height="4"/>')
    fragment, _ = exhibit.exhibit(icon_svg)
    assert "data:image/png;base64" in fragment


def test_cli_writes_fragment_and_lists_refs() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        out = Path(tmp) / "x.exhibit.html"
        result = subprocess.run([sys.executable, str(SCRIPTS / "exhibit.py"), str(EXAMPLE), "--out", str(out)],
                                capture_output=True, text=True)
        assert result.returncode == 0, result.stderr
        assert "data-ref (" in result.stdout and out.read_text(encoding="utf-8").startswith("<doc-mock")


def main() -> int:
    tests = [(name, fn) for name, fn in globals().items() if name.startswith("test_") and callable(fn)]
    failed = 0
    for name, fn in tests:
        try:
            fn()
            print(f"PASS {name}")
        except AssertionError as exc:
            failed += 1
            print(f"FAIL {name}: {exc}")
    print(f"{len(tests) - failed}/{len(tests)} passed")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
