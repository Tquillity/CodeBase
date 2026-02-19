# knowledge_graph.py
# Sprint 3: thread-safe SQLite persistent index for cross-repository memory.
# Stores repos, clusters, copy history; no raw path export; no git shell calls.
from __future__ import annotations

import hashlib
import json
import logging
import os
import sqlite3
import threading
import time
from typing import Any, Dict, List, Optional, Tuple

try:
    import appdirs  # type: ignore[import-untyped]
except ImportError:
    appdirs = None

from constants import KNOWLEDGE_DB_FILENAME, RECOMMENDATION_HISTORY_DAYS

logger = logging.getLogger(__name__)

_lock: threading.Lock = threading.Lock()
_connection: Optional[sqlite3.Connection] = None


def _db_path() -> str:
    if appdirs is not None:
        base = appdirs.user_data_dir("CodeBase", "")
    else:
        base = os.path.join(os.path.expanduser("~"), ".local", "share", "CodeBase")
    os.makedirs(base, exist_ok=True)
    return os.path.join(base, KNOWLEDGE_DB_FILENAME)


def _get_connection() -> sqlite3.Connection:
    global _connection
    with _lock:
        if _connection is None:
            path = _db_path()
            _connection = sqlite3.connect(path, check_same_thread=False)
            _connection.execute("PRAGMA journal_mode=WAL")
            _init_schema(_connection)
        return _connection


def _init_schema(conn: sqlite3.Connection) -> None:
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS repos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            root_path TEXT UNIQUE NOT NULL,
            first_seen_at REAL NOT NULL,
            last_seen_at REAL NOT NULL
        );
        CREATE TABLE IF NOT EXISTS clusters (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            repo_id INTEGER NOT NULL,
            name TEXT NOT NULL,
            module_keys TEXT NOT NULL,
            file_count INTEGER NOT NULL,
            aggregate_impact REAL NOT NULL,
            created_at REAL NOT NULL,
            FOREIGN KEY (repo_id) REFERENCES repos(id)
        );
        CREATE TABLE IF NOT EXISTS file_stats (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            repo_id INTEGER NOT NULL,
            path_hash TEXT NOT NULL,
            relative_path TEXT NOT NULL,
            copy_count INTEGER DEFAULT 0,
            last_copied_at REAL,
            UNIQUE(repo_id, path_hash),
            FOREIGN KEY (repo_id) REFERENCES repos(id)
        );
        CREATE TABLE IF NOT EXISTS copy_events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            repo_id INTEGER NOT NULL,
            path_hashes TEXT NOT NULL,
            copied_at REAL NOT NULL,
            FOREIGN KEY (repo_id) REFERENCES repos(id)
        );
        CREATE INDEX IF NOT EXISTS idx_repos_root ON repos(root_path);
        CREATE INDEX IF NOT EXISTS idx_clusters_repo ON clusters(repo_id);
        CREATE INDEX IF NOT EXISTS idx_file_stats_repo ON file_stats(repo_id);
        CREATE INDEX IF NOT EXISTS idx_copy_events_repo_at ON copy_events(repo_id, copied_at);
    """)
    conn.commit()


def _path_hash(path: str) -> str:
    return hashlib.sha256(path.encode("utf-8", errors="replace")).hexdigest()[:32]


def path_hash(path: str) -> str:
    """Public hash for a path (for callers that need to pass hashes into get_files_often_copied_together)."""
    return _path_hash(path)


def record_repo_seen(repo_root: str) -> int:
    """Ensure repo exists; update last_seen_at. Returns repo id."""
    conn = _get_connection()
    now = time.time()
    with _lock:
        cur = conn.execute(
            "SELECT id FROM repos WHERE root_path = ?", (repo_root,)
        )
        row = cur.fetchone()
        if row:
            conn.execute(
                "UPDATE repos SET last_seen_at = ? WHERE id = ?", (now, row[0])
            )
            conn.commit()
            return int(row[0])
        cur = conn.execute(
            "INSERT INTO repos (root_path, first_seen_at, last_seen_at) VALUES (?, ?, ?)",
            (repo_root, now, now),
        )
        conn.commit()
        return cur.lastrowid or 0


def record_clusters(repo_root: str, clusters: List[Tuple[str, List[str], int, float]]) -> None:
    """Store clusters for this repo (replaces previous clusters for repo)."""
    repo_id = record_repo_seen(repo_root)
    conn = _get_connection()
    with _lock:
        conn.execute("DELETE FROM clusters WHERE repo_id = ?", (repo_id,))
        now = time.time()
        for name, module_keys, file_count, agg_impact in clusters:
            conn.execute(
                "INSERT INTO clusters (repo_id, name, module_keys, file_count, aggregate_impact, created_at) VALUES (?, ?, ?, ?, ?, ?)",
                (repo_id, name, json.dumps(module_keys), file_count, agg_impact, now),
            )
        conn.commit()


def record_copy_event(repo_root: str, absolute_paths: List[str]) -> None:
    """Record a copy event (files copied together). Paths are not exported; stored as hashes + relative for current repo only."""
    if not absolute_paths:
        return
    repo_id = record_repo_seen(repo_root)
    conn = _get_connection()
    now = time.time()
    path_hashes_list: List[str] = []
    with _lock:
        for abs_path in absolute_paths:
            try:
                rel = os.path.relpath(abs_path, repo_root)
            except ValueError:
                continue
            if rel.startswith(".."):
                continue
            h = _path_hash(abs_path)
            path_hashes_list.append(h)
            cur = conn.execute(
                "SELECT id, copy_count FROM file_stats WHERE repo_id = ? AND path_hash = ?",
                (repo_id, h),
            )
            row = cur.fetchone()
            if row:
                conn.execute(
                    "UPDATE file_stats SET copy_count = copy_count + 1, last_copied_at = ?, relative_path = ? WHERE id = ?",
                    (now, rel, row[0]),
                )
            else:
                conn.execute(
                    "INSERT INTO file_stats (repo_id, path_hash, relative_path, copy_count, last_copied_at) VALUES (?, ?, ?, 1, ?)",
                    (repo_id, h, rel, now),
                )
        if path_hashes_list:
            conn.execute(
                "INSERT INTO copy_events (repo_id, path_hashes, copied_at) VALUES (?, ?, ?)",
                (repo_id, json.dumps(path_hashes_list), now),
            )
        conn.commit()


def get_files_often_copied_together(repo_root: str, current_path_hashes: List[str], limit: int = 20) -> List[str]:
    """
    Return relative paths (for current repo) that were often copied together with the given paths.
    current_path_hashes: list of path hashes for files currently selected (optional; if empty, returns top copied files).
    """
    repo_id = record_repo_seen(repo_root)
    conn = _get_connection()
    cutoff = time.time() - (RECOMMENDATION_HISTORY_DAYS * 24 * 3600)
    with _lock:
        cur = conn.execute(
            "SELECT path_hashes FROM copy_events WHERE repo_id = ? AND copied_at >= ? ORDER BY copied_at DESC LIMIT 500",
            (repo_id, cutoff),
        )
        rows = cur.fetchall()
    # Co-occurrence: count how often each path_hash appears with current_path_hashes
    candidate_counts: Dict[str, int] = {}
    current_set = set(current_path_hashes)
    for (path_hashes_json,) in rows:
        try:
            hashes = set(json.loads(path_hashes_json))
        except (json.JSONDecodeError, TypeError):
            continue
        if current_set and not (current_set & hashes):
            continue
        for h in hashes:
            if h not in current_set:
                candidate_counts[h] = candidate_counts.get(h, 0) + 1
    # Resolve hashes to relative_path for this repo
    out: List[str] = []
    with _lock:
        for h, _ in sorted(candidate_counts.items(), key=lambda x: (-x[1], x[0]))[:limit]:
            cur = conn.execute(
                "SELECT relative_path FROM file_stats WHERE repo_id = ? AND path_hash = ?",
                (repo_id, h),
            )
            row = cur.fetchone()
            if row and row[0] not in out:
                out.append(row[0])
    return out


def get_high_impact_cluster_names_from_history(repo_root: str, limit: int = 10) -> List[Tuple[str, float]]:
    """Return (cluster_name, aggregate_impact) for clusters we've seen for this repo, by impact."""
    repo_id = record_repo_seen(repo_root)
    conn = _get_connection()
    with _lock:
        cur = conn.execute(
            "SELECT name, aggregate_impact FROM clusters WHERE repo_id = ? ORDER BY aggregate_impact DESC LIMIT ?",
            (repo_id, limit),
        )
        return [(row[0], row[1]) for row in cur.fetchall()]


def get_similar_clusters_from_other_repos(repo_root: str, cluster_name: str, limit: int = 5) -> List[Tuple[str, str]]:
    """Return (other_repo_root, cluster_name) for clusters with same name from other repos. Does not export raw paths beyond what caller already has."""
    repo_id = record_repo_seen(repo_root)
    conn = _get_connection()
    with _lock:
        cur = conn.execute(
            "SELECT r.root_path, c.name FROM clusters c JOIN repos r ON c.repo_id = r.id WHERE c.repo_id != ? AND c.name = ? ORDER BY c.aggregate_impact DESC LIMIT ?",
            (repo_id, cluster_name, limit),
        )
        return [(row[0], row[1]) for row in cur.fetchall()]
