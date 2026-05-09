import tkinter as tk
from tkinter import messagebox, simpledialog

from app.modules.petrinetwork import PetriNetwork


class PetriSimulation:
    """
    Управляет симуляцией. Задержка — двухфазная:
      Фаза 1 (немедленно): токены с входных позиций снимаются, переход становится оранжевым.
      Фаза 2 (через delay мс): токены добавляются на выходные позиции, переход возвращается в норму.
    """

    def __init__(self, network: PetriNetwork, root: tk.Tk):
        self.network = network
        self.root = root
        self.animation_speed = 1000
        # t_name -> after_id; позволяет отслеживать ожидающие переходы
        self._pending: dict = {}

    # ── Вспомогательные ───────────────────────────────────────────────────

    def get_enabled_transitions(self) -> set:
        model = self.network.build_model()
        return model.enabled_transitions(self.network.get_marking())

    def _pick_by_priority(self, enabled: set) -> str:
        """Максимальный приоритет; при равенстве — диалог выбора."""
        candidates = [(self.network.transitions[t]['element'].priority, t) for t in enabled]
        max_p = max(p for p, _ in candidates)
        top = sorted(name for p, name in candidates if p == max_p)
        if len(top) == 1:
            return top[0]
        choice = simpledialog.askstring(
            "Выбор перехода",
            f"Активные переходы (приоритет {max_p}):\n{', '.join(top)}"
            "\n\nВведите имя перехода:",
            parent=self.root
        )
        return choice if (choice and choice in top) else top[0]

    # ── Срабатывание ──────────────────────────────────────────────────────

    def _highlight_flash(self, elem, color='red', ms=200):
        """Подсвечивает элемент на ms миллисекунд синхронно (для мгновенных переходов)."""
        elem.highlight(color)
        self.root.update()
        # Настоящий sleep через вложенный event loop
        done = tk.BooleanVar(value=False)
        self.root.after(ms, lambda: done.set(True))
        self.root.wait_variable(done)

    def _fire_instant(self, t_name: str):
        """Мгновенное срабатывание с короткой визуальной вспышкой."""
        elem = self.network.transitions[t_name]['element']
        self._highlight_flash(elem, 'red', 200)
        self.network.fire_transition(t_name)
        elem.clear_highlight()

    def _start_delayed_fire(self, t_name: str):
        """
        Фаза 1: снимаем токены, окрашиваем переход в оранжевый,
        планируем фазу 2 через delay мс.
        """
        model = self.network.build_model()
        intermediate = model.consume(self.network.get_marking(), t_name)
        self.network.set_marking(intermediate)

        elem = self.network.transitions[t_name]['element']
        elem.show_pending()
        self.root.update()   # ← обязательно, иначе оранжевый не отрисуется

        after_id = self.root.after(
            elem.delay,
            lambda name=t_name: self._complete_delayed_fire(name)
        )
        self._pending[t_name] = after_id

    def _complete_delayed_fire(self, t_name: str):
        """Фаза 2: добавляем выходные токены, снимаем оранжевый цвет."""
        self._pending.pop(t_name, None)

        model = self.network.build_model()
        final = model.produce(self.network.get_marking(), t_name)
        self.network.set_marking(final)

        elem = self.network.transitions[t_name]['element']
        elem.clear_pending()
        self.root.update()

    # ── Публичный API ─────────────────────────────────────────────────────

    def simulation_step(self) -> bool:
        """Один шаг вперёд. Для delayed-переходов возвращает True сразу после фазы 1."""
        enabled = self.get_enabled_transitions()
        if not enabled:
            messagebox.showinfo("Симуляция", "Нет активных переходов.", parent=self.root)
            return False

        t_name = self._pick_by_priority(enabled)
        elem = self.network.transitions[t_name]['element']

        if elem.delay <= 0:
            self._fire_instant(t_name)
        else:
            self._start_delayed_fire(t_name)

        return True

    def play_scenario(self):
        scenario = simpledialog.askstring(
            "Сценарий",
            "Введите последовательность переходов через запятую.\nПример: T1, T2, T3",
            parent=self.root
        )
        if not scenario:
            return
        steps = [s.strip() for s in scenario.split(",") if s.strip()]
        if not steps:
            return

        def run_step(index):
            if index >= len(steps):
                return
            t_name = steps[index]
            if t_name not in self.network.transitions:
                messagebox.showwarning("Сценарий", f"Переход '{t_name}' не существует.",
                                       parent=self.root)
                return
            if t_name not in self.get_enabled_transitions():
                messagebox.showwarning("Сценарий",
                                       f"Переход '{t_name}' не разрешён в текущей разметке.",
                                       parent=self.root)
                return

            elem = self.network.transitions[t_name]['element']
            if elem.delay <= 0:
                self._fire_instant(t_name)
                self.root.after(150, lambda: run_step(index + 1))
            else:
                self._start_delayed_fire(t_name)
                # Следующий шаг — после завершения задержки
                self.root.after(elem.delay + 50, lambda: run_step(index + 1))

        run_step(0)

    def auto_simulation(self):
        def run_step():
            enabled = self.get_enabled_transitions()
            if not enabled:
                return
            t_name = self._pick_by_priority(enabled)
            elem = self.network.transitions[t_name]['element']

            if elem.delay <= 0:
                self._fire_instant(t_name)
                self.root.after(self.animation_speed, run_step)
            else:
                self._start_delayed_fire(t_name)
                # Следующий шаг — после завершения задержки + пауза
                self.root.after(elem.delay + self.animation_speed, run_step)

        run_step()

    def update_speed(self, value=None):
        try:
            self.animation_speed = max(100, int(value))
        except (TypeError, ValueError):
            pass