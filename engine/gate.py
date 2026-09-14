"""Execution gate and control proof.

The gate is the only path to execution. It admits a proposal when
  identity is authenticated,
  the action is in A_safe (g, h, φ constraints),
  declared field changes are a subset of the action's authorised changes (h = 0),
and it grants  min(requested level, mathematically granted level).

The proof simulation runs the same proposals twice:
  shadow mode     the gate only logs; agents execute what they requested
  enforcing mode  the gate decides; humans approve whene the level requires it
and hands both traces to the independent temporal-logic monitor.
"""
import hashlib
import json
import numpy as np
from . import config as cfg
from .agents import AGENTS, propose
from .autonomy import grant, MANDATE, binding_names
from .core import evaluate, decode_reasons
from .invariants import INVARIANTS, check_trace, hash_chain, verify_chain
from .state import generate, seed_from
from .uncertainty import calibrated_table, stable_vector

APPROVERS = ["ops-lead-1", "ops-lead-2", "control-officer"]


def authorised_changes(a_idx):
    return {k for k, v in cfg.ACTIONS[a_idx]["changes"].items() if v}


def evidence_hash(payload):
    return hashlib.sha256(json.dumps(payload, sort_keys=True, default=str).encode()).hexdigest()


def decide(i, a_idx, requested, authenticated, declared_changes, ev, g):
    reasons = []
    mask = int(ev["reason_mask"][i, a_idx])
    extra = set(declared_changes) - authorised_changes(a_idx)
    if extra:
        mask |= 64
    if not authenticated:
        reasons.append(dict(code="IDENTITY", text="Proposal has no authenticated agent identity"))
    reasons += decode_reasons(mask)
    granted = int(g["level"][i, a_idx])
    if reasons or granted == cfg.DENY:
        return dict(decision="DENY", level=cfg.DENY, granted=granted, reasons=reasons, binding=[])
    level = int(min(requested, granted))
    binding = binding_names(g["binding"][i, a_idx]) if granted <= requested else []
    if requested < granted:
        binding = ["requested"]
    return dict(decision="ALLOW", level=level, granted=granted, reasons=[], binding=binding)


def simulate(n=300, seed=11):
    rng = np.random.default_rng(seed)
    cases = generate(n, seed_from("proof", seed))
    ev = evaluate(cases)
    agent_of = rng.integers(0, len(AGENTS), n)
    grants = {ag: grant(cases, ev, ag) for ag in range(len(AGENTS))}
    props = {ag: propose(ag, cases) for ag in range(len(AGENTS))}

    unauth = rng.random(n) < 0.03
    no_evidence = rng.random(n) < 0.06
    tamper = rng.random(n) < 0.05

    shadow, enforce = [], []
    seq_s, seq_e = [0], [0]
    gate_summary = {"ALLOW": {v: 0 for v in ["AUTO", "APPROVE", "PROPOSE", "HUMAN"]}, "DENY": {}}

    def add(trace, counter, **e):
        counter[0] += 1
        e["seq"] = counter[0]
        trace.append(e)

    for i in range(n):
        ag = int(agent_of[i])
        g = grants[ag]
        a = int(props[ag][0][i])
        req = int(props[ag][1][i])
        cls = int(cases["cls"][i])
        declared = set(authorised_changes(a))
        if tamper[i] and not cfg.ACTIONS[a]["changes"].get("economics"):
            declared |= {"economics", "protected"}
        changes = {k: True for k in declared}
        authenticated = not unauth[i]
        common = dict(action=cfg.ACTIONS[a]["code"], cls=cfg.CLASSES[cls]["code"],
                      ssi_source_approved=bool(cases["ssi_ok"][i]), pset_valid=bool(cases["pset_ok"][i]),
                      original_linked=bool(cases["linked"][i]), four_eyes_required=bool(cfg.ACT_FOUR_EYES[a]),
                      calibrated=bool(calibrated_table(ag)[cls, a]), material_drift=not bool(stable_vector(ag)[cls]))
        d = decide(i, a, req, authenticated, declared, ev, g)
        key = f"P{i:04d}"
        payload = dict(key=key, action=common["action"], J=float(ev["comps"]["R"][i, a]), decision=d["decision"],
                       level=d["level"], reasons=[r["code"] for r in d["reasons"]])
        ehash = evidence_hash(payload)

        # shadow mode: gate logs, agent executes as requested
        add(shadow, seq_s, key=key, type="PROPOSE", agent=AGENTS[ag]["code"], **common)
        add(shadow, seq_s, key=key, type="GATE", decision=d["decision"], agent="gate")
        shadow_approvals = 1 if (req <= cfg.APPROVE) else 0
        for k in range(shadow_approvals):
            add(shadow, seq_s, key=key, type="APPROVE", approver=APPROVERS[k], agent=AGENTS[ag]["code"])
        add(shadow, seq_s, key=key, type="EXECUTE", agent=AGENTS[ag]["code"], authenticated=authenticated,
            level=req, mandate=int(MANDATE[a]), changes=changes,
            approved_transformation=declared <= authorised_changes(a),
            evidence_hash=None if no_evidence[i] else ehash, **common)

        # enforcing mode
        add(enforce, seq_e, key=key, type="PROPOSE", agent=AGENTS[ag]["code"], **common)
        add(enforce, seq_e, key=key, type="GATE", decision=d["decision"], agent="gate")
        if d["decision"] == "DENY":
            for r in d["reasons"]:
                gate_summary["DENY"][r["code"]] = gate_summary["DENY"].get(r["code"], 0) + 1
            esc = f"{key}.esc"
            add(enforce, seq_e, key=esc, type="EXECUTE", agent="ops-analyst", authenticated=True, level=cfg.HUMAN,
                mandate=cfg.AUTO, changes={}, approved_transformation=True, evidence_hash=ehash,
                action="ESCALATE", cls=common["cls"], ssi_source_approved=True, pset_valid=True,
                original_linked=True, four_eyes_required=False, calibrated=True, material_drift=False)
            continue
        lvl = d["level"]
        gate_summary["ALLOW"][cfg.LEVEL_NAMES[lvl]] += 1
        needs = 0
        if lvl < cfg.AUTO or changes.get("economics") or cfg.ACT_FOUR_EYES[a]:
            needs = 2 if cfg.ACT_FOUR_EYES[a] else 1
        for k in range(needs):
            add(enforce, seq_e, key=key, type="APPROVE", approver=APPROVERS[k], agent="human")
        executor = AGENTS[ag]["code"] if lvl >= cfg.APPROVE else "ops-analyst"
        add(enforce, seq_e, key=key, type="EXECUTE", agent=executor, authenticated=True, level=lvl,
            mandate=int(MANDATE[a]) if lvl >= cfg.APPROVE else cfg.AUTO, changes=changes,
            approved_transformation=True, evidence_hash=ehash, **common)

    v_shadow = check_trace(shadow)
    v_enforce = check_trace(enforce)
    chained, root = hash_chain(enforce)
    ok, _ = verify_chain(enforce, chained)
    tampered = [dict(e) for e in enforce]
    mid = len(tampered) // 2
    tampered[mid] = dict(tampered[mid], level=cfg.AUTO)
    t_ok, t_seq = verify_chain(tampered, chained)

    invariants = []
    for code, tex, text, _ in INVARIANTS:
        invariants.append(dict(code=code, tex=tex, text=text, shadow=len(v_shadow[code]),
                               enforcing=len(v_enforce[code]), examples=v_shadow[code][:3]))
    return dict(
        n=n, seed=seed, invariants=invariants,
        totals=dict(shadow=sum(len(v) for v in v_shadow.values()), enforcing=sum(len(v) for v in v_enforce.values()),
                    shadow_events=len(shadow), enforcing_events=len(enforce)),
        injected=dict(unauthenticated=int(unauth.sum()), missing_evidence=int(no_evidence.sum()),
                      field_tampering=int(tamper.sum())),
        gate=gate_summary,
        chain=dict(root=root, verified=ok, length=len(chained), tail=chained[-5:],
                   tamper_test=dict(modified_seq=tampered[mid]["seq"], verified=t_ok, first_break=t_seq)),
        trace_sample=enforce[:14],
    )
