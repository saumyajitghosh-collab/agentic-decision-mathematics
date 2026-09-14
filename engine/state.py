"""State estimation.

The control layer, not the agent, owns the belief about operational state:

    b_t(x) = P(x_t = x | O_1:t)  ∝  P(x) · Π_e  P(o_e | x)^{r_e}

Evidence reliability r_e ∈ (0, 1] tempers each likelihood (a power posterior),
so a stale or partially authoritative message moves the belief less than a
golden-source observation.
"""
import hashlib
import numpy as np
from . import config as cfg

LOG_L1 = np.log(cfg.LIK)
LOG_L0 = np.log(1.0 - cfg.LIK)


def posterior(prior, obs, rel):
    """prior (N,K); obs (N,E) with 1 present, 0 absent, -1 unobserved; rel (N,E)."""
    o = obs[:, :, None]
    ll = np.where(o == 1, LOG_L1[None], np.where(o == 0, LOG_L0[None], 0.0))
    ll = ll * rel[:, :, None]
    logpost = np.log(prior) + ll.sum(1)
    logpost = logpost - logpost.max(1, keepdims=True)
    post = np.exp(logpost)
    return post / post.sum(1, keepdims=True)


def entropy_norm(b):
    """Normalised Shannon entropy in [0, 1]."""
    p = np.clip(b, 1e-12, 1.0)
    return -(p * np.log(p)).sum(-1) / np.log(cfg.K)


def evidence_contributions(prior, obs, rel):
    """Per-evidence log-likelihood vectors for a single case (for explanation)."""
    rows = []
    for e in range(cfg.E):
        if obs[e] == -1:
            continue
        ll = (LOG_L1[e] if obs[e] == 1 else LOG_L0[e]) * rel[e]
        rows.append(dict(code=cfg.EVIDENCE[e][0], label=cfg.EVIDENCE[e][1],
                         observed=bool(obs[e] == 1), reliability=round(float(rel[e]), 2),
                         loglik=[round(float(v), 3) for v in ll]))
    return rows


def seed_from(*parts):
    h = hashlib.sha256("|".join(str(p) for p in parts).encode()).hexdigest()
    return int(h[:12], 16)


def generate(n, seed, class_idx=None, drift_recent=False):
    """Synthetic cases drawn from the generative model in config.

    Evidence is generated from the true likelihoods, then corrupted with
    probability (1 - reliability): corrupted signals are coin flips. The engine's
    tempered posterior is therefore an approximation, as in real operations.
    """
    rng = np.random.default_rng(seed)
    if class_idx is None:
        w = cfg.CLASS_VOLUME / cfg.CLASS_VOLUME.sum()
        cls = rng.choice(cfg.C, size=n, p=w)
    else:
        cls = np.full(n, int(class_idx))
    priors = cfg.PRIORS[cls].copy()
    true_priors = priors.copy()
    if drift_recent:
        m = cls == cfg.DRIFT_CLASS
        true_priors[m] = cfg.DRIFT_PRIOR / cfg.DRIFT_PRIOR.sum()
    u = rng.random((n, 1))
    x_true = (u > np.cumsum(true_priors, 1)).sum(1)
    x_true = np.minimum(x_true, cfg.K - 1)

    lo, hi = cfg.REL_RANGE[:, 0], cfg.REL_RANGE[:, 1]
    rel = lo + (hi - lo) * rng.random((n, cfg.E))
    clean = (rng.random((n, cfg.E)) < cfg.LIK[:, x_true].T).astype(int)
    corrupt = rng.random((n, cfg.E)) > rel
    coin = (rng.random((n, cfg.E)) < 0.5).astype(int)
    val = np.where(corrupt, coin, clean)
    observed = rng.random((n, cfg.E)) < cfg.OBS_RATE
    obs = np.where(observed, val, -1)

    notional = cfg.CLASS_NOTIONAL[cls] * np.exp(cfg.NOTIONAL_SIGMA * rng.standard_normal(n))
    size = np.sqrt(notional / cfg.CLASS_NOTIONAL[cls])
    cases = dict(
        cls=cls, x_true=x_true, obs=obs, rel=rel, prior=priors,
        notional=notional,
        cutoff_h=1.5 + 10.5 * rng.random(n),
        ssi_ok=rng.random(n) < 0.90,
        pset_ok=rng.random(n) < 0.92,
        linked=rng.random(n) < 0.88,
        handling=cfg.CLASS_HANDLING[cls],
        fail_cost=np.clip(cfg.CLASS_FAIL[cls] * size, 20, 20000),
        remediation=np.clip(cfg.REMEDIATION_BASE * size, 50, 20000),
        propagation=cfg.CLASS_PROP[cls],
        noise=rng.standard_normal((n, 3, cfg.K)),
        drift=np.full(n, bool(drift_recent)),
    )
    cases["belief"] = posterior(priors, obs, rel)
    return cases


def subset(cases, idx):
    return {k: (v[idx] if isinstance(v, np.ndarray) else v) for k, v in cases.items()}
