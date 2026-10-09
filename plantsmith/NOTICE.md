# Notice

This skill is MIT licensed (see `LICENSE`). It ports ideas, not code, from the projects
below. No source file was copied; the wording here is new.

| Project | Licence | What was ported |
|---|---|---|
| [Agents365-ai/365-skills](https://github.com/Agents365-ai/365-skills), `plugins/plantuml` | MIT, Copyright (c) 2026 Agents365-ai | The render, validate, look loop: check image magic bytes and size instead of trusting the exit, retry up to 3 times simplifying one step at a time, a vision self-check of the PNG, and "report which backend rendered; never fall back silently". |
| [microsoft/amplifier-bundle-dot-graph](https://github.com/microsoft/amplifier-bundle-dot-graph) | MIT, Copyright (c) Microsoft Corporation | "No diagram without a title, no colour without a legend"; a fixed shape vocabulary with one meaning per shape; review by a separate reviewer against written criteria. |
| [Dynokostya/just-works](https://github.com/Dynokostya/just-works), `.claude/skills/plantuml-diagramming` | Apache-2.0 | PlantUML `<style>` blocks over `skinparam` for colour; declare sequence participants first, in display order; no inline colours on elements; every diagram has a title; `autonumber` with an explicit format. |
| [C4 model](https://c4model.com) (Simon Brown), pages diagrams/notation and diagrams/checklist | CC BY 4.0 | Rules paraphrased into lint and rubric checks (title format, a key, typed and described elements, technology on containers, unidirectional intent labels, one level per diagram); the 21 review-checklist questions are quoted in `RUBRIC.md`. |
| [C4-PlantUML](https://github.com/plantuml-stdlib/C4-PlantUML) (Ricardo Niepel, kirchsth and contributors) | MIT | Used via the PlantUML stdlib (`!include <C4/...>`, C4 2.13.0); not copied. |
| [cheriftj/c4-model-skill](https://github.com/cheriftj/c4-model-skill) (Cherif Toujeni) | MIT | Ported: the weak-label ban ("Uses" alone is not a label) and the blocking / important / nice-to-have triage of review findings. |
| [awslabs/aws-icons-for-plantuml](https://github.com/awslabs/aws-icons-for-plantuml) | Icons: CC-BY-ND 2.0 (`LICENSE`); code: MIT (`LICENSE-CODE`), per its README "License Summary" | Used via the PlantUML stdlib (`!include <awslib20/...>`, v20.0); icons are referenced, never copied or modified. |
| [Azure-PlantUML](https://github.com/plantuml-stdlib/Azure-PlantUML) (Ricardo Niepel and contributors) | MIT (upstream `LICENSE`) | Used via the PlantUML stdlib (`!include <azure/...>`, 2.2.0); not copied. |
| [PlantUML-icons-GCP](https://github.com/Crashedmind/PlantUML-icons-GCP) | No licence file in the upstream repository (GitHub reports none); its README says the generator is based on awslabs/aws-icons-for-plantuml | Used via the PlantUML stdlib (`!include <gcp/...>`, 6.0.0); not copied. |
| [jgraph/drawio-diagrams](https://github.com/jgraph/drawio-diagrams), templates/ (branch dev) | Apache-2.0 (LICENSE names no copyright holder; repository owner jgraph) | Conventions only, paraphrased: role/product labels, numbered step badges with a step list, swatch legend, frame kind by border style, one edge style per diagram, title-bar format. No template XML, shape, icon or image copied. |

The Apache-2.0 project ships no NOTICE file of its own; this entry records the attribution.
The Azure and GCP icon libraries are used by `examples/azure-data-platform` and `examples/gcp-data-platform`.
