"""Preregistered, blinded agent benchmark.

1. Freeze an evaluation manifest (population, evidence, metrics, loss function,
   invariants, calibration method, statistical tests) and hash it (SHA-256 of
   canonical JSON). Nothing in the manifest depends on which agent wins.
2. Score agents under blinded labels. The label permutation is derived from the
   manifest hash, so it is fixed before scoring and reproducible afterwards.
3. Unblind only by presenting the manifest hash.

Metrics
  valid           proposal ∈ A_safe
  control-safe    valid ∧ requested autonomy <= mathematically granted autonomy
  regret          J(a_exec) − J(a*)            (a_exec = ESCALATE when the gate denies)
  human minutes   handling · (1 − saving(level))
  resolution      p_in_time(x_true, a_exec)    (simulation truth, never shown to agents)
  tail loss       empirical CVaR_95 of realised loss outcomes (Bernoulli draws from simulation truth)
  autonomous      executed level = AUTO
Rates carry Wilson 95% intervals; regret carries a percentile bootstrap interval,
and the best two agents get a paired bootstrap test on the regret difference.
"""
import hashlib
import json
from datetime import datetime, timezone
import numpy as np
from . import config as cfg
from .agents import AGENTS, propose
from .autonomy import grant
from .core import evaluate, objective
from .invariants import INVARIANTS
from .state import generate, seed_from
from .uncertainty import wilson_lower

METRICS = ["valid", "control_safe", "agreement", "mean_regret", "human_minutes", "resolution",
           "tail_loss_cvar95", "autonomous"]
BOOT = 2000

# Enough labels for any number of participants; we keep the last |AGENTS| so
# the historical 3-agent benchmark still produces "Agent X, Y, Z".
_BLIND_LABELS = ["Agent V", "Agent W", "Agent X", "Agent Y", "Agent Z"]


def manifest(n, seed, lam):
    lam = cfg.normalise_lambdas(lam)
    body = dict(
        version="1.0",
        population=dict(cases=int(n), seed=int(seed), class_mix="volume-weighted", generator="engine.state.generate"),
        exception_classes=[c["code"] for c in cfg.CLASSES],
        permitted_evidence=[e[0] for e in cfg.EVIDENCE],
        metrics=METRICS,
        loss_function=dict(form="J = Σ λ_k · component_k", lambdas=lam, tail_alpha=cfg.TAIL_ALPHA),
        control_invariants=[dict(code=c, tex=t) for c, t, _, _ in INVARIANTS],
        calibration=dict(method="split conformal", alpha_base=cfg.ALPHA_BASE, irreversibility_slope=cfg.ALPHA_IRREV_SLOPE,
                         coverage_tolerance=cfg.COVERAGE_TOL, set_size_max=cfg.SET_SIZE_MAX),
        statistical_tests=dict(rates="Wilson 95%", regret=f"percentile bootstrap, {BOOT} resamples",
                               comparison=f"paired bootstrap on regret difference, {BOOT} resamples"),
        agents=dict(count=len(AGENTS), identities="blinded until manifest hash is presented",
                    design="one participant is deliberately misspecified (reads a partial evidence model; "
                         "the benchmark therefore measures diagnostic discrimination as well as calibration noise"),
    )
    canon = json.dumps(body, sort_keys=True, separators=(", ": "))
    digest = hashlib.sha256(canon.encode()).hexdigest()
    return body, digest


def blind_map(digest):
    rng = np.random.default_rng(int(digest[:12], 16))
    perm = rng.permutation(len(AGENTS))
    labels = _BLIND_LABELS[-len(AGENTS):]
    return {labels[j]: AGENTS[int(perm[j])]["name"] for j in range(len(AGENTS))}, perm


def _wilson(k, n):
    lo = wilson_lower(k, n