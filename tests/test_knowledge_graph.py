# tests/test_knowledge_graph.py
import os
import sys
import tempfile
import time
from unittest.mock import patch

import pytest

import knowledge_graph as kg


def test_read_only_query_does_not_update_last_seen():
    with tempfile.TemporaryDirectory() as tmp:
        db_path = os.path.join(tmp, "test_knowledge.db")
        with patch.object(kg, "_db_path", return_value=db_path):
            kg.close_connection()
            repo = os.path.join(tmp, "repo")
            os.makedirs(repo)
            first_id = kg.record_repo_seen(repo)
            conn = kg._get_connection()
            row = conn.execute(
                "SELECT last_seen_at FROM repos WHERE id = ?", (first_id,)
            ).fetchone()
            assert row is not None
            original_seen = row[0]
            time.sleep(0.01)
            kg.get_high_impact_cluster_names_from_history(repo)
            row2 = conn.execute(
                "SELECT last_seen_at FROM repos WHERE id = ?", (first_id,)
            ).fetchone()
            assert row2 is not None
            assert row2[0] == original_seen
            kg.close_connection()


def test_record_repo_seen_updates_last_seen():
    with tempfile.TemporaryDirectory() as tmp:
        db_path = os.path.join(tmp, "test_seen.db")
        with patch.object(kg, "_db_path", return_value=db_path):
            kg.close_connection()
            repo = os.path.join(tmp, "repo")
            os.makedirs(repo)
            first_id = kg.record_repo_seen(repo)
            conn = kg._get_connection()
            row = conn.execute(
                "SELECT last_seen_at FROM repos WHERE id = ?", (first_id,)
            ).fetchone()
            assert row is not None
            original_seen = row[0]
            time.sleep(0.01)
            kg.record_repo_seen(repo)
            row2 = conn.execute(
                "SELECT last_seen_at FROM repos WHERE id = ?", (first_id,)
            ).fetchone()
            assert row2 is not None
            assert row2[0] > original_seen
            kg.close_connection()


def test_path_hash_case_insensitive_on_windows():
    if sys.platform != "win32":
        pytest.skip("Case-folding hash stability is only meaningful on Windows")
    assert kg.path_hash(r"C:\Repo\Foo.py") == kg.path_hash(r"C:\Repo\foo.py")


def test_path_hash_uses_normalize_for_cache():
    path_a = os.path.join("repo", "src", "module.py")
    path_b = path_a.replace("/", os.sep)
    assert kg.path_hash(path_a) == kg.path_hash(path_b)


def test_close_connection_idempotent():
    with tempfile.TemporaryDirectory() as tmp:
        db_path = os.path.join(tmp, "test_close.db")
        with patch.object(kg, "_db_path", return_value=db_path):
            kg.close_connection()
            repo = os.path.join(tmp, "repo")
            os.makedirs(repo)
            kg.record_repo_seen(repo)
            kg.close_connection()
            kg.close_connection()
            assert kg._connection is None


def test_record_copy_event_and_cooccurrence():
    with tempfile.TemporaryDirectory() as tmp:
        db_path = os.path.join(tmp, "test_knowledge2.db")
        with patch.object(kg, "_db_path", return_value=db_path):
            kg.close_connection()
            repo = os.path.join(tmp, "repo")
            os.makedirs(repo)
            f1 = os.path.join(repo, "a.py")
            f2 = os.path.join(repo, "b.py")
            open(f1, "w").close()
            open(f2, "w").close()
            kg.record_copy_event(repo, [f1, f2])
            h1 = kg.path_hash(f1)
            recs = kg.get_files_often_copied_together(repo, [h1])
            assert "b.py" in recs or "a.py" in recs
            kg.close_connection()
