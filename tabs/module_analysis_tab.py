# tabs/module_analysis_tab.py
# Module Analysis tab: dependency graph, impact scores, one-click module selection.
from __future__ import annotations

import logging
import os
import tkinter as tk
from typing import Any, Dict, List, Optional, Tuple

import ttkbootstrap as ttk
from widgets import Tooltip

from module_analyzer import (
    IMPORT_PATTERNS,
    MAX_GRAPH_NODES,
    modules_with_impact,
)

logger = logging.getLogger(__name__)

# Matplotlib: explicit TkAgg for Linux (Wayland/X11)
try:
    import matplotlib
    matplotlib.use("TkAgg")
    from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
    from matplotlib.figure import Figure
    _HAS_MPL = True
except ImportError:
    _HAS_MPL = False

try:
    import networkx as nx  # type: ignore[import-untyped]
except ImportError:
    nx = None


class ModuleAnalysisTab(ttk.Frame):
    def __init__(self, parent: ttk.Frame, gui: Any) -> None:
        super().__init__(parent)
        self.gui = gui
        self._last_modules: List[Tuple[str, int, float]] = []
        self._last_module_to_paths: Dict[str, List[str]] = {}
        self._last_G: Any = None
        self._last_py_files_by_rel: Dict[str, str] = {}
        self._canvas: Optional[Any] = None
        self._fallback_text: Optional[tk.Text] = None
        self._fallback_var: Optional[tk.StringVar] = None
        self._right_placeholder: Optional[Any] = None
        self._right_container: Optional[ttk.Frame] = None
        self.setup_ui()

    def setup_ui(self) -> None:
        toolbar = ttk.Frame(self)
        toolbar.pack(side=tk.TOP, fill=tk.X, padx=8, pady=(8, 4))
        self.analyze_btn = self.gui.create_button(
            toolbar,
            "Analyze Repository",
            self._on_analyze,
            "Scan repo and build dependency graph (Python, JS/TS, Rust, etc.)",
        )
        self.analyze_btn.pack(side=tk.LEFT, padx=(0, 8))
        self.select_module_btn = self.gui.create_button(
            toolbar,
            "Select This Module",
            self._on_select_module,
            "Select all files of the chosen module in the main file tree",
            state=tk.DISABLED,
        )
        self.select_module_btn.pack(side=tk.LEFT, padx=(0, 8))
        Tooltip(self.analyze_btn, "Build dependency graph from current repository")
        Tooltip(self.select_module_btn, "Add this module's files to selection and update preview")

        paned = ttk.Panedwindow(self, orient=tk.HORIZONTAL)
        paned.pack(fill=tk.BOTH, expand=True, padx=8, pady=(4, 8))

        # Left: Treeview (module name, file count, impact)
        left_frame = ttk.Frame(paned)
        self._tree_scroll = ttk.Scrollbar(left_frame)
        self.tree = ttk.Treeview(
            left_frame,
            columns=("files", "impact"),
            show="tree headings",
            selectmode="browse",
            height=20,
            yscrollcommand=self._tree_scroll.set,
        )
        self._tree_scroll.config(command=self.tree.yview)
        self.tree.column("#0", width=220, anchor=tk.W)
        self.tree.column("files", width=70, anchor=tk.E)
        self.tree.column("impact", width=80, anchor=tk.E)
        self.tree.heading("#0", text="Module / Package")
        self.tree.heading("files", text="Files")
        self.tree.heading("impact", text="Impact")
        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(5, 0), pady=(0, 5))
        self._tree_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        paned.add(left_frame, weight=1)

        # Right: Graph or fallback text
        right_frame = ttk.Frame(paned)
        ph = ttk.Label(
            right_frame,
            text="Click 'Analyze Repository' to build the dependency graph.",
            font=("Arial", 10),
        )
        ph.pack(expand=True)
        paned.add(right_frame, weight=2)

        self.tree.bind("<<TreeviewSelect>>", self._on_tree_select)
        self._right_placeholder = ph
        self._right_container = right_frame
        self._left_empty_label: Optional[ttk.Label] = None

    def _on_tree_select(self, event: tk.Event) -> None:
        sel = self.tree.selection()
        if sel:
            self.select_module_btn.config(state=tk.NORMAL)
        else:
            self.select_module_btn.config(state=tk.DISABLED)

    def _on_analyze(self) -> None:
        if self.gui.is_loading:
            self.gui.show_status_message("Another operation in progress.", error=True)
            return
        repo = self.gui.current_repo_path
        if not repo or not os.path.isdir(repo):
            self.gui.show_status_message("No repository loaded.", error=True)
            return
        self.analyze_btn.config(state=tk.DISABLED)
        self.gui.show_status_message("Analyzing modules...")

        # Use enabled text extensions from settings; fall back to all supported if not set
        ext_settings = self.gui.settings.get("app", "text_extensions", {})
        enabled_extensions = {
            ext for ext, val in ext_settings.items()
            if val == 1 and ext in IMPORT_PATTERNS
        }
        if not enabled_extensions:
            enabled_extensions = set(IMPORT_PATTERNS.keys())

        def worker() -> None:
            try:
                modules, G, py_files_by_rel, module_to_abs = modules_with_impact(
                    repo, enabled_extensions=enabled_extensions
                )
                self.gui.task_queue.put(
                    (self._apply_analysis_result, (modules, G, py_files_by_rel, module_to_abs))
                )
            except Exception as e:
                logger.exception("Module analysis failed")
                self.gui.task_queue.put((self._on_analysis_error, (str(e),)))

        t = __import__("threading").Thread(target=worker, daemon=True)
        self.gui.register_background_thread(t)
        t.start()

    def _on_analysis_error(self, message: str) -> None:
        self.analyze_btn.config(state=tk.NORMAL)
        self.gui.show_status_message(f"Analysis failed: {message}", error=True)
        self.gui.hide_loading_state()

    def _apply_analysis_result(
        self,
        modules: List[Tuple[str, int, float]],
        G: Any,
        py_files_by_rel: Dict[str, str],
        module_to_abs_paths: Dict[str, List[str]],
    ) -> None:
        self._last_modules = modules
        self._last_module_to_paths = module_to_abs_paths
        self._last_G = G
        self._last_py_files_by_rel = py_files_by_rel
        self.analyze_btn.config(state=tk.NORMAL)
        if not modules:
            self.gui.show_status_message("No supported source files found.")
            self._show_empty_state()
            return
        self.gui.show_status_message("Module analysis complete.")
        self._refresh_tree()
        self._show_graph_or_fallback()

    def _empty_state_message(self) -> str:
        return (
            "No supported source files found in this repository.\n\n"
            "Module Analysis works with: Python, JavaScript/TypeScript, Rust, C/C++, Java, Go, etc.\n\n"
            "Make sure your text extensions are enabled in Settings."
        )

    def _show_empty_state(self) -> None:
        """Show friendly empty-state message in both left and right panels."""
        self.tree.delete(*self.tree.get_children())
        # Left panel: hide tree and scrollbar, show centered message
        left_parent = self.tree.master
        self.tree.pack_forget()
        self._tree_scroll.pack_forget()
        if self._left_empty_label:
            self._left_empty_label.destroy()
        self._left_empty_label = ttk.Label(
            left_parent,
            text=self._empty_state_message(),
            font=("Arial", 10),
            wraplength=280,
            justify=tk.CENTER,
        )
        self._left_empty_label.pack(fill=tk.BOTH, expand=True, pady=20, padx=10)
        # Right panel
        self._clear_right()
        if self._right_container:
            ph = ttk.Label(
                self._right_container,
                text=self._empty_state_message(),
                font=("Arial", 10),
                wraplength=400,
                justify=tk.CENTER,
            )
            ph.pack(expand=True, fill=tk.BOTH, pady=20, padx=20)
            self._right_placeholder = ph
        self.select_module_btn.config(state=tk.DISABLED)

    def _refresh_tree(self) -> None:
        if self._left_empty_label:
            self._left_empty_label.destroy()
            self._left_empty_label = None
        # Restore tree and scrollbar if they were hidden by empty state
        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(5, 0), pady=(0, 5))
        self._tree_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        self.tree.delete(*self.tree.get_children())
        for name, count, impact in self._last_modules:
            display_name = name.replace(os.sep, ".")
            self.tree.insert(
                "",
                tk.END,
                text=display_name,
                values=(count, f"{impact:.3f}"),
            )
        if self._last_modules:
            self.select_module_btn.config(state=tk.NORMAL)

    def _clear_right(self) -> None:
        if self._canvas:
            self._canvas.get_tk_widget().destroy()
            self._canvas = None
        if self._fallback_text:
            self._fallback_text.destroy()
            self._fallback_text = None
        if self._fallback_var is not None:
            self._fallback_var = None
        container = self._right_container
        if container:
            for w in container.winfo_children():
                w.destroy()
            ph = ttk.Label(container, text="", font=("Arial", 10))
            ph.pack(expand=True)
            self._right_placeholder = ph

    def _show_graph_or_fallback(self) -> None:
        self._clear_right()
        G = self._last_G
        n = G.number_of_nodes() if G is not None else 0
        if n > MAX_GRAPH_NODES or not _HAS_MPL or nx is None:
            self._show_fallback_text()
            return
        self._show_matplotlib_graph()

    def _show_fallback_text(self) -> None:
        if self._right_placeholder:
            self._right_placeholder.destroy()
            self._right_placeholder = None
        # Searchable text: adjacency list or summary
        filter_frame = ttk.Frame(self._right_container)
        filter_frame.pack(fill=tk.X)
        self._fallback_var = tk.StringVar()
        ttk.Label(filter_frame, text="Filter:").pack(side=tk.LEFT, padx=(0, 4))
        entry = ttk.Entry(filter_frame, textvariable=self._fallback_var, width=30)
        entry.pack(side=tk.LEFT, fill=tk.X, expand=True)
        entry.bind("<KeyRelease>", self._on_fallback_filter)
        sb = ttk.Scrollbar(self._right_container)
        self._fallback_text = tk.Text(
            self._right_container,
            wrap=tk.WORD,
            font=("Monospace", 9),
            yscrollcommand=sb.set,
            state=tk.DISABLED,
        )
        sb.config(command=self._fallback_text.yview)
        self._fallback_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        sb.pack(side=tk.RIGHT, fill=tk.Y)
        lines: List[str] = []
        if self._last_G is not None and nx is not None:
            G = self._last_G
            lines.append(f"Nodes: {G.number_of_nodes()}, Edges: {G.number_of_edges()}\n")
            for u in sorted(G.nodes()):
                succ = list(G.successors(u))
                if succ:
                    lines.append(f"{u} -> {', '.join(sorted(succ))}\n")
                else:
                    lines.append(f"{u}\n")
        else:
            lines.append("No graph (install networkx for dependency graph).\n")
            for name, count, impact in self._last_modules:
                lines.append(f"  {name}: {count} files, impact {impact:.3f}\n")
        self._fallback_text.config(state=tk.NORMAL)
        self._fallback_text.insert(tk.END, "".join(lines))
        self._fallback_text.config(state=tk.DISABLED)
        self._fallback_full_content = "".join(lines)

    def _on_fallback_filter(self, event: tk.Event) -> None:
        if not self._fallback_text or self._fallback_var is None:
            return
        q = self._fallback_var.get().strip().lower()
        content = getattr(self, "_fallback_full_content", "")
        if not q:
            self._fallback_text.config(state=tk.NORMAL)
            self._fallback_text.delete("1.0", tk.END)
            self._fallback_text.insert(tk.END, content)
            self._fallback_text.config(state=tk.DISABLED)
            return
        lines = [l for l in content.splitlines() if q in l.lower()]
        self._fallback_text.config(state=tk.NORMAL)
        self._fallback_text.delete("1.0", tk.END)
        self._fallback_text.insert(tk.END, "\n".join(lines) or "(no matches)")
        self._fallback_text.config(state=tk.DISABLED)

    def _show_matplotlib_graph(self) -> None:
        if not _HAS_MPL or nx is None or self._last_G is None:
            return
        if self._right_placeholder:
            self._right_placeholder.destroy()
            self._right_placeholder = None
        fig = Figure(figsize=(6, 5), dpi=100)
        ax = fig.add_subplot(111)
        G = self._last_G
        try:
            pos = nx.spring_layout(G, k=0.5, iterations=50, seed=42)
        except Exception:
            pos = nx.shell_layout(G)
        nx.draw_networkx_edges(G, pos, ax=ax, edge_color="gray", alpha=0.6, arrows=True)
        nx.draw_networkx_nodes(G, pos, ax=ax, node_color="steelblue", node_size=80)
        labels = {n: os.path.basename(n) if os.path.basename(n) else n for n in G.nodes()}
        nx.draw_networkx_labels(G, pos, labels, ax=ax, font_size=6)
        ax.axis("off")
        fig.tight_layout()
        self._canvas = FigureCanvasTkAgg(fig, master=self._right_container)
        self._canvas.draw()
        if self._right_container:
            self._canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)

    def _on_select_module(self) -> None:
        sel = self.tree.selection()
        if not sel or not self._last_module_to_paths:
            self.gui.show_status_message("Select a module first.", error=True)
            return
        item = self.tree.item(sel[0])
        display_name = item["text"]
        # Tree shows display_name with . separator; keys in _last_module_to_paths use os.sep; "(root)" -> "."
        key = "(root)" if display_name == "(root)" else display_name.replace(".", os.sep)
        if key not in self._last_module_to_paths:
            key = display_name
        paths = self._last_module_to_paths.get(key, [])
        if not paths:
            self.gui.show_status_message("No files for this module.", error=True)
            return
        self.gui.file_handler.select_files_by_paths(paths)
        self.gui.show_status_message(f"Selected {len(paths)} file(s) from {display_name}.")
        self.gui.notebook.select(1)

    def perform_search(self, query: str, case_sensitive: bool, whole_word: bool) -> List[Any]:
        return []

    def center_match(self, match_data: Any) -> None:
        pass

    def highlight_match(self, match_data: Any, is_focused: bool = True) -> None:
        pass

    def highlight_all_matches(self, matches: List[Any]) -> None:
        pass

    def clear_highlights(self) -> None:
        pass

    def clear(self) -> None:
        self.tree.delete(*self.tree.get_children())
        self._last_modules = []
        self._last_module_to_paths = {}
        self._last_G = None
        self._last_py_files_by_rel = {}
        self._clear_right()
        if self._right_container:
            ph = ttk.Label(
                self._right_container,
                text="Click 'Analyze Repository' to build the dependency graph.",
                font=("Arial", 10),
            )
            ph.pack(expand=True)
            self._right_placeholder = ph
        self.select_module_btn.config(state=tk.DISABLED)
