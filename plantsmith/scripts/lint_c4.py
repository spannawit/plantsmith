"""C4 rules for lint.py, active only when the source includes the bundled C4 stdlib (`!include <C4/...>`).

Rules (STYLE.md numbers in brackets; the C4 model's notation and review checklist):
  c4-element-incomplete  ERROR  Container*/Component* without alias, name, technology and
                                description; WARN for Person*/System* without a description [11]
  c4-rel-unlabelled      ERROR  a Rel* without a label                              [12]
  c4-birel               ERROR  BiRel*: every C4 line is unidirectional              [12]
  c4-rel-no-tech         WARN   a Rel* between two containers without a technology   [12]
  c4-weak-label          WARN   a one-word Rel* label ("Uses", "Calls", "Reads", ...) [12]
  c4-title-format        WARN   title is not "<Type> diagram for <scope>"            [0]
  c4-mixed-level         ERROR  an element below the level the title names           [13]
  c4-no-legend           ERROR  no SHOW_LEGEND() / SHOW_FLOATING_LEGEND() / legend   [0]
  c4-tag-no-legendtext   WARN   AddElementTag/AddRelTag/AddBoundaryTag without $legendText [9]
  c4-dashed-unmarked     ERROR  a dashed/dotted tag whose $legendText lacks "inferred"
                                or "not stated"                                     [5]
Icon-library rules, active when the source includes `<awslib...>`, `<azure...>` or `<gcp...>`:
  icon-empty-tech        ERROR  an icon macro without a technology (2 args fail to render, `""` prints `[]`)
  icon-group-unlabelled  ERROR  a *Group(...) frame (AWSCloudGroup, VPCGroup, ...) without a label
  icon-provider-mismatch ERROR  a provider library (awslib / azure / gcp) is included but the
                                title and legend never name that provider (no AWS icons on an
                                Azure or GCP platform, and the reverse)
  icon-no-cloud-frame    WARN   awslib service icons but no AWSCloudGroup frame (the services are
                                AWS, so the cloud frame is a stated fact; a one-service sketch may skip it)
Each finding is a (line, severity, rule, message) tuple; lint.py wraps them.
"""
from __future__ import annotations

import re

C4_INCLUDE = re.compile(r"^\s*!include\s+<C4/", re.IGNORECASE | re.MULTILINE)
CALL = re.compile(r"^\s*(\w+)\s*\((.*)\)\s*\{?\s*$")
STYLE_MACRO = re.compile(
    r"^\s*(?:Update\w*Style|Add\w*Tag|Update(?:Legend|Boundary)\w*|SetPropertyHeader|AddProperty"
    r"|AWSGroupColoring|AWSGroupEntity)\s*\(", re.IGNORECASE
)
TITLE_TYPE = re.compile(
    r"^\s*title\s+(system\s+context|context|system\s+landscape|landscape|container|component|deployment|dynamic)"
    r"\s+diagram\s+for\s+\S",
    re.IGNORECASE,
)
CONTAINER = re.compile(r"^Container(?:Db|Queue)?(?:_Ext)?$")
COMPONENT = re.compile(r"^Component(?:Db|Queue)?(?:_Ext)?$")
PERSON_SYSTEM = re.compile(r"^(?:Person|System(?:Db|Queue)?)(?:_Ext)?$")
REL = re.compile(r"^Rel(?:_(?:D|U|L|R|Down|Up|Left|Right|Back|Neighbor|Back_Neighbor))?$")
BIREL = re.compile(r"^BiRel\w*$")
WEAK_LABELS = {"uses", "calls", "reads"}
# The level each title type allows; anything below it is a mixed-level error.
FORBIDDEN_BELOW = {
    "context": (CONTAINER, COMPONENT),
    "landscape": (CONTAINER, COMPONENT),
    "container": (COMPONENT,),
}


def is_c4(text: str) -> bool:
    return bool(C4_INCLUDE.search(text))


def is_style_macro(line: str) -> bool:
    """C4 style macros define colours once, like `<style>` classes (exempt from inline-colour)."""
    return bool(STYLE_MACRO.match(line))


def split_args(raw: str) -> tuple[list[str], dict[str, str]]:
    """Positional args (quotes stripped) and $named args of one macro call."""
    parts, current, quoted, depth = [], "", False, 0
    for char in raw:
        if char == '"':
            quoted = not quoted
        elif not quoted and char == "(":
            depth += 1
        elif not quoted and char == ")":
            depth -= 1
        if char == "," and not quoted and depth == 0:
            parts.append(current.strip())
            current = ""
        else:
            current += char
    if current.strip():
        parts.append(current.strip())
    positional, named = [], {}
    for part in parts:
        match = re.match(r"^\$(\w+)\s*=\s*(.*)$", part)
        if match:
            named[match.group(1).lower()] = match.group(2).strip().strip('"')
        else:
            positional.append(part.strip().strip('"').strip())
    return positional, named


def title_level(title_line: str) -> str:
    match = TITLE_TYPE.match(title_line)
    if not match:
        return ""
    word = match.group(1).lower().split()[-1]
    return word


def c4_findings(numbered_lines: list[tuple[int, str]]) -> list[tuple[int, str, str, str]]:
    """numbered_lines: (line number, text) for code lines below the preamble, comments removed."""
    findings: list[tuple[int, str, str, str]] = []
    containers: set[str] = set()
    calls: list[tuple[int, str, list[str], dict[str, str]]] = []
    title_line, has_legend = (0, ""), False
    for number, text in numbered_lines:
        if re.match(r"^\s*title\b", text, re.IGNORECASE) and not title_line[1]:
            title_line = (number, text)
        if re.match(r"^\s*(?:SHOW_LEGEND|SHOW_FLOATING_LEGEND)\s*\(|^\s*legend\b", text, re.IGNORECASE):
            has_legend = True
        match = CALL.match(text)
        if match:
            positional, named = split_args(match.group(2))
            calls.append((number, match.group(1), positional, named))
            if CONTAINER.match(match.group(1)) and positional:
                containers.add(positional[0])

    level = title_level(title_line[1])
    if title_line[1] and not level:
        findings.append((title_line[0], "WARN", "c4-title-format",
                         'title should read "<Type> diagram for <scope>" (e.g. "Container diagram for Order Sync")'))
    if not has_legend:
        findings.append((1, "ERROR", "c4-no-legend", "add SHOW_LEGEND() at the end: a C4 diagram always has a key"))

    for number, name, positional, named in calls:
        filled = [arg for arg in positional if arg]
        if CONTAINER.match(name) or COMPONENT.match(name):
            if len(filled) < 4:
                findings.append((number, "ERROR", "c4-element-incomplete",
                                 f"{name} needs alias, name, technology and description"))
        elif PERSON_SYSTEM.match(name) and len(filled) < 3:
            findings.append((number, "WARN", "c4-element-incomplete", f"{name} needs a short description"))
        for forbidden in FORBIDDEN_BELOW.get(level, ()):
            if forbidden.match(name):
                findings.append((number, "ERROR", "c4-mixed-level",
                                 f"{name} is below the level of a {level} diagram: one level per diagram"))
        if BIREL.match(name):
            findings.append((number, "ERROR", "c4-birel", "BiRel is not C4: draw two unidirectional Rel lines"))
        elif REL.match(name):
            findings += rel_findings(number, positional, containers)
        if re.match(r"^Add\w*Tag$", name):
            findings += tag_findings(number, named)
    return findings


def rel_findings(number: int, positional: list[str], containers: set[str]) -> list[tuple[int, str, str, str]]:
    label = positional[2] if len(positional) > 2 else ""
    techn = positional[3] if len(positional) > 3 else ""
    if not label:
        return [(number, "ERROR", "c4-rel-unlabelled", "every relationship has a label describing its intent")]
    found = []
    if label.lower().rstrip(".") in WEAK_LABELS or len(label.split()) == 1:
        found.append((number, "WARN", "c4-weak-label",
                      f'"{label}" is one word: describe the intent ("Publishes order events to")'))
    if positional[0] in containers and positional[1] in containers and not techn:
        found.append((number, "WARN", "c4-rel-no-tech", "a container-to-container line names its protocol or technology"))
    return found


ICON_INCLUDE = re.compile(r"^\s*!include\s+<(?:awslib|azure|gcp)", re.IGNORECASE | re.MULTILINE)
NOT_AN_ICON = re.compile(
    r"^(?:Bi)?Rel|^Lay_|^(?:Person|System|Container|Component|Boundary|Enterprise|Deployment|Node)"
    r"|^(?:Add|Update|Set|SHOW|LAYOUT|HIDE)",
    re.IGNORECASE,
)


PROVIDERS = (  # (library include prefix, words that name the provider in a title or legend)
    ("awslib", re.compile(r"\bAWS\b|\bAmazon\b", re.IGNORECASE)),
    ("azure", re.compile(r"\bAzure\b", re.IGNORECASE)),
    ("gcp", re.compile(r"\bGCP\b|\bGoogle Cloud\b", re.IGNORECASE)),
)


def provider_findings(text: str, title_and_legend: str) -> list[tuple[int, str, str, str]]:
    """Every provider whose icon library is included is named in the title or the legend."""
    findings = []
    for prefix, names in PROVIDERS:
        include = re.search(rf"^\s*!include\s+<{prefix}", text, re.IGNORECASE | re.MULTILINE)
        if include and not names.search(title_and_legend):
            line = text[:include.start()].count("\n") + 1
            findings.append((line, "ERROR", "icon-provider-mismatch",
                             f"<{prefix}...> icons are included but the title and legend never name that provider: "
                             "use the icons of the provider the sources name"))
    return findings


def is_icon_lib(text: str) -> bool:
    return bool(ICON_INCLUDE.search(text))


def icon_findings(numbered_lines: list[tuple[int, str]]) -> list[tuple[int, str, str, str]]:
    findings: list[tuple[int, str, str, str]] = []
    texts = "\n".join(text for _, text in numbered_lines)
    services = [number for number, text in numbered_lines
                if (m := CALL.match(text)) and not NOT_AN_ICON.match(m.group(1)) and not m.group(1).endswith("Group")
                and not m.group(1).startswith("AWSGroup")]
    if services and "!include <awslib" in texts.lower() and not re.search(r"^\s*AWSCloudGroup\s*\(", texts, re.M):
        findings.append((services[0], "WARN", "icon-no-cloud-frame",
                         "AWS service icons without an AWSCloudGroup frame: the services are AWS, draw the frame"))
    for number, text in numbered_lines:
        match = CALL.match(text)
        if not match or NOT_AN_ICON.match(match.group(1)) or match.group(1).startswith("AWSGroup"):
            continue
        name, (positional, _) = match.group(1), split_args(match.group(2))
        if name.endswith("Group"):
            if len(positional) < 2 or not positional[1]:
                findings.append((number, "ERROR", "icon-group-unlabelled",
                                 f"{name} frame needs its label (the cloud, region, VPC, AZ or subnet name)"))
        elif len(positional) < 3 or not positional[2]:
            findings.append((number, "ERROR", "icon-empty-tech",
                             f'{name} needs its technology ("PostgreSQL"): 2 args fail, an empty one prints "[]"'))
    return findings


def tag_findings(number: int, named: dict[str, str]) -> list[tuple[int, str, str, str]]:
    legend = named.get("legendtext", "")
    if not legend:
        return [(number, "WARN", "c4-tag-no-legendtext", "give the tag a $legendText so SHOW_LEGEND() lists it")]
    style = named.get("linestyle", "").lower()
    if ("dashed" in style or "dotted" in style) and not re.search(r"inferred|not stated", legend, re.IGNORECASE):
        return [(number, "ERROR", "c4-dashed-unmarked",
                 'a dashed or dotted line means "inferred / not stated": say so in its $legendText')]
    return []
