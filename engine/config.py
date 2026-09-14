"""Synthetic domain catalogue and policy parameters.

Every number in this file is an illustrative assumption used to exercise the
mathematics. Replace it with institution data before drawing any operational
conclusion. Nothing here describes a real firm, client or system.
"""
import numpy as np

# ---------------------------------------------------------------------------
# Autonomy lattice
# ---------------------------------------------------------------------------
DENY, HUMAN, PROPOSE, APPROVE, AUTO = -1, 0, 1, 2, 3
LEVEL_NAMES = {DENY: "DENY", HUMAN: "HUMAN", PROPOSE: "PROPOSE", APPROVE: "APPROVE", AUTO: "AUTO"}
LEVEL_HELP = {
    "AUTO": "Agent executes; outcomes sampled after the fact",
    "APPROVE": "Agent prepares the executable action; a human approves it",
    "PROPOSE": "Agent recommends; a human investigates and executes",
    "HUMAN": "Agent is excluded; a human owns the case",
    "DENY": "Action is not permissible in this state",
}
# Share of the class handling time removed when a case runs at each level
LEVEL_SAVING = np.array([0.0, 0.35, 0.70, 0.95])
# Share of action errors that reach an effect undetected, by level
LEVEL_MISS = np.array([0.30, 0.25, 0.45, 1.00])
# Share of removed minutes that converts into releasable capacity (partial automation fragments work)
LEVEL_CAPTURE = np.array([0.0, 0.55, 0.70, 1.00])

# ---------------------------------------------------------------------------
# Hidden operational state: root-cause hypotheses
# --------------------------------------------------------------------------
HYPOTHESES = [
    ("OUR_SSI", "Our standing SSI is stable"),
    ("CPTY_SSI", "Counterparty SSI is stable"),
    ("PSET", "Place of settlement mismatch"),
    ("SEC_SHORT", "Securities position shortfall"),
    ("CASH_SHORT", "Cash funding shortfall"),
    ("ECON", "Trade economics disagree"),
    ("LAG", "Upstream data lag, self-resolving"),
]
K = len(HYPOTHESES)
