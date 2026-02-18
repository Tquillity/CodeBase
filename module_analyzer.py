# module_analyzer.py
# Multi-language dependency graph: regex-based imports, folder-as-module heuristic.
from __future__ import annotations

import logging
import os
import re
from typing import Any, Dict, List, Optional, Set, Tuple

try:
    import networkx as nx  # type: ignore[import-untyped]
except ImportError:
    nx = None

logger = logging.getLogger(__name__)

# Read only first 50 KB per file for speed
MAX_READ_BYTES = 50 * 1024

# Maximum nodes beyond which we skip graph layout (use text fallback in UI)
MAX_GRAPH_NODES = 100

# Skip these directories when walking (non-source)
SKIP_DIRS = frozenset({
    "__pycache__", ".git", "venv", ".venv", "env", "node_modules",
    "dist", "build", "target", ".next", ".nuxt", "vendor",
})

# Extension -> regex to capture import path/module (first group).
# Patterns capture the first meaningful path or name.
IMPORT_PATTERNS: Dict[str, str] = {
    # Python: import foo; from foo.bar import z (tighter: module name = word chars + dots only)
    ".py": r"(?:^|\n)\s*(?:import\s+([a-zA-Z0-9_.]+)|from\s+([a-zA-Z0-9_.]+)\s+import)",
    # JavaScript/TypeScript: import x from 'path'; require('path'); import('path')
    ".js": r"(?:import\s+.*?\s+from\s+['\"]([^'\"]+)['\"]|import\s+['\"]([^'\"]+)['\"]|require\s*\(\s*['\"]([^'\"]+)['\"]\s*\)|import\s*\(\s*['\"]([^'\"]+)['\"]\s*\))",
    ".jsx": r"(?:import\s+.*?\s+from\s+['\"]([^'\"]+)['\"]|import\s+['\"]([^'\"]+)['\"]|require\s*\(\s*['\"]([^'\"]+)['\"]\s*\)|import\s*\(\s*['\"]([^'\"]+)['\"]\s*\))",
    ".ts": r"(?:import\s+.*?\s+from\s+['\"]([^'\"]+)['\"]|import\s+['\"]([^'\"]+)['\"]|require\s*\(\s*['\"]([^'\"]+)['\"]\s*\)|import\s*\(\s*['\"]([^'\"]+)['\"]\s*\))",
    ".tsx": r"(?:import\s+.*?\s+from\s+['\"]([^'\"]+)['\"]|import\s+['\"]([^'\"]+)['\"]|require\s*\(\s*['\"]([^'\"]+)['\"]\s*\)|import\s*\(\s*['\"]([^'\"]+)['\"]\s*\))",
    ".mjs": r"(?:import\s+.*?\s+from\s+['\"]([^'\"]+)['\"]|import\s+['\"]([^'\"]+)['\"]|require\s*\(\s*['\"]([^'\"]+)['\"]\s*\)|import\s*\(\s*['\"]([^'\"]+)['\"]\s*\))",
    ".cjs": r"(?:import\s+.*?\s+from\s+['\"]([^'\"]+)['\"]|import\s+['\"]([^'\"]+)['\"]|require\s*\(\s*['\"]([^'\"]+)['\"]\s*\)|import\s*\(\s*['\"]([^'\"]+)['\"]\s*\))",
    # Rust: use foo::bar; use crate::baz;
    ".rs": r"(?:^|\n)\s*use\s+([a-zA-Z0-9_::]+)",
    # Java/Kotlin: import pkg.Class;
    ".java": r"(?:^|\n)\s*import\s+([a-zA-Z0-9_.]+)\s*;",
    ".kt": r"(?:^|\n)\s*import\s+([a-zA-Z0-9_.]+)\s*;",
    ".kts": r"(?:^|\n)\s*import\s+([a-zA-Z0-9_.]+)\s*;",
    # C/C++: #include "local" or #include <system>
    ".c": r'#include\s*["<]([^">]+)[">]',
    ".h": r'#include\s*["<]([^">]+)[">]',
    ".cpp": r'#include\s*["<]([^">]+)[">]',
    ".cc": r'#include\s*["<]([^">]+)[">]',
    ".cxx": r'#include\s*["<]([^">]+)[">]',
    ".hpp": r'#include\s*["<]([^">]+)[">]',
    # Go: import "pkg" or import ( "pkg" )
    ".go": r'import\s+(?:"([^"]+)"|\(\s*"([^"]+)"[^)]*\))',
    # C#: using Foo.Bar;
    ".cs": r"(?:^|\n)\s*using\s+([a-zA-Z0-9_.]+)\s*;",
    # Ruby: require 'x'; require_relative 'x'
    ".rb": r"(?:require|require_relative)\s+['\"]([^'\"]+)['\"]",
    # PHP: use Foo\Bar; require 'x';
    ".php": r"(?:^|\n)\s*(?:use\s+([a-zA-Z0-9_\\]+)\s*;|require(?:_once)?\s+['\"]([^'\"]+)['\"])",
    # Swift: import Module
    ".swift": r"(?:^|\n)\s*import\s+([a-zA-Z0-9_.]+)",
    # Dart: import 'package:...' or import 'path';
    ".dart": r"import\s+['\"]([^'\"]+)['\"]",
    # Scala: import pkg.Class
    ".scala": r"(?:^|\n)\s*import\s+([a-zA-Z0-9_.]+)",
    # Vue SFC: same as JS/TS in script
    ".vue": r"(?:import\s+.*?\s+from\s+['\"]([^'\"]+)['\"]|import\s+['\"]([^'\"]+)['\"]|require\s*\(\s*['\"]([^'\"]+)['\"]\s*\))",
}


def _get_imports_from_source(file_path: str) -> List[str]:
    """
    Read first MAX_READ_BYTES of file, apply regex for file extension, return clean module refs.
    """
    ext = os.path.splitext(file_path)[1].lower()
    pattern = IMPORT_PATTERNS.get(ext)
    if not pattern:
        return []
    try:
        with open(file_path, "r", encoding="utf-8", errors="replace") as f:
            source = f.read(MAX_READ_BYTES)
    except OSError:
        return []
    if not source:
        return []
    refs: List[str] = []
    try:
        for m in re.finditer(pattern, source, re.MULTILINE | re.DOTALL):
            for g in m.groups():
                if g is not None and isinstance(g, str):
                    g = g.strip()
                    if g:
                        refs.append(g)
                    break
    except re.error:
        logger.debug("Regex error for %s pattern", ext)
    return refs


def _normalize_module_ref(ref: str, current_dir: str) -> Optional[str]:
    """
    Normalize import ref to a path-like key we can match to module (folder) names.
    - Relative JS/TS: '../utils' -> parent/../utils -> utils dir or path
    - Alias @/utils -> utils (strip common aliases)
    - Python: foo.bar -> foo
    - External (react, etc.): return None to skip
    """
    ref = ref.strip()
    if not ref:
        return None
    # Skip obvious externals (no path sep, no dot for packages)
    if ref.startswith("."):
        # Relative: . or .. or ./
        parts = ref.replace("/", os.sep).split(os.sep)
        out: List[str] = []
        base = (current_dir or "").split(os.sep) if current_dir else []
        for p in parts:
            if p == "..":
                if base:
                    base.pop()
            elif p and p != ".":
                base.append(p)
        return os.sep.join(base) if base else None
    if "/" in ref or "\\" in ref:
        # Path-like: @/ ~/ #/ -> strip common JS/TS/Vite aliases
        ref = re.sub(r"^[@~#]/?", "", ref)
        ref = ref.replace("\\", os.sep)
        return ref.strip("/") or None
    # Dotted (Python, Java): take first component for folder match
    if "." in ref:
        first = ref.split(".")[0]
        if first and first != "node_modules":
            return first
    # Single name: could be local module folder
    if ref and ref != "node_modules":
        return ref
    return None


def discover_modules(
    repo_root: str,
    enabled_extensions: Set[str],
) -> Tuple[Dict[str, List[Tuple[str, str]]], Dict[str, str]]:
    """
    Walk repo, collect files with enabled extensions, group by containing folder (module).
    Returns (module_name -> [(rel_path, abs_path), ...], rel_path -> abs_path).
    """
    module_to_files: Dict[str, List[Tuple[str, str]]] = {}
    all_files: Dict[str, str] = {}
    # Only consider extensions we have import patterns for (or all enabled if no pattern = still show as module)
    exts = frozenset(e.lower() for e in enabled_extensions if e.startswith("."))
    if not exts:
        return module_to_files, all_files
    try:
        for root, dirs, files in os.walk(repo_root):
            dirs[:] = [d for d in dirs if d not in SKIP_DIRS and not d.startswith(".")]
            try:
                rel_root = os.path.relpath(root, repo_root)
            except ValueError:
                continue
            if rel_root == ".":
                rel_root = ""
            for f in files:
                ext = os.path.splitext(f)[1].lower()
                if ext not in exts:
                    continue
                rel_path = os.path.join(rel_root, f) if rel_root else f
                abs_path = os.path.join(root, f)
                all_files[rel_path] = abs_path
                # Module = containing folder (relative path of dir)
                mod_name = rel_root if rel_root else "."
                if mod_name not in module_to_files:
                    module_to_files[mod_name] = []
                module_to_files[mod_name].append((rel_path, abs_path))
    except OSError as e:
        logger.warning("Error walking repo %s: %s", repo_root, e)
    return module_to_files, all_files


def _resolve_ref_to_module(
    ref_key: Optional[str],
    current_file_rel: str,
    module_names: Set[str],
) -> Optional[str]:
    """Resolve normalized ref to a module (folder) name in module_names."""
    if not ref_key:
        return None
    current_dir = os.path.dirname(current_file_rel)
    # Direct match: ref_key is a module name
    if ref_key in module_names:
        return ref_key
    # ref_key might be path to file; find module = dir of that path
    # e.g. ref_key = "components/Button" -> module "components"
    for mod in module_names:
        if ref_key == mod or ref_key.startswith(mod + os.sep):
            return mod
    # Try parent of current_dir + ref_key (relative)
    cand = os.path.normpath(os.path.join(current_dir, ref_key))
    if cand in module_names:
        return cand
    # First segment as module (e.g. utils from utils/helper)
    first = ref_key.split(os.sep)[0] if os.sep in ref_key else ref_key
    for mod in module_names:
        if mod == first or mod.endswith(os.sep + first):
            return mod
    return None


def build_dependency_graph(
    repo_root: str,
    module_to_files: Dict[str, List[Tuple[str, str]]],
    all_files: Dict[str, str],
) -> Tuple[Any, Dict[str, float]]:
    """
    Build networkx DiGraph: nodes = module names, edge A->B if any file in A imports from B.
    Impact = in_degree_centrality (how many modules depend on this one).
    """
    if nx is None:
        return None, {}
    G: Any = nx.DiGraph()
    module_names = set(module_to_files.keys())
    for mod in module_names:
        G.add_node(mod)
    for mod_name, file_list in module_to_files.items():
        for rel_path, abs_path in file_list:
            imports = _get_imports_from_source(abs_path)
            for ref in imports:
                ref_key = _normalize_module_ref(ref, os.path.dirname(rel_path))
                target = _resolve_ref_to_module(ref_key, rel_path, module_names)
                if target and target != mod_name:
                    G.add_edge(mod_name, target)
    if G.number_of_nodes() == 0:
        return G, {}
    try:
        centrality = nx.in_degree_centrality(G)
    except Exception:
        centrality = {n: 0.0 for n in G.nodes()}
    return G, centrality


def modules_with_impact(
    repo_root: str,
    enabled_extensions: Optional[Set[str]] = None,
) -> Tuple[List[Tuple[str, int, float]], Any, Dict[str, str], Dict[str, List[str]]]:
    """
    Multi-language: discover modules (folders) from enabled extensions, build graph, impact = in_degree_centrality.
    Returns:
      - list of (module_display_name, file_count, impact_score) sorted by impact desc
      - networkx DiGraph (or None)
      - rel_path -> abs_path for all scanned files
      - module_display_name -> list of absolute paths (for selection bridge)
    """
    if enabled_extensions is None:
        enabled_extensions = set(IMPORT_PATTERNS.keys())
    module_to_files, all_files = discover_modules(repo_root, enabled_extensions)
    if not module_to_files:
        return [], None, {}, {}
    G, centrality = build_dependency_graph(repo_root, module_to_files, all_files)
    result: List[Tuple[str, int, float]] = []
    module_to_abs_paths: Dict[str, List[str]] = {}
    for mod_name, files in module_to_files.items():
        count = len(files)
        impact = centrality.get(mod_name, 0.0) if centrality else 0.0
        display = mod_name if mod_name != "." else "(root)"
        result.append((display, count, impact))
        module_to_abs_paths[mod_name] = [abs_path for _, abs_path in files]
    result.sort(key=lambda x: (-x[2], -x[1], x[0]))
    return result, G, all_files, module_to_abs_paths
