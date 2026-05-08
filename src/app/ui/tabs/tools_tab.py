import tkinter as tk
from tkinter import ttk
from tkinter import messagebox
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.PetriNetEditor import PetriNetEditor

class ToolsTab:
    def __init__(self, parent, editor: "PetriNetEditor"):
        self.editor = editor
        self.frame = ttk.Frame(parent)
        
        ttk.Separator(self.frame, orient='horizontal').pack(fill='x', pady=10)
        
        parent.add(self.frame, text="Инструменты")

        # Палитра инструментов
        ttk.Label(self.frame, text="Инструменты:", font=('Arial', 10, 'bold')).pack(pady=5)
        palette = ttk.Frame(self.frame)
        palette.pack(fill="x", padx=10)

        self.tool_var = tk.StringVar(value="select")
        ttk.Radiobutton(palette, text="Курсор", variable=self.tool_var, value="select",
                        command=lambda: editor.handlers.set_mode("select")).pack(fill="x", pady=2)
        ttk.Radiobutton(palette, text="● Позиция", variable=self.tool_var, value="add_place",
                        command=lambda: editor.handlers.set_mode("add_place")).pack(fill="x", pady=2)
        ttk.Radiobutton(palette, text="▮ Переход", variable=self.tool_var, value="add_transition",
                        command=lambda: editor.handlers.set_mode("add_transition")).pack(fill="x", pady=2)
        ttk.Radiobutton(palette, text="→ Дуга", variable=self.tool_var, value="add_arc",
                        command=lambda: editor.handlers.set_mode("add_arc")).pack(fill="x", pady=2)

        # Панель свойств
        ttk.Label(self.frame, text="Свойства:", font=('Arial', 10, 'bold')).pack(pady=5)
        prop_frame = ttk.Frame(self.frame)
        prop_frame.pack(fill='x', padx=10)
        prop_frame.grid_columnconfigure(0, weight=0)
        prop_frame.grid_columnconfigure(1, weight=1)

        ttk.Label(prop_frame, text="Имя:").grid(row=0, column=0, sticky='w')
        self.element_name_var = tk.StringVar()
        self.name_entry = ttk.Entry(prop_frame, textvariable=self.element_name_var, width=22)
        self.name_entry.grid(row=0, column=1, sticky='ew', padx=(6, 0), pady=1)
        self.name_entry.bind('<Return>', self._on_name_changed)
        self.name_entry.bind('<FocusOut>', self._on_name_changed)

        ttk.Label(prop_frame, text="Тип:").grid(row=1, column=0, sticky='w')
        self.element_type_var = tk.StringVar()
        ttk.Entry(prop_frame, textvariable=self.element_type_var, state='readonly', width=22).grid(
            row=1, column=1, sticky='ew', padx=(6, 0), pady=1)

        ttk.Label(prop_frame, text="Фишки:").grid(row=2, column=0, sticky='w')
        self.tokens_var = tk.StringVar(value='0')
        self.tokens_spinbox = ttk.Spinbox(prop_frame, from_=0, to=10, textvariable=self.tokens_var,
                                          state='readonly', command=editor.petriNetwork.update_tokens)
        self.tokens_spinbox.grid(row=2, column=1, sticky='ew', padx=(6, 0), pady=1)
        
        ttk.Separator(self.frame, orient='horizontal').pack(fill='x', pady=10)

        # Кнопка показа/скрытия имён
        # True — имена видны по умолчанию (соответствует name_hidden=False в PetriNetElement)
        self.show_names_var = tk.BooleanVar(value=True)
        self.show_names_btn = ttk.Checkbutton(
            self.frame,
            text="Показывать имена всех элементов",
            variable=self.show_names_var,
            command=self._toggle_show_all_names
        )
        self.show_names_btn.pack(fill='x', padx=10, pady=5)
        
        ttk.Separator(self.frame, orient='horizontal').pack(fill='x', pady=10)
    
    def _toggle_show_all_names(self):
        """Показывает или скрывает имена всех элементов сети."""
        show = self.show_names_var.get()
        # Сохраняем состояние в редакторе для корректной работы hover-биндингов
        self.editor.show_all_names = show

        for data in self.editor.petriNetwork.places.values():
            elem = data['element']
            if show:
                elem.show_name()
            else:
                elem.hide_name()
        for data in self.editor.petriNetwork.transitions.values():
            elem = data['element']
            if show:
                elem.show_name()
            else:
                elem.hide_name()

        # Перевешиваем биндинги — чтобы hover включался/выключался корректно
        self.editor._rebind_all_elements()

    def _on_name_changed(self, event=None):
        """Обработчик изменения имени элемента из панели свойств."""
        new_name = self.element_name_var.get().strip()
        if not new_name or not self.editor.petriNetwork.selected_element:
            return

        elem = self.editor.petriNetwork.selected_element
        old_name = elem.name
        elem_type = elem.type

        if new_name == old_name:
            return

        if elem_type == 'place':
            if new_name in self.editor.petriNetwork.places:
                messagebox.showwarning("Имя", "Позиция с таким именем уже существует.", parent=self.editor.root)
                self.element_name_var.set(old_name)
                return
        else:
            if new_name in self.editor.petriNetwork.transitions:
                messagebox.showwarning("Имя", "Переход с таким именем уже существует.", parent=self.editor.root)
                self.element_name_var.set(old_name)
                return

        self._do_rename(elem_type, old_name, new_name)

    def _do_rename(self, elem_type: str, old_name: str, new_name: str):
        """Выполняет переименование элемента без диалога."""
        if elem_type == 'place':
            data = self.editor.petriNetwork.places.pop(old_name)
            data['element'].name = new_name
            self.editor.petriNetwork.places[new_name] = data
        else:
            data = self.editor.petriNetwork.transitions.pop(old_name)
            data['element'].name = new_name
            self.editor.petriNetwork.transitions[new_name] = data

        if old_name in self.editor.petriNetwork.real_object_map:
            self.editor.petriNetwork.real_object_map[new_name] = \
                self.editor.petriNetwork.real_object_map.pop(old_name)
        if old_name in self.editor.petriNetwork.initial_marking:
            self.editor.petriNetwork.initial_marking[new_name] = \
                self.editor.petriNetwork.initial_marking.pop(old_name)

        if data['element'].text_id:
            self.editor.canvas.itemconfig(data['element'].text_id, text=new_name)

        self.editor._bind_element(elem_type, new_name)
        self.editor.petriNetwork.select_element(elem_type, new_name)

    # Аксессоры для доступа к переменным из редактора
    def get_element_name_var(self):
        return self.element_name_var

    def get_element_type_var(self):
        return self.element_type_var

    def get_tokens_var(self):
        return self.tokens_var

    def get_tokens_spinbox(self):
        return self.tokens_spinbox
    
    def _on_load_network(self):
        self.editor.saveload.load_from_file()
        self.editor._rebind_all_elements()