"""Agentic Decision Mathematics — Flask entry point.

AI proposes. Mathematics decides what is permissible, optimal and sufficiently
certain. Controls decide whether it executes.
"""
import os
from flask import Flask, jsonify, render_template, request

from engine import config as cfg
from engine.agents import AGENT_INDEX
from engine import arena, benchmark, external, frontier, gate, savings, sensitivity

app = Flask(__name__)
app.json.sort_keys = False


def body():
    return request.get_json(silent=True) or {}


def clamp_int(v, lo, hi, default):
    try:
        return max(lo, min(hi, int(v)))
    except (TypeError, ValueError):
        return default


def clamp_float(v, lo, hi, default):
    try:
        return max(lo, min(hi, float(v)))
    except (TypeError, ValueError):
        return default


def agent_idx(code, default="B"):
    return AGENT_INDEX.get(code or default, AGENT_INDEX[default])


@app.errorhandler(external.InputError)
@app.errorhandler(KeyError)
def bad_request(err):
    return jsonify(error=str(err).strip("'")), 400


@app.get("/")
def index():
    return render_template("index.html")


@app.get("/healthz")
def health():
    return jsonify(status="ok")


@app.get("/api/catalogue")
def api_catalogue():
    data = frontier.catalogue()
    data["cases"] = arena.case_list()
    return jsonify(data)


@app.post("/api/arena")
def api_arena():
    b = body()
    mode = b.get("mode", "cvar")
    if mode not in ("expected", "cvar", "robust"):
        mode = "cvar"
    return jsonify(arena.analyse(b.get("case_id", arena.CASES[0]["id"]), b.get("lambdas"), mode,
                                 b.get("operating_agent", "B")))


@app.post("/api/benchmark")
def api_benchmark():
    b = body()
    return jsonify(benchmark.run(clamp_int(b.get("n"), 200, 5000, 2000), clamp_int(b.get("seed"), 0, 10**9, 2026),
                                 b.get("lambdas")))


@app.post("/api/benchmark/unblind")
def api_unblind():
    digest = str(body().get("manifest_hash", ""))
    if len(digest) != 64:
        return jsonify(error="Provide the 64-character manifest hash"), 400
    return jsonify(mapping=benchmark.unblind(digest))


@app.post("/api/frontier")
def api_frontier():
    return jsonify(frontier.frontier(agent_idx(body().get("agent"))))


@app.post("/api/sensitivity")
def api_sensitivity():
    b = body()
    keys = cfg.LAMBDA_KEYS
    x_key = b.get("x_key") if b.get("x_key") in keys else "F"
    y_key = b.get("y_key") if b.get("y_key") in keys else "H"
    if x_key == y_key:
        y_key = next(k for k in keys if k != x_key)
    out = sensitivity.analyse(b.get("case_id", arena.CASES[0]["id"]), b.get("lambdas"), x_key, y_key,
                              clamp_int(b.get("res"), 5, 31, 17), clamp_float(b.get("span"), 0.5, 5.0, 3.0))
    out["population"] = sensitivity.population_stability()
    return jsonify(out)


@app.post("/api/savings")
def api_savings():
    b = body()
    return jsonify(savings.lab(agent_idx(b.get("agent")), b.get("lambdas"),                                risk_budget=clamp_float(b.get("risk_budget"), -0.5, 1.0, 0.10),
                                target=clamp_float(b.get("target"), 0.0, 0.9, 0.25)))


@app.post("/api/proof")
def api_proof():
    b = body()
    return jsonify(math.simulate(clamp_int(b.get("n"), 50, 1500, 300), clamp_int(b.get("seed"), 0, 10**9, 11)))


@app.get("/api/evaluate")
def api_evaluate_example():
    return jsonify(mapping=external.EXAMPLE)


@app.post("/api/evaluate")
def api_evaluate():
    return jsonify(external.evaluate_proposal(body()))


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)), debug=bool(os.environ.get("FLASK_DEBUG")))
