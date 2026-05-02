from tkinter import messagebox, simpledialog
from typing import TYPE_CHECKING

from src.app.modules.elements import PetriNetElement


class PetriSimulation:
    def __init__(self, canvas_manager):
        self.animation_speed = 1000
        self.canvas_manager = canvas_manager
    
    def get_enabled_transitions(self):
        enabled = set()
        for t_name, t_data in self.canvas_manager.petriNetwork.transitions.items():
            elem: PetriNetElement = t_data['element']
            enabled_flag = True
            for arc in elem.input_arcs:
                if arc.arc_type == 'inhibitor':
                    if self.canvas_manager.petriNetwork.places[arc.source.name]['tokens'] > 0:
                        enabled_flag = False
                        break
                else:
                    if self.canvas_manager.petriNetwork.places[arc.source.name]['tokens'] < arc.weight:
                        enabled_flag = False
                        break
            if enabled_flag:
                enabled.add(t_name)
        return enabled
    
    def simulation_step(self):
        enabled = self.get_enabled_transitions()
        if not enabled:
            return False
        
        t_name = None
        enabled_sorted = sorted(enabled)
        if len(enabled_sorted) == 1:
            t_name = enabled_sorted[0]
        else:
            choice = simpledialog.askstring(
                "Выбор перехода",
                "Разрешенные переходы:\n" + ", ".join(enabled_sorted) + "\n\nВведите имя перехода для срабатывания:"
            )
            if choice and choice in enabled:
                t_name = choice
            else:
                t_name = enabled_sorted[0]
        
        self.canvas_manager.petriNetwork.highlight_element(self.canvas_manager.petriNetwork.transitions[t_name]['element'], 'red')
        self.canvas_manager.root.update()
        self.canvas_manager.root.after(200)
        
        self.canvas_manager.petriNetwork.fire_transition(t_name)
        
        self.canvas_manager.petriNetwork.clear_highlight()
        return True
    
    def play_scenario(self):
        scenario = simpledialog.askstring(
            "Сценарий",
            "Введите последовательность переходов через запятую.\nПример: Обработка_С1, Перемещение, Обработка_С2"
        )
        if not scenario:
            return
        steps = [s.strip() for s in scenario.split(",") if s.strip()]
        if not steps:
            return

        for t_name in steps:
            if t_name not in self.canvas_manager.petriNetwork.transitions:
                messagebox.showwarning("Сценарий", f"Переход {t_name} не существует.")
                return
            enabled = self.get_enabled_transitions()
            if t_name not in enabled:
                messagebox.showwarning("Сценарий", f"Переход {t_name} не разрешен в текущей разметке.")
                return
            self.canvas_manager.petriNetwork.highlight_element(self.canvas_manager.petriNetwork.transitions[t_name]['element'], 'red')
            self.canvas_manager.root.update()
            self.canvas_manager.root.after(150)
            self.canvas_manager.petriNetwork.fire_transition(t_name)
            self.canvas_manager.petriNetwork.clear_highlight()
            
    def auto_simulation(self):
        def run_step():
            if self.simulation_step():
                self.canvas_manager.root.after(self.animation_speed, run_step)
        run_step()
        
    def update_speed(self):
        try:
            self.animation_speed = int(self.canvas_manager.speed_var.get())
        except ValueError:
            pass