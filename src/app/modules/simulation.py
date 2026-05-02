import tkinter as tk
from tkinter import messagebox, simpledialog
from typing import Callable

from app.modules.petrinetwork import PetriNetwork


class PetriSimulation:
    """Управляет симуляцией. Знает только о PetriNetwork и root — не об editor."""

    def __init__(self, network: PetriNetwork, root: tk.Tk):
        self.network = network
        self.root = root
        self.animation_speed = 1000

    # ============ Логика ============

    def get_enabled_transitions(self) -> set:
        enabled = set()
        for t_name, t_data in self.network.transitions.items():
            elem = t_data['element']
            ok = True
            for arc in elem.input_arcs:
                tokens = self.network.places[arc.source.name]['tokens']
                if arc.arc_type == 'inhibitor':
                    if tokens > 0:
                        ok = False
                        break
                else:
                    if tokens < arc.weight:
                        ok = False
                        break
            if ok:
                enabled.add(t_name)
        return enabled

    def simulation_step(self) -> bool:
        enabled = self.get_enabled_transitions()
        if not enabled:
            return False

        enabled_sorted = sorted(enabled)
        if len(enabled_sorted) == 1:
            t_name = enabled_sorted[0]
        else:
            choice = simpledialog.askstring(
                "Выбор перехода",
                "Разрешенные переходы:\n" + ", ".join(enabled_sorted) +
                "\n\nВведите имя перехода для срабатывания:",
                parent=self.root
            )
            t_name = choice if (choice and choice in enabled) else enabled_sorted[0]

        self.network.highlight_element(
            self.network.transitions[t_name]['element'], 'red'
        )
        self.root.update()
        self.root.after(200)

        self.network.fire_transition(t_name)
        self.network.clear_highlight()
        return True

    def play_scenario(self):
        scenario = simpledialog.askstring(
            "Сценарий",
            "Введите последовательность переходов через запятую.\n"
            "Пример: Обработка_С1, Перемещение, Обработка_С2",
            parent=self.root
        )
        if not scenario:
            return
        steps = [s.strip() for s in scenario.split(",") if s.strip()]
        if not steps:
            return

        for t_name in steps:
            if t_name not in self.network.transitions:
                messagebox.showwarning("Сценарий", f"Переход {t_name} не существует.", parent=self.root)
                return
            if t_name not in self.get_enabled_transitions():
                messagebox.showwarning("Сценарий",
                                       f"Переход {t_name} не разрешен в текущей разметке.",
                                       parent=self.root)
                return
            self.network.highlight_element(
                self.network.transitions[t_name]['element'], 'red'
            )
            self.root.update()
            self.root.after(150)
            self.network.fire_transition(t_name)
            self.network.clear_highlight()

    def auto_simulation(self):
        def run_step():
            if self.simulation_step():
                self.root.after(self.animation_speed, run_step)
        run_step()

    def update_speed(self, value: int):
        """Вызывается из UI при изменении спиннера скорости."""
        self.animation_speed = max(100, int(value))