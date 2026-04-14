"""
Backend scaffold for Phase 1.

Provides a lightweight FastAPI-compatible `app` object. We attempt to import FastAPI so the real dependency can be used
when installed; if it's unavailable (tests running before venv installation) we provide a minimal fallback to allow imports.
This keeps imports safe during initial environment scaffolding and testing.
"""

try:
    from fastapi import FastAPI  # type: ignore
except Exception:
    class FastAPI:  # minimal fallback
        def __init__(self) -> None:
            self._routes = []

        def add_api_route(self, *args, **kwargs):
            self._routes.append((args, kwargs))

app = FastAPI()

# simple health endpoint registration when FastAPI is present
def _register_health():
    try:
        # If real FastAPI, use decorator style to register a simple route
        if hasattr(app, "get"):
            @app.get("/health")
            def health():
                return {"status": "ok"}
        else:
            # fallback: record a health route using add_api_route if available
            if hasattr(app, "add_api_route"):
                app.add_api_route("/health", lambda: {"status": "ok"})
    except Exception:
        # intentionally catch specific exceptions if route registration fails at import time
        pass

_register_health()