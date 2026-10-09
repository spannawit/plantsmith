"""Plain-Python tests for publish.py. Run: python tests/test_publish.py"""
from __future__ import annotations

import re
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SCRIPTS = next(ROOT.glob("*/scripts/publish.py")).parent
EXAMPLES = SCRIPTS.parent / "examples"
sys.path.insert(0, str(SCRIPTS))

import exhibit  # noqa: E402
import publish  # noqa: E402

SVG = (EXAMPLES / "pipeline-dag" / "pipeline-dag.svg").read_text(encoding="utf-8")
NAMESPACES = re.compile(r'xmlns(?::\w+)?="http://www\.w3\.org/[^"]*"')


def test_page_is_self_contained() -> None:
    page = publish.publish(SVG)
    assert page.startswith("<!doctype html>") and page.rstrip().endswith("</html>")
    assert "http" not in NAMESPACES.sub("", page), "no URL outside the SVG namespace declarations"
    for pattern in (r"<script\b[^>]*\bsrc=", r"<link\b", r"@import", r"@font-face", r"\burl\(\s*['\"]?https?:"):
        assert not re.search(pattern, page, re.I), pattern


def test_page_has_title_theme_legend_and_png_export() -> None:
    page = publish.publish(SVG)
    assert "<title>Nightly sales report pipeline (DAG)</title>" in page, "the diagram's own title"
    assert "prefers-color-scheme: dark" in page and 'id="ps-theme"' in page
    assert 'id="ps-png"' in page and "toBlob" in page and 'data-act="legend"' in page
    assert "WHEEL_NEEDS_MODIFIER = false" in page and ":hover" in page
    assert publish.publish(SVG, title="EMI platform").count("<title>EMI platform</title>") == 1


def test_remote_refs_are_refused() -> None:
    for bad in ('<defs/><image href="logo.png" width="1" height="1"/>', '<defs/><a href="https://x.invalid"/>'):
        try:
            publish.publish(SVG.replace("<defs/>", bad))
        except exhibit.ExhibitError:
            continue
        raise AssertionError("not refused: " + bad)


def test_cli_writes_page_beside_the_svg() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        src = Path(tmp) / "d.svg"
        src.write_text(SVG, encoding="utf-8")
        result = subprocess.run([sys.executable, str(SCRIPTS / "publish.py"), str(src)], capture_output=True, text=True)
        assert result.returncode == 0, result.stderr
        assert (Path(tmp) / "d.page.html").read_text(encoding="utf-8").startswith("<!doctype html>")


def test_docs_step6_names_the_three_targets() -> None:  # phase 2
    skill = " ".join((SCRIPTS.parent / "SKILL.md").read_text(encoding="utf-8").split())
    step6 = skill.split("### 6.")[1].split("### 7.")[0]
    assert "scripts/exhibit.py" in step6 and "Interactive by default" in step6
    assert "scripts/publish.py" in step6 and "PNG/JPEG/WebP only" in step6
    reference = (SCRIPTS.parent / "reference" / "plantuml-features.md").read_text(encoding="utf-8")
    assert "## Standalone page" in reference and "What the html-plan runtime does with the exhibit" in reference


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
