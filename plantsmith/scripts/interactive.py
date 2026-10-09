"""The interactive layers shared by exhibit.py (html-plan) and publish.py (standalone page).

CSS layer (always works, no script needed): hovering an element or group highlights it and
every line that starts or ends at it, everything else dims to 35 %; `<title>` tooltips.
JS layer (inline, no network): drag to pan, wheel or pinch to zoom, double-click to reset,
click for a sticky highlight, buttons for zoom, reset, the legend and a full-screen overlay. Stdlib only.
"""
from __future__ import annotations

import hashlib
import re
from html import escape

DIM = 0.35


def svg_id(seed: str) -> str:
    return "ps-" + hashlib.sha1(seed.encode("utf-8")).hexdigest()[:8]


def css_layer(sid: str, nodes: list[str]) -> str:
    """Scoped to the SVG id; per-node rules use the `~` sibling combinator (PlantUML writes
    clusters, then elements, then links as siblings), so no `:has()` is needed."""
    rules = [
        f"#{sid} g[data-ref]{{transition:opacity .15s}}",
        f"#{sid}:hover g[data-ref]{{opacity:{DIM}}}",
        f"#{sid} g[data-ref]:hover{{opacity:1}}",
    ]
    rules += [
        f'#{sid} g[data-ref="{n}"]:hover ~ g[data-from="{n}"],#{sid} g[data-ref="{n}"]:hover ~ g[data-to="{n}"]{{opacity:1}}'
        for n in nodes
    ]
    rules += [
        f"#{sid}.ps-focus g[data-ref]:not(.ps-on){{opacity:{DIM}}}",
        f"#{sid} g[data-ref].ps-on{{opacity:1}}",
        f"#{sid} g.link:hover path,#{sid} g.link.ps-on path{{stroke-width:2.5px}}",
        f"#{sid}.ps-nolegend g.legend{{display:none}}",
        f"#{sid}.ps-js{{cursor:grab;touch-action:none}}",
        ".ps-bar{display:flex;gap:4px;justify-content:flex-end;margin:0 0 4px}",
        ".ps-bar button{font:12px/1 system-ui,sans-serif;padding:4px 8px;border:1px solid #c9c5bc;"
        "border-radius:5px;background:#fff;color:#1b1a18;cursor:pointer}",
    ]
    return "<style>\n" + "\n".join(rules) + "\n</style>"


def toolbar(sid: str) -> str:
    buttons = (("in", "+", "Zoom in"), ("out", "−", "Zoom out"), ("reset", "Reset", "Reset view"),
               ("legend", "Legend", "Show or hide the legend"), ("full", "⛶ Full screen", "Open the diagram full screen (Esc closes)"))
    return f'<div class="ps-bar" data-for="{sid}">' + "".join(
        f'<button type="button" data-act="{act}" title="{tip}">{label}</button>' for act, label, tip in buttons
    ) + "</div>"


JS = r"""(function () {
  var ID = "__ID__", WHEEL_NEEDS_MODIFIER = __MOD__;
  function find() {
    var s = document.getElementById(ID); if (s && !s.__ps) return s;
    var all = document.querySelectorAll("*");
    for (var i = 0; i < all.length; i++) {
      var r = all[i].shadowRoot; if (!r) continue;
      var t = r.getElementById(ID); if (t && !t.__ps) return t;
    }
    return null;
  }
  var svg = find(); if (!svg) return; svg.__ps = true;
  svg.classList.add("ps-js");
  var root = svg.getRootNode();
  var vb0 = svg.getAttribute("viewBox").split(/[\s,]+/).map(Number), vb = vb0.slice();
  svg.__psVB0 = vb0.join(" ");
  function setVB() { svg.setAttribute("viewBox", vb.join(" ")); }
  var groups = svg.querySelectorAll("g[data-ref]"), links = svg.querySelectorAll("g[data-from]");
  function related(ref) {
    var on = {}; on[ref] = 1;
    for (var i = 0; i < links.length; i++) {
      var l = links[i];
      if (l.getAttribute("data-from") === ref || l.getAttribute("data-to") === ref || l.getAttribute("data-ref") === ref) {
        on[l.getAttribute("data-ref")] = 1; on[l.getAttribute("data-from")] = 1; on[l.getAttribute("data-to")] = 1;
      }
    }
    return on;
  }
  var sticky = null;
  function focus(ref) {
    var on = ref ? related(ref) : {};
    svg.classList.toggle("ps-focus", !!ref);
    for (var i = 0; i < groups.length; i++) groups[i].classList.toggle("ps-on", !!on[groups[i].getAttribute("data-ref")]);
  }
  function refAt(e) { var g = e.target.closest ? e.target.closest("g[data-ref]") : null; return g ? g.getAttribute("data-ref") : null; }
  svg.addEventListener("mouseover", function (e) { if (!sticky) focus(refAt(e)); });
  svg.addEventListener("mouseleave", function () { if (!sticky) focus(null); });
  function zoom(f, cx, cy) {
    var r = svg.getBoundingClientRect(); if (!r.width) return;
    var px = cx === undefined ? 0.5 : (cx - r.left) / r.width, py = cy === undefined ? 0.5 : (cy - r.top) / r.height;
    var x = vb[0] + px * vb[2], y = vb[1] + py * vb[3];
    vb[2] *= f; vb[3] *= f; vb[0] = x - px * vb[2]; vb[1] = y - py * vb[3]; setVB();
  }
  function reset() { vb = vb0.slice(); setVB(); sticky = null; focus(null); }
  var ptrs = {}, drag = null, moved = 0, pinch = 0;
  svg.addEventListener("pointerdown", function (e) {
    ptrs[e.pointerId] = { x: e.clientX, y: e.clientY }; moved = 0;
    if (Object.keys(ptrs).length === 1) drag = { x: e.clientX, y: e.clientY, vb: vb.slice() };
    svg.setPointerCapture(e.pointerId);
  });
  svg.addEventListener("pointermove", function (e) {
    if (!ptrs[e.pointerId]) return;
    ptrs[e.pointerId] = { x: e.clientX, y: e.clientY };
    var ids = Object.keys(ptrs);
    if (ids.length === 2) {
      var a = ptrs[ids[0]], b = ptrs[ids[1]], d = Math.hypot(a.x - b.x, a.y - b.y);
      if (pinch) zoom(pinch / d, (a.x + b.x) / 2, (a.y + b.y) / 2);
      pinch = d; moved = 99; drag = null; return;
    }
    if (!drag) return;
    var r = svg.getBoundingClientRect(), k = vb[2] / r.width;
    moved = Math.max(moved, Math.abs(e.clientX - drag.x) + Math.abs(e.clientY - drag.y));
    vb[0] = drag.vb[0] - (e.clientX - drag.x) * k; vb[1] = drag.vb[1] - (e.clientY - drag.y) * k; setVB();
  });
  function up(e) { delete ptrs[e.pointerId]; if (Object.keys(ptrs).length < 2) pinch = 0; if (!Object.keys(ptrs).length) drag = null; }
  svg.addEventListener("pointerup", up); svg.addEventListener("pointercancel", up);
  svg.addEventListener("click", function (e) {
    if (moved > 3) { e.stopPropagation(); e.preventDefault(); return; }
    var ref = refAt(e); sticky = ref && ref !== sticky ? ref : null; focus(sticky);
  });
  svg.addEventListener("dblclick", function (e) { e.preventDefault(); reset(); });
  svg.addEventListener("wheel", function (e) {
    if (WHEEL_NEEDS_MODIFIER && !(e.ctrlKey || e.metaKey)) return;
    e.preventDefault(); zoom(e.deltaY < 0 ? 0.9 : 1.1, e.clientX, e.clientY);
  }, { passive: false });
  // Full screen: a clone of the SVG in a viewport overlay on document.body (outside any shadow
  // root), with its own pan/zoom (wheel needs no modifier there), legend toggle and close.
  function panzoom(el) {
    var v0 = el.getAttribute("viewBox").split(/[\s,]+/).map(Number), v = v0.slice();
    function set() { el.setAttribute("viewBox", v.join(" ")); }
    function z(f, cx, cy) {
      var r = el.getBoundingClientRect(); if (!r.width) return;
      var px = cx === undefined ? 0.5 : (cx - r.left) / r.width, py = cy === undefined ? 0.5 : (cy - r.top) / r.height;
      var x = v[0] + px * v[2], y = v[1] + py * v[3];
      v[2] *= f; v[3] *= f; v[0] = x - px * v[2]; v[1] = y - py * v[3]; set();
    }
    var d = null;
    el.addEventListener("pointerdown", function (e) { d = { x: e.clientX, y: e.clientY, v: v.slice() }; el.setPointerCapture(e.pointerId); });
    el.addEventListener("pointermove", function (e) {
      if (!d) return; var r = el.getBoundingClientRect(), k = v[2] / r.width;
      v[0] = d.v[0] - (e.clientX - d.x) * k; v[1] = d.v[1] - (e.clientY - d.y) * k; set();
    });
    function stop() { d = null; }
    el.addEventListener("pointerup", stop); el.addEventListener("pointercancel", stop);
    el.addEventListener("wheel", function (e) { e.preventDefault(); z(e.deltaY < 0 ? 0.9 : 1.1, e.clientX, e.clientY); }, { passive: false });
    el.addEventListener("dblclick", function (e) { e.preventDefault(); v = v0.slice(); set(); });
    return { zoom: z, reset: function () { v = v0.slice(); set(); } };
  }
  function fullScreen() {
    var old = document.getElementById(ID + "-full-overlay"); if (old) old.remove();
    var ov = document.createElement("div"); ov.id = ID + "-full-overlay";
    ov.setAttribute("style", "position:fixed;inset:0;z-index:2147483000;background:rgba(20,19,17,.92);display:flex;flex-direction:column;");
    var top = document.createElement("div");
    top.setAttribute("style", "display:flex;gap:6px;justify-content:flex-end;padding:10px 14px;");
    var mk = function (label, tip) { var b = document.createElement("button"); b.type = "button"; b.textContent = label; b.title = tip;
      b.setAttribute("style", "font:13px/1 system-ui,sans-serif;padding:6px 10px;border:1px solid #777;border-radius:6px;background:#fff;color:#1b1a18;cursor:pointer"); return b; };
    var bIn = mk("+", "Zoom in"), bOut = mk("−", "Zoom out"), bReset = mk("Reset", "Reset view"), bLeg = mk("Legend", "Show or hide the legend"), bClose = mk("✕ Close", "Close (Esc)");
    [bIn, bOut, bReset, bLeg, bClose].forEach(function (b) { top.appendChild(b); });
    var stage = document.createElement("div"); stage.setAttribute("style", "flex:1;min-height:0;padding:0 14px 14px;");
    var clone = svg.cloneNode(true); clone.id = ID + "-full"; clone.classList.remove("ps-js", "ps-focus", "ps-nolegend");
    clone.setAttribute("viewBox", svg.__psVB0); clone.setAttribute("style", "width:100%;height:100%;display:block;background:#fff;border-radius:8px;cursor:grab;touch-action:none");
    clone.querySelectorAll("g[data-ref].ps-on").forEach(function (g) { g.classList.remove("ps-on"); });
    var st = root.querySelector ? root.querySelector("style") : null;
    if (st) { var s2 = document.createElement("style"); s2.textContent = st.textContent.split("#" + ID).join("#" + ID + "-full"); ov.appendChild(s2); }
    stage.appendChild(clone); ov.appendChild(top); ov.appendChild(stage); document.body.appendChild(ov);
    var pz = panzoom(clone);
    function close() { ov.remove(); document.removeEventListener("keydown", onKey); }
    function onKey(e) { if (e.key === "Escape") close(); }
    document.addEventListener("keydown", onKey);
    bIn.addEventListener("click", function () { pz.zoom(0.8); }); bOut.addEventListener("click", function () { pz.zoom(1.25); });
    bReset.addEventListener("click", pz.reset); bLeg.addEventListener("click", function () { clone.classList.toggle("ps-nolegend"); });
    bClose.addEventListener("click", close);
    ov.addEventListener("click", function (e) { if (e.target === ov || e.target === stage) close(); });
  }
  var bar = root.querySelector ? root.querySelector('.ps-bar[data-for="' + ID + '"]') : null;
  if (bar) bar.addEventListener("click", function (e) {
    var b = e.target.closest("button"); if (!b) return; e.stopPropagation();
    var act = b.getAttribute("data-act");
    if (act === "in") zoom(0.8); else if (act === "out") zoom(1.25); else if (act === "reset") reset();
    else if (act === "legend") svg.classList.toggle("ps-nolegend"); else if (act === "full") fullScreen();
  });
  svg.__psReset = reset;
})();"""


def js_layer(sid: str, wheel_needs_modifier: bool) -> str:
    return JS.replace("__ID__", sid).replace("__MOD__", "true" if wheel_needs_modifier else "false")


def title_for(words: str, kind: str, ends: tuple[str, str] | None, line: str | None, puml_lines: int, puml_name: str) -> str:
    """Tooltip text: the element's own words (name, technology, description); a link says where
    it goes; the .puml line when the caller passed the source and the line is inside it."""
    text = words
    if kind == "link" and ends:
        text = f"{ends[0]} → {ends[1]}" + (f": {words}" if words else "")
    if line and puml_lines and line.isdigit() and int(line) <= puml_lines:
        text += f" ({puml_name}:{line})"
    return escape(text, quote=False)


def page(title: str, svg: str, css: str, bar: str, js: str) -> str:
    """The standalone page: the diagram on a white card, page chrome light or dark."""
    t = escape(title)
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{t}</title>
<style>
:root{{--bg:#f6f5f2;--fg:#1b1a18;--muted:#6b675e;--line:#d9d6cf}}
@media (prefers-color-scheme: dark){{:root:not([data-theme="light"]){{--bg:#17161a;--fg:#e6e3dc;--muted:#a19d94;--line:#3a3840}}}}
:root[data-theme="dark"]{{--bg:#17161a;--fg:#e6e3dc;--muted:#a19d94;--line:#3a3840}}
body{{margin:0;background:var(--bg);color:var(--fg);font:14px/1.45 system-ui,-apple-system,"Segoe UI",sans-serif}}
header{{display:flex;flex-wrap:wrap;gap:8px;align-items:center;padding:12px 16px}}
header h1{{font-size:16px;margin:0 auto 0 0}}
header button{{font:13px/1 system-ui,sans-serif;padding:6px 10px;border:1px solid var(--line);border-radius:6px;background:transparent;color:var(--fg);cursor:pointer}}
.card{{margin:0 16px 16px;background:#fff;border:1px solid var(--line);border-radius:8px;overflow:hidden;height:calc(100vh - 110px);min-height:320px}}
.card .ps-bar{{display:none}}
.card svg{{width:100%;height:100%;display:block}}
footer{{margin:0 16px 16px;color:var(--muted);font-size:12px}}
</style>
</head>
<body>
<header><h1>{t}</h1>
<button type="button" data-act="in" title="Zoom in">+</button>
<button type="button" data-act="out" title="Zoom out">&minus;</button>
<button type="button" data-act="reset" title="Reset view">Reset</button>
<button type="button" data-act="legend" title="Show or hide the legend">Legend</button>
<button type="button" id="ps-theme" title="Light or dark page">Theme</button>
<button type="button" id="ps-png" title="Download the diagram as PNG">PNG</button>
</header>
<main class="card">
{css}
{bar}
{svg}
</main>
<footer>Drag to pan, wheel or pinch to zoom, double-click to reset, click an element to keep it highlighted. Hover shows the element's details.</footer>
<script>
{js}
</script>
<script>
(function () {{
  var svg = document.querySelector("main.card svg"), bar = document.querySelector(".card .ps-bar");
  document.querySelectorAll("header button[data-act]").forEach(function (b) {{
    b.addEventListener("click", function () {{ var t = bar.querySelector('[data-act="' + b.getAttribute("data-act") + '"]'); if (t) t.click(); }});
  }});
  document.getElementById("ps-theme").addEventListener("click", function () {{
    var r = document.documentElement, dark = r.dataset.theme ? r.dataset.theme === "dark" : matchMedia("(prefers-color-scheme: dark)").matches;
    r.dataset.theme = dark ? "light" : "dark";
  }});
  document.getElementById("ps-png").addEventListener("click", function () {{
    var clone = svg.cloneNode(true), vb = (svg.__psVB0 || svg.getAttribute("viewBox")).split(/[\\s,]+/).map(Number);
    clone.setAttribute("viewBox", vb.join(" ")); clone.setAttribute("width", vb[2]); clone.setAttribute("height", vb[3]);
    clone.removeAttribute("style"); clone.classList.remove("ps-focus", "ps-nolegend");
    var url = "data:image/svg+xml;charset=utf-8," + encodeURIComponent(new XMLSerializer().serializeToString(clone));
    var img = new Image();
    img.onload = function () {{
      var c = document.createElement("canvas"); c.width = vb[2] * 2; c.height = vb[3] * 2;
      var g = c.getContext("2d"); g.fillStyle = "#fff"; g.fillRect(0, 0, c.width, c.height); g.drawImage(img, 0, 0, c.width, c.height);
      c.toBlob(function (blob) {{ var a = document.createElement("a"); a.href = URL.createObjectURL(blob); a.download = document.title.replace(/[^\\w.-]+/g, "-") + ".png"; a.click(); }});
    }};
    img.src = url;
  }});
  document.documentElement.dataset.psReady = "1";
}})();
</script>
</body>
</html>
"""
