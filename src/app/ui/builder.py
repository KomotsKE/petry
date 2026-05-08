import tkinter as tk
from tkinter import ttk
from app.ui.tabs.tools_tab import ToolsTab
from app.ui.tabs.simulation_tab import SimulationTab
from app.ui.tabs.marking_tab import MarkingTab
from app.ui.tabs.analysis_tab import AnalysisTab


class UIBuilder:
    def __init__(self, editor):
        self.editor = editor
        self.root = editor.root
        self.pre_build()

    def pre_build(self):
        self._setup_style()
        self._create_main_panels()
        self._create_canvas()

    def post_build(self):
        self._create_status_bar()
        self._create_notebook()
        self._create_tabs()
        self._link_ui_variables()

    def _setup_style(self):
        ttk.Style().theme_use("clam")

    def _create_main_panels(self):
        main_panel = ttk.PanedWindow(self.root, orient=tk.HORIZONTAL)
        main_panel.pack(fill=tk.BOTH, expand=True)

        self.editor.left_frame = ttk.Frame(main_panel, width=300)
        main_panel.add(self.editor.left_frame, weight=0)

        canvas_frame = ttk.Frame(main_panel)
        main_panel.add(canvas_frame, weight=1)
        self.editor.canvas_frame = canvas_frame

    def _create_canvas(self):
        self.editor.canvas = tk.Canvas(self.editor.canvas_frame, bg='white')
        self.editor.canvas.grid(row=0, column=0, sticky='nsew')
        self.editor.canvas_frame.grid_rowconfigure(0, weight=1)
        self.editor.canvas_frame.grid_columnconfigure(0, weight=1)

    def _create_status_bar(self):
        status = ttk.Frame(self.root, padding=(6, 2))
        status.pack(side="bottom", fill="x")
        self.editor.status_var = tk.StringVar(value="Приложение готово к работе")
        ttk.Label(status, textvariable=self.editor.status_var).pack(side="left")

    def _create_notebook(self):
        self.editor.notebook = ttk.Notebook(self.editor.left_frame)
        self.editor.notebook.pack(fill=tk.BOTH, expand=True)

    def _create_tabs(self):
        self.editor.tools_tab = ToolsTab(self.editor.notebook, self.editor)
        self.editor.simulation_tab = SimulationTab(self.editor.notebook, self.editor)
        self.editor.marking_tab = MarkingTab(self.editor.notebook, self.editor)
        self.editor.analysis_tab = AnalysisTab(self.editor.notebook, self.editor)

    def _link_ui_variables(self):
        net = self.editor.petriNetwork
        tab = self.editor.tools_tab
        net.element_name_var  = tab.get_element_name_var()
        net.element_type_var  = tab.get_element_type_var()
        net.tokens_var        = tab.get_tokens_var()
        net.tokens_spinbox    = tab.get_tokens_spinbox()
        net.priority_var      = tab.get_priority_var()
        net.priority_spinbox  = tab.get_priority_spinbox()
        net.label_var         = tab.get_label_var()
        net.label_entry       = tab.get_label_entry()
        self.editor.speed_var = self.editor.simulation_tab.get_speed_var()