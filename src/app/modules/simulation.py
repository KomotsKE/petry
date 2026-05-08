import tkinter as tk
from tkinter import messagebox, simpledialog

from app.modules.petrinetwork import PetriNetwork


class PetriSimulation:
    """Управляет симуляцией. Вся логика enabled/fire — в PetriNetModel."""

    def __init__(self, network: PetriNetwork, root: tk.Tk):
        self.network = network
        self.root = root
        self.animation_speed = 1000

    def get_enabled_transitions(self) -> set:
        model = self.network.build_model()
        return model.enabled_transitions(self.network.get_marking())

    def _pick_by_priority(self, enabled: set) -> str:
        """
        Из множества активных переходов выбирает тот (или те),
        у кого наибольший приоритет. Если остаётся один — возвращает его.
        Если несколько с одинаковым максимальным приоритетом — спрашивает.
        """
        # Собираем (priority, name) для каждого активного перехода
        candidates = []
        for t_name in enabled:
            elem = self.network.transitions[t_name]['element']
            candidates.append((elem.priority, t_name))

        max_priority = max(p for p, _ in candidates)
        top = [name for p, name in candidates if p == max_priority]

        if len(top) == 1:
            return top[0]

        # Несколько переходов с одинаковым максимальным приоритетом
        top_sorted = sorted(top)
        choice = simpledialog.askstring(
            "Выбор перехода",
            f"Активные переходы (приоритет {max_priority}):\n" +
            ", ".join(top_sorted) +
            "\n\nВведите имя перехода для срабатывания:",
            parent=self.root
        )
        return choice if (choice and choice in top) else top_sorted[0]

    def simulation_step(self) -> bool:
        enabled = self.get_enabled_transitions()
        if not enabled:
            return False

        t_name = self._pick_by_priority(enabled)

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
            "Пример: T1, T2, T3",
            parent=self.root
        )
        if not scenario:
            return
        steps = [s.strip() for s in scenario.split(",") if s.strip()]
        if not steps:
            return

        for t_name in steps:
            if t_name not in self.network.transitions:
                messagebox.showwarning("Сценарий", f"Переход '{t_name}' не существует.",
                                       parent=self.root)
                return
            if t_name not in self.get_enabled_transitions():
                messagebox.showwarning("Сценарий",
                                       f"Переход '{t_name}' не разрешён в текущей разметке.",
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
        self.animation_speed = max(100, int(value))