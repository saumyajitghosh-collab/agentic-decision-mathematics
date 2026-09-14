"""Properties the control plane must satisfy. Run: pytest -q"""
import numpy as np
import pytest

from engine import config as cfg
from engine.autonomy import grant
from engine.benchmark import manifest, run as run_benchmark, unblind
from engine.core import discrete_cvar, evaluate, optimum
from engine.gate import simulate
from engine.invariants import Atom, Once, Implies, G_violations, hash_chain, verify_chain
from engine.savings import allocate, class_tables, lab, workforce
from engine.sensitivity import lower_envelope
from engine.state import generate
from engine.uncertainty import calibration_status, q_hat, calibrated_table, stable_vector
from app import app


@pytest.fixture(scope="module")
def population():
    cases = generate(1500, 99)
    return cases, evaluate(cases)


def test_belief_is_a_distribution(population):
    cases, _ = population
    assert np.allclose(cases["belief"].sum(1), 1.0)
    assert (cases["belief"] >= 0).all()


def test_cvar_matches_brute_force():
    rng = np.random.default_rng(0)
    for _ in range(50):
        losses = rng.integers(0, 1000, 12).astype(float)
        counts = rng.integers(1, 20, 12)
        probs = counts / counts.sum()
        alpha = 0.9
        exact = discrete_cvar(losses[None], probs[None], alpha)[0]
        scale = 1000
        atoms = np.sort(np.repeat(losses, counts * scale))[::-1]
        k = (1 - alpha) * len(atoms)
        full = int(np.floor(k))
        tail = atoms[:full].sum() + (k - full) * atoms[full]
        assert exact == pytest.approx(tail / k, rel=1e-9)


def test_cvar_dominates_expected_loss(population):
    _, ev = population
    assert (ev["raw"]["cvar"] >= ev["raw"]["expected_loss"] - 1e-9).all()


def test_escalate_is_always_feasible(population):
    _, ev = population
    assert ev["feasible"][:, cfg.ESC].all()


def test_optimum_is_feasible_and_minimal(population):
    _, ev = population
    a_star, J = optimum(ev, cfg.DEFAULT_LAMBDAS)
    idx = np.arange(len(a_star))
    assert ev["feasible"][idx, a_star].all()
    Jm = np.where(ev["feasible"], J, np.inf)
    assert np.allclose(J[idx, a_star], Jm.min(1))


def test_conformal_needs_enough_data():
    assert q_hat(np.linspace(0, 1, 18), 0.05) == np.inf   # need n >= 19
    assert np.isfinite(q_hat(np.linspace(0, 1, 19), 0.05))


def test_conformal_coverage_meets_target():
    for c in [0, 1, 3]:
        st = calibration_status(1, c, 0.05)
        assert st["coverage"] >= 0.95 - cfg.COVERAGE_TOL


def test_rare_class_is_not_calibrated():
    rare = [i for i, c in enumerate(cfg.CLASSES) if c["code"] == "CORP_ACTION"][0]
    assert not calibrated_table(1)[rare].any()


def test_drift_is_detected_only_where_injected():
    stable = stable_vector(1)
    assert not stable[cfg.DRIFT_CLASS]
    assert stable[[c for c in range(cfg.C) if c != cfg.DRIFT_CLASS]].all()


def test_autonomy_is_the_meet_of_caps(population):
    cases, ev = population
    g = grant(cases, ev, 1)
    lvl, caps = g["level"], g["caps"]
    agent_actions = np.ones(cfg.A, bool)
    agent_actions[cfg.ESC] = False
    feas = ev["feasible"] & agent_actions[None, :]
    assert (lvl[feas] == caps[feas].min(-1)).all()
    auto = lvl == cfg.AUTO
    assert g["calibrated"][auto].all() and g["stable"][auto].all()
    assert (ev["raw"]["risk"][auto] < cfg.R1).all()
    assert (lvl[~ev["feasible"]] == cfg.DENY).all()


def test_enforcing_mode_has_zero_invariant_violations():
    for seed in range(1, 4):
        r = simulate(250, seed)
        assert r["totals"]["enforcing"] == 0
        assert r["totals"]["shadow"] > 0
        assert r["chain"]["verified"] and not r["chain"]["tamper_test"]["verified"]


def test_ltl_once_operator():
    trace = [dict(type="PROPOSE"), dict(type="APPROVE"), dict(type="EXECUTE")]
    execute = Atom("x", lambda t, i: t[i]["type"] == "EXECUTE")
    approve = Atom("a", lambda t, i: t[i]["type"] == "APPROVE")
    assert G_violations(Implies(execute, Once(approve)), trace) == []
    assert G_violations(Implies(execute, Once(approve)), [trace[0], trace[2]]) == [1]


def test_hash_chain_detects_tampering():
    events = [dict(seq=i, v=i) for i in range(1, 20)]
    chained, _ = hash_chain(events)
    assert verify_chain(events, chained)[0]
    events[7] = dict(events[7], v=999)
    ok, seq = verify_chain(events, chained)
    assert not ok and seq == 8


def test_breakpoints_match_brute_force(population):
    _, ev = population
    rng = np.random.default_rng(3)
    for i in rng.integers(0, 1500, 25):
        comps = {k: v[i] for k, v in ev["comps"].items()}
        feas = ev["feasible"][i]
        for k in cfg.LAMBDA_KEYS:
            beta = sum(cfg.DEFAULT_LAMBDAS[j] * comps[j] for j in cfg.LAMBDA_KEYS if j != k)
            for s in lower_envelope(beta, comps[k], feas, (0.0, 5.0)):
                if s["end"] - s["start"] < 1e-3:
                    continue
                mid = (s["start"] + s["end"]) / 2
                J = np.where(feas, beta + mid * comps[k], np.inf)
                assert cfg.ACTIONS[int(J.argmin())]["code"] == s["action"]


def test_allocation_respects_risk_budget():
    lam_key = tuple(sorted(cfg.DEFAULT_LAMBDAS.items()))
    _, KC, EL, TL, _ = class_tables(1, lam_key)
    r_max = EL[:, 0].sum() * 1.1
    z = allocate(KC, EL, TL, r_max, TL.max(1).sum())
    assert EL[np.arange(cfg.C), z].sum() <= r_max + 1e-6


def test_workforce_respects_floors():
    residual = cfg.CLASS_VOLUME * cfg.CLASS_HANDLING * 0.5
    wf = workforce(residual)
    for j, sk in enumerate(cfg.SKILLS):
        assert (wf["HC"][j] >= cfg.SKILL_FLOOR[sk]).all()


def test_minutes_removed_exceed_headcount_released():
    s = lab(1, risk_budget=0.1)["solution"]
    assert s["minutes_removed_pct"] >= s["fte_reduction_pct"]


def test_manifest_hash_is_deterministic_and_blinding_reproducible():
    assert manifest(1000, 7, None)[1] == manifest(1000, 7, None)[1]
    r = run_benchmark(400, 7)
    assert r["manifest_hash"] == manifest(400, 7, None)[1]
    assert sorted(unblind(r["manifest_hash"]).values()) == ["Agent A", "Agent B", "Rules baseline"]


def test_api_endpoints():
    c = app.test_client()
    assert c.get("/healthz").status_code == 200
    assert c.get("/api/catalogue").status_code == 200
    for url, body in [("/api/arena", {"case_id": "EXC-51566", "mode": "robust"}), ("/api/frontier", {}),
                      ("/api/sensitivity", {"case_id": "EXC-49872"}), ("/api/savings", {}), ("/api/proof", {"n": 100})]:
        assert c.post(url, json=body).status_code == 200
    ex = c.get("/api/evaluate").get_json()["example"]
    r = c.post("/api/evaluate", json=ex).get_json()
    assert r["decision"] in ("ALLOW", "DENY") and len(r["evidence_hash"]) == 64
    assert c.post("/api/evaluate", json={"case_id": "nope"}).status_code == 400
    bad = dict(ex, proposal=dict(ex["proposal"], action="WIRE_MONEY"))
    assert c.post("/api/evaluate", json=bad).status_code == 400


def test_external_tampering_is_denied():
    c = app.test_client()
    ex = c.get("/api/evaluate").get_json()["example"]
    tampered = dict(ex, proposal=dict(ex["proposal"], changes=["ssi", "settlement_instruction", "economics"]))
    r = c.post("/api/evaluate", json=tampered).get_json()
    assert r["decision"] == "DENY"
    assert any(x["code"] == "FIELD_INVARIANCE" for x in r["reasons"])
