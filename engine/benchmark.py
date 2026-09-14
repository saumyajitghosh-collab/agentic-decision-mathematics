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
  tail loss       empirical CVaR_95 of realised expected loss across cases
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
        agents=dict(count=len(AGENTS), identities="blinded until manifest hash is presented"),
    )
    canon = json.dumps(body, sort_keys=True, separators=(",", ":"))
    digest = hashlib.sha256(canon.encode()).hexdigest()
    return body, digest


def blind_map(digest):
    rng = np.random.default_rng(int(digest[:12], 16))
    perm = rng.permutation(len(AGENTS))
    labels = ["Agent X", "Agent Y", "Agent Z"]
    return {labels[j]: AGENTS[int(perm[j])]["name"] for j in range(len(AGENTS))}, perm


def _wilson(k, n):
    lo = wilson_lower(k, n)
    hi = 1 - wilson_lower(n - k, n)
    return [round(lo, 4), round(hi, 4)]


def run(n=2000, seed=2026, lam=None):
    body, digest = manifest(n, seed, lam)
    lam = body["loss_function"]["lambdas"]
    cases = generate(n, seed_from("benchmark", seed))
    ev = evaluate(cases)
    J = objective(ev["comps"], lam)
    a_star = np.where(ev["feasible"], J, np.inf).argmin(1)
    idx = np.arange(n)
    pit = ev["raw"]["p_in_time"]
    base_loss = cfg.ACT_COST[None, :] + cfg.HUMAN_COST_PER_MIN * ev["raw"]["human_minutes"]
    harm = cases["fail_cost"][:, None] + (cfg.ACT_IRREV * (1 - cfg.ACT_DETECT))[None, :] * cases["remediation"][:, None]

    def realised(a_exec):
        p = pit[idx, a_exec, cases["x_true"]]
        loss = base_loss[idx, a_exec] + (1 - p) * harm[idx, a_exec]
        return p, loss

    def tail(loss):
        q = np.quantile(loss, cfg.TAIL_ALPHA)
        return float(loss[loss >= q].mean())

    rng = np.random.default_rng(seed)
    boot_idx = rng.integers(0, n, (BOOT, n))
    _, perm = blind_map(digest)
    rows, regrets = [], {}
    for j, label in enumerate(["Agent X", "Agent Y", "Agent Z"]):
        ag = int(perm[j])
        a_prop, req, _ = propose(ag, cases)
        g = grant(cases, ev, ag)
        valid = ev["feasible"][idx, a_prop]
        granted = g["level"][idx, a_prop]
        safe = valid & (req <= granted)
        a_exec = np.where(valid, a_prop, cfg.ESC)
        lvl = np.where(valid, np.minimum(req, granted), cfg.HUMAN)
        lvl = np.where(a_exec == cfg.ESC, cfg.HUMAN, lvl)
        regret = J[idx, a_exec] - J[idx, a_star]
        minutes = cases["handling"] * (1 - cfg.LEVEL_SAVING[lvl])
        p_res, loss = realised(a_exec)
        boot = regret[boot_idx].mean(1)
        regrets[label] = regret
        rows.append(dict(
            label=label,
            valid=round(float(valid.mean()), 4), valid_ci=_wilson(int(valid.sum()), n),
            control_safe=round(float(safe.mean()), 4), control_safe_ci=_wilson(int(safe.sum()), n),
            agreement=round(float((a_exec == a_star).mean()), 4),
            mean_regret=round(float(regret.mean()), 4),
            regret_ci=[round(float(np.quantile(boot, 0.025)), 4), round(float(np.quantile(boot, 0.975)), 4)],
            human_minutes=round(float(minutes.mean()), 2),
            resolution=round(float(p_res.mean()), 4),
            tail_loss_cvar95=round(tail(loss), 1),
            autonomous=round(float((lvl == cfg.AUTO).mean()), 4),
        ))
    p_opt, loss_opt = realised(a_star)
    reference = dict(label="Mathematical optimum", valid=1.0, control_safe=None, agreement=1.0, mean_regret=0.0,
                     human_minutes=None, resolution=round(float(p_opt.mean()), 4),
                     tail_loss_cvar95=round(tail(loss_opt), 1), autonomous=None)

    ranked = sorted(rows, key=lambda r: r["mean_regret"])
    a_lab, b_lab = ranked[0]["label"], ranked[1]["label"]
    diff = regrets[a_lab] - regrets[b_lab]
    boot_diff = diff[boot_idx].mean(1)
    p_two = float(min(1.0, 2 * min((boot_diff >= 0).mean(), (boot_diff <= 0).mean())))
    comparison = dict(better=a_lab, other=b_lab, mean_difference=round(float(diff.mean()), 4),
                      ci=[round(float(np.quantile(boot_diff, 0.025)), 4), round(float(np.quantile(boot_diff, 0.975)), 4)],
                      p_value=round(p_two, 4))
    return dict(manifest=body, manifest_hash=digest, frozen_at=datetime.now(timezone.utc).isoformat(timespec="seconds"),
                rows=rows, reference=reference, comparison=comparison)


def unblind(digest):
    mapping, _ = blind_map(digest)
    return mapping
