"""
LLM orchestration helper.

Provides `call_llm(prompt, schema_state, timeout=45, retries=3)` which returns a dict:
{
  "schema": { ... populated schema ... },
  "missing": ["field_name"],
  "question": "A specific question for that field"
}

This module prefers calling the OpenAI client if API key is present, but falls back to a deterministic heuristic
to produce a valid structure so the application remains testable without network access. Tests should monkeypatch
`call_llm` to simulate LLM behavior where needed.
"""
from typing import Dict, Any, List
import os
import time

try:
    import openai
    # configure OpenRouter client if an API key is present
    OR_KEY = os.getenv("OPENROUTER_API_KEY")
    if OR_KEY:
        # OpenRouter exposes an OpenAI-compatible API surface; set base and key
        openai.api_base = "https://openrouter.ai/api/v1"
        openai.api_key = OR_KEY
except Exception:
    openai = None  # optional; tests should mock this behavior

def _heuristic_fill(prompt: str, schema_state: Dict[str, Any]) -> Dict[str, Any]:
    # produce a populated schema (no type coercion) by returning the provided state
    # and selecting the first missing field to ask a simple question.
    missing = []
    for k, v in schema_state.items():
        if v is None or v == "" or (isinstance(v, list) and len(v) == 0):
            missing.append(k)
    # if no missing, return as-is
    question = f"Please provide value for {missing[0]}" if missing else ""
    return {"schema": schema_state, "missing": missing[:1], "question": question}

def call_llm(prompt: str, schema_state: Dict[str, Any], timeout: int = 45, retries: int = 3) -> Dict[str, Any]:
    """
    Call the LLM to populate schema and return exactly 1 missing field plus a question.

    This function will attempt up to `retries` times, enforcing a per-call timeout (seconds).
    If OpenAI is not available or an error occurs, falls back to a deterministic heuristic.
    """
    last_exc = None
    for attempt in range(1, retries + 1):
        try:
            if openai and os.getenv("OPENROUTER_API_KEY"):
                # NOTE: this code path is intentionally minimal. Tests should mock call_llm; real deployments
                # must replace this with a robust Structured Outputs integration that enforces schemas.
                resp = openai.ChatCompletion.create(
                    model="openai/gpt-4o-2024-08-06",
                    messages=[{"role": "user", "content": prompt}],
                    timeout=timeout
                )
                # Minimal parsing: expect assistant content in JSON form
                content = resp.choices[0].message["content"]
                # attempt to parse JSON from the assistant; if it fails, fall back
                import json
                parsed = json.loads(content)
                return {
                    "schema": parsed.get("schema", schema_state),
                    "missing": parsed.get("missing", [])[:1],
                    "question": parsed.get("question", "")
                }
            else:
                return _heuristic_fill(prompt, schema_state)
        except Exception as e:
            last_exc = e
            # simple backoff
            time.sleep(0.5 * attempt)
            continue
    # if all retries fail, raise the last exception or return heuristic
    if last_exc:
        return _heuristic_fill(prompt, schema_state)
    return _heuristic_fill(prompt, schema_state)