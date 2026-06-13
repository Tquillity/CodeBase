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


def test_rust_use_import_extraction():
    with tempfile.NamedTemporaryFile(suffix=".rs", mode="w", delete=False) as f:
        f.write("use std::collections::HashMap;\nuse crate::utils::helper;\n")
        path = f.name
    try:
        refs = _get_imports_from_source(path)
        assert "std::collections::HashMap" in refs
        assert "crate::utils::helper" in refs
        assert _normalize_module_ref(refs[0], "src") == "std"
    finally:
        os.unlink(path)


def test_typescript_import_extraction():
    with tempfile.NamedTemporaryFile(suffix=".ts", mode="w", delete=False) as f:
        f.write("import { foo } from './utils/helper';\nrequire('lodash');\n")
        path = f.name
    try:
        refs = _get_imports_from_source(path)
        assert "./utils/helper" in refs
        assert "lodash" in refs
    finally:
        os.unlink(path)
