import math
from tkinter import messagebox, simpledialog
from typing import List
import tkinter as tk

from app.modules.elements import Arc, PetriNetElement
from app.modules.petri import ModelArc, PetriNetModel


class PetriNetwork:
    def __init__(self, canvas: tk.Canvas, root: tk.Tk, editor=None):
        self.canvas = canvas
        self.root = root
        self.editor = editor
        self.places = {}
        self.transitions = {}
        self.arcs: List[Arc] = []
        self.real_object_map = {}
        self.initial_marking = {}
        self.selected_element = None
        self.selected_elements = set()
        self.selected_arc = None

        # groups: List[dict] — {'name': str, 'elements': set[str]}
        self.groups: List[dict] = []

        # UI-переменные — заполняются из UIBuilder.post_build()
        self.element_name_var = None
        self.element_type_var = None
        self.tokens_var = None
        self.tokens_spinbox = None
        self.priority_var = None
        self.priority_spinbox = None
        self.label_var = None
        self.label_entry = None
        self.delay_var = None
        self.delay_spinbox = None

    # ── Вспомогательное: обновить UI групп ───────────────────────────────

    def _notify_groups_changed(self):
        if self.editor and hasattr(self.editor, 'groups_tab'):
            self.editor.groups_tab._refresh_groups()

    # ── Поиск ─────────────────────────────────────────────────────────────

    def get_element_at(self, x, y) -> PetriNetElement | None:
        for data in self.transitions.values():
            elem = data['element']
            if abs(x - elem.x) <= elem.width + 2 and abs(y - elem.y) <= elem.height + 2:
                return elem
        for data in self.places.values():
            elem = data['element']
            if math.hypot(x - elem.x, y - elem.y) <= elem.radius + 2:
                return elem
        return None

    # ── Подсветка ─────────────────────────────────────────────────────────

    def clear_highlight(self):
        for data in self.places.values():
            data['element'].clear_highlight()
        for data in self.transitions.values():
            data['element'].clear_highlight()

    def highlight_group(self, group_elements: set, color='orange'):
        self.clear_highlight()
        for name in group_elements:
            if name in self.places:
                self.places[name]['element'].highlight(color)
            elif name in self.transitions:
                self.transitions[name]['element'].highlight(color)

    def highlight_element(self, elem: PetriNetElement, color='red'):
        self.clear_highlight()
        elem.highlight(color)

    # ── Создание элементов ────────────────────────────────────────────────

    def create_place(self, x, y, name=None, tokens=0) -> str:
        if name is None:
            name = f"P{len(self.places) + 1}"
        while name in self.places:
            name = f"P{len(self.places) + 1}"
        element = PetriNetElement(self.canvas, x, y, name, 'place')
        element.draw(tokens)
        self.places[name] = {'element': element, 'tokens': tokens}
        return name

    def create_transition(self, x, y, name=None, priority=1, label="", delay=0) -> str:
        if name is None:
            name = f"T{len(self.transitions) + 1}"
        while name in self.transitions:
            name = f"T{len(self.transitions) + 1}"
        element = PetriNetElement(self.canvas, x, y, name, 'transition')
        element.priority = max(1, int(priority))
        element.label = label or ""
        element.delay = max(0, int(delay))
        element.draw()
        self.transitions[name] = {'element': element}
        return name

    def create_arc(self, source_elem: PetriNetElement, target_elem: PetriNetElement,
                   weight=1, arc_type='normal') -> Arc | None:
        if source_elem.type == target_elem.type:
            return None
        for arc in self.arcs:
            if arc.source == source_elem and arc.target == target_elem:
                return None
        arc = Arc(self.canvas, source_elem, target_elem, weight, arc_type)

        counter = next((a for a in self.arcs
                        if a.source == target_elem and a.target == source_elem), None)
        if counter:
            counter.offset_index = 1
            arc.offset_index = 1
            counter.update_position()

        arc.draw()
        self.arcs.append(arc)
        source_elem.output_arcs.append(arc)
        target_elem.input_arcs.append(arc)
        return arc

    def delete_arc(self, arc: Arc):
        arc.delete()
        if arc in self.arcs:
            self.arcs.remove(arc)
        if arc in arc.source.output_arcs:
            arc.source.output_arcs.remove(arc)
        if arc in arc.target.input_arcs:
            arc.target.input_arcs.remove(arc)

        counter = next((a for a in self.arcs
                        if a.source == arc.target and a.target == arc.source), None)
        if counter:
            counter.offset_index = 0
            counter.update_position()

    def _ask_arc_type(self, initial: str) -> str | None:
        dialog_root = tk.Toplevel(self.root)
        dialog_root.title("Тип дуги")
        dialog_root.geometry("300x150")
        dialog_root.resizable(False, False)
        dialog_root.grab_set()

        from tkinter import ttk
        var = tk.StringVar(value=initial if initial in ("normal", "inhibitor") else "normal")
        result = [None]

        frame = ttk.Frame(dialog_root, padding=10)
        frame.pack(fill="both", expand=True)

        ttk.Label(frame, text="Выберите тип дуги:", font=("Arial", 10)).pack(anchor="w", pady=(0, 10))
        ttk.Radiobutton(frame, text="Normal (обычная)", value="normal", variable=var).pack(anchor="w", pady=5)
        ttk.Radiobutton(frame, text="Inhibitor (ингибиторная)", value="inhibitor", variable=var).pack(anchor="w", pady=5)

        btn_frame = ttk.Frame(frame)
        btn_frame.pack(fill="x", pady=(20, 0))

        def ok():
            result[0] = var.get()
            dialog_root.destroy()

        def cancel():
            dialog_root.destroy()

        ttk.Button(btn_frame, text="OK", command=ok, width=10).pack(side="left", padx=5)
        ttk.Button(btn_frame, text="Отмена", command=cancel, width=10).pack(side="left", padx=5)

        self.root.wait_window(dialog_root)
        return result[0]

    def edit_arc_properties(self, arc: Arc):
        weight = simpledialog.askinteger(
            "Вес дуги", "Введите вес дуги (>=1):",
            initialvalue=arc.weight, minvalue=1, maxvalue=1000,
            parent=self.root
        )
        if weight is None:
            return
        arc_type = self._ask_arc_type(arc.arc_type)
        if not arc_type:
            return
        arc.set_properties(weight=weight, arc_type=arc_type.strip())

    # ── Доменная модель ───────────────────────────────────────────────────

    def build_model(self) -> PetriNetModel:
        return PetriNetModel(
            places=list(self.places.keys()),
            transitions=list(self.transitions.keys()),
            arcs=[
                ModelArc(source=a.source.name, target=a.target.name,
                         weight=a.weight, arc_type=a.arc_type)
                for a in self.arcs
            ]
        )

    # ── Маркировка ────────────────────────────────────────────────────────

    def get_marking(self) -> tuple:
        return tuple(self.places[n]['tokens'] for n in sorted(self.places.keys()))

    def set_marking(self, marking: tuple):
        for i, name in enumerate(sorted(self.places.keys())):
            if i < len(marking):
                self.places[name]['tokens'] = marking[i]
                self.places[name]['element'].redraw_tokens(marking[i])

    def fire_transition(self, t_name: str):
        new_marking = self.build_model().fire(self.get_marking(), t_name)
        self.set_marking(new_marking)

    def save_initial_state(self):
        self.initial_marking = {n: d['tokens'] for n, d in self.places.items()}
        messagebox.showinfo("Сохранено", "Начальное состояние сохранено", parent=self.root)

    def load_initial_state(self):
        if not self.initial_marking:
            messagebox.showwarning("Ошибка", "Сначала сохраните начальное состояние", parent=self.root)
            return
        for name, tokens in self.initial_marking.items():
            if name in self.places:
                self.places[name]['tokens'] = tokens
                self.places[name]['element'].redraw_tokens(tokens)

    def reset_marking(self):
        self.set_marking(tuple(0 for _ in self.places))

    def rename_element(self, elem_type: str, old_name: str, new_name: str) -> bool:
        """Переименовывает элемент и синхронизирует группы. Возвращает True при успехе."""
        if not new_name or new_name == old_name:
            return False

        if new_name in self.places or new_name in self.transitions:
            messagebox.showerror("Ошибка", f"Элемент с именем '{new_name}' уже существует!")
            return False

        data = None
        if elem_type == 'place' and old_name in self.places:
            data = self.places.pop(old_name)
            self.places[new_name] = data
        elif elem_type == 'transition' and old_name in self.transitions:
            data = self.transitions.pop(old_name)
            self.transitions[new_name] = data

        if not data:
            return False

        data['element'].name = new_name

        if old_name in self.initial_marking:
            self.initial_marking[new_name] = self.initial_marking.pop(old_name)

        if old_name in self.real_object_map:
            self.real_object_map[new_name] = self.real_object_map.pop(old_name)

        if data['element'].text_id:
            self.canvas.itemconfig(data['element'].text_id, text=new_name)

        # Обновляем имена в группах
        for g in self.groups:
            if old_name in g['elements']:
                g['elements'].discard(old_name)
                g['elements'].add(new_name)

        self._notify_groups_changed()
        return True

    # ── Обновление свойств из UI ──────────────────────────────────────────

    def update_tokens(self):
        if self.selected_element and self.selected_element.type == 'place':
            name = self.selected_element.name
            try:
                tokens = int(self.tokens_var.get())
                if tokens >= 0:
                    self.places[name]['tokens'] = tokens
                    self.places[name]['element'].redraw_tokens(tokens)
            except ValueError:
                pass

    def update_delay(self, *_):
        if not self.selected_element or self.selected_element.type != 'transition':
            return
        try:
            d = max(0, int(self.delay_var.get()))
            self.selected_element.delay = d
            self.selected_element.redraw_delay()
        except ValueError:
            pass

    def update_priority(self, *_):
        if not self.selected_element or self.selected_element.type != 'transition':
            return
        try:
            p = max(1, int(self.priority_var.get()))
            self.selected_element.priority = p
            self.selected_element.redraw_priority()
        except ValueError:
            pass

    def update_label(self, *_):
        if not self.selected_element or self.selected_element.type != 'transition':
            return
        lbl = self.label_var.get()
        self.selected_element.label = lbl
        self.selected_element.redraw_label()

    # ── Выбор элементов ───────────────────────────────────────────────────

    def toggle_multi_select(self, elem: PetriNetElement):
        """Добавляет/убирает элемент из множественного выделения (Ctrl+клик)."""
        if elem in self.selected_elements:
            self.selected_elements.discard(elem)
            elem.clear_highlight()
        else:
            self.selected_elements.add(elem)
            color = 'blue' if elem.type == 'place' else 'green'
            elem.highlight(color)
        self.selected_element = elem

    def select_arc(self, arc: Arc):
        self.deselect_all()
        self.selected_arc = arc
        if arc.line_id:
            self.canvas.itemconfig(arc.line_id, fill="#1e88e5", width=3)
        self.element_name_var.set(f"{arc.source.name}→{arc.target.name}")
        self.element_type_var.set("Дуга")
        self.tokens_var.set("0")
        self.tokens_spinbox.configure(state='disabled')
        self.priority_var.set("1")
        self.priority_spinbox.configure(state='disabled')
        self.label_var.set("")
        self.label_entry.configure(state='disabled')
        self.delay_var.set("0")
        self.delay_spinbox.configure(state='disabled')

    def select_element(self, elem_type, name):
        self.deselect_all()
        if elem_type == 'place':
            data = self.places[name]
            elem = data['element']
            self.selected_element = elem
            self.selected_elements = {elem}
            self.highlight_element(elem, 'blue')
            self.element_name_var.set(name)
            self.element_type_var.set('Позиция')
            self.tokens_var.set(str(data['tokens']))
            self.tokens_spinbox.configure(state='normal')
            self.priority_var.set("1")
            self.priority_spinbox.configure(state='disabled')
            self.label_var.set("")
            self.label_entry.configure(state='disabled')
            self.delay_var.set("0")
            self.delay_spinbox.configure(state='disabled')
        else:
            data = self.transitions[name]
            elem = data['element']
            self.selected_element = elem
            self.selected_elements = {elem}
            self.highlight_element(elem, 'green')
            self.element_name_var.set(name)
            self.element_type_var.set('Переход')
            self.tokens_var.set('0')
            self.tokens_spinbox.configure(state='disabled')
            self.priority_var.set(str(elem.priority))
            self.priority_spinbox.configure(state='normal')
            self.label_var.set(elem.label)
            self.label_entry.configure(state='normal')
            self.delay_var.set(str(elem.delay))
            self.delay_spinbox.configure(state='normal')

    def deselect_all(self):
        self.selected_element = None
        self.selected_elements = set()
        if getattr(self, "selected_arc", None) is not None:
            a = self.selected_arc
            self.selected_arc = None
            if a and a.line_id:
                a.update_position()
        self.clear_highlight()
        self.element_name_var.set('')
        self.element_type_var.set('')
        self.tokens_var.set('0')
        self.tokens_spinbox.configure(state='disabled')
        self.priority_var.set('1')
        self.priority_spinbox.configure(state='disabled')
        self.label_var.set('')
        self.label_entry.configure(state='disabled')
        self.delay_var.set('0')
        self.delay_spinbox.configure(state='disabled')

    def delete_selected(self, event=None):
        if self.selected_arc is not None:
            self.delete_arc(self.selected_arc)
            self.selected_arc = None
            self.deselect_all()
            return

        to_delete = list(self.selected_elements) or (
            [self.selected_element] if self.selected_element else []
        )
        for elem in to_delete:
            name = elem.name
            for arc in list(set(elem.input_arcs) | set(elem.output_arcs)):
                if arc in self.arcs:
                    self.delete_arc(arc)
            elem.delete_from_canvas()
            if elem.type == 'place':
                self.places.pop(name, None)
            else:
                self.transitions.pop(name, None)
            self.real_object_map.pop(name, None)
            self.initial_marking.pop(name, None)
            # Убираем из всех групп
            for g in self.groups:
                g['elements'].discard(name)

        self.deselect_all()
        self._notify_groups_changed()

    # ── Управление группами ───────────────────────────────────────────────

    def get_all_element_names(self) -> set:
        return set(self.places.keys()) | set(self.transitions.keys())

    def add_group(self, name: str, elements: set) -> bool:
        name = name.strip()
        if not name:
            return False
        if any(g['name'] == name for g in self.groups):
            messagebox.showerror("Ошибка", f"Группа '{name}' уже существует!", parent=self.root)
            return False
        all_elements = self.get_all_element_names()
        invalid = elements - all_elements
        if invalid:
            messagebox.showerror(
                "Ошибка",
                f"Элементы не найдены в сети: {', '.join(sorted(invalid))}",
                parent=self.root
            )
            return False
        self.groups.append({'name': name, 'elements': set(elements)})
        self._notify_groups_changed()
        return True

    def remove_group(self, name: str):
        self.groups = [g for g in self.groups if g['name'] != name]
        self._notify_groups_changed()

    def rename_group(self, old_name: str, new_name: str) -> bool:
        new_name = new_name.strip()
        if not new_name or old_name == new_name:
            return False
        if any(g['name'] == new_name for g in self.groups):
            messagebox.showerror("Ошибка", f"Группа '{new_name}' уже существует!", parent=self.root)
            return False
        for g in self.groups:
            if g['name'] == old_name:
                g['name'] = new_name
                self._notify_groups_changed()
                return True
        return False

    def add_elements_to_group(self, group_name: str, elements: set) -> bool:
        all_elements = self.get_all_element_names()
        invalid = elements - all_elements
        if invalid:
            messagebox.showerror(
                "Ошибка",
                f"Элементы не найдены: {', '.join(sorted(invalid))}",
                parent=self.root
            )
            return False
        for g in self.groups:
            if g['name'] == group_name:
                g['elements'].update(elements)
                self._notify_groups_changed()
                return True
        return False

    def remove_element_from_group(self, group_name: str, element_name: str) -> bool:
        for g in self.groups:
            if g['name'] == group_name:
                if element_name in g['elements']:
                    g['elements'].discard(element_name)
                    self._notify_groups_changed()
                    return True
        return False

    def get_groups(self) -> list:
        return list(self.groups)

    def get_element_groups(self, element_name: str) -> list:
        """Возвращает список групп, в которые входит элемент."""
        return [g['name'] for g in self.groups if element_name in g['elements']]