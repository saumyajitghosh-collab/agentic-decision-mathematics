"""Policy sensitivity.

J(a; Î») = Î£_k Î»_k Â· c_k(a) is linear in every Î»_k, so along a one-dimensional
sweep of Î»_k each action is a straight line  J_a(Î»_k) = Î²_a + Î»_k Â· c_k(a).
The optimal action is the lower envelope of those lines, and its breakpoints are
exact line intersections â€” no grid search:

  Î»* = (Î²_b âˆ’ Î²_a) / (c_k(a) âˆ’ c_k(b))   for the next action b that undercuts a.

The two-dimensional phase diagram evaluates the same linear form on a grid.
Across a population, a class is "decision-stable" when the optimal action is the
same under every stakeholder preset; otherwise the disagreement is about risk
appetite, not about the AI.
"""
from functools import lru_cache
import numpy as np
from . import config as cfg
from .arena import load_case
from .core import evaluate, objective
from .state import generate, seed_from


def lower_envelope(beta, slope, feasible, key_range):
    lo, hi = key_range
    idx = np.where(feasible)[0]
    beta, slope = beta[idx], slope[idx]
    x = lo
    vals = beta + x * slope
    tied = np.where(vals <= vals.min() + 1e-12)[0]
    cur = int(tied[np.argmin(slope[tied])])
    segments = []
    while True:
        cand = []
        for j in range(len(idx)):
            if j == cur or slope[j] >= slope[cur]:
                continue
            xc = (beta[j] - beta[cur]) / (slope[cur] - slope[j])
            if xc > x + 1e-12:
                cand.append((xc, j))
        if not cand:
            segments.append(dict(action=cfg.ACTIONS[idx[cur]]["code"], start=round(float(x), 4), end=round(float(hi), 4)))
            break
        xc, j = min(cand)
        # tie-break: among lines crossing at the same point take the smallest slope
        ties = [jj for (xx, jj) in cand if abs(xx - xc) < 1e-9]
        j = min(ties, key=lambda jj: slope[jj])
        if xc >= hi:
            segments.append(dict(action=cfg.ACTIONS[idx[cur]]["code"], start=round(float(x), 4), end=round(float(hi), 4)))
            break
        segments.append(dict(action=cfg.ACTIONS[idx[cur]]["code"], start=round(float(x), 4), end=round(float(xc), 4)))
        x, cur = xc, j
    return segments


def analyse(case_id, lam=None, x_key="F", y_key="H", res=17, span=3.0, sweep_key=None):
    lam = cfg.normalise_lambdas(lam)
    cases, spec = load_case(case_id)
    ev = evaluate(cases)
    comps = {k: v[0] for k, v in ev["comps"].items()}
    feasible = ev["feasible"][0]

    presets = []
    for name, p in cfg.PRESETS.items():
        J = objective({k: v[None] for k, v in comps.items()}, p)[0]
        a = int(np.where(feasible, J, np.inf).argmin())
        presets.append(dict(name=name, lambdas=p, action=cfg.ACTIONS[a]["code"]))
    stable = len({p["action"] for p in presets}) == 1

    xs = np.linspace(0, span, res)
    ys = np.linspace(0, span, res)
    base = sum(lam[k] * comps[k] for k in cfg.LAMBDA_KEYS if k not in (x_key, y_key))
    grid = base[None, None, :] + xs[None, :, None] * comps[x_key][None, None, :] + ys[:, None, None] * comps[y_key][None, None, :]
    grid = np.where(feasible[None, None, :], grid, np.inf)
    phase = grid.argmin(-1)
    codes = [cfg.ACTIONS[a]["code"] for a in range(cfg.A)

    sweeps = {}
    for k in ([sweep_key] if sweep_key else cfg.LAMBDA_KEYS):
        beta = sum(lam[j] * comps[j] for j in cfg.LAMBDA_KEYS if j != k)
        segs = lower_envelope(beta, comps[k], feasible, (0.0, 5.0))
        sweeps[k] = dict(segments=segs, current=lam[k],
                          breakpoints=[s["start"] for s in segs[1:]])

    J_now = objective({k: v[None] for k, v in comps.items()}, lam)[0]
    a_now = int(np.where(feasible, J_now, np.inf).argmin())
    return dict(
        case=dict(id=spec["id"], title=spec["title"]), lambdas=lam, x_key=x_key, y_key=y_key,
            xs=[round(float(v), 3) for v in xs], ys=[round(float(v), 3) for v in xs],
        pa¡…Í”õmm½‘•Ím¥¹Ğ¡„¥t™½È„¥¸É½İt™½ÈÉ½Ü¥¸Á¡…Í•t°(€€€€€€€ÁÉ•Í•ÑÌõÁÉ•Í•ÑÌ°ÍÑ…‰±”õÍÑ…‰±”°ÕÉÉ•¹Ğõ™œ¹Q%=9Mm…}¹½İul‰½‘”‰t°Íİ••ÁÌõÍİ••ÁÌ°(€€€€€€€€€€€½µÁ½¹•¹ÑÌõí¬èí½‘•Ím…tèÉ½Õ¹¡™±½…Ğ¡½µÁÍm­um…t¤°€Ğ¤™½È„¥¸É…¹”¡™œ¹¤¥˜™•…Í¥‰±•m…uô™½È¬¥¸™œ¹15	}-eMô°(€€€€¤(()±ÉÕ}…¡”¡µ…áÍ¥é”ôĞ¤)‘•˜Á½ÁÕ±…Ñ¥½¹}ÍÑ…‰¥±¥Ñä¡¸ôÈĞÀÀ°Í••ôÔ¤è(€€€…Í•Ì€ô•¹•É…Ñ”¡¸°Í••‘}™É½´ ‰ÍÑ…‰¥±¥Ñäˆ°Í••¤¤(€€€•Ø€ô•Ù…±Õ…Ñ”¡…Í•Ì¤(€€€¡½¥•Ì€ômt(€€€™½È¹…µ”°À¥¸™œ¹AIMQL¹¥Ñ•µÌ ¤è(€€€€€€€(€ô½‰©•Ñ¥Ù”¡•Ùl‰½µÁÌ‰t°À¤(€€€€€€€¡½¥•Ì¹…ÁÁ•¹¡¹À¹İ¡•É”¡•Ùl‰™•…Í¥‰±”‰t°(°¹À¹¥¹˜¤¹…Éµ¥¸ Ä¤¤(€€€¡½¥•Ì€ô¹À¹ÍÑ…¬¡¡½¥•Ì°€Ä¤(€€€…É•”€ô€¡¡½¥•Ì€ôô¡½¥•Ílè°€èÅt¤¹…±° Ä¤(€€€É½İÌ€ômt(€€€™½ÈŒ¥¸É…¹”¡™œ¹¤è(€€€€€€€´€ô…Í•Íl‰±Ì‰t€ôôŒ(€€€€€€€€Œµ½ÍĞ½µµ½¸‘¥Í…É••µ•¹Ğèİ¡¥ ÁÉ•Í•Ğ‘•Á…ÉÑÌ™É½´=Á•É…Ñ¥½¹Ìµ½ÍĞ½™Ñ•¸(€€€€€€€½ÁÌ€ô±¥ÍĞ¡™œ¹AIMQL¤¹¥¹‘•à ‰=Á•É…Ñ¥½¹Ìˆ¤(€€€€€€€‘•Á…ÉÑÌ€ôí¹…µ”è™±½…Ğ ¡¡½¥•Ím´°¥t€„ô¡½¥•Ím´°½ÁÍt¤¹µ•…¸ ¤¤™½È¤°¹…µ”¥¸•¹Õµ•É…Ñ”¡™œ¹AIMQL¤¥˜¤€„ô½ÁÍô(€€€€€€€É½İÌ¹…ÁÁ•¹¡‘¥Ğ¡½‘”õ™œ¹1MMMmul‰½‘”‰t°¹…µ”õ™œ¹1MMMmul‰¹…µ”‰t°¸õ¥¹Ğ¡´¹ÍÕ´ ¤¤°(€€€€€€€€€€€€€€€€€€€€€€€€ÍÑ…‰±•}Í¡…É”õÉ½Õ¹¡™±½…Ğ¡…É••mµt¹µ•…¸ ¤¤°€Ğ¤°(€€€€€€€€€€€€€€€€€€€€€€€€‘•Á…ÉÑÌõí¬èÉ½Õ¹¡Ø°€Ğ¤™½È¬°Ø¥¸‘•Á…ÉÑÌ¹¥Ñ•µÌ ¤¥ô¤¤(€€€É•ÑÕÉ¸‘¥Ğ¡½Ù•É…±°õÉ½Õ¹¡™±½…Ğ¡…É•”¹µ•…¸ ¤¤°€Ğ¤°±…ÍÍ•ÌõÉ½İÌ¤(