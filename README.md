# Agentic Decision Mathematics

**AI proposes. Mathematics decides what is permissible, optimal and sufficiently certain. Controls decide whether it executes.**

A pure-maths control plane for agentic AI in securities operations. Any agent â€” an LLM, a vendor model, a rules engine â€” proposes an action for an operational exception. A deterministic engine maintains the *belief* about what is actually wrong, bounds what may be done, finds the optimal action, decides how much autonomy is earned, and enforces formally specified controls before anything executes.

**No language model sits in the decision path.** Every number in the interface is computed live by the engine.

> **Synthetic data only.** Exception classes, volumes, likelihoods, corts, agents and thresholds are illustrative assumptions in `engine/config.py`. Replace them with institution data before drawing any operational conclusion.

---

## The question this application answers

> *Can we create a pure-maths based AI application which improves the Agentic AI work being done?*

Yes â€” by inverting the architecture. The prevailing pattern is **agent thinks â†’ agent decides â†’ agent executes**. This application implements the alternative:

```
Agent proposes  â†’  Mathematics evaluates  â†’  Mathematics optimises  â†’  Gate authorises  â†’  System executes
(the only AI stage)      (deterministic)           (deterministic)        (formal invariants)     (hash-chained)
```

The agent does not even own the state of the world. It may propose an *interpretation* of the evidence; the control layer maintains the operational belief state. The LLM supplies intelligence; mathematics supplies bounds, proof, optimisation and execution authority.

## Quick start

```bash
pip install -r requirements.txt

# 1. CLI demo â€” the full pipeline, no web server:
python demo.py

# 2. Web application â€” six screens:
python app.py            # then open http://localhost:5000

# 3. Tests (20 property tests over the mathematics and controls):
pip install -r requirements-dev.txt
pytest
```

`demo.py` runs four stages end to end: one curated case through belief â†’ proposals â†’ feasible set â†’ optimiser â†’ autonomy â†’ gate â†’ regret; a pre-registered blinded population benchmark; the capacity-constrained savings lab; and a runtime-invariant verification replay with a tamper-evident hash chain.

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
Observations â”€â–º Belief state â”€â–º Agent interpretation â”€â–º Feasible set â”€â–º Optimiser â”€â–º Autonomy lattice â”€â–º Gate â”€â–º Execution
   Oâ‚:â‚œ          b(x)            pÌ‚(x), Î“Î±(x)            A_safe          a*            â„“ = â‹€ caps          G(Ï†)     hash chain
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
  uncertainty.py       split conformal calibration registry, drift detection (Wâ‚, KL, CUSUM)
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

The engine is model-agnostic. Any external agent â€” commercial LLM, in-house model, deterministic classifier â€” can submit proposals through one contract:

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

The engine never treats the operational state as known. For root-cause hypotheses *x* and observed evidence *oâ‚‘* with reliability *râ‚‘ âˆˆ (0, 1]*:

```
b(x) âˆ P(x) Â· Î â‚‘ P(oâ‚‘ | x)^râ‚‘
```

The reliability exponent (a power posterior) lets a stale counterparty message move the belief less than a golden-source record. Normalised entropy `U = H(b) / log|X|` feeds the autonomy score.

### 2. Outcome uncertainty and the objective

For action *a*, resolution before cutoff happens with probability `p_it(x, a)`. Loss:

```
L = câ‚ + wÂ·Hâ‚ + (1 âˆ’ y) Â· m Â· (fail + irrevâ‚ Â· (1 âˆ’ detectâ‚) Â· remediation),   m ~ LogNormal, E[m] = 1
```

CVaR at 95% is computed **exactly** on a discretised loss distribution (Rockafellarâ€“Uryasev), not by Monte Carlo. Operational risk is `R(a) = P_err(a) Â· Severity(a)`, with severity weighting exposure, irreversibility, detectability, propagation and control severity.

```
J(a) = Î»_CÂ·E[L]/C_ref + Î»_RÂ·R + Î»_TÂ·E[T]/24 + Î»_HÂ·H/60 + Î»_FÂ·P_fail + Î»_KÂ·CVaRâ‚‰â‚…/Â}É•˜)€()Ù•ÉäÑ•É´¥Ì¹½Éµ…±¥Í•Ñ¼„½µµ•¹ÍÕÉ…Ñ”Í…±”‰•™½É”Ý•¥¡Ñ¥¹œ¸Q¡”Ý•¥¡ÑÌƒ:ì…É”€¨©½Ù•É¹…¹”½‰©•ÑÌ¨¨°Í•Ð‰äÍÑ…­•¡½±‘•ÉÌ°¹½Ð‰äÑ¡”µ½‘•°ƒŠP…¹Ñ¡”A½±¥äM•¹Í¥Ñ¥Ù¥ÑäÍÉ••¸•áÁ½Í•Ì•á…Ñ±äÝ¡•É”Ñ¡”½ÁÑ¥µ…°…Ñ¥½¸¡…¹•Ì…ÌÑ¡•äµ½Ù”¸((ŒŒŒ€Ì¸•…Í¥‰±”Í•Ð()€)}Í…™”€ôì„€èœ¡à°„¤ƒŠ&€À°€ ¡à°„¤€ô€À°€ƒ>¡à°„¤€ôQIUô)€((¨€¨©œ¨¨è¹½Ñ¥½¹…°Ý¥Ñ¡¥¸Ñ¡”…Ñ¥½¸Ì±¥µ¥ÐìY…HƒŠ&µ…à¡™±½½È°‰ÁÌƒ
Ü¹½Ñ¥½¹…°¥€ìÉ¥Í¬‰•±½ÜÑ¡”‘•¹¥…°Ñ¡É•Í¡½±¸(¨€¨© ¨¨è‘•±…É•™¥•±¡…¹•ÌµÕÍÐ‰”„ÍÕ‰Í•Ð½˜Ñ¡”…Ñ¥½¸Ì…ÕÑ¡½É¥Í•¡…¹•Ì€¡™¥•±¥¹Ù…É¥…¹”¤¸(¨€¨«>¨¨èMM$¡…¹•Ì¹••…¸…ÁÁÉ½Ù•½±‘•¸Í½ÕÉ”ìÍ•ÑÑ±•µ•¹Ð¥¹ÍÑÉÕÑ¥½¹Ì¹••„Ù…±¥Á±…”½˜Í•ÑÑ±•µ•¹Ðì…¹•°½É•Á±…”¹••‘ÌÑ¡”½É¥¥¹…°±¥¹­•¸()M1Q€¥Ì…±Ý…åÌ™•…Í¥‰±”°Í¼Ñ¡”™•…Í¥‰±”Í•Ð¥Ì¹•Ù•È•µÁÑä¸((ŒŒŒ€Ð¸Q¡É•”½ÁÑ¥µ¥Í…Ñ¥½¸µ½‘•Ì()€)•áÁ•Ñ•€€„¨€ô…Éµ¥¹}í}Í…™•ô}‰m)t€€€€€€€€€€€€€€€€€€€€€€£:í},€ô€À¤)Ù…È€€€€€€„¨€ô…Éµ¥¹}í}Í…™•ô}‰m)t€¬ƒ:í}/
ÝY…I:Ä€€€€€€€€€€¡‘•™…Õ±Ð¤)É½‰ÕÍÐ€€€€„¨€ô…Éµ¥¹}í…ôµ…á}íàƒŠ" Mô(¡„ð€ ÇŠ"K:Ô¥ˆ€¬ƒ:×:Ñ}à¤€€€£:Ôµ½¹Ñ…µ¥¹…Ñ¥½¸½˜Ñ¡”‰•±¥•˜°(€€€€€€€€€€€€€€€€€€€€€€€€€€€€€€€€€€€€€€€€€€€€€€€€€€€€€€€€€€€€€L€ô½¹™½Éµ…°Í•ÐƒŠ"¨íà€èˆ¡à¤ƒŠ&”€À¸ÄÁô¤)€()Q¡”É½‰ÕÍÐµ½‘”ÑÉ•…ÑÌÑ¡”½¹™½Éµ…°ÁÉ•‘¥Ñ¥½¸Í•Ð…Ì„€©Í•Ð¨°¹½Ð„‘¥ÍÑÉ¥‰ÕÑ¥½¸ƒŠPÑ¡”Ý½ÉÍÐ…Í”¥ÌÑ…­•¸½Ù•È¥Ð¸((ŒŒŒ€Ô¸•¥Í¥½¸É•É•Ð°¹½Ð…ÕÉ…ä()€)I•É•Ð¡„¤€ô(¡…}•á•Œ¤ƒŠ"H(¡„¨¤)€()QÝ¼…•¹ÑÌ…¸‰½Ñ ‰”€‰½ÉÉ•Ðˆ…¹ÍÑ¥±°‘¥™™•È•¹½Éµ½ÕÍ±ä¥¸½Á•É…Ñ¥¹œ½ÕÑ½µ”¸I•É•Ðµ•…ÍÕÉ•Ì‘¥ÍÑ…¹”™É½´Ñ¡”µ…Ñ¡•µ…Ñ¥…°½ÁÑ¥µÕ´…¹¥ÌÑ¡”ÁÉ¥µ…Éä‰•¹¡µ…É¬µ•ÑÉ¥ŒƒŠP½µÁÕÑ•Õ¹‘•ÈÑ¡”™É½é•¸°½Ù•É¹…¹”µ…ÁÁÉ½Ù•Ý•¥¡ÐÙ•Ñ½È¸((ŒŒŒ€Ø¸ÕÑ½¹½µä¥Ì•…É¹•°¹½ÐÉ…¹Ñ•()ÕÑ½¹½µä¥ÌÑ¡”µ••Ð½˜¥¹‘•Á•¹‘•¹Ð…ÁÌƒŠP±…ÍÌ•¥±¥¹œ°…±¥‰É…Ñ¥½¸ÅÕ…±¥Ñä°‘É¥™ÐÍÑ…‰¥±¥Ñä°…•¹Ðµ…¹‘…Ñ”°ÕÑ½™˜ÁÉ•ÍÍÕÉ”ƒŠP…¹UQ=€…‘‘¥Ñ¥½¹…±±äÉ•ÅÕ¥É•ÌÑ¡”½¹™½Éµ…°…±¥‰É…Ñ¥½¸É•¥ÍÑÉäÑ¼½¹™¥É´ÍÕ™™¥¥•¹Ð•Ù¥‘•¹”™½ÈÑ¡”±…ÍÌè()€)UQ<¡„¤ƒŠPM…™”¡„¤ƒŠ"œ…±¥‰É…Ñ•¡„¤ƒŠ"œMÑ…‰±”¡„¤ƒŠ"œÕÑ¡½É¥Í•¡„¤)€()Q¡”…±¥‰É…Ñ¥½¸I•¥ÍÑÉä¥Ì•áÁ±¥¥Ð…‰½ÕÐÑ¡”½¹™½Éµ…°Õ…É…¹Ñ•”èÕ¹‘•È•á¡…¹•…‰¥±¥Ñä°™¥¹¥Ñ”µÍ…µÁ±”½Ù•É…”¡½±‘ÌÉ•…É‘±•ÍÌ½˜…±¥‰É…Ñ¥½¸µÍ•ÐÍ¥é”ì„Íµ…±°Í…µÁ±”‘•É…‘•Ì€©•™™¥¥•¹ä¨€¡½…ÉÍ•ÈÍ•ÑÌ¤°Ý¡¥±”½Ù•É…”¥Ì•¹Õ¥¹•±äÑ¡É•…Ñ•¹•½¹±ä‰ä‘¥ÍÑÉ¥‰ÕÑ¥½¸Í¡¥™Ð¸±…ÍÍ•ÌÑ¡…Ð‘É¥™Ð…É”…ÑÑ•¹Õ…Ñ•…ÕÑ½µ…Ñ¥…±±ä€¡]…ÍÍ•ÉÍÑ•¥¸°-0…¹UMU4µ½¹¥Ñ½ÉÌ¤¸((ŒŒŒ€Ü¸ÕÑ½¹½µä…Ì…¸…±±½…Ñ¥½¸ÁÉ½‰±•´()Q¡”M…Ù¥¹Ì1…ˆÍ½±Ù•Ì„5%1@Ñ¡…Ð…±±½…Ñ•Ì…ÕÑ½¹½µä•¥±¥¹Ì…É½ÍÌ•á•ÁÑ¥½¸±…ÍÍ•ÌÑ¼µ…á¥µ¥Í”…Á…¥ÑäÉ•±•…Í•ÍÕ‰©•ÐÑ¼•áÁ•Ñ•µ±½ÍÌ…¹Ñ…¥°µ±½ÍÌ‰Õ‘•ÑÌ°Ñ¡•¸„Í•½¹5%1@Ñ¡…Ð½¹Ù•ÉÑÌÉ•Í¥‘Õ…°µ¥¹ÕÑ•Ì¥¹Ñ¼ÍÕÍÑ…¥¹…‰±”¡•…‘½Õ¹ÐÕ¹‘•ÈÍ­¥±°™±½½ÉÌ°É•¥½¸½¹ÍÑÉ…¥¹ÑÌ…¹½¹ÑÉ½°µ½Ù•É…”µ¥¹¥µ„¸Q¡”½ÕÑÁÕÐ‘•½µÁ½Í•ÌÑ¡”…À‰•ÑÝ••¸€©µ¥¹ÕÑ•ÌÉ•µ½Ù•¨…¹€©Á•½Á±”É•±•…Í•¨¥¹Ñ¼™É…µ•¹Ñ…Ñ¥½¸…¹ÍÑ…™™¥¹œÉ¥¥‘¥ÑäƒŠPÑ¡”µ…Ñ¡•µ…Ñ¥…°É•…Í½¸…¸…ÕÑ½µ…Ñ¥½¸Ñ…É•Ð¥Ì¹½Ð„¡•…‘½Õ¹ÐÑ…É•Ð¸((ŒŒŒ€à¸IÕ¹Ñ¥µ”Ù•É¥™¥…Ñ¥½¸½˜™½Éµ…°¥¹Ù…É¥…¹ÑÌ()QÝ•±Ù”Á…ÍÐµÑ¥µ”1Q0¥¹Ù…É¥…¹ÑÌ€¡£>¥€Ý¥Ñ =¹•€½!¥ÍÑ½É¥…±±å€½Á•É…Ñ½ÉÌ¤…É”µ½¹¥Ñ½É•½¸•Ù•ÉäÁÉ½Á½Í…°ÑÉ…”¥¸‰½Ñ Í¡…‘½Ü…¹•¹™½É¥¹œµ½‘•Ì¸Ù•Éä•á•ÕÑ••Ù•¹Ð•¹Ñ•ÉÌ„M!´ÈÔØ¡…Í ¡…¥¸ìÑ…µÁ•É¥¹œ¥Ì‘•Ñ•Ñ•…¹±½…±¥Í•¸Q¡”µ½¹¥Ñ½È¥Ì¥¹‘•Á•¹‘•¹Ð½˜Ñ¡”…Ñ”ƒŠPÑ¡•¥È…É••µ•¹Ð¥Ì¥ÑÍ•±˜Ñ•ÍÑ•¸((ŒŒ•Á±½åµ•¹Ð()‰…Í (ŒI•¹‘•È€¡É•¹‘•È¹å…µ°¥¹±Õ‘•¤½È…¹ä]M$¡½ÍÐè)Õ¹¥½É¸…ÁÀé…ÁÀ)€((ŒŒQ•ÍÑÌ()‰…Í )ÁåÑ•ÍÐ€µÄ)€()AÉ½Á•ÉÑäÑ•ÍÑÌ½Ù•Èè‰•±¥•˜…±¥‰É…Ñ¥½¸°•á…ÐY…H……¥¹ÍÐ„‰ÉÕÑ”µ™½É”É•™•É•¹”°™•…Í¥‰±”µÍ•Ð¥¹Ù…É¥…¹ÑÌ€¡M1Q…±Ý…åÌ™•…Í¥‰±”¤°…ÕÑ½¹½µäµ½¹½Ñ½¹¥¥Ñä°…Ñ”½¥¹Ù…É¥…¹Ð…É••µ•¹Ð°¡…Í µ¡…¥¸Ñ…µÁ•È‘•Ñ•Ñ¥½¸°‰•¹¡µ…É¬‰±¥¹‘¥¹œ‘•Ñ•Éµ¥¹¥Í´°…¹Í…Ù¥¹Ìµ5%1@½¹ÍÑÉ…¥¹ÐÍ…Ñ¥Í™…Ñ¥½¸¸((ŒŒI•±…Ñ¥½¸Ñ¼ÁÉ¥½ÈÝ½É¬()Q¡¥ÌÁÉ½Ñ½ÑåÁ”¥µÁ±•µ•¹ÑÌÑ¡”…É¡¥Ñ•ÑÕÉ”‘•ÍÉ¥‰•¥¸€©•¹Ñ¥Œ•¥Í¥½¸5…Ñ¡•µ…Ñ¥ÌèI¥Í¬µ½¹ÍÑÉ…¥¹•±±½…Ñ¥½¸½˜=Á•É…Ñ¥½¹…°ÕÑ½¹½µäU¹‘•ÈU¹•ÉÑ…¥¹Ñä¥¸¥¹…¹¥…°5…É­•Ð%¹™É…ÍÑÉÕÑÕÉ”¨€¡¡½Í °€ÈÀÈØ°Ý½É­¥¹œÁ…Á•È¤ƒŠP‰•±¥•˜µÍÑ…Ñ”½¹ÑÉ½°É…Ñ¡•ÈÑ¡…¸…•¹Ðµ½Ý¹•ÍÑ…Ñ”°Ñ¡”Ñ¡É•”µÝ…äÕ¹•ÉÑ…¥¹Ñä‘•½µÁ½Í¥Ñ¥½¸€¡ÍÑ…Ñ”€¼µ½‘•°€¼½ÕÑ½µ”¤°Y…H…ÌÑ¡”Ý½ÉÍÐ€ ÇŠ"K:Ä¤Ñ…¥°°½¹™½Éµ…°ÁÉ•‘¥Ñ¥½¸Ý¥Ñ Ñ¡”•™™¥¥•¹äµÙ•ÉÍÕÌµ½Ù•É…”‘¥ÍÑ¥¹Ñ¥½¸°ÉÕ¹Ñ¥µ”Ù•É¥™¥…Ñ¥½¸½˜„ÍÁ•¥™¥•¥¹Ù…É¥…¹ÐÍÕ‰Í•Ð°…¹…ÕÑ½¹½µä…Ì„É¥Í¬µ½¹ÍÑÉ…¥¹•É•Í½ÕÉ”Ñ¼‰”½ÁÑ¥µ…±±ä…±±½…Ñ•É…Ñ¡•ÈÑ¡…¸„Á•Éµ¥ÍÍ¥½¸‘•Ù•±½Á•ÉÌÉ…¹Ð¸((ŒŒ1¥•¹”()5%PƒŠPÍ•”1%9M€¸((ŒŒ¥Í±…¥µ•È()±°‘…Ñ„°…•¹ÑÌ°µ•ÑÉ¥Ì…¹É•ÍÕ±ÑÌ…É”Íå¹Ñ¡•Ñ¥Œ…¹¥±±ÕÍÑÉ…Ñ¥Ù”¸Q¡¥ÌÉ•Á½Í¥Ñ½Éä‘½•Ì¹½Ð‘•ÍÉ¥‰”…¹äÉ•…°¥¹ÍÑ¥ÑÕÑ¥½¸°±¥•¹Ð½ÈÍåÍÑ•´¸9½Ñ¡¥¹œ¡•É”¥Ì¥¹Ù•ÍÑµ•¹Ð°±•…°½È½Á•É…Ñ¥½¹…°…‘Ù¥”¸(