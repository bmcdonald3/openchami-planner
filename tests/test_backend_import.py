import importlib

def test_backend_main_imports_and_has_app():
    mod = importlib.import_module("backend.main")
    assert hasattr(mod, "app"), "backend.main must expose 'app'"