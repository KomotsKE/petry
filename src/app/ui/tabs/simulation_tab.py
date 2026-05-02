import tkinter as tk
from tkinter import ttk

class SimulationTab:
    def __init__(self, parent, editor):
        self.editor = editor
        self.frame = ttk.Frame(parent)
        parent.add(self.frame, text="Симуляция")

        ttk.Label(self.frame, text="Управление:", font=('Arial', 10, 'bold')).pack(pady=5)
        ttk.Button(self.frame, text="Шаг вперед", command=editor.simulation.simulation_step).pack(fill='x', padx=10, pady=2)
        ttk.Button(self.frame, text="Авто-симуляция", command=editor.simulation.auto_simulation).pack(fill='x', padx=10, pady=2)
        ttk.Button(self.frame, text="Проиграть сценарий...", command=editor.simulation.play_scenario).pack(fill='x', padx=10, pady=2)

        ttk.Label(self.frame, text="Скорость (мс):").pack(pady=(10,0))
        self.speed_var = tk.StringVar(value='1000')
        ttk.Spinbox(self.frame, from_=100, to=5000, textvariable=self.speed_var,
                    command=editor.simulation.update_speed).pack(pady=2)
        
    def get_speed_var(self):
        return self.speed_var 