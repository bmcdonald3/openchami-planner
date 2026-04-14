"""
Phase 1 -> Phase 3 backend implementation.

Provides:
- Pydantic model `FabricaConfig` with 15 fields.
- An in-memory session store using cachetools.TTLCache (maxsize=1000, ttl=86400).
- /analyze POST endpoint that accepts raw text up to 50KB and initializes a session and queries the LLM for next question.
- /answer POST endpoint that accepts JSON {session_id, key, value}, updates the stored model state,
  validates it with Pydantic, calls the LLM for the next missing field, and returns progress.
- /export GET endpoint that returns a .zip containing apis.yaml when the session is complete.
"""

from typing import List, Dict, Optional, Any
from uuid import uuid4
from fastapi import FastAPI, Request, HTTPException, Query
from fastapi.responses import JSONResponse, Response
from pydantic import BaseModel, Field, ValidationError, EmailStr
from cachetools import TTLCache
from io import BytesIO
import zipfile
import json

# LLM helper
from backend.llm import call_llm

app = FastAPI()

# --- Pydantic model with 15 fields ---
class FabricaConfig(BaseModel):
    redfish_endpoints: List[str] = Field(default_factory=list)
    polling_interval_seconds: int = 60
    http_success_codes: List[int] = Field(default_factory=lambda: [200])
    name: str = ""
    description: Optional[str] = None
    contact_email: Optional[EmailStr] = None
    retries: int = 3
    timeout_seconds: int = 30
    base_path: Optional[str] = None
    token: Optional[str] = None
    use_tls: bool = True
    cert_path: Optional[str] = None
    proxy: Optional[str] = None
    vendor: Optional[str] = None
    version: Optional[str] = None

# --- Session store ---
session_cache: TTLCache = TTLCache(maxsize=1000, ttl=86400)

# health endpoint
@app.get("/health")
def health():
    return {"status": "ok"}

# helper to find missing fields (fields considered missing if None, empty string, or empty list)
def _missing_fields(state: Dict[str, Any]) -> List[str]:
    missing = []
    for name in FabricaConfig.model_fields:
        val = state.get(name)
        if val is None:
            missing.append(name)
            continue
        if isinstance(val, list) and len(val) == 0:
            missing.append(name)
            continue
        if isinstance(val, str) and val == "":
            missing.append(name)
            continue
    return missing

@app.post("/analyze")
async def analyze(request: Request):
    # read raw body bytes and enforce <= 50KB
    body = await request.body()
    if len(body) > 50 * 1024:
        return JSONResponse(status_code=413, content={"detail": "Payload too large"})
    text = body.decode("utf-8", errors="ignore")
    # create initial empty config
    cfg = FabricaConfig()  # defaults
    session_id = str(uuid4())
    session_cache[session_id] = cfg.model_dump()
    # call LLM to get next missing and question
    llm_result = call_llm(prompt=text, schema_state=session_cache[session_id], timeout=45, retries=3)
    missing = llm_result.get("missing", [])
    question = llm_result.get("question", None)
    return {"session_id": session_id, "missing_fields": missing, "next_question": question, "state": session_cache[session_id]}

class AnswerPayload(BaseModel):
    session_id: str
    key: str
    value: Any

@app.post("/answer")
async def answer(payload: AnswerPayload):
    if payload.session_id not in session_cache:
        raise HTTPException(status_code=404, detail="session not found")
    state = dict(session_cache[payload.session_id])  # copy
    # update the key
    if payload.key not in FabricaConfig.model_fields:
        raise HTTPException(status_code=400, detail="unknown field")
    state[payload.key] = payload.value
    # validate via Pydantic; will raise ValidationError if types invalid
    try:
        FabricaConfig.model_validate(state)
    except ValidationError as e:
        raise HTTPException(status_code=422, detail=e.errors())
    # store back
    session_cache[payload.session_id] = state
    # call LLM for next question
    prompt = json.dumps({"action": "answer_update"})
    llm_result = call_llm(prompt=prompt, schema_state=state, timeout=45, retries=3)
    missing = llm_result.get("missing", [])
    question = llm_result.get("question", None)
    completion = 100 if not missing else int((1 - len(missing) / len(FabricaConfig.model_fields)) * 100)
    return {"status": "ok", "next_missing": missing[0] if missing else None, "missing_fields": missing, "completion": completion, "next_question": question, "state": state}

@app.get("/export")
def export(session_id: str = Query(...)):
    if session_id not in session_cache:
        raise HTTPException(status_code=404, detail="session not found")
    state = dict(session_cache[session_id])
    missing = _missing_fields(state)
    if missing:
        raise HTTPException(status_code=400, detail=f"session incomplete, missing: {missing}")
    # render a simple YAML representation
    lines = []
    for k in FabricaConfig.model_fields:
        v = state.get(k)
        if isinstance(v, list):
            if len(v) == 0:
                lines.append(f"{k}: []")
            else:
                lines.append(f"{k}:")
                for item in v:
                    lines.append(f"  - {item}")
        elif isinstance(v, bool):
            lines.append(f"{k}: {'true' if v else 'false'}")
        elif v is None:
            lines.append(f"{k}: null")
        else:
            # escape double quotes
            s = str(v).replace('\"', '\\"')
            lines.append(f'{k}: "{s}"')
    yaml_bytes = ("\n".join(lines) + "\n").encode("utf-8")
    # create zip in memory
    buf = BytesIO()
    with zipfile.ZipFile(buf, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("apis.yaml", yaml_bytes)
    buf.seek(0)
    return Response(content=buf.read(), media_type="application/zip", headers={
        "Content-Disposition": f'attachment; filename="apis_{session_id}.zip"'
    })