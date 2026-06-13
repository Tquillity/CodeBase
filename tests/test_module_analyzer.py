# tests/test_module_analyzer.py
from module_analyzer import _normalize_module_ref, _get_imports_from_source
import os
import tempfile


def test_normalize_rust_module_ref():
    assert _normalize_module_ref("foo::bar::baz", "src") == "foo"


def test_normalize_python_dotted_ref():
    assert _normalize_module_ref("pkg.mod", "src") == "pkg"


def test_python_multi_import():
    with tempfile.NamedTemporaryFile(suffix=".py", mode="w", delete=False) as f:
        f.write("import os, sys, json\nfrom pathlib import Path\n")
        path = f.name
    try:
        refs = _get_imports_from_source(path)
        assert "os" in refs
        assert "sys" in refs
        assert "json" in refs
        assert "pathlib" in refs
    finally:
        os.unlink(path)
