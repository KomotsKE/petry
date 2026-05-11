import tkinter as tk
from tkinter import ttk


class SimulationTab:
    def __init__(self, parent, editor):
        self.editor = editor
        self.frame = ttk.Frame(parent)
        parent.add(self.frame, text="Симуляция")

        ttk.Label(self.frame, text="Управление:", font=('Arial', 10, 'bold')).pack(pady=5)
        ttk.Button(self.frame, text="Шаг вперед",
                   command=editor.simulation.simulation_step).pack(fill='x', padx=10, pady=2)

        self.auto_btn_var = tk.StringVar(value="Авто-симуляция")
        self.auto_btn = ttk.Button(self.frame, textvariable=self.auto_btn_var,
                                   command=editor.simulation.auto_simulation)
        self.auto_btn.pack(fill='x', padx=10, pady=2)

        ttk.Button(self.frame, text="Проиграть сценарий...",
                   command=editor.simulation.play_scenario).pack(fill='x', padx=10, pady=2)

        # Регистрируем колбэк смены состояния авто-симуляции
        editor.simulation._on_auto_state_change = self._on_auto_state_change
        
        # ── Файлы ────────────────────────────────────────────────────────
        ttk.Separator(self.frame, orient='horizontal').pack(fill='x', pady=8)
        ttk.Label(self.frame, text="Файл:", font=('Arial', 10, 'bold')).pack(pady=(0, 4))
        file_frame = ttk.Frame(self.frame)
        file_frame.pack(fill="x", padx=10)
        ttk.Button(file_frame, text="Сохранить сеть",
                   command=editor.saveload.save_to_file).pack(fill="x", pady=2)
        ttk.Button(file_frame, text="Загрузить сеть",
                   command=self._on_load_network).pack(fill="x", pady=2)

    def _on_auto_state_change(self, running: bool):
        if running:
            self.auto_btn_var.set("⏹ Остановить")
        else:
            self.auto_btn_var.set("Авто-симуляция")
            
    def _on_load_network(self):
        self.editor.saveload.load_from_file()
        self.editor._rebind_all_elements()