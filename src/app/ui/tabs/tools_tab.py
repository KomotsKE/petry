import tkinter as tk
from tkinter import ttk, messagebox
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.PetriNetEditor import PetriNetEditor


class ToolsTab:
    def __init__(self, parent, editor: "PetriNetEditor"):
        self.editor = editor
        self.frame = ttk.Frame(parent)
        parent.add(self.frame, text="Инструменты")

        # ── Палитра инструментов ──────────────────────────────────────────
        ttk.Separator(self.frame, orient='horizontal').pack(fill='x', pady=8)
        ttk.Label(self.frame, text="Инструменты:", font=('Arial', 10, 'bold')).pack(pady=(0, 4))

        palette = ttk.Frame(self.frame)
        palette.pack(fill="x", padx=10)
        self.tool_var = tk.StringVar(value="select")
        for text, value in [
            ("Курсор",    "select"),
            ("● Позиция", "add_place"),
            ("▮ Переход", "add_transition"),
            ("→ Дуга",    "add_arc"),
        ]:
            ttk.Radiobutton(palette, text=text, variable=self.tool_var, value=value,
                            command=lambda v=value: editor.handlers.set_mode(v)
                            ).pack(fill="x", pady=2)

        # ── Файлы ────────────────────────────────────────────────────────
        ttk.Separator(self.frame, orient='horizontal').pack(fill='x', pady=8)
        ttk.Label(self.frame, text="Файл:", font=('Arial', 10, 'bold')).pack(pady=(0, 4))
        file_frame = ttk.Frame(self.frame)
        file_frame.pack(fill="x", padx=10)
        ttk.Button(file_frame, text="Сохранить сеть",
                   command=editor.saveload.save_to_file).pack(fill="x", pady=2)
        ttk.Button(file_frame, text="Загрузить сеть",
                   command=self._on_load_network).pack(fill="x", pady=2)

        # ── Свойства ─────────────────────────────────────────────────────
        ttk.Separator(self.frame, orient='horizontal').pack(fill='x', pady=8)
        ttk.Label(self.frame, text="Свойства:", font=('Arial', 10, 'bold')).pack(pady=(0, 4))

        prop = ttk.Frame(self.frame)
        prop.pack(fill='x', padx=10)
        prop.grid_columnconfigure(1, weight=1)

        # Имя
        ttk.Label(prop, text="Имя:").grid(row=0, column=0, sticky='w', pady=1)
        self.element_name_var = tk.StringVar()
        self.name_entry = ttk.Entry(prop, textvariable=self.element_name_var, width=22)
        self.name_entry.grid(row=0, column=1, sticky='ew', padx=(6, 0), pady=1)
        self.name_entry.bind('<Return>', self._on_name_changed)
        self.name_entry.bind('<FocusOut>', self._on_name_changed)

        # Тип
        ttk.Label(prop, text="Тип:").grid(row=1, column=0, sticky='w', pady=1)
        self.element_type_var = tk.StringVar()
        ttk.Entry(prop, textvariable=self.element_type_var, state='readonly', width=22
                  ).grid(row=1, column=1, sticky='ew', padx=(6, 0), pady=1)

        # Фишки (только для позиций)
        ttk.Label(prop, text="Фишки:").grid(row=2, column=0, sticky='w', pady=1)
        self.tokens_var = tk.StringVar(value='0')
        self.tokens_spinbox = ttk.Spinbox(
            prop, from_=0, to=10, textvariable=self.tokens_var,
            state='disabled', width=22,
            command=editor.petriNetwork.update_tokens
        )
        self.tokens_spinbox.grid(row=2, column=1, sticky='ew', padx=(6, 0), pady=1)

        # Приоритет (только для переходов)
        ttk.Label(prop, text="Приоритет:").grid(row=3, column=0, sticky='w', pady=1)
        self.priority_var = tk.StringVar(value='1')
        self.priority_spinbox = ttk.Spinbox(
            prop, from_=1, to=100, textvariable=self.priority_var,
            state='disabled', width=22,
            command=editor.petriNetwork.update_priority
        )
        self.priority_spinbox.grid(row=3, column=1, sticky='ew', padx=(6, 0), pady=1)
        # Также реагируем на ручной ввод
        self.priority_var.trace_add('write', editor.petriNetwork.update_priority)

        # Метка (только для переходов)
        ttk.Label(prop, text="Метка:").grid(row=4, column=0, sticky='w', pady=1)
        self.label_var = tk.StringVar()
        self.label_entry = ttk.Entry(prop, textvariable=self.label_var,
                                     state='disabled', width=22)
        self.label_entry.grid(row=4, column=1, sticky='ew', padx=(6, 0), pady=1)
        self.label_entry.bind('<Return>', lambda e: editor.petriNetwork.update_label())
        self.label_entry.bind('<FocusOut>', lambda e: editor.petriNetwork.update_label())
        self.label_var.trace_add('write', editor.petriNetwork.update_label)

        # Задержка (только для переходов)
        ttk.Label(prop, text="Задержка (мс):").grid(row=5, column=0, sticky='w', pady=1)
        self.delay_var = tk.StringVar(value='0')
        self.delay_spinbox = ttk.Spinbox(
            prop, from_=0, to=60000, increment=100,
            textvariable=self.delay_var,
            state='disabled', width=22,
            command=editor.petriNetwork.update_delay
        )
        self.delay_spinbox.grid(row=5, column=1, sticky='ew', padx=(6, 0), pady=1)
        self.delay_var.trace_add('write', editor.petriNetwork.update_delay)

        # ── Показ имён ────────────────────────────────────────────────────
        ttk.Separator(self.frame, orient='horizontal').pack(fill='x', pady=8)
        self.show_names_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(
            self.frame,
            text="Показывать имена всех элементов",
            variable=self.show_names_var,
            command=self._toggle_show_all_names
        ).pack(fill='x', padx=10, pady=4)

        self.show_labels_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(
            self.frame,
            text="Показывать метки переходов",
            variable=self.show_labels_var,
            command=self._toggle_show_labels
        ).pack(fill='x', padx=10, pady=4)

        ttk.Separator(self.frame, orient='horizontal').pack(fill='x', pady=8)

    # ── Переключение видимости имён ───────────────────────────────────────

    def _toggle_show_all_names(self):
        show = self.show_names_var.get()
        self.editor.show_all_names = show
        for data in self.editor.petriNetwork.places.values():
            elem = data['element']
            elem.show_name() if show else elem.hide_name()
        for data in self.editor.petriNetwork.transitions.values():
            elem = data['element']
            elem.show_name() if show else elem.hide_name()
        self.editor._rebind_all_elements()

    def _toggle_show_labels(self):
        show = self.show_labels_var.get()
        for data in self.editor.petriNetwork.transitions.values():
            elem = data['element']
            elem.labels_hidden = not show
            elem.redraw_label()

    # ── Переименование из панели свойств ─────────────────────────────────

    def _on_name_changed(self, event=None):
        new_name = self.element_name_var.get().strip()
        if not new_name or not self.editor.petriNetwork.selected_element:
            return
        elem = self.editor.petriNetwork.selected_element
        old_name = elem.name
        elem_type = elem.type
        if new_name == old_name:
            return

        target_dict = (self.editor.petriNetwork.places
                       if elem_type == 'place'
                       else self.editor.petriNetwork.transitions)
        if new_name in target_dict:
            messagebox.showwarning("Имя", "Элемент с таким именем уже существует.",
                                   parent=self.editor.root)
            self.element_name_var.set(old_name)
            return

        self._do_rename(elem_type, old_name, new_name)

    def _do_rename(self, elem_type: str, old_name: str, new_name: str):
        net = self.editor.petriNetwork
        if elem_type == 'place':
            data = net.places.pop(old_name)
            data['element'].name = new_name
            net.places[new_name] = data
        else:
            data = net.transitions.pop(old_name)
            data['element'].name = new_name
            net.transitions[new_name] = data

        if old_name in net.real_object_map:
            net.real_object_map[new_name] = net.real_object_map.pop(old_name)
        if old_name in net.initial_marking:
            net.initial_marking[new_name] = net.initial_marking.pop(old_name)

        if data['element'].text_id:
            self.editor.canvas.itemconfig(data['element'].text_id, text=new_name)

        self.editor._bind_element(elem_type, new_name)
        net.select_element(elem_type, new_name)

    # ── Загрузка сети ─────────────────────────────────────────────────────

    def _on_load_network(self):
        self.editor.saveload.load_from_file()
        self.editor._rebind_all_elements()

    # ── Аксессоры ─────────────────────────────────────────────────────────

    def get_element_name_var(self):   return self.element_name_var
    def get_element_type_var(self):   return self.element_type_var
    def get_tokens_var(self):         return self.tokens_var
    def get_tokens_spinbox(self):     return self.tokens_spinbox
    def get_priority_var(self):       return self.priority_var
    def get_priority_spinbox(self):   return self.priority_spinbox
    def get_label_var(self):          return self.label_var
    def get_label_entry(self):        return self.label_entry
    def get_delay_var(self):          return self.delay_var
    def get_delay_spinbox(self):      return self.delay_spinbox