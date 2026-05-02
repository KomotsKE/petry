import tkinter as tk
from tkinter import ttk

class ToolsTab:
    def __init__(self, parent, editor):
        self.editor = editor
        self.frame = ttk.Frame(parent)
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

        ttk.Separator(self.frame, orient='horizontal').pack(fill='x', pady=10)

        # Панель свойств
        ttk.Label(self.frame, text="Свойства:", font=('Arial', 10, 'bold')).pack(pady=5)
        prop_frame = ttk.Frame(self.frame)
        prop_frame.pack(fill='x', padx=10)
        prop_frame.grid_columnconfigure(0, weight=0)
        prop_frame.grid_columnconfigure(1, weight=1)

        ttk.Label(prop_frame, text="Имя:").grid(row=0, column=0, sticky='w')
        self.element_name_var = tk.StringVar()
        ttk.Entry(prop_frame, textvariable=self.element_name_var, state='readonly', width=22).grid(
            row=0, column=1, sticky='ew', padx=(6, 0), pady=1)

        ttk.Label(prop_frame, text="Тип:").grid(row=1, column=0, sticky='w')
        self.element_type_var = tk.StringVar()
        ttk.Entry(prop_frame, textvariable=self.element_type_var, state='readonly', width=22).grid(
            row=1, column=1, sticky='ew', padx=(6, 0), pady=1)

        ttk.Label(prop_frame, text="Фишки:").grid(row=2, column=0, sticky='w')
        self.tokens_var = tk.StringVar(value='0')
        self.tokens_spinbox = ttk.Spinbox(prop_frame, from_=0, to=10, textvariable=self.tokens_var,
                                          state='readonly', command=editor.update_tokens)
        self.tokens_spinbox.grid(row=2, column=1, sticky='ew', padx=(6, 0), pady=1)

    # Аксессоры для доступа к переменным из редактора
    def get_element_name_var(self):
        return self.element_name_var

    def get_element_type_var(self):
        return self.element_type_var

    def get_tokens_var(self):
        return self.tokens_var

    def get_tokens_spinbox(self):
        return self.tokens_spinbox

