// Chimni playground: the real interpreter (src/chimni) running on Pyodide.
"use strict";

const $ = (s) => document.querySelector(s);
const els = {
  example: $("#example"), program: $("#program"), inputs: $("#inputs"), hl: $("#prog-hl"),
  status: $("#status"), run: $("#run"), share: $("#share"), result: $("#result"),
  resultText: $("#result-text"), resultHint: $("#result-hint"), grid: $("#grid"),
  compare: $("#compare-body"), altLang: $("#alt-lang"),
};

let EXAMPLES = [];
let current = null;          // the example last picked
let runPy = null;            // playground.run, once Pyodide is up
let timer = null;

const esc = (s) => s.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");

// ------------------------------------------------------------ highlighting
const CELL_CLASS = { "@": "t-src", "#": "t-grp", "%": "t-grp", "?": "t-flt", "*": "t-pick", "+": "t-agg",
  "~": "t-srt", "_": "t-txt", ";": "t-txt", "^": "t-emit", "'": "t-tie", ".": "t-dot" };

function cellClass(cell) {
  if (cell === ".") return "t-dot";
  if (cell.includes("'") && /^['0-9]/.test(cell)) return "t-tie";
  return CELL_CLASS[cell[0]] || "";
}

function hlCell(cell) {
  const cls = cellClass(cell);
  if (cls === "t-tie" || cls === "t-dot") return `<span class="${cls}">${esc(cell)}</span>`;
  // operator head, then (fields) and [params]
  let out = "", i = 0, head = "";
  while (i < cell.length && !"([".includes(cell[i])) head += cell[i++];
  out += `<span class="${cls}">${esc(head)}</span>`;
  const rest = cell.slice(i);
  out += esc(rest)
    .replace(/(\([^)]*\))/g, '<span class="t-fld">$1</span>')
    .replace(/(\[[^\]]*\])/g, '<span class="t-par">$1</span>')
    .replace(/((?:&gt;|&lt;|[=!])+)(?=<span class="t-par">)/g, `<span class="${cls}">$1</span>`);
  return out;
}

function splitLine(line) {
  // [{text, cell:bool}] keeping whitespace, mirroring the interpreter's split_cells
  const parts = [];
  let cur = "", depth = 0, inq = false, ws = "";
  const flush = () => { if (cur) { parts.push({ text: cur, cell: true }); cur = ""; } };
  for (const ch of line) {
    if (ch === '"') inq = !inq;
    if (!inq && /\s/.test(ch) && depth <= 0) { flush(); ws += ch; continue; }
    if (ws) { parts.push({ text: ws, cell: false }); ws = ""; }
    if (!inq) { if ("([{".includes(ch)) depth++; else if (")]}".includes(ch)) depth--; }
    cur += ch;
  }
  flush();
  if (ws) parts.push({ text: ws, cell: false });
  return parts;
}

// Which source line (0-based) holds grid row r (1-based)?
function lineOfRow(src, r) {
  let seenSig = false, row = 0;
  const lines = src.split("\n");
  for (let i = 0; i < lines.length; i++) {
    const s = lines[i].trim();
    if (!s || s.startsWith("--")) continue;
    if (!seenSig) { seenSig = true; continue; }
    if (++row === r) return i;
  }
  return -1;
}

function highlight(errLine = -1) {
  const src = els.program.value;
  let seenSig = false;
  const html = src.split("\n").map((line, i) => {
    const s = line.trim();
    let body;
    if (!s) body = "";
    else if (s.startsWith("--")) body = `<span class="t-com">${esc(line)}</span>`;
    else if (!seenSig) { seenSig = true; body = `<span class="t-sig">${esc(line)}</span>`; }
    else {
      let comment = false;
      body = splitLine(line).map((p) => {
        if (comment) return `<span class="t-com">${esc(p.text)}</span>`;
        if (!p.cell) return esc(p.text);
        if (p.text === "--") { comment = true; return `<span class="t-com">--</span>`; }
        return hlCell(p.text);
      }).join("");
    }
    return `<span class="ln${i === errLine ? " t-err" : ""}">${body || " "}</span>`;
  }).join("");
  els.hl.innerHTML = html;
  syncScroll();
}

function syncScroll() {
  const pre = els.hl.parentElement;
  pre.scrollTop = els.program.scrollTop;
  pre.scrollLeft = els.program.scrollLeft;
}

// ------------------------------------------------------------- rendering
function render(res, { stale = false } = {}) {
  const src = els.program.value;
  els.result.classList.toggle("error", !res.ok);
  els.result.classList.toggle("stale", stale);
  els.resultText.textContent = res.ok ? res.result : res.error;
  els.resultHint.textContent = stale ? "pre-rendered · Python is loading" :
    res.ok ? "Python repr" : ({ grammar: "caught before running", run: "caught while running", inputs: "check the inputs" }[res.stage] || "");
  highlight(res.row && res.stage !== "inputs" ? lineOfRow(src, res.row) : -1);
  renderGrid(res);
}

function renderGrid(res) {
  const rows = res.rows || [];
  if (!rows.length) {
    els.grid.style.gridTemplateColumns = "";
    els.grid.innerHTML = `<p class="hint">${res.stage === "grammar" ? "Fix the grammar error to see the dataflow." : "Nothing to show yet."}</p>`;
    return;
  }
  const width = Math.max(...rows.map((r) => r.length));
  const outs = new Map(res.trace.map((t) => [`${t.r},${t.c}`, t.out]));
  els.grid.style.gridTemplateColumns = `repeat(${width}, max-content)`;
  let html = "";
  rows.forEach((row, ri) => {
    for (let ci = 0; ci < width; ci++) {
      const text = row[ci];
      const arrow = ci === 0 ? "" : `<span class="garrow">${text !== undefined && text !== "." ? "→" : ""}</span>`;
      if (text === undefined) { html += `<div class="gcell">${arrow}<div class="gpad"></div></div>`; continue; }
      const key = `${ri + 1},${ci + 1}`;
      const isErr = !res.ok && res.row === ri + 1 && res.col === ci + 1;
      const ran = outs.has(key);
      const cls = ["gbox", cellClass(text) === "t-tie" ? "tie" : "", text === "." ? "empty" : "",
        text.startsWith("^") ? "emit" : "", isErr ? "err" : "", !ran && !isErr ? "skipped" : ""].join(" ");
      const val = isErr ? "✕ error here" : text === "." ? "" : ran ? outs.get(key) : "";
      html += `<div class="gcell">${arrow}<div class="${cls}" title="${esc(val)}"><div class="code">${hlCell(text)}</div><div class="val">${esc(val)}</div></div></div>`;
    }
  });
  els.grid.innerHTML = html;
}

function renderCompare(ex) {
  els.altLang.textContent = ex.alt.lang;
  const s = ex.size, unit = s.py_tokens !== undefined ? "tokens" : "chars";
  const n = (k) => `${s[k + "_lines"]} lines · ${s[k + "_" + unit]} ${unit}`;
  const block = (title, k, code) =>
    `<div class="cmp-col"><h4>${title}<span>${n(k)}</span></h4><pre>${esc(code.trimEnd())}</pre></div>`;
  els.compare.innerHTML =
    block(ex.alt.lang, "alt", ex.alt.code) +
    block("Python", "py", ex.python) +
    `<p class="hint">Chimni: ${n("chimni")} · <a href="https://github.com/prat8897/chimni/blob/main/${ex.alt.file}">${ex.alt.file}</a></p>`;
}

// ----------------------------------------------------------------- running
function runNow() {
  clearTimeout(timer);
  if (!runPy) {
    const pristine = current && els.program.value === current.program && els.inputs.value === current.inputs;
    if (pristine) render(current.prerun, { stale: true });
    else {
      highlight();
      els.result.classList.remove("error");
      els.result.classList.add("stale");
      els.resultText.textContent = "Python is still loading — this run will happen as soon as it's ready.";
      els.resultHint.textContent = "";
    }
    return;
  }
  render(JSON.parse(runPy(els.program.value, els.inputs.value)));
}

function scheduleRun() {
  highlight();
  clearTimeout(timer);
  timer = setTimeout(runNow, 220);
}

function loadExample(ex, { run = true } = {}) {
  current = ex;
  els.example.value = ex.stem;
  els.program.value = ex.program;
  els.inputs.value = ex.inputs;
  renderCompare(ex);
  if (run) runNow();
}

// -------------------------------------------------------------- share links
const b64 = {
  enc: (s) => btoa(String.fromCharCode(...new TextEncoder().encode(s))).replace(/\+/g, "-").replace(/\//g, "_").replace(/=+$/, ""),
  dec: (s) => new TextDecoder().decode(Uint8Array.from(atob(s.replace(/-/g, "+").replace(/_/g, "/")), (c) => c.charCodeAt(0))),
};

function fromHash() {
  const m = location.hash.match(/^#code=(.+)$/);
  if (!m) return false;
  try {
    const { p, i, e } = JSON.parse(b64.dec(m[1]));
    const ex = EXAMPLES.find((x) => x.stem === e) || EXAMPLES[0];
    loadExample(ex, { run: false });
    els.program.value = p;
    els.inputs.value = i;
    runNow();
    return true;
  } catch { return false; }
}

async function share() {
  const code = b64.enc(JSON.stringify({ p: els.program.value, i: els.inputs.value, e: current && current.stem }));
  const url = `${location.origin}${location.pathname}#code=${code}`;
  history.replaceState(null, "", url);
  try { await navigator.clipboard.writeText(url); els.share.textContent = "Copied ✓"; }
  catch { els.share.textContent = "Link in address bar"; }
  setTimeout(() => (els.share.textContent = "Copy link"), 1800);
}

// ------------------------------------------------------------ comparison table
function renderTable() {
  const unit = EXAMPLES[0].size.py_tokens !== undefined ? "tokens" : "chars";
  const key = (k) => `${k}_${unit}`;
  const max = Math.max(...EXAMPLES.map((e) => e.size[key("py")]));
  const tot = (k) => EXAMPLES.reduce((a, e) => a + e.size[k], 0);
  const bars = (s) => ["py", "alt", "ch"].map((k) => {
    const v = s[key(k === "ch" ? "chimni" : k)];
    return `<span class="bar"><i class="${k}" style="width:${(v / max) * 120}px"></i>${v}</span>`;
  }).join("");
  $("#cmp-table thead .bars").firstChild.textContent = unit === "tokens" ? "Tokens " : "Characters ";
  $("#cmp-table tbody").innerHTML = EXAMPLES.map((e) => `
    <tr data-stem="${e.stem}">
      <td><span class="stem">${e.stem}</span><span class="title">${esc(e.title)}</span></td>
      <td class="num">${e.size.py_lines}</td>
      <td><span class="lang ${e.alt.lang}">${e.alt.lang}</span></td>
      <td class="num">${e.size.alt_lines}</td>
      <td class="num">${e.size.chimni_lines}</td>
      <td class="bars">${bars(e.size)}</td>
    </tr>`).join("");
  $("#cmp-table tfoot").innerHTML = `<tr><td>Total</td><td class="num">${tot("py_lines")}</td><td></td>
    <td class="num">${tot("alt_lines")}</td><td class="num">${tot("chimni_lines")}</td>
    <td class="bars">${tot(key("py"))} · ${tot(key("alt"))} · ${tot(key("chimni"))} ${unit}</td></tr>`;
  $("#cmp-foot").textContent = `Lines of code, comments excluded; Chimni's count includes its signature line. ` +
    (unit === "tokens" ? "Tokens are cl100k_base. " : "Characters with whitespace squeezed. ") +
    "Click a row to open it in the playground.";
  $("#cmp-table tbody").addEventListener("click", (ev) => {
    const tr = ev.target.closest("tr[data-stem]");
    if (!tr) return;
    loadExample(EXAMPLES.find((e) => e.stem === tr.dataset.stem));
    $("#play").scrollIntoView();
  });
}

// ------------------------------------------------------------------- boot
function setStatus(state, text) {
  els.status.className = `status ${state}`;
  els.status.querySelector("span").textContent = text;
}

async function bootPython() {
  try {
    const t0 = performance.now();
    const py = await loadPyodide();
    const names = ["py/chimni/__init__.py", "py/chimni/interpreter.py", "playground.py"];
    const files = await Promise.all(names.map(async (f) => {
      const r = await fetch(f);
      if (!r.ok) throw new Error(`could not fetch ${f}`);
      return r.text();
    }));
    py.FS.mkdirTree("/home/pyodide/chimni");
    py.FS.writeFile("/home/pyodide/chimni/__init__.py", files[0]);
    py.FS.writeFile("/home/pyodide/chimni/interpreter.py", files[1]);
    py.FS.writeFile("/home/pyodide/playground.py", files[2]);
    py.runPython("import sys; sys.path.insert(0, '/home/pyodide')");
    runPy = py.pyimport("playground").run;
    const ver = py.runPython("import sys; sys.version.split()[0]");
    setStatus("ready", `Python ${ver} in your browser · ready in ${((performance.now() - t0) / 1000).toFixed(1)}s`);
    els.run.disabled = false;
    runNow();
  } catch (err) {
    console.error(err);
    setStatus("failed", "Couldn't load Python — showing pre-rendered results only");
  }
}

async function main() {
  els.run.disabled = true;
  if (typeof loadPyodide === "function") bootPython();       // start the download first
  else setStatus("failed", "Couldn't reach the Pyodide CDN — showing pre-rendered results only");

  EXAMPLES = await (await fetch("examples.json")).json();
  els.example.innerHTML = EXAMPLES.map((e) => `<option value="${e.stem}">${e.stem.replace("_", " · ").replace(/_/g, " ")}</option>`).join("");
  if (!fromHash()) loadExample(EXAMPLES[0]);
  renderTable();

  els.example.addEventListener("change", () => loadExample(EXAMPLES.find((e) => e.stem === els.example.value)));
  els.program.addEventListener("input", scheduleRun);
  els.inputs.addEventListener("input", scheduleRun);
  els.program.addEventListener("scroll", syncScroll);
  els.run.addEventListener("click", runNow);
  els.share.addEventListener("click", share);
  window.addEventListener("hashchange", fromHash);
  document.querySelectorAll("button.try").forEach((b) => b.addEventListener("click", () => {
    els.program.value = b.dataset.program;
    els.inputs.value = b.dataset.inputs;
    runNow();
    $("#play").scrollIntoView();
  }));

  for (const ta of [els.program, els.inputs]) {
    ta.addEventListener("keydown", (ev) => {
      if (ev.key === "Enter" && (ev.metaKey || ev.ctrlKey)) { ev.preventDefault(); runNow(); return; }
      if (ev.key === "Tab" && !ev.shiftKey) {
        ev.preventDefault();
        document.execCommand("insertText", false, "  ");
      }
    });
  }
}

main();
