"""Plain-Python tests for lint.py. Run: python tests/test_lint.py"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SCRIPTS = next(ROOT.glob("*/scripts/lint.py")).parent
FIXTURES = ROOT / "tests" / "fixtures"
sys.path.insert(0, str(SCRIPTS))

import lint  # noqa: E402


def rules(name: str) -> set[tuple[str, str]]:
    text = (FIXTURES / name).read_text(encoding="utf-8")
    return {(f.severity, f.rule) for f in lint.lint_text(text)}


def test_clean_fixture_has_no_findings() -> None:
    assert rules("clean.puml") == set(), rules("clean.puml")


def test_missing_title_is_an_error() -> None:
    assert ("ERROR", "no-title") in rules("no_title.puml")


def test_colour_without_legend_is_an_error() -> None:
    assert ("ERROR", "colour-no-legend") in rules("colour_no_legend.puml")


def test_dashed_edge_without_marker_is_an_error() -> None:
    assert ("ERROR", "dashed-unmarked") in rules("dashed_unmarked.puml")


def test_long_element_label_warns_but_long_note_does_not() -> None:
    findings = lint.lint_text((FIXTURES / "long_label.puml").read_text(encoding="utf-8"))
    long_lines = [f.line for f in findings if f.rule == "long-label"]
    assert long_lines == [4], long_lines


def test_skinparam_colour_outside_preamble_warns() -> None:
    assert ("WARN", "inline-colour") in rules("inline_colour.puml")


def test_missing_ortho_and_opaque_legend_warn() -> None:
    found = rules("no_ortho_legend.puml")
    assert ("ERROR", "no-ortho") in found and ("WARN", "legend-background") in found, found


def test_sequence_reply_arrow_is_not_dashed() -> None:
    assert not lint.is_dashed("A --> B : reply")
    assert lint.is_dashed("A ..> B : inferred")
    assert lint.is_dashed("A -[#999999,dashed]-> B")
    assert not lint.is_dashed("...")


def test_shipped_preambles_do_not_mask_title_or_legend() -> None:
    preamble = (SCRIPTS.parent / "preambles" / "house.puml").read_text(encoding="utf-8")
    preamble += (SCRIPTS.parent / "templates" / "skeleton.puml").read_text(encoding="utf-8")
    no_title = "\n".join(ln for ln in preamble.splitlines() if not ln.startswith("title "))
    assert ("ERROR", "no-title") in {(f.severity, f.rule) for f in lint.lint_text(no_title)}
    gantt = (SCRIPTS.parent / "preambles" / "house-gantt.puml").read_text(encoding="utf-8")
    gantt += (SCRIPTS.parent / "templates" / "skeleton-gantt.puml").read_text(encoding="utf-8")
    no_legend = gantt.split("legend right")[0] + "[Bar] starts 2026-01-05 and ends 2026-01-09\n[Bar] is colored in #FADBD8\n@endgantt\n"
    assert ("ERROR", "colour-no-legend") in {(f.severity, f.rule) for f in lint.lint_text(no_legend)}


def found(text: str) -> set[tuple[str, str]]:
    return {(f.severity, f.rule) for f in lint.lint_text(text)}


PREAMBLE = (SCRIPTS.parent / "preambles" / "house.puml").read_text(encoding="utf-8")
SKELETON = (SCRIPTS.parent / "templates" / "skeleton.puml").read_text(encoding="utf-8")
HOUSE = PREAMBLE + SKELETON  # what SKILL.md step 3 starts a diagram from


def test_preamble_comments_do_not_mark_a_dashed_edge() -> None:  # finding 6
    without_legend = HOUSE.split("legend right")[0] + 'rectangle "A" as a\nrectangle "B" as b\na ..> b\n@enduml\n'
    assert ("ERROR", "dashed-unmarked") in found(without_legend)


def test_direction_hinted_arrow_is_dashed_and_plain_dotted_link_is_not() -> None:  # finding 7
    assert lint.is_dashed("line .right.> book : inferred: isbn")
    assert lint.is_dashed("a .> b")
    assert lint.is_dashed("b <.. a")
    assert not lint.is_dashed("line_rows .. line")
    assert not lint.is_dashed("dim_seller .[#6B7280]. dim_product")  # styled plain link: no arrowhead
    assert not lint.is_dashed('a --> b : "x..y"')


def test_broken_preamble_fence_is_an_error() -> None:  # finding 8
    no_end = HOUSE.replace("' house-preamble-end", "")
    assert ("ERROR", "preamble-fence") in found(no_end)
    assert ("ERROR", "preamble-fence") not in found(HOUSE)


def test_title_inside_body_or_note_and_commented_settings_do_not_count() -> None:  # finding 9
    text = (
        "@startuml\n' skinparam linetype ortho\n"
        'entity "book" as b {\n  title : varchar\n}\n'
        "note right of b\n  title of the book\nend note\n@enduml\n"
    )
    result = found(text)
    assert ("ERROR", "no-title") in result and ("ERROR", "no-ortho") in result, result


def test_general_style_selector_colour_needs_a_legend() -> None:  # finding 10
    text = (
        "@startuml\nskinparam linetype ortho\ntitle T\n<style>\n"
        "rectangle {\n  BackgroundColor #FF0000\n}\n</style>\nrectangle \"A\" as a\n@enduml\n"
    )
    assert ("ERROR", "colour-no-legend") in found(text)


def test_bracket_labels_are_length_checked() -> None:  # finding 11
    long = "A description line that is far longer than forty characters"
    one_line = f"@startuml\nskinparam linetype ortho\ntitle T\ncomponent C [{long}]\n@enduml\n"
    multi = f"@startuml\nskinparam linetype ortho\ntitle T\ncomponent C [\n  {long}\n  short line\n]\n@enduml\n"
    for text in (one_line, multi):
        warnings = [f for f in lint.lint_text(text) if f.rule == "long-label"]
        assert len(warnings) == 1, (text, warnings)


def test_legend_row_alone_marks_dashed_edges() -> None:  # phase 1.1 item 7
    assert ("ERROR", "dashed-unmarked") not in rules("dashed_legend_only.puml")
    assert ("ERROR", "dashed-unmarked") in rules("dashed_unmarked.puml")


def test_creole_pair_in_label_warns_but_escaped_or_note_does_not() -> None:  # item 3
    head = "@startuml\nskinparam linetype ortho\ntitle T\n"
    bad = [
        'rectangle "DAG extract__lazada" as d\n',
        'rectangle "A" as a\nrectangle "B" as b\na --> b : run__id\n',
        'entity "t" as t {\n  extract__lazada : varchar\n}\n',
        'entity "t" as t {\n  **bold** : int\n}\n',
    ]
    for body in bad:
        assert ("WARN", "creole-in-label") in found(head + body + "@enduml\n"), body
    good = [
        'rectangle "DAG extract~__lazada~__sales" as d\n',
        'rectangle "DAG extract~_~_lazada" as d\n',
        'rectangle "A" as a\nnote right of a\n  **bold** and nonff__x\nend note\n',
        'rectangle "x" as extract__alias\n',
        'entity "t" as t {\n  id : int\n  __\n  //italic detail//\n}\n',
    ]
    for body in good:
        assert ("WARN", "creole-in-label") not in found(head + body + "@enduml\n"), body


def test_long_entity_field_warns_but_one_that_fits_does_not() -> None:  # item 4
    head = '@startuml\nskinparam linetype ortho\ntitle T\nentity "t" as t {\n'
    fits = "  {field} parent_category_perm_key : VARCHAR(32) <<FK>>\n"  # prints 44 chars, one line
    wraps = "  {field} abcdefghij_abcdefghij_abcdefgh : VARCHAR(32) <<own key>>\n"  # prints 54, wrapped
    assert ("WARN", "long-field") not in found(head + fits + "}\n@enduml\n")
    assert ("WARN", "long-field") in found(head + wraps + "}\n@enduml\n")
    assert lint.field_text("{field} perm_key : VARCHAR(32) <<own key>>") == "perm_key : VARCHAR(32) «own key»"
    table = 'object "rows" as r {\n  | a very long records table row that is wider than forty-eight chars |\n}\n'
    assert ("WARN", "long-field") not in found("@startuml\nskinparam linetype ortho\ntitle T\n" + table + "@enduml\n")


def fenced(text: str) -> str:
    return text.split("' house-preamble-begin")[1].split("' house-preamble-end")[0]


def test_preamble_plus_skeleton_is_clean_and_examples_embed_the_preamble() -> None:  # items 9, 12
    assert found(HOUSE) == set(), found(HOUSE)
    assert "house-preamble" not in SKELETON and "\ntitle " in SKELETON
    assert PREAMBLE.rstrip().endswith("' house-preamble-end")
    assert '!$LEGEND_FRAME = "#999999"' in fenced(PREAMBLE).split("!theme")[0], "knob sits at the top"
    gantt = (SCRIPTS.parent / "preambles" / "house-gantt.puml").read_text(encoding="utf-8")
    for example in sorted((SCRIPTS.parent / "examples").glob("*/*.puml")):
        text = example.read_text(encoding="utf-8")
        want = fenced(preamble_for(text))
        assert fenced(text) == want, f"{example.name} embeds a stale preamble"
        assert found(text) == set(), (example.name, found(text))


def layout_move_snippets() -> list[str]:
    reference = (SCRIPTS.parent / "reference" / "plantuml-features.md").read_text(encoding="utf-8")
    section = reference.split("## Layout moves")[1].split("\n## ")[0]
    return [block.split("```")[0] for block in section.split("```plantuml\n")[1:]]


def preamble_for(text: str) -> str:
    """The shipped preamble a diagram starts from, picked by its includes."""
    for marker, path in (("@startwbs", "templates/skeleton-wbs.puml"), ("@startmindmap", "templates/skeleton-mindmap.puml"),
                         ("@startnwdiag", "preambles/house-nwdiag.puml"), ("<archimate", "preambles/house-archimate.puml")):
        if marker in text:
            return (SCRIPTS.parent / path).read_text(encoding="utf-8")
    name = ("house-gantt.puml" if "@startgantt" in text else "house-c4.puml" if "<C4/" in text
            else "house-azure.puml" if "<azure" in text else "house-gcp.puml" if "<gcp" in text
            else "house-aws.puml" if "<awslib" in text or "Group(" in text else "house.puml")
    return (SCRIPTS.parent / "preambles" / name).read_text(encoding="utf-8")


def wrap_snippet(snippet: str) -> str:
    if "Rel_" in snippet or "Container(" in snippet:  # a C4 move: C4 preamble, C4 title and key
        return preamble_for("<C4/") + "\ntitle Container diagram for a layout move\n" + snippet + "SHOW_LEGEND()\n@enduml\n"
    legend = "legend right\n  |<#E3F2FD>| stage |\n  | dashed line | inferred / not stated |\nendlegend\n"
    title = "\ntitle Layout move on AWS\n" if "<awslib" in snippet else "\ntitle Layout move\n"
    return preamble_for(snippet) + title + snippet + legend + "@enduml\n"


def test_layout_move_snippets_lint_clean() -> None:  # item 2
    snippets = layout_move_snippets()
    assert len(snippets) == 10, len(snippets)  # before + after for moves A-C and G; one each for D, E
    for snippet in snippets:
        assert [f for f in lint.lint_text(wrap_snippet(snippet)) if f.severity == "ERROR"] == [], snippet


def test_title_and_note_lines_with_hyphens_are_not_relations() -> None:  # phase 1.2 item 9
    for title in ("title Seller Center (non-fulfillment) pipeline: four hourly stages, marketplace APIs to Redshift",
                  "title ORD-4457 OrderKey: dimension tables touched, own keys and foreign keys (MR !289 / !485)"):
        text = f"@startuml\nskinparam linetype ortho\n{title}\nrectangle \"A\" as a\n@enduml\n"
        assert ("WARN", "long-label") not in found(text), title
    assert lint.labels_on("note right of a : step-by-step: a long note text that is far over forty chars") == []


def test_body_lines_share_the_48_char_limit_with_fields() -> None:  # item 9
    head = "@startuml\nskinparam linetype ortho\ntitle T\nrectangle r [\n  Step\n  ....\n"
    fits = "  //image 497 (Amaze 506, Lazada 523), 5 workers//\n"  # 44 chars printed
    wraps = "  //a body line that is clearly longer than forty-eight chars//\n"
    assert ("WARN", "long-label") not in found(head + fits + "]\n@enduml\n")
    assert ("WARN", "long-label") in found(head + wraps + "]\n@enduml\n")


C4_HOUSE = (SCRIPTS.parent / "preambles" / "house-c4.puml").read_text(encoding="utf-8")
C4_SKELETON = (SCRIPTS.parent / "templates" / "skeleton-c4.puml").read_text(encoding="utf-8")


def c4(body: str, title: str = "title Container diagram for Order Sync", legend: str = "SHOW_LEGEND()") -> set:
    return found(f"{C4_HOUSE}\n{title}\n{body}\n{legend}\n@enduml\n")


def test_c4_preamble_plus_skeleton_is_clean() -> None:  # phase 1.2 items 2, 4
    assert found(C4_HOUSE + C4_SKELETON) == set(), found(C4_HOUSE + C4_SKELETON)
    assert "skinparam linetype ortho" in fenced(C4_HOUSE) and "!include <C4/C4_Container>" in C4_HOUSE
    assert fenced(C4_HOUSE).split("!theme")[0].strip().endswith('!$LEGEND_FRAME = "#999999"')


def test_c4_element_completeness() -> None:  # item 4
    assert ("ERROR", "c4-element-incomplete") in c4('Container(a, "Extractor", "", "Pulls orders")')
    assert ("ERROR", "c4-element-incomplete") in c4('ContainerDb(d, "Warehouse", "Redshift")')
    assert ("WARN", "c4-element-incomplete") in c4('System_Ext(s, "Marketplace API")')
    assert not any(r.startswith("c4-element") for _, r in c4(
        'Container(a, "Extractor", "Python, Airflow", "Pulls orders hourly")\n'
        'Person(p, "Analyst", "Reads reports")'))


def test_c4_relationship_rules() -> None:  # item 4
    els = ('Container(a, "Extractor", "Python", "Pulls orders")\n'
           'ContainerDb(d, "Warehouse", "Redshift", "Stores orders")\nSystem_Ext(s, "API", "Order source")\n')
    assert ("ERROR", "c4-rel-unlabelled") in c4(els + "Rel(a, d)")
    assert ("ERROR", "c4-rel-unlabelled") in c4(els + 'Rel_D(a, d, "")')
    assert ("ERROR", "c4-birel") in c4(els + 'BiRel(a, d, "Syncs", "JDBC")')
    assert ("WARN", "c4-weak-label") in c4(els + 'Rel(a, s, "Uses", "HTTPS")')
    assert ("WARN", "c4-rel-no-tech") in c4(els + 'Rel(a, d, "Writes order facts to")')
    assert ("WARN", "c4-rel-no-tech") not in c4(els + 'Rel(a, s, "Pulls new orders from")')  # external end
    clean = c4(els + 'Rel_D(a, d, "Writes order facts to", "COPY")\nRel(a, s, "Pulls new orders from", "HTTPS")')
    assert not any(r.startswith("c4-") for _, r in clean), clean


def test_c4_title_level_legend_and_tags() -> None:  # item 4
    el = 'Container(a, "Extractor", "Python", "Pulls orders")'
    assert ("WARN", "c4-title-format") in c4(el, title="title Order Sync overview")
    assert ("ERROR", "c4-mixed-level") in c4(el, title="title System context diagram for Order Sync")
    assert ("ERROR", "c4-mixed-level") in c4('Component(c, "Parser", "Python", "Parses JSON")')
    assert ("ERROR", "c4-mixed-level") not in c4(el)
    assert ("ERROR", "c4-no-legend") in c4(el, legend="LAYOUT_WITH_LEGEND()")
    assert ("ERROR", "c4-no-legend") not in c4(el, legend="SHOW_FLOATING_LEGEND()")
    assert ("WARN", "c4-tag-no-legendtext") in c4('AddElementTag("legacy", $bgColor="#EEEEEE")\n' + el)
    dashed = 'AddRelTag("async", $lineStyle=DashedLine(), $legendText="asynchronous")\n'
    assert ("ERROR", "c4-dashed-unmarked") in c4(dashed + el)
    marked = 'AddRelTag("guess", $lineStyle=DottedLine(), $legendText="not stated in the source")\n'
    assert ("ERROR", "c4-dashed-unmarked") not in c4(marked + el)


def test_c4_style_macros_are_not_inline_colour_and_no_ortho_is_exempt() -> None:  # item 4
    result = c4('UpdateElementStyle("container", $bgColor="#E3F2FD", $legendText="container")\n'
                'Container(a, "Extractor", "Python", "Pulls orders")')
    assert ("WARN", "inline-colour") not in result and ("ERROR", "no-ortho") not in result, result
    assert ("WARN", "inline-colour") in found(HOUSE.replace("@enduml", 'rectangle "x" as x #FF0000\n@enduml'))


def test_one_word_relationship_label_is_weak() -> None:  # item 4 (STYLE rule 12)
    els = 'Container(a, "A", "Python", "Does a")\nContainerDb(d, "D", "Redshift", "Stores d")\n'
    assert ("WARN", "c4-weak-label") in c4(els + 'Rel(a, d, "Fingerprints", "SQL")')
    assert ("WARN", "c4-weak-label") not in c4(els + 'Rel(a, d, "Fingerprints the reference side of", "SQL")')


AWS_HOUSE = (SCRIPTS.parent / "preambles" / "house-aws.puml").read_text(encoding="utf-8")
AWS_SKELETON = (SCRIPTS.parent / "templates" / "skeleton-aws.puml").read_text(encoding="utf-8")


def test_aws_icon_rules() -> None:  # phase 1.2 items 13, 16
    assert found(AWS_HOUSE + AWS_SKELETON) == set(), found(AWS_HOUSE + AWS_SKELETON)
    assert "skinparam linetype ortho" in fenced(AWS_HOUSE) and "hide stereotype" in fenced(AWS_HOUSE)
    head = AWS_HOUSE + "!include <awslib20/Database/RDS>\ntitle T\n"
    assert ("ERROR", "icon-empty-tech") in found(head + 'RDS(db, "Primary", "")\n@enduml\n')
    assert ("ERROR", "icon-empty-tech") in found(head + 'RDS(db, "Primary")\n@enduml\n')
    assert ("ERROR", "icon-group-unlabelled") in found(head + 'VPCGroup(vpc, "") {\n}\n@enduml\n')
    clean = found(head + 'AWSCloudGroup(c, "AWS Cloud") {\n VPCGroup(vpc, "VPC") {\n  RDS(db, "Primary", "PostgreSQL")\n }\n}\n'
                  + "legend right\n| icon | AWS service |\nendlegend\n@enduml\n")
    assert not any(rule.startswith("icon-") for _, rule in clean), clean
    edges = head + 'RDS(a, "A", "PostgreSQL")\nRDS(b, "B", "PostgreSQL")\n'
    legend = "legend right\n| icon | AWS service |\nendlegend\n@enduml\n"
    assert ("ERROR", "icon-edge-unlabelled") in found(edges + "a --> b\n" + legend)
    assert ("WARN", "icon-edge-no-protocol") in found(edges + "a --> b : replicates\n" + legend)
    assert ("ERROR", "icon-no-legend") in found(edges + "a --> b : replicates (SQL)\n@enduml\n")
    labelled = found(edges + "a --> b : replicates (SQL)\na -[hidden]right- b\n" + legend)
    assert not any(rule.startswith("icon-") and rule != "icon-no-cloud-frame" for _, rule in labelled), labelled
    junction = found(edges + 'circle " " as j\na --> j : replicates (SQL)\nj --> b\n' + legend)  # phase 1.7
    assert ("ERROR", "icon-edge-unlabelled") not in junction, junction
    assert ("ERROR", "icon-edge-unlabelled") in found(edges + 'circle "J" as j\na --> j : replicates (SQL)\nj --> b\n' + legend)
    no_ortho = "@startuml\n!include <awslib20/AWSCommon>\ntitle T\n@enduml\n"
    assert ("ERROR", "no-ortho") in found(no_ortho), "icon diagrams keep ortho on"


def test_legend_line_style_row_exempts_an_unlabelled_edge() -> None:  # phase 1.8, STYLE rule 15
    edges = AWS_HOUSE + '!include <awslib20/Database/RDS>\ntitle T\nRDS(a, "A", "PostgreSQL")\nRDS(b, "B", "PostgreSQL")\n'

    def unlabelled(edge: str, row: str, where: str = "legend") -> bool:
        key = "legend right\n| icon | AWS service |\n" + (row if where == "legend" else "") + "endlegend\n"
        note = f"note as n\n{row}end note\n" if where == "note" else ""
        return ("ERROR", "icon-edge-unlabelled") in found(edges + edge + "\n" + note + key + "@enduml\n")

    told = "| dashed line | not stated in the source: how A replicates to B |\n"
    assert not unlabelled("a .right.> b", told), "the legend row carries the dashed line's meaning"
    assert not unlabelled("a -[dotted]-> b", "| dotted line | not stated |\n")
    assert not unlabelled("a -[bold]-> b", "| bold line | the order path |\n"), "the arrow's own style word"
    # phase 1.8.1 MED-3: a plain line still carries its intent label (STYLE rule 16)
    assert unlabelled("a --> b", "| solid line | stated in the source |\n"), "a solid row never exempts"
    assert unlabelled("a -[plain]-> b", "| plain line | stated |\n"), "a plain row never exempts"
    assert unlabelled("a -[thickness=3]-> b", "| solid line | stated |\n")
    assert unlabelled("a .right.> b", "| dashed frame | Availability Zone |\n"), "a frame row is not a line row"
    assert unlabelled("a --> b", told), "a dashed-line row does not explain a solid line"
    assert unlabelled("a .right.> b", "| dotted line | not stated |\n"), "`..>` draws dashed, not dotted"
    assert unlabelled("a .right.> b", told, where="note"), "only the legend explains a line style"
    assert unlabelled("a .right.> b", "| icon | dashed line |\n"), "the style is named in the first cell"


def test_legend_rows_are_read_in_any_legend_position_and_case() -> None:  # phase 1.8.1 MED-1, MED-2
    edges = AWS_HOUSE + '!include <awslib20/Database/RDS>\ntitle T\nRDS(a, "A", "PostgreSQL")\nRDS(b, "B", "PostgreSQL")\n'
    told = "| dashed line | not stated |\n"

    def unlabelled(opener: str, row: str = told, closer: str = "endlegend") -> bool:
        legend = f"{opener}\n| icon | AWS service |\n{row}{closer}\n"
        return ("ERROR", "icon-edge-unlabelled") in found(edges + "a .right.> b\n" + legend + "@enduml\n")

    for opener in ("legend top left", "legend bottom right", "Legend right", "LEGEND"):
        assert not unlabelled(opener), opener
    assert not unlabelled("Legend right", closer="EndLegend")
    assert not unlabelled("legend right", "| Dashed Line | not stated |\n"), "the row's words in any case"
    assert not unlabelled("legend right", "| DASHED LINES | not stated |\n")


def test_position_word_opens_a_block_only_after_legend() -> None:  # phase 1.8.2 re-review R2
    # a one-line `title Top` is a whole title, not the start of a block: the checks after it must run
    edges = AWS_HOUSE + '!include <awslib20/Database/RDS>\nRDS(a, "A", "PostgreSQL")\nRDS(b, "B", "PostgreSQL")\n'
    tail = "a --> b\nlegend right\n| icon | AWS service |\nendlegend\n@enduml\n"
    for word in ("title", "header", "footer", "caption"):
        title = "" if word == "title" else "title T\n"
        text = edges + title + f"{word} Top\n" + tail
        assert ("ERROR", "icon-edge-unlabelled") in found(text), word
        assert ("ERROR", "no-title") not in found(text), word
    opened = [ln.block for ln in lint.classify("legend top left\n| a |\nendlegend\ntitle Top\nrectangle X\n")]
    assert opened == ["legend", "legend", "legend", "", ""], opened  # legend keeps its position words


def test_no_noodle_lines() -> None:  # phase 1.3: ortho everywhere, curved line types are errors
    for name in ("house.puml", "house-c4.puml", "house-aws.puml", "house-azure.puml", "house-gcp.puml"):
        preamble = (SCRIPTS.parent / "preambles" / name).read_text(encoding="utf-8")
        assert "skinparam linetype ortho" in fenced(preamble), name
        stripped = preamble.replace("skinparam linetype ortho\n", "")
        assert ("ERROR", "no-ortho") in found(stripped + "title T\n@enduml\n"), name
    for line in ("skinparam linetype polyline", "skinparam linetype spline"):
        assert ("ERROR", "curved-lines") in found(HOUSE.replace("@enduml", line + "\n@enduml")), line
    dot = "@startdot\ndigraph G {\nsplines=true;\na -> b;\n}\n@enddot\n"
    assert ("ERROR", "curved-lines") in found(dot)
    assert ("ERROR", "curved-lines") not in found(dot.replace("splines=true", "splines=ortho"))
    sequence = '@startuml\ntitle T\nparticipant "A" as a\nparticipant "B" as b\na -> b : ask\n@enduml\n'
    assert ("ERROR", "no-ortho") not in found(sequence), "sequence diagrams are exempt"


def test_icon_provider_must_match_the_named_provider() -> None:  # phase 1.4 provider rule
    for provider in ("azure", "gcp"):
        preamble = (SCRIPTS.parent / "preambles" / f"house-{provider}.puml").read_text(encoding="utf-8")
        skeleton = (SCRIPTS.parent / "templates" / f"skeleton-{provider}.puml").read_text(encoding="utf-8")
        assert found(preamble + skeleton) == set(), (provider, found(preamble + skeleton))
    aws_titled_azure = AWS_HOUSE + "!include <azure/AzureCommon>\n" + AWS_SKELETON
    assert ("ERROR", "icon-provider-mismatch") in found(aws_titled_azure)
    gcp_on_aws_title = AWS_HOUSE + "!include <gcp/GCPCommon>\n" + AWS_SKELETON
    assert ("ERROR", "icon-provider-mismatch") in found(gcp_on_aws_title)
    named = gcp_on_aws_title.replace("| icon | the AWS service", "| icon | Google Cloud or AWS service")
    assert ("ERROR", "icon-provider-mismatch") not in found(named)
    assert ("ERROR", "icon-provider-mismatch") not in found(AWS_HOUSE + AWS_SKELETON)


def test_aws_services_without_a_cloud_frame_warn() -> None:  # phase 1.4 frame rule
    legend = "legend right\n| icon | AWS service |\nendlegend\n@enduml\n"
    bare = AWS_HOUSE + '!include <awslib20/Database/RDS>\ntitle Deployment diagram for X on AWS\nRDS(db, "DB", "PostgreSQL")\n' + legend
    assert ("WARN", "icon-no-cloud-frame") in found(bare)
    framed = bare.replace('RDS(db, "DB", "PostgreSQL")', 'AWSCloudGroup(c, "AWS Cloud") {\n  RDS(db, "DB", "PostgreSQL")\n}')
    assert ("WARN", "icon-no-cloud-frame") not in found(framed)
    styled = framed.replace('AWSCloudGroup(c, "AWS Cloud") {',
                            'AWSGroupColoring(Stage, #F2F8EC, #3F8624, dashed)\nAWSCloudGroup(c, "AWS Cloud") {')
    assert ("WARN", "inline-colour") not in found(styled), "library styling macros are not inline colour"


def test_frame_style_needs_a_legend_row() -> None:  # phase 1.5, STYLE rule 21
    az = (SCRIPTS.parent / "preambles" / "house-azure.puml").read_text(encoding="utf-8")
    body = ('!include <azure/Storage/AzureBlobStorage>\ntitle Deployment diagram for X on Azure\n'
            'rectangle "Microsoft Azure" as a <<AzureCloud>> {\n  rectangle "Batch" as b <<LogicalFrame>> {\n'
            '    AzureBlobStorage(s, "Raw", "Azure Blob Storage")\n  }\n}\n')
    bare = az + body + "legend right\n| icon | Azure service |\n| dashed line | not stated |\nendlegend\n@enduml\n"
    assert ("WARN", "frame-style-unlegended") in found(bare), "a dashed LINE row does not explain a dashed frame"
    told = bare.replace("| dashed line | not stated |", "| dashed frame | Batch, a logical group |")
    assert ("WARN", "frame-style-unlegended") not in found(told)
    solid = az + body.replace(' <<LogicalFrame>>', '') + "legend right\n| icon | Azure service |\nendlegend\n@enduml\n"
    assert ("WARN", "frame-style-unlegended") not in found(solid), "solid frames need no border row"


def test_new_skeletons_lint_clean() -> None:  # phase 1.5 items 2, 4, 5, 7, 9, 12
    for name in ("dfd", "swimlane", "state"):
        text = PREAMBLE + (SCRIPTS.parent / "templates" / f"skeleton-{name}.puml").read_text(encoding="utf-8")
        assert found(text) == set(), (name, found(text))
    for name in ("wbs", "cause-tree", "mindmap"):
        text = (SCRIPTS.parent / "templates" / f"skeleton-{name}.puml").read_text(encoding="utf-8")
        assert found(text) == set(), (name, found(text))
    tree = (SCRIPTS.parent / "templates" / "skeleton-wbs.puml").read_text(encoding="utf-8")
    cause = (SCRIPTS.parent / "templates" / "skeleton-cause-tree.puml").read_text(encoding="utf-8")
    assert fenced(tree) == fenced(cause), "the two wbs skeletons share one header"
    assert "!function $step($n)" in fenced(PREAMBLE), "numbered-step badge in the preamble"


def test_cli_exit_codes() -> None:
    script = str(SCRIPTS / "lint.py")
    ok = subprocess.run([sys.executable, script, str(FIXTURES / "clean.puml")], capture_output=True)
    bad = subprocess.run([sys.executable, script, str(FIXTURES / "no_title.puml")], capture_output=True)
    assert ok.returncode == 0 and bad.returncode == 1, (ok.returncode, bad.returncode)


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
