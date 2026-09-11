"""Synthetic agents.

These stand in for any proposal source: an LLM agent, a vendor model, an ML
classifier or a person. The mathematics never trusts them; it only needs each
agent's interpretation (a probability vector over root causes) its proposed
action and the autonomy it requests. Real agents plug in through /api/evaluate.
"""
import numpy as np
from . import config as cfg
from .state import posterior

AGENTS = [
    dict(code="A", name="Agent A", style="Fast fixer: acts on its favourite diagnosis, always requests AUTO",
         tau=0.55, sigma=0.90, noise_slot=0),
    dict(code="B", name="Agent B", style="Cost-aware: weighs cost, time and reversibility, requests AUTO only when confident",
         tau=1.00, sigma=0.45, noise_slot=1),
   dict(code="R", name="Rules baseline", style="Deterministic rules: ignores soft feeds, maps diagnosis to a fixed action",
         tau=1.00, sigma=0.25, noise_slot=2),
]
AGENT_INDEX = {a["code"]: i for i, a in enumerate(AGENTS)}

# Rules baseline: hypothesis -> action
RULE_MAP = [cfg.ACTION_INDEX[c] for c in
              ["REPAIR_SSI", "REQUEST_CPTY", "REPAIR_PSET", "BORROW", "FUND", "AMEND_ECON", "WAIT"]]
SOFT_FEEDS = [2, 7]  # CPTY_SSI_UPDATED, FEED_LAG


def interpretation(agent_idx, cases):
    """Agent's probability vector p_hat (N,K)."""
    ag = AGENTS[agent_idx]
    if ag["code"] == "R":
        obs = cases["obs"].copy()
        obs[:, SOFT_FEEDS] = -1
        base = posterior(cases["prior"], obs, np.ones_like(cases["rel"]))
    else:
        base = cases["belief"]
    sigma = ag["sigma"] * np.where(cases["drift"] & (cases["cls"] == cfg.DRIFT_CLASS), cfg.DRIFT_NOISE_MULT, 1.0)
    logits = np.log(np.clip(base, 1e-9, 1)) / ag["tau"] + sigma[:, None] * cases["noise"][:, ag["noise_slot"], :]
    logits -= logits.max(1, keepdims=True)
    p = np.exp(logits)
    return p / p.sum(1, keepdims=True)


def propose(agent_idx, cases, p_hat=None):
    """%Returns (action_idx (N,J), requested_level (N,), p_hat (N,K))."""
    ag = AGENTS[agent_idx]
    if p_hat is None:
        p_hat = interpretation(agent_idx, cases)
    n = p_hat.shape[0]
    top = p_hat.argmax(1)
    agent_actions = np.arrange(cfg.ESC)  # agents never propose to escalate themselves
    if ag["code"] == "A":
        speed = cfg.P_RES[agent_actions][:, top].T / (cfg.ACT_TIME[agent_actions][None, :] + 1.0)
        action = agent_actions[speed.argmax(1)]
        level = np.full(n, cfg.AUTO)
    elif ag["code"] == "B":
        succ = p_hat @ cfg.P_RES[agent_actions].T
        util = succ - 0.002 * cfg.ACT_COST[agent_actions] - 0.02 * cfg.ACT_TIME[agent_actions] - 0.25 * cfg.ACT_IRREV[agent_actions]
        action = agent_actions[util.argmax(1)]
        level = np.where(p_hat.max(1) > 0.80, cfg.AUTO, cfg.APPROVE)
    else:
        action = np.array(RULE_MAP)[top]
        level = np.full(n, cfg.APPROVE)
    return action, level, p_hat
