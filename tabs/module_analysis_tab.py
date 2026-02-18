# tabs/module_analysis_tab.py
# Module Analysis tab: dependency graph, impact scores, clusters, one-click module/cluster selection.
from __future__ import annotations

import logging
import os
import tkinter as tk
from typing import TYPE_CHECKING, Any, Dict, List, Optional, Tuple, cast

import ttkbootstrap as ttk
from widgets import Tooltip

from module_analyzer import (
    IMPORT_PATTERNS,
    MAX_GRAPH_NODES,
    modules_with_impact,
)

if TYPE_CHECKING:
    from gui import RepoPromptGUI

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

try:
    from scipy.cluster import hierarchy as scipy_hierarchy  # type: ignore[import-untyped]
    _HAS_SCIPY_DENDRO = True
except ImportError:
    scipy_hierarchy = None
    _HAS_SCIPY_DENDRO = False


# Tree parent IDs for left-panel sections
_MODULES_PARENT_TEXT = "Modules"
_CLUSTERS_PARENT_TEXT = "Clusters"


class ModuleAnalysisTab(ttk.Frame):
    _last_modules: List[Tuple[str, int, float]]
    _last_module_to_paths: Dict[str, List[str]]
    _last_G: Any
    _last_py_files_by_rel: Dict[str, str]
    _last_clusters: List[Tuple[str, List[str], int, float]]
    _last_cluster_to_paths: Dict[str, List[str]]
    _last_linkage_Z: Any
    _canvas: Optional[Any]
    _fallback_text: Optional[tk.Text]
    _fallback_var: Optional[tk.StringVar]
    _right_placeholder: Optional[Any]
    _right_container: Optional[ttk.Frame]
    _left_empty_label: Optional[ttk.Label]
    _selected_cluster_name: Optional[str]
    select_cluster_btn: ttk.Button

    def __init__(self, parent: tk.Misc, gui: Any) -> None:
        super().__init__(parent)
        self.gui = gui
        self._last_modules = []
        self._last_module_to_paths = {}
        self._last_G = None
        self._last_py_files_by_rel = {}
        self._last_clusters = []
        self._last_cluster_to_paths = {}
        self._last_linkage_Z = None
        self._canvas = None
        self._fallback_text = None
        self._fallback_var = None
        self._right_placeholder = None
        self._right_container = None
        self._left_empty_label = None
        self._selected_cluster_name = None
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
        self.select_cluster_btn = self.gui.create_button(
            toolbar,
            "Select This Cluster",
            self._on_select_cluster,
            "Select all files in this cluster in the main file tree",
            state=tk.DISABLED,
        )
        self.select_cluster_btn.pack(side=tk.LEFT, padx=(0, 8))
        Tooltip(self.analyze_btn, "Build dependency graph from current repository")
        Tooltip(self.select_module_btn, "Add this module's files to selection and update preview")
        Tooltip(self.select_cluster_btn, "Add this cluster's files to selection and update preview")

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

    def _on_tree_select(self, event: tk.Event[Any]) -> None:
        self._on_tree_select_impl()

    def _on_tree_select_impl(self) -> None:
        sel = self.tree.selection()
        if not sel:
            self.select_module_btn.config(state=tk.DISABLED)
            self.select_cluster_btn.config(state=tk.DISABLED)
            self._selected_cluster_name = None
            return
        item_id = sel[0]
        tags = self.tree.item(item_id, "tags")
        if "cluster" in tags:
            self._selected_cluster_name = self.tree.item(item_id, "text")
            self.select_module_btn.config(state=tk.DISABLED)
            self.select_cluster_btn.config(state=tk.NORMAL)
        elif "module" in tags:
            self._selected_cluster_name = None
            self.select_module_btn.config(state=tk.NORMAL)
            self.select_cluster_btn.config(state=tk.DISABLED)
        else:
            self._selected_cluster_name = None
            self.select_module_btn.config(state=tk.DISABLED)
            self.select_cluster_btn.config(state=tk.DISABLED)

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
                modules, G, py_files_by_rel, module_to_abs, clusters, linkage_Z = (
                    modules_with_impact(repo, enabled_extensions=enabled_extensions)
                )
                self.gui.task_queue.put(
                    (
                        self._apply_analysis_result,
                        (modules, G, py_files_by_rel, module_to_abs, clusters, linkage_Z),
                    )
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
        clusters: List[Tuple[str, List[str], int, float]],
        linkage_Z: Any,
    ) -> None:
        self._last_modules = modules
        self._last_module_to_paths = module_to_abs_paths
        self._last_G = G
        self._last_py_files_by_rel = py_files_by_rel
        self._last_clusters = clusters
        self._last_linkage_Z = linkage_Z
        cluster_to_paths: Dict[str, List[str]] = {}
        for cname, mod_keys, _fc, _imp in clusters:
            paths: List[str] = []
            for mod_key in mod_keys:
                paths.extend(module_to_abs_paths.get(mod_key, []))
            cluster_to_paths[cname] = paths
        self._last_cluster_to_paths = cluster_to_paths
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
        self.select_cluster_btn.config(state=tk.DISABLED)

    def _refresh_tree(self) -> None:
        if self._left_empty_label:
            self._left_empty_label.destroy()
            self._left_empty_label = None
        # Restore tree and scrollbar if they were hidden by empty state
        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(5, 0), pady=(0, 5))
        self._tree_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        self.tree.delete(*self.tree.get_children())
        modules_parent = self.tree.insert("", tk.END, text=_MODULES_PARENT_TEXT, values=("", ""), open=True)
        for name, count, impact in self._last_modules:
            display_name = name.replace(os.sep, ".")
            self.tree.insert(
                modules_parent,
                tk.END,
                text=display_name,
                values=(count, f"{impact:.3f}"),
                tags=("module",),
            )
        clusters_parent = self.tree.insert("", tk.END, text=_CLUSTERS_PARENT_TEXT, values=("", ""), open=True)
        for cname, _mods, file_count, agg_impact in self._last_clusters:
            self.tree.insert(
                clusters_parent,
                tk.END,
                text=cname,
                values=(file_count, f"{agg_impact:.3f}"),
                tags=("cluster",),
            )
        if self._last_modules:
            self.select_module_btn.config(state=tk.NORMAL)
        self._on_tree_select_impl()

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
        G = self._last_G
        has_dendro = (
            _HAS_SCIPY_DENDRO
            and scipy_hierarchy is not None
            and self._last_linkage_Z is not None
        )
        if has_dendro:
            fig = Figure(figsize=(6, 7), dpi=100)
            ax_graph = fig.add_subplot(211)
            ax_dendro = fig.add_subplot(212)
        else:
            fig = Figure(figsize=(6, 5), dpi=100)
            ax_graph = fig.add_subplot(111)
            ax_dendro = None
        try:
            pos = nx.spring_layout(G, k=0.5, iterations=50, seed=42)
        except Exception:
            pos = nx.shell_layout(G)
        node_to_cluster_idx: Dict[str, int] = {}
        for idx, (_cname, mods, _fc, _imp) in enumerate(self._last_clusters):
            for mod in mods:
                node_to_cluster_idx[mod] = idx
        _cluster_colors = [
            "#1f77b4", "#ff7f0e", "#2ca02c", "#d62728", "#9467bd",
            "#8c564b", "#e377c2", "#7f7f7f", "#bcbd22", "#17becf",
        ]
        node_colors = [
            _cluster_colors[node_to_cluster_idx.get(n, 0) % len(_cluster_colors)]
            for n in G.nodes()
        ]
        nx.draw_networkx_edges(G, pos, ax=ax_graph, edge_color="gray", alpha=0.6, arrows=True)
        nx.draw_networkx_nodes(
            G, pos, ax=ax_graph, node_color=node_colors, node_size=80
        )
        labels = {n: os.path.basename(n) if os.path.basename(n) else n for n in G.nodes()}
        nx.draw_networkx_labels(G, pos, labels, ax=ax_graph, font_size=6)
        ax_graph.axis("off")
        if ax_dendro is not None and scipy_hierarchy is not None and self._last_linkage_Z is not None:
            nodes_ordered = list(G.nodes())
            scipy_hierarchy.dendrogram(
                self._last_linkage_Z,
                ax=ax_dendro,
                leaf_rotation=90,
                leaf_label_func=lambda i: nodes_ordered[i] if i < len(nodes_ordered) else str(i),
            )
            ax_dendro.set_title("Dendrogram")
        fig.tight_layout()
        self._canvas = FigureCanvasTkAgg(fig, master=self._right_container)  # type: ignore[no-untyped-call]
        self._canvas.draw()  # type: ignore[no-untyped-call]
        if self._right_container:
            self._canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)  # type: ignore[no-untyped-call]

    def _on_select_module(self) -> None:
        gui = cast("RepoPromptGUI", self.gui)
        sel = self.tree.selection()
        if not sel or not self._last_module_to_paths:
            gui.show_status_message("Select a module first.", error=True)
            return
        item = self.tree.item(sel[0])
        if "module" not in item.get("tags", ()):
            gui.show_status_message("Select a module from the Modules section.", error=True)
            return
        display_name = item["text"]
        key = "(root)" if display_name == "(root)" else display_name.replace(".", os.sep)
        if key not in self._last_module_to_paths:
            key = display_name
        paths = self._last_module_to_paths.get(key, [])
        if not paths:
            gui.show_status_message("No files for this module.", error=True)
            return
        gui.file_handler.select_files_by_paths(paths)
        gui.show_status_message(f"Selected {len(paths)} file(s) from {display_name}.")
        gui.notebook.select(1)  # type: ignore[no-untyped-call]

    def _on_select_cluster(self) -> None:
        gui = cast("RepoPromptGUI", self.gui)
        sel = self.tree.selection()
        if not sel or not self._last_cluster_to_paths:
            gui.show_status_message("Select a cluster first.", error=True)
            return
        item = self.tree.item(sel[0])
        if "cluster" not in item.get("tags", ()):
            gui.show_status_message("Select a cluster from the Clusters section.", error=True)
            return
        cname = item["text"]
        paths = self._last_cluster_to_paths.get(cname, [])
        if not paths:
            gui.show_status_message("No files in this cluster.", error=True)
            return
        gui.file_handler.select_cluster_by_paths(paths)
        gui.show_status_message(f"Selected {len(paths)} file(s) from {cname}.")
        gui.notebook.select(1)  # type: ignore[no-untyped-call]

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
        self._last_clusters = []
        self._last_cluster_to_paths = {}
        self._last_linkage_Z = None
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
        self.select_cluster_btn.config(state=tk.DISABLED)
