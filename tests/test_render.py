"""Plain-Python tests for render.py. Run: python tests/test_render.py

Pure checks always run. Real renders run only when PlantUML resolves; otherwise
they print SKIP (never a silent pass).
"""
from __future__ import annotations

import contextlib
import http.server
import os
import struct
import subprocess
import sys
import tempfile
import threading
from collections.abc import Iterator
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SCRIPTS = next(ROOT.glob("*/scripts/render.py")).parent
FIXTURES = ROOT / "tests" / "fixtures"
sys.path.insert(0, str(SCRIPTS))

import render  # noqa: E402

SKIPPED: list[str] = []


def fake_png(width: int, height: int, end: bytes = render.PNG_IEND) -> bytes:
    header = render.PNG_MAGIC + struct.pack(">I", 13) + b"IHDR" + struct.pack(">II", width, height)
    return header + b"\0" * 2000 + end


@contextlib.contextmanager
def env_vars(**values: str) -> Iterator[None]:
    old = {name: os.environ.get(name) for name in values}
    os.environ.update(values)
    try:
        yield
    finally:
        for name, value in old.items():
            if value is None:
                os.environ.pop(name, None)
            else:
                os.environ[name] = value


@contextlib.contextmanager
def witness_server() -> Iterator[tuple[int, list[str]]]:
    """A 127.0.0.1 HTTP server that records every request (proves fetches happen or not)."""
    hits: list[str] = []

    class Handler(http.server.BaseHTTPRequestHandler):
        def do_GET(self) -> None:  # noqa: N802
            hits.append(self.path)
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b'{"k": "FETCHED"}')

        def log_message(self, *args: object) -> None:
            pass

    server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield server.server_address[1], hits
    finally:
        server.shutdown()
        server.server_close()


def plantuml_available() -> bool:
    try:
        render.resolve_command()
        return True
    except render.RenderError:
        return False


def run_cli(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run([sys.executable, str(SCRIPTS / "render.py"), *args], capture_output=True, text=True)


def test_png_size_reads_ihdr() -> None:
    assert render.png_size(fake_png(800, 600)) == (800, 600)


def test_png_magic_is_checked() -> None:
    try:
        render.png_size(b"<svg>not a png</svg>")
    except render.RenderError:
        return
    raise AssertionError("non-PNG bytes accepted")


def test_aspect_bounds() -> None:
    assert render.format_aspect(1000, 600) == ("1.67:1", True)
    assert render.format_aspect(600, 1300)[1] is False
    assert render.format_aspect(2100, 1000)[1] is False


def test_remote_include_is_refused() -> None:
    result = run_cli(str(FIXTURES / "remote.puml"))
    assert result.returncode == 1 and "remote reference refused" in result.stderr, result.stderr


def test_png_without_iend_is_rejected() -> None:  # finding 5
    with tempfile.TemporaryDirectory() as tmp:
        good, padded = Path(tmp) / "good.png", Path(tmp) / "padded.png"
        good.write_bytes(fake_png(800, 600))
        padded.write_bytes(fake_png(800, 600, end=b"\0" * 12))
        assert render.verify_png(good) == (800, 600)
        try:
            render.verify_png(padded)
        except render.RenderError:
            return
    raise AssertionError("PNG without IEND accepted")


def test_parent_absolute_and_url_reads_are_refused() -> None:  # findings 1 and 2 (static part)
    refused = [
        "!include ../outside.iuml",
        "!include C:/shared/outside.iuml",
        "!include /etc/outside.iuml",
        '!$d = %load_json("http://127.0.0.1:9/x.json")',
        '!$d = %loadJSON("https://example.invalid/x.json")',
        'rectangle "<img:../logo.png>" as r',
    ]
    for line in refused:
        try:
            render.check_source(f"@startuml\n{line}\n@enduml\n")
        except render.RenderError:
            continue
        raise AssertionError(f"not refused: {line}")
    assert render.check_source("@startuml\n!include part.iuml\n@enduml\n") is True
    assert render.check_source("@startuml\n!include <C4/C4_Context>\n@enduml\n") is False


def test_command_line_spec_with_jar_is_split() -> None:  # finding 3
    with env_vars(**{render.ENV_VAR: "java -jar /tools/plantuml.jar"}):
        command, _ = render.resolve_command()
    assert command[-2:] == ["-jar", "/tools/plantuml.jar"] and "java" in Path(command[0]).name.lower(), command
    exe = r"C:\My Tools\plantuml.exe" if os.name == "nt" else "/opt/My Tools/plantuml"
    with env_vars(**{render.ENV_VAR: f'"{exe}" -charset UTF-8'}):
        command, _ = render.resolve_command()
    assert command == [exe, "-charset", "UTF-8"], command


def test_relative_renderer_path_is_made_absolute() -> None:  # finding 4
    with tempfile.TemporaryDirectory() as tmp:
        jar = Path(tmp) / "plantuml.jar"
        jar.write_bytes(b"")
        cwd = os.getcwd()
        os.chdir(tmp)
        try:
            with env_vars(**{render.ENV_VAR: "plantuml.jar"}):
                command, _ = render.resolve_command()
        finally:
            os.chdir(cwd)
        assert command[-1] == str(jar.resolve()), command


def test_sibling_include_renders_and_inherited_unsecure_cannot_fetch() -> None:  # findings 1 and 2
    if not plantuml_available():
        SKIPPED.append("test_sibling_include_renders_and_inherited_unsecure_cannot_fetch (plantuml not found)")
        return
    with tempfile.TemporaryDirectory() as tmp, witness_server() as (port, hits):
        folder = Path(tmp)
        (folder / "part.iuml").write_text('rectangle "From sibling" as s\n', encoding="utf-8")
        (folder / "main.puml").write_text(
            "@startuml\n!theme plain\ntitle Include\n!include part.iuml\n@enduml\n", encoding="utf-8")
        (folder / "net.iuml").write_text(
            f'!$d = %load_json("http://127.0.0.1:{port}/x.json")\nrectangle "$d.k" as n\n', encoding="utf-8")
        (folder / "sneaky.puml").write_text("@startuml\ntitle Sneaky\n!include net.iuml\n@enduml\n", encoding="utf-8")
        loose = {"PLANTUML_SECURITY_PROFILE": "UNSECURE", "JAVA_TOOL_OPTIONS": "-DPLANTUML_SECURITY_PROFILE=UNSECURE"}
        with env_vars(**loose):
            ok = run_cli(str(folder / "main.puml"))
            run_cli(str(folder / "sneaky.puml"))
        assert ok.returncode == 0, ok.stderr
        assert "From sibling" in (folder / "main.svg").read_text(encoding="utf-8")
        assert hits == [], f"PlantUML fetched {hits} despite the forced profile"


def test_docs_forbid_hosted_rendering() -> None:  # finding 12
    skill = (SCRIPTS.parent / "SKILL.md").read_text(encoding="utf-8")
    assert "Hosted or web rendering is forbidden in every case" in skill
    assert "silently" not in skill


def test_docs_restore_means_rerender() -> None:  # finding 13
    skill = (SCRIPTS.parent / "SKILL.md").read_text(encoding="utf-8")
    assert "restore the previous source AND re-render it" in " ".join(skill.split())


def skill_step(number: int) -> str:
    skill = (SCRIPTS.parent / "SKILL.md").read_text(encoding="utf-8")
    return " ".join(skill.split(f"### {number}.")[1].split("### ")[0].split())


def test_docs_two_rounds_second_is_structural() -> None:  # phase 1.1 items 1, 2, 6
    assert "Done when: exit 0. An aspect WARN is not a stop: step 5 answers it with a structural round or a split." in skill_step(4)
    step5 = skill_step(5)
    assert "Round 2 is reserved for STRUCTURE" in step5 and "Record every pass" in step5
    for move in ("Layout move A", "Layout move B", "Layout move C", "scripts/crop.py"):
        assert move in step5, move
    assert len((SCRIPTS.parent / "SKILL.md").read_text(encoding="utf-8").splitlines()) <= 200


def test_docs_no_host_document_and_no_reviewer() -> None:  # item 11
    assert "When there is no host document (a bake-off or a scratch folder)" in skill_step(6)
    assert "When no separate reviewer is available" in skill_step(7) and "say so in the report" in skill_step(7)


def test_docs_dashed_edges_need_one_legend_row_not_a_word_each() -> None:  # item 7
    step3 = skill_step(3)
    assert "ONE legend row" in step3 and "only when that edge needs its own reason" in step3
    assert "cat preambles/house.puml templates/skeleton.puml" in step3  # item 12


def test_docs_key_marks_and_failure_pattern() -> None:  # items 8, 10
    reference = " ".join((SCRIPTS.parent / "reference" / "plantuml-features.md").read_text(encoding="utf-8").split())
    style = " ".join((SCRIPTS.parent / "STYLE.md").read_text(encoding="utf-8").split())
    assert "A `*` before a field is NOT a key" in reference and "mandatory (NOT NULL)" in reference
    assert "marks a key" not in reference
    assert "**Failure points are flow elements.**" in style and "Never a red note" in style


def test_docs_legend_row_exemption_and_ink_box() -> None:  # phase 1.8.1 MED-3, LOW-3, MED-4
    style = " ".join((SCRIPTS.parent / "STYLE.md").read_text(encoding="utf-8").split())
    assert "A solid or plain line never does: it still carries its intent label (rule 16)" in style
    assert "a `|=` header row, a first cell that starts with a colour swatch, and `plain` are not read" in style
    assert "crossed by more than 2 px" not in style and "ink box" in style


def test_aspect_warn_points_to_layout_moves_not_direction() -> None:  # item 5
    assert "change direction" not in render.ASPECT_WARN
    assert "layout move" in render.ASPECT_WARN and "split" in render.ASPECT_WARN
    assert render.ASPECT_WARN.isascii()


def test_merged_fan_in_endpoints_are_found() -> None:  # phase 1.2, STYLE rule 15
    merged = (FIXTURES / "fanin_merged.svg").read_text(encoding="utf-8")
    separated = (FIXTURES / "fanin_separated.svg").read_text(encoding="utf-8")
    assert render.merged_endpoints(render.link_endpoints(merged)) == [(3, (67.99, 156.467))]
    assert len(render.link_endpoints(separated)) == 3
    assert render.merged_endpoints(render.link_endpoints(separated)) == []


def test_labels_on_nodes_borders_and_lines_are_found() -> None:  # phase 1.6, STYLE rule 15
    found = render.labels.check((FIXTURES / "labels_overlap.svg").read_text(encoding="utf-8"))
    on_node = {(f.label, f.target) for f in found if f.rule == "label-on-node"}
    assert ("invokes (Lambda proxy)", "Web shop API [Amazon API Gateway]") in on_node
    assert ("3 publishes (SQS)", "Order events [Amazon SQS]") in on_node
    assert ("writes slip (S3 PUT)", "Fulfilment [AWS Lambda]") in on_node
    assert ("5 reads slips (HTTPS)", "border of AWS Cloud") in on_node
    assert len(found) == 5 and all(f.depth > 0 for f in found)
    message = found[0].message()
    assert message.startswith('label-on-node: "') and " overlaps " in message and message.endswith(" px")
    assert '" at (' in message  # the label's top-left corner, for crop.py


def test_a_label_closer_than_the_clearance_touches_the_border() -> None:  # phase 1.6 calibration
    found = render.labels.check((FIXTURES / "labels_touch.svg").read_text(encoding="utf-8"))
    assert [(f.label, f.target) for f in found] == [("serves", "border of Application layer"),
                                                     ("stores", "border of Technology layer")]
    # phase 1.8.1: the ink box reaches the descent for every word, so the 1.4 px gap under the
    # baseline of "serves" / "stores" is now 1.1 px inside the box
    assert [f.depth for f in found] == [1.1, 1.1], found
    assert "overlaps border of Application layer by 1.1 px" in found[0].message()
    edge = ('<g class="link" id="a"><path d="M0,0 L0,100"/>'
            '<text x="10" y="50" font-size="12" textLength="30">near</text></g>')
    frame = '<g class="cluster" id="f"><rect x="41.5" y="0" width="100" height="100"/></g>'
    touching = render.labels.check(edge + frame)
    assert [(f.rule, f.depth) for f in touching] == [("label-on-node", -1.5)], touching
    assert "touches border of element (gap 1.5 px, needs 2)" in touching[0].message()


def test_clear_labels_and_a_label_beside_its_own_line_pass() -> None:  # phase 1.6 calibration
    assert render.labels.check((FIXTURES / "labels_clean.svg").read_text(encoding="utf-8")) == []
    edge = '<g class="link" id="a"><path d="M10,0 L10,100"/><text x="14" y="50" font-size="12" textLength="30">own</text></g>'
    other = '<g class="link" id="b"><path d="M30,0 L30,100"/></g>'
    assert render.labels.check(edge) == []
    assert [f.rule for f in render.labels.check(edge + other)] == ["label-on-edge"]


def test_a_label_crossed_by_its_own_line_is_found() -> None:  # phase 1.8, STYLE rule 15
    # Graphviz centres an ortho label on the bend of a down-then-right line (azure "uploads daily CSV")
    bend = ('<g class="link" id="a"><path d="M100,0 L100,50 L200,50"/>'
            '<text x="40" y="54" font-size="12" textLength="70">uploads (HTTPS)</text></g>')
    found = render.labels.check(bend)
    assert [(f.rule, f.label, f.depth) for f in found] == [("label-on-own-line", "uploads (HTTPS)", 5.0)], found
    assert found[0].message() == 'label-on-own-line: "uploads (HTTPS)" at (40,45) crossed by its own line by 5.0 px'


def test_a_label_beside_its_own_line_is_not_crossed_but_one_inside_is() -> None:  # phase 1.8.1 MED-4
    # ortho seats every label 0.2-1.0 px beside its own line; a line inside the ink box is a crossing
    def own(x: str) -> list:
        return render.labels.check(f'<g class="link" id="a"><path d="M10,0 L10,100"/>'
                                   f'<text x="{x}" y="50" font-size="12" textLength="30">own</text></g>')
    assert own("10.5") == [] and own("10") == [], (own("10.5"), own("10"))  # 0.5 px gap; on the edge
    assert [(f.rule, f.depth) for f in own("8.5")] == [("label-on-own-line", 1.5)], own("8.5")


def test_own_line_depth_uses_one_ink_box_for_every_word() -> None:  # phase 1.8.1 MED-4
    # reviewer probe: a horizontal own line under the text; `reads` has no descender, `receipts` has
    def crossing(text: str, above_baseline: float) -> list:
        y = 100 - above_baseline
        return [(f.rule, f.depth) for f in render.labels.check(
            f'<g class="link" id="h"><path d="M0,{y} L200,{y}"/>'
            f'<text x="50" y="100" font-size="12" textLength="40">{text}</text></g>')]
    assert crossing("reads", 1.9) == [("label-on-own-line", 4.4)], crossing("reads", 1.9)
    assert crossing("receipts", 0.2) == [("label-on-own-line", 2.7)], crossing("receipts", 0.2)
    assert crossing("reads", 0.2) == crossing("receipts", 0.2), "the same rule for every word"


def test_note_on_link_and_head_tail_labels_are_not_crossed_by_their_line() -> None:  # phase 1.8.1 HIGH-1
    # real renders, clean at 1:1: a note's border is not the link's line; "1", "many" and the
    # caption are separate rows on either side of the line, never one box across it
    for name in ("labels_note_on_link.svg", "labels_head_tail.svg"):
        found = render.labels.check((FIXTURES / name).read_text(encoding="utf-8"))
        assert found == [], (name, [f.message() for f in found])


def test_a_run_left_of_a_row_does_not_join_it() -> None:  # phase 1.8.2 re-review R1
    # a caption right of the line and a head label "1" left of it share a baseline; the link's own
    # line runs between them, so joining them into one box would put the line inside it
    caption = '<text x="104" y="50" font-size="12" textLength="40">caption</text>'
    head = '<text x="88" y="50" font-size="12" textLength="6">1</text>'
    for runs in (caption + head, head + caption):
        found = render.labels.check(f'<g class="link" id="a"><path d="M100,0 L100,100"/>{runs}</g>')
        assert found == [], [f.message() for f in found]
    joined = render.labels.label_rows(
        '<text x="10" y="50" font-size="12" textLength="6">3</text>'
        '<text x="17" y="50" font-size="12" textLength="50"> publishes</text>')
    assert [r.text for r in joined] == ["3 publishes"], joined  # a no-break-space run still joins


def test_a_real_render_crossed_by_its_own_line_still_fires() -> None:  # phase 1.8.1 HIGH-1
    # causal-chain as shipped in 1.8: "not stated" sits on the bend of its own down-then-left line
    found = render.labels.check((FIXTURES / "labels_own_line.svg").read_text(encoding="utf-8"))
    assert [(f.rule, f.label, f.depth) for f in found] == [("label-on-own-line", "not stated", 11.5)], found


def test_links_are_told_apart_without_unique_ids() -> None:  # phase 1.8.1 LOW-2
    def link(lid: str | None, d: str, text: str = "") -> str:
        ida = f' id="{lid}"' if lid is not None else ""
        label = f'<text x="14" y="50" font-size="12" textLength="30">{text}</text>' if text else ""
        return f'<g class="link"{ida}><path d="{d}"/>{label}</g>'
    for lid, named in ((None, "link 2"), ("x", "x")):  # missing ids, then a duplicate id
        found = render.labels.check(link(lid, "M10,0 L10,100", "own") + link(lid, "M30,0 L30,100"))
        assert [(f.rule, f.label) for f in found] == [("label-on-edge", "own")], (lid, found)
        assert f"the line of '{named}'" in found[0].message(), found[0].message()


def test_c4_and_aws_preambles_render_with_the_stdlib_under_sandbox() -> None:  # phase 1.2 items 2, 13
    if not plantuml_available():
        SKIPPED.append("test_c4_and_aws_preambles_render_with_the_stdlib_under_sandbox (plantuml not found)")
        return
    skill = SCRIPTS.parent
    sources = {
        "c4": (skill / "preambles" / "house-c4.puml").read_text(encoding="utf-8")
        + (skill / "templates" / "skeleton-c4.puml").read_text(encoding="utf-8"),
        "aws": (skill / "preambles" / "house-aws.puml").read_text(encoding="utf-8")
        + (skill / "templates" / "skeleton-aws.puml").read_text(encoding="utf-8"),
        "aws_smoke": (FIXTURES / "aws_smoke.puml").read_text(encoding="utf-8"),
    }
    with tempfile.TemporaryDirectory() as tmp:
        for name, text in sources.items():
            src = Path(tmp) / f"{name}.puml"
            src.write_text(text, encoding="utf-8")
            result = run_cli(str(src))
            assert result.returncode == 0, (name, result.stderr)
            assert "merged endpoints:" in result.stdout and "label-on-node:" in result.stdout, result.stdout
        smoke = (Path(tmp) / "aws_smoke.svg").read_text(encoding="utf-8")
        assert "cannot include" not in smoke.lower() and "Formation" in smoke, "an icon include failed"


def test_azure_and_gcp_preambles_and_smoke_files_render() -> None:  # phase 1.4 provider rule
    if not plantuml_available():
        SKIPPED.append("test_azure_and_gcp_preambles_and_smoke_files_render (plantuml not found)")
        return
    skill = SCRIPTS.parent
    sources = {f"{p}_start": (skill / "preambles" / f"house-{p}.puml").read_text(encoding="utf-8")
               + (skill / "templates" / f"skeleton-{p}.puml").read_text(encoding="utf-8") for p in ("azure", "gcp")}
    sources.update({name: (FIXTURES / f"{name}.puml").read_text(encoding="utf-8") for name in ("azure_smoke", "gcp_smoke")})
    sources["negative"] = "@startuml\n!include <azure/AzureCommon>\n!include <azure/General/AzureNoSuchThing>\ntitle t\n@enduml\n"
    with tempfile.TemporaryDirectory() as tmp:
        for name, text in sources.items():
            src = Path(tmp) / f"{name}.puml"
            src.write_text(text, encoding="utf-8")
            result = run_cli(str(src))
            if name == "negative":
                assert result.returncode == 1, "a missing stdlib include must fail the render"
            else:
                assert result.returncode == 0, (name, result.stderr)


def test_new_preambles_and_skeletons_render() -> None:  # phase 1.5
    if not plantuml_available():
        SKIPPED.append("test_new_preambles_and_skeletons_render (plantuml not found)")
        return
    skill = SCRIPTS.parent
    house = (skill / "preambles" / "house.puml").read_text(encoding="utf-8")
    sources = {n: house + (skill / "templates" / f"skeleton-{n}.puml").read_text(encoding="utf-8")
               for n in ("dfd", "swimlane", "state")}
    sources.update({n: (skill / "templates" / f"skeleton-{n}.puml").read_text(encoding="utf-8")
                    for n in ("wbs", "cause-tree", "mindmap")})
    for example in ("subnet-map", "archimate-layers", "aws-steps"):
        sources[example] = (skill / "examples" / example / f"{example}.puml").read_text(encoding="utf-8")
    with tempfile.TemporaryDirectory() as tmp:
        for name, text in sources.items():
            src = Path(tmp) / f"{name}.puml"
            src.write_text(text, encoding="utf-8")
            result = run_cli(str(src))
            assert result.returncode == 0, (name, result.stderr)


def test_docs_phase15_rows_and_rules() -> None:  # phase 1.5
    skill = " ".join((SCRIPTS.parent / "SKILL.md").read_text(encoding="utf-8").split())
    step1 = skill.split("### 1.")[1].split("### 2.")[0]
    for needle in ("skeleton-dfd.puml", "skeleton-swimlane.puml", "skeleton-state.puml", "skeleton-cause-tree.puml",
                   "house-nwdiag.puml", "house-archimate.puml"):
        assert needle in step1, needle
    assert "check the row anchoring by eye" in skill.split("### 5.")[1]
    style = " ".join((SCRIPTS.parent / "STYLE.md").read_text(encoding="utf-8").split())
    for needle in ("Numbered steps are optional; intent labels are not.", "Frame kind by border style.",
                   "applies to LINES only", "a dead-letter queue is a `queue` filled `<<failure>>`"):
        assert needle in style, needle
    reference = (SCRIPTS.parent / "reference" / "plantuml-features.md").read_text(encoding="utf-8")
    assert "Never map a timeline to `@startchronology`" in reference and "| gcp |" in reference
    notice = (SCRIPTS.parent / "NOTICE.md").read_text(encoding="utf-8")
    assert "jgraph/drawio-diagrams" in notice and "No template XML, shape, icon or image copied." in notice


def test_docs_provider_rule_frames_and_checklist() -> None:  # phase 1.4
    style = " ".join((SCRIPTS.parent / "STYLE.md").read_text(encoding="utf-8").split())
    assert "The icon library follows the provider the SOURCES name" in style
    assert "never AWS icons or AWS frames for a non-AWS platform" in style
    assert "the outer `AWSCloudGroup` is a stated fact" in style
    reference = (SCRIPTS.parent / "reference" / "plantuml-features.md").read_text(encoding="utf-8")
    section = reference.split("## Cloud platform map: acceptance checklist")[1].split("\n## ")[0]
    assert all(f"\n{n}. " in section for n in range(1, 11)), "ten checklist rows"
    assert "**AWS**" in section and "**Azure**" in section and "**Google Cloud**" in section
    skill = " ".join((SCRIPTS.parent / "SKILL.md").read_text(encoding="utf-8").split())
    assert "Cloud platform map: acceptance checklist" in skill and "house-azure.puml" in skill and "house-gcp.puml" in skill


def test_docs_aws_style_is_the_infra_default_and_no_noodle_lines_lead() -> None:  # phase 1.3
    skill = " ".join((SCRIPTS.parent / "SKILL.md").read_text(encoding="utf-8").split())
    step1 = skill.split("### 1.")[1].split("### 2.")[0]
    assert "the DEFAULT for infra maps" in step1 and "the provider's architecture style" in step1
    assert "when the reader asks for C4 or the map names no cloud services" in step1
    aws_row = step1.index("the DEFAULT for infra maps")
    assert aws_row < step1.index("C4 Container"), "the AWS row comes before the C4 rows"
    step5 = skill.split("### 5.")[1].split("### 6.")[0]
    assert step5.split("|---|---|")[1].strip().startswith("| Curved, diagonal or tangled lines (noodles)")
    assert "html-plan page" in skill.split("### 6.")[1] and "NEVER pack html-plan with `--artifact`" in skill
    style = (SCRIPTS.parent / "STYLE.md").read_text(encoding="utf-8")
    assert style.index("## No noodle lines") < style.index("## Rules")
    rubric = " ".join((SCRIPTS.parent / "RUBRIC.md").read_text(encoding="utf-8").split())
    assert "Curved, diagonal or tangled lines score at most 2" in rubric


def wrapped_preamble(body: str) -> str:
    preamble = (SCRIPTS.parent / "preambles" / "house.puml").read_text(encoding="utf-8")
    return preamble + body + "@enduml\n"


def test_preamble_renders_sequence_and_layout_moves() -> None:  # items 2, 8 (hide circle is safe in sequences)
    if not plantuml_available():
        SKIPPED.append("test_preamble_renders_sequence_and_layout_moves (plantuml not found)")
        return
    import test_lint  # the same snippet extraction the lint test uses
    sources = {"sequence": wrapped_preamble('title Seq\nparticipant "A" as a\nparticipant "B" as b\na -> b : ask\nb --> a : reply\n')}
    for number, snippet in enumerate(test_lint.layout_move_snippets()):
        sources[f"move{number}"] = test_lint.wrap_snippet(snippet)
    with tempfile.TemporaryDirectory() as tmp:
        for name, text in sources.items():
            src = Path(tmp) / f"{name}.puml"
            src.write_text(text, encoding="utf-8")
            result = run_cli(str(src))
            assert result.returncode == 0, (name, result.stderr)
        assert "reply" in (Path(tmp) / "sequence.svg").read_text(encoding="utf-8")


def test_docs_state_the_sequence_exception_in_step_3() -> None:  # finding 14
    skill = (SCRIPTS.parent / "SKILL.md").read_text(encoding="utf-8")
    step3 = skill.split("### 3.")[1].split("### 4.")[0]
    assert "Sequence diagrams are the" in step3 and "`note` that says `not stated`" in step3


def test_readme_install_creates_the_skill_folder() -> None:  # finding 15
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    assert "mkdir -p ~/.claude/skills/plantsmith && cp -r plantsmith/. ~/.claude/skills/plantsmith/" in readme
    assert "New-Item -ItemType Directory -Force" in readme


def test_env_jar_runs_through_java_headless() -> None:
    old = os.environ.get(render.ENV_VAR)
    os.environ[render.ENV_VAR] = "/opt/tools/plantuml.jar"
    try:
        command, location = render.resolve_command()
    finally:
        if old is None:
            del os.environ[render.ENV_VAR]
        else:
            os.environ[render.ENV_VAR] = old
    assert command[-2:] == ["-jar", "/opt/tools/plantuml.jar"] and render.HEADLESS in command, command
    assert render.ENV_VAR in location


def test_help_states_local_only() -> None:
    result = run_cli("--help")
    assert "NEVER contacts the network" in result.stdout


def test_real_render_writes_verified_png() -> None:
    if not plantuml_available():
        SKIPPED.append("test_real_render_writes_verified_png (plantuml not found)")
        return
    with tempfile.TemporaryDirectory() as out:
        result = run_cli(str(FIXTURES / "clean.puml"), "--out-dir", out)
        assert result.returncode == 0, result.stderr
        assert "renderer: PlantUML version" in result.stdout and "aspect" in result.stdout, result.stdout
        assert "label-on-node: 0, label-on-edge: 0, label-on-own-line: 0" in result.stdout, result.stdout
        assert "WARN" not in result.stdout, result.stdout
        assert (Path(out) / "clean.png").read_bytes().startswith(render.PNG_MAGIC)


def test_warn_lines_survive_a_console_without_utf8() -> None:  # phase 1.8.1 HIGH-2
    if not plantuml_available():
        SKIPPED.append("test_warn_lines_survive_a_console_without_utf8 (plantuml not found)")
        return
    with tempfile.TemporaryDirectory() as out:
        result = subprocess.run([sys.executable, str(SCRIPTS / "render.py"), str(FIXTURES / "label_on_frame.puml"),
                                 "--out-dir", out], capture_output=True, env={**os.environ, "PYTHONIOENCODING": "cp874"})
    stdout = result.stdout.decode("utf-8", "replace")
    assert result.returncode == 0, result.stderr.decode("utf-8", "replace")
    assert "WARN label-on-node:" in stdout and "«group1»" in stdout, stdout


def test_syntax_error_exits_1_with_plantuml_stderr() -> None:
    if not plantuml_available():
        SKIPPED.append("test_syntax_error_exits_1_with_plantuml_stderr (plantuml not found)")
        return
    with tempfile.TemporaryDirectory() as out:
        result = run_cli(str(FIXTURES / "bad.puml"), "--out-dir", out)
    assert result.returncode == 1 and "plantuml exited" in result.stderr, result.stderr


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
    for skip in SKIPPED:
        print(f"SKIP {skip}")
    print(f"{len(tests) - failed - len(SKIPPED)}/{len(tests)} passed, {len(SKIPPED)} skipped")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
