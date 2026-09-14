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
# ---------------------------------------------------------------------------
HYPOTHESES = [
    ("OUR_SSI", "Our standing SSI is stale"),
    ("CPTY_SSI", "Counterparty SSI is stale"),
    ("PSET", "Place of settlement mismatch"),
    ("SEC_SHORT", "Securities position shortfall"),
    ("CASH_SHORT", "Cash funding shortfall"),
    ("ECON", "Trade economics disagree"),
    ("LAG", "Upstream data lag, self-resolving"),
]
K = len(HYPOTHESES)

# ---------------------------------------------------------------------------
# Observable evidence: P(signal present | hypothesis), reliability range
# ---------------------------------------------------------------------------
EVIDENCE = [
    ("GOLDEN_SSI_DIFF", "Golden-source SSI differs from instruction", [0.92, 0.25, 0.30, 0.05, 0.05, 0.05, 0.10], (0.85, 1.00)),
    ("CPTY_NMAT", "Counterparty status: settlement details unmatched", [0.60, 0.85, 0.55, 0.05, 0.05, 0.30, 0.15], (0.60, 0.95)),
    ("CPTY_SSI_UPDATED", "Counterparty SSI updated in last 5 days", [0.10, 0.80, 0.20, 0.10, 0.10, 0.10, 0.15], (0.55, 0.90)),
    ("PSET_NONDEFAULT", "Place of settlement differs from market default", [0.20, 0.20, 0.90, 0.05, 0.05, 0.05, 0.05], (0.80, 1.00)),
    ("POSITION_SHORT", "Position projection shows shortfall", [0.05, 0.05, 0.05, 0.93, 0.10, 0.05, 0.20], (0.75, 1.00)),
    ("CASH_NEGATIVE", "Cash projection negative at cutoff", [0.05, 0.05, 0.05, 0.10, 0.92, 0.05, 0.15], (0.75, 1.00)),
    ("ECON_TOLERANCE", "Quantity or price outside matching tolerance", [0.05, 0.05, 0.05, 0.05, 0.05, 0.94, 0.10], (0.85, 1.00)),
    ("FEED_LAG", "Upstream feed lag above 30 minutes", [0.10, 0.10, 0.10, 0.20, 0.20, 0.10, 0.85], (0.50, 0.90)),
]
E = len(EVIDENCE)
LIK = np.array([e[2] for e in EVIDENCE])            # (E, K)
REL_RANGE = np.array([e[3] for e in EVIDENCE])      # (E, 2)
OBS_RATE = 0.85

# ---------------------------------------------------------------------------
# Exception classes
# ---------------------------------------------------------------------------
VOLUME_SCALE = 2.5
CLASSES = [
    dict(code="SSI_BREAK", name="SSI / static-data break", skill="Static data",
         prior=[0.38, 0.30, 0.14, 0.02, 0.02, 0.04, 0.10], volume=420, handling=14,
         history=42814, cal_n=8200, fail_cost=180, notional=2.5e6, propagation=0.70),
    dict(code="MATCH_BREAK", name="Settlement matching break", skill="Matching",
         prior=[0.06, 0.12, 0.12, 0.02, 0.02, 0.48, 0.18], volume=610, handling=11,
         history=61200, cal_n=8200, fail_cost=150, notional=3.0e6, propagation=0.45),
    dict(code="UNCONFIRMED", name="Unconfirmed counterparty instruction", skill="Matching",
         prior=[0.05, 0.40, 0.08, 0.02, 0.02, 0.18, 0.25], volume=380, handling=9,
         history=35500, cal_n=7100, fail_cost=120, notional=2.0e6, propagation=0.35),
    dict(code="SEC_FAIL", name="Securities shortfall / pending fail", skill="Settlements",
         prior=[0.03, 0.04, 0.03, 0.62, 0.04, 0.04, 0.20], volume=240, handling=22,
         history=18900, cal_n=3780, fail_cost=420, notional=6.0e6, propagation=0.60),
    dict(code="CASH_FAIL", name="Cash funding shortfall", skill="Cash & funding",
         prior=[0.02, 0.03, 0.02, 0.04, 0.66, 0.03, 0.20], volume=150, handling=18,
         history=12400, cal_n=2480, fail_cost=380, notional=8.0e6, propagation=0.55),
    dict(code="PSET_BREAK", name="Place of settlement mismatch", skill="Static data",
         prior=[0.18, 0.10, 0.55, 0.02, 0.02, 0.03, 0.10], volume=190, handling=12,
         history=15700, cal_n=3140, fail_cost=170, notional=2.5e6, propagation=0.50),
    dict(code="CANCEL_REPLACE", name="Cancel / replace amendment", skill="Settlements",
         prior=[0.08, 0.06, 0.06, 0.03, 0.02, 0.60, 0.15], volume=130, handling=16,
         history=9800, cal_n=1960, fail_cost=260, notional=4.0e6, propagation=0.40),
    dict(code="CORP_ACTION", name="Corporate action on pending trade", skill="Corporate actions",
         prior=[0.04, 0.04, 0.04, 0.22, 0.06, 0.45, 0.15], volume=12, handling=45,
         history=87, cal_n=42, fail_cost=900, notional=5.0e6, propagation=0.80),
]
C = len(CLASSES)
PRIORS = np.array([c["prior"] for c in CLASSES])
PRIORS = PRIORS / PRIORS.sum(1, keepdims=True)
CLASS_VOLUME = np.array([c["volume"] for c in CLASSES], float) * VOLUME_SCALE
CLASS_HANDLING = np.array([c["handling"] for c in CLASSES], float)
CLASS_FAIL = np.array([c["fail_cost"] for c in CLASSES], float)
CLASS_NOTIONAL = np.array([c["notional"] for c in CLASSES], float)
CLASS_PROP = np.array([c["propagation"] for c in CLASSES], float)
REMEDIATION_BASE = 500.0
NOTIONAL_SIGMA = 0.9

# Drift injected into one class for the demonstration
DRIFT_CLASS = 2  # UNCONFIRMED
DRIFT_PRIOR = np.array([0.14, 0.40, 0.10, 0.02, 0.02, 0.26, 0.06])
DRIFT_NOISE_MULT = 2.6
DRIFT_START_DAY = 60

# ---------------------------------------------------------------------------
# Candidate actions
# ---------------------------------------------------------------------------
# changes: which protected fields an action is authorised to modify
ACTIONS = [
    dict(code="REPAIR_SSI", name="Repair SSI from golden source", cost=2, time=0.5, minutes=2,
         irrev=0.30, detect=0.70, ctrl=0.50, policy_cap=AUTO, four_eyes=False, limit=None,
         changes=dict(ssi=True, settlement_instruction=True),
         p_res=[0.96, 0.10, 0.30, 0.02, 0.02, 0.03, 0.60]),
    dict(code="REQUEST_CPTY", name="Request counterparty re-instruction", cost=1, time=6.0, minutes=3,
         irrev=0.02, detect=0.90, ctrl=0.10, policy_cap=AUTO, four_eyes=False, limit=None,
         changes=dict(),
         p_res=[0.30, 0.90, 0.55, 0.05, 0.05, 0.55, 0.70]),
    dict(code="REPAIR_PSET", name="Repair place of settlement", cost=2, time=0.5, minutes=2,
         irrev=0.35, detect=0.65, ctrl=0.45, policy_cap=AUTO, four_eyes=False, limit=None,
         changes=dict(pset=True, settlement_instruction=True),
         p_res=[0.25, 0.10, 0.95, 0.02, 0.02, 0.03, 0.55]),
    dict(code="WAIT", name="Hold for upstream update", cost=0, time=4.0, minutes=0.5,
         irrev=0.00, detect=0.95, ctrl=0.05, policy_cap=AUTO, four_eyes=False, limit=None,
         changes=dict(),
         p_res=[0.05, 0.08, 0.05, 0.10, 0.10, 0.05, 0.94]),
    dict(code="BORROW", name="Borrow securities / partial settle", cost=40, time=3.0, minutes=4,
         irrev=0.60, detect=0.50, ctrl=0.40, policy_cap=AUTO, four_eyes=False, limit=25e6,
         changes=dict(release=True),
         p_res=[0.02, 0.02, 0.02, 0.88, 0.05, 0.03, 0.50]),
    dict(code="FUND", name="Request cash funding", cost=15, time=2.0, minutes=3,
         irrev=0.55, detect=0.55, ctrl=0.40, policy_cap=AUTO, four_eyes=False, limit=40e6,
         changes=dict(release=True),
         p_res=[0.02, 0.02, 0.02, 0.05, 0.91, 0.03, 0.50]),
    dict(code="AMEND_ECON", name="Amend trade economics", cost=5, time=1.0, minutes=5,
         irrev=0.70, detect=0.40, ctrl=0.90, policy_cap=APPROVE, four_eyes=True, limit=None,
         changes=dict(economics=True, protected=True),
         p_res=[0.03, 0.05, 0.05, 0.03, 0.03, 0.93, 0.45]),
    dict(code="CANCEL_REBOOK", name="Cancel and rebook", cost=18, time=5.0, minutes=8,
         irrev=0.85, detect=0.35, ctrl=0.85, policy_cap=APPROVE, four_eyes=True, limit=None,
         changes=dict(cancel_replace=True, protected=True, release=True, settlement_instruction=True),
         p_res=[0.75, 0.50, 0.72, 0.05, 0.05, 0.95, 0.60]),
    dict(code="ESCALATE", name="Route to operations analyst", cost=0, time=5.0, minutes=None,
         irrev=0.00, detect=1.00, ctrl=0.00, policy_cap=HUMAN, four_eyes=False, limit=None,
         changes=dict(),
         p_res=[0.84, 0.80, 0.84, 0.76, 0.78, 0.84, 0.95]),
]
A = len(ACTIONS)
ESC = A - 1
P_RES = np.array([a["p_res"] for a in ACTIONS])            # (A, K)
ACT_COST = np.array([a["cost"] for a in ACTIONS], float)
ACT_TIME = np.array([a["time"] for a in ACTIONS], float)
ACT_MIN = np.array([a["minutes"] or 0 for a in ACTIONS], float)
ACT_IRREV = np.array([a["irrev"] for a in ACTIONS], float)
ACT_DETECT = np.array([a["detect"] for a in ACTIONS], float)
ACT_CTRL = np.array([a["ctrl"] for a in ACTIONS], float)
ACT_POLICY_CAP = np.array([a["policy_cap"] for a in ACTIONS], int)
ACT_FOUR_EYES = np.array([a["four_eyes"] for a in ACTIONS], bool)
ACT_LIMIT = np.array([a["limit"] or np.inf for a in ACTIONS], float)
ACT_SETTLE_INSTR = np.array([bool(a["changes"].get("settlement_instruction")) for a in ACTIONS])
ACT_SSI = np.array([bool(a["changes"].get("ssi")) for a in ACTIONS])
ACT_CANCEL = np.array([bool(a["changes"].get("cancel_replace")) for a in ACTIONS])
ACTION_INDEX = {a["code"]: i for i, a in enumerate(ACTIONS)}

# ---------------------------------------------------------------------------
# Economics of the loss model
# ---------------------------------------------------------------------------
HUMAN_COST_PER_MIN = 1.5      # EUR
LATE_FACTOR = 0.30            # resolution probability kept if action lands after cutoff
FOLLOWUP_HOURS = 8.0
C_REF = 250.0                 # EUR normaliser for cost terms
EXPOSURE_REF = 50e6           # EUR notional normaliser for severity
EXPOSURE_SIGMA = 0.6          # loss multiplier dispersion
EXPOSURE_GRID = 16            # quantile grid points for exact discrete CVaR
TAIL_ALPHA = 0.95
TAIL_FLOOR = 1500.0           # EUR, g(x,a) = CVaR - max(floor, bps · notional) <= 0
TAIL_BPS = 1.5e-4
ROBUST_EPS = 0.30             # ε-contamination radius for the robust mode

# Severity weights: exposure, irreversibility, (1-detectability), propagation, control severity
SEVERITY_W = np.array([0.30, 0.25, 0.15, 0.15, 0.15])

# Risk thresholds for the autonomy lattice.
#
# Provenance. R = E[P_err · Severity] is a per-case risk score in [0, 1]
# (severity weights sum to 1). The thresholds are derived from a stated
# risk appetite — the board-level tolerable annual operational loss — and
# the frozen synthetic population (seed 99, n = 2000):
#
#   TOLERABLE_ANNUAL_LOSS   stated risk appetite (EUR)
#   TRADING_DAYS            business days per year
#   DAILY_RISK_BUDGET       = TOLERABLE_ANNUAL_LOSS / TRADING_DAYS
#
# For a candidate threshold t, the expected daily EUR loss from letting
# every case with R < t run autonomously is vol · E[p_err · harm · 1{R<t}].
# Solving for the t that consumes a target share of DAILY_RISK_BUDGET:
#
#   R1 = 0.050  consumes ≈ 1.0% of the daily budget   (AUTO band)
#   R2 = 0.110  consumes ≈ 6.3% of the daily budget   (APPROVE band)
#   R3 = 0.250  consumes ≈ 21.6% of the daily budget  (PROPOSE band)
#
# (PROPOSE is still gated by a human; the 22% spend is the upper envelope
# before HUMAN takeover.) Values are pinned here as constants so the
# lattice is reproducible without re-running the population simulation.
TOLERABLE_ANNUAL_LOSS = 250_000   # EUR, board-stated risk appetite for this book
TRADING_DAYS = 252
DAILY_RISK_BUDGET = TOLERABLE_ANNUAL_LOSS / TRADING_DAYS   # ≈ EUR 992/day
R1, R2, R3 = 0.050, 0.110, 0.250

# Autonomy score: benefit - wR*R - wI*irreversibility - wU*uncertainty
AUT_W_R, AUT_W_I, AUT_W_U = 2.0, 0.55, 0.60
S_AUTO, S_APPROVE, S_PROPOSE = 0.45, 0.20, -0.05

# Conformal calibration
ALPHA_BASE = 0.05             # alpha for a fully reversible action
ALPHA_IRREV_SLOPE = 0.9       # alpha(a) = base * (1 - slope * irrev)
COVERAGE_TOL = 0.020
SET_SIZE_MAX = 3.5
TEST_N_CAP = 4000

# Drift monitor
DRIFT_DAYS, DRIFT_BASELINE_DAYS, DRIFT_DAILY_N = 70, 60, 150
W_EPS, KL_EPS = 0.035, 0.050
CUSUM_K_SIGMA, CUSUM_H_SIGMA = 0.5, 5.0

# Objective weights (lambda) and presets
LAMBDA_KEYS = ["C", "R", "T", "H", "F", "K"]
LAMBDA_LABELS = {
    "C": "Economic cost", "R": "Operational risk", "T": "Resolution time",
    "H": "Human effort", "F": "Settlement failure", "K": "Tail loss (CVaR)",
}
DEFAULT_LAMBDAS = {"C": 1.0, "R": 1.0, "T": 0.5, "H": 0.8, "F": 1.0, "K": 0.15}
PRESETS = {
    "COO": {"C": 1.0, "R": 1.0, "T": 1.5, "H": 2.0, "F": 1.0, "K": 0.15},
    "Risk": {"C": 1.0, "R": 2.5, "T": 0.5, "H": 0.5, "F": 2.5, "K": 0.60},
    "Operations": {"C": 1.0, "R": 1.0, "T": 1.0, "H": 1.0, "F": 1.0, "K": 0.15},
    "Finance": {"C": 2.0, "R": 1.0, "T": 0.5, "H": 1.6, "F": 1.0, "K": 0.15},
}

# Workforce model
REGIONS = [("APAC", 0.25), ("EMEA", 0.45), ("AMER", 0.30)]
SKILLS = ["Static data", "Matching", "Settlements", "Cash & funding", "Corporate actions"]
SKILL_FLOOR = {"Static data": 1, "Matching": 1, "Settlements": 2, "Cash & funding": 1, "Corporate actions": 2}
MINUTES_PER_FTE = 420.0
STRESS_FACTOR = 1.25
FLEX_EFFICIENCY = 0.80
FLEX_COST = 1.10


def alpha_for_action(a_idx):
    return ALPHA_BASE * (1.0 - ALPHA_IRREV_SLOPE * ACT_IRREV[a_idx])


def normalise_lambdas(lam):
    out = dict(DEFAULT_LAMBDAS)
    for k, v in (lam or {}).items():
        if k in out:
            out[k] = max(0.0, float(v))
    return out
