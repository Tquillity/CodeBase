# tests/conftest.py
# Cross-test isolation + robust Tk root creation for the GUI test suite.
from __future__ import annotations

import os
import sys

import pytest


def _pin_tcl_tk_library() -> None:
    """Pin TCL_LIBRARY / TK_LIBRARY to the interpreter's bundled Tcl/Tk dirs.

    The GUI tests create one Tk root per test (~40 per run). On Windows, Tcl
    searches several candidate directories for its library files when a root is
    created, and under rapid repeated interpreter initialization this resolution
    intermittently fails (`Can't find a usable tk.tcl` / `couldn't read
    spinbox.tcl`). Setting the library env vars explicitly makes the lookup
    deterministic and removes the ambiguity. No-op if the dirs can't be found or
    the vars are already set. The shipped app creates a single root and is
    unaffected either way.
    """
    tcl_base = os.path.join(sys.base_prefix, "tcl")
    if not os.path.isdir(tcl_base):
        return
    try:
        for name in os.listdir(tcl_base):
            full = os.path.join(tcl_base, name)
            if not os.path.isdir(full):
                continue
            if name.startswith("tcl8") and "TCL_LIBRARY" not in os.environ:
                os.environ["TCL_LIBRARY"] = full
            elif name.startswith("tk8") and "TK_LIBRARY" not in os.environ:
                os.environ["TK_LIBRARY"] = full
    except OSError:
        pass


_pin_tcl_tk_library()


@pytest.fixture
def make_ttk_root():
    """Factory that creates withdrawn ttkbootstrap roots, retrying the transient
    Tcl/Tk init race, and destroys them at test teardown.

    Per-test roots keep the heavyweight GUI tests isolated (a single shared root
    accumulates widget state and breaks them). The retry absorbs the rare
    Tcl-library init failure so a flake never reaches the test.
    """
    import ttkbootstrap as ttk

    created = []

    def _make():
        last_err = None
        for _ in range(6):
            try:
                root = ttk.Window()
                root.withdraw()
                created.append(root)
                return root
            except Exception as e:  # transient Tcl init race during root creation
                last_err = e
        raise last_err  # pragma: no cover - exhausted retries

    yield _make

    for root in created:
        try:
            root.destroy()
        except Exception:
            pass


@pytest.fixture(autouse=True)
def reset_ttkbootstrap_state():
    """Reset ttkbootstrap's process-global singletons between tests.

    ttkbootstrap keeps global state that leaks across tests when GUI modules
    create and destroy their own Tk roots, surfacing on Windows as
    `TclError: application has been destroyed` (and previously a native crash):

      1. Style.instance — the Style singleton is bound to the first root's
         interpreter; nulling it rebuilds it against the current live root.
      2. Publisher subscribers — widgets subscribe for theme-change events and
         are NOT auto-unsubscribed on destroy, so a stale subscriber from a
         destroyed root fires into a dead interpreter on the next publish.
      3. tkinter._default_root — ttk.Style binds its master to _default_root and
         tk.Tk() won't overwrite a non-None one, so a stale (destroyed) default
         root would make a freshly-built Style call a dead interpreter.

    No-op for tests that never touch ttkbootstrap; harmless on Linux.
    """
    def _reset() -> None:
        try:
            import ttkbootstrap.style as _tbstyle
            _tbstyle.Style.instance = None
        except Exception:
            pass
        try:
            from ttkbootstrap.publisher import Publisher
            Publisher.clear_subscribers()
        except Exception:
            pass
        try:
            import tkinter as _tk
            root = getattr(_tk, "_default_root", None)
            if root is not None:
                try:
                    alive = bool(root.winfo_exists())
                except Exception:
                    alive = False
                if not alive:
                    _tk._default_root = None
        except Exception:
            pass

    _reset()
    yield
    _reset()
