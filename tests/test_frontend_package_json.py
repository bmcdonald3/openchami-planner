import json
from pathlib import Path

def test_frontend_package_json_exists_and_has_dependencies():
    p = Path("frontend/package.json")
    assert p.exists(), "frontend/package.json should exist"
    data = json.loads(p.read_text(encoding="utf-8"))
    assert "dependencies" in data, "package.json must have dependencies"
    deps = data["dependencies"]
    assert "axios" in deps, "axios must be listed as a dependency"