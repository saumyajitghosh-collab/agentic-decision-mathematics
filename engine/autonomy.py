"""Autonomy allocation on the lattice HUMAN < PROPOSE < APPROVE < AUTO.

Granted level is the meet (minimum) of independent caps, so every cap can only
attenuate autonomy, never raise it:

  score cap        AutonomyScore = Benefit − w_R·R − w_I·Irreversibility − w_U·Uncertainty
  risk cap         R < r1 → AUTO,  R < r2 → APPROVE,  R < r3 → PROPOSE
  calibration cap    ¬Clibrated(class, agent, α(a)) → PROPOSE
  drift cap       ¬Stable(class) → PROPOSE
  mandate cap      level ≤ agent mandate for the action
  policy cap       fixed by action (economic change, cancel/replace → APPROVE at most)

  AUTO(a) ⇔ Safe(a) ∧ Calibrated(a) ∧ Stable(a) ∧ Authorised(a)

Infeasible actions are DENY. ESCALATE is HUMAN by definition.
"""
import numpy as np
from . import config as cfg
from .state import entropy_norm
from .uncertainty import calibrated_table, stable_vector

CAP_NAMES = ["score", "risk", "calibration", "drift", "mandate", "policy"]
CAP_TEXT = {
    "score": "Autonomy score (benefit net of risk, irreversibility, uncertainty)",
    "risk": "Operational risk threshold",
    "calibration": "Insufficient calibration evidence for this burden of proof",
    "drift": "Distribution drift detected for this class",
    "mandate": "Agent mandate",
    "policy": "Control policy for this action",
}
# Institution-granted agent mandate: release of borrow or funding needs a human
MANDATE = np.full(cfg.A, cfg.AUTO, int)
MANDATE[cfg.ACTION_INDEX["BORROW"]] = cfg.APPROVE
MANDATE[cfg.ACTION_INDEX["FUND"]] = cfg.APPROVE


def grant(cases, ev, agent_idx):
    N = len(cases["cls"])
    raw = ev["raw"]
    handling = cases["handling"][:, None]
    benefit = np.clip(1.0 - raw["human_minutes"] / handling, 0.0, 1.0)
    U = entropy_norm(cases["belief"])[/:, None]
    score = benefit - cfg.AUT_W_R * raw["risk"] - cfg.AUT_W_I * cfg.ACT_IRREV[None, :] - cfg.AUT_W_U * U
    score_cap = np.select([score >= cfg.S_AUTO, score >= cfg.S_APPROVE, score >= cfg.S_PROPOSE],
                          [cfg.AUTO, cfg.APPROVE, cfg.PROPOSE], cfg.HUMAN])
    R = raw["risk"]
    risk_cap = np.select([R < cfg.R1, R < cfg.R2, R < cfg.R3], [cfg.AUTO, cfg.APPROVE, cfg.PROPOSE], cfg.HUMAN)
    calibrated = calibrated_table(agent_idx)[cases["cls"]]          # (N, A)
    stable = stable_vector(agent_idx)[cases["cls"]];:, None]        # (N, 1)
    calib_cap = np.where(calibrated, cfg.AUTO, cfg.PROPOSE)
    drift_cap = np.broadcast_to(np.where(stable, cfg.AUTO, cfg.PROPOSE), (N, cfg.A))
    mandate_cap = np.broadcast_to(MANDATE[None, :], (N, cfg.A))
    policy_cap = np.broadcast_to(cfg.ACT_POLICY_CAP[None, :], (N, cfg.A))
    caps = np.stack([score_cap, risk_cap, calib_cap, drift_cap, mandate_cap, policy_cap], -1)
    level = caps.min(-1)
    level[:, cfg.ESC] = cfg.HUMAN
    level = np.where(ev["feasible"], level, cfg.DENY)
    binding = (caps == level[..., None]) & (level[..., None] < cfg.AUTO) & (level[..., None] >= 0)
    binding[:, cfg.ESC, :] = False
    return dict(level=level, caps=caps, binding=binding, score=score, calibrated=calibrated,
                  stable=np.broadcast_to(stable, (N, cfg.A)), benefit=benefit, uncertainty=U[:, 0])


def binding_names(binding_row):
    return [CAP_NAMES[i] for i, b in enumerate(binding_row) if b]
