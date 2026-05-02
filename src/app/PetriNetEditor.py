import tkinter as tk
from tkinter import ttk, messagebox, simpledialog
from typing import Optional

from app.modules.elements import Arc
from app.modules.event_handlers import EditorEventHandlers
from app.modules.petrinetwork import PetriNetwork
from app.modules.simulation import PetriSimulation
from app.ui.builder import UIBuilder


class PetriNetEditor:
    def __init__(self, root):
        self.root = root
        self.root.title("Визуальный редактор и эмулятор сетей Петри")
        self.root.geometry("1200x800")
    
        self.selected_element = None
        self.selected_elements = set()
        self.selected_arc = None
        
        self.ui_builder = UIBuilder(self)
        
        self.petriNetwork = PetriNetwork(self)
        self.simulation = PetriSimulation(self)
        self.handlers = EditorEventHandlers(self)
        
        self.ui_builder.post_build()
        
        self.canvas.bind('<Button-1>', self.handlers.on_canvas_click)
        self.canvas.bind('<B1-Motion>', self.handlers.on_canvas_drag)
        self.canvas.bind('<ButtonRelease-1>', self.handlers.on_canvas_release)
        self.canvas.bind('<Delete>', self.delete_selected)
        self.canvas.bind('<BackSpace>', self.delete_selected)
        self.canvas.bind('<Button-3>', self.handlers.on_right_click)
        self.root.bind_all('<ButtonRelease-1>', self.handlers.on_global_button_release, add='+')


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

        self.petriNetwork.clear_highlight()
        if len(self.selected_elements) <= 1:
            self.petriNetwork.highlight_element(elem, 'blue' if elem.type == 'place' else 'green')
        else:
            for e in self.selected_elements:
                for canvas_id in e.canvas_ids:
                    self.canvas.itemconfig(canvas_id, outline='purple', width=3)
            
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
    
        


    
