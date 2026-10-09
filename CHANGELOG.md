# Changelog

All notable changes to plantsmith are recorded here, newest first.
The format follows [Keep a Changelog 1.1.0](https://keepachangelog.com/en/1.1.0/); version numbers mark build phases of the skill, not Semantic Versioning releases.

## [Unreleased]

## [1.8.2] - 2026-10-08

### Fixed
- `labels.py`: a text run joins a row only when it starts no more than 1 px back across the row's end (`ROW_JOIN_MIN_GAP`), so overlapping runs are no longer merged.
- `lint.py`: a position word (`left`, `right`, ...) opens a legend block only after the word `legend`.
- Review notes from the 1.8.1 re-check applied; 96 tests pass.

## [1.8.1] - 2026-10-08

### Fixed
- `label-on-own-line` measured the wrong line: a link's own line is now its unfilled path, each text row is measured alone, head and tail labels use their own rows.
- Notes beside a link and head/tail labels no longer raise false positives; links are matched by position.
- `render.py` WARN output no longer crashes on a legacy-codepage stdout (stdout is forced to UTF-8).
- Legend rows are read in any legend position and any case; only `dashed`, `dotted` and `bold` rows exempt a line from its label, a solid or plain line never does.
- One ink box per word, and any own-line crossing counts (the 2 px threshold is gone); the clean fixture was corrected.

### Changed
- `causal-chain` cleared by a longer arrow; `architecture-map` `receipts` (2.7 px) recorded as an engine limit.

## [1.8] - 2026-10-08

### Added
- `labels.py` third check `label-on-own-line`: a line running through the ink box of its own label; `render.py` reports all three counts independently.
- `lint.py` legend-only exemption: a dashed line may go unlabelled once when a legend row names the line style in its first cell.
- `## Common rationalizations` table in `SKILL.md` (four rows, kept at the 200-line cap).

### Changed
- `aws-vpc` reaches 0 / 0 / 0 (the `replicates` caption moved into the legend); `azure-data-platform` cleared by a longer arrow.

## [1.7] - 2026-10-07

### Added
- `reference/plantuml-features.md` Layout move G fix table with the move order: split or shorten the label, `--->`, `ranksep`/`nodesep`, outside run, junction plus legend row, split the diagram.
- `render.py` WARN prints the label's top-left corner; examples README gains a "Labels (node / edge)" column.

### Changed
- `azure-data-platform`, `gcp-data-platform`, `c4-container` and `archimate-layers` driven to 0 / 0; `aws-vpc` 12 to 3, `architecture-map` 2 to 1; residuals carry their engine limit and px.
- `lint.py`: an unlabelled line leaving a text-less junction circle is exempt from `icon-edge-unlabelled`.

## [1.6] - 2026-10-07

### Added
- `scripts/labels.py` SVG post-check run by `render.py`: `label-on-node` and `label-on-edge` (clearance 2 px).
- STYLE rule 15 "Labels clear of borders"; Layout move G; the cloud checklist row for labels widened.

### Changed
- Decisions written into STYLE: diagrams stay top to bottom; every line keeps its intent label, numbered badges are optional (rule 16).
- `aws-steps` fixed from 5 findings to 0.

## [1.5] - 2026-10-07

### Added
- Interactive layer for `exhibit.py`: hover highlight with dimming, tooltips, drag pan, wheel and pinch zoom, double-click reset, sticky click highlight (CSS plus a small inline script, `scripts/interactive.py`).
- `scripts/publish.py`: a standalone HTML page with light/dark theme and PNG export; nothing is fetched or vendored.
- `exhibit.py` accepts `data:` images, so icon diagrams work; SKILL step 6 names three targets (html-plan exhibit, standalone page, whiteboard PNG).
- Shapes added: data flow and lineage (rule 17), cause trees (18), wbs trees and authority matrix (19), ArchiMate layers (20), swimlane, state, nwdiag and mind-map skeletons.
- Frame-kind rule 21 (solid administrative, dashed logical, dotted hosting not stated) with lint `frame-style-unlegended`; optional `$step(n)` badges (rule 16).
- Mapping table of diagram types to bundled libraries (31 rows); Azure and GCP zone stereotypes.
- Nine examples (`aws-steps`, `column-lineage`, `incident-cause-tree`, `ownership-tree`, `runbook-swimlane`, `dag-run-states`, `subnet-map`, `archimate-layers`, `report-ideas`); every example now has `.exhibit.html` and `.page.html`; 84 tests.

## [1.4] - 2026-10-07

### Added
- Provider rule: the icon library follows the provider the sources name; lint `icon-provider-mismatch` is an error.
- `preambles/house-azure.puml`, `house-gcp.puml`, skeletons, and the `azure-data-platform` and `gcp-data-platform` examples.
- Frame rule for AWS: the AWS Cloud frame is always drawn, Region, VPC, AZ and subnet only when stated, coloured stage frames, a "hosting not stated" frame; lint `icon-no-cloud-frame`.
- Ten-row cloud platform acceptance checklist; NOTICE rows for the Azure and GCP icon libraries.

## [1.3] - 2026-10-07

### Added
- "No noodle lines" block at the top of STYLE; lint `no-ortho` and `curved-lines` are errors with no exemptions.
- `scripts/exhibit.py`: wraps a rendered SVG as an html-plan `doc-mock` fragment with a `data-ref` per element and line; refuses remote references.
- Lint `icon-edge-unlabelled`, `icon-edge-no-protocol`, `icon-no-legend`.

### Changed
- Orthogonal edges in every preamble, C4 included (Gantt exempt); AWS style becomes the default for infra maps that name cloud services, C4 only on request; STYLE rule 14 rewritten; rubric Layout scores at most 2 for curved or tangled lines.

## [1.2] - 2026-10-07

### Added
- C4 System Context and Container diagrams on PlantUML's bundled C4 library: `preambles/house-c4.puml`, `templates/skeleton-c4.puml`, `scripts/lint_c4.py`.
- AWS icon library support: `preambles/house-aws.puml` (24 service include paths smoke-tested) and `templates/skeleton-aws.puml`.
- STYLE rules 11 to 15 (C4 elements, relationships, one level per diagram, cloud icons, endpoints never coincide); RUBRIC gains the 21-question C4 checklist and blocking / important / nice triage.
- `render.py` merged-endpoint SVG check; Layout moves D, E, F; examples `c4-container` and `aws-vpc`.

### Fixed
- Lint false positives on hyphens in titles and notes; body-line limit 48; `=` heading gotcha; side-entry row.

## [1.1] - 2026-10-07

### Added
- `scripts/crop.py` (pure-Python PNG crop and tiles) for looking at large renders at 1:1; `templates/skeleton*.puml`.
- Layout moves A (stores inside the stage that writes them), B (ER parents above children) and C (detail inside the body); `$LEGEND_FRAME` knob; `hide circle`.
- Failure points drawn as in-flow `<<failure>>` elements (rule 10); lint `creole-in-label`.

### Changed
- A second fix round is allowed and is for structure only (rule 8); `wrapWidth` 300; `«PK»` text mark replaces `*`.
- Pipeline and schema shapes now fit the 1:2 to 2:1 page rule that the first version missed.

## [1.0] - 2026-10-06

### Added
- The skill: `SKILL.md` workflow, `STYLE.md`, `RUBRIC.md`, `NOTICE.md`, `preambles/house.puml` and `house-gantt.puml`, `reference/plantuml-features.md`.
- `scripts/render.py`: local-only rendering, PNG checks, aspect warning, prints the PlantUML binary used.
- `scripts/lint.py` with seven rules; all three records-table forms (Creole note table, object-body table, `json` card).
- Six examples with two-pass render records: `causal-chain`, `architecture-map`, `pipeline-dag`, `sequence-lanes`, `dated-timeline`, `entity-schema`.

### Fixed
- Hardening after a blind review: `SANDBOX` was dropped on any `!include` and an inherited `UNSECURE` profile survived; now `SANDBOX`, or `ALLOWLIST` confined to the diagram folder when the source includes a sibling file.
- URL, absolute and `..` targets refused in `!include`, `!import`, `!theme from`, `%load_json` and `<img:>`; `-D` overrides stripped from `JAVA_TOOL_OPTIONS`; a PNG must end with `IEND`; tests grew from 18 to 33.
