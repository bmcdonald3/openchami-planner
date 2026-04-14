import zipfile
import io
from fastapi.testclient import TestClient
import backend.main as bm
from backend.main import FabricaConfig
import pytest
from pathlib import Path

client = TestClient(bm.app)

def test_export_incomplete_returns_400():
    resp = client.post("/analyze", data=b"short text")
    assert resp.status_code == 200
    sid = resp.json()["session_id"]
    # immediately try export (session incomplete)
    resp2 = client.get("/export", params={"session_id": sid})
    assert resp2.status_code == 400

def test_export_complete_session_returns_zip_with_apis_yaml():
    # start session
    resp = client.post("/analyze", data=b"start")
    assert resp.status_code == 200
    sid = resp.json()["session_id"]
    # prepare values for each field
    vals = {}
    for name, field in FabricaConfig.model_fields.items():
        t = field.annotation
        # handle list types with correct inner element types
        is_list = t is list or getattr(t, "__origin__", None) is list or str(t).startswith("typing.List")
        if is_list:
            args = getattr(t, "__args__", None) or ()
            inner = args[0] if len(args) >= 1 else None
            if inner is int:
                vals[name] = [200]
            else:
                vals[name] = ["item"]
        elif t is int:
            vals[name] = 1
        elif t is bool:
            vals[name] = True
        else:
            # strings and optionals
            if name == "contact_email":
                vals[name] = "a@b.com"
            else:
                vals[name] = f"v_{name}"
    # submit answers for all fields
    for k, v in vals.items():
        res = client.post("/answer", json={"session_id": sid, "key": k, "value": v})
        assert res.status_code == 200
    # now export should succeed
    resp2 = client.get("/export", params={"session_id": sid})
    assert resp2.status_code == 200
    # read zip
    z = zipfile.ZipFile(io.BytesIO(resp2.content))
    assert "apis.yaml" in z.namelist()
    content = z.read("apis.yaml").decode("utf-8")
    for key in FabricaConfig.model_fields:
        assert key in content

def test_frontend_app_exists():
    p = Path("frontend/src/App.jsx")
    assert p.exists(), "frontend/src/App.jsx should exist"