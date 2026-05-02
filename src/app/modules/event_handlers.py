import tkinter as tk
from tkinter import messagebox, simpledialog
from typing import Optional

from app.modules.elements import Arc
from app.modules.petrinetwork import PetriNetwork


class EditorEventHandlers:
    def __init__(self, editor, canvas: tk.Canvas, network: PetriNetwork, root: tk.Tk):
        self.network = network
        self.root = root
        self.canvas = canvas
        self.editor = editor
        self.arc_source = None
        self.drag_data = None
        self._arc_drag = None
        self.mode = 'select'

    # ============ Очистка arc_source ============

    def _clear_arc_source(self):
        """arc_source — наша ответственность, не PetriNetwork."""
        if self.arc_source:
            self.arc_source.clear_highlight()
            self.arc_source = None

    # ============ Клики и перетаскивание ============

    def on_canvas_click(self, event):
        x, y = self.canvas.canvasx(event.x), self.canvas.canvasy(event.y)

        if self.mode == 'add_place':
            name = self.network.create_place(x, y)
            self.editor._bind_element('place', name)

        elif self.mode == 'add_transition':
            name = self.network.create_transition(x, y)
            self.editor._bind_element('transition', name)

        elif self.mode == 'add_arc':
            clicked_elem = self.network.get_element_at(x, y)
            if not clicked_elem:
                return
            if self._arc_drag and self._arc_drag.get("temp_id"):
                self.canvas.delete(self._arc_drag["temp_id"])
                self._arc_drag = None
            self.arc_source = clicked_elem
            self.network.highlight_element(clicked_elem)
            sx, sy = clicked_elem.get_connection_point(x, y)
            temp_id = self.canvas.create_line(
                sx, sy, x, y,
                fill="#444", width=2, arrow=tk.LAST, arrowshape=(10, 12, 5),
                dash=(4, 2), tags=("temp_arc",)
            )
            self._arc_drag = {'source': clicked_elem, 'temp_id': temp_id, 'from': (sx, sy)}

        elif self.mode == 'select':
            clicked_elem = self.network.get_element_at(x, y)
            if clicked_elem:
                if (event.state & 0x0004) != 0:
                    self.network.toggle_multi_select(clicked_elem)
                else:
                    self.network.select_element(clicked_elem.type, clicked_elem.name)
                self.drag_data = {'x': x, 'y': y, 'element': clicked_elem}
            else:
                arc = self.get_arc_at(event.x, event.y)
                if arc:
                    self.network.select_arc(arc)
                else:
                    self.network.deselect_all()

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

            target = self.network.get_element_at(x, y)
            if target and target != source:
                if source.type == target.type:
                    messagebox.showwarning("Дуга", "Дуга должна соединять позицию и переход.",
                                           parent=self.root)
                else:
                    self.network.create_arc(source, target)

            self._arc_drag = None
            self._clear_arc_source()
            self.network.clear_highlight()
            return

        self.drag_data = None

    def on_global_button_release(self, event):
        if self.mode != 'add_arc' or self._arc_drag is None:
            return
        if event.widget == self.canvas:
            return
        if self._arc_drag.get('temp_id'):
            try:
                self.canvas.delete(self._arc_drag['temp_id'])
            except tk.TclError:
                pass
        self._arc_drag = None
        self._clear_arc_source()

    def on_element_button1(self, elem_type: str, name: str, event):
        x, y = self.canvas.canvasx(event.x), self.canvas.canvasy(event.y)
        if self.mode == 'add_arc':
            self.on_canvas_click(event)
            return
        if self.mode == 'select':
            if (event.state & 0x0004) != 0:
                elem = (self.network.places[name]['element']
                        if elem_type == 'place'
                        else self.network.transitions[name]['element'])
                self.network.toggle_multi_select(elem)
                self.drag_data = {'x': x, 'y': y, 'element': elem}
            else:
                self.network.select_element(elem_type, name)
                self.drag_data = {'x': x, 'y': y, 'element': self.network.selected_element}

    # ============ Контекстные меню ============

    def prompt_tokens(self, place_name: str):
        val = simpledialog.askinteger(
            "Фишки", f"Фишек в позиции '{place_name}':",
            initialvalue=self.network.places[place_name]['tokens'],
            minvalue=0, maxvalue=1000, parent=self.root
        )
        if val is None:
            return
        self.network.places[place_name]['tokens'] = int(val)
        self.network.places[place_name]['element'].redraw_tokens(int(val))
        self.network.tokens_var.set(str(val))
    
    def show_place_menu(self, event, name: str):
        menu = tk.Menu(self.root, tearoff=0)
        menu.add_command(label="Переименовать...",
                         command=lambda: self.network.rename_element('place', name))
        menu.add_command(label="Задать фишки...",
                         command=lambda: self.prompt_tokens(name))
        menu.add_separator()
        menu.add_command(label="Удалить", command=self.network.delete_selected)
        menu.tk_popup(event.x_root, event.y_root)

    def show_transition_menu(self, event, name: str):
        menu = tk.Menu(self.root, tearoff=0)
        menu.add_command(label="Переименовать...",
                         command=lambda: self.network.rename_element('transition', name))
        menu.add_separator()
        menu.add_command(label="Удалить", command=self.network.delete_selected)
        menu.tk_popup(event.x_root, event.y_root)

    def show_arc_menu(self, event, arc: Arc):
        menu = tk.Menu(self.root, tearoff=0)
        menu.add_command(label="Свойства дуги...",
                         command=lambda: self.network.edit_arc_properties(arc))
        menu.add_command(label="Удалить дугу",
                         command=lambda: self.network.delete_arc(arc))
        menu.tk_popup(event.x_root, event.y_root)

    def get_arc_at(self, screen_x: int, screen_y: int) -> Optional[Arc]:
        item = self.canvas.find_closest(screen_x, screen_y)
        if not item:
            return None
        tags = set(self.canvas.gettags(item[0]))
        uid = next((t.split("arc:", 1)[1] for t in tags if t.startswith("arc:")), None)
        if not uid:
            return None
        return next((a for a in self.network.arcs if a.uid == uid), None)

    def on_right_click(self, event, forced_type=None, forced_name=None):
        x, y = self.canvas.canvasx(event.x), self.canvas.canvasy(event.y)
        elem_type, name = forced_type, forced_name

        if not (forced_type and forced_name):
            clicked_elem = self.network.get_element_at(x, y)
            if clicked_elem:
                elem_type, name = clicked_elem.type, clicked_elem.name
            else:
                arc = self.get_arc_at(event.x, event.y)
                if arc:
                    self.show_arc_menu(event, arc)
                return

        if elem_type == 'place':
            self.network.select_element('place', name)
            self.show_place_menu(event, name)
        elif elem_type == 'transition':
            self.network.select_element('transition', name)
            self.show_transition_menu(event, name)

    def set_mode(self, mode: str):
        self.mode = mode
        if hasattr(self.editor, 'tool_var'):
            self.editor.tool_var.set(mode)
        self._clear_arc_source()
        if self._arc_drag and self._arc_drag.get("temp_id"):
            self.canvas.delete(self._arc_drag["temp_id"])
        self._arc_drag = None
        self.canvas.configure(cursor='' if mode == 'select' else 'crosshair')
        if hasattr(self.editor, 'status_var'):
            msg = ("Режим дуги: потяните ЛКМ от объекта к объекту"
                   if mode == "add_arc" else f"Режим: {mode}")
            self.editor.status_var.set(msg)