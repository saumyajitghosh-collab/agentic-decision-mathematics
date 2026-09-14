# Agentic Decision Mathematics

**AI proposes. Mathematics decides what is permissible, optimal and sufficiently certain. Controls decide whether it executes.**

A pure-maths control plane for agentic AI in securities operations. Any agent — an LLM, a vendor model, a rules engine — proposes an action for an operational exception. A deterministic engine maintains the *belief* about what is actually wrong, bounds what may be done, finds the optimal action, decides how much autonomy is earned, and enforces formally specified controls before anything executes.

**No language model sits in the decision path.** Every number in the interface is computed live by the engine.

> **Synthetic data only.** Exception classes, volumes, likelihoods, costs, agents and thresholds are illustrative assumptions in `engine/config.py`. Replace them with institution data before drawing any operational conclusion.

---

## The question this application answers

> *Can we create a pure-maths based AI application which improves the Agentic AI work being done?*

Yes — by inverting the architecture. The prevailing pattern is **agent thinks → agent decides → agent executes**. This application implements the alternative:

```
Agent proposes  →  Mathematics evaluates  →  Mathematics optimises  →  Gate authorises  →  System executes
(the only AI stage)      (deterministic)           (deterministic)        (formal invariants)     (hash-chained)
```

The agent does not even own the state of the world. It may propose an *interpretation* of the evidence; the control layer maintains the operational belief state. The LLM supplies intelligence; mathematics supplies bounds, proof, optimisation and execution authority.

## Quick start

```bash
pip install -r requirements.txt

# 1. CLI demo — the full pipeline, no web server:
python demo.py

# 2. Web application — six screens:
python app.py            # then open http://localhost:5000

# 3. Tests (20 property tests over the mathematics and controls):
pip install -r requirements-dev.txt
pytest
```

`demo.py` runs four stages end to end: one curated case through belief → proposals → feasible set → optimiser → autonomy → gate → regret; a pre-registered blinded population benchmark; the capacity-constrained savings lab; and a runtime-invariant verification replay with a tamper-evident hash chain.

## Screens

| Screen | Question it answers |
|---|---|
| **Overview** | What is the architecture, and where does the AI sit in it? |
| **Decision Arena** | Given one operational state, which proposal is best, what does the gate allow, and how much regret does each agent incur? Includes a preregistered, blinded population benchmark. |
| **Autonomy Frontier** | Where is autonomy earned? Benefit against risk per class and action, the Calibration Registry, and the drift monitor. |
| **Policy Sensitivity** | Which disagreements are about facts and which are about risk appetite? Phase diagram, exact breakpoints, stakeholder presets. |
| **Savings Lab** | What headcount reduction is feasible under a risk budget, and why do minutes removed differ from people released? |
| **Proof & Control** | Do the controls actually hold? Shadow-mode versus enforcing-mode replay against twelve temporal-logic invariants, with a tamper-evident log. |

## Architecture

```
Observations ─► Belief state ─► Agent interpretation ─► Feasible set ─► Optimiser ─► Autonomy lattice ─► Gate ─► Execution
   O₁:ₜ          b(x)            p̂(x), Γα(x)            A_safe          a*            ℓ = ⋀ caps          G(φ)     hash chain
                                  (only AI stage)
```

```
app.py                 Flask routes (JSON API + single-page UI)
demo.py               CLI end-to-end demo (no web server required)
engine/
  config.py            synthetic catalogue: hypotheses, evidence, classes, actions, thresholds, presets
  state.py             Bayesian belief state and synthetic population generator
  agents.py            synthetic proposal sources (model-agnostic stand-ins)
  core.py              loss model, exact CVaR, risk, feasible set, objective
  uncertainty.py       split conformal calibration registry, drift detection (W₁, KL, CUSUM)
  autonomy.py          autonomy lattice as the meet of independent caps
  invariants.py        past-time LTL monitor, twelve invariants, SHA-256 hash chain
  gate.py              execution gate and shadow-vs-enforcing proof simulation
  arena.py             curated and sampled cases; expected, tail-aware and robust optimisation
  benchmark.py         manifest hashing, blinding, Wilson intervals, paired bootstrap
  sensitivity.py       exact lower-envelope breakpoints, phase diagram, population stability
  savings.py           autonomy allocation MILP and workforce MILP
  frontier.py          benefit/risk frontier and catalogue metadata
  external.py          /api/evaluate contract for real agents
static/, templates/    interface (vanilla JS, hand-drawn SVG charts, KaTeX)
tests/                 property tests for the mathematics and the controls
```

### Connecting a real agent

The engine is model-agnostic. Any external agent — commercial LLM, in-house model, deterministic classifier — can submit proposals through one contract:

```
POST /api/evaluate
{
  "agent": "my-llm",
  "case": { "evidence": {"GOLDEN_SSI_DIFF": [1, 0.97], ...}, "notional": 3.2e6, "cutoff_h": 6 },
  "proposal": { "action": "REPAIR_SSI", "requested_level": "AUTO", "stated_confidence": 0.93,
                "p_hat": [0.90, 0.07, ...], "declared_changes": ["settlement_account"] }
}
```

The engine responds with the belief state (computed independently of the agent's claims), the feasible set, the optimal action, the granted autonomy level, gate reasons, and decision regret against the optimum. See `engine/external.py` for the full contract and a worked example.

## The mathematics

### 1. State uncertainty: belief, not knowledge

The engine never treats the operational state as known. For root-cause hypotheses *x* and observed evidence *oₑ* with reliability *rₑ ∈ (0, 1]*:

```
b(x) ∝ P(x) · Πₑ P(oₑ | x)^rₑ
```

The reliability exponent (a power posterior) lets a stale counterparty message move the belief less than a golden-source record. Normalised entropy `U = H(b) / log|X|` feeds the autonomy score.

### 2. Outcome uncertainty and the objective

For action *a*, resolution before cutoff happens with probability `p_it(x, a)`. Loss:

```
L = cₐ + w·Hₐ + (1 − y) · m · (fail + irrevₐ · (1 − detectₐ) · remediation),   m ~ LogNormal, E[m] = 1
```

CVaR at 95% is computed **exactly** on a discretised loss distribution (Rockafellar–Uryasev), not by Monte Carlo. Operational risk is `R(a) = P_err(a) · Severity(a)`, with severity weighting exposure, irreversibility, detectability, propagation and control severity.

```
J(a) = λ_C·E[L]/C_ref + λ_R·R + λ_T·E[T]/24 + λ_H·H/60 + λ_F·P_fail + λ_K·CVaR₉₅/C_ref
```

Every term is normalised to a commensurate scale before weighting. The weights λ are **governance objects**, set by stakeholders, not by the model — and the Policy Sensitivity screen exposes exactly where the optimal action changes as they move.

### 3. Feasible set

```
A_safe = { a : g(x, a) ≤ 0,  h(x, a) = 0,  φ(x, a) = TRUE }
```

* **g**: notional within the action's limit; `CVaR ≤ max(floor, bps · notional)`; risk below the denial threshold.
* **h**: declared field changes must be a subset of the action's authorised changes (field invariance).
* **φ**: SSI changes need an approved golden source; settlement instructions need a valid place of settlement; cancel/replace needs the original linked.

`ESCALATE` is always feasible, so the feasible set is never empty.

### 4. Three optimisation modes

```
expected   a* = argmin_{A_safe} E_b[J]                      (λ_K = 0)
cvar       a* = argmin_{A_safe} E_b[J] + λ_K·CVaR_α          (default)
robust     a* = argmin_{a} max_{x ∈ S} J(a | (1−ε)b + εδ_x)   (ε-contamination of the belief,
                                                              S = conformal set ∪ {x : b(x) ≥ 0.10})
```

The robust mode treats the conformal prediction set as a *set*, not a distribution — the worst case is taken over it.

### 5. Decision regret, not accuracy

```
Regret(a) = J(a_exec) − J(a*)
```

Two agents can both be "correct" and still differ enormously in operating outcome. Regret measures distance from the mathematical optimum and is the primary benchmark metric — computed under the frozen, governance-approved weight vector.

### 6. Autonomy is earned, not granted

Autonomy is the meet of independent caps — class ceiling, calibration quality, drift stability, agent mandate, cutoff pressure — and `AUTO` additionally requires the conformal calibration registry to confirm sufficient evidence for the class:

```
AUTO(a) ⇔ Safe(a) ∧ Calibrated(a) ∧ Stable(a) ∧ Authorised(a)
```

The Calibration Registry is explicit about the conformal guarantee: under exchangeability, finite-sample coverage holds regardless of calibration-set size; a small sample degrades *efficiency* (coarser sets), while coverage is genuinely threatened only by distribution shift. Classes that drift are attenuated automatically (Wasserstein, KL and CUSUM monitors).

### 7. Autonomy as an allocation problem

The Savings Lab solves a MILP that allocates autonomy ceilings across exception classes to maximise capacity released subject to expected-loss and tail-loss budgets, then a second MILP that converts residual minutes into sustainable headcount under skill floors, region constraints and control-coverage minima. The output decomposes the gap between *minutes removed* and *people released* into fragmentation and staffing rigidity — the mathematical reason an automation target is not a headcount target.

### 8. Runtime verification of formal invariants

Twelve past-time LTL invariants (`G(φ)` with `Once`/`Historically` operators) are monitored on every proposal trace in both shadow and enforcing modes. Every executed event enters a SHA-256 hash chain; tampering is detected and localised. The monitor is independent of the gate — their agreement is itself tested.

## Deployment

```bash
# Render (render.yaml included) or any WSGI host:
gunicorn app:app
```

## Tests

```bash
pytest -q
```

Property tests cover: belief calibration, exact CVaR against a brute-force reference, feasible-set invariants (ESCALATE always feasible), autonomy monotonicity, gate/invariant agreement, hash-chain tamper detection, benchmark blinding determinism, and savings-MILP constraint satisfaction.

## Relation to prior work

This prototype implements the architecture described in *Agentic Decision Mathematics: Risk-Constrained Allocation of Operational Autonomy Under Uncertainty in Financial Market Infrastructure* (Ghosh, 2026, working paper) — belief-state control rather than agent-owned state, the three-way uncertainty decomposition (state / model / outcome), CVaR as the worst (1−α) tail, conformal prediction with the efficiency-versus-coverage distinction, runtime verification of a specified invariant subset, and autonomy as a risk-constrained resource to be optimally allocated rather than a permission developers grant.

## Licence

MIT — see `LICENSE`.

## Disclaimer

All data, agents, metrics and results are synthetic and illustrative. This repository does not describe any real institution, client or system. Nothing here is investment, legal or operational advice.
