/* Agentic Decision Mathematics ‚Äî client.
   Every number rendered here comes from the Flask engine; the browser only draws. */
(() => {
  "use strict";

  // ---------------------------------------------------------------- helpers
  const $ = (s, r = document) => r.querySelector(s);
  const $$ = (s, r = document) => Array.from(r.querySelectorAll(s));
  const esc = (s) => String(s ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", "'": "&#39;" }[c]));
  const pct = (v, d = 1) => (v == null ? "‚Äî" : `${(v * 100).toFixed(d)}%`);
  const num = (v, d = 2) => (v == null ? "‚Äî" : Number(v).toLocaleString("en-GB", { minimumFractionDigits: d, maximumFractionDigits: d }));
  const eur = (v) => (v == null ? "‚Äî" : `‚Ç¨${Math.round(v).toLocaleString("en-GB")}`);
  const signed = (v, d = 0) => `${v >= 0 ? "+" : "‚àí"}${Math.abs(v * 100).toFixed(d)}%`;
  const lv = (name) => `<span class="lv lv-${esc(name)}">${esc(name)}</span>`;
  const tex = (t, display = false) => `<span class="tex" data-tex="${esc(t)}" data-display="${display}"></span>`;
  const eq = (t, note = "") => `<div class="eq">${tex(t, true)}</div>${note ? `<div class="eq-note">${note}</div>` : ""}`;
  const debounce = (fn, ms) => { let id; return (...a) => { clearTimeout(id); id = setTimeout(() => fn(...a), ms); }; };

  const LEVEL_COLOR = { AUTO: "#0e7c66", APPROVE: "#b7791f", PROPOSE: "#5b5ba8", HUMAN: "#6b7280", DENY: "#b42318" };
  const ACTION_COLOR = {
    REPAIR_SSI: "#2f6690", REQUEST_CPTY: "#4f7f52", REPAIR_PSET: "#7b4b94", WAIT: "#9aa5b1", BORROW: "#c0763a",
    FUND: "#c9a227", AMEND_ECON: "#a23b72", CANCEL_REBOOK: "#6b2737", ESCALATE: "#34425a",
  };
  const LAMBDA_TEX = { C: "\\lambda_C", R: "\\lambda_R", T: "\\lambda_T", H: "\\lambda_H", F: "\\lambda_F", K: "\\lambda_K" };

  function renderMath(root) {
    $$(".tex", root).forEach((el) => {
      if (window.katex) {
        try {
          window.katex.render(el.dataset.tex, el, { displayMode: el.dataset.display === "true", throwOnError: false });
        } catch (e) { el.textContent = el.dataset.tex; }
      } else {
        el.textContent = el.dataset.tex;
      }
    });
  }

  async function api(path, body) {
    const opts = body === undefined ? {} : { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) };
    const r = await fetch(path, opts);
    const d = await r.json().catch(() => ({}));
    if (!r.ok) throw new Error(d.error || r.statusText);
    return d;
  }

  async function load(target, fn) {
    target.innerHTML = `<div class="loading">Computing‚Ä¶</div>`;
    try {
      target.innerHTML = await fn();
      renderMath(target);
    } catch (e) {
      target.innerHTML = `<p class="error">Could not compute: ${esc(e.message)}</p>`;
    }
  }

  // tooltips: any element with data-tip
  const tip = $("#tooltip");
  document.addEventListener("mousemove", (e) => {
    const t = e.target.closest && e.target.closest("[data-tip]");
    if (!t) { tip.style.display = "none"; return; }
    tip.innerHTML = t.dataset.tip;
    tip.style.display = "block";
    const x = Math.min(e.clientX + 14, window.innerWidth - tip.offsetWidth - 8);
    tip.style.left = `${x}px`;
    tip.style.top = `${e.clientY + 14}px`;
  });

  // ---------------------------------------------------------------- state
  const S = {
    cat: null,
    lambdas: null,
    mode: "cvar",
    agent: "B",
    caseId: "EXC-48291",
    rnd: 1,
    sens: { caseId: "EXC-49872", x: "F", y: "H", span: 3, res: 17 },
    sav: { agent: "B", budget: 0.1, target: 0.25 },
    proof: { n: 300, seed: 11 },
    bench: { n: 2000, seed: 2026, result: null, mapping: null },
    frontierAgent: "B",
  };

  function sliders(prefix, onInput) {
    return `<div class="sliders">${Object.entries(S.cat.lambdas).map(([k, label]) => `
      <div class="slider-row">
        <label for="${prefix}-${k}">${esc(label)} ${tex(LAMBDA_TEX[k])}</label>
        <output id="${prefix}-${k}-out">${num(S.lambdas[k])}</output>
        <input type="range" id="${prefix}-${k}" data-k="${k}" min="0" max="3" step="0.05" value="${S.lambdas[k]}">
      </div>`).join("")}</div>
      <div class="controls" style="margin-top:10px">${Object.keys(S.cat.presets).map((p) => `<button class="btn ghost small" data-preset="${p}">${p}</button>`).join("")}
      <button class="btn ghost small" data-preset="__default">Default</button></div>`;
  }

  function wireSliders(root, prefix, onChange) {
    $$(`input[type=range][id^="${prefix}-"]`, root).forEach((inp) => {
      inp.addEventListener("input", () => {
        S.lambdas[inp.dataset.k] = parseFloat(inp.value);
        $(`#${prefix}-${inp.dataset.k}-out`, root).textContent = num(S.lambdas[inp.dataset.k]);
        onChange();
      });
    });
    $$("[data-preset]", root).forEach((b) => b.addEventListener("click", () => {
      const p = b.dataset.preset === "__default" ? S.cat.default_lambdas : S.cat.presets[b.dataset.preset];
      S.lambdas = { ...p };
      Object.entries(S.lambdas).forEach(([k, v]) => {
        const inp = $(`#${prefix}-${k}`, root);
        if (inp) { inp.value = v; $(`#${prefix}-${k}-out`, root).textContent = num(v); }
      });
      onChange();
    }));
  }

  const agentSelect = (id, value) => `<select id="${id}">${S.cat.agents.map((a) => `<option value="${a.code}" ${a.code === value ? "selected" : ""}>${esc(a.name)}</option>`).join("")}</select>`;
  const segmented = (id, options, value) => `<div class="seg" id="${id}" role="group">${options.map(([v, l]) => `<button type="button" data-v="${v}" aria-pressed="${v === value}">${esc(l)}</button>`).join("")}</div>`;
  function wireSeg(root, id, fn) {
    $$(`#${id} button`, root).forEach((b) => b.addEventListener("click", () => {
      $$(`#${id} button`, root).forEach((x) => x.setAttribute("aria-pressed", String(x === b)));
      fn(b.dataset.v);
    }));
  }

  // ---------------------------------------------------------------- charts
  function lineChart({ w = 680, h = 300, series, xd, yd, xFmt, yFmt, xLabel, yLabel, hlines = [], vlines = [] }) {
    const m = { l: 56, r: 16, t: 14, b: 44 };
    const X = (v) => m.l + ((v - xd[0]) / (xd[1] - xd[0])) * (w - m.l - m.r);
    const Y = (v) => h - m.b - ((v - yd[0]) / (yd[1] - yd[0])) * (h - m.t - m.b);
    const ticks = (d, n) => Array.from({ length: n + 1 }, (_, i) => d[0] + (i * (d[1] - d[0])) / n);
    let s = `<svg class="chart" viewBox="0 0 ${w} ${h}" role="img" aria-label="${esc(yLabel)} against ${esc(xLabel)}">`;
    ticks(yd, 5).forEach((t) => { s += `<line x1="${m.l}" x2="${w - m.r}" y1="${Y(t)}" y2="${Y(t)}" stroke="#e2e7ec"/><text x="${m.l - 8}" y="${Y(t) + 4}" font-size="11" text-anchor="end" fill="#7a8799">${yFmt(t)}</text>`; });
    ticks(xd, 6).forEach((t) => { s += `<text x="${X(t)}" y="${h - m.b + 17}" font-size="11" text-anchor="middle" fill="#7a8799">${xFmt(t)}</text>`; });
    s += `<line x1="${m.l}" x2="${w - m.r}" y1="${h - m.b}" y2="${h - m.b}" stroke="#cbd3db"/>`;
    s += `<text x="${(m.l + w - m.r) / 2}" y="${h - 6}" font-size="12" text-anchor="middle" fill="#4b5a70">${esc(xLabel)}</text>`;
    s += `<text transform="translate(14 ${(m.t + h - m.b) / 2}) rotate(-90)" font-size="12" text-anchor="middle" fill="#4b5a70">${esc(yLabel)}</text>`;
    hlines.forEach((l) => { s += `<line x1="${m.l}" x2="${w - m.r}" y1="${Y(l.y)}" y2="${Y(l.y)}" stroke="${l.color}" stroke-dasharray="5 4"/><text x="${w - m.r - 4}" y="${Y(l.y) - 5}" font-size="11" text-anchor="end" fill="${l.color}">${esc(l.label)}</text>`; });
    vlines.forEach((l) => { s += `<line x1="${X(l.x)}" x2="${X(l.x)}" y1="${m.t}" y2="${h - m.b}" stroke="${l.color}" stroke-width="1.5"/><text x="${X(l.x) + 5}" y="${m.t + 11}" font-size="11" fill="${l.color}">${esc(l.label)}</text>`; });
    series.forEach((se) => {
      const d = se.points.map((p, i) => `${i ? "L" : "M"}${X(p[0]).toFixed(1)},${Y(p[1]).toFixed(1)}`).join("");
      s += `<path d="${d}" fill="none" stroke="${se.color}" stroke-width="${se.width || 2}" ${se.dash ? `stroke-dasharray="${se.dash}"` : ""}/>`;
      se.points.forEach((p) => { s += `<circle cx="${X(p[0])}" cy="${Y(p[1])}" r="3" fill="${se.color}" data-tip="${esc(se.tip ? se.tip(p) : "")}"/>`; });
    });
    return s + "</svg>";
  }

  function sparkline(values, { w = 220, h = 42, split, baseline, alarm }) {
    const max = Math.max(...values) * 1.1 || 1;
    const X = (i) => (i / (values.length - 1)) * w;
    const Y = (v) => h - 3 - (v / max) * (h - 6);
    const d = values.map((v, i) => `${i ? "L" : "M"}${X(i).toFixed(1)},${Y(v).toFixed(1)}`).join("");
    let s = `<svg width="${w}" height="${h}" viewBox="0 0 ${w} ${h}" aria-hidden="true">`;
    s += `<rect x="${X(split)}" y="0" width="${w - X(split)}" height="${h}" fill="#dce7f2"/>`;
    s += `<line x1="0" x2="${w}" y1="${Y(baseline)}" y2="${Y(baseline)}" stroke="#7a8799" stroke-dasharray="3 3"/>`;
    s += `<path d="${d}" fill="none" stroke="#15233b" stroke-width="1.4"/>`;
    if (alarm != null) s += `<circle cx="${X(alarm)}" cy="${Y(values[alarm])}" r="3.5" fill="#b42318"/>`;
    return s + "</svg>";
  }

  // ---------------------------------------------------------------- overview
  function viewOverview() {
    const stages = [
      ["Operations data", "Observations", String.raw`O_{1:t},\; r_e`, "arena"],
      ["Control layer", "Belief state", String.raw`b_t(x)=P(x\mid O_{1:t})`, "arena"],
      ["Agent", "Interpretation", String.raw`\hat p(x),\;\Gamma_\alpha(x)`, "frontier", true],
      ["Control layer", "Feasible set", String.raw`A_{\text{safe}}=\{a: g\le 0,\,h=0,\,\varphi\}`, "arena"],
      ["Control layer", "Optimiser", String.raw`a^*=\arg\min_{A_{\text{safe}}} J`, "sensitivity"],
      ["Control layer", "Autonomy", String.raw`\ell=\bigwedge_k \mathrm{cap_k`, "frontier"],
      ["Control layer", "Gate", String.raw`\mathbf{G}(\mathit{Exec}\to\varphi)`, "proof"],
      ["Systems", "Execution", String.raw`H_t=\mathrm{h}(H_{t-1}\Vert e_t)`, "proof"],
    ];
    const levels = ["DENY", "HUMAN", "PROPOSE", "APPROVE", "AUTO"];
    return `
      <section class="hero">
        <h1><span class="line">AI proposes.</span><span class="line">Mathematics decides what is permissible, optimal and sufficiently certain.</span><span class="line">Controls decide whether it executes.</span></h1>
        <p>A decision engine that sits between any agent and securities-operations systems. The agent supplies intelligence; the engine supplies bounds, proof, optimisation and execution authority. Every figure on these screens is computed live from a synthetic population.</p>
      </section>
      <div class="pipeline reveal">${stages.map(([who, name, t, screen, agent]) => `
        <div class="pipe ${agent ? "agent" : ""}"><div class="who">${who}</div><h3>${name}</h3>
          <div class="tex-inline">${tex(t)}</div><a href="#${screen}">Open</a></div>`).join("")}
      </div>
      <p class="small faint" style="margin-top:8px">Only the striped stage is an AI model. Everything else is deterministic and reproducible.</p>

      <div class="section">
        <div class="section-head"><h2>Three kinds of uncertainty, kept separate</h2></div>
        <div class="grid g3">
          <div class="sheet"><h3>State</h3><p class="muted small">What is actually wrong with this trade?</p>${eq(String.raw`b(x)\propto P(x)\prod_e P(o_e\mid x)^{r_e}`, "Evidence reliability tempers each likelihood.")}</div>
          <div class="sheet"><h3>Model</h3><p class="muted small">How far can this agent's interpretation be trusted?</p>${eq(String.raw`P\big(y\in\Gamma_\alpha(x)\big)\ge 1-\alpha`, "Split conformal, per agent and exception class.")}</div>
          <div class="sheet"><h3>Outcome</h3><p class="muted small">What happens if we act?</p>${eq(String.raw`\mathrm{CVaR}_\alpha(L_a)=\mathbb{E}[L_a\mid L_a\ge \mathrm{VaR}_\alpha]`, "Tail loss enters the objective and the feasible set.")}</div>
        </div>
      </div>

      <div class="section">
        <div class="section-head"><h2>The autonomy lattice</h2><span class="small muted">Granted level is the meet of independent caps; each cap can only lower it.</span></div>
        <div class="lattice">${levels.map((l) => `<div>${lv(l)}<p>${esc(S.cat.levels[l])}</p></div>`).join("")}</div>
        <div style="margin-top:12px">${eq(String.raw`\mathrm{AUTOM(a)\iff \mathrm{Safet(a)\land\mathrm{Calibrated}(a)\land\mathrm{Stable}(a)\land\mathrm{Authorised}(a)`)}</div>
      </div>

      <div class="section grid g2">
        <div class="sheet"><h2>Model-independent by design</h2>
          <p class="lede">Any agent (an LLM, a vendor model, a rules engine) submits a proposal. The engine returns the gate decision, the mathematical ceiling, the binding constraints and the regret against the optimum.</p>
          <pre class="snippet">curl -X POST $HOST/api/evaluate \\
  -H "Content-Type: application/json" \\
  -d @proposal.json</pre>
          <p class="small muted">GET <a href="/api/evaluate">/api/evaluate</a> returns an example payload.</p>
        </div>
        <div class="sheet"><h2>How to read the screens</h2>
          <p class="lede">Each result sits next to the equation that produced it. Change a weight, a case or a risk budget and the engine recomputes; nothing is pre-rendered.</p>
          <p class="small muted">Decision Arena compares agents on one case and on a preregistered, blinded population. Autonomy Frontier shows where autonomy is earned. Policy Sensitivity shows which disagreements are about risk appetite. Savings Lab separates minutes removed from people released. Proof &amp; Control replays proposals through the formal invariants.</p>
        </div>
      </div>
      <p class="notice">All data is synthetic and illustrative. Parameters live in <b>engine/config.py</b> and must be replaced with institution data before any operational conclusion is drawn.</p>`;
  }

  // ---------------------------------------------------------------- arena
  function viewArena() {
    return `
      <header class="screen-head"><h1>Decision Arena</h1>
        <p>Three agents read the same operational state. The engine computes the belief, the feasible set and the optimum, then scores each proposal by regret and decides what the gate allows.</p></header>
      <div class="grid g-side">
        <div class="stack">
          <div class="sheet"><h3>Case</h3>
            <div class="case-list" id="case-list">${S.cat.cases.map((c) => `<button type="button" data-id="${c.id}" aria-pressed="${c.id === S.caseId}">${esc(c.title)}<span>${c.id} ¬∑ ${c.cls}</span></button>`).join("")}</div>
            <button class="btn ghost" id="rnd" style="margin-top:10px;width:100%">Draw a random case</button>
          </div>
          <div class="sheet stack">
            <div class="field"><span class="label">Optimisation</span>${segmented("mode", [["expected", "Expected"], ["cvar", "Tail-aware"], ["robust", "Robust"]], S.mode)}</div>
            <div class="field"><label for="op-agent">Autonomy computed for</label>${agentSelect("op-agent", S.agent)}</div>
          </div>
          <div class="sheet"><h3>Priority weights</h3>${sliders("al")}</div>
        </div>
        <div id="arena-out"></div>
      </div>
      <div class="section" id="bench">
        <div class="section-head"><div><h2>Preregistered, blinded benchmark</h2>
          <p class="lede">The manifest is frozen and hashed before scoring. Agent identities stay blinded until the hash is presented.</p></div>
          <div class="controls">
            <div class="field"><label for="b-n">Cases</label><input type="number" id="b-n" min="200" max="5000" step="100" value="${S.bench.n}"></div>
            <div class="field"><label for="b-seed">Seed</label><input type="number" id="b-seed" value="${S.bench.seed}"></div>
            <button class="btn" id="b-run">Freeze manifest and score</button>
          </div></div>
        <div id="bench-out">${S.bench.result ? benchHtml(S.bench.result) : `<p class="muted">Not yet run.</p>`}</div>
      </div>`;
  }

  function wireArena(root) {
    const out = $("#arena-out", root);
    const run = () => load(out, async () => arenaHtml(await api("/api/arena", { case_id: S.caseId, mode: S.mode, lambdas: S.lambdas, operating_agent: S.agent })));
    const runSoon = debounce(run, 250);
    $$("#case-list button", root).forEach((b) => b.addEventListener("click", () => {
      S.caseId = b.dataset.id;
      $$("#case-list button", root).forEach((x) => x.setAttribute("aria-pressed", String(x === b)));
      run();
    }));
    $("#rnd", root).addEventListener("click", () => {
      S.rnd += 1;
      S.caseId = `RND-${S.rnd}`;
      $$("#case-list button", root).forEach((x) => x.setAttribute("aria-pressed", "false"));
      run();
    });
    wireSeg(root, "mode", (v) => { S.mode = v; run(); });
    $("#op-agent", root).addEventListener("change", (e) => { S.agent = e.target.value; run(); });
    wireSliders(root, "al", runSoon);
    $("#b-run", root).addEventListener("click", async (e) => {
      S.bench.n = parseInt($("#b-n", root).value, 10) || 2000;
      S.bench.seed = parseInt($("#b-seed", root).value, 10) || 0;
      e.target.disabled = true;
      await load($("#bench-out", root), async () => {
        S.bench.result = await api("/api/benchmark", { n: S.bench.n, seed: S.bench.seed, lambdas: S.lambdas });
        S.bench.mapping = null;
        return benchHtml(S.bench.result);
      });
      e.target.disabled = false;
      wireBench(root);
    });
    wireBench(root);
    run();
  }

  function arenaHtml(d) {
    const c = d.case;
    const hyp = d.hypotheses;
    const maxB = Math.max(...d.belief, ...d.prior);
    const feasibleJ = d.actions.filter((a) => a.feasible).map((a) => (d.mode === "robust" ? a.J_robust : a.J));
    const maxJ = Math.max(...feasibleJ);
    const jOf = (a) => (d.mode === "robust" ? a.J_robust : a.J);
    const modeTex = {
      expected: String.raw`a^*=\arg\min_{a\in A_{\text{safe}}}\;\mathbb{E}_{x\sim b}\big[J(a\mid x)\big]`,
      cvar: String.raw`a^*=\arg\min_{a\in A_{\text{safe}}}\;\sum_k \lambda_k\,c_k(a),\quad c_K=\mathrm{CVaR}_{0.95}(L_a)/C_{\text{ref}}`,
      robust: String.raw`a^*=\arg\min_{a\in A_{\text{safe}}}\;\max_{x\in S} J\big(a\mid (1-\varepsilon)b+\varepsilon\delta_x\big),\quad S=\Gamma_\alpha\cup\{x:b(x)\ge 0.1\}`,
    }[d.mode];
    return `
      <div class="stack">
        <div class="sheet">
          <div class="case-head"><div><div class="small faint">${esc(c.id)} ¬∑ ${esc(c.cls)}</div><h2>${esc(c.title)}</h2><p class="muted" style="margin:4px 0 0">${esc(c.story)}</p></div>
            ${c.true_state ? `<div><span class="tag">Simulation truth: ${esc(c.true_state)}</span></div>` : ""}</div>
          <div class="facts"><span>Notional <b>‚Ç¨${(c.notional / 1e6).toFixed(1)}m</b></span><span>Cutoff in <b>${num(c.cutoff_h, 1)} h</b></span>
            <span>Handling <b>${c.handling} min</b></span><span>SSI source approved <b>${c.ssi_ok ? "yes" : "no"}</b></span>
            <span>PSET valid <b>${c.pset_ok ? "yes" : "no"}</b></span><span>Original linked <b>${c.linked ? "yes" : "no"}</b></span></div>
        </div>

        <div class="grid g2">
          <div class="sheet"><h3>Evidence</h3>
            <div class="table-wrap"><table><thead><tr><th>Signal</th><th>Observed</th><th class="num">Reliability</th></tr></thead><tbody>
              ${d.evidence.map((e) => `<tr><td>${esc(e.label)}</td><td>${e.observed ? "present" : "absent"}</td><td class="num">${num(e.reliability)}</td></tr>`).join("")}
            </tbody></table></div>
            ${eq(String.raw`b(x)\;\propto\;P(x)\prod_{e} P(o_e\mid x)^{\,r_e}`, "Unobserved signals contribute nothing; lower reliability flattens a likelihood.")}
          </div>
          <div class="sheet"><h3>Belief state</h3>
            ${hyp.map((h, i) => `<div class="belief-row" data-tip="${esc(h.label)}<br>prior ${pct(d.prior[i])} ‚Üí posterior ${pct(d.belief[i])}">
              <span>${esc(h.code)}</span><div class="belief-bars"><span class="post" style="width:${(d.belief[i] / maxB) * 100}%"></span><span class="prior" style="width:${(d.prior[i] / maxB) * 100}%"></span></div><span class="num">${pct(d.belief[i], 0)}</span></div>`).join("")}
            <div class="legend" style="margin:8px 0"><span><i style="background:#15233b"></i>posterior</span><span><i style="background:#7a8799;height:3px"></i>class prior</span></div>
            ${eq(String.raw`U=\frac{H(b)}{\log|X|}=${d.uncertainty.toFixed(3)}`)}
            ${d.mode === "robust" ? `<p class="small muted">Robust set S: ${d.robust_set.map((x) => `<span class="tag">${esc(x)}</span>`).join("")}</p>` : ""}
          </div>
        </div>

        <div class="agents">${d.agents.map((a) => `
          <div class="agent"><h3>${esc(a.name)}</h3><div class="small faint">${esc(a.style)}</div>
            <dl>
              <dt>Proposes</dt><dd class="code">${esc(a.proposal)}</dd>
              <dt>Requests</dt><dd>${lv(a.requested)}</dd>
              <dt>Confidence</dt><dd>${pct(a.stated_confidence, 0)}</dd>
              <dt>Conformal set</dt><dd>${a.conformal_set.map((x) => `<span class="tag">${esc(x)}</span>`).join("")} <span class="faint small">Œ±=${a.alpha}</span></dd>
              <dt>Gate</dt><dd>${a.gate === "ALLOW" ? lv(a.granted) : lv("DENY")} ${a.gate_reasons.map((r) => `<span class="tag warn" data-tip="${esc(r.text)}">${esc(r.code)}</span>`).join("")}</dd>
              <dt>Binding</dt><dd class="small">${a.binding.length ? a.binding.map((b) => `<span class="tag">${esc(b)}</span>`).join("") : "‚Äî"}</dd>
              <dt>Executes</dt><dd class="code">${esc(a.executed)}</dd>
              <dt>Regret</dt><dd><b>${num(a.regret, 3)}</b> ${a.agrees ? `<span class="small faint">matches optimum</span>` : ""}</dd>
            </dl></div>`).join("")}
        </div>

        <div class="sheet">
          <div class="verdict">
            <div><div class="small faint">Mathematical optimum</div><div class="big">${esc(d.optimum.code)}</div><div style="margin-top:6px">${lv(d.optimum.level)} <span class="small muted">for ${esc(d.operating_agent)}</span></div></div>
            <div>
              <p style="margin:0 0 6px">${esc(d.optimum.name)}. ${d.optimum.binding.length ? `Autonomy is held at ${esc(d.optimum.level)} by: ${d.optimum.binding.map((b) => `<span class="tag">${esc(b)}</span>`).join("")}` : d.optimum.level === "AUTO" ? "Every cap admits autonomous execution." : ""}</p>
              <p class="small muted" style="margin:0 0 8px">Expected: <b>${d.by_mode.expected}</b> ¬∑ Tail-aware: <b>${d.by_mode.cvar}</b> ¬∑ Robust: <b>${d.by_mode.robust}</b>.
                Calibration for this class at Œ±=${num(d.calibration.alpha, 4)}: ${esc(d.calibration.reason)}. Drift: ${d.drift.stable ? "stable" : `material (W‚ÇÅ ${d.drift.w1}, KL ${d.drift.kl}${d.drift.cusum_alarm ? ", CUSUM alarm" : "")}`}.</p>
              ${eq(modeTex)}
              ${eq(String.raw`\mathrm{Regret}(a)=J(a_{\text{exec}})-J(a^*),\qquad a_{\text{exec}}=\begin{cases}a & \text{gate allows}\\ \text{ESCALATE} & \text{gate denies}\end{cases}`)}
            </div>
          </div>
        </div>

        <div class="sheet"><h3>Every candidate action</h3>
          <div class="table-wrap"><table><thead><tr><th>Action</th><th>Feasibility</th><th class="num">E[L]</th><th class="num">CVaR‚Çâ‚ÇÖ</th><th class="num">Risk R</th><th class="num">P(fail)</th><th class="num">E[T] h</th><th class="num">Human min</th><th>${d.mode === "robust" ? "Worst-case J" : "Objective J"}</th><th>Autonomy</th><th>Binding caps</th></tr></thead><tbody>
            ${d.actions.map((a) => `<tr class="${a.optimal ? "best" : a.feasible ? "" : "off"}">
              <td><span class="code" data-tip="${esc(a.name)}<br>irreversibility ${a.irreversibility}">${esc(a.code)}</span></td>
              <td>${a.feasible ? "feasible" : a.reasons.map((r) => `<span class="tag warn" data-tip="${esc(r.text)}">${esc(r.code)}</span>`).join("")}</td>
              <td class="num">${eur(a.expected_loss)}</td><td class="num">${eur(a.cvar)}</td><td class="num">${num(a.risk, 3)}</td>
              <td class="num">${pct(a.p_fail, 0)}</td><td class="num">${num(a.expected_hours, 1)}</td><td class="num">${num(a.human_minutes, 0)}</td>
              <td>${a.feasible ? `<div style="display:flex;gap:8px;align-items:center"><div class="bar" style="flex:1"><i style="width:${(jOf(a) / maxJ) * 100}%"></i></div><span class="num" data-tip="${Object.entries(a.weighted).map(([k, v]) => `${k}: ${v}`).join("<br>")}">${num(jOf(a), 3)}</span></div>` : "‚Äî"}</td>
              <td>${lv(a.level)}</td><td class="small">${a.binding.map((b) => `<span class="tag">${esc(b)}</span>`).join("")}</td></tr>`).join("")}
          </tbody></table></div>
          ${eq(String.raw`J(a)=\lambda_C\tfrac{\mathbb{E}[L]}{C_{\text{ref}}}+\lambda_R R+\lambda_T\tfrac{\mathbb{E}[T]}{24}+\lambda_H\tfrac{H}{60}+\lambda_F P_{\text{fail}}+\lambda_K\tfrac{\mathrm{CVaR}_{0.95}}{C_{\text{ref}}}`, "Hover an objective value for its weighted components. ESCALATE is always feasible, so the feasible set is never empty.")}
          ${eq(String.raw`R(a)=P_{\text{err}}(a)\cdot\big(0.30\,\text{exposure}+0.25\,\text{irrev}+0.15\,(1-\text{detect})+0.15\,\text{propagation}+0.15\,\text{control}\big)`)}
        </div>
      </div>`;
  }

  function benchHtml(r) {
    const map = S.bench.mapping;
    const name = (label) => (map ? `${label} <span class="small muted">= ${esc(map[label])}</span>` : label);
    const ci = (x) => `<span class="small faint">[${x.map((v) => num(v, 3)).join(", ")}]</span>`;
    const m = r.manifest;
    const pval = r.comparison.p_value < 0.001 ? "p < 0.001" : `p = ${num(r.comparison.p_value, 3)}`;
    return `
      <div class="stack">
        <div class="sheet"><div class="grid g2">
          <div><h3>Manifest</h3>
            <p class="small muted" style="margin:0">${m.population.cases} cases, seed ${m.population.seed}, ${m.population.class_mix}; ${m.exception_classes.length} exception classes; ${m.permitted_evidence.length} evidence signals; ${m.control_invariants.length} invariants; calibration by ${m.calibration.method}; rates with ${m.statistical_tests.rates}; regret by ${m.statistical_tests.regret}.</p></div>
          <div><h3>SHA-256</h3><div class="hash">${esc(r.manifest_hash)}</div><div class="small faint">Frozen ${esc(r.frozen_at)}</div></div>
        </div></div>
        <div class="sheet"><div class="table-wrap"><table><thead><tr><th>Agent</th><th class="num">Valid</th><th class="num">Control-safe</th><th class="num">Matches optimum</th><th class="num">Mean regret</th><th class="num">Human min/case</th><th class="num">Resolution</th><th class="num">Tail loss CVaR‚Çâ‚ÇÖ</th><th class="num">Autonomous</th></tr></thead><tbody>
          ${r.rows.map((x) => `<tr><td>${name(x.label)}</td><td class="num">${pct(x.valid)} ${ci(x.valid_ci)}</td><td class="num">${pct(x.control_safe)} ${ci(x.control_safe_ci)}</td><td class="num">${pct(x.agreement)}</td>
            <td class="num"><b>${num(x.mean_regret, 3)}</b> ${ci(x.regret_ci)}</td><td class="num">${num(x.human_minutes, 1)}</td><td class="num">${pct(x.resolution)}</td><td class="num">${eur(x.tail_loss_cvar95)}</td><td class="num">${pct(x.autonomous)}</td></tr>`).join("")}
          <tr class="best"><td>${esc(r.reference.label)}</td><td class="num">100%</td><td class="num">‚Äî</td><td class="num">100%</td><td class="num">0.000</td><td class="num">‚Äî</td><td class="num">${pct(r.reference.resolution)}</td><td class="num">${eur(r.reference.tail_loss_cvar95)}</td><td class="num">‚Äî</td></tr>
          </tbody></table></div>
          <p style="margin:12px 0 10px">${name(r.comparison.better)} has lower mean regret than ${name(r.comparison.other)} by <b>${num(Math.abs(r.comparison.mean_difference), 3)}</b> (95% CI ${ci(r.comparison.ci)}; paired bootstrap ${pval}).</p>
          <div class="controls">${map ? `<span class="small muted">Unblinded against the manifest hash.</span>` : `<button class="btn ghost" id="b-unblind">Unblind with manifest hash</button>`}</div>
          <div style="margin-top:12px">${eq(String.raw`\text{Control-safe}\iff a\in A_{\text{safe}}\;\land\;\ell_{\text{requested}}\le \ell_{\text{granted}}\qquad \text{Resolution}=p_{\text{in-time}}(x_{\text{true}},a_{\text{exec}})`, "Resolution uses the simulated true root cause, which neither the agents nor the engine observe.")}</div>
        </div>
      </div>`;
  }

  function wireBench(root) {
    const b = $("#b-unblind", root);
    if (!b) return;
    b.addEventListener("click", async () => {
      const r = await api("/api/benchmark/unblind", { manifest_hash: S.bench.result.manifest_hash });
      S.bench.mapping = r.mapping;
      const out = $("#bench-out", root);
      out.innerHTML = benchHtml(S.bench.result);
      renderMath(out);
    });
  }

  // ---------------------------------------------------------------- frontier
  function viewFrontier() {
    return `
      <header class="screen-head"><h1>Autonomy Frontier</h1>
        <p>Autonomy is earned per exception class and per action. It needs acceptable risk, statistical calibration at the action's burden of proof, a stable data distribution and a mandate.</p></header>
      <div class="controls" style="margin-bottom:18px"><div class="field"><label for="f-agent">Agent</label>${agentSelect("f-agent", S.frontierAgent)}</div></div>
      <div id="frontier-out"></div>`;
  }

  function wireFrontier(root) {
    const out = $("#frontier-out", root);
    const run = () => load(out, async () => frontierHtml(await api("/api/frontier", { agent: S.frontierAgent })));
    $("#f-agent", root).addEventListener("change", (e) => { S.frontierAgent = e.target.value; run(); });
    run();
  }

  function scatter(points, th) {
    const w = 760, h = 380, m = { l: 58, r: 20, t: 16, b: 46 };
    const xmax = Math.max(...points.map((p) => p.benefit)) * 1.08;
    const ymax = Math.max(th.r3 * 1.25, ...points.map((p) => p.risk)) * 1.05;
    const X = (v) => m.l + (v / xmax) * (w - m.l - m.r);
    const Y = (v) => h - m.b - (v / ymax) * (h - m.t - m.b);
    let s = `<svg class="chart" viewBox="0 0 ${w} ${h}" role="img" aria-label="Autonomy frontier: benefit against risk">`;
    const bands = [[0, th.r1, "AUTO"], [th.r1, th.r2, "APPROVE"], [th.r2, th.r3, "PROPOSE"], [th.r3, ymax, "DENY"]];
    bands.forEach(([a, b, l]) => {
      s += `<rect x="${m.l}" y="${Y(b)}" width="${w - m.l - m.r}" height="${Y(a) - Y(b)}" fill="${LEVEL_COLOR[l]}" opacity="0.07"/>`;
      s += `<text x="${w - m.r - 6}" y="${Y(b) + 14}" text-anchor="end" font-size="11" fill="${LEVEL_COLOR[l]}" font-weight="600">${l === "DENY" ? "DENY" : `‚â§ ${l}`}</text>`;
    });
    [["r_1", th.r1], ["r_2", th.r2], ["r_3", th.r3]].forEach(([n, v]) => { s += `<line x1="${m.l}" x2="${w - m.r}" y1="${Y(v)}" y2="${Y(v)}" stroke="#7a8799" stroke-dasharray="4 4"/><text x="${m.l + 4}" y="${Y(v) - 4}" font-size="11" fill="#4b5a70">${n.replace("_", "")} = ${v}</text>`; });
    for (let i = 0; i <= 5; i++) {
      const xv = (xmax * i) / 5;
      s += `<text x="${X(xv)}" y="${h - m.b + 17}" font-size="11" text-anchor="middle" fill="#7a8799">${xv.toFixed(0)}</text>`;
      const yv = (ymax * i) / 5;
      s += `<text x="${m.l - 8}" y="${Y(yv) + 4}" font-size="11" text-anchor="end" fill="#7a8799">${yv.toFixed(2)}</text>`;
    }
    s += `<text x="${(m.l + w - m.r) / 2}" y="${h - 6}" font-size="12" text-anchor="middle" fill="#4b5a70">Benefit: human minutes avoided per case</text>`;
    s += `<text transform="translate(14 ${(m.t + h - m.b) / 2}) rotate(-90)" font-size="12" text-anchor="middle" fill="#4b5a70">Risk R(a)</text>`;
    const eff = points.filter((p) => p.efficient).sort((a, b) => a.benefit - b.benefit);
    if (eff.length > 1) s += `<path d="${eff.map((p, i) => `${i ? "L" : "M"}${X(p.benefit)},${Y(p.risk)}`).join("")}" fill="none" stroke="#15233b" stroke-width="1.5"/>`;
    points.forEach((p) => {
      const tipHtml = `<b>${esc(p.cls_name)}</b><br>${esc(p.action)}<br>benefit ${p.benefit} min ¬∑ risk ${p.risk}<br>feasible in ${pct(p.feasible_share, 0)} of cases<br>modal level ${p.level}${p.efficient ? "<br>on the efficient frontier" : ""}`;
      s += `<circle cx="${X(p.benefit)}" cy="${Y(p.risk)}" r="${p.efficient ? 6 : 4.5}" fill="${LEVEL_COLOR[p.level]}" stroke="${p.efficient ? "#15233b" : "#fff"}" stroke-width="${p.efficient ? 2 : 1}" data-tip="${esc(tipHtml)}"/>`;
    });
    return s + "</svg>";
  }

  function mixBar(mix) {
    const order = ["HUMAN", "PROPOSE", "APPROVE", "AUTO"];
    return `<div class="mix" data-tip="${order.map((l) => `${l} ${pct(mix[l] || 0, 0)}`).join("<br>")}">${order.map((l) => `<i style="width:${(mix[l] || 0) * 100}%;background:${LEVEL_COLOR[l]}"></i>`).join("")}</div>`;
  }

  function frontierHtml(d) {
    const actions = S.cat.actions.slice(0, -1);
    return `
      <div class="stack">
        <div class="sheet"><div class="section-head"><h2>Benefit against risk, by class and action</h2>
          <div class="legend">${["AUTO", "APPROVE", "PROPOSE", "HUMAN"].map((l) => `<span><i style="background:${LEVEL_COLOR[l]}"></i>${l}</span>`).join("")}<span><i style="background:#fff;border:2px solid #15233b"></i>efficient</span></div></div>
          ${scatter(d.points, d.thresholds)}
          ${eq(String.raw`B(a)=\mathbb{E}\big[(h_i-H_a)(1-P_{\text{fail}})\big],\qquad R(a)=\mathbb{E}\big[P_{\text{err}}\cdot \mathrm{Severity}\bi/]`, "Colour is the level most often granted to the pair across the population, after all caps.")}
        </div>

        <div class="grid g2">
          <div class="sheet"><h3>Granted autonomy for the optimal action, by class</h3>
            <div class="table-wrap"><table><tbody>${d.class_mix.map((c) => `<tr><td>${esc(c.name)}</td><td style="width:45%">${mixBar(c.mix)}</td><td class="num small">${pct(c.mix.AUTO, 0)} auto</td></tr>`).join("")}</tbody></table></div>
          </div>
          <div class="sheet"><h3>Lattice rule</h3>
            ${eq(String.raw`\ell(a)=\min\{\mathrm{cap}_{\text{score}},\mathrm{cap}_{\text{risk}},\mathrm{cap}_{\text{calib}},\mathrm{cap}_{\text{drift}},\mathrm{cap}_{\text{mandate}},\mathrm{cap}_{\text{policy}}\}`)}
            ${eq(String.raw`\mathrm{Score}(a)=\mathrm{Benefit}-2.0\,R-0.55\,\mathrm{Irrev}-0.60\,Ua)}
            ${eq(String.raw`\alpha(a)=0.05\,(1-0.9\,\mathrm{irrev}_a)\;\Rightarrow\; n_{\text{cal}}\ge \lceil 1/\alpha(a)\rceil-1`, "The less reversible the action, the more calibration evidence autonomy requires.")}
          </div>
        </div>

        <div class="sheet"><div class="section-head"><h2>Calibration Registry</h2><span class="small muted">${esc(d.agent)} ¬∑ split conformal per exception class</span></div>
          <div class="table-wrap"><table><thead><tr><th>Exception class</th><th class="num">History</th><th class="num">n cal</th><th class="num">qÃÇ at Œ±=0.05</th><th class="num">Coverage</th><th class="num">Wilson LB</th><th class="num">E|Œì|</th><th>Status</th><th>By action (burden of proof)</th></tr></thead><tbody>
            ${d.registry.map((r) => `<tr><td>${esc(r.name)}</td><td class="num">${r.history.toLocaleString("en-GB")}</td><td class="num">${r.headline.n_cal.toLocaleString("en-GB")}</td>
              <td class="num">${r.headline.q_hat == null ? "‚àû" : num(r.headline.q_hat, 3)}</td><td class="num">${pct(r.headline.coverage)}</td><td class="num">${pct(r.headline.coverage_lb)}</td><td class="num">${num(r.headline.mean_set_size, 2)}</td>
              <td>${r.headline.calibrated ? `<span class="lv lv-AUTO">CALIBRATED</span>` : `<span class="tag warn">${esc(r.headline.reason)}</span>`}</td>
              <td><div style="display:flex;gap:4px">${r.by_action.map((a) => `<span data-tip="${esc(a.action)}<br>Œ± = ${a.alpha}<br>coverage LB ${pct(a.coverage_lb)}<br>set size ${a.set_size}<br>${a.calibrated ? "calibrated" : "not calibrated"}" style="width:14px;height:14px;border-radius:50%;display:inline-block;${a.calibrated ? "background:#0e7c66" : "border:1.5px solid #b42318"}"></span>`).join("")}</div></td></tr>`).join("")}
          </tbody></table></div>
          <p class="small faint">Dots, left to right: ${actions.map((a) => a.code).join(", ")}.</p>
          ${eq(String.raw`\hat q=s_{(\lceil (n+1)(1-\alpha)\rceil)},\qquad \Gamma_\alpha(x)=\{y:1-\hat p(y\mid x)\le \hat q\},\qquad \mathrm{Calibrated}\iff \hat q<\infty\land \mathrm{LB}\ge 1-\alpha-0.02\land \mathbb{E}|\Gamma|\le 3.5`)}
        </div>

        <div class="sheet"><div class="section-head"><h2>Drift monitor</h2><span class="small muted">Baseline days 1‚Äì${d.drift_thresholds.baseline_days}; shaded live window to day ${d.drift_thresholds.days}</span></div>
          <div class="table-wrap"><table><thead><tr><th>Exception class</th><th class="num">W‚ÇÅ scores</th><th class="num">KL mix</th><th>Daily error rate</th><th>CUSUM</th><th>Status</th></tr></thead><tbody>
            ${d.drift.map((r) => `<tr><td>${esc(r.name)}</td><td class="num ${r.w1 > d.drift_thresholds.w ? "error" : ""}">${num(r.w1, 4)}</td><td class="num ${r.kl > d.drift_thresholds.kl ? "error" : ""}">${num(r.kl, 4)}</td>
              <td>${sparkline(r.error_rate, { split: d.drift_thresholds.baseline_days, baseline: r.baseline_error, alarm: r.cusum_alarm_day })}</td>
              <td class="small">${r.cusum_alarm ? `alarm day ${r.cusum_alarm_day + 1}` : "no alarm"}</td>
              <td>${r.stable ? `<span class="lv lv-AUTO">STABLE</span>` : `<span class="lv lv-PROPOSE">ATTENUATE</span>`}</td></tr>`).join("")}
          </tbody></table></div>
          ${eq(String.raw`W_1\le ${d.drift_thresholds.w}\;\land\;\mathrm{KL}\le ${d.drift_thresholds.kl}\;\land\;\max_t S_t\le h,\qquad S_t=\max\big(0,\,S_{t-1}+e_t-\mu_0-k\sigma_0\big)`, "A failed check caps autonomy at PROPOSE for that class until the distribution is re-baselined.")}
        </div>
      </div>`;
  }

  // ---------------------------------------------------------------- sensitivity
  function viewSensitivity() {
    const keys = Object.keys(S.cat.lambdas);
    const opt = (id, v) => `<select id="${id}">${keys.map((k) => `<option value="${k}" ${k === v ? "selected" : ""}>${esc(S.cat.lambdas[k])}</option>`).join("")}</select>`;
    return `
      <header class="screen-head"><h1>Policy Sensitivity</h1>
        <p>The weights Œª are governance objects, not code constants. This screen shows exactly where the recommendation changes, and whether a disagreement is about the facts or about risk appetite.</p></header>
      <div class="sheet stack">
        <div class="controls">
          <div class="field"><label for="s-case">Case</label><select id="s-case">${S.cat.cases.map((c) => `<option value="${c.id}" ${c.id === S.sens.caseId ? "selected" : ""}>${esc(c.id)} ¬∑ ${esc(c.title)}</option>`).join("")}</select></div>
          <div class="field"><label for="s-x">Horizontal axis</label>${opt("s-x", S.sens.x)}</div>
          <div class="field"><label for="s-y">Vertical axis</label>${opt("s-y", S.sens.y)}</div>
        </div>
        ${sliders("sl")}
      </div>
      <div id="sens-out" class="section"></div>`;
  }

  function wireSensitivity(root) {
    const out = $("#sens-out", root);
    const run = () => load(out, async () => sensHtml(await api("/api/sensitivity", { case_id: S.sens.caseId, x_key: S.sens.x, y_key: S.sens.y, lambdas: S.lambdas, res: S.sens.res, span: S.sens.span })));
    const runSoon = debounce(run, 250);
    $("#s-case", root).addEventListener("change", (e) => { S.sens.caseId = e.target.value; run(); });
    $("#s-x", root).addEventListener("change", (e) => { S.sens.x = e.target.value; run(); });
    $("#s-y", root).addEventListener("change", (e) => { S.sens.y = e.target.value; run(); });
    wireSliders(root, "sl", runSoon);
    run();
  }

  function sensHtml(d) {
    const res = d.xs.length;
    const lx = S.cat.lambdas[d.x_key], ly = S.cat.lambdas[d.y_key];
    const cx = Math.round((d.lambdas[d.x_key] / d.xs[res - 1]) * (res - 1));
    const cy = Math.round((d.lambdas[d.y_key] / d.ys[res - 1]) * (res - 1));
    const used = [...new Set(d.phase.flat())];
    let cells = "";
    for (let yi = res - 1; yi >= 0; yi--) {
      for (let xi = 0; xi < res; xi++) {
        const a = d.phase[yi][xi];
        cells += `<div class="${xi === cx && yi === cy ? "here" : ""}" style="background:${ACTION_COLOR[a]}" data-tip="${esc(a)}<br>${esc(lx)} ${d.xs[xi]}<br>${esc(ly)} ${d.ys[yi]}"></div>`;
      }
    }
    const sweepRows = Object.entries(d.sweeps).map(([k, sw]) => {
      const segs = sw.segments;
      const span = 5;
      const bar = segs.map((s) => `<i style="width:${((s.end - s.start) / span) * 100}%;background:${ACTION_COLOR[s.action]}" data-tip="${esc(s.action)}: ${s.start} ‚Äì ${s.end}">${(s.end - s.start) / span > 0.14 ? esc(s.action) : ""}</i>`).join("");
      let text;
      if (segs.length === 1) text = `<b>${esc(segs[0].action)}</b> stays optimal for every ${tex(LAMBDA_TEX[k])} in [0, 5].`;
      else text = segs.slice(1).map((s, i) => `${esc(segs[i].action)} ‚Üí <b>${esc(s.action)}</b> when ${tex(LAMBDA_TEX[k])} ${sw.current < s.start ? "exceeds" : "passes"} <b>${num(s.start, 2)}</b>`).join("; ");
      return `<div style="padding:10px 0;border-bottom:1px solid var(--rule-soft)">
        <div class="small"><b>${esc(S.cat.lambdas[k])}</b> <span class="faint">(now ${num(sw.current)})</span> ¬∑ ${text}</div>
        <div style="position:relative"><div class="segline">${bar}</div><span style="position:absolute;top:-3px;left:calc(${Math.min(sw.current / span, 1) * 100}% - 1px);width:2px;height:28px;background:#15233b"></span></div></div>`;
    }).join("");
    return `
      <div class="grid g2">
        <div class="sheet"><h3>Phase diagram ¬∑ ${esc(d.case.title)}</h3>
          <div class="phase-wrap"><div class="ylab">${esc(ly)} ${tex(LAMBDA_TEX[d.y_key])} ‚Üí ${d.ys[res - 1]}</div>
            <div class="phase" style="grid-template-columns:repeat(${res},1fr)">${cells}</div>
            <div class="xlab">${esc(lx)} ${tex(LAMBDA_TEX[d.x_key])} ‚Üí ${d.xs[res - 1]}</div></div>
          <div class="legend" style="margin-top:10px">${used.map((a) => `<span><i style="background:${ACTION_COLOR[a]}"></i>${esc(a)}</span>`).join("")}<span><i style="border:2px solid #15233b"></i>current weights</span></div>
        </div>
        <div class="stack">
          <div class="sheet"><h3>Stakeholder presets</h3>
            <table><tbody>${d.presets.map((p) => `<tr><td>${esc(p.name)}</td><td class="code">${esc(p.action)}</td><td class="small faint">${Object.entries(p.lambdas).map(([k, v]) => `${k} ${v}`).join(" ¬∑ ")}</td></tr>`).join("")}</tbody></table>
            <div class="callout ${d.stable ? "ok" : ""}" style="margin-top:12px">${d.stable ? `Every preset reaches <b>${esc(d.presets[0].action)}</b>. This decision is technically obvious.` : `The presets disagree. The disagreement is about risk appetite, not about the AI: the facts and the feasible set are identical under every preset.`}</div>
          </div>
          <div class="sheet"><h3>Why the breakpoints are exact</h3>
            ${eq(String.raw`J_a(\lambda_k)=\beta_a+\lambda_k\,c_k(a)\;\Rightarrow\;\lambda_k^*=\frac{\beta_b-\beta_a}{c_k(a)-c_k(b)}`, "J is linear in each weight, so the optimum is the lower envelope of straight lines. No grid search.")}
          </div>
        </div>
      </div>
      <div class="sheet section"><h3>Where the recommendation changes ¬∑ current: <span class="code">${esc(d.current)}</span></h3>${sweepRows}</div>
      <div class="sheet section"><div class="section-head"><h3>Population stability across presets</h3><span class="small muted">Share of cases where all four presets choose the same action: <b>${pct(d.population.overall)}</b></span></div>
        <div class="table-wrap"><table><thead><tr><th>Exception class</th><th class="num">Cases</th><th>Decision-stable share</th><th>Departs from Operations preset</th></tr></thead><tbody>
          ${d.population.classes.map((c) => `<tr><td>${esc(c.name)}</td><td class="num">${c.n}</td><td><div style="display:flex;gap:8px;align-items:center"><div class="bar" style="flex:1"><i style="width:${c.stable_share * 100}%"></i></div><span class="num">${pct(c.stable_share, 0)}</span></div></td>
            <td class="small">${Object.entries(c.departs).map(([k, v]) => `${esc(k)} ${pct(v, 0)}`).join(" ¬∑ ")}</td></tr>`).join("")}
        </tbody></table></div></div>`;
  }

  // ---------------------------------------------------------------- savings
  function viewSavings() {
    return `
      <header class="screen-head"><h1>Savings Lab</h1>
        <p>Autonomy is allocated like a scarce resource under risk budgets, then the residual work is staffed with integer headcount, control floors and a stress buffer. Minutes removed and people released are reported separately.</p></header>
      <div class="sheet"><div class="controls">
        <div class="field"><label for="v-agent">Operating agent</label>${agentSelect("v-agent", S.sav.agent)}</div>
        <div class="field" style="min-width:260px"><label for="v-budget">Risk budget: change in expected operational loss vs all-human <output id="v-budget-out"><b>${signed(S.sav.budget)}</b></output></label>
          <input type="range" id="v-budget" min="-0.2" max="0.8" step="0.02" value="${S.sav.budget}"></div>
        <div class="field" style="min-width:220px"><label for="v-target">Headcount target <output id="v-target-out"><b>${pct(S.sav.target, 0)}</b></output></label>
          <input type="range" id="v-target" min="0.05" max="0.4" step="0.01" value="${S.sav.target}"></div>
      </div></div>
      <div id="sav-out" class="section"></div>`;
  }

  function wireSavings(root) {
    const out = $("#sav-out", root);
    const run = () => load(out, async () => savHtml(await api("/api/savings", { agent: S.sav.agent, risk_budget: S.sav.budget, target: S.sav.target, lambdas: S.lambdas })));
    const runSoon = debounce(run, 250);
    $("#v-agent", root).addEventListener("change", (e) => { S.sav.agent = e.target.value; run(); });
    $("#v-budget", root).addEventListener("input", (e) => { S.sav.budget = parseFloat(e.target.value); $("#v-budget-out", root).innerHTML = `<b>${signed(S.sav.budget)}</b>`; runSoon(); });
    $("#v-target", root).addEventListener("input", (e) => { S.sav.target = parseFloat(e.target.value); $("#v-target-out", root).innerHTML = `<b>${pct(S.sav.target, 0)}</b>`; runSoon(); });
    run();
  }

  function savHtml(d) {
    const s = d.solution;
    if (!s) return `<div class="callout">No allocation satisfies this risk budget. Even the lowest-loss allocation needs a budget of ${signed(d.envelope.best_budget)}.</div>`;
    const tp = d.target_point;
    const verdict = d.target_feasible
      ? `<div class="callout ok">A <b>${pct(d.target, 0)}</b> headcount reduction is reachable, first at a risk budget of <b>${signed(tp.risk_budget)}</b> expected operational loss versus the all-human process.</div>`
      : `<div class="callout">A <b>${pct(d.target, 0)}</b> headcount reduction is <b>not reachable</b> under these calibration, drift, mandate and control constraints. The most any allocation achieves is <b>${pct(d.max_fte_reduction)}</b>.</div>`;
    const ymax = Math.max(d.target, ...d.curve.map((p) => p.minutes_removed)) * 1.15;
    const xd = [d.curve[0].risk_budget, d.curve[d.curve.length - 1].risk_budget];
    const chart = lineChart({
      series: [
        { color: "#9aa5b1", dash: "5 4", points: d.curve.map((p) => [p.risk_budget, p.minutes_removed]), tip: (p) => `minutes removed ${pct(p[1])} at ${signed(p[0])}` },
        { color: "#15233b", width: 2.5, points: d.curve.map((p) => [p.risk_budget, p.fte_reduction]), tip: (p) => `FTE reduction ${pct(p[1])} at ${signed(p[0])}` },
      ],
      xd, yd: [0, ymax], xFmt: (v) => signed(v), yFmt: (v) => pct(v, 0),
      xLabel: "Risk budget (expected operational loss vs all-human)", yLabel: "Reduction",
      hlines: [{ y: d.target, color: "#b42318", label: `target ${pct(d.target, 0)}` }],
      vlines: S.sav.budget >= xd[0] && S.sav.budget <= xd[1] ? [{ x: S.sav.budget, color: "#0e7c66", label: "current" }] : [],
    });
    const skills = [...new Set(s.grid.map((g) => g.skill))];
    const regions = [...new Set(s.grid.map((g) => g.region))];
    const cell = (sk, rg) => s.grid.find((g) => g.skill === sk && g.region === rg);
    return `
      <div class="stack">
        ${verdict}
        <div class="kpis">
          <div class="kpi"><div class="v">${pct(s.minutes_removed_pct)}</div><div class="k">Human minutes removed</div></div>
          <div class="kpi"><div class="v">${pct(s.capacity_released_pct)}</div><div class="k">Capacity actually releasable</div></div>
          <div class="kpi"><div class="v">${pct(s.fte_reduction_pct)}</div><div class="k">FTE reduction ¬∑ ${d.baseline.fte} ‚Üí ${s.fte}</div></div>
          <div class="kpi"><div class="v">${num(s.loss_index, 0)}</div><div class="k">Expected-loss index (all-human = 100)</div></div>
        </div>
        <div class="grid g2">
          <div class="sheet"><h3>What each risk budget buys</h3>${chart}
            <div class="legend"><span><i style="background:#15233b"></i>FTE reduction</span><span><i style="background:#9aa5b1"></i>minutes removed</span></div></div>
          <div class="sheet"><h3>Why minutes removed ‚â† people released</h3>
            <table><tbody>
              <tr><td>Minutes removed by the allocated autonomy</td><td class="num"><b>${pct(s.minutes_removed_pct)}</b></td></tr>
              <tr><td>Lost to fragmentation: partial automation frees slivers of tasks, not whole tasks</td><td class="num">‚àí${pct(s.decomposition.fragmentation)}</td></tr>
              <tr><td>Lost to staffing rigidity: integer FTE, stress buffer, control floors (${s.floor_binding_cells} floor-bound cells)</td><td class="num">${s.decomposition.staffing_rigidity >= 0 ? "‚àí" : "+"}${pct(Math.abs(s.decomposition.staffing_rigidity))}</td></tr>
              <tr class="best"><td>Headcount reduction</td><td class="num"><b>${pct(s.fte_reduction_pct)}</b></td></tr>
            </tbody></table>
            <p class="small muted">Tail-loss index ${num(s.tail_index, 0)} (all-human = 100). Classes held back by calibration or drift cannot contribute autonomy whatever the budget.</p>
          </div>
        </div>
        <div class="sheet"><h3>Autonomy allocation by class</h3>
          <div class="table-wrap"><table><thead><tr><th>Exception class</th><th class="num">Cases/day</th><th class="num">Handling</th><th>Ceiling</th><th>Case-level autonomy available</th><th class="num">Minutes removed/day</th><th class="num">Share</th><th class="num">Releasable</th><th class="num">Loss index</th></tr></thead><tbody>
            ${s.classes.map((c) => `<tr><td>${esc(c.name)}</td><td class="num">${num(c.volume, 0)}</td><td class="num">${c.handling} min</td><td>${lv(c.ceiling)}</td><td style="width:18%">${mixBar(c.level_mix)}</td>
              <td class="num">${num(c.minutes_removed, 0)}</td><td class="num">${pct(c.share_removed, 0)}</td><td class="num">${num(c.capacity_released, 0)}</td><td class="num">${num(c.loss_index, 0)}</td></tr>`).join("")}
          </tbody></table></div>
          ${eq(String.raw`\max_{x}\sum_{i,z}x_{iz}K_i(z)\quad\text{s.t.}\quad \sum_{i,z}x_{iz}\,EL_i(z)\le R_{\max},\;\; \sum_{i,z}x_{iz}\,TL_i(z)\le L_{\max},\;\; \sum_z x_{iz}=1,\;\; x_{iz}\in\{0,1\}`, "Each case runs at min(class ceiling, level granted to its optimal action). TL sums standalone CVaRs, an upper bound on portfolio CVaR by subadditivity.")}
        </div>
        <div class="sheet"><h3>Staffing by skill and region ¬∑ baseline ‚Üí optimised</h3>
          <div class="table-wrap"><table><thead><tr><th>Skill</th>${regions.map((r) => `<th class="num">${r}</th>`).join("")}<th class="num">Floor</th></tr></thead><tbody>
            ${skills.map((sk) => `<tr><td>${esc(sk)}</td>${regions.map((rg) => { const c = cell(sk, rg); return `<td class="num">${c.baseline} ‚Üí <b>${c.optimised}</b>${c.optimised === c.floor ? ` <span class="tag">floor</span>` : ""}</td>`; }).join("")}<td class="num">${cell(sk, regions[0]).floor}</td></tr>`).join("")}
            <tr><td>Flexible pool</td>${s.flex.regions.map((_, i) => `<td class="num">${s.flex.baseline[i]} ‚Üí <b>${s.flex.optimised[i]}</b></td>`).join("")}<td></td></tr>
          </tbody></table></div>
          ${eq(String.raw`\min\sum_{j,t}HC_{jt}+1.1\sum_t F_t\quad\text{s.t.}\quad 420\,HC_{jt}+0.8\,y_{jt}\ge 1.25\,W_{jt},\;\;\sum_j y_{jt}\le 420\,F_t,\;\; HC_{jt}\ge \underline{HC}_j,\;\; HC,F\in\mathbb{Z}_+a)}
        </div>
      </div>`;
  }

  // ---------------------------------------------------------------- proof
  function viewProof() {
    return `
      <header class="screen-head"><h1>Proof &amp; Control Console</h1>
        <p>The same proposals are replayed twice: in shadow mode, where the gate only logs, and in enforcing mode, where it decides. An independent temporal-logic monitor then checks both traces against twelve invariants.</p></header>
      <div class="sheet"><div class="controls">
        <div class="field"><label for="p-n">Proposals</label><input type="number" id="p-n" min="50" max="1500" step="50" value="${S.proof.n}"></div>
        <div class="field"><label for="p-seed">Seed</label><input type="number" id="p-seed" value="${S.proof.seed}"></div>
        <button class="btn" id="p-run">Replay</button>
      </div></div>
      <div id="proof-out" class="section"></div>`;
  }

  function wireProof(root) {
    const out = $("#proof-out", root);
    const run = () => load(out, async () => proofHtml(await api("/api/proof", S.proof)));
    $("#p-run", root).addEventListener("click", () => {
      S.proof.n = parseInt($("#p-n", root).value, 10) || 300;
      S.proof.seed = parseInt($("#p-seed", root).value, 10) || 0;
      run();
    });
    run();
  }

  function proofHtml(d) {
    const maxV = Math.max(1, ...d.invariants.map((i) => i.shadow));
    const inj = d.injected;
    return `
      <div class="stack">
        <div class="kpis">
          <div class="kpi"><div class="v">${d.totals.shadow}</div><div class="k">Invariant violations, shadow mode</div></div>
          <div class="kpi"><div class="v" style="color:var(--auto)">${d.totals.enforcing}</div><div class="k">Invariant violations, enforcing mode</div></div>
          <div class="kpi"><div class="v">${d.n}</div><div class="k">Agent proposals replayed</div></div>
          <div class="kpi"><div class="v">${inj.unauthenticated + inj.missing_evidence + inj.field_tampering}</div><div class="k">Injected faults ¬∑ ${inj.unauthenticated} identity, ${inj.missing_evidence} evidence, ${inj.field_tampering} tampering</div></div>
        </div>
        <div class="callout ${d.totals.enforcing === 0 ? "ok" : ""}">${d.totals.enforcing === 0 ? `The enforcing trace satisfies all ${d.invariants.length} invariants at every position of every proposal's trace. The checker is the monitor below, not the gate that produced the trace.` : `The enforcing trace has violations. Inspect the table below.`}</div>

        <div class="sheet"><h3>Control invariants</h3>
          <div class="table-wrap"><table><thead><tr><th>Id</th><th>Formula</th><th>Meaning</th><th>Shadow violations</th><th class="num">Enforcing</th></tr></thead><tbody>
            ${d.invariants.map((i) => `<tr><td class="code">${i.code}</td><td>${tex(i.tex)}</td><td class="small">${esc(i.text)}</td>
              <td style="min-width:150px"><div style="display:flex;gap:8px;align-items:center"><div class="bar" style="flex:1"><i style="width:${(i.shadow / maxV) * 100}%;background:var(--deny)"></i></div><span class="num" data-tip="${i.examples.map((e) => `${esc(e.key)} ¬∑ ${esc(e.action)} ¬∑ agent ${esc(e.agent)}`).join("<br>") || "none"}">${i.shadow}</span></div></td>
              <td class="num"><b>${i.enforcing}</b></td></tr>`).join("")}
          </tbody></table></div>
          ${eq(String.raw`\mathbf{O}\,\psi \text{ at } i \iff \exists j\le i:\psi \text{ at } j,\qquad \mathbf{G}\,\varphi \iff \forall i:\varphi \text{ at } ig, "Past-time LTL evaluated over each proposal's finite event trace.")}
        </div>

        <div class="grid g2">
          <div class="sheet"><h3>Gate decisions, enforcing mode</h3>
            <p class="small muted" style="margin:0 0 6px">Allowed, at granted level</p>
            <div style="display:flex;flex-wrap:wrap;gap:8px 14px">${Object.entries(d.gate.ALLOW).map(([l, n]) => `<span>${lv(l)} <b>${n}</b></span>`).join("")}</div>
            <p class="small muted" style="margin:14px 0 6px">Denied, by reason (then escalated to a human)</p>
            <table><tbody>${Object.entries(d.gate.DENY).sort((a, b) => b[1] - a[1]).map(([r, n]) => `<tr><td><span class="tag warn">${esc(r)}</span></td><td class="num">${n}</td></tr>`).join("")}</tbody></table>
          </div>
          <div class="sheet"><h3>Tamper-evident decision log</h3>
            ${eq(String.raw`H_t=\mathrm{SHA256}\big(H_{t-1}\,\Vert\,\mathrm{canonical}(e_t)\big),\qquad H_0=0^{64}`)}
            <p class="small" style="margin:10px 0 4px">Chain of ${d.chain.length} events ¬∑ ${d.chain.verified ? `<span class="lv lv-AUTO">VERIFIED</span>` : `<span class="lv lv-DENY">BROKEN</span>`}</p>
            <div class="hash">root ${esc(d.chain.root)}</div>
            <p class="small" style="margin:12px 0 4px">Tamper test: event ${d.chain.tamper_test.modified_seq} altered to claim AUTO ‚Üí ${d.chain.tamper_test.verified ? "not detected" : `<b>detected at event ${d.chain.tamper_test.first_break}</b>`}</p>
            <table class="log"><tbody>${d.chain.tail.map((c) => `<tr><td class="num">${c.seq}</td><td class="hash">${esc(c.hash.slice(0, 32))}‚Ä¶</td></tr>`).join("")}</tbody></table>
          </div>
        </div>

        <div class="sheet"><h3>Enforcing trace, first events</h3>
          <div class="table-wrap"><table class="log"><thead><tr><th class="num">Seq</th><th>Proposal</th><th>Event</th><th>Actor</th><th>Action</th><th>Detail</th></tr></thead><tbody>
            ${d.trace_sample.map((e) => `<tr><td class="num">${e.seq}</td><td>${esc(e.key)}</td><td>${esc(e.type)}</td><td>${esc(e.agent || "")}</td><td class="code">${esc(e.action || "")}</td>
              <td>${e.type === "GATE" ? (e.decision === "ALLOW" ? "allow" : `<span class="tag warn">deny</span>`) : e.type === "EXECUTE" ? lv(["HUMAN", "PROPOSE", "APPROVE", "AUTO"][e.level]) : e.type === "APPROVE" ? esc(e.approver) : esc(e.cls || "")}</td></tr>`).join("")}
          </tbody></table></div>
        </div>
      </div>`;
  }

  // ---------------------------------------------------------------- router
  const SCREENS = {
    overview: [viewOverview, null],
    arena: [viewArena, wireArena],
    frontier: [viewFrontier, wireFrontier],
    sensitivity: [viewSensitivity, wireSensitivityt∞(ÄÄÄÅÕÖŸ•πùÃËÅmŸ•ï›MÖŸ•πùÃ∞Å›•…ïMÖŸ•πùÕt∞(ÄÄÄÅ¡…ΩΩòËÅmŸ•ï›A…ΩΩò∞Å›•…ïA…ΩΩôt∞(ÄÅÙÏ((ÄÅô’πç—•Ω∏Å…Ω’—î†§ÅÏ(ÄÄÄÅçΩπÕ–ÅπÖµîÄÙÄ°±ΩçÖ—•Ω∏π°ÖÕ†ÅÒÄàçΩŸï…Ÿ•ï‹à§πÕ±•çî†ƒ§Ï(ÄÄÄÅçΩπÕ–Å≠ï‰ÄÙÅMI9MmπÖµïtÄ¸ÅπÖµîÄËÄâΩŸï…Ÿ•ï‹àÏ(ÄÄÄÄêê†àππÖÿÅÑà§πôΩ…Öç††°Ñ§ÄÙ¯ÅÑπÕï———…•â’—î†âÖ…•Ñµç’……ïπ–à∞ÅÑπëÖ—ÖÕï–πÕç…ïï∏ÄÙÙÙÅ≠ï‰Ä¸Äâ¡ÖùîàÄËÄâôÖ±Õîà§§Ï(ÄÄÄÅçΩπÕ–ÅµÖ•∏ÄÙÄê†àçµÖ•∏à§Ï(ÄÄÄÅçΩπÕ–ÅmŸ•ï‹∞Å›•…ïtÄÙÅMI9Mm≠ïÂtÏ(ÄÄÄÅµÖ•∏π•ππï…!Q50ÄÙÅŸ•ï‹†§Ï(ÄÄÄÅ…ïπëï…5Ö—†°µÖ•∏§Ï(ÄÄÄÅ•òÄ°›•…î§Å›•…î°µÖ•∏§Ï(ÄÄÄÅ›•πëΩ‹πÕç…Ω±±Qº†¿∞Ä¿§Ï(ÄÅÙ((ÄÅÖÕÂπåÅô’πç—•Ω∏ÅâΩΩ–†§ÅÏ(ÄÄÄÅçΩπÕ–ÅµÖ•∏ÄÙÄê†àçµÖ•∏à§Ï(ÄÄÄÅµÖ•∏π•ππï…!Q50ÄÙÅÄÒë•ÿÅç±ÖÕÃÙâ±ΩÖë•πúà˘1ΩÖë•πúÅçÖ—Ö±Ωù’ï‚Ä¶</div>`;
    try {
      S.cat = await api("/api/catalogue");
      S.lambdas = { ...S.cat.default_lambdas };
      window.addEventListener("hashchange", route);
      route();
    } catch (e) {
      main.innerHTML = `<p class="error">Engine unavailable: ${esc(e.message)}</p>`;
    }
  }

  boot();
})();
