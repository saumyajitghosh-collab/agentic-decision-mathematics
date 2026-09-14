// Pyodide Bridge for Agentic Decision Mathematics
// Runs the full Python mathematical engine in the browser via WebAssembly.
// Intercepts fetch('/api/...') calls and routes them to Pyodide — the
// existing frontend (app.js) is completely unmodified.

let pyodide = null;

const PYODIDE_CDN = 'https://cdn.jsdelivr.net/pyodide/v0.26.4/full/';
const ENGINE_BASE = 'https://raw.githubusercontent.com/saumyajitghosh-collab/agentic-decision-mathematics/main/engine/';

const ENGINE_FILES = [
    '__init__.py', 'config.py', 'state.py', 'agents.py', 'core.py',
    'uncertainty.py', 'autonomy.py', 'invariants.py', 'gate.py',
    'arena.py', 'benchmark.py', 'sensitivity.py', 'savings.py',
    'frontier.py', 'external.py'
];

async function initPyodide() {
    const statusEl = document.getElementById('py-status');
    const setStat = (msg) => { if (statusEl) statusEl.textContent = msg; };

    setStat('Loading Pyodide runtime (10 MB)...');
    pyodide = await loadPyodide({ indexURL: PYODIDE_CDN });

    setStat('Loading numpy and scipy...');
    await pyodide.loadPackage(['numpy', 'scipy']);

    // Create engine directory in the virtual filesystem
    pyodide.FS.mkdirTree('/engine');

    // Fetch each engine .py file from GitHub and install into the VFS
    setStat('Loading mathematical engine (15 modules)...');
    for (const file of ENGINE_FILES) {
        const resp = await fetch(ENGINE_BASE + file);
        if (!resp.ok) throw new Error('Failed to fetch ' + file + ': ' + resp.status);
        const code = await resp.text();
        pyodide.FS.writeFile('/engine/' + file, code);
    }

    // Make / importable and load the engine package
    pyodide.runPython('import sys; sys.path.insert(0, "/")');
    pyodide.runPython('import engine');

    // Load the API dispatcher
    setStat('Initializing API layer...');
    const dispResp = await fetch('engine_dispatcher.py');
    if (!dispResp.ok) throw new Error('Failed to fetch engine_dispatcher.py: ' + dispResp.status);
    const dispCode = await dispResp.text();
    pyodide.runPython(dispCode);

    // ---- Install fetch interceptor ----
    const originalFetch = window.fetch;
    window.fetch = async function(input, init) {
        const url = typeof input === 'string'
            ? input
            : (input instanceof URL ? input.href : (input && input.url) || '');
        const method = ((init && init.method) || 'GET').toUpperCase();

        if (url.startsWith('/api/') || url === '/healthz') {
            const bodyStr = (init && init.body) ? init.body : '{}';
            pyodide.globals.set('_req_path', url);
            pyodide.globals.set('_req_method', method);
            pyodide.globals.set('_req_body', bodyStr);
            try {
                const resultStr = pyodide.runPython(
                    'handle_request(_req_path, _req_method, _req_body)'
                );
                return new Response(resultStr, {
                    status: 200,
                    headers: { 'Content-Type': 'application/json' }
                });
            } catch (err) {
                const msg = String((err && err.message) || err);
                return new Response(JSON.stringify({ error: msg }), {
                    status: 400,
                    headers: { 'Content-Type': 'application/json' }
                });
            }
        }
        return originalFetch(input, init);
    };

    // Hide loading overlay
    const overlay = document.getElementById('pyodide-loading');
    if (overlay) overlay.style.display = 'none';

    // Dynamically load app.js now that the engine is ready
    const script = document.createElement('script');
    script.src = 'static/js/app.js';
    document.body.appendChild(script);
}

window.addEventListener('DOMContentLoaded', function () {
    initPyodide().catch(function (err) {
        console.error('Pyodide initialization failed:', err);
        const overlay = document.getElementById('pyodide-loading');
        if (overlay) {
            overlay.innerHTML =
                '<div style="color:#f85149;padding:24px;max-width:520px;text-align:left">' +
                '<h2 style="margin:0 0 12px">Engine failed to load</h2>' +
                '<p style="color:#7d8590;margin:0 0 8px">' + String(err.message || err) + '</p>' +
                '<p style="color:#7d8590;margin:0">Please refresh the page, or run locally with ' +
                '<code style="color:#e6edf3">pip install -r requirements.txt && python app.py</code></p>' +
                '</div>';
        }
    });
});
