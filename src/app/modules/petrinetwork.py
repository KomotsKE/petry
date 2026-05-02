import json
import math
from tkinter import messagebox, simpledialog, ttk
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
        """Снимает подсветку со всех элементов сети.
        Примечание: очистка arc_source — ответственность EditorEventHandlers."""
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

    # ============ Разметка ============

    def fire_transition(self, t_name: str):
        elem: PetriNetElement = self.transitions[t_name]['element']
        for arc in elem.input_arcs:
            if arc.arc_type == 'normal':
                src = arc.source.name
                self.places[src]['tokens'] -= arc.weight
                self.places[src]['element'].redraw_tokens(self.places[src]['tokens'])
        for arc in elem.output_arcs:
            if arc.arc_type == 'normal':
                tgt = arc.target.name
                self.places[tgt]['tokens'] += arc.weight
                self.places[tgt]['element'].redraw_tokens(self.places[tgt]['tokens'])

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
        for name in self.places:
            self.places[name]['tokens'] = 0
            self.places[name]['element'].redraw_tokens(0)

    def get_current_marking_tuple(self) -> tuple:
        return tuple(self.places[n]['tokens'] for n in sorted(self.places.keys()))

    def set_marking_from_tuple(self, marking_tuple: tuple):
        for i, name in enumerate(sorted(self.places.keys())):
            if i < len(marking_tuple):
                self.places[name]['tokens'] = marking_tuple[i]
                self.places[name]['element'].redraw_tokens(marking_tuple[i])

    # ============ Анализ ============

    def build_model_from_editor(self) -> PetriNetModel:
        places = list(self.places.keys())
        transitions = list(self.transitions.keys())
        arcs = [
            ModelArc(source=a.source.name, target=a.target.name,
                     weight=a.weight, arc_type=a.arc_type)
            for a in self.arcs
        ]
        return PetriNetModel(places=places, transitions=transitions, arcs=arcs)

    def build_reachability_graph(self):
        current_marking = self.get_current_marking_tuple()
        model = self.build_model_from_editor()
        visited, edges, enabled_cache = model.reachability_graph(current_marking, max_states=5000)
        self.set_marking_from_tuple(current_marking)
        return visited, edges, enabled_cache

    def check_liveness(self):
        current_marking = self.get_current_marking_tuple()
        visited, edges, enabled_cache = self.build_reachability_graph()
        model = self.build_model_from_editor()
        live_map = model.liveness_from_reachability(visited, edges, enabled_cache)

        is_net_live = all(bool(live_map.get(t, False)) for t in self.transitions)
        self.set_marking_from_tuple(current_marking)

        lines = [
            f"{'✓' if live_map.get(t, False) else '✗'}  {t}"
            for t in sorted(self.transitions.keys())
        ]
        status = "Сеть живая ✓" if is_net_live else "Сеть НЕ живая ✗"
        messagebox.showinfo("Живость", status + "\n\n" + "\n".join(lines), parent=self.root)
        return is_net_live

    def show_reachability_window(self):
        model = self.build_model_from_editor()
        current_marking = self.get_current_marking_tuple()
        visited, edges, enabled_cache = model.reachability_graph(current_marking, max_states=5000)

        win = tk.Toplevel(self.root)  # ← был баг: self.editorroot
        win.title("Граф достижимости")
        win.geometry("900x600")

        nb = ttk.Notebook(win)
        nb.pack(fill="both", expand=True)

        # Вкладка состояний
        tab_states = ttk.Frame(nb)
        nb.add(tab_states, text="Состояния")

        cols = ["id"] + sorted(self.places.keys())
        tv = ttk.Treeview(tab_states, columns=cols, show="headings")
        tv.pack(side="left", fill="both", expand=True)
        vs = ttk.Scrollbar(tab_states, orient="vertical", command=tv.yview)
        tv.configure(yscrollcommand=vs.set)
        vs.pack(side="right", fill="y")

        tv.heading("id", text="M#")
        tv.column("id", width=60, anchor="center")
        for p in sorted(self.places.keys()):
            tv.heading(p, text=p)
            tv.column(p, width=120, anchor="center")

        visited_sorted = sorted(visited)
        for i, m in enumerate(visited_sorted):
            row = [f"M{i}"] + [m[j] for j in range(len(sorted(self.places.keys())))]
            tv.insert("", "end", values=row)

        # Вкладка переходов
        tab_edges = ttk.Frame(nb)
        nb.add(tab_edges, text="Переходы")

        tv2 = ttk.Treeview(tab_edges, columns=("from", "t", "to"), show="headings")
        tv2.pack(side="left", fill="both", expand=True)
        vs2 = ttk.Scrollbar(tab_edges, orient="vertical", command=tv2.yview)
        tv2.configure(yscrollcommand=vs2.set)
        vs2.pack(side="right", fill="y")
        tv2.heading("from", text="От")
        tv2.heading("t", text="Переход")
        tv2.heading("to", text="К")
        tv2.column("from", width=100, anchor="center")
        tv2.column("t", width=200, anchor="w")
        tv2.column("to", width=100, anchor="center")

        idx = {m: i for i, m in enumerate(visited_sorted)}
        for a, t, b in edges:
            tv2.insert("", "end", values=(f"M{idx[a]}", t, f"M{idx[b]}"))

        ttk.Label(win,
                  text=f"Состояний: {len(visited)} | Рёбер: {len(edges)} | Ограничение: 5000"
                  ).pack(side="bottom", fill="x")

    # ============ Сохранение / Загрузка ============

    def get_network_data(self) -> dict:
        return {
            'places': {
                name: {'x': d['element'].x, 'y': d['element'].y, 'tokens': d['tokens']}
                for name, d in self.places.items()
            },
            'transitions': {
                name: {'x': d['element'].x, 'y': d['element'].y}
                for name, d in self.transitions.items()
            },
            'arcs': [
                {'source': a.source.name, 'target': a.target.name,
                 'weight': a.weight, 'type': a.arc_type}
                for a in self.arcs
            ],
            'real_objects': self.real_object_map,
            'initial_marking': self.initial_marking,
        }

    def load_network_data(self, data: dict):
        self.canvas.delete('all')
        self.places.clear()
        self.transitions.clear()
        self.arcs.clear()
        self.real_object_map = data.get('real_objects', {})
        self.initial_marking = data.get('initial_marking', {})

        element_map = {}
        for name, pdata in data['places'].items():
            self.create_place(pdata['x'], pdata['y'], name, pdata['tokens'])
            element_map[name] = self.places[name]['element']
        for name, tdata in data['transitions'].items():
            self.create_transition(tdata['x'], tdata['y'], name)
            element_map[name] = self.transitions[name]['element']
        for arc_data in data['arcs']:
            source = element_map.get(arc_data['source'])
            target = element_map.get(arc_data['target'])
            if source and target:
                self.create_arc(source, target,
                                arc_data.get('weight', 1),
                                arc_data.get('type', 'normal'))

    def save_to_file(self):
        filename = tk.filedialog.asksaveasfilename(
            defaultextension=".json",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")],
            parent=self.root
        )
        if filename:
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(self.get_network_data(), f, ensure_ascii=False, indent=2)
            messagebox.showinfo("Сохранено", f"Сеть сохранена в {filename}", parent=self.root)

    def load_from_file(self):
        filename = tk.filedialog.askopenfilename(
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")],
            parent=self.root
        )
        if filename:
            with open(filename, 'r', encoding='utf-8') as f:
                data = json.load(f)
            self.load_network_data(data)
            messagebox.showinfo("Загружено", f"Сеть загружена из {filename}", parent=self.root)

    def rename_element(self, elem_type: str, old_name: str):
        new_name = simpledialog.askstring(
            "Переименование", f"Новое имя для '{old_name}':",
            initialvalue=old_name, parent=self.root
        )
        if not new_name:
            return
        new_name = new_name.strip()
        if not new_name or new_name == old_name:
            return

        if elem_type == 'place':
            if new_name in self.places:
                messagebox.showwarning("Имя", "Позиция с таким именем уже существует.", parent=self.root)
                return
            data = self.places.pop(old_name)
            data['element'].name = new_name
            self.places[new_name] = data
            self.canvas.itemconfig(data['element'].text_id, text=new_name)
        else:
            if new_name in self.transitions:
                messagebox.showwarning("Имя", "Переход с таким именем уже существует.", parent=self.root)
                return
            data = self.transitions.pop(old_name)
            data['element'].name = new_name
            self.transitions[new_name] = data
            self.canvas.itemconfig(data['element'].text_id, text=new_name)

        if old_name in self.real_object_map:
            self.real_object_map[new_name] = self.real_object_map.pop(old_name)
        if old_name in self.initial_marking:
            self.initial_marking[new_name] = self.initial_marking.pop(old_name)

        return new_name  # вернём новое имя, чтобы caller мог обновить selection