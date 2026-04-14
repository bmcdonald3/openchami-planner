from fastapi.testclient import TestClient
import pytest
from pydantic import ValidationError
import json

import backend.main as bm

client = TestClient(bm.app)

def test_pydantic_validation_rejects_wrong_type():
    bad = {"polling_interval_seconds": "not-an-int"}
    with pytest.raises(ValidationError):
        bm.FabricaConfig.model_validate(bad)

def test_analyze_payload_too_large_returns_413():
    payload = b"x" * (51 * 1024)  # 51KB
    resp = client.post("/analyze", data=payload)
    assert resp.status_code == 413

def test_ttlcache_configuration():
    assert hasattr(bm, "session_cache")
    # TTLCache exposes maxsize and ttl attributes
    assert getattr(bm.session_cache, "maxsize") == 1000
    assert getattr(bm.session_cache, "ttl") == 86400

def test_answer_updates_single_field_and_preserves_others():
    # initialize session
    resp = client.post("/analyze", data=b"short text")
    assert resp.status_code == 200
    body = resp.json()
    sid = body["session_id"]
    # default for polling_interval_seconds should be 60
    assert body["state"]["polling_interval_seconds"] == 60
    # submit answer to update only 'name'
    answer = {"session_id": sid, "key": "name", "value": "MyDevice"}
    resp2 = client.post("/answer", json=answer)
    assert resp2.status_code == 200
    data = resp2.json()
    assert data["state"]["name"] == "MyDevice"
    # ensure other field unchanged
    assert data["state"]["polling_interval_seconds"] == 60