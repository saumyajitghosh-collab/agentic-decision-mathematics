"""Decision Arena: several agents, one operational state, one mathematical judge.

Three optimisation modes over the feasible set A_safe:
  expected   a* = argmin E_{x~b}[J(a | x)]                (tail weight λ_K = 0)
  cvar       a* = argmin E[J] with λ_K·CVaR_α tail term     (default)
  robust     a* = argmin max_{x ∈ S} J(a | (1−ε)·b + ε·δ_x),  S = Γ_α(agent) ∪ {x : b(x) >= 0.10}
             (distributionally robust over an ε-contamination ambiguity set of the belief)

Regret of a proposal:  Regret(a) = J(a_exec) − J(a*),  where a_exec is the
proposal if the gate admits it, otherwise ESCALATE.
"""
import numpy as np
from . import config as cfg
from .agents import AGENTS, AGENT_INDEX, propose
from .autonomy import grant, binding_names, CAP_NAMES
from .core import evaluate, objective, decode_reasons
from .gate import decide, authorised_changes
from .state import posterior, entropy_norm, evidence_contributions, seed_from, generate
from .uncertainty import conformal_set_for, calibration_status, drift_report

EV_CODES = [e[0] for e in cfg.EVIDENCE]
CLS_CODES = [c["code"] for c in cfg.CLASSES]

CASES = [
    dict(id="EXC-48291", title="SSI break with a golden-source mismatch", cls="SSI_BREAK",
         story="Instruction rejected by the counterparty. Golden-source SSI differs from what was sent.",
         obs={"GOLDEN_SSI_DIFF": (1, .97), "CPTY_NMAT": (1, .85), "CPTY_SSI_UPDATED": (0, .80),
              "PSET_NONDEFAULT": (0, .95), "POSITION_SHORT": (0, .95), "CASH_NEGATIVE": (0, .95),
              "ECON_TOLERANCE": (0, .95), "FEED_LAG": (0, .70)},
         notional=3.2e6, cutoff_h=6.0, ssi_ok=True, pset_ok=True, linked=True),
    dict(id="EXC-51307", title="Unconfirmed instruction in a drifting class", cls="UNCONFIRMED",
         story="Counterparty has not confirmed. Its SSI record changed this week. This class is drifting.",
         obs={"GOLDEN_SSI_DIFF": (0, .90), "CPTY_NMAT": (1, .70), "CPTY_SSI_UPDATED": (1, .65),
              "ECON_TOLERANCE": (0, .90), "POSITION_SHORT": (0, .90), "CASH_NEGATIVE": (0, .90)},
         notional=2.4e6, cutoff_h=9.0, ssi_ok=True, pset_ok=True, linked=True),
    dict(id="EXC-50144", title="Securities shortfall four hours before cutoff", cls="SEC_FAIL",
         story="Position projection shows a shortfall four hours before cutoff on an 18m trade.",
         obs={"POSITION_SHORT": (1, .95), "FEED_LAG": (1, .60), "CASH_NEGATIVE": (0, .90),
              "ECON_TOLERANCE": (0, .95), "GOLDEN_SSI_DIFF": (0, .95)},
         notional=18e6, cutoff_h=4.0, ssi_ok=True, pset_ok=True, linked=True),
    dict(id="EXC-49872", title="Price break outside matching tolerance", cls="MATCH_BREAK",
         story="Counterparty reports unmatched details; price differs beyond tolerance.",
         obs={"ECON_TOLERANCE": (1, .98), "CPTY_NMAT": (1, .80), "GOLDEN_SSI_DIFF": (0, .95),
              "PSET_NONDEFAULT": (0, .95), "FEED_LAG": (0, .70), "POSITION_SHORT": (0, .90)},
         notional=4.0e6, cutoff_h=7.0, ssi_ok=True, pset_ok=True, linked=True),
    dict(id="EXC-50919", title="Corporate action on a pending trade", cls="CORP_ACTION",
         story="A distribution changed entitlements on a pending trade. Only 87 historical cases exist.",
         obs={"ECON_TOLERANCE": (1, .90), "POSITION_SHORT": (1, .80), "CASH_NEGATIVE": (0, .85),
              "GOLDEN_SSI_DIFF": (0, .95)},
         notional=5.5e6, cutoff_h=8.0, ssi_ok=True, pset_ok=True, linked=True),
    dict(id="EXC-51566", title="PSET or SSI? Conflicting, low-reliability evidence", cls="PSET_BREAK",
         story="Evidence points two ways and the SSI golden-source update is still awaiting approval.",
         obs={"GOLDEN_SSI_DIFF": (1, .60), "PSET_NONDEFAULT": (1, .70), "CPTY_NMAT": (1, .60),
              "FEED_LAG": (1, .55), "ECON_TOLERANCE": (0, .90)},
         notional=6.0e6, cutoff_h=5.0, ssi_ok=False, pset_ok=True, linked=True),
]
CASE_INDEX = {c["id"]: i for i, c in enumerate(CASES)}


def build_case(spec):
    c = CLS_CODES.index(spec["cls"])
    obs = np.full((1, cfg.E), -1)
    rel = np.ones((1, cfg.E))
    for code, (v, r) in spec["obs"].items():
        e = EV_CODES.index(code)
        obs[0, e], rel[0, e] = v, r
    prior = cfg.PRIORS[[c]]
    size = np.sqrt(spec["notional"] / cfg.CLASS_NOTIONAL[c])
    rng = np.random.default_rng(seed_from("case", spec["id"]))
    cases = dict(
        cls=np.array([c]), x_true=np.array([-1]), obs=obs, rel=rel, prior=prior,
        notional=np.array([spec["notional"]]), cutoff_h=np.array([spec["cutoff_h"]]),
        ssi_ok=np.array([spec["ssi_ok"]]), pset_ok=np.array([spec["pset_ok"]]), linked=np.array([spec["linked"]]),
        handling=cfg.CLASS_HANDLING[[c]], fail_cost=np.array([cfg.CLASS_FAIL[c] * size]),
        remediation=np.array([cfg.REMEDIATION_BASE * size]), propagation=cfg.CLASS_PROP[[c]],
        noise=rng.standard_normal((1, 3, cfg.K)), drift=np.array([c == cfg.DRIFT_CLASS]),
    )
    cases["belief"] = posterior(prior, obs, rel)
    return cases


def _repeat(cases, n):
    return {k: (np.repeat(v, n, axis=0) if isinstance(v, np.ndarray) else v) for k, v in cases.items()}


def _mode_lambdas(lam, mode):
    lam = cfg.normalise_lambdas(lam)
    if mode == "expected":
        lam["K"] = 0.0
    return lam


def load_case(case_id):
    if case_id in CASE_INDEX:
        spec = CASES[CASE_INDEX[case_id]]
        return build_case(spec), dict(spec, true_state=None)
    try:
        n = int(str(case_id).split("-")[-1])
    except ValueError:
        raise KeyError(f"Unknown case {case_id}")
    cases = generate(1, seed_from("arena", n))
    c = int(cases["cls"][0])
    spec = dict(id=f"RND-{n}", title=f"Sampled case: {cfg.CLASSES[c]['name']}", cls=cfg.CLASSES[c]["code"],
                story="Drawn from the synthetic population. The simulated true root cause is shown for "
                      "teaching only; the engine and the agents never see it.",
                notional=float(cases["notional"][0]), cutoff_h=round(float(cases["cutoff_h"][0]), 1),
                ssi_ok=bool(cases["ssi_ok"][0]), pset_ok=bool(cases["pset_ok"][0]), linked=bool(cases["linked"][0]),
                true_state=cfg.HYPOTHESES[int(cases["x_true"][0])][0])
    return cases, spec


def analyse(case_id, lam=None, mode="cvar", operating_agent="B"):
    cases, spec = load_case(case_id)
    lam = _mode_lambdas(lam, mode)
    op = AGENT_INDEX.get(operating_agent, 1)
    c_idx = int(cases["cls"][0])
    ev = evaluate(cases)
    feasible = ev["feasible"][0]
    J = objective(ev["comps"], lam)[0]

    # contaminated beliefs (1−ε)·b + ε·δ_x for the robust mode
    cond = _repeat(cases, cfg.K)
    contaminated = (1 - cfg.ROBUST_EPS) * cases["belief"] + cfg.ROBUST_EPS * np.eye(cfg.K)
    ev_x = evaluate(cond, belief=contaminated)
    J_x = objective(ev_x["comps"], lam)                    # (K, A)

    agents_out, sets = [], {}
    for ag_idx, ag in enumerate(AGENTS):
        a_prop, req, p_hat = propose(ag_idx, cases)
        a_prop, req, p_hat = int(a_prop[0]), int(req[0]), p_hat[0]
        g = grant(cases, ev, ag_idx)
        alpha = cfg.alpha_for_action(a_prop)
        s, q = conformal_set_for(ag_idx, c_idx, p_hat, alpha)
        sets[ag_idx] = s
        d = decide(0, a_prop, req, True, authorised_changes(a_prop), ev, g)
        agents_out.append(dict(
            code=ag["code"], name=ag["name"], style=ag["style"],
            p_hat=[round(float(v), 4) for v in p_hat], stated_confidence=round(float(p_hat.max()), 3),
            proposal=cfg.ACTIONS[a_prop]["code"], proposal_idx=a_prop, requested=cfg.LEVEL_NAMES[req],
            alpha=round(alpha, 4), q_hat=None if q is None else round(q, 4),
            conformal_set=[cfg.HYPOTHESES[k][0] for k in range(cfg.K) if s[k]],
            conformal_size=int(s.sum()), gate=d["decision"], granted=cfg.LEVEL_NAMES[d["level"]],
            gate_reasons=d["reasons"], binding=d["binding"],
            executed=cfg.ACTIONS[a_prop]["code"] if d["decision"] == "ALLOW" else "ESCALATE",
            executed_idx=a_prop if d["decision"] == "ALLOW" else cfg.ESC,
        ))

    b = cases["belief"][0]
    robust_set = sets[op] | (b >= 0.10)
    J_rob = np.where(robust_set[:, None], J_x, -np.inf).max(0)
    score = J_rob if mode == "robust" else J
    score_m = np.where(feasible, score, np.inf)
    a_star = int(score_m.argmin())

    g_op = grant(cases, ev, op)
    for a in agents_out:
        a["regret"] = round(float(score[a["executed_idx"]] - score[a_star]), 4)
        a["agrees"] = a["executed_idx"] == a_star

    actions = []
    raw = ev["raw"]
    for a in range(cfg.A):
        actions.append(dict(
            code=cfg.ACTIONS[a]["code"], name=cfg.ACTIONS[a]["name"], feasible=bool(feasible[a]),
            reasons=decode_reasons(ev["reason_mask"][0, a]), irreversibility=float(cfg.ACT_IRREV[a]),
            weighted={k: round(float(lam[k] * ev["comps"][k][0, a]), 4) for k in cfg.LAMBDA_KEYS},
            expected_loss=round(float(raw["expected_loss"][0, a]), 1), cvar=round(float(raw["cvar"][0, a]), 1),
            risk=round(float(raw["risk"][0, a]), 4), p_fail=round(float(raw["p_fail"][0, a]), 4),
            p_err=round(float(raw["p_err"][0, a]), 4),
            expected_hours=round(float(raw["expected_hours"][0, a]), 2),
            human_minutes=round(float(raw["human_minutes"][0, a]), 1),
            J=round(float(J[a]), 4), J_robust=round(float(J_rob[a]), 4),
            level=cfg.LEVEL_NAMES[int(g_op["level"][0, a])],
            caps={CAP_NAMES[k]: cfg.LEVEL_NAMES[int(g_op["caps"][0, a, k])] for k in range(len(CAP_NAMES))},
            binding=binding_names(g_op["binding"][0, a]),
            autonomy_score=round(float(g_op["score"][0, a]), 3),
            optimal=a == a_star,
        ))

    exp_star = int(np.where(feasible, objective(ev["comps"], _mode_lambdas(lam, "expected"))[0], np.inf).argmin())
    cvar_star = int(np.where(feasible, J, np.inf).argmin())
    rob_star = int(np.where(feasible, J_rob, np.inf).argmin())
    drift = drift_report(op)[c_idx]
    calib = calibration_status(op, c_idx, cfg.alpha_for_action(a_star))

    return dict(
        case=dict(id=spec["id"], title=spec["title"], story=spec["story"], cls=cfg.CLASSES[c_idx]["name"],
                  cls_code=spec["cls"], notional=spec["notional"], cutoff_h=spec["cutoff_h"],
                  ssi_ok=spec["ssi_ok"], pset_ok=spec["pset_ok"], linked=spec["linked"],
                  handling=float(cfg.CLASS_HANDLING[c_idx]), true_state=spec.get("true_state")),
        hypotheses=[dict(code=h[0], label=h[1]) for h in cfg.HYPOTHESES],
        prior=[round(float(v), 4) for v in cases["prior"][0]],
        belief=[round(float(v), 4) for v in b],
        uncertainty=round(float(entropy_norm(cases["belief"])[0]), 3),
        evidence=evidence_contributions(cases["prior"][0], cases["obs"][0], cases["rel"][0]),
        agents=agents_out, actions=actions, mode=mode, lambdas=lam,
        operating_agent=AGENTS[op]["name"],
        robust_set=[cfg.HYPOTHESES[k][0] for k in range(cfg.K) if robust_set[k]],
        optimum=dict(code=cfg.ACTIONS[a_star]["code"], name=cfg.ACTIONS[a_star]["name"],
                     level=cfg.LEVEL_NAMES[int(g_op["level"][0, a_star])],
                     binding=binding_names(g_op["binding"][0, a_star])),
        by_mode=dict(expected=cfg.ACTIONS[exp_star]["code"], cvar=cfg.ACTIONS[cvar_star]["code"],
                     robust=cfg.ACTIONS[rob_star]["code"]),
        calibration=calib, drift=dict(stable=drift["stable"], w1=drift["w1"], kl=drift["kl"],
                                      cusum_alarm=drift["cusum_alarm"]),
    )


def case_list():
    return [dict(id=c["id"], title=c["title"], cls=c["cls"]) for c in CASES]
