"""Runtime verification of control invariants.

A small past-time linear temporal logic (ptLTL) evaluated over finite event
traces. Each invariant has the form  G(φ): φ must hold at every position of
every proposal's trace. Past operators let a property refer to history:

  O ψ   (once)          ψ held at some earlier or current position
  H ψ   (historically)  ψ held at every earlier and current position

The monitor is independent of the gate. The gate enforces controls with the
decision mathematics; the monitor re-checks the resulting trace. Agreement
between the two is tested in tests/test_engine.py.
"""
import hashlib
import json
from dataclasses import dataclass
from typing import Callable


class Formula:
    def holds(self, trace, i):
        raise NotImplementedError


@dataclass
class Atom(Formula):
    name: str
    fn: Callable

    def holds(self, trace, i):
        return bool(self.fn(trace, i))


@dataclass
class Not(Formula):
    f: Formula

    def holds(self, trace, i):
        return not self.f.holds(trace, i)


@dataclass
class And(Formula):
    a: Formula
    b: Formula

    def holds(self, trace, i):
        return self.a.holds(trace, i) and self.b.holds(trace, i)


@dataclass
class Implies(Formula):
    a: Formula
    b: Formula

    def holds(self, trace, i):
        return (not self.a.holds(trace, i)) or self.b.holds(trace, i)


@dataclass
class Once(Formula):
    f: Formula

    def holds(self, trace, i):
        return any(self.f.holds(trace, j) for j in range(i + 1))


@dataclass
class Historically(Formula):
    f: Formula

    def holds(self, trace, i):
        return all(self.f.holds(trace, j) for j in range(i + 1))


def G_violations(formula, trace):
    """Positions where the body of G(formula) fails."""
    return [i for i in range(len(trace)) if not formula.holds(trace, i)]


# ---------------------------------------------------------------------------
# Atoms over events
# ---------------------------------------------------------------------------
EXEC = Atom("Execute", lambda t, i: t[i]["type"] == "EXECUTE")
APPROVAL = Atom("HumanApproval", lambda t, i: t[i]["type"] == "APPROVE")
GATE_DENY = Atom("GateDeny", lambda t, i: t[i]["type"] == "GATE" and t[i].get("decision") == "DENY")
AUTH = Atom("AuthenticatedIdentity", lambda t, i: bool(t[i].get("authenticated")))
ECON = Atom("EconomicChange", lambda t, i: bool(t[i].get("changes", {}).get("economics")))
SSI = Atom("SSIChange", lambda t, i: bool(t[i].get("changes", {}).get("ssi")))
SSI_OK = Atom("ApprovedSSI", lambda t, i: bool(t[i].get("ssi_source_approved")))
FOUR_REQ = Atom("FourEyesRequired", lambda t, i: bool(t[i].get("four_eyes_required")))
FOUR_OK = Atom("FourEyesApproved", lambda t, i: len({e.get("approver") for e in t[: i + 1] if e["type"] == "APPROVE"}) >= 2)
SETTLE = Atom("SettlementInstruction", lambda t, i: bool(t[i].get("changes", {}).get("settlement_instruction")))
PSET_OK = Atom("ValidSettlementLocation", lambda t, i: bool(t[i].get("pset_valid")))
CANCEL = Atom("CancelReplace", lambda t, i: bool(t[i].get("changes", {}).get("cancel_replace")))
LINKED = Atom("OriginalInstructionLinked", lambda t, i: bool(t[i].get("original_linked")))
WITHIN_MANDATE = Atom("AgentAuthority≤Mandate", lambda t, i: t[i].get("level", 0) <= t[i].get("mandate", 3))
AUTO_LEVEL = Atom("Autonomy=AUTO", lambda t, i: t[i].get("level") == 3)
CALIBRATED = Atom("Calibrated", lambda t, i: bool(t[i].get("calibrated")))
DRIFT = Atom("MaterialDrift", lambda t, i: bool(t[i].get("material_drift")))
PROTECTED = Atom("ProtectedFieldChange", lambda t, i: bool(t[i].get("changes", {}).get("protected")))
TRANSFORM_OK = Atom("ApprovedTransformation", lambda t, i: bool(t[i].get("approved_transformation")))
EVIDENCE = Atom("ReconstructableDecisionEvidence", lambda t, i: bool(t[i].get("evidence_hash")))

INVARIANTS = [
    ("I1", r"\mathbf{G}(\mathit{Execute} \rightarrow \mathit{AuthenticatedIdentity})",
     "Every execution carries an authenticated identity", Implies(EXEC, AUTH)),
    ("I2", r"\mathbf{G}(\mathit{Execute} \land \mathit{EconChange} \rightarrow \mathbf{O}\,\mathit{HumanApproval})",
     "Economic changes execute only after human approval", Implies(And(EXEC, ECON), Once(APPROVAL))),
    ("I3", r"\mathbf{G}(\mathit{Execute} \land \mathit{SSIChange} \rightarrow \mathit{ApprovedSSI})",
     "SSI changes come from an approved golden source", Implies(And(EXEC, SSI), SSI_OK)),
    ("I4", r"\mathbf{G}(\mathit{Execute} \land \mathit{FourEyesReq} \rightarrow \mathit{FourEyesApproved})",
     "Four-eyes actions have two distinct approvers", Implies(And(EXEC, FOUR_REQ), FOUR_OK)),
    ("I5", r"\mathbf{G}(\mathit{Execute} \land \mathit{SettlementInstr} \rightarrow \mathit{ValidPSET})",
     "Settlement instructions carry a valid place of settlement", Implies(And(EXEC, SETTLE), PSET_OK)),
    ("I6", r"\mathbf{G}(\mathit{Execute} \land \mathit{CancelReplace} \rightarrow \mathit{OriginalLinked})",
     "Cancel/replace links the original instruction", Implies(And(EXEC, CANCEL), LINKED)),
    ("I7", r"\mathbf{G}(\mathit{Execute} \rightarrow \mathit{Authority} \leq \mathit{Mandate})",
     "Executed autonomy never exceeds the agent's mandate", Implies(EXEC, WITHIN_MANDATE)),
    ("I8", r"\mathbf{G}(\mathit{Execute} \rightarrow \lnot\,\mathbf{O}\,\mathit{GateDeny})",
     "Nothing executes after the gate denies it", Implies(EXEC, Not(Once(GATE_DENY)))),
    ("I9", r"\mathbf{G}(\mathit{Execute} \land \mathit{AUTO} \rightarrow \mathit{Calibrated})",
     "Autonomous execution requires statistical calibration", Implies(And(EXEC, AUTO_LEVEL), CALIBRATED)),
    ("I10", r"\mathbf{G}(\mathit{Execute} \land \mathit{AUTO} \rightarrow \lnot\,\mathit{MaterialDrift})",
     "Autonomous execution is suspended under material drift", Implies(And(EXEC, AUTO_LEVEL), Not(DRIFT))),
    ("I11", r"\mathbf{G}(\mathit{Execute} \land \mathit{ProtectedChange} \rightarrow \mathit{ApprovedTransformation})",
     "Protected fields change only through approved transformations", Implies(And(EXEC, PROTECTED), TRANSFORM_OK)),
    ("I12", r"\mathbf{G}(\mathit{Execute} \rightarrow \mathit{DecisionEvidence})",
     "Every execution has reconstructable decision evidence", Implies(EXEC, EVIDENCE)),
]


def check_trace(events):
    """Group events by proposal key and evaluate every invariant. Returns violations."""
    by_key = {}
    for e in events:
        by_key.setdefault(e["key"], []).append(e)
    violations = {inv[0]: [] for inv in INVARIANTS}
    for key, trace in by_key.items():
        for code, _, _, body in INVARIANTS:
            for i in G_violations(body, trace):
                violations[code].append(dict(key=key, seq=trace[i]["seq"], action=trace[i].get("action"),
                                             agent=trace[i].get("agent")))
    return violations


# ---------------------------------------------------------------------------
# Tamper-evident decision log
# ---------------------------------------------------------------------------
def _digest(prev, event):
    payload = json.dumps(event, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256((prev + payload).encode()).hexdigest()


def hash_chain(events):
    prev = "0" * 64
    chained = []
    for e in events:
        h = _digest(prev, e)
        chained.append(dict(seq=e["seq"], prev=prev, hash=h))
        prev = h
    return chained, prev


def verify_chain(events, chained, trusted_head=None):
    """Verify a hash-chained event log against its chain metadata.

    Returns (ok, detail) where detail is the trusted head hash on success,
    or the seq of the first broken event on failure.  An empty or
    length-mismatched log is NOT verified.
    """
    if not events:
        return False, None
    if len(events) != len(chained):
        return False, chained[-1]["seq"] if chained else None
    prev = "0" * 64
    for e, c in zip(events, chained):
        if c["prev"] != prev or _digest(prev, e) != c["hash"]:
            return False, e["seq"]
        prev = c["hash"]
    if trusted_head is not None and prev != trusted_head:
        return False, chained[-1]["seq"]
    return True, prev
