"""Policy sensitivity.

J(a; λ) = Σ_k λ_k · c_k(a) is linear in every λ_k, so along a one-dimensional
sweep of λ_k each action is a straight line  J_a(λ_k) = β_a + λ_k · c_k(a).
The optimal action is the lower envelope of those lines, and its breakpoints are
exact line intersections — no grid search:

  λ* = (β_b − β_a) / (c_k(a) − c_k(b))   for the next action b that undercuts a.

The two-dimensional phase diagram evaluates the same linear form on a grid.
Across a population, a class is "decision-stable" when the optimal action is the
same under every stakeholder preset; otherwise the disagreement is about risk
appetite, not about the AI.
"""
from functools import lru_cache
import numpy as np
from . import config as cfg
from .arena import load_case
from .core import evaluate, objective
from .state import generate, seed_from


def lower_envelope(beta, slope, feasible, key_range):
    lo, hi = key_range
    idx = np.where(feasible)[0]
    beta, slope = beta[idx], slope[idx]
    x = lo
    vals = beta + x * slope
    tied = np.where(vals <= vals.min() + 1e-12)[0]
    cur = int(tied[np.argmin(slope[tied])])
    segments = []
    while True:
        cand = []
        for j in range(len(idx)):
            if j == cur or slope[j] >= slope[cur]:
                continue
            xc = (beta[j] - beta[cur]) / (slope[cur] - slope[j])
            if xc > x + 1e-12:
                cand.append((xc, j))
        if not cand:
            segments.append(dict(action=cfg.ACTIONS[idx[cur]]["code"], start=round(float(x), 4), end=round(float(hi), 4)))
            break
        xc, j = min(cand)
        # tie-break: among lines crossing at the same point take the smallest slope
        ties = [jj for (xx, jj) in cand if abs(xx - xc) < 1e-9]
        j = min(ties, key=lambda jj: slope[jj])
        if xc >= hi:
            segments.append(dict(action=cfg.ACTIONS[idx[cur]]["code"], start=round(float(x), 4), end=round(float(hi), 4)))
            break
        segments.append(dict(action=cfg.ACTIONS[idx[cur]]["code"], start=round(float(x), 4), end=round(float(xc), 4)))
        x, cur = xc, j
    return segments


def analyse(case_id, lam=None, x_key="F", y_key="H", res=17, span=3.0, sweep_key=None):
    lam = cfg.normalise_lambdas(lam)
    cases, spec = load_case(case_id)
    ev = evaluate(cases)
    comps = {k: v[0] for k, v in ev["comps"].items()}
    feasible = ev["feasible"][0]

    presets = []
    for name, p in cfg.PRESETS.items():
        J = objective({k: v[None] for k, v in comps.items()}, p)[0]
        a = int(np.where(feasible, J, np.inf).argmin())
        presets.append(dict(name=name, lambdas=p, action=cfg.ACTIONS[a]["code"]))
    stable = len({p["action"] for p in presets}) == 1

    xs = np.linspace(0, span, res)
    ys = np.linspace(0, span, res)
    base = sum(lam[k] * comps[k] for k in cfg.LAMBDA_KEYS if k not in (x_key, y_key))
    grid = base[None, None, :] + xs[None, :, None] * comps[x_key][None, None, :] + ys[:, None, None] * comps[y_key][None, None, :]
    grid = np.where(feasible[None, None, :], grid, np.inf)
    phase = grid.argmin(-1)
    codes = [cfg.ACTIONS[a]["code"] for a in range(cfg.A)]

    sweeps = {}
    for k in ([sweep_key] if sweep_key else cfg.LAMBDA_KEYS):
        beta = sum(lam[j] * comps[j] for j in cfg.LAMBDA_KEYS if j != k)
        segs = lower_envelope(beta, comps[k], feasible, (0.0, 5.0))
        sweeps[k] = dict(segments=segs, current=lam[k],
                         breakpoints=[s["start"] for s in segs[1:]])

    J_now = objective({k: v[None] for k, v in comps.items()}, lam)[0]
    a_now = int(np.where(feasible, J_now, np.inf).argmin())
    return dict(
        case=dict(id=spec["id"], title=spec["title"]), lambdas=lam, x_key=x_key, y_key=y_key,
        xs=[round(float(v), 3) for v in xs], ys=[round(float(v), 3) for v in ys],
        phase=[[codes[int(a)] for a in row] for row in phase],
        presets=presets, stable=stable, current=cfg.ACTIONS[a_now]["code"], sweeps=sweeps,
        components={k: {codes[a]: round(float(comps[k][a]), 4) for a in range(cfg.A) if feasible[a]} for k in cfg.LAMBDA_KEYS},
    )


@lru_cache(maxsize=4)
def population_stability(n=2400, seed=5):
    cases = generate(n, seed_from("stability", seed))
    ev = evaluate(cases)
    choices = []
    for name, p in cfg.PRESETS.items():
        J = objective(ev["comps"], p)
        choices.append(np.where(ev["feasible"], J, np.inf).argmin(1))
    choices = np.stack(choices, 1)
    agree = (choices == choices[:, :1]).all(1)
    rows = []
    for c in range(cfg.C):
        m = cases["cls"] == c
        # most common disagreement: which preset departs from Operations most often
        ops = list(cfg.PRESETS).index("Operations")
        departs = {name: float((choices[m, i] != choices[m, ops]).mean()) for i, name in enumerate(cfg.PRESETS) if i != ops}
        rows.append(dict(code=cfg.CLASSES[c]["code"], name=cfg.CLASSES[c]["name"], n=int(m.sum()),
                         stable_share=round(float(agree[m].mean()), 4),
                         departs={k: round(v, 4) for k, v in departs.items()}))
    return dict(overall=round(float(agree.mean()), 4), classes=rows)
