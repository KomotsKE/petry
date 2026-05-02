import tkinter as tk
from tkinter import ttk, messagebox, simpledialog
from typing import Optional

from src.app.modules.elements import Arc
from src.app.modules.petrinetwork import PetriNetwork
from src.app.modules.simulation import PetriSimulation
from src.app.ui.tabs.analysis_tab import AnalysisTab
from src.app.ui.builder import UIBuilder
from src.app.ui.tabs.marking_tab import MarkingTab
from src.app.ui.tabs.simulation_tab import SimulationTab
from src.app.ui.tabs.tools_tab import ToolsTab

class PetriNetEditor:
    def __init__(self, root):
        self.root = root
        self.root.title("Визуальный редактор и эмулятор сетей Петри")
        self.root.geometry("1200x800")
        
        # Состояния редактора
        self.mode = 'select'  # 'select', 'add_place', 'add_transition', 'add_arc'
        self.arc_source = None  # источник для создания дуги
        self.selected_element = None
        self.selected_elements = set()  # множественное выделение (для привязки к процессу)
        self.selected_arc = None
        self.drag_data = None
        self._arc_drag = None  # {'source': PetriNetElement, 'temp_id': int, 'from': (x,y)}
        
        self.ui_builder = UIBuilder(self)
        
        self.petriNetwork = PetriNetwork(self)
        self.simulation = PetriSimulation(self)
        
        self.ui_builder.post_build()
        
        self.canvas.bind('<Button-1>', self.on_canvas_click)
        self.canvas.bind('<B1-Motion>', self.on_canvas_drag)
        self.canvas.bind('<ButtonRelease-1>', self.on_canvas_release)
        self.canvas.bind('<Delete>', self.delete_selected)
        self.canvas.bind('<BackSpace>', self.delete_selected)
        self.canvas.bind('<Button-3>', self.on_right_click)
        self.root.bind_all('<ButtonRelease-1>', self.on_global_button_release, add='+')

        
    def set_mode(self, mode):
        self.mode = mode
        if hasattr(self, "tool_var"):
            self.tool_var.set(mode)
        self.arc_source = None
        # Сброс "тянущейся" дуги
        if getattr(self, "_arc_drag", None) and self._arc_drag.get("temp_id"):
            self.canvas.delete(self._arc_drag["temp_id"])
        self._arc_drag = None
        self.canvas.configure(cursor='' if mode == 'select' else 'crosshair')
        if hasattr(self, "status_var"):
            if mode == "add_arc":
                self.status_var.set("Режим дуги: потяните ЛКМ от объекта к объекту")
            else:
                self.status_var.set(f"Режим: {mode}")
        
    
    # ============ Обработка мыши ============
    
    def on_canvas_click(self, event):
        x, y = self.canvas.canvasx(event.x), self.canvas.canvasy(event.y)
        
        if self.mode == 'add_place':
            self.petriNetwork.create_place(x, y)
        elif self.mode == 'add_transition':
            self.petriNetwork.create_transition(x, y)
        elif self.mode == 'add_arc':
            clicked_elem = self.petriNetwork.get_element_at(x, y)
            if not clicked_elem:
                return
            if self._arc_drag is not None and self._arc_drag.get("temp_id"):
                self.canvas.delete(self._arc_drag["temp_id"])
                self._arc_drag = None
            self.arc_source = clicked_elem
            self.petriNetwork.highlight_element(clicked_elem)
            sx, sy = clicked_elem.get_connection_point(x, y)
            temp_id = self.canvas.create_line(
                sx, sy, x, y,
                fill="#444", width=2, arrow=tk.LAST, arrowshape=(10, 12, 5),
                dash=(4, 2),
                tags=("temp_arc",)
            )
            self._arc_drag = {'source': clicked_elem, 'temp_id': temp_id, 'from': (sx, sy)}
        elif self.mode == 'select':
            clicked_elem = self.petriNetwork.get_element_at(x, y)
            if clicked_elem:
                self.selected_arc = None
                if (event.state & 0x0004) != 0:
                    self.toggle_multi_select(clicked_elem)
                else:
                    self.select_element(clicked_elem.type, clicked_elem.name)
                self.drag_data = {'x': x, 'y': y, 'element': clicked_elem}
            else:
                arc = self.get_arc_at(event.x, event.y)
                if arc:
                    self.select_arc(arc)
                else:
                    self.deselect_all()
                
    def on_canvas_drag(self, event):
        if self.mode == 'add_arc' and self._arc_drag is not None:
            x, y = self.canvas.canvasx(event.x), self.canvas.canvasy(event.y)
            sx, sy = self._arc_drag['from']
            self.canvas.coords(self._arc_drag['temp_id'], sx, sy, x, y)
            return

        if self.drag_data is not None and self.mode == 'select':
            x, y = self.canvas.canvasx(event.x), self.canvas.canvasy(event.y)
            dx = x - self.drag_data['x']
            dy = y - self.drag_data['y']
            self.drag_data['element'].move(dx, dy)
            self.drag_data['x'] = x
            self.drag_data['y'] = y
            
    def on_canvas_release(self, event):
        if self.mode == 'add_arc' and self._arc_drag is not None:
            x, y = self.canvas.canvasx(event.x), self.canvas.canvasy(event.y)
            source = self._arc_drag['source']
            if self._arc_drag.get('temp_id'):
                self.canvas.delete(self._arc_drag['temp_id'])

            target = self.petriNetwork.get_element_at(x, y)
            if target and target != source:
                if source.type == target.type:
                    messagebox.showwarning("Дуга", "Дуга должна соединять позицию и переход.")
                else:
                    self.petriNetwork.create_arc(source, target)

            self._arc_drag = None
            self.arc_source = None
            self.petriNetwork.clear_highlight()
            return

        self.drag_data = None

    def on_global_button_release(self, event):
        if self.mode != 'add_arc':
            return
        if self._arc_drag is None:
            return
        if event.widget == self.canvas:
            return

        if self._arc_drag.get('temp_id'):
            try:
                self.canvas.delete(self._arc_drag['temp_id'])
            except tk.TclError:
                pass
        self._arc_drag = None
        self.arc_source = None
        self.clear_highlight()

    def on_element_button1(self, elem_type: str, name: str, event):
        x, y = self.canvas.canvasx(event.x), self.canvas.canvasy(event.y)
        if self.mode == 'add_arc':
            self.on_canvas_click(event)
            return

        if self.mode == 'select':
            self.selected_arc = None
            if (event.state & 0x0004) != 0:
                elem = self.places[name]['element'] if elem_type == 'place' else self.transitions[name]['element']
                self.toggle_multi_select(elem)
                self.drag_data = {'x': x, 'y': y, 'element': elem}
            else:
                self.select_element(elem_type, name)
                self.drag_data = {'x': x, 'y': y, 'element': self.selected_element}

    # ============ Выделение и подсветка ============
    
    def select_arc(self, arc: Arc):
        self.deselect_all()
        self.selected_arc = arc
        if arc.line_id:
            self.canvas.itemconfig(arc.line_id, fill="#1e88e5", width=3)
        self.element_name_var.set(f"{arc.source.name}→{arc.target.name}")
        self.element_type_var.set("Дуга")
        self.tokens_var.set("0")
        self.tokens_spinbox.configure(state='disabled')
        self.real_object_var.set("")

    def select_element(self, elem_type, name):
        self.deselect_all()
        
        if elem_type == 'place':
            data = self.petriNetwork.places[name]
            elem = data['element']
            self.selected_element = elem
            self.selected_elements = {elem}
            self.petriNetwork.highlight_element(elem, 'blue')
            self.element_name_var.set(name)
            self.element_type_var.set('Позиция')
            self.tokens_var.set(str(data['tokens']))
            self.tokens_spinbox.configure(state='normal')
            self.real_object_var.set(self.petriNetwork.real_object_map.get(name, ''))
        else:
            data = self.petriNetwork.transitions[name]
            elem = data['element']
            self.selected_element = elem
            self.selected_elements = {elem}
            self.petriNetwork.highlight_element(elem, 'green')
            self.element_name_var.set(name)
            self.element_type_var.set('Переход')
            self.tokens_var.set('0')
            self.tokens_spinbox.configure(state='disabled')
            self.real_object_var.set(self.petriNetwork.real_object_map.get(name, ''))
    
    def deselect_all(self): 
        self.selected_element = None
        self.selected_elements = set()
        if getattr(self, "selected_arc", None) is not None:
            a = self.selected_arc
            self.selected_arc = None
            if a and a.line_id:
                a.update_position()
        self.petriNetwork.clear_highlight()
        self.element_name_var.set('')
        self.element_type_var.set('')
        self.tokens_var.set('0')
        self.tokens_spinbox.configure(state='disabled')
        self.real_object_var.set('')
        
    def toggle_multi_select(self, elem):
        """Добавляет/убирает элемент в множественное выделение"""
        if elem in self.selected_elements:
            self.selected_elements.remove(elem)
        else:
            self.selected_elements.add(elem)
        self.selected_element = elem
        self.element_name_var.set(elem.name)
        self.element_type_var.set('Позиция' if elem.type == 'place' else 'Переход')
        if elem.type == 'place':
            self.tokens_var.set(str(self.petriNetwork.places[elem.name]['tokens']))
            self.tokens_spinbox.configure(state='normal')
        else:
            self.tokens_var.set('0')
            self.tokens_spinbox.configure(state='disabled')
        self.real_object_var.set(self.petriNetwork.real_object_map.get(elem.name, ''))

        self.petriNetwork.clear_highlight()
        if len(self.selected_elements) <= 1:
            self.petriNetwork.highlight_element(elem, 'blue' if elem.type == 'place' else 'green')
        else:
            for e in self.selected_elements:
                for canvas_id in e.canvas_ids:
                    self.canvas.itemconfig(canvas_id, outline='purple', width=3)
            
    
                
    def on_real_object_changed(self, *args):
        """Сохраняет в real_object_map при изменении текста в поле 'Объект'"""
        if self.selected_element:
            name = self.selected_element.name
            value = self.real_object_var.get().strip()
            if value:
                self.petriNetwork.real_object_map[name] = value
            else:
                self.petriNetwork.real_object_map.pop(name, None)

    def delete_selected(self, event=None):
        """Удаляет все выделенные элементы/дуги"""
        if self.selected_arc is not None:
            self.petriNetwork.delete_arc(self.selected_arc)
            self.selected_arc = None
            self.deselect_all()
            return

        to_delete = list(self.selected_elements)
        if not to_delete and self.selected_element:
            to_delete = [self.selected_element]

        for elem in to_delete:
            name = elem.name
            arcs_to_remove = list(set(elem.input_arcs) | set(elem.output_arcs))
            for arc in arcs_to_remove:
                if arc in self.petriNetwork.arcs:
                    self.petriNetwork.delete_arc(arc)

            if elem.type == 'place':
                elem.redraw_tokens(0)

            for cid in elem.canvas_ids:
                self.canvas.delete(cid)
            self.canvas.delete(elem.text_id)

            if elem.type == 'place':
                del self.petriNetwork.places[name]
            else:
                del self.petriNetwork.transitions[name]

            self.petriNetwork.real_object_map.pop(name, None)
            self.petriNetwork.initial_marking.pop(name, None)

        self.deselect_all()
    
    # ============ Фишки ============
    
    def update_tokens(self):
        if self.selected_element and self.selected_element.type == 'place':
            name = self.selected_element.name
            try:
                tokens = int(self.tokens_var.get())
                if 0 <= tokens <= 10:
                    self.petriNetwork.places[name]['tokens'] = tokens
                    self.petriNetwork.places[name]['element'].redraw_tokens(tokens)   # ← изменение
            except ValueError:
                pass
    
    # ============ Контекстные меню ============
    
    def on_right_click(self, event, forced_type=None, forced_name=None):
        x, y = self.canvas.canvasx(event.x), self.canvas.canvasy(event.y)

        elem = None
        elem_type = None
        name = None

        if forced_type and forced_name:
            elem_type, name = forced_type, forced_name
        else:
            clicked_elem = self.petriNetwork.get_element_at(x, y)
            if clicked_elem:
                elem = clicked_elem
                elem_type = elem.type
                name = elem.name
            else:
                arc = self.get_arc_at(event.x, event.y)
                if arc:
                    self.show_arc_menu(event, arc)
                    return

        if elem_type == 'place':
            self.select_element('place', name)
            self.show_place_menu(event, name)
        elif elem_type == 'transition':
            self.select_element('transition', name)
            self.show_transition_menu(event, name)


    def get_arc_at(self, screen_x: int, screen_y: int) -> Optional[Arc]:
        item = self.canvas.find_closest(screen_x, screen_y)
        if not item:
            return None
        tags = set(self.canvas.gettags(item[0]))
        uid = None
        for t in tags:
            if t.startswith("arc:"):
                uid = t.split("arc:", 1)[1]
                break
        if not uid:
            return None
        for a in self.petriNetwork.arcs:
            if a.uid == uid:
                return a
        return None

    def show_place_menu(self, event, name: str):
        menu = tk.Menu(self.root, tearoff=0)
        menu.add_command(label="Переименовать...", command=lambda: self.petriNetwork.rename_element('place', name))
        menu.add_command(label="Задать фишки...", command=lambda: self.prompt_tokens(name))
        menu.add_separator()
        menu.add_command(label="Удалить", command=self.delete_selected)
        menu.tk_popup(event.x_root, event.y_root)

    def show_transition_menu(self, event, name: str):
        menu = tk.Menu(self.root, tearoff=0)
        menu.add_command(label="Переименовать...", command=lambda: self.petriNetwork.rename_element('transition', name))
        menu.add_separator()
        menu.add_command(label="Удалить", command=self.delete_selected)
        menu.tk_popup(event.x_root, event.y_root)

    def show_arc_menu(self, event, arc: Arc):
        menu = tk.Menu(self.root, tearoff=0)
        menu.add_command(label="Свойства дуги...", command=lambda: self.petriNetwork.edit_arc_properties(arc))
        menu.add_command(label="Удалить дугу", command=lambda: self.petriNetwork.delete_arc(arc))
        menu.tk_popup(event.x_root, event.y_root)

    def prompt_tokens(self, place_name: str):
        val = simpledialog.askinteger("Фишки", f"Фишек в позиции '{place_name}':",
                                    initialvalue=self.petriNetwork.places[place_name]['tokens'],
                                    minvalue=0, maxvalue=1000)
        if val is None:
            return
        self.petriNetwork.places[place_name]['tokens'] = int(val)
        self.petriNetwork.places[place_name]['element'].redraw_tokens(int(val))   # ← изменение
        self.tokens_var.set(str(val))
        


    
