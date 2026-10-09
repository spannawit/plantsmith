---
name: plantsmith
description: PlantUML diagrams from written sources under a fixed house style, rendered locally and checked by eye. Use for an architecture, pipeline, data flow, sequence, schema, timeline or causal chain diagram, a records table beside a node, or any PlantUML authoring or rendering.
---

# plantsmith

Turn written sources (notes, tickets, specs, runbooks) into a PlantUML diagram that is
faithful, tidy and self-contained, then render it **on this machine** and look at it
before handing it over. Every file below is relative to this skill's folder.

- House style, the rules every diagram follows: [`STYLE.md`](STYLE.md)
- Proven syntax for records tables, notes, containers, lanes, legends, Creole escapes, the
  layout moves, C4 and the cloud icon libraries: [`reference/plantuml-features.md`](reference/plantuml-features.md)
- Review rubric for deliverables: [`RUBRIC.md`](RUBRIC.md)
- One worked example per shape, with both render passes recorded: [`examples/README.md`](examples/README.md)

## Workflow

### 1. Pick the diagram type by shape

| Shape of the content | PlantUML diagram | Start from |
|---|---|---|
| Cloud / platform / infrastructure map whose sources name cloud services: the DEFAULT for infra maps | the provider's architecture style: official icons of the provider the sources name, styled stage frames, the provider's frames (cloud, region, VPC/VNet, AZ, subnet) where stated | AWS: `preambles/house-aws.puml` + `templates/skeleton-aws.puml`; Azure: `house-azure.puml` + `skeleton-azure.puml`; Google Cloud: `house-gcp.puml` + `skeleton-gcp.puml` |
| System context: one system, its people and the systems it talks to | C4 Context (`Person`, `System`, `System_Ext`, `Rel`) | `preambles/house-c4.puml` with the include switched to `<C4/C4_Context>` + `templates/skeleton-c4.puml` |
| Containers of one system, when the reader asks for C4 or the map names no cloud services | C4 Container (AWS services as `$sprite`); Component only on request; Deployment one diagram per environment | `preambles/house-c4.puml` + `templates/skeleton-c4.puml` |
| Architecture map that is neither (repos, stages, no single system in scope) | component / deployment (`package`, `rectangle`, `database`, `cloud`) | `preambles/house.puml` + `templates/skeleton.puml` |
| Pipeline DAG: stages, tasks, checks, cadence | component / deployment, one `package` per stage, cadence in the stage title, each store inside the stage that writes it | `preambles/house.puml` + `templates/skeleton.puml` |
| Sequence: a procedure between actors, numbered steps, lanes | sequence (`box` lanes, `autonumber "<b>[00]"`, `group`) | `preambles/house.puml` + `templates/skeleton.puml` |
| Entity schema: tables by schema, typed columns | `entity` inside one `package` per schema, parents above children | `preambles/house.puml` + `templates/skeleton.puml` |
| Records table beside a node | Creole table in a `note`, a table inside an `object` body, or a `json` card | see `reference/plantuml-features.md` |
| Causal chain: event led to event, with checks | component with `linetype ortho` (rounded boxes, `hexagon` checks, notes) | `preambles/house.puml` + `templates/skeleton.puml` |
| Timeline, every step DATED in the source | Gantt (`@startgantt`) | `preambles/house-gantt.puml` + `templates/skeleton-gantt.puml` |
| Timeline with undated steps | not Gantt: a causal-chain style flow plus a Creole date table in a note, "no date" written in | `preambles/house.puml` + `templates/skeleton.puml` |
| Data flow or column lineage: processes, stores, externals, which column feeds which | component with `entity` tables (`src::col --> dst::col`, or a lineage table) | `preambles/house.puml` + `templates/skeleton-dfd.puml` |
| Runbook, DAG task flow, decision tree: steps by role, Yes / No branches | activity with lanes (`\|lane\|`) | `preambles/house.puml` + `templates/skeleton-swimlane.puml` |
| Lifecycle of one thing (a DAG run, a ticket, a partition) | state | `preambles/house.puml` + `templates/skeleton-state.puml` |
| Incident causes, ownership, brainstorm: a tree | `@startwbs` cause tree / ownership tree; `@startmindmap` for sketches only (its lines curve) | `templates/skeleton-cause-tree.puml`, `skeleton-wbs.puml`, `skeleton-mindmap.puml` |
| Subnet and address map; ArchiMate layer view | `@startnwdiag`; `archimate` stdlib | `preambles/house-nwdiag.puml`; `preambles/house-archimate.puml` |
| More than ~30 nodes, or a page outside 1:2 to 2:1 | split into an overview plus detail diagrams | either |

Done when: one row is chosen and you can name the preamble and skeleton you will start from.

### 2. Read the sources; list facts and "not stated"

Read every source in full. Write two lists in your working notes: **facts** (each one with
where it came from) and **not stated** (anything you would be tempted to draw that the
sources do not say: approvals, dates, cardinality, keys, FK targets, retries, owners).
Re-read for superseded decisions: only the current one is drawn.

Done when: every element you plan to draw maps to a fact, and the "not stated" list exists
(it may be empty, and you say so).

### 3. Author from the preamble and the skeleton

Start the new `<name>.puml` as the preamble followed by the skeleton, then edit only below the
`' house-preamble-end` marker, so the file renders on its own anywhere:

```bash
cat preambles/house.puml templates/skeleton.puml > <name>.puml      # Gantt: house-gantt.puml + skeleton-gantt.puml
```

The preamble is the house settings (never edited per diagram); the skeleton holds the
placeholder title, the shape vocabulary and a worked legend to cut down. Then:

- Title always (what, scope, as-of date when known).
- Shapes carry meaning (`STYLE.md` rule 2); groups the sources name are `package` containers,
  and a store sits inside the stage package that writes it (reference § Layout moves).
- Labels at most 40 characters per line. Detail (source refs, counts, SQL, rules) goes inside the
  element body for elements in nested packages (`..` separator + `//italic//` line), or in a `note`
  beside a free-standing element (`STYLE.md` rule 4).
- One colour, one meaning: colour only through the `<<group1>>`..`<<group4>>` / `<<failure>>`
  stereotypes defined in the preamble's `<style>`; never `#colour` on an element. A failure point is
  the element where it happens, filled `<<failure>>` (`STYLE.md` rule 10).
- A legend whenever more than two shape kinds or any colour appear; swatch rows use `|<#HEX>| meaning |`.
- Every "not stated" item is either left out or drawn dashed (`..>`, or `..` for an undirected ER
  link) with ONE legend row such as `| dashed line | inferred / not stated in the source |`. Write
  `not stated` or `inferred` on an edge only when that edge needs its own reason
  (`not stated: refresh`). Sequence diagrams are the exception: replies are already dashed, so a
  gap there is a `note` that says `not stated`.
- Escape Creole in identifiers: `extract~__lazada` prints `extract__lazada` (reference § Creole).
- C4: every element is a macro with a name and a short description, every Container also its
  technology; every `Rel` is one-way with an intent label ("Publishes order events to", never a bare
  "Uses") and a protocol between containers; no `BiRel`; one level per diagram; title
  `<Type> diagram for <scope>`; `SHOW_LEGEND()` last (`STYLE.md` rules 0, 11-13; reference § C4).
- AWS: a service the sources name is drawn with its official icon macro and a real technology
  (`Redshift(dw, "Sales DW", "Amazon Redshift")`), in group frames that mirror the source
  (`STYLE.md` rule 14; reference § Icon libraries). In C4, add it as `$sprite="Redshift"`.

Then run the linter and fix every ERROR:

```bash
python scripts/lint.py <name>.puml
```

Done when: lint prints `0 error(s)`, and any WARN left is one you can justify in the report.

### 4. Render locally

```bash
python scripts/render.py <name>.puml            # writes <name>.svg and <name>.png beside it
python scripts/render.py <name>.puml --out-dir <dir>
```

It never contacts the network; it refuses URL, absolute and `..` references, so includes stay in the diagram's
folder. It prints which PlantUML rendered (version and path), verifies the PNG (magic bytes, size) and prints
`size: WxH px, aspect R (W:H) OK|WARN, merged endpoints: N, label-on-node: N, label-on-edge: N, label-on-own-line: N`,
plus a `WARN` line per arrowhead stack (within 3 px), per label closer than 2 px to a node, frame border, frame title
or other line, and per label its own line runs into (`STYLE.md` rule 15; all three must reach 0 or be recorded).

On exit 1, read the PlantUML error it prints (the line number counts from `@startuml`), fix that
line and render again. Up to 3 tries, simplifying one step at a time when a direct fix fails:
drop exotic shapes for `rectangle`, drop notes, shorten labels, remove edges, then switch to a
simpler diagram type. After 3 failures, stop and show the error; do not claim a diagram.
Report the renderer line as printed. Hosted or web rendering is forbidden in every case, announced
or not: when local rendering is unavailable, stop and report what is missing.

Done when: exit 0. An aspect WARN is not a stop: step 5 answers it with a structural round or a split.

### 5. Look at the PNG, fix (at most two rounds), look again

Open the PNG with the Read tool. The viewer shrinks anything over 2000 px, so zoom before judging
small text: `python scripts/crop.py <name>.png --tile 1` (or `--box x,y,w,h`), then Read the `.crop.png` it writes.
Check, in this order (the lines first: `STYLE.md` "No noodle lines"). A cloud platform map also
passes reference § "Cloud platform map: acceptance checklist", every row ticked in the report:

| Look for | Usual fix |
|---|---|
| Curved, diagonal or tangled lines (noodles) | the diagram FAILS the look: ortho on, then Layout moves A-F, before anything else |
| A label sitting on another edge, or far from its own edge | shorten it to a few words and move the rest into the body or a `note` |
| Edges crossing nodes, titles or other labels | reorder declarations, a direction hint (`-left->`, `.right.>`), or drop a long back-edge in favour of a note |
| Clipped or mid-word wrapped text | shorter label, or a `\n` break between words |
| A colour or shape not in the legend | add the legend row |
| Stages side by side instead of stacked (a store package between two stages of one repo) | **structural:** move each store into the stage package that writes it (Layout move A) |
| ER: children above parents, or a wide row of tables | **structural:** parents first, FK edges child to parent upward or undirected `..`, `-[hidden]-` pins, `skinparam ranksep` / `nodesep` (Layout move B) |
| Notes far from their elements inside nested packages | **structural:** detail inside the element body (Layout move C) |
| An external entering a nested package from above crosses its title tabs | enter from the side (`-right->`), or put the external on the rank it feeds |
| C4: a line from an external loops round and crosses other labels | **structural:** put the external on the rank above what it feeds (`Rel_D`), pin with `Lay_D` / `Lay_R` (Layout move D) |
| `WARN merged-endpoints` from `render.py`: arrowheads stacked on one point | merge parallel edges, move one to another side with a hint, or a junction element (Layout move F) |
| `WARN label-on-node`: a label against the node above or below (short line) | longer runs: `skinparam ranksep 90`-`100` (or `nodesep` for side edges), aspect still in range (Layout move G) |
| `WARN label-on-node`: a label on a frame title or border (ortho centres it on its edge) | split or shorten the label (`invokes\n(Lambda)`), a longer arrow on that line only (`a ---> b`), the external on a long outside run (`-up->` from below), then a junction just outside the frame (`circle " " as j`); reversing the declaration does not help; record the engine limit and gap in px (Layout move G) |
| `WARN label-on-own-line`: its own line runs through the label (ortho put it on the line's bend) | a longer arrow on that line only (`a ---> b`) moves it onto the straight run (on azure a shorter or split label stayed on the bend); else record the engine limit and gap in px (Layout move G) |
| Sibling groups (two AZs) not lined up row for row | **structural:** `-[hidden]right-` pins between corresponding elements + `-down->` edges (Layout move E) |
| A `src::col --> dst::col` line enters a table through its top or crosses row text | check the row anchoring by eye; if it is not on the row, use a lineage table in a note (reference § Data flow and column lineage) |
| A strip or wall (aspect WARN) | the structural rows above; if the page still is a strip, split |

Round 1 fixes what the look found (labels, crossings, wraps, legend). Round 2 is reserved for
STRUCTURE: the Layout moves (`reference/plantuml-features.md` § Layout moves) or a split, never a
second cosmetic pass. Use round 2 only when round 1 leaves an aspect WARN or a structural row
above. When pass 1 already shows a structural defect, round 1 may be the structural one; round 2
is then the cosmetic one. Render and look after each round. Record every pass: what you saw, what you changed, what
remains. If a round is worse than the pass before it, restore the previous source AND re-render it
(step 4) so the SVG and PNG match the source, look again, and record that.

Done when: you have looked at every PNG (crops for small text) and written the pass record.

### 6. Save beside the document

Keep `<name>.puml`, `<name>.svg` and `<name>.png` together in the folder of the document the
diagram serves; link the PNG (or SVG) from the document, and keep the `.puml` as the editable source.
When there is no host document (a bake-off or a scratch folder), keep the three files together
where they are and say so in the report.

Other hosts (reference § html-plan exhibits, § Standalone page):
- html-plan page: `python scripts/exhibit.py <name>.svg --puml <name>.puml`, paste the fragment
  under the claim it proves. Interactive by default (hover highlights an element and its lines,
  tooltips, pan, zoom, sticky highlight, legend toggle); `data-ref` targets for `<doc-pin ref>`. One
  diagram per claim, cropped to the claim (split, do not shrink); keep the `.puml` beside the page.
  NEVER pack html-plan with `--artifact` for a page that holds a company diagram.
- Vault system note that is not a plan: `python scripts/publish.py <name>.svg` writes one
  self-contained `<name>.page.html` (same layers, light/dark, PNG export); link it from the note.
- Whiteboard: upload the PNG with a one-line caption (it takes PNG/JPEG/WebP only, no SVG, no anchors).

Done when: the three files sit side by side, and the document links one of the images (or the
report says there is no host document).

### 7. Review a deliverable

If the diagram goes to other people, have one separate reviewer (a fresh agent, not you) score
it against [`RUBRIC.md`](RUBRIC.md). Give it the sources, the `.puml` and the PNG path, not
your own verdict (for a C4 diagram, also the Yes/No checklist in the rubric). Fix any metric
scored 2 or less and every blocking finding, or report why it stays. When no separate
reviewer is available (no subagents allowed), skip this step and say so in the report; never
score your own diagram as the review.

Done when: the rubric scores are recorded with the pass record, or the report says step 7 was skipped and why.

## Common rationalizations

| If you think | Then |
|---|---|
| "The render log says OK; the reader can judge the picture" | The log cannot see a label on a border or a line through a word, and the reader is not the QA step. Open the PNG at 1:1; hand over only what passed the checklist. |
| "One more render pass and it will be right" | Two rounds is the cap. A third means the shape is wrong: change the layout move or split the diagram, and say so. |
| "That label only touches the border a little" | A touch is a touch; the check draws the line at 2 px for a reason. Fix it or record the engine limit with the px. |
| "Curved lines are fine for this one" | They are never fine here. Elbows only, every diagram. |

## Report

Tell the user: the three file paths, the renderer line from `render.py`, every pass (what
changed; each pass names the line check first: noodles, merged endpoints, crossings), the "not stated" list and how it is drawn, and any WARN or rubric gap left.
