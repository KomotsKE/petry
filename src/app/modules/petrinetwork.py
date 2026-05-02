import json
import math
from tkinter import messagebox, simpledialog, ttk
from typing import TYPE_CHECKING, List
import tkinter as tk


from src.app.modules.elements import Arc, PetriNetElement
from src.app.modules.petri import ModelArc, PetriNetModel

class PetriNetwork:
    def __init__(self, canvas_manager):
        # Модель данных
        self.canvas_manager = canvas_manager
        self.canvas = canvas_manager.canvas
        self.places = {}  # name -> {'element': PetriNetElement, 'tokens': int}
        self.transitions = {}  # name -> {'element': PetriNetElement}
        self.arcs = []  # список всех дуг
        self.real_object_map = {}  # привязка к реальным объектам
        self.initial_marking = {}  # сохраненное начальное состояние
        
    def get_element_at(self, x, y):
        for data in self.transitions.values():
            elem = data['element']
            if abs(x - elem.x) <= elem.width + 2 and abs(y - elem.y) <= elem.height + 2:
                return elem
        for data in self.places.values():
            elem = data['element']
            if math.hypot(x - elem.x, y - elem.y) <= elem.radius + 2:
                return elem
        return None
    
    def clear_highlight(self):
        for data in self.places.values():
            data['element'].clear_highlight()
        for data in self.transitions.values():
            data['element'].clear_highlight()
        if self.canvas_manager.arc_source:
            self.canvas_manager.arc_source.clear_highlight()
            self.canvas_manager.arc_source = None
    
    def highlight_element(self, elem, color='red'):
        self.clear_highlight()
        elem.highlight(color)
    
    def create_place(self, x, y, name=None, tokens=0):
        if name is None:
            name = f"P{len(self.places) + 1}"
        while name in self.places:
            name = f"P{len(self.places) + 1}"
        element = PetriNetElement(self.canvas, x, y, name, 'place')
        element.draw(tokens)
        self.places[name] = {'element': element, 'tokens': tokens}
        for cid in element.canvas_ids + [element.text_id]:
            self.canvas.tag_bind(cid, '<Button-1>',
                                lambda e, n=name: self.canvas_manager.on_element_button1('place', n, e))
            self.canvas.tag_bind(cid, '<Button-3>',
                                lambda e, n=name: self.canvas_manager.on_right_click(e, 'place', n))
        return name
    
    def create_transition(self, x, y, name=None):
        if name is None:
            name = f"T{len(self.transitions) + 1}"
        while name in self.transitions:
            name = f"T{len(self.transitions) + 1}"
        element = PetriNetElement(self.canvas, x, y, name, 'transition')
        element.draw()
        self.transitions[name] = {'element': element}
        for cid in element.canvas_ids + [element.text_id]:
            self.canvas.tag_bind(cid, '<Button-1>',
                                lambda e, n=name: self.canvas_manager.on_element_button1('transition', n, e))
            self.canvas.tag_bind(cid, '<Button-3>',
                                lambda e, n=name: self.canvas_manager.on_right_click(e, 'transition', n))
        return name
    
    def create_arc(self, source_elem: PetriNetElement, target_elem: PetriNetElement, weight=1, arc_type='normal'):
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
        weight = simpledialog.askinteger("Вес дуги", "Введите вес дуги (>=1):", initialvalue=arc.weight, minvalue=1, maxvalue=1000)
        if weight is None:
            return
        arc_type = simpledialog.askstring("Тип дуги", "Введите тип: normal или inhibitor", initialvalue=arc.arc_type)
        if not arc_type:
            return
        arc.set_properties(weight=weight, arc_type=arc_type.strip())

    def load_network_data(self, data):
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
                self.create_arc(source, target, arc_data.get('weight', 1), 
                               arc_data.get('type', 'normal'))
    
        
    def fire_transition(self, t_name):
        t_data = self.transitions[t_name]
        elem: PetriNetElement = t_data['element']
        
        for arc in elem.input_arcs:
            if arc.arc_type == 'normal':
                source_name = arc.source.name
                self.places[source_name]['tokens'] -= arc.weight
                self.places[source_name]['element'].redraw_tokens(self.places[source_name]['tokens'])
        
        for arc in elem.output_arcs:
            if arc.arc_type == 'normal':
                target_name = arc.target.name
                self.places[target_name]['tokens'] += arc.weight
                self.places[target_name]['element'].redraw_tokens(self.places[target_name]['tokens'])
    
    def save_initial_state(self):
        self.initial_marking = {}
        for name, data in self.places.items():
            self.initial_marking[name] = data['tokens']
        messagebox.showinfo("Сохранено", "Начальное состояние сохранено")
        
    def load_initial_state(self):
        if not self.initial_marking:
            messagebox.showwarning("Ошибка", "Сначала сохраните начальное состояние")
            return
        
        for name, tokens in self.initial_marking.items():
            if name in self.places:
                self.places[name]['tokens'] = tokens
                self.places[name]['element'].redraw_tokens(tokens)   # ← изменение
    
    def reset_marking(self):
        for name in self.places:
            self.places[name]['tokens'] = 0
            self.places[name]['element'].redraw_tokens(0)
            
    def get_current_marking_tuple(self):
        marking = []
        for name in sorted(self.places.keys()):
            marking.append(self.places[name]['tokens'])
        return tuple(marking)
    
    def set_marking_from_tuple(self, marking_tuple):
        for i, name in enumerate(sorted(self.places.keys())):
            if i < len(marking_tuple):
                self.places[name]['tokens'] = marking_tuple[i]
                self.places[name]['element'].redraw_tokens(marking_tuple[i])
    
    def build_model_from_editor(self) -> PetriNetModel:
        places = list(self.places.keys())
        transitions = list(self.transitions.keys())
        arcs: List[ModelArc] = []
        for a in self.arcs:
            arcs.append(ModelArc(source=a.source.name, target=a.target.name, weight=a.weight, arc_type=a.arc_type))
        return PetriNetModel(places=places, transitions=transitions, arcs=arcs)
    
    def build_reachability_graph(self):
        current_marking = self.get_current_marking_tuple()
        model = self.build_model_from_editor()
        visited, edges, enabled_cache = model.reachability_graph(current_marking, max_states=5000)
        
        visited_sorted = sorted(visited)
        for i, m in enumerate(visited_sorted):
            state_str = ", ".join([f"{name}: {m[j]}" for j, name in enumerate(sorted(self.places.keys()))])

        for from_m, t, to_m in edges[:20]:
            from_idx = visited_sorted.index(from_m)
            to_idx = visited_sorted.index(to_m)
            self.log(f"  M{from_idx} --[{t}]--> M{to_idx}")
        
        self.set_marking_from_tuple(current_marking)
        return visited, edges, enabled_cache
    
    def check_liveness(self):
        current_marking = self.get_current_marking_tuple()
        visited, edges, enabled_cache = self.build_reachability_graph()
        model = self.build_model_from_editor()
        live_map = model.liveness_from_reachability(visited, edges, enabled_cache)

        is_net_live = True
        for t_name in sorted(self.transitions.keys()):
            is_live = bool(live_map.get(t_name, False))
            if not is_live:
                is_net_live = False
        
        self.set_marking_from_tuple(current_marking)
        return is_net_live

    def show_reachability_window(self):
        model = self.build_model_from_editor()
        current_marking = self.get_current_marking_tuple()
        visited, edges, enabled_cache = model.reachability_graph(current_marking, max_states=5000)

        win = tk.Toplevel(self.root)
        win.title("Граф достижимости")
        win.geometry("900x600")

        nb = ttk.Notebook(win)
        nb.pack(fill="both", expand=True)

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
            row = [f"M{i}"] + [m[j] for j, _ in enumerate(sorted(self.places.keys()))]
            tv.insert("", "end", values=row)

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

        info = ttk.Label(win, text=f"Состояний: {len(visited)} | Рёбер: {len(edges)} | Ограничение: 5000")
        info.pack(side="bottom", fill="x")
        
    def get_network_data(self):
        data = {
            'places': {},
            'transitions': {},
            'arcs': [],
            'real_objects': self.real_object_map,
            'initial_marking': self.initial_marking
        }
        
        for name, pdata in self.places.items():
            elem = pdata['element']
            data['places'][name] = {
                'x': elem.x,
                'y': elem.y,
                'tokens': pdata['tokens']
            }
        
        for name, tdata in self.transitions.items():
            elem = tdata['element']
            data['transitions'][name] = {
                'x': elem.x,
                'y': elem.y
            }
        
        for arc in self.arcs:
            data['arcs'].append({
                'source': arc.source.name,
                'target': arc.target.name,
                'weight': arc.weight,
                'type': arc.arc_type
            })
        
        return data
    
    def save_to_file(self):
        data = self.get_network_data()
        filename = tk.filedialog.asksaveasfilename(
            defaultextension=".json",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")]
        )
        if filename:
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            messagebox.showinfo("Сохранено", f"Сеть сохранена в {filename}")
            
    def load_from_file(self):
        filename = tk.filedialog.askopenfilename(
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")]
        )
        if filename:
            with open(filename, 'r', encoding='utf-8') as f:
                data = json.load(f)
            self.load_network_data(data)
            messagebox.showinfo("Загружено", f"Сеть загружена из {filename}")

    
    def rename_element(self, elem_type: str, old_name: str):
        new_name = simpledialog.askstring("Переименование", f"Новое имя для '{old_name}':", initialvalue=old_name)
        if not new_name:
            return
        new_name = new_name.strip()
        if not new_name or new_name == old_name:
            return
        if elem_type == 'place':
            if new_name in self.places:
                messagebox.showwarning("Имя", "Позиция с таким именем уже существует.")
                return
            data = self.places.pop(old_name)
            data['element'].name = new_name
            self.places[new_name] = data
            self.canvas.itemconfig(data['element'].text_id, text=new_name)
        else:
            if new_name in self.transitions:
                messagebox.showwarning("Имя", "Переход с таким именем уже существует.")
                return
            data = self.transitions.pop(old_name)
            data['element'].name = new_name
            self.transitions[new_name] = data
            self.canvas.itemconfig(data['element'].text_id, text=new_name)

        if old_name in self.real_object_map:
            self.real_object_map[new_name] = self.real_object_map.pop(old_name)
        if old_name in self.initial_marking:
            self.initial_marking[new_name] = self.initial_marking.pop(old_name)

        self.canvas_manager.select_element(elem_type, new_name)
        
    