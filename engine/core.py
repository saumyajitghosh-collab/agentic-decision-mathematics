"""Decision mathematics for candidate actions.

For each case with belief b and each action a:

  outcome      y ~ Bernoulli(p_it(x, a)),   p_it = p_res(x, a) · late(a)
  loss         L = c_a + w·H_a + (1 - y) · m · (fail + irrev_a · (1 - detect_a) · remediation),  m ~ LogNormal, E[m] = 1
  expected     E[L] = c_a + w·H_a + P(unresolved) · harm_a
  tail         CVaR_α(L), computed exactly on a discretised loss distribution
  risk         R_a = P_err(a) · Severity(a),  Severity = w · [exposure, irrev, 1-detect, propagation, control]
  objective    J(a) = λ_C·E[L]/C_ref + λ_R·R + λ_T·E[T]/24 + λ_H·H/60 + λ_F·P_fail + λ_K·CVaR/C_ref

Feasible set:
  A_safe = { a : g_i(x,a) <= 0, h_j(x,a) = 0, φ(x,a) = TRUE }
ESCALATE is always feasible, so A_safe is never empty.
"""
import numpy as np
from scipy.stats import norm
from . import config as cfg

REASONS = [
    (1, "SSI_SOURCE", "φ: SSI change requires an approved golden source"),
    (2, "PSET_REF", "φ: settlement instruction requires a valid place of settlement"),
    (4, "ORIGINAL_LINK", "φ: cancel/replace requires the original instruction to be linked"),
    (8, "NOTIONAL_LIMIT", "g: notional exceeds the action's authorised limit"),
    (16, "TAIL_LIMIT", "g: CVaR tail loss exceeds the authorised limit"),
    (32, "RISK_CEILING", "g: operational risk at or above the denial threshold"),
    (64, "FIELD_INVARIANCE", "h: proposal modifies fields the action is not authorised to change"),
]


def decode_reasons(mask):
    return [dict(code=c, text=t) for bit, c, t in REASONS if int(mask) & bit]


def _grid():
    u = (np.arange(cfg.EXPOSURE_GRID) + 0.5) / cfg.EXPOSURE_GRID
    m = np.exp(cfg.EXPOSURE_SIGMA * norm.ppf(u))
    return m / m.mean()


M_GRID = _grid()


def discrete_cvar(losses, probs, alpha):
    """Exact CVaR_α (Rockafellar–Uryasev) of a discrete distribution, vectorised on the last axis."""
    order = np.argsort(-losses, axis=-1)
    L = np.take_along_axis(losses, order, -1)
    p = np.take_along_axis(probs, order, -1)
    beta = 1.0 - alpha
    prev = np.cumsum(p, -1) - p
    w = np.clip(beta - prev, 0.0, p)
    return (w * L).sum(-1) / beta


def evaluate(cases, belief=None):
    """Evaluate every action for every case. Returns dict of (N, A) arrays."""
    B = cases["belief"] if belief is None else belief
    N = B.shape[0]
    late = np.where(cfg.ACT_TIME[None, :] <= cases["cutoff_h"][:, None], 1.0, cfg.LATE_FACTOR)
    pit = late[:, :, None] * cfg.P_RES[None, :, :]
    b = B[:, None, :]

    H = np.broadcast_to(cfg.ACT_MIN[None, :], (N, cfg.A)).copy()
    H[:, cfg.ESC] = cases["handling"]
    base = cfg.ACT_COST[None, :] + cfg.HUMAN_COST_PER_MIN * H
    harm = cases["fail_cost"][:, None] + (cfg.ACT_IRREV * (1.0 - cfg.ACT_DETECT))[None, :] * cases["remediation"][:, None]

    p_unres = (b * (1.0 - pit)).sum(-1)
    p_err = (b * (1.0 - cfg.P_RES[None])).sum(-1)
    EL = base + p_unres * harm
    ET = cfg.ACT_TIME[None, :] + p_unres * cfg.FOLLOWUP_HOURS

    Q = cfg.EXPOSURE_GRID
    losses = np.concatenate([base[..., None], base[..., None] + M_GRID[None, None, :] * harm[..., None]], -1)
    probs = np.concatenate([(1.0 - p_unres)[..., None], np.repeat((p_unres / Q)[..., None], Q, -1)], -1)
    cvar = discrete_cvar(losses, probs, cfg.TAIL_ALPHA)

    expo = np.minimum(1.0, cases["notional"] / cfg.EXPOSURE_REF)
    feats = np.stack([
        np.broadcast_to(expo[:, None], (N, cfg.A)),
        np.broadcast_to(cfg.ACT_IRREV[None, :], (N, cfg.A)),
        np.broadcast_to(1.0 - cfg.ACT_DETECT[None, :], (N, cfg.A)),
        np.broadcast_to(np.asarray(cases["propagation"], float)[:, None], (N, cfg.A)),
        np.broadcast_to(cfg.ACT_CTRL[None, :], (N, cfg.A)),
    ], -1)
    severity = feats @ cfg.SEVERITY_W
    R = p_err * severity

    comps = dict(C=EL / cfg.C_REF, R=R, T=ET / 24.0, H=H / 60.0, F=p_unres, K=cvar / cfg.C_REF)
    raw = dict(tail_limit=np.broadcast_to(np.maximum(cfg.TAIL_FLOOR, cfg.TAIL_BPS * cases["notional"])[:, None], (N, cfg.A)),
               expected_loss=EL, cvar=cvar, risk=R, p_err=p_err, p_fail=p_unres,
               expected_hours=ET, human_minutes=H, severity=severity, p_in_time=pit)

    mask = np.zeros((N, cfg.A), int)
    mask |= np.where(cfg.ACT_SSI[None, :] & ~cases["ssi_ok"][:, None], 1, 0)
    mask |= np.where(cfg.ACT_SETTLE_INSTR[None, :] & ~cases["pset_ok"][:, None], 2, 0)
    mask |= np.where(cfg.ACT_CANCEL[None, :] & ~cases["linked"][:, None], 4, 0)
    mask |= np.where(cases["notional"][:, None] > cfg.ACT_LIMIT[None, :], 8, 0)
    tail_limit = np.maximum(cfg.TAIL_FLOOR, cfg.TAIL_BPS * cases["notional"])
    mask |= np.where(cvar > tail_limit[:, None], 16, 0)
    mask |= np.where(R >= cfg.R3, 32, 0)
    mask[:, cfg.ESC] = 0
    return dict(comps=comps, raw=raw, reason_mask=mask, feasible=mask == 0)


def objective(comps, lam):
    lam = cfg.normalise_lambdas(lam)
    return sum(lam[k] * comps[k] for k in cfg.LAMBDA_KEYS)


def optimum(ev, lam):
    J = objective(ev["comps"], lam)
    Jm = np.where(ev["feasible"], J, np.inf)
    return Jm.argmin(1), J
