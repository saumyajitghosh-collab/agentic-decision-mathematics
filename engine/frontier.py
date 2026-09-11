"""Autonomy frontier.

Each point is an (exception class, action) pair aggregated over the synthetic
population where the action is feasible:

  Benefit  B = E[(handling − H_a) · (1 − P_fail)]    human minutes avoided per case
  Risk     R = E[P_err · Severity]

The efficient frontier keeps pairs that no other pair beats on both axes.
Horizontal thresholds r1 < r2 < r3 are the risk caps of the autonomy lattice.
"""
from functools import lru_cache
import numpy as np
from . import config as cfg
from .agents import AGENTS
from .autonomy import grant, CAP_NAMES, CAP_TEXT
from .core import evaluate
from .invariants import INVARIANTS
from .savings import class_tables
from .state import generate, seed_from
from .uncertainty import registry, drift_report


@lru_cache(maxsize=8)
def frontier(agent_idx=1, n=3000):
    cases = generate(n, seed_from("frontier", 1))
    ev = evaluate(cases)
    g = grant(cases, ev, agent_idx)
    raw = ev["raw"]
    benefit = (cases["handling"][:, None] - raw["human_minutes"]) * (1 - raw["p_fail"])
    points = []
    for c in range(cfg.C):
        m = cases["cls"] == c
        for a in range(cfg.ESC):
            f = ev["feasible"][m, a]
            if f.sum() < max(3, 0.15 * m.sum()):
                continue
            lv = g["level"][m, a][f]
            counts = np.bincount(lv, minlength=4)
            points.append(dict(
                cls=cfg.CLASSES[c]["code"], cls_name=cfg.CLASSES[c]["name"], action=cfg.ACTIONS[a]["code"],
                benefit=round(float(benefit[m, a][f].mean()), 3), risk=round(float(raw["risk"][m, a][f].mean()), 4),
                feasible_share=round(float(f.mean()), 3), irreversibility=float(cfg.ACT_IRREV[a]),
                level=cfg.LEVEL_NAMES[int(counts.argmax())],
                level_mix={cfg.LEVEL_NAMES[i]: round(float(counts[i] / f.sum()), 3) for i in range(4)},
            ))
    order = sorted(range(len(points)), key=lambda i: (-points[i]["benefit"], points[i]["risk"]))
    best_risk = np.inf
    for i in order:
        if points[i]["risk"] < best_risk:
            points[i]["efficient"] = True
            best_risk = points[i]["risk"]
        else:
            points[i]["efficient"] = False

    lam_key = tuple(sorted(cfg.DEFAULT_LAMBDAS.items()))
    _, _, _, _, mix = class_tables(agent_idx, lam_key)
    class_mix = [dict(code=cfg.CLASSES[c]["code"], name=cfg.CLASSES[c]["name"],
                      mix={cfg.LEVEL_NAMES[i]: round(float(mix[c, i]), 3) for i in range(4)}) for c in range(cfg.C)]
    return dict(agent=AGENTS[agent_idx]["name"], points=points, thresholds=dict(r1=cfg.R1, r2=cfg.R2, r3=cfg.R3),
                registry=registry(agent_idx), drift=drift_report(agent_idx), class_mix=class_mix,
                drift_thresholds=dict(w=cfg.W_EPS, kl=cfg.KL_EPS, baseline_days=cfg.DRIFT_BASELINE_DAYS,
                                      days=cfg.DRIFT_DAYS))


def catalogue():
    return dict(
        hypotheses=[dict(code=h[0], label=h[1]) for h in cfg.HYPOTHESES],
        evidence=[dict(code=e[0], label=e[1]) for e in cfg.EVIDENCE],
        classes=[dict(code=c["code"], name=c["name"], skill=c["skill"], volume=float(cfg.CLASS_VOLUME[i]),
                      handling=c["handling"], history=c["history"]) for i, c in enumerate(cfg.CLASSES)],
        actions=[dict(code=a["code"], name=a["name"], irreversibility=a["irrev"], four_eyes=a["four_eyes"],
                      alpha=round(cfg.alpha_for_action(i), 4)) for i, a in enumerate(cfg.ACTIONS)],
        agents=[dict(code=a["code"], name=a["name"], style=a["style"]) for a in AGENTS],
        levels=cfg.LEVEL_HELP, lambdas=cfg.LAMBDA_LABELS, default_lambdas=cfg.DEFAULT_LAMBDAS, presets=cfg.PRESETS,
        caps=[dict(code=c, text=CAP_TEXT[c]) for c in CAP_NAMES],
        invariants=[dict(code=c, tex=t, text=x) for c, t, x, _ in INVARIANTS],
        thresholds=dict(r1=cfg.R1, r2=cfg.R2, r3=cfg.R3, alpha_base=cfg.ALPHA_BASE),
    )
