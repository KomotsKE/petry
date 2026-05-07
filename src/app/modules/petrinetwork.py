import json
import math
from tkinter import messagebox, simpledialog, ttk, filedialog
from typing import List
import tkinter as tk

from app.modules.elements import Arc, PetriNetElement
from app.modules.petri import ModelArc, PetriNetModel


class PetriNetwork:
    def __init__(self, canvas: tk.Canvas, root: tk.Tk):
        self.canvas = canvas
        self.root = root
        self.places = {}       # name -> {'element': PetriNetElement, 'tokens': int}
        self.transitions = {}  # name -> {'element': PetriNetElement}
        self.arcs: List[Arc] = []
        self.real_object_map = {}
        self.initial_marking = {}
        self.selected_element = None
        self.selected_elements = set()
        self.selected_arc = None
        
        self.element_name_var = None
        self.element_type_var = None
        self.tokens_var = None
        self.tokens_spinbox = None

    # ============ Поиск элементов ============

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

    # ============ Подсветка ============

    def clear_highlight(self):
        for data in self.places.values():
            data['element'].clear_highlight()
        for data in self.transitions.values():
            data['element'].clear_highlight()

    def highlight_element(self, elem: PetriNetElement, color='red'):
        self.clear_highlight()
        elem.highlight(color)

    # ============ Создание элементов ============

    def create_place(self, x, y, name=None, tokens=0) -> str:
        if name is None:
            name = f"P{len(self.places) + 1}"
        while name in self.places:
            name = f"P{len(self.places) + 1}"
        element = PetriNetElement(self.canvas, x, y, name, 'place')
        element.draw(tokens)
        self.places[name] = {'element': element, 'tokens': tokens}
        return name

    def create_transition(self, x, y, name=None) -> str:
        if name is None:
            name = f"T{len(self.transitions) + 1}"
        while name in self.transitions:
            name = f"T{len(self.transitions) + 1}"
        element = PetriNetElement(self.canvas, x, y, name, 'transition')
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

    def edit_arc_properties(self, arc: Arc):
        weight = simpledialog.askinteger(
            "Вес дуги", "Введите вес дуги (>=1):",
            initialvalue=arc.weight, minvalue=1, maxvalue=1000,
            parent=self.root
        )
        if weight is None:
            return
        arc_type = simpledialog.askstring(
            "Тип дуги", "Введите тип: normal или inhibitor",
            initialvalue=arc.arc_type,
            parent=self.root
        )
        if not arc_type:
            return
        arc.set_properties(weight=weight, arc_type=arc_type.strip())

    # ============ Доменная модель ============

    def build_model(self) -> PetriNetModel:
        """Строит чистую доменную модель из текущего состояния сети.
        Используется для всей логики — fire, enabled, reachability."""
        return PetriNetModel(
            places=list(self.places.keys()),
            transitions=list(self.transitions.keys()),
            arcs=[
                ModelArc(source=a.source.name, target=a.target.name,
                         weight=a.weight, arc_type=a.arc_type)
                for a in self.arcs
            ]
        )

    # ============ Маркировка ============

    def get_marking(self) -> tuple:
        return tuple(self.places[n]['tokens'] for n in sorted(self.places.keys()))

    def set_marking(self, marking: tuple):
        for i, name in enumerate(sorted(self.places.keys())):
            if i < len(marking):
                self.places[name]['tokens'] = marking[i]
                self.places[name]['element'].redraw_tokens(marking[i])

    def fire_transition(self, t_name: str):
        """Делегирует логику в PetriNetModel — дублирования нет."""
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
        """
        Переименовывает элемент.
        Возвращает True если успешно, False если имя занято или элемент не найден.
        """
        if not new_name or new_name == old_name:
            return False

        # Проверка уникальности
        if new_name in self.places or new_name in self.transitions:
            messagebox.showerror("Ошибка", f"Элемент с именем '{new_name}' уже существует!")
            return False

        data = None
        if elem_type == 'place' and old_name in self.places:
            data = self.places[old_name]
        elif elem_type == 'transition' and old_name in self.transitions:
            data = self.transitions[old_name]

        if not data:
            return False

        # Обновляем словари
        if elem_type == 'place':
            del self.places[old_name]
            self.places[new_name] = data
        else:
            del self.transitions[old_name]
            self.transitions[new_name] = data

        # Обновляем имя элемента
        data['element'].name = new_name

        # Обновляем дуги
        for arc in self.arcs:
            if arc['source'] == old_name:
                arc['source'] = new_name
            if arc['target'] == old_name:
                arc['target'] = new_name

        # Обновляем начальную разметку
        if old_name in self.initial_marking:
            val = self.initial_marking.pop(old_name)
            self.initial_marking[new_name] = val

        # Обновляем real_object_map если есть
        if old_name in self.real_object_map:
            self.real_object_map[new_name] = self.real_object_map.pop(old_name)

        # Обновляем текст на холсте
        if data['element'].text_id:
            self.canvas.itemconfig(data['element'].text_id, text=new_name)

        return True

    
    def update_tokens(self):
        if self.selected_element and self.selected_element.type == 'place':
            name = self.selected_element.name
            try:
                tokens = int(self.tokens_var.get())
                if 0 <= tokens <= 10:
                    self.places[name]['tokens'] = tokens
                    self.places[name]['element'].redraw_tokens(tokens)
            except ValueError:
                pass
# ============ Выбор элементов ============
    def select_arc(self, arc: Arc):
        self.deselect_all()
        self.selected_arc = arc
        if arc.line_id:
            self.canvas.itemconfig(arc.line_id, fill="#1e88e5", width=3)
        self.element_name_var.set(f"{arc.source.name}→{arc.target.name}")
        self.element_type_var.set("Дуга")
        self.tokens_var.set("0")
        self.tokens_spinbox.configure(state='disabled')

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
            if elem.type == 'place':
                elem.redraw_tokens(0)
            for cid in elem.canvas_ids:
                self.canvas.delete(cid)
            self.canvas.delete(elem.text_id)
            if elem.type == 'place':
                del self.places[name]
            else:
                del self.transitions[name]
            self.real_object_map.pop(name, None)
            self.initial_marking.pop(name, None)

        self.deselect_all()
            
    