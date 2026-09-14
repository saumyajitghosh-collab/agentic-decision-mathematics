"""Preregistered, blinded agent benchmark.

1. Freeze an evaluation manifest (population, evidence, metrics, loss function,
   invariants, calibration method, statistical tests) and hash it (SHA-256 of
   canonical JSON). Nothing in the manifest depends on which agent wins.
2. Score agents under blinded labels. The label permutation is derived from the
   manifest hash, so it is fixed before scoring and reproducible afterwards.
3. Unblind only by presenting the manifest hash.

Metrics
  valid           proposal âˆˆ A_safe
  control-safe    valid âˆ§ requested autonomy <= mathematically granted autonomy
  regret          J(a_exec) âˆ’ J(a*)            (a_exec = ESCALATE when the gate denies)
  human minutes   handling Â· (1 âˆ’ saving(level))
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
        loss_function=dict(form="J = Î£ Î»_k Â· component_k", lambdas=lam, tail_alpha=cfg.TAIL_ALPHA),
        control_invariants=[dict(code=c, tex=t) for c, t, _, _ in INVARIANTS],
        calibration=dict(method="split conformal", alpha_base=cfg.ALPHA_BASE, irreversibility_slope=cfg.ALPHA_IRREV_SLOPE,
                         coverage_tolerance=cfg.COVERAGE_TOL, set_size_max=cfg.SET_SIZE_MAX),
        statistical_tests=dict(rates="Wilson 95%", regret=f"percentile bootstrap, {BOOT} resamples",
                               comparison=f"paired bootstrap on regret difference, {BOOT} resamples"),
        agents=dict(count=len(AGENTS), identities="blinded until manifest hash is presented",
                    design="one participant is deliberately misspecified (reads a partial]šY[˜ÙH[Ù[
NÈ‚ˆH™[˜ÚX\šÈ\™Y›Ü™HYX\Ý\™\ÈXYÛ›ÜÝXÈ\ØÜš[Z[˜][Ûˆ\ÈÙ[\ÈØ[Xœ˜][Ûˆ›Ú\ÙHŠKˆ
BˆØ[›ÛˆHœÛÛ‹™[\Ê›ÙKÛÜÚÙ^\ÏUYKÙ\\˜]ÜœÏJ‹‹ŽˆŠJBˆYÙ\ÝH\ÚX‹œÚLMŠØ[›Û‹™[˜ÛÙJ
JKš^YÙ\Ý

Bˆ™]\›ˆ›ÙKYÙ\Ý‚‚™Yˆ›[™ÛX\
YÙ\Ý
N‚ˆ›™ÈHœœ˜[™ÛK™Y˜][Ü›™Ê[
YÙ\ÝÎŒL—KMŠJBˆ\›HH›™Ëœ\›]]][ÛŠ[ŠQÑS•ÊJBˆX™[ÈHÐ“S‘ÓP‘SÖË[[ŠQÑS•ÊN—Bˆ™]\›ˆÛX™[ÖÚ—NˆQÑS•ÖÚ[
\›VÚ—JWVÈ›˜[YH—H›Üˆˆ[ˆ˜[™ÙJ[ŠQÑS•ÊJ_K\›B‚‚™YˆÝÚ[ÛÛŠËŠN‚ˆÈHÚ[ÛÛ—ÛÝÙ\ŠËŠBˆHHHHÚ[ÛÛ—ÛÝÙ\ŠˆHËŠBˆ™]\›ˆÜ›Ý[™
Ë
K›Ý[™
K
WB‚‚™Yˆ[ŠLŒÙYYLŒ‹[OS›Û™JN‚ˆ›ÙKYÙ\ÝHX[šY™\Ý
‹ÙYY[JBˆ[HH›ÙVÈ›ÜÜ×Ù[˜Ý[Ûˆ—VÈ›[X™\È—BˆØ\Ù\ÈHÙ[™\˜]J‹ÙYYÙœ›ÛJ˜™[˜ÚX\šÈ‹ÙYY
JBˆ]ˆH]˜[X]JØ\Ù\ÊBˆˆHØš™XÝ]™J]–È˜ÛÛ\È—K[JBˆWÜÝ\ˆHœÚ\™J]–È™™X\ÚX›H—K‹œš[™ŠK˜\™ÛZ[ŠJBˆYHœ˜\˜[™ÙJŠBˆ]H]–Èœ˜]È—VÈœÚ[—Ý[YH—Bˆ˜\ÙWÛÜÜÈHÙ™ËPÕÐÓÔÕÓ›Û™K—H
ÈÙ™Ë’SPS—ÐÓÔÕÔT—ÓRSˆ
ˆ]–Èœ˜]È—VÈš[X[—ÛZ[]\È—Bˆ\›HHØ\Ù\ÖÈ™˜Z[ØÛÜÝ—VÎ‹›Û™WH
È
Ù™ËPÕÒT”‘Uˆ
ˆ
HHÙ™ËPÕÑUPÕ
JVÓ›Û™K—H
ˆØ\Ù\ÖÈœ™[YYX][Ûˆ—VÎ‹›Û™WB‚ˆÈ\‹XØ\ÙH™\››Ý[HÝ]ÛÛYH˜]ÜÈ
Ú\™YXÜ›ÜÜÈYÙ[È›ÜˆZ\™YÛÛ\\š\ÛÛŠBˆÝ]ÛÛYWÜ›™ÈHœœ˜[™ÛK™Y˜][Ü›™ÊÙYY
ÈÍÍÍÊBˆHHÝ]ÛÛYWÜ›™Ëœ˜[™ÛJŠB‚ˆYˆ™X[\ÙY
WÙ^XÊN‚ˆH]ÚYWÙ^XËØ\Ù\ÖÈžÝYH—WBˆ˜Z[HHˆˆÜÜÈH˜\ÙWÛÜÜÖÚYWÙ^X×H
È˜Z[
ˆ\›VÚYWÙ^X×Bˆ™]\›ˆÜÜÂ‚ˆYˆZ[
ÜÜÊN‚ˆHHœœ]X[[JÜÜËÙ™Ë•RSÐSJBˆ™]\›ˆ›Ø]
ÜÜÖÛÜÜÈHWK›YX[Š
JB‚ˆ›™ÈHœœ˜[™ÛK™Y˜][Ü›™ÊÙYY
Bˆ›ÛÝÚYH›™Ëš[YÙ\œÊ‹
“ÓÕŠJBˆË\›HH›[™ÛX\
YÙ\Ý
BˆX™[ÈHÐ“S‘ÓP‘SÖË[[ŠQÑS•ÊN—Bˆ›ÝÜË™YÜ™]ÈH×KßBˆ›Üˆ‹X™[[ˆ[[Y\˜]JX™[ÊN‚ˆYÈH[
\›VÚ—JBˆWÜ›Ü™\KÈH›ÜÜÙJYËØ\Ù\ÊBˆÈHÜ˜[
Ø\Ù\Ë]‹YÊBˆ˜[YH]–È™™X\ÚX›H—VÚYWÜ›ÜBˆÜ˜[YHÖÈ›]™[—VÚYWÜ›ÜBˆØY™HH˜[Y	ˆ
™\HHÜ˜[Y
BˆWÙ^XÈHœÚ\™J˜[YWÜ›ÜÙ™Ë‘TÐÊBˆ›HœÚ\™J˜[Yœ›Z[š[][J™\KÜ˜[Y
KÙ™Ë’SPSŠBˆ›HœÚ\™JWÙ^XÈOHÙ™Ë‘TÐËÙ™Ë’SPS‹›
Bˆ™YÜ™]H–ÚYWÙ^X×HH–ÚYWÜÝ\—BˆZ[]\ÈHØ\Ù\ÖÈš[™[™È—H
ˆ
HHÙ™Ë“U‘SÔÐU’S‘ÖÛ›JBˆÜ™\ËÜÜÈH™X[\ÙY
WÙ^XÊBˆ›ÛÝH™YÜ™]Ø›ÛÝÚYK›YX[ŠJBˆ™YÜ™]ÖÛX™[HH™YÜ™]ˆ›ÝÜË˜\[™
XÝ
ˆX™[[X™[ˆ˜[Y\›Ý[™
›Ø]
˜[Y›YX[Š
JK
K˜[YØÚOWÝÚ[ÛÛŠ[
˜[YœÝ[J
JKŠKˆÛÛ›ÛÜØY™O\›Ý[™
›Ø]
ØY™K›YX[Š
JK
KÛÛ›ÛÜØY™WØÚOWÝÚ[ÛÛŠ[
ØY™KœÝ[J
JKŠKˆYÜ™Y[Y[\›Ý[™
›Ø]

WÙ^XÈOHWÜÝ\ŠK›YX[Š
JK
KˆYX[—Ü™YÜ™]\›Ý[™
›Ø]
™YÜ™]›YX[Š
JK
Kˆ™YÜ™]ØÚOVÜ›Ý[™
›Ø]
œœ]X[[J›ÛÝŒJJK
K›Ý[™
›Ø]
œœ]X[[J›ÛÝŽMÍJJK
WKˆ[X[—ÛZ[]\Ï\›Ý[™
›Ø]
Z[]\Ë›YX[Š
JKŠKˆ™\ÛÛ][Û\›Ý[™
›Ø]
Ü™\Ë›YX[Š
JK
KˆZ[ÛÜÜ×ØÝ˜\ŽMO\›Ý[™
Z[
ÜÜÊKJKˆ]]Û›Û[Ý\Ï\›Ý[™
›Ø]

›OHÙ™ËUUÊK›YX[Š
JK
Kˆ
JBˆÛÜÜÜ×ÛÜH™X[\ÙY
WÜÝ\ŠBˆ™Y™\™[˜ÙHHXÝ
X™[H“X][X]XØ[Ü[][H‹˜[YLKŒÛÛ›ÛÜØY™OS›Û™KYÜ™Y[Y[LKŒYX[—Ü™YÜ™]LŒˆ[X[—ÛZ[]\ÏS›Û™K™\ÛÛ][Û\›Ý[™
›Ø]
ÛÜ›YX[Š
JK
KˆZ[ÛÜÜ×ØÝ˜\ŽMO\›Ý[™
Z[
ÜÜ×ÛÜ
KJK]]Û›Û[Ý\ÏS›Û™JB‚ˆ˜[šÙYHÛÜY
›ÝÜËÙ^O[[X™HŽˆ–È›YX[—Ü™YÜ™]—JBˆWÛX‹—ÛXˆH˜[šÙYÌVÈ›X™[—K˜[šÙYÌWVÈ›X™[—BˆY™ˆH™YÜ™]ÖØWÛX—HH™YÜ™]ÖØ—ÛX—Bˆ›ÛÝÙY™ˆHY™–Ø›ÛÝÚYK›YX[ŠJBˆÝÛÈH›Ø]
Z[ŠKŒˆ
ˆZ[Š
›ÛÝÙY™ˆH
K›YX[Š
K
›ÛÝÙY™ˆH
K›YX[Š
JJJBˆÛÛ\\š\ÛÛˆHXÝ
™]\XWÛX‹Ý\X—ÛX‹YX[—ÙY™™\™[˜ÙO\›Ý[™
›Ø]
Y™‹›YX[Š
JK
KˆÚOVÜ›Ý[™
›Ø]
œœ]X[[J›ÛÝÙY™‹ŒJJK
K›Ý[™
›Ø]
œœ]X[[J›ÛÝÙY™‹ŽMÍJJK
WKˆÝ˜[YO\›Ý[™
ÝÛË
JBˆ™]\›ˆXÝ
X[šY™\ÝX›ÙKX[šY™\ÝÚ\ÚYYÙ\Ýœ›Þ™[—Ø]Y]][YK››ÝÊ[Y^›Û™K]ÊKš\ÛÙ›Ü›X]
[Y\ÜXÏHœÙXÛÛ™ÈŠKˆ›ÝÜÏ\›ÝÜË™Y™\™[˜ÙO\™Y™\™[˜ÙKÛÛ\\š\ÛÛXÛÛ\\š\ÛÛŠB‚‚™Yˆ[˜›[™
YÙ\Ý
N‚ˆX\[™ËÈH›[™ÛX\
YÙ\Ý
Bˆ™]\›ˆX\[™Â