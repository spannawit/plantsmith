# Examples

Nineteen synthetic diagrams, one per shape, most for a fictional bookshop. Every folder also holds the html-plan exhibit (`.exhibit.html`) and the standalone page (`.page.html`) made from its SVG.
`.puml` source (its synthetic source brief is the comment block at the top), the `.svg` and
the `.png`, all produced by `scripts/render.py` and passing `scripts/lint.py` with no findings.

| Shape | Folder | Diagram type |
|---|---|---|
| Causal chain | `causal-chain/` | component, `linetype ortho` |
| Architecture map | `architecture-map/` | component / deployment |
| Pipeline DAG | `pipeline-dag/` | component, one package per stage |
| Sequence with lanes | `sequence-lanes/` | sequence, `box` lanes |
| Dated timeline | `dated-timeline/` | Gantt |
| Entity schema with records | `entity-schema/` | entity + all three records-table forms |
| Container map (C4) | `c4-container/` | C4 Container, `preambles/house-c4.puml` |
| Cloud infrastructure (AWS) | `aws-vpc/` | awslib20 icons in nested group frames, `preambles/house-aws.puml` |
| Cloud data platform (Azure) | `azure-data-platform/` | Azure-PlantUML icons in styled frames, `preambles/house-azure.puml` |
| Cloud data platform (Google Cloud) | `gcp-data-platform/` | GCP icons in styled frames, `preambles/house-gcp.puml` |
| Numbered steps on AWS (optional badges) | `aws-steps/` | awslib20 + `$step(n)` badges and a step table |
| Data flow and column lineage | `column-lineage/` | component + `entity`, `skeleton-dfd.puml` |
| Incident cause tree | `incident-cause-tree/` | `@startwbs`, `skeleton-cause-tree.puml` |
| Ownership tree with an authority matrix | `ownership-tree/` | `@startwbs`, `skeleton-wbs.puml` |
| Runbook swimlane | `runbook-swimlane/` | activity with lanes, `skeleton-swimlane.puml` |
| DAG-run lifecycle | `dag-run-states/` | state, `skeleton-state.puml` |
| Subnet map | `subnet-map/` | `@startnwdiag`, `preambles/house-nwdiag.puml` |
| ArchiMate layer view | `archimate-layers/` | `archimate` stdlib, `preambles/house-archimate.puml` |
| Brainstorm sketch | `report-ideas/` | `@startmindmap` (curved lines: sketch only), `skeleton-mindmap.puml` |

## Render passes (STYLE.md rule 8)

| Example | Pass 1: what the look found | Pass 2: the fix, and what remains | Labels (node / edge / own-line) |
|---|---|---|---|
| aws-steps | 1:2.10 strip; "places order" sat on the AWS Cloud title; two labels crossed their lines | round 1: customer and manager enter from the side, two-line labels (`orders\n(HTTPS)`); round 2: `nodesep 110`. 1:1.18, 0 merged endpoints. Phase 1.6: the label check found 5 (three labels against the node above or below, two on the AWS Cloud border); `ranksep 100`, `invokes\n(Lambda)`, the manager enters from below (`-up->`): 1:1.94, label-on-node 0, label-on-edge 0 | 0 / 0 / 0 |
| column-lineage | five `src::col --> dst::col` lines ran down through the rows of two tables; `isbn : char(13)` fell into a method compartment | round 1: the column lines became a lineage table in a note beside the target, `{field}` on typed fields. 1:1.84, clean | 0 / 0 / 0 |
| incident-cause-tree | the `<<AND>>` stereotype did not print; the dashed gate style also dashed its lines (dashed = not stated) | round 1: the gate reads "AND: published anyway", styled bold not dashed. 1.76:1, clean | 0 / 0 / 0 |
| ownership-tree | clean on pass 1 (1.08:1) | none needed | 0 / 0 / 0 |
| runbook-swimlane | "Open an incident" landed in the analyst lane; legend called the decision a diamond | round 1: lane set inside the No branch; legend says hexagon (decision) and diamond (join). 1:1.14, clean | 0 / 0 / 0 |
| dag-run-states | empty compartment under every state name; legend said "filled dot" for a ring | round 1: `hide empty description`, legend wording. 1:1.26; the two retry labels sit close together between their parallel lines Phase 1.7: residual 0 / 1, `a task fails` crosses the retry line by 7.9 px. Engine limit: the two opposite edges between `running` and `up for retry` run as parallel lines 10 px apart and ortho puts both labels on the same side; seven variants (direction hints, reversal, state order, two-line labels) gave 1 to 4 crossings each; the state notation has no neutral junction (choice = decision, fork/join = concurrency) | 0 / 1 / 0 |
| subnet-map | clean on pass 1 (1:1.16); the address labels sit on their drop lines by nwdiag design | none needed (not routed; linetype does not apply) | 0 / 0 / 0 |
| archimate-layers | the "hosts" relation was a diagonal: the library resets the line type | round 1: ortho set after the include (preamble), legend wording. 1:1.83; "serves" and "stores" sit next to the layer frame titles Phase 1.7: 2 label-on-node (touching the layer frame tops, gap 1.4 px); `skinparam ranksep 90` after the preamble: 1:1.96, 0 / 0 | 0 / 0 / 0 |
| report-ideas | the mind-map engine draws curved lines; 2.31:1 | not fixable in mindmap (also not with `top to bottom direction`): kept as the sketch example, wbs for deliverables. Aspect WARN remains | 0 / 0 / 0 |
| causal-chain | the dashed "not stated" label collided with the "Saturday" caption | a `.left.>` direction hint made it worse (the cloud overlapped the node). Pass 3 went back to the pass-1 layout, cut the caption to `not stated` and moved the question into a note on the cloud: clean Phase 1.8: label-on-own-line 1, `not stated` crossed by its own line on the bend (9.0 px; 11.5 px with the phase 1.8.1 ink box) Phase 1.8.1: a longer arrow (`distributor ...> shelf`, Layout move G) moved it onto the straight run: 1:1.38, 0 / 0 / 0, checked at 1:1 | 0 / 0 / 0 |
| architecture-map | the `checkout` and `reorders` captions sit on neighbouring edges | wider `nodesep`/`ranksep` pushed the page to 2.13:1 without clearing them, so the pass-1 source was restored. Remaining: `checkout` touches the `receipts` edge Phase 1.7: 0 / 2; a longer arrow to the payments cloud (`web ---> payments`) cleared `checkout`: 1.60:1. Residual: `reorders` touches the unlabelled Stock-to-Catalogue line (gap 0.7 px). Engine limit: both lines leave Stock service 47 px apart and the one-word label is 45 px; `-right->` reflowed `shelf counts` onto the `sales` line, a junction put the label on the circle (3.5 px), reordering changed nothing Phase 1.8: label-on-own-line 1, `receipts` crossed by its own line by 2.7 px Phase 1.8.1: a longer arrow (`web ---> email`, Layout move G) reflowed the map to 4 / 5 / 1 (`orders` 8.0 px on its own line), so the 1.7 source stays. Engine limit: ortho seats the label on the elbow of the right-then-down line, and the horizontal run passes 0.2 px above its baseline (2.7 px into the ink box) | 0 / 1 / 1 |
| pipeline-dag | the long dashed back-edge's caption landed in the middle of the transform stage, far from its edge | the back-edge was replaced by a `not stated` note beside the alert: clean. Remaining: the `match` caption brushes the publish container border | 0 / 0 / 0 |
| sequence-lanes | clean, but the "not stated" note floated at the bottom, away from the deposit step | the note was moved to the deposit step (07) | 0 / 0 / 0 |
| dated-timeline | the week axis showed ISO week numbers, and the last month header ("May") was clipped | `printscale weekly with calendar date` shows week-start dates. Remaining: the clipped "May" header (a Gantt limit) | 0 / 0 / 0 |
| azure-data-platform | 1:1.24; "uploads daily CSV (HTTPS)" sat on the dashed Key Vault line, labels on stage borders | round 1: Key Vault moved into the Warehouse frame, orders read downward; round 2 (cosmetic): the secrets edge drawn downward. Clean at 1:1.66; two labels sit on stage frame borders (not titles) Phase 1.7: 6 label-on-node (three labels across the Azure and stage borders); split labels (`writes JSON\n(Blob API)`, `copies rows\n(PolyBase)`, `reads secrets\n(not stated)`) and `nodesep 100`: 1:1.64, 0 / 0 Phase 1.8: label-on-own-line 1, `uploads daily CSV (HTTPS)` crossed by its own line by 6.7 px on the bend of its down-then-right path; a shorter label (6.7 px) and a split label (6.0 px) stayed on the bend; a longer arrow (`till ---> landing`) moved it onto the straight run: 1:1.65, 0 / 0 / 0, 0.3 px beside its own line, checked at 1:1 | 0 / 0 / 0 |
| gcp-data-platform | 1.23:1; edges tangled through the Warehouse frame, two labels on other lines | round 1: Composer and the landing bucket loaded BigQuery directly; round 2: pin; pass 4: two columns (landing / orders), two-line labels; pass 5 (over budget): pipeline left of Composer. 1:1.55, 0 merged endpoints; "writes rows (Write API)" crosses its own line at the bend (recorded) Phase 1.7: 5 label-on-node; split labels, `ranksep 110` / `nodesep 90`, the till enters on a longer arrow (`till ---> landing`), and the CSV line goes through a junction just outside Ingest (round 1 shorter label and reversal did not move it off the Warehouse border): 1:1.88, 0 / 0 Phase 1.8: label-on-own-line 0; the bend crossing of "writes rows" recorded in 1.5 is gone since 1.7 (1.0 px beside its line) | 0 / 0 / 0 |
| c4-container | elbows on (C4 preamble ortho): four labels on lines and nodes | round 1: edges all down, short labels, manager to the side; round 2: `nodesep 160`. 1.47:1; "Takes payments via [HTTPS]" straddles the boundary border Phase 1.7: 3 / 1 (three labels on the boundary, one on the Reads-orders line); `Writes sales to`, `E-mails the PDF to`, `Rel_R` to the payment provider, `nodesep 200`: 1.77:1, 0 / 0 | 0 / 0 / 0 |
| aws-vpc | rows aligned across the two zones (Layout move E pins), 1:1.85; the `SQL` captions sat on the Auto Scaling group borders and `replication` sat on the AZ 2 border | round 1: dropped the two `SQL` captions (the RDS technology says PostgreSQL) and moved the replication caveat to the legend row: clean. The ELB's two edges to the proxies leave and arrive at separate points (0 merged endpoints, Layout move F) Phase 1.7: 12 label-on-node; `balances\n(HTTPS)` into AZ 2, `ranksep 60` with both `conf ---> db` lines: `balances` and `stores pages` clear, 1:1.98. Residual 3 / 0: `replicates (not stated)` crosses the AZ 1 (2.5 px), AZ 2 (26.5 px) and Private Subnet 2 (10.2 px) borders. Engine limit: the two zones sit 24 px apart (`nodesep` does not widen the gap) and the flat edge's label (67 px) is centred in it; reversal changed nothing and a junction was placed outside AZ 1 and routed round both zones Phase 1.8: the `replicates\n(not stated)` caption dropped; the legend's `dashed line` row ("not stated in the source: how Primary replicates to Secondary") carries its meaning (STYLE rule 15, legend-only exemption in lint): 1:1.98, 0 / 0 / 0, checked at 1:1 | 0 / 0 / 0 |
| entity-schema | `isbn : char(13)` dropped into a method compartment (parentheses); the `inferred` caption collided with the `order_id` edge; the legend said `*` but the picture draws a circle | `{field}` prefix, a `.right.>` hint on the inferred edge: clean. Phase 1.1: `*` (IE: mandatory, not a key) replaced by the `«PK»` text mark, `hide circle` drops the "E" spot, FK edges point up so parents sit above children (Layout move B), the dashed edge is marked by its legend row | 0 / 0 / 0 |

The labels column is `render.py`'s `label-on-node / label-on-edge / label-on-own-line` on the shipped SVG
(STYLE rule 15); a non-zero count carries its engine limit and gap in the pass-2 cell, or says the Layout
move G fixes are not yet tried.

All six were re-rendered in phase 1.1 with the current preamble (`wrapWidth 300`, `hide circle`, the
`$LEGEND_FRAME` knob); a test keeps each example's preamble identical to `preambles/`. Failure points
follow STYLE rule 10: `pipeline-dag` fills the alert box on the mismatch branch and `causal-chain` fills
the steps that failed, both with `<<failure>>`, never a coloured note.

The first render of `sequence-lanes` failed outright: `top to bottom direction` in the preamble
made PlantUML parse it as a class diagram. That line was removed from the preamble (see the gaps in `STYLE.md`).
