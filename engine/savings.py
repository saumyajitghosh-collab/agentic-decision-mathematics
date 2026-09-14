"""Savings Lab: autonomy as a scarce, optimally allocated resource.

Stage 1 — allocate autonomy ceilings z_i ∈ {HUMAN, PROPOSE, APPROVE, AUTO} per class (MILP):
  max   Σ_i Σ_z x_iz · K_i(z)                         releasable capacity (minutes/day)
  s.t.  Σ_i Σ_z x_iz · EL_i(z) <= R_max               expected operational loss per day
        Σ_i Σ_z x_iz · TL_i(z) <= L_max               tail loss per day (Σ vol_i · CVaR_95 per case,
                                                       an upper bound on portfolio CVaR by subadditivity)
  M_i(z) = vol · handling · E[saving(level)]           minutes removed
  K_i(z) = vol · handling · E[saving(level) · capture(level)]
  EL_i(z) = vol · E[p_err · harm · miss(level)]         miss: share of errors reaching an effect
        Σ_z x_iz = 1,  x_iz ∈ {0, 1}
  Each case runs at min(z_i, level granted to the optimal action for that case), so
  calibration, drift, mandate and risk caps are respected inside M, EL and TL.

Stage 2 — size the workforce for the residual work (MILP):
  min   Σ_jt HC_jt + c_flex · Σ_t F_t
  s.t.  m · HC_jt + η · y_jt >= s · W_jt              capacity covers stressed workload
        Σ_j y_jt <= m · F_t                           flexible pool minutes per region
        HC_jt >= floor_j                              control coverage (four-eyes needs two)
        HC_jt, F_t ∈ Z+,  y_jt >= 0
Minutes removed and people removed diverge because of floors, integrality, stress
buffers and skill boundaries. The lab reports both.
"""
from functools import lru_cache
import numpy as np
from scipy.optimize import milp, LinearConstraint, Bounds
from . import config as cfg
from .autonomy import grant
from .core import evaluate, objective
from .state import generate, seed_from

LEVELS = [cfg.HUMAN, cfg.PROPOSE, cfg.APPROVE, cfg.AUTO]
PER_CLASS = 400


@lru_cache(maxsize=16)
def class_tables(agent_idx, lam_key):
    lam = dict(lam_key)
    M = np.zeros((cfg.C, 4))
    KC = np.zeros((cfg.C, 4))
    EL = np.zeros((cfg.C, 4))
    TL = np.zeros((cfg.C, 4))
    TL_real = np.zeros((cfg.C, 4))
    mix = np.zeros((cfg.C, 4))
    for c in range(cfg.C):
        cs = generate(PER_CLASS, seed_from("savings", c), class_idx=c)
        ev = evaluate(cs)
        J = objective(ev["comps"], lam)
        a_star = np.where(ev["feasible"], J, np.inf).argmin(1)
        idx = np.arange(PER_CLASS)
        g = grant(cs, ev, agent_idx)
        case_level = np.maximum(g["level"][idx, a_star], cfg.HUMAN)
        mix[c] = np.bincount(case_level, minlength=4) / PER_CLASS
        p_err = ev["raw"]["p_err"][idx, a_star]
        harm = cs["fail_cost"] + cfg.ACT_IRREV[a_star] * (1 - cfg.ACT_DETECT[a_star]) * cs["remediation"]
        vol, handling = cfg.CLASS_VOLUME[c], cfg.CLASS_HANDLING[c]
        for zi, z in enumerate(LEVELS):
            lvl = np.minimum(case_level, z)
            M[c, zi] = vol * handling * cfg.LEVEL_SAVING[lvl].mean()
            KC[c, zi] = vol * handling * (cfg.LEVEL_SAVING[lvl] * cfg.LEVEL_CAPTURE[lvl]).mean()
            per_case = p_err * harm * cfg.LEVEL_MISS[lvl]
            EL[c, zi] = vol * per_case.mean()
            q = np.quantile(per_case, cfg.TAIL_ALPHA)
            TL[c, zi] = vol * per_case[per_case >= q].mean()
            # Realised tail loss (Bernoulli draws from simulation truth)
            p_loss = p_err * cfg.LEVEL_MISS[lvl]
            _rng = np.random.default_rng(seed_from("savings_real", c, zi))
            _u = _rng.random(PER_CLASS)
            _fail = _u < p_loss
            _rl = _fail * harm
            _qr = np.quantile(_rl, cfg.TAIL_ALPHA)
            _tail = _rl[_rl >= _qr]
            TL_real[c, zi] = vol * (_tail.mean() if len(_tail) else 0.0)
    return M, KC, EL, TL, TL_real, mix


def allocate(KC, EL, TL, r_max, l_max):
    n = cfg.C * 4
    c = -KC.reshape(-1)
    A_eq = np.zeros((cfg.C, n))
    for i in range(cfg.C):
        A_eq[i, i * 4:(i + 1) * 4] = 1
    cons = [LinearConstraint(A_eq, 1, 1),
            LinearConstraint(EL.reshape(1, -1), -np.inf, r_max),
            LinearConstraint(TL.reshape(1, -1), -np.inf, l_max)]
    res = milp(c, constraints=cons, integrality=np.ones(n), bounds=Bounds(0, 1))
    if not res.success:
        return None
    x = np.round(res.x).reshape(cfg.C, 4)
    return x.argmax(1)


def workforce(residual_minutes):
    """residual_minutes (C,) per day -> optimal staffing."""
    J_, T_ = len(cfg.SKILLS), len(cfg.REGIONS)
    W = np.zeros((J_, T_))
    for c in range(cfg.C):
        j = cfg.SKILLS.index(cfg.CLASSES[c]["skill"])
        for t, (_, share) in enumerate(cfg.REGIONS):
            W[j, t] += residual_minutes[c] * share
    nHC, nF, nY = J_ * T_, T_, J_ * T_
    n = nHC + nF + nY
    m, eta, s = cfg.MINUTES_PER_FTE, cfg.FLEX_EFFICIENCY, cfg.STRESS_FACTOR
    cost = np.concatenate([np.ones(nHC), np.full(nF, cfg.FLEX_COST), np.zeros(nY)])
    rows, lo, hi = [], [], []
    for j in range(J_):
        for t in range(T_):
            r = np.zeros(n)
            r[j * T_ + t] = m
            r[nHC + nF + j * T_ + t] = eta
            rows.append(r); lo.append(s * W[j, t]); hi.append(np.inf)
    for t in range(T_):
        r = np.zeros(n)
        for j in range(J_):
            r[nHC + nF + j * T_ + t] = 1
        r[nHC + t] = -m
        rows.append(r); lo.append(-np.inf); hi.append(0)
    lb = np.zeros(n)
    for j, skill in enumerate(cfg.SKILLS):
        for t in range(T_):
            lb[j * T_ + t] = cfg.SKILL_FLOOR[skill]
    integrality = np.concatenate([np.ones(nHC + nF), np.zeros(nY)])
    res = milp(cost, constraints=[LinearConstraint(np.array(rows), lo, hi)], integrality=integrality,
               bounds=Bounds(lb, np.inf))
    x = res.x
    HC = np.round(x[:nHC]).reshape(J_, T_)
    F = np.round(x[nHC:nHC + nF])
    floors = np.array([[cfg.SKILL_FLOOR[sk]] * T_ for sk in cfg.SKILLS], float)
    need = s * W / m
    floor_binding = int(((HC == floors) & (floors > need)).sum())
    return dict(W=W, HC=HC, F=F, total=float(HC.sum() + F.sum()), floor_binding=floor_binding,
                stressed_need=float(need.sum()), raw_need=float((W / m).sum()))


def lab(agent_idx=1, lam=None, risk_budget=0.10, tail_budget=0.10, target=0.25, sweep=15):
    """risk_budget: allowed change in expected operational loss versus the all-human process (0.10 = +10%).
    tail_budget: allowed change in CVaR_95 tail loss versus all-human (0.10 = +10%).
    """
    lam = cfg.normalise_lambdas(lam)
    M, KC, EL, TL, TL_real, mix = class_tables(agent_idx, tuple(sorted(lam.items())))
    total_minutes = float((cfg.CLASS_VOLUME * cfg.CLASS_HANDLING).sum())
    human_el = float(EL[:, 0].sum())
    human_tl = float(TL[:, 0].sum())
    human_tl_real = float(TL_real[:, 0].sum())
    best_el, worst_el = float(EL.min(1).sum()), float(EL.max(1).sum())
    worst_tl = float(TL.max(1).sum())
    worst_tl_real = float(TL_real.max(1).sum())
    base_wf = workforce(cfg.CLASS_VOLUME * cfg.CLASS_HANDLING)
    r_max = human_el * (1 + float(risk_budget))
    l_max = human_tl * (1 + float(tail_budget))

    def solve(rm, lm):
        z = allocate(KC, EL, TL, rm, lm)
        if z is None:
            return None
        i = np.arange(cfg.C)
        wf = workforce(cfg.CLASS_VOLUME * cfg.CLASS_HANDLING - KC[i, z])
        return z, M[i, z], KC[i, z], wf

    curve = []
    lo_b, hi_b = best_el / human_el - 1, worst_el / human_el - 1
    for b in np.linspace(lo_b, hi_b, sweep):
        s_ = solve(human_el * (1 + b) + 1e-6, l_max)
        if s_ is None:
            continue
        z, removed, captured, wf = s_
        curve.append(dict(risk_budget=round(float(b), 4),
                          minutes_removed=round(float(removed.sum() / total_minutes), 4),
                          fte_reduction=round(float(1 - wf["total"] / base_wf["total"]), 4)))
    feasible_target = next((p for p in curve if p["fte_reduction"] >= target), None)

    out = dict(
        agent=agent_idx, target=target, risk_budget=float(risk_budget),
        tail_budget=float(tail_budget),
        r_max=round(r_max, 1), l_max=round(l_max, 1),
        envelope=dict(human_el=round(human_el, 1), best_budget=round(lo_b, 4), worst_budget=round(hi_b, 4),
                      human_tl=round(human_tl, 1), worst_tl=round(worst_tl, 1),
                      human_tl_real=round(human_tl_real, 1), worst_tl_real=round(worst_tl_real, 1)),
        baseline=dict(fte=base_wf["total"], minutes=round(total_minutes, 0)),
        curve=curve, target_feasible=feasible_target is not None, target_point=feasible_target,
        max_fte_reduction=max((p["fte_reduction"] for p in curve), default=0.0),
    )
    sol = solve(r_max, l_max)
    if sol is None:
        out["solution"] = None
        return out
    z, removed, captured, wf = sol
    classes = []
    for c in range(cfg.C):
        work = cfg.CLASS_VOLUME[c] * cfg.CLASS_HANDLING[c]
        classes.append(dict(code=cfg.CLASSES[c]["code"], name=cfg.CLASSES[c]["name"], skill=cfg.CLASSES[c]["skill"],
                            volume=float(cfg.CLASS_VOLUME[c]), handling=float(cfg.CLASS_HANDLING[c]),
                            ceiling=cfg.LEVEL_NAMES[LEVELS[z[c]]],
                            level_mix={cfg.LEVEL_NAMES[l]: round(float(mix[c, i]), 3) for i, l in enumerate(LEVELS)},
                            minutes_removed=round(float(removed[c]), 0), share_removed=round(float(removed[c] / work), 4),
                            capacity_released=round(float(captured[c]), 0),
                            loss_index=round(float(EL[c, z[c]] / max(EL[c, 0], 1e-9) * 100), 1)))
    minutes_pct = float(removed.sum() / total_minutes)
    captured_pct = float(captured.sum() / total_minutes)
    fte_pct = float(1 - wf["total"] / base_wf["total"])
    grid = []
    for j, sk in enumerate(cfg.SKILLS):
        for t, (reg, _) in enumerate(cfg.REGIONS):
            grid.append(dict(skill=sk, region=reg, baseline=int(base_wf["HC"][j, t]), optimised=int(wf["HC"][j, t]),
                             floor=cfg.SKILL_FLOOR[sk]))
    el = float(EL[np.arange(cfg.C), z].sum())
    out["solution"] = dict(
        classes=classes, grid=grid,
        flex=dict(baseline=[int(v) for v in base_wf["F"]], optimised=[int(v) for v in wf["F"]],
                  regions=[r for r, _ in cfg.REGIONS]),
        fte=wf["total"], minutes_removed_pct=round(minutes_pct, 4), capacity_released_pct=round(captured_pct, 4),
        fte_reduction_pct=round(fte_pct, 4),        loss_index=round(el / human_el * 100, 1),
        tail_index=round(float(TL[np.arange(cfg.C), z].sum()) / human_tl * 100, 1),
        realised_tail_index=round(float(TL_real[np.arange(cfg.C), z].sum()) / max(human_tl_real, 1) * 100, 1),
        floor_binding_cells=wf["floor_binding"],
        decomposition=dict(fragmentation=round(minutes_pct - captured_pct, 4),
                           staffing_rigidity=round(captured_pct - fte_pct, 4)),
    )
    return out
