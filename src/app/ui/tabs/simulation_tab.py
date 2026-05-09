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

        ttk.Label(self.frame, text="Скорость (мс):").pack(pady=(10, 0))
        self.speed_var = tk.StringVar(value='1000')
        ttk.Spinbox(self.frame, from_=100, to=5000, textvariable=self.speed_var,
                    command=lambda: editor.simulation.update_speed(self.speed_var.get())
                    ).pack(pady=2)

        # Регистрируем колбэк смены состояния авто-симуляции
        editor.simulation._on_auto_state_change = self._on_auto_state_change

    def _on_auto_state_change(self, running: bool):
        if running:
            self.auto_btn_var.set("⏹ Остановить")
        else:
            self.auto_btn_var.set("Авто-симуляция")

    def get_speed_var(self):
        return self.speed_var