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
Agent proposes  →  Mathematics evaluates  →  Mathematics optimises  →  Gate authorises  →  System executes*(the only AI stage)      (deterministic)           (deterministic)        (formal invariants)     (hash-chained)
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
    ₁:ₜ           b(x)           p̂(x), Γα(x)            A_safe          a*            ℓ = ⋀ caps            G(φ)     hash chain
                                  (only agentic stage)
```

``b``a