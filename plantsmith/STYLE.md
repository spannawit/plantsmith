# House style (PlantUML)

Every rule is mandatory where PlantUML offers it. Where it does not, the gap and its
fallback are listed at the end; say so in the report instead of pretending.

## No noodle lines

Lines are straight segments with right-angle elbows (`skinparam linetype ortho`), routed around
nodes and labels. No curves, no diagonals, no two lines sharing a path. Every diagram is judged
first on its lines: a diagram with curved or tangled lines fails, whatever else is right.
Motivation, in the reviewer's words: "I HATE NOODLE/SPAGHETTI LINES!!!"

## Rules

0. **Title always.** No diagram without a title; no colour without a legend. A C4 title reads
   `<Type> diagram for <scope>` ("Container diagram for Order Sync"), and the key is
   `SHOW_LEGEND()`, never `LAYOUT_WITH_LEGEND()` (it lists unused types and drops tag rows).
1. **Direction and routing.** Top to bottom (PlantUML's default; see the gaps below for why the
   preamble does not say `top to bottom direction`). Orthogonal edges (`skinparam linetype ortho`)
   in every diagram that routes lines, C4 and AWS included (see "No noodle lines"; lint ERRORs
   `no-ortho` and `curved-lines`).
   No edge may cross a node, a container title or another edge's label. Siblings of one stage
   sit side by side. Decided 2026-10-07: top to bottom stays the house direction.
2. **Shapes carry meaning.**

   | Meaning | PlantUML element |
   |---|---|
   | data store | `database` (cylinder) |
   | topic or queue | `queue`; a dead-letter queue is a `queue` filled `<<failure>>` |
   | external system, API or cloud service | `cloud` |
   | process, task or step | `rectangle` (rounded by the preamble) |
   | check or decision | `hexagon` (component diagrams have no diamond) |
   | document, report, file or ticket | `file`, or a `note` for detail text |
   | repo, stage, schema or lane | `package` (container with a title); sequence lanes are `box` |

   Add a legend when more than two shape kinds appear.
3. **Grouping is real.** Every grouping the sources name is a container, nested where it
   helps. Never group by colour alone. A data store sits inside the stage package that WRITES it,
   not in a separate store package: a repo -> bucket -> repo flow cannot stack top to bottom
   otherwise (reference § Layout moves, A). Name the bucket or schema in the store's label.
4. **Detail sits with the node.** Source refs, counts, SQL and job names go INSIDE the element
   body when the element sits in a nested package (a `..` / `....` separator, then `//italic//`
   lines; reference § Layout moves, C), and in a `note` beside a free-standing element or for a
   records table (reference § Records tables). Notes on elements inside nested packages drift
   far from them. Labels stay at or under 40 characters per line, entity fields (name, type and
   mark) at or under 48, note lines at about 45; nothing wraps mid-word (`skinparam wrapWidth 300`).
   Split into two diagrams before shrinking text.
5. **Thin source is marked on the picture.** A fact the sources do not state (approvals, dates,
   cardinality, FK targets, natural vs surrogate key, retries) is absent, or drawn dashed (`..>`,
   or `..` for an undirected ER link) plus ONE legend row (`dashed line | inferred / not stated`).
   The word goes on an edge only when that edge needs its own reason. Never drawn as fact.
6. **Current decisions only.** A decision superseded by a later section or addendum does not
   appear as current.
7. **Page shape.** Aspect ratio between 1:2 and 2:1 (`render.py` warns). A strip is a failure:
   apply a Layout move (rule 8, round 2), and split when the page is still a strip.
8. **At most two fix rounds.** Render, look at the PNG, fix collisions and crossings (round 1),
   render and look again. A second round is for STRUCTURE only (the Layout moves or a split),
   when round 1 leaves an aspect WARN or a structural defect. Record every pass.
9. **One colour, one meaning.** Each fill stands for exactly one thing (a stage, a schema, a
   failure) and appears in the legend. Colours are defined once as stereotype classes in
   `<style>` and applied with `<<name>>`; the same colour never marks two kinds. In C4 the
   equivalent is the style macros in the C4 preamble (`UpdateElementStyle`, `AddElementTag`,
   `AddRelTag`), defined once, each with a `$legendText` so `SHOW_LEGEND()` lists it.
10. **Failure points are flow elements.** A failure point the sources name is the element where it
    happens, filled `<<failure>>`: the step, store or feed that fails, or an outcome box on a
    check's error branch (`examples/pipeline-dag`, the alert). Its reason goes in the body
    (rule 4). Never a red note: notes stay neutral, and a coloured note needs an inline colour
    (rule 9).
11. **C4 elements are complete.** Every element is its macro (`Person`, `System_Ext`, `Container`,
    `ContainerDb`, ...) with a name and a short description of what it does; every Container (and
    Component) also names its technology. Acronyms are spelled out or in the legend.
12. **C4 relationships say what they do.** Every line is one-way (no `BiRel`), labelled with the
    intent read in the arrow's direction ("Publishes order events to"); a single verb ("Uses",
    "Calls", "Reads") is not a label. A line between two containers names its protocol or
    technology ("HTTPS", "SQL", "Kafka"). Dashed means inferred / not stated (rule 5).
13. **One level per diagram.** Context: the system in scope plus the people and systems directly
    connected to it. Container: the containers of that one system plus the people and systems they
    talk to. Component: the inside of one container, only on request. Deployment: one diagram per
    environment. Context plus Container suffice for most readers.
14. **Cloud services use their official icons; infra maps use the provider's style.** The icon
    library follows the provider the SOURCES name: `awslib20` (`preambles/house-aws.puml`) for AWS,
    `azure` 2.2.0 (`house-azure.puml`) for Azure, `gcp` 6.0.0 (`house-gcp.puml`) for Google Cloud. A
    multi-cloud map uses each provider's own icons for its own services; never AWS icons or AWS
    frames for a non-AWS platform (lint ERROR `icon-provider-mismatch` when the title and legend do
    not name every provider whose library is included). For AWS: service icons as the nodes, `GenericGroup` frames for stages and
    the AWS groups (AWS Cloud > Region > VPC > Availability Zone > subnet) where the source names
    them. C4 Container with sprites is the alternative only when the reader asks for C4 or the map
    has no cloud services. Draw an icon only for a service the source names (no RDS icon for a
    "Postgres" the source does not place on RDS, no EKS icon for "Kubernetes"); use a neutral
    icon (`Genericdatabase`, `Containers`) and say what is not stated. The C4 relationship rules
    (rule 12) apply to these diagrams too: one-way lines with an intent label and the protocol.
    Frames: for a platform on AWS the outer `AWSCloudGroup` is a stated fact (the services are AWS)
    and is always drawn; `RegionGroup`, `VPCGroup`, AZ and subnet frames only where the sources
    state them (a region stated for one service frames that service only). Stage frames use the
    AWS group look: `AWSGroupColoring` + `AWSGroupEntity` with one colour per stage and a sprite,
    each colour in the legend. Externals (vendors, users) sit outside the cloud frame; a system
    whose hosting the sources do not state sits in a grey dotted "hosting not stated" frame.
15. **Edge endpoints never coincide** (part of "No noodle lines"). Fan-in edges arrive on distinct points of the target's border
    or on distinct sides; arrowheads never stack. `render.py` measures it on the SVG
    (`merged endpoints: N`, one `WARN merged-endpoints` line per cluster within 3 px). When the
    engine cannot separate them, reduce the fan-in (one labelled edge from a group, a junction
    element, a hidden ordering, a direction hint to another side) and record the choice in the
    pass record (reference § Layout moves, F). Never switch to `polyline`: that trades a merge for
    diagonals.
    **Labels clear of borders.** An edge label or step badge never touches a node, a frame border, a
    frame title or another line; the look fails on it as it fails on a noodle. `render.py` measures
    it (`label-on-node: N`, `label-on-edge: N`; "touches" = closer than 2 px) and both must reach 0,
    or the pass record names the engine limit and the gap in px (fixes: reference § Layout moves, G).
    Its own line never runs through it either (`label-on-own-line: N`: the line runs inside the ink box
    of a text row, ascent to descent for every word, as on the bend of a down-then-across line), held
    to the same bar.
    A junction (`circle " " as j`, a legend row) also serves a frame crossing: put it just outside the
    frame, label the run that stays clear, and let the continuation go unlabelled (lint allows it).
    A dashed, dotted or bold line may also go unlabelled when a legend row names its style in the first
    cell (`| dashed line | not stated: ... |`): the row says what the line means, so lint accepts it.
    A solid or plain line never does: it still carries its intent label (rule 16). Lint reads a row
    whose first cell is the style word and `line` (`| Dotted lines |` too, any legend position); a
    `|=` header row, a first cell that starts with a colour swatch, and `plain` are not read.

16. **Numbered steps are optional; intent labels are not.** A diagram may tell its story in numbered
    badges (`$step(1)` from the preamble, in a label, an edge label or the legend) with a numbered
    step table in the legend. Every line still carries its intent label and protocol (rules 12, 14):
    badges add the order, they never replace the label. Decided 2026-10-07: every line carries
    `intent (protocol)`, with the badge as an optional prefix.
17. **Data flow and lineage.** Processes are rounded boxes (numbered as in the source), stores are
    cylinders, externals are actors; a table whose columns matter is an `entity`, and a column-level
    flow is `src::col --> dst::col`, checked by eye in step 5 (a lineage table in a note when the
    line does not land on the row).
18. **Cause trees cite evidence.** The problem on top, causes grouped by category (data, process,
    tooling, people), every leaf with its evidence or "not stated"; a fault-tree gate is a node whose
    text starts "AND:" or "OR:". Elbow lines only (wbs), never fishbone diagonals.
19. **Trees are wbs.** Ownership and other hierarchies are `@startwbs` (elbows by construction); an
    authority matrix is a Creole table in the legend. `@startmindmap` draws curves: sketches only.
20. **ArchiMate layers stack.** Business on top, application in the middle, technology at the
    bottom, each layer a Grouping; a relation from a lower layer to a higher one uses the `_Up`
    variant; every relation has a label.
21. **Frame kind by border style.** Solid frame = an administrative boundary (account, cloud,
    subscription, VPC); dashed frame = a logical group or zone (stage, AZ, Batch / Streaming, a
    layer); dotted frame = hosting not stated. "Dashed means not stated" (rule 5) applies to LINES
    only. Every dashed or dotted frame kind has a legend row (lint WARN `frame-style-unlegended`).
    A provider's own group macros keep their provider border (AWS Region is dotted teal); the
    legend row names it.

## PlantUML settings (in `preambles/house.puml`)

| Setting | Why |
|---|---|
| `!theme plain` | neutral base; colour is added only where it means something |
| `skinparam linetype ortho` | orthogonal edges (rule 1) |
| `skinparam wrapWidth 300`, `maxMessageSize 300` | notes, messages and entity fields wrap between words; an entity field of 48 characters (name, type, mark) stays on one line, and so does a note line of about 45 |
| `skinparam lifelineStrategy solid` | intended solid lifelines (see gaps) |
| `skinparam legendBackgroundColor transparent`, `legendBorderColor $LEGEND_FRAME` | the legend reads as a key, not a node; the frame colour is the named knob `!$LEGEND_FRAME` at the top of the preamble (`"transparent"` removes the frame) |
| `hide stereotype` | stereotype names used for colour do not print on elements |
| `hide circle` | no class spot (the "E" on entities, "C" on classes); key marks are text (`<<PK>>`, `<<FK>>`, `<<own key>>`) |
| `<style>`: font, title size, `rectangle { RoundCorner 14 }`, `.failure`, `.group1`..`.group4` | rounded process boxes; the colour palette with one meaning per class |
| `autonumber "<b>[00]"` (sequence) | numbered steps with a fixed format |
| ER edges plain (`--`, `..>`, `..`), parents above children | crow's feet only where the source states cardinality; FK edges run child to parent upward (`-up->`) or undirected (reference § Layout moves, B) |
| no Gantt for undated steps | a Gantt bar invents a date |

## What PlantUML cannot do here, and the fallback

| Gap (PlantUML 1.2026.8) | Fallback |
|---|---|
| No diamond in component/deployment diagrams | `hexagon` for checks; the legend says so |
| No `rank=same` rows, so no dated ladder with aligned rungs | dated steps: Gantt; mixed or undated: a flow plus a Creole date table in a note with "no date" written in |
| `linetype ortho` places edge labels near the edge midpoint; with bundled edges a label can sit on another edge or far from its own | short labels, detail in notes, direction hints, drop long back-edges; check in the step 5 look |
| `top to bottom direction` makes PlantUML parse a sequence diagram as a class diagram (syntax error) | left out of the preamble; top to bottom is the default anyway |
| `skinparam lifelineStrategy solid` showed no visible effect with `!theme plain`; lifelines render dashed | accepted; lifelines are not a meaning carrier |
| Sequence replies are dashed by UML convention, so a dashed arrow cannot also mean "not stated" | in sequence diagrams, mark a source gap with a `note` that says `not stated` |
| A column type with parentheses (`char(13)`) makes a field parse as a method in a body without separators | add a `--` separator or the `{field}` prefix |
| `hide stereotype` hides element stereotypes only; field marks like `<<PK>>` still print as `«PK»` | that is the house key mark: use it only where the source states the key. A `*` before a field means mandatory (NOT NULL) in IE notation, not a key: use it only where the source states NOT NULL |
| Creole markup inside identifiers: `__` underlines, `**` bolds, `//` italicises | escape with `~`: `extract~__lazada` prints `extract__lazada` (lint WARN `creole-in-label`) |
| Graphviz cannot stack the stages of one repo container when a separate store package sits between them in the flow | stores inside the stage that writes them (rule 3) |
| C4 legend glyphs (person, container, boundary icons) render as empty boxes with the house font | accepted; the row text carries the meaning |
| Under `linetype ortho`, edge labels sit at a fixed point on the edge and can land on a node, a frame title or another line (C4's two-line labels most of all) | short intent labels, wider `nodesep`/`ranksep`, edges in one direction, `Lay_*`/hidden pins (reference § Layout moves, D); record what stays |
| Gantt: the last month header is clipped at the chart's end; milestone labels cross grid lines | accepted; keep labels short |
| SVG tooltips on elements were not verified in this version | detail goes in notes |
