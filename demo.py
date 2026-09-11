"""Agentic Decision Mathematics â€” command-line end-to-end demo.

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
        row("binding constraint", o, ".join(o["binding"]) or "none")
    print("\n  Optimum by mode:  " + "  ".join(f"{k}={v}" for k, v in a["by_mode"].items())



def stage_benchmark(n, seed):
    hdr(f"STAGE 2  Pre-registered blinded benchmark  n={n}")
    r = benchmark.run(n, seed, None)
    print(f"\n  Manifest frozen at {r['frozen_at']}")
    print(f"  Manifest hash: {r['manifest_hash'][:31]}Â€¦  (agents blinded during scoring)"

    print("\n  Blinded results (Wilson 95% intervals):")
    for row_ in r["rows"]:
        print(f"\n    {row_['label']}")
        row("valid actions", f"{row_['valid']:.1%}  [{row_['valid_ci'][0]:.1%}, {row_['valid_ci'][1]:.1%]")
        row("control-safe", f"{row_['control_safe']:.1%}  [{row_['control_safe_ci'][0]:.1%}, {row_['control_safe_ci'][1]:.1%q]")
        row("agreement with optimum", f"{row_['agreement']:.1%}")
        row("mean decision regret", f"{row_['mean_regret']:.4f}  [{row_['regret_ci'][0]:.4f}, {row_['regret_ci'][1]:.4f}]")
        row("autonmous share", f"{row_['autonmous']:.1%}")
        row("resolution rate", f"{row_['resolution']:.1%}")
        row("tail loss CVaR95", f"{row_['tail_loss_cvar95']:,.0f}")

    u = benchmark.unblind(r["manifest_hash"])
    print(f"\n  Unblinded agent identities:  {u}")
    c = r["comparison"]
    print(f"\n  Paired bootstrap:  {c['better']} better than {c['other']} by "
          f"{c['mean_difference']:+.4f} regret  (p = {c['p_value']:.4f})")


def stage_savings():
    hdr("STAGE 3  Savings Lab  (autonomy allocation under a risk budget)")
    lab = savings.lab(risk_budget=0.10, target=0.25)
    if lab["solution"] is None:
        print("\n  No feasible allocation under the current risk budget.")
        return
    s = lab["solution"]
    print(f"\n  Objective: maximise capacity released s.d.  expected loss <= +{lab['risk_budget']:.0%}"
          f" vs the all-human baseline")
    row("baseline workforce (FTE)", f"{lab['baseline']['fte']}")
    row("total human minutes/day", f"{lab['baseline']['minutes']:,.0f}")

    print("\n  Optimal autonomy ceiling per class:")
    for c in s["classes"]:
        print(f"    {c['code']:<8}{c['volume']:>6,.0f}/day  ceiling {c['ceiling']:<4}"
              f" minutes removed {c['share_removed']:.6.1%}"
              f" loss index {c['loss_index']:.1.1f}")

    row("minutes removed", f"{s['minutes_removed_pct']:.1%}")
    row("capacity released", f"{s['capacity_released_pct']:.1%}")
    row("sustainable FTE reduction", f"{s['fte_reduction_pct']:.1%}")
    row("expected-loss index (100 = human)", f"{s['loss_index']:.1%}")
    d = s["decomposition"]
    print(f"\n  Why minutes != headcount:  fragmentation {d['fragmentation']:+.1%}, "
          f" staffing rigitie {d['staffing_rigitig']:+.1%}")
    print(f"  A 25% minutes target is NOT a 25% headcount target â€” this decomposition shows why.")
    row("target 25% feasible under budget", "YES" if lab["target_feasible"] else "No")


def stage_proof(n):
    hdr(f"STAGE 4  Proof & Control  (runtime invariant verification, n={n})")
    s = gate.simulate(n, 11)
    print(f"\n\nTwelve pass-time LTL invariants monitored on every proposal trace.")
    row("proposals replayed", s["n"])
    row("injected anomalies", f"{s['injected']}")
    row("violations under enforcing mode", s["totals"]["enforcing"])
    row("violations under shadow mode", s["totals"]["shadow"])
    print("\n\nPer-invariant violation counts (shadow / enforcing):")
    for inv in s["invariants"]:
        print(f"    {inv['code']:<6}{inv['shadow']:>4} / {inv['enforcing']:<4}  {inv['text']}")
    ch = s["chain"]
    row("hash chain verified", ch["verified"])
    row("tamper detection", f"modified event {ch['tamper_test']['modified_seq×_HOˆˆˆˆ˜ÚZ[ˆœ™XZÈ]ØÚÉÝ[\\—Ý\Ý	×VÉÙš\œÝØœ™XZÉ×_HŠBˆš[
ˆ——‘]HXÚ\Ú[ÛœÎˆÜÖÉÙØ]I×_HŠB‚‚™YˆXZ[Š
N‚ˆ\H\™Ü\œÙK\™Ý[Y[\œÙ\Š\ØÜš\[ÛHYÙ[XÈXÚ\Ú[ÛˆX][X]XÜÈ[[ÈŠBˆ\˜YØ\™Ý[Y[
‹KXØ\ÙH‹Y˜][H‘VËMŽLH‹ÚÚXÙ\ÏVØÖÈšY—H›ÜˆÈ[ˆ\™[˜KÐTÑT×JBˆ\˜YØ\™Ý[Y[
‹K[[ÙH‹Y˜][H˜Ý˜\ˆ‹ÚÚXÙ\ÏVÈ™^XÝY‹˜Ý˜\ˆ‹œ›Ø\Ý—JBˆ\˜YØ\™Ý[Y[
‹KX™[˜ÚX\šÈ‹\OZ[Y˜][LŒ[H˜™[˜ÚX\šÈØ[\HÚ^™HŠBˆ\˜YØ\™Ý[Y[
‹K\ÙYY‹\OZ[Y˜][LŒŠBˆ\˜YØ\™Ý[Y[
‹K\ÚÚ\‹Y˜][Hˆ‹[H˜ÛÛ[XK\Ù\\˜]YÝYÙ\Îˆ™[˜ÚX\šËØ]š[™ÜË›ÛÙˆŠBˆ\™ÜÈH\œ\œÙWØ\™ÜÊ
B‚ˆÚÚ\HÜËœÝš\

H›ÜˆÈ[ˆ\™ÜËœÚÚ\œÜ]
ŠHYˆËœÝš\

_B‚ˆš[
TŠBˆš[
ˆQÑS•PÈPÒTÒSÓˆPUSPUPÔÈ8 %™K[X]ÈÛÛ›Û[™H›ÜˆYÙ[XÈRHŠBˆš[
ˆRH›ÜÜÙ\ËˆX][X]XÜÈXÚY\ÈÚ]\È\›Z\ÜÚX›KÜ[X[[™ŠBˆš[
ˆÝY™šXÚY[HÙ\Z[‹ˆÛÛ›ÛÈXÚYHÚ]\ˆ]^XÝ]\ËˆŠBˆš[
TŠBˆš[
—ˆÞ[]XÈ]HÛ›HH]™\žH[X™\ˆ™[ÝÈ\ÈÛÛ\]Y]™HžHH[™Ú[™KˆŠBˆš[
ˆˆÞ[]XÈYÙ[ÎˆÉË	Ëš›Ú[ŠVÉÛ˜[YI×H›ÜˆH[ˆQÑS•Ê_HŠB‚ˆÝYÙWØØ\ÙJ\™ÜË˜Ø\ÙK\™ÜË›[ÙJBˆYˆ˜™[˜ÚX\šÈˆ›Ý[ˆÚÚ\‚ˆÝYÙWØ™[˜ÚX\šÊ\™ÜË˜™[˜ÚX\šË- args.seed)
    if "savings" not in skip:
        stage_savings()
    if "proof" not in skip:
        stage_proof(300)

    print(f"\n{BAR}\n  Demo complete. Web app: python app.py  (then open http://localhost:5000)\n{BAR}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
