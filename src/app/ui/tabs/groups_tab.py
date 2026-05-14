import tkinter as tk
from tkinter import ttk, messagebox, simpledialog
from typing import Set


class GroupsTab:
    def __init__(self, notebook: ttk.Notebook, editor):
        self.notebook = notebook
        self.editor = editor
        self.network = editor.petriNetwork
        self.frame = ttk.Frame(notebook)
        notebook.add(self.frame, text="Группы")
        self._build_ui()

    def _build_ui(self):
        # Treeview для групп
        self.tree = ttk.Treeview(self.frame, columns=("name",), show="tree headings")
        self.tree.heading("#0", text="Группа / Элемент")
        self.tree.heading("name", text="Имя")
        self.tree.column("#0", width=150)
        self.tree.column("name", width=100)
        self.tree.pack(fill="both", expand=True, padx=5, pady=5)
        self.tree.bind('<<TreeviewSelect>>', self._on_group_select)

        # Кнопки
        btn_frame = ttk.Frame(self.frame)
        btn_frame.pack(fill="x", padx=5, pady=5)

        ttk.Button(btn_frame, text="Добавить группу", command=self._add_group).pack(side="left", padx=2)
        ttk.Button(btn_frame, text="Удалить группу", command=self._remove_group).pack(side="left", padx=2)
        ttk.Button(btn_frame, text="Обновить список", command=self._refresh_groups).pack(side="left", padx=2)

        self._refresh_groups()

    def _refresh_groups(self):
        # Очистить дерево
        for item in self.tree.get_children():
            self.tree.delete(item)

        groups = self.network.get_groups()
        for group in groups:
            group_item = self.tree.insert("", "end", text=group['name'], values=(group['name'],))
            for elem in sorted(group['elements']):
                self.tree.insert(group_item, "end", text=elem, values=(elem,))

    def _on_group_select(self, event):
        selected = self.tree.selection()
        if not selected:
            self.network.clear_highlight()
            return
        item = selected[0]
        parent = self.tree.parent(item)
        if parent:  # Это элемент, не группа
            return
        group_name = self.tree.item(item, "values")[0]
        groups = self.network.get_groups()
        for g in groups:
            if g['name'] == group_name:
                self.network.highlight_group(g['elements'])
                break

    def _add_group(self):
        # Диалог для имени группы
        name = simpledialog.askstring("Новая группа", "Введите имя группы:", parent=self.frame)
        if not name:
            return

        # Диалог для выбора элементов
        elements = self._select_elements_dialog()
        if elements:
            if self.network.add_group(name, elements):
                self._refresh_groups()

    def _select_elements_dialog(self):
        dialog = tk.Toplevel(self.frame)
        dialog.title("Выберите элементы для группы")
        dialog.geometry("400x400")

        # Список всех элементов
        all_elements = sorted(list(self.network.places.keys()) + list(self.network.transitions.keys()))
        selected = set()

        # Фрейм с скроллбаром
        frame = ttk.Frame(dialog)
        frame.pack(fill="both", expand=True, padx=10, pady=10)

        canvas = tk.Canvas(frame, height=300)
        scrollbar = ttk.Scrollbar(frame, orient="vertical", command=canvas.yview)
        scrollable_frame = ttk.Frame(canvas)

        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )

        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)

        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        # Checkbuttons
        vars_dict = {}
        for elem in all_elements:
            var = tk.BooleanVar()
            vars_dict[elem] = var
            ttk.Checkbutton(scrollable_frame, text=elem, variable=var).pack(anchor="w")

        def ok():
            for elem, var in vars_dict.items():
                if var.get():
                    selected.add(elem)
            dialog.destroy()

        def cancel():
            selected.clear()
            dialog.destroy()

        btn_frame = ttk.Frame(dialog)
        btn_frame.pack(fill="x", pady=10)
        ttk.Button(btn_frame, text="OK", command=ok).pack(side="left", padx=5)
        ttk.Button(btn_frame, text="Отмена", command=cancel).pack(side="left", padx=5)

        self.frame.wait_window(dialog)
        return selected

    def _remove_group(self):
        selected = self.tree.selection()
        if not selected:
            messagebox.showwarning("Предупреждение", "Выберите группу для удаления", parent=self.frame)
            return

        item = selected[0]
        parent = self.tree.parent(item)
        if parent:  # Это элемент, не группа
            messagebox.showwarning("Предупреждение", "Выберите группу, а не элемент", parent=self.frame)
            return

        group_name = self.tree.item(item, "values")[0]
        if messagebox.askyesno("Подтверждение", f"Удалить группу '{group_name}'?", parent=self.frame):
            self.network.remove_group(group_name)
            self._refresh_groups()
