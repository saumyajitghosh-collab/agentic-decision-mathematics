"""Decision mathematics for candidate actions.

For each case with belief b and each action a:

  outcome      y ~ Bernoulli(p_it(x, a)),   p_it = p_res(x, a) Â· late(a)
  loss         L = c_a + wÂ·H_a + (1 - y) Â· m Â· (fail + irrev_a Â· (1 - detect_a) Â· remediation),  m ~ LogNormal, E[m] = 1
  expected     E[L] = c_a + wÂ·H_a + P(unresolved) Â· harm_a
  tail         CVaR_Î±(L), computed exactly on a discretised loss distribution
  risk         R_a = P_err(a) Â· Severity(a),  Severity = w Â· [exposure, irrev, 1-detect, propagation, control]
  objective    H(a) = Î»_CÂ·E[L]/C_ref + Î»_RÂ·R + Î»_TÂ·E[T]/24 + Î»_HÂ·H/60 + Î»_FÂ·P_fail + Î»_KÂ·CVaR/C_ref

Feasible set:
  A_safe = { a : g_i(x,a) <= 0, h_j(x,a) = 0, Ï†(x,a) = TRUE }
ESCALATE is always feasible, so A_safe is never empty.
"""
import numpy as np
from scipy.stats import norm
from . import config as cfg

REASONS = [
    (1, "SSI_SOURCE", "Ï†: SSI change requires an approved golden source"),
    (2, "PSET_REF", "Ï†: settlement instruction requires a valid place of settlement"),
    (4, "ORIGINAL_LINK", "Ï†: cancel/replace requires the original instruction to be linked"),
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
    """Exact CVaR_Î± (Rockafellarâ€“Uryasev) of a discrete distribution, vectorised on the last axis."""
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
    ET = cfg.ACT_TIME[None, :] + p_unres * cfg.FOLLOWUP_HOURTÊ‚ˆHHÙ™Ë‘VÔÕT‘WÑÔ’QˆÜÜÙ\ÈHœ˜ÛÛ˜Ø][˜]JØ˜\ÙVË‹‹‹›Û™WK˜\ÙVË‹‹‹›Û™WH
ÈWÑÔ’QÓ›Û™K›Û™K—H
ˆ\›VË‹‹‹›Û™WWKLJBˆ›ØœÈHœ˜ÛÛ˜Ø][˜]JÊKŒHÝ[œ™\ÊVË‹‹‹›Û™WKœœ™\X]

Ý[œ™\ÈÈJVË‹‹‹›Û™WKKLWKLJBˆÝ˜\ˆH\ØÜ™]WØÝ˜\ŠÜÜÙ\Ë›ØœËÙ™Ë•RSÐSJB‚ˆ^ÈHœ›Z[š[][JKŒØ\Ù\ÖÈ››Ý[Û˜[—HÈÙ™Ë‘VÔÕT‘WÔ‘QŠBˆ™X]ÈHœœÝXÚÊÂˆœ˜œ›ØYØ\ÝÝÊ^ÖÎ‹›Û™WK
‹Ù™ËJJKˆœ˜œ›ØYØ\ÝÝÊÙ™ËPÕÒT”‘U–Ó›Û™K—K
‹Ù™ËJJKˆœ˜œ›ØYØ\ÝÝÊKŒHÙ™ËPÕÑUPÕÓ›Û™K—K
‹Ù™ËJJKˆœ˜œ›ØYØ\ÝÝÊœ˜\Ø\œ˜^JØ\Ù\ÖÈœ›ÜYØ][Ûˆ—K›Ø]
VÎ‹›Û™WK
‹Ù™ËJJKˆœ˜œ›ØYØ\ÝÝÊÙ™ËPÕÐÕ“Ó›Û™K—K
‹Ù™ËJJKˆKLJBˆÙ]™\š]HH™X]ÈÙ™Ë”ÑU‘T’UWÕÂˆˆHÙ\œˆ
ˆÙ]™\š]B‚ˆÛÛ\ÈHXÝ
ÏQSÈÙ™Ë×Ô‘Q‹T‹QUÈŒRÈŒŒ\Ý[œ™\ËÍØäaÈ€¬™œ¹}I¤(€€€É…Ü€ô‘¥Ð¡Ñ…¥±}±¥µ¥Ðõ¹À¹‰É½…‘…ÍÑ}Ñ¼¡¹À¹µ…á¥µÕ´¡™œ¹Q%1}1==H°™œ¹Q%1}	AL€¨…Í•Íl‰¹½Ñ¥½¹…°‰t¥lè°9½¹•t°€¡8°™œ¹¤¤°(€€€€€€€€€€€€€€•áÁ•Ñ•‘}±½ÍÌõ0°Ù…ÈõÙ…È°É¥Í¬õH°Á}•ÉÈõÁ}•ÉÈ°Á}™…¥°õÁ}Õ¹É•Ì°(€€€€€€€€€€€€€€•áÁ•Ñ•‘}¡½ÕÉÌõP°¡Õµ…¹}µ¥¹ÕÑ•Ìõ °Í•Ù•É¥ÑäõÍ•Ù•É¥Ñä°Á}¥¹}Ñ¥µ”õÁ¥Ð¤((€€€µ…Í¬€ô¹À¹é•É½Ì ¡8°™œ¹¤°¥¹Ð¤(€€€µ…Í¬ðô¹À¹Ý¡•É”¡™œ¹Q}MM%m9½¹”°€ét€˜ù…Í•Íl‰ÍÍ¥}½¬‰ulè°9½¹•t°€Ä°€À¤(€€€µ…Í¬ðô¹À¹Ý¡•É”¡™œ¹Q}MQQ1}%9MQIm9½¹”°€ét€˜ù…Í•Íl‰ÁÍ•Ñ}½¬‰ulè°9½¹•t°€È°€À¤(€€€µ…Í¬ðô¹À¹Ý¡•É”¡™œ¹Q}91m9½¹”°€ét€˜ù…Í•Íl‰±¥¹­•‰ulè°9½¹•t°€Ð°€À¤(€€€µ…Í¬ðô¹À¹Ý¡•É”¡…Í•Íl‰¹½Ñ¥½¹…°‰ulè°9½¹•u > cfg.ACT_LIMIT[None, :], 8, 0)
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
