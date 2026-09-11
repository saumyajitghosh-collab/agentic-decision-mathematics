"""Evaluate a proposal from any external agent.

The engine never needs to know what produced the proposal. It needs the
operational observations, the proposed action, the requested autonomy, the
declared field changes and (optionally) the agent's probability vector over
root causes plus the name of the calibration profile registered for that agent.

    execution-control architecture: model-independent
    statistical calibration:        model-specific (one profile per agent)
"""
import numpy as np
from . import config as cfg
from .agents import AGENT_INDEX
from .arena import build_case, load_case, CASE_INDEX
from .autonomy import grant, binding_names
from .core import evaluate, objective, decode_reasons
from .gate import decide, evidence_hash
from .uncertainty import conformal_set_for

LEVEL_BY_NAME = {v: k for k, v in cfg.LEVEL_NAMES.items()}

EXAMPLE = {
    "case": {
        "class": "SSI_BREAK",
        "evidence": {"GOLDEN_SSI_DIFF": [1, 0.97], "CPTY_NMAT": [1, 0.85], "ECON_TOLERANCE": [0, 0.95]},
        "notional": 3200000, "cutoff_h": 6, "ssi_source_approved": True, "pset_valid": True, "original_linked": True,
    },
    "proposal": {
        "agent_id": "my-agent", "calibration_profile": "B", "authenticated": True,
        "action": "REPAIR_SSI", "requested_level": "AUTO", "changes": ["ssi", "settlement_instruction"],
        "p_hat": [0.86, 0.08, 0.03, 0.0, 0.0, 0.01, 0.02],
    },
    "mode": "cvar",
}


class InputError(ValueError):
    pass


def _case_from(payload):
    if "case_id" in payload:
        if payload["case_id"] not in CASE_INDEX and not str(payload["case_id"]).startswith("RND-"):
            raise InputError(f"Unknown case_id {payload['case_id']}")
        return load_case(payload["case_id"])[0]
    c = payload.get("case")
    if not isinstance(c, dict):
        raise InputError("Provide either case_id or a case object")
    codes = [x["code"] for x in cfg.CLASSES]
    if c.get("class") not in codes:
        raise InputError(f"case.class must be one of {codes}")
    ev_codes = [e[0] for e in cfg.EVIDENCE]
    obs = {}
    for k, v in (c.get("evidence") or {}).items():
        if k not in ev_codes:
            raise InputError(f"Unknown evidence code {k}; expected one of {ev_codes}")
        if not (isinstance(v, (list, tuple)) and len(v) == 2 and v[0] in (0, 1) and 0 < float(v[1]) <= 1):
            raise InputError(f"evidence.{k} must be [0 or 1, reliability in (0, 1]]")
        obs[k] = (int(v[0]), float(v[1]))
    spec = dict(id="EXTERNAL", title="External case", cls=c["class"], obs=obs,
                notional=float(c.get("notional", cfg.CLASS_NOTIONAL[codes.index(c["class"])])),
                cutoff_h=float(c.get("cutoff_h", 6.0)), ssi_ok=bool(c.get("ssi_source_approved", True)),
                pset_ok=bool(c.get("pset_valid", True)), linked=bool(c.get("original_linked", True)))
    return build_case(spec)


def evaluate_proposal(payload):
    cases = _case_from(payload)
    p = payload.get("proposal") or {}
    if p.get("action") not in cfg.ACTION_INDEX:
        raise InputError(f"proposal.action must be one of {list(cfg.ACTION_INDEX)}")
    req_name = p.get("requested_level", "APPROVE")
    if req_name not in ("HUMAN", "PROPOSE", "APPROVE", "AUTO"):
        raise InputError("proposal.requested_level must be HUMAN, PROPOSE, APPROVE or AUTO")
    profile = p.get("calibration_profile", "B")
    if profile not in AGENT_INDEX:
        raise InputError(f"proposal.calibration_profile must be one of {list(AGENT_INDEX)}")
    ag = AGENT_INDEX[profile]
    a = cfg.ACTION_INDEX[p["action"]]
    req = LEVEL_BY_NAME[req_name]
    changes = set(p.get("changes") or [])
    lam = cfg.normalise_lambdas(payload.get("lambdas"))
    if payload.get("mode") == "expected":
        lam["K"] = 0.0

    ev = evaluate(cases)
    g = grant(cases, ev, ag)
    J = objective(ev["comps"], lam)[0]
    feasible = ev["feasible"][0]
    a_star = int(np.where(feasible, J, np.inf).argmin())
    d = decide(0, a, req, bool(p.get("authenticated", False)), changes, ev, g)
    executed = a if d["decision"] == "ALLOW" else cfg.ESC

    conformal = None
    if p.get("p_hat") is not None:
        ph = np.asarray(p["p_hat"], float)
        if ph.shape != (cfg.K,) or (ph < 0).any() or ph.sum() <= 0:
            raise InputError(f"proposal.p_hat must be {cfg.K} non-negative numbers")
        ph = ph / ph.sum()
        s, q = conformal_set_for(ag, int(cases["cls"][0]), ph, cfg.alpha_for_action(a))
        conformal = dict(alpha=round(cfg.alpha_for_action(a), 4), q_hat=q,
                         set=[cfg.HYPOTHESES[k][0] for k in range(cfg.K) if s[k]])

    result = dict(
        decision=d["decision"], granted_level=cfg.LEVEL_NAMES[d["level"]],
        mathematical_ceiling=cfg.LEVEL_NAMES[int(g["level"][0, a])],
        reasons=d["reasons"], binding_constraints=d["binding"],
        executed_action=cfg.ACTIONS[executed]["code"],
        optimal_action=cfg.ACTIONS[a_star]["code"],
        optimal_level=cfg.LEVEL_NAMES[int(g["level"][0, a_star])],
        optimal_binding=binding_names(g["binding"][0, a_star]),
        regret=round(float(J[executed] - J[a_star]), 4),
        belief={cfg.HYPOTHESES[k][0]: round(float(cases["belief"][0, k]), 4) for k in range(cfg.K)},
        feasible_actions=[cfg.ACTIONS[i]["code"] for i in range(cfg.A) if feasible[i]],
        infeasible=[dict(action=cfg.ACTIONS[i]["code"], reasons=decode_reasons(ev["reason_mask"][0, i]))
                    for i in range(cfg.A) if not feasible[i]],
        objective={cfg.ACTIONS[i]["code"]: round(float(J[i]), 4) for i in range(cfg.A)},
        conformal=conformal, lambdas=lam,
    )
    result["evidence_hash"] = evidence_hash(result)
    return result
