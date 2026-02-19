# module_analyzer.py
# Multi-language dependency graph: regex-based imports, folder-as-module heuristic.
# Sprint 2: hierarchical clustering via shortest-path distance matrix.
from __future__ import annotations

import logging
import os
import re
from typing import Any, Dict, List, Optional, Set, Tuple

try:
    import networkx as nx  # type: ignore[import-untyped]
except ImportError:
    nx = None

try:
    from scipy.cluster import hierarchy as scipy_hierarchy  # type: ignore[import-untyped]
    _HAS_SCIPY = True
except ImportError:
    scipy_hierarchy = None
    _HAS_SCIPY = False

logger = logging.getLogger(__name__)

# Read only first 50 KB per file for speed
MAX_READ_BYTES = 50 * 1024

# Maximum nodes beyond which we skip graph layout (use text fallback in UI)
MAX_GRAPH_NODES = 100

# Default max distance for disconnected components (overridden by constants.CLUSTER_DISCONNECTED_DISTANCE when used)
_DEFAULT_DISCONNECTED_DISTANCE = 1000.0

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


def _condensed_distance_from_graph(
    G: Any,
    nodes: List[str],
    disconnected_distance: float,
) -> List[float]:
    """
    Build condensed distance matrix (n*(n-1)/2) for linkage.
    Distance = shortest path length on undirected graph; disconnected = disconnected_distance.
    """
    n = len(nodes)
    if n <= 1:
        return []
    try:
        Gu = G.to_undirected()
    except Exception:
        Gu = G
    node_to_idx = {nd: i for i, nd in enumerate(nodes)}
    condensed: List[float] = [0.0] * (n * (n - 1) // 2)
    for i in range(n):
        for j in range(i + 1, n):
            u, v = nodes[i], nodes[j]
            try:
                length = nx.shortest_path_length(Gu, u, v)
            except (nx.NetworkXNoPath, nx.NodeNotFound, Exception):
                length = disconnected_distance
            k = (i * (2 * n - i - 1)) // 2 + (j - i - 1)
            condensed[k] = float(length)
    return condensed


def _hierarchical_clusters(
    G: Any,
    centrality: Dict[str, float],
    module_to_files: Dict[str, List[Tuple[str, str]]],
    disconnected_distance: float,
    max_cluster_size: int,
    impact_threshold: float,
) -> Tuple[List[Tuple[str, List[str], int, float]], Any]:
    """
    Compute hierarchical clusters from dependency graph.
    Returns (list of (cluster_display_name, module_keys, file_count, aggregate_impact), linkage_matrix Z).
    Z is None if clustering failed or scipy unavailable.
    """
    if not _HAS_SCIPY or scipy_hierarchy is None or nx is None or G is None:
        return [], None
    n = G.number_of_nodes()
    if n <= 1:
        return [], None
    nodes = list(G.nodes())
    condensed = _condensed_distance_from_graph(G, nodes, disconnected_distance)
    if len(condensed) == 0:
        return [], None
    try:
        Z = scipy_hierarchy.linkage(condensed, method="average")
    except Exception as e:
        logger.debug("linkage failed: %s", e)
        return [], None
    # Request a reasonable number of clusters so no cluster exceeds max_cluster_size
    n_clusters = max(2, min(25, (n + max_cluster_size - 1) // max(1, max_cluster_size)))
    try:
        labels = scipy_hierarchy.fcluster(Z, n_clusters, criterion="maxclust")
    except Exception as e:
        logger.debug("fcluster failed: %s", e)
        return [], None
    # Group module names by cluster id
    cluster_id_to_modules: Dict[int, List[str]] = {}
    for idx, label in enumerate(labels):
        if idx >= len(nodes):
            continue
        mod = nodes[idx]
        cid = int(label)
        cluster_id_to_modules.setdefault(cid, []).append(mod)
    result: List[Tuple[str, List[str], int, float]] = []
    for cid in sorted(cluster_id_to_modules.keys()):
        mods = cluster_id_to_modules[cid]
        file_count = sum(len(module_to_files.get(m, [])) for m in mods)
        aggregate_impact = sum(centrality.get(m, 0.0) for m in mods)
        if aggregate_impact < impact_threshold:
            continue
        name = f"Cluster {cid}"
        result.append((name, mods, file_count, aggregate_impact))
    result.sort(key=lambda x: (-x[3], -x[2], x[0]))
    return result, Z


def compute_optimal_prompt_paths(
    module_to_abs_paths: Dict[str, List[str]],
    centrality: Dict[str, float],
    max_bytes: int,
    impact_threshold: float = 0.0,
) -> List[str]:
    """
    Knapsack-style: select highest-impact modules first, add all their files until max_bytes.
    Returns list of absolute paths. Does not read file contents; uses file size as proxy for content length.
    """
    try:
        from constants import INTELLIGENT_PROMPT_THRESHOLD
    except ImportError:
        INTELLIGENT_PROMPT_THRESHOLD = 0.01
    thresh = impact_threshold if impact_threshold > 0 else INTELLIGENT_PROMPT_THRESHOLD
    # (module_display, total_size, paths)
    module_sizes: List[Tuple[str, int, List[str]]] = []
    for mod, paths in module_to_abs_paths.items():
        impact = centrality.get(mod, 0.0)
        if impact < thresh:
            continue
        total = 0
        for p in paths:
            try:
                total += os.path.getsize(p)
            except OSError:
                pass
        if paths:
            module_sizes.append((mod, total, paths))
    module_sizes.sort(key=lambda x: (-centrality.get(x[0], 0.0), -x[1], x[0]))
    out: List[str] = []
    used = 0
    for _mod, size, paths in module_sizes:
        if used + size > max_bytes:
            break
        used += size
        out.extend(paths)
    return out


def get_recommendations(
    repo_root: str,
    current_paths: Optional[List[str]] = None,
    max_often_copied: int = 10,
    max_high_impact: int = 5,
    max_similar: int = 5,
) -> List[Dict[str, Any]]:
    """
    Smart local recommendations using knowledge graph (no external AI).
    Returns list of dicts: {"type": str, "title": str, "paths": List[str]} or {"type", "title", "description"}.
    paths are absolute for current repo.
    """
    try:
        import knowledge_graph as kg
    except ImportError:
        return []
    recs: List[Dict[str, Any]] = []
    current_hashes = []
    if current_paths:
        for p in current_paths:
            current_hashes.append(kg.path_hash(p))
    often = kg.get_files_often_copied_together(repo_root, current_hashes, limit=max_often_copied)
    if often:
        paths_abs = [os.path.join(repo_root, rel) for rel in often if not rel.startswith("..")]
        paths_abs = [p for p in paths_abs if os.path.isfile(p)]
        if paths_abs:
            recs.append({
                "type": "often_copied",
                "title": "Files often copied together",
                "paths": paths_abs,
            })
    high_impact = kg.get_high_impact_cluster_names_from_history(repo_root, limit=max_high_impact)
    if high_impact:
        recs.append({
            "type": "high_impact_clusters",
            "title": "High-impact clusters (from history)",
            "description": ", ".join(f"{n} ({i:.2f})" for n, i in high_impact[:5]),
        })
    if current_paths:
        # "Similar clusters from other repos" — use first path to guess a cluster name or use "current selection"
        similar = kg.get_similar_clusters_from_other_repos(repo_root, "Cluster 1", limit=max_similar)
        if similar:
            recs.append({
                "type": "similar_clusters",
                "title": "Similar clusters in other repos",
                "description": f"{len(similar)} repo(s) have matching cluster pattern.",
            })
    return recs


def modules_with_impact(
    repo_root: str,
    enabled_extensions: Optional[Set[str]] = None,
) -> Tuple[
    List[Tuple[str, int, float]],
    Any,
    Dict[str, str],
    Dict[str, List[str]],
    List[Tuple[str, List[str], int, float]],
    Any,
]:
    """
    Multi-language: discover modules (folders) from enabled extensions, build graph, impact = in_degree_centrality.
    Sprint 2: also computes hierarchical clusters from shortest-path distance (undirected).
    Returns:
      - list of (module_display_name, file_count, impact_score) sorted by impact desc
      - networkx DiGraph (or None)
      - rel_path -> abs_path for all scanned files
      - module_display_name -> list of absolute paths (for selection bridge)
      - list of (cluster_name, module_keys, file_count, aggregate_impact) for clusters
      - linkage matrix Z (for dendrogram) or None
    """
    try:
        from constants import (
            CLUSTER_DISCONNECTED_DISTANCE,
            CLUSTER_IMPACT_THRESHOLD,
            MAX_CLUSTER_SIZE,
        )
    except ImportError:
        CLUSTER_DISCONNECTED_DISTANCE = _DEFAULT_DISCONNECTED_DISTANCE
        CLUSTER_IMPACT_THRESHOLD = 0.0
        MAX_CLUSTER_SIZE = 50

    if enabled_extensions is None:
        enabled_extensions = set(IMPORT_PATTERNS.keys())
    module_to_files, all_files = discover_modules(repo_root, enabled_extensions)
    if not module_to_files:
        return [], None, {}, {}, [], None
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

    clusters: List[Tuple[str, List[str], int, float]] = []
    linkage_Z: Any = None
    if G is not None and centrality:
        clusters, linkage_Z = _hierarchical_clusters(
            G,
            centrality,
            module_to_files,
            disconnected_distance=CLUSTER_DISCONNECTED_DISTANCE,
            max_cluster_size=MAX_CLUSTER_SIZE,
            impact_threshold=CLUSTER_IMPACT_THRESHOLD,
        )
    return result, G, all_files, module_to_abs_paths, clusters, linkage_Z
