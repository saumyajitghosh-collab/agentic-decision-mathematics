"""API dispatcher — mirrors app.py's Flask routes, executed inside Pyodide.

Takes (path, method, body_json_string) and returns a JSON string, so the
JavaScript fetch interceptor can wrap it in a Response object.
"""
import json
import numpy as np


def handle_request(path, method, body_str):
    body = json.loads(body_str) if body_str and body_str != '{}' else {}

    from engine import arena, benchmark, external, frontier, gate, savings, sensitivity
    from engine import config as cfg
    from engine.agents import AGENT_INDEX

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

    result = None

    if path == '/api/catalogue':
        result = frontier.catalogue()
        result["cases"] = arena.case_list()

    elif path == '/api/arena':
        mode = body.get("mode", "cvar")
        if mode not in ("expected", "cvar", "robust"):
            mode = "cvar"
        result = arena.analyse(
            body.get("case_id", arena.CASES[0]["id"]),
            body.get("lambdas"), mode,
            body.get("operating_agent", "B")
        )

    elif path == '/api/benchmark':
        result = benchmark.run(
            clamp_int(body.get("n"), 200, 5000, 2000),
            clamp_int(body.get("seed"), 0, 10 ** 9, 2026),
            body.get("lambdas")
        )

    elif path == '/api/benchmark/unblind':
        digest = str(body.get("manifest_hash", ""))
        if len(digest) != 64:
            result = {"error": "Provide the 64-character manifest hash"}
        else:
            result = {"mapping": benchmark.unblind(digest)}

    elif path == '/api/frontier':
        result = frontier.frontier(agent_idx(body.get("agent")))

    elif path == '/api/sensitivity':
        keys = cfg.LAMBDA_KEYS
        x_key = body.get("x_key") if body.get("x_key") in keys else "F"
        y_key = body.get("y_key") if body.get("y_key") in keys else "H"
        if x_key == y_key:
            y_key = next(k for k in keys if k != x_key)
        out = sensitivity.analyse(
            body.get("case_id", arena.CASES[0]["id"]),
            body.get("lambdas"), x_key, y_key,
            clamp_int(body.get("res"), 5, 31, 17),
            clamp_float(body.get("span"), 0.5, 5.0, 3.0)
        )
        out["population"] = sensitivity.population_stability()
        result = out

    elif path == '/api/savings':
        result = savings.lab(
            agent_idx(body.get("agent")),
            body.get("lambdas"),
            risk_budget=clamp_float(body.get("risk_budget"), -0.5, 1.0, 0.10),
            target=clamp_float(body.get("target"), 0.0, 0.9, 0.25)
        )

    elif path == '/api/proof':
        result = gate.simulate(
            clamp_int(body.get("n"), 50, 1500, 300),
            clamp_int(body.get("seed"), 0, 10 ** 9, 11)
        )

    elif path == '/api/evaluate' and method == 'GET':
        result = {
            "description": "POST a proposal from any agent to this endpoint.",
            "example": external.EXAMPLE
        }

    elif path == '/api/evaluate' and method == 'POST':
        result = external.evaluate_proposal(body)

    elif path == '/healthz':
        result = {"status": "ok"}

    else:
        result = {"error": "Unknown endpoint: %s %s" % (method, path)}

    def default(o):
        if isinstance(o, np.integer):
            return int(o)
        if isinstance(o, np.floating):
            return float(o)
        if isinstance(o, np.ndarray):
            return o.tolist()
        if isinstance(o, (set, frozenset)):
            return sorted(o)
        if isinstance(o, bytes):
            return o.decode('utf-8', errors='replace')
        raise TypeError("Not serializable: %r" % type(o))

    return json.dumps(result, default=default)
