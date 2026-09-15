#!/usr/bin/env python3
"""Apply Batch 3 UI patches to app.js (idempotent). Called by deploy-pages workflow."""
import sys


def main(path):
    with open(path) as f:
        c = f.read()
    orig = c

    # Patch 1: "Three agents" -> "Synthetic agents"
    old1 = '<p>Three agents read the same operational state.'
    new1 = '<p>Synthetic agents read the same operational state.'
    if old1 in c:
        c = c.replace(old1, new1, 1)

    # Patch 2: manifest design disclosure in benchHtml
    old2 = 'regret by ${m.statistical_tests.regret}.</p></div>'
    new2 = ('regret by ${m.statistical_tests.regret}.</p>\n'
            '            <p class="small muted" style="margin:4px 0 0">${m.agents.count} participants. ${esc(m.agents.design || "")}</p></div>')
    if old2 in c:
        c = c.replace(old2, new2, 1)

    # Patch 3: R1-R3 provenance callout in frontierHtml (Lattice rule sheet)
    old3 = 'requires.")}\n          </div>\n        </div>\n\n        <div class="sheet"><div class="section-head"><h2>Calibration Registry</h2>'
    prov_line = ('            ${d.thresholds.provenance ? `<div class="callout" style="margin-top:12px">'
                 '<p class="small muted" style="margin:0">Risk thresholds R1=${num(d.thresholds.r1, 3)}, '
                 'R2=${num(d.thresholds.r2, 3)}, R3=${num(d.thresholds.r3, 3)} are derived from a stated '
                 'tolerable annual loss of \u20ac${(d.thresholds.provenance.tolerable_annual_loss / 1000).toFixed(0)}k '
                 'over ${d.thresholds.provenance.trading_days} trading days '
                 '(\u20ac${(d.thresholds.provenance.daily_risk_budget / 1000).toFixed(1)}k daily budget). '
                 '<a href="https://github.com/saumyajitghosh-collab/agentic-decision-mathematics/blob/main/engine/config.py" '
                 'target="_blank">See the derivation in config.py</a>.</p></div>` : ""}\n')
    new3 = 'requires.")}\n' + prov_line + '          </div>\n        </div>\n\n        <div class="sheet"><div class="section-head"><h2>Calibration Registry</h2>'
    if old3 in c:
        c = c.replace(old3, new3, 1)

    # Patch 4: uncertainty sweep section in savHtml + uncertaintyHtml function
    old4 = 'HC,F\\in\\mathbb{Z}_+`)}\n        </div>\n      </div>`;\n  }\n\n  // ---------------------------------------------------------------- proof'
    new4_parts = [
        'HC,F\\in\\mathbb{Z}_+`)}',
        '        </div>',
        '        ${d.uncertainty ? uncertaintyHtml(d.uncertainty) : ""}',
        '      </div>`;',
        '  }',
        '',
        '  function uncertaintyHtml(u) {',
        '    if (!u) return "";',
        '    const fmt = (v) => pct(v, 1);',
        '    return `',
        '        <div class="sheet"><h3>Uncertainty sweep \u00b7 what the FTE reduction depends on</h3>',
        '          <p class="lede">The headline FTE reduction is a point estimate inside this range. The two drivers below are the dominant uncertainties.</p>',
        '          <div class="kpis">',
        '            <div class="kpi"><div class="v">${fmt(u.fte_reduction_min)}</div><div class="k">FTE reduction \u00b7 low</div></div>',
        '            <div class="kpi"><div class="v">${fmt(u.fte_reduction_median)}</div><div class="k">FTE reduction \u00b7 median</div></div>',
        '            <div class="kpi"><div class="v">${fmt(u.fte_reduction_max)}</div><div class="k">FTE reduction \u00b7 high</div></div>',
        '          </div>',
        '          <div class="table-wrap"><table><thead><tr><th class="num">${esc(u.drivers[0])}</th><th class="num">${esc(u.drivers[1])}</th><th class="num">FTE reduction</th></tr></thead><tbody>',
        '            ${u.rows.map((r) => `<tr><td class="num">${r.capture_scale}</td><td class="num">${r.floor_scale}</td><td class="num">${fmt(r.fte_reduction)}</td></tr>`).join("")}',
        '          </tbody></table></div>',
        '          <p class="small muted">${esc(u.note)}</p>',
        '        </div>`;',
        '  }',
        '',
        '  // ---------------------------------------------------------------- proof',
    ]
    new4 = '\n'.join(new4_parts)
    if old4 in c:
        c = c.replace(old4, new4, 1)

    if c != orig:
        with open(path, "w") as f:
            f.write(c)
        print(f"patched {path}")
    else:
        print(f"no changes to {path}")


if __name__ == "__main__":
    main(sys.argv[1])
