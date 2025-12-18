import ttkbootstrap as ttk
import tkinter as tk
from ttkbootstrap.scrolled import ScrolledText
import logging
from widgets import Tooltip
from constants import ERROR_MESSAGE_DURATION

class ModuleAnalysisTab(ttk.Frame):
    def __init__(self, parent, gui):
        super().__init__(parent)
        self.gui = gui
        # Colors now managed by ttkbootstrap theme
        self.analysis_results = None
        self.setup_ui()

    def setup_ui(self):
        """Setup the module analysis tab UI components."""
        # Main button frame
        self.button_frame = ttk.Frame(self)
        self.button_frame.pack(side=tk.TOP, fill='x', pady=5)

        # Analysis button
        self.analyze_button = self.gui.create_button(
            self.button_frame, 
            "Analyze Modules", 
            self.start_analysis,
            "Analyze repository for module dependencies and groupings"
        )
        self.analyze_button.pack(side=tk.LEFT, padx=10, pady=5)

        # Clear button
        self.clear_button = self.gui.create_button(
            self.button_frame, 
            "Clear Results", 
            self.clear_results,
            "Clear current analysis results"
        )
        self.clear_button.pack(side=tk.LEFT, padx=5, pady=5)

        # Export button (initially disabled)
        self.export_button = self.gui.create_button(
            self.button_frame, 
            "Export Modules", 
            self.export_modules,
            "Export module analysis results",
            state=tk.DISABLED
        )
        self.export_button.pack(side=tk.LEFT, padx=5, pady=5)

        # Progress frame
        self.progress_frame = ttk.Frame(self)
        self.progress_frame.pack(side=tk.TOP, fill='x', pady=5)

        self.progress_label = ttk.Label(
            self.progress_frame, 
            text="Ready to analyze"
        )
        self.progress_label.pack(side=tk.LEFT, padx=10)

        # Main content area with notebook for different views
        self.content_notebook = ttk.Notebook(self)
        self.content_notebook.pack(fill="both", expand=True, padx=5, pady=5)

        # Module tree view
        self.tree_frame = ttk.Frame(self.content_notebook)
        self.content_notebook.add(self.tree_frame, text="Module Tree")

        self.setup_tree_view()

        # Dependency graph view
        self.graph_frame = ttk.Frame(self.content_notebook)
        self.content_notebook.add(self.graph_frame, text="Dependency Graph")

        self.setup_graph_view()

        # Analysis details view
        self.details_frame = tk.Frame(self.content_notebook)
        self.content_notebook.add(self.details_frame, text="Analysis Details")

        self.setup_details_view()

    def setup_tree_view(self):
        """Setup the module tree view."""
        # Tree view for modules
        self.module_tree = ttk.Treeview(
            self.tree_frame, 
            columns=("files", "type", "dependencies"), 
            show="tree headings"
        )
        self.module_tree.heading("#0", text="Module Name")
        self.module_tree.heading("files", text="Files")
        self.module_tree.heading("type", text="Type")
        self.module_tree.heading("dependencies", text="Dependencies")

        # Scrollbar for tree
        tree_scrollbar = ttk.Scrollbar(self.tree_frame, orient="vertical", command=self.module_tree.yview)
        self.module_tree.configure(yscrollcommand=tree_scrollbar.set)

        # Pack tree and scrollbar
        self.module_tree.pack(side="left", fill="both", expand=True, padx=5, pady=5)
        tree_scrollbar.pack(side="right", fill="y")

        # Bind double-click to show module details
        self.module_tree.bind("<Double-1>", self.on_module_double_click)

    def setup_graph_view(self):
        """Setup the dependency graph view."""
        self.graph_text = ScrolledText(
            self.graph_frame,
            wrap=tk.WORD,
            font=("Arial", 10),
            state=tk.DISABLED,
            bootstyle="dark"
        )
        self.graph_text.pack(fill="both", expand=True, padx=5, pady=5)

    def setup_details_view(self):
        """Setup the analysis details view."""
        self.details_text = ScrolledText(
            self.details_frame,
            wrap=tk.WORD,
            font=("Arial", 10),
            state=tk.DISABLED,
            bootstyle="dark"
        )
        self.details_text.pack(fill="both", expand=True, padx=5, pady=5)


    def start_analysis(self):
        """Start the module analysis process."""
        if not self.gui.current_repo_path:
            self.gui.show_status_message("No repository loaded. Please select a repository first.", error=True)
            return

        if self.gui.is_loading:
            self.gui.show_status_message("Another operation is in progress. Please wait.", error=True)
            return

        # Import here to avoid circular imports
        from module_analyzer import ModuleAnalyzer
        
        self.analyze_button.config(state=tk.DISABLED)
        self.progress_label.config(text="Analyzing modules...")
        self.gui.show_loading_state("Analyzing module dependencies...")

        # Create analyzer and start background analysis
        analyzer = ModuleAnalyzer(self.gui)
        analyzer.analyze_repository(
            self.gui.current_repo_path,
            self._on_analysis_complete
        )

    def _on_analysis_complete(self, results, errors):
        """Handle completion of module analysis."""
        self.gui.hide_loading_state()
        self.analyze_button.config(state=tk.NORMAL)
        
        if errors:
            error_msg = f"Analysis completed with {len(errors)} errors: {'; '.join(errors[:3])}"
            self.gui.show_status_message(error_msg, error=True, duration=ERROR_MESSAGE_DURATION)
        else:
            self.gui.show_status_message("Module analysis completed successfully.")

        self.analysis_results = results
        self._display_results(results, errors)

    def _display_results(self, results, errors):
        """Display the analysis results in the UI."""
        if not results:
            self.progress_label.config(text="No modules found")
            return

        # Update progress label
        module_count = len(results.get('modules', []))
        self.progress_label.config(text=f"Found {module_count} modules")

        # Populate tree view
        self._populate_module_tree(results)

        # Update graph view
        self._update_graph_view(results)

        # Update details view
        self._update_details_view(results, errors)

        # Enable export button
        self.export_button.config(state=tk.NORMAL)

    def _populate_module_tree(self, results):
        """Populate the module tree with results."""
        # Clear existing items
        for item in self.module_tree.get_children():
            self.module_tree.delete(item)

        modules = results.get('modules', [])
        for i, module in enumerate(modules):
            module_name = module.get('name', f'Module {i+1}')
            files = module.get('files', [])
            module_type = module.get('type', 'Unknown')
            dependencies = module.get('dependencies', [])

            # Insert module
            module_id = self.module_tree.insert(
                "", "end", 
                text=module_name,
                values=(len(files), module_type, len(dependencies)),
                tags=('module',)
            )

            # Insert files under module
            for file_path in files:
                file_name = file_path.split('/')[-1] if '/' in file_path else file_path
                self.module_tree.insert(
                    module_id, "end",
                    text=file_name,
                    values=(file_path, "", ""),
                    tags=('file',)
                )

    def _update_graph_view(self, results):
        """Update the dependency graph view."""
        # ttkbootstrap ScrolledText is always editable
        self.graph_text.delete(1.0, tk.END)

        # Simple text representation of dependencies
        graph_text = "Dependency Graph:\n\n"
        
        modules = results.get('modules', [])
        for module in modules:
            module_name = module.get('name', 'Unknown')
            dependencies = module.get('dependencies', [])
            
            graph_text += f"Module: {module_name}\n"
            if dependencies:
                graph_text += f"  Dependencies: {', '.join(dependencies)}\n"
            else:
                graph_text += "  Dependencies: None (standalone)\n"
            graph_text += "\n"

        self.graph_text.insert(1.0, graph_text)
        # ttkbootstrap ScrolledText is always editable

    def _update_details_view(self, results, errors):
        """Update the analysis details view."""
        # ttkbootstrap ScrolledText is always editable
        self.details_text.delete(1.0, tk.END)

        details = f"Module Analysis Results\n{'='*50}\n\n"
        
        # Summary statistics
        modules = results.get('modules', [])
        total_files = sum(len(module.get('files', [])) for module in modules)
        
        details += f"Total Modules: {len(modules)}\n"
        details += f"Total Files Analyzed: {total_files}\n"
        details += f"Standalone Modules: {len([m for m in modules if not m.get('dependencies', [])])}\n\n"

        # Module details
        for i, module in enumerate(modules):
            module_name = module.get('name', f'Module {i+1}')
            files = module.get('files', [])
            dependencies = module.get('dependencies', [])
            module_type = module.get('type', 'Unknown')
            
            details += f"Module: {module_name}\n"
            details += f"  Type: {module_type}\n"
            details += f"  Files: {len(files)}\n"
            details += f"  Dependencies: {len(dependencies)}\n"
            if dependencies:
                details += f"    {', '.join(dependencies)}\n"
            details += f"  Files:\n"
            for file_path in files:
                details += f"    - {file_path}\n"
            details += "\n"

        # Errors
        if errors:
            details += f"\nErrors:\n{'-'*20}\n"
            for error in errors:
                details += f"- {error}\n"

        self.details_text.insert(1.0, details)
        # ttkbootstrap ScrolledText is always editable

    def on_module_double_click(self, event):
        """Handle double-click on module tree item."""
        item = self.module_tree.selection()[0]
        tags = self.module_tree.item(item)['tags']
        
        if 'file' in tags:
            # Jump to file in content tab
            file_path = self.module_tree.item(item)['values'][0]
            self.gui.notebook.select(0)  # Switch to content tab

    def export_modules(self):
        """Export module analysis results."""
        if not self.analysis_results:
            self.gui.show_status_message("No analysis results to export.", error=True)
            return

        self.gui.show_status_message("Export functionality coming soon!")

    def clear_results(self):
        """Clear the analysis results."""
        self.analysis_results = None
        
        # Clear tree
        for item in self.module_tree.get_children():
            self.module_tree.delete(item)

        # Clear text views
        # ttkbootstrap ScrolledText is always editable
        self.graph_text.delete(1.0, tk.END)
        # ttkbootstrap ScrolledText is always editable

        # ttkbootstrap ScrolledText is always editable
        self.details_text.delete(1.0, tk.END)
        # ttkbootstrap ScrolledText is always editable

        # Reset UI
        self.progress_label.config(text="Ready to analyze")
        self.export_button.config(state=tk.DISABLED)
        self.gui.show_status_message("Analysis results cleared.")

    def perform_search(self, query, case_sensitive, whole_word):
        """Search functionality for the module analysis tab."""
        return []

    def highlight_all_matches(self, matches):
        """Highlight search matches."""
        pass

    def highlight_match(self, match_data, is_focused=True):
        """Highlight a specific match."""
        pass

    def center_match(self, match_data):
        """Center on a specific match."""
        pass

    def clear_highlights(self):
        """Clear all highlights."""
        pass

    def clear(self):
        """Clear the tab content."""
        self.clear_results()
