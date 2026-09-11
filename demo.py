"""Agentic Decision Mathematics — command-line end-to-end demo.

Runs the full control-plane pipeline without a web server:

  1. One curated case, end to end: belief state -> agent proposals ->
     feasible set -> robust optimiser -> autonomy lattice -> gate -> regret.
  2. A pre-registered, blinded population benchmark across agents.
  3. The capacity-constrained savings lab (autonomy allocation MILP).
  4. The proof-and-control replay (runtime invariant verification).

Usage:
  python demo.py                     # all stages
  python demo.py --case EXC-48291 --mode robust
  python demo.py --skip benchmark,savings,proof

All data is synthetic. See engine/config.py.
"""
import argparse
import sys

from engine import arena, benchmark, gate, savings
from engine import config as cfg
from engine.agents import AGENTS

BAR = "=" * 78


def hdr(title):
    print(f"\n{BAR}\n  {title}\n{BAR}")


def row(label, value):
    print(f"    {label:<46}{value}")


def stage_case(case_id, mode):
    hdr(f"STAGE 1  Decision Arena  {case_id}  mode={mode}")
    a = arena.analyse(case_id, None, mode)

    print(f"\n  {a['case']['title']}  ({a['case']['cls']})")
    print(f"  {a['case']['story']}")
    row("notional", f"EUR {a['case']['notional']:,.0f}")
    row("hours to cutoff", f"{a['case']['cutoff_h']:.0f}h")

    print("\n  Belief state over root causes (the control layer owns this, not the agent):")
    for h, p in zip(a["hypotheses"], a["belief"]):
        bar = "#" * int(round(p * 40))
        print(f"    {h['code']:<12}{p:6.1%}  {bar}")
    row("normalised entropy", f"{a['uncertainty']:.3f}")
    row("drift", f"stable={a['drift']['stable']}  W1={a['drift']['w1']:.3f}")

    print("\n  Agent proposals under the mathematical judge:")
    for r in a["agents"]:
        print(f"\n    {r['name']:<6} proposes {r['proposal']:<28} requests {r['requested']}")
        row("gate", f"{r['gate']}"
            + (f"  [{' ,'.join(x['code'] for x in r['gate_reasons'])}]" if r["gate_reasons"] else ""))
        row("granted autonomy", r["granted"])
        row("stated confidence", f"{r['stated_confidence']:.0%}"
            + f"  (conformal set: {r['conformal_size']} hypotheses)")
        row("executed as", r["executed"])
        row("decision regret", f"{r['regret']:+.4f}")

    o = a["optimum"]
    print(f"\n  Optimal action under the {mode} objective:  {o['code']}  ({o['name']})")
    row("autonomy level", o["level"])
    row("binding constraint", ", ".join(o["binding"]) or "none")
    print("\n  Optimum by mode:  " + "   ".join(f"{k}={v}" for k, v in a["by_mode"].items()))


def stage_benchmark(n, seed):
    hdr(f"STAGE 2  Pre-registered blinded benchmark  n={n}")
    r = benchmark.run(n, seed, None)
    print(f"\n  Manifest frozen at {r['frozen_at']}")
    print(f"  Manifest hash: {r['manifest_hash'][:32]}…  (agents blinded during scoring)")

    print("\n  Blinded results (Wilson 95% intervals):")
    for row_ in r["rows"]:
        print(f"\n    {row_['label']}")
        row("valid actions", f"{row_['valid']:.1%}  [{row_['valid_ci'][0]:.1%}, {row_['valid_ci'][1]:.1%}]")
        row("control-safe", f"{row_['control_safe']:.1%}  [{row_['control_safe_ci'][0]:.1%}, {row_['control_safe_ci'][1]:.1%}]")
        row("agreement with optimum", f"{row_['agreement']:.1%}")
        row("mean decision regret", f"{row_['mean_regret']:.4f}  [{row_['regret_ci'][0]:.4f}, {row_['regret_ci'][1]:.4f}]")
        row("autonomous share", f"{row_['autonomous']:.1%}")
        row("resolution rate", f"{row_['resolution']:.1%}")
        row("tail loss CVaR95", f"{row_['tail_loss_cvar95']:,.0f}")

    u = benchmark.unblind(r["manifest_hash"])
    print(f"\n  Unblinded agent identities:  {u}")
    c = r["comparison"]
    print(f"  Paired bootstrap:  {c['better']} better than {c['other']} by "
          f"{c['mean_difference']:+.4f} regret  (p = {c['p_value']:.4f})")


def stage_savings():
    hdr("STAGE 3  Savings Lab  (autonomy allocation under a risk budget)")
    lab = savings.lab(risk_budget=0.10, target=0.25)
    if lab["solution"] is None:
        print("\n  No feasible allocation under the current risk budget.")
        return
    s = lab["solution"]
    print(f"\n  Objective: maximise capacity released s.t. expected loss <= +{lab['risk_budget']:.0%}"
          f" vs the all-human baseline")
    row("baseline workforce (FTE)", f"{lab['baseline']['fte']}")
    row("total human minutes/day", f"{lab['baseline']['minutes']:,.0f}")

    print("\n  Optimal autonomy ceiling per class:")
    for c in s["classes"]:
        print(f"    {c['code']:<16}{c['volume']:>6,.0f}/day  ceiling {c['ceiling']:<8}"
              f"  minutes removed {c['share_removed']:>6.1%}"
              f"  loss index {c['loss_index']:>5.1f}")

    row("minutes removed", f"{s['minutes_removed_pct']:.1%}")
    row("capacity released", f"{s['capacity_released_pct']:.1%}")
    row("sustainable FTE reduction", f"{s['fte_reduction_pct']:.1%}")
    row("expected-loss index (100 = human)", f"{s['loss_index']:.1f}")
    d = s["decomposition"]
    print(f"\n  Why minutes != headcount:  fragmentation {d['fragmentation']:+.1%},"
          f"  staffing rigidity {d['staffing_rigidity']:+.1%}")
    print(f"  A 25% minutes target is NOT a 25% headcount target — this decomposition shows why.")
    row("target 25% feasible under budget", "YES" if lab["target_feasible"] else "NO")


def stage_proof(n):
    hdr(f"STAGE 4  Proof & Control  (runtime invariant verification, n={n})")
    s = gate.simulate(n, 11)
    print(f"\n  Twelve past-time LTL invariants monitored on every proposal trace.")
    row("proposals replayed", s["n"])
    row("injected anomalies", f"{s['injected']}")
    row("violations — enforcing mode", s["totals"]["enforcing"])
    row("violations — shadow mode", s["totals"]["shadow"])
    print("\n  Per-invariant violation counts (shadow / enforcing):")
    for inv in s["invariants"]:
        print(f"    {inv['code']:<6}{inv['shadow']:>4} / {inv['enforcing']:<4}  {inv['text']}")
    ch = s["chain"]
    row("hash chain verified", ch["verified"])
    row("tamper detection", f"modified event {ch['tamper_test']['modified_seq']} -> "
        f"chain break at {ch['tamper_test']['first_break']}")
    print(f"\n  Gate decisions: {s['gate']}")


def main():
    ap = argparse.ArgumentParser(description="Agentic Decision Mathematics demo")
    ap.add_argument("--case", default="EXC-48291", choices=[c["id"] for c in arena.CASES])
    ap.add_argument("--mode", default="cvar", choices=["expected", "cvar", "robust"])
    ap.add_argument("--benchmark", type=int, default=2000, help="benchmark sample size")
    ap.add_argument("--seed", type=int, default=2026)
    ap.add_argument("--skip", default="", help="comma-separated stages: benchmark,savings,proof")
    args = ap.parse_args()

    skip = {s.strip() for s in args.skip.split(",") if s.strip()}

    print(BAR)
    print("  AGENTIC DECISION MATHEMATICS — a pure-maths control plane for agentic AI")
    print("  AI proposes. Mathematics decides what is permissible, optimal and")
    print("  sufficiently certain. Controls decide whether it executes.")
    print(BAR)
    print("\n  Synthetic data only — every number below is computed live by the engine.")
    print(f"  Synthetic agents: {', '.join(a['name'] for a in AGENTS)}")

    stage_case(args.case, args.mode)
    if "benchmark" not in skip:
        stage_benchmark(args.benchmark, args.seed)
    if "savings" not in skip:
        stage_savings()
    if "proof" not in skip:
        stage_proof(300)

    print(f"\n{BAR}\n  Demo complete. Web app: python app.py  (then open http://localhost:5000)\n{BAR}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
