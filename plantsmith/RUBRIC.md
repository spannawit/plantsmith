# Review rubric

For a separate reviewer. Score the rendered PNG (the SVG if no PNG) against the written
sources: the sources are the truth, not the prettiest picture. Read the sources first, then
the `.puml`, then the image. Integers 1 to 5.

| Metric | 5 means | 1 means |
|---|---|---|
| Completeness | every element the request asks for is present (steps, dead ends, groups, lanes, axis, columns) | half or more missing |
| Faithfulness | every label traces to the source; thin sources are marked, not filled in | invented nodes or wrong relations |
| Layout | top to bottom, straight lines with right-angle elbows, no edge crossings or overlaps, groups read as groups. Curved, diagonal or tangled lines score at most 2, whatever else is right | tangled; crossings and collisions decide the reading order |
| Neatness at a glance | a human gets the shape in five seconds; page between 1:2 and 2:1 | a strip or a wall; zooming is needed to find the start |
| Style | consistent fonts, colours with meaning and a legend, labels not clipped or wrapped mid-word | mixed styles, clipped text, unexplained colour |
| Detail capacity | evidence lines, columns or records sit beside the right element without crowding | detail dropped or dumped into one blob |
| Editability | plain-text source; a one-node change is a one-line edit | an image only, or a change reflows everything unpredictably |
| Cost | 0 or 1 fix rounds in the two-pass record | 3 or more rounds |

Weights: completeness 2, faithfulness 2, layout 2, neatness 2, style 1, detail 1,
editability 1, cost 1 (max 60).

## C4 checklist (C4 diagrams only)

Answer each question Yes or No, from the C4 model's review checklist (c4model.com, CC BY 4.0,
Simon Brown). List every "No" with the element or line that caused it.

| Group | Question |
|---|---|
| General | Does the diagram have a title? |
| General | Do you understand what the diagram type is? |
| General | Do you understand what the diagram scope is? |
| General | Does the diagram have a key/legend? |
| Elements | Does every element have a name? |
| Elements | Do you understand the type of every element? (i.e. the level of abstraction; e.g. software system, container, etc) |
| Elements | Do you understand what every element does? |
| Elements | Where applicable, do you understand the technology choices associated with every element? |
| Elements | Do you understand the meaning of all acronyms and abbreviations used? |
| Elements | Do you understand the meaning of all colours used? |
| Elements | Do you understand the meaning of all shapes used? |
| Elements | Do you understand the meaning of all icons used? |
| Elements | Do you understand the meaning of all border styles used? (e.g. solid, dashed, etc) |
| Elements | Do you understand the meaning of all element sizes used? (e.g. small vs large boxes) |
| Relationships | Does every arrow have a label describing the intent of that relationship? |
| Relationships | Does the description match the relationship direction? |
| Relationships | Where applicable, do you understand the technology choices associated with every relationship? (e.g. protocols for inter-process communication) |
| Relationships | Do you understand the meaning of all acronyms and abbreviations used? |
| Relationships | Do you understand the meaning of all colours used? |
| Relationships | Do you understand the meaning of all arrow heads used? |
| Relationships | Do you understand the meaning of all line styles used? (e.g. solid, dashed, etc) |

Any "No" under General, or on the relationship-label question, caps Style at 2.

Triage every finding (ported from cheriftj/c4-model-skill):

| Severity | Meaning | Examples |
|---|---|---|
| Blocking | a C4 rule is broken | a Container without technology, bare "Uses" labels, mixed levels, `BiRel` |
| Important | clarity suffers | no legend, no title, container lines without protocol, too dense |
| Nice-to-have | style and consistency | visual order, overflowing labels, naming |

Propose the exact correction for every blocking and important finding.

## Report

Report: the eight scores, the weighted total, one line naming the decisive observation, and
every metric at 2 or less with the element that caused it. Also name the shape the diagram
represents (causal chain, architecture map, pipeline DAG, sequence, timeline, entity schema)
and whether the chosen diagram type fits it.
