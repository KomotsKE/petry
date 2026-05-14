import tkinter as tk
from tkinter import ttk, messagebox, simpledialog


class GroupsTab:
    """
    Вкладка управления группами элементов сети.

    Возможности:
      • Добавить группу (с выбором элементов)
      • Удалить группу
      • Переименовать группу
      • Добавить элементы в выбранную группу
      • Удалить элемент из группы
      • Клик на группе → подсветка элементов на canvas
      • Клик на элементе группы → выделение на canvas
    """

    def __init__(self, notebook: ttk.Notebook, editor):
        self.notebook = notebook
        self.editor = editor
        self.network = editor.petriNetwork

        self.frame = ttk.Frame(notebook)
        notebook.add(self.frame, text="Группы")

        self._build_ui()

    # ── Сборка UI ─────────────────────────────────────────────────────────

    def _build_ui(self):
        # ── TreeView ──────────────────────────────────────────────────────
        tree_frame = ttk.Frame(self.frame)
        tree_frame.pack(fill="both", expand=True, padx=5, pady=(5, 0))

        self.tree = ttk.Treeview(
            tree_frame,
            columns=("type",),
            show="tree headings",
            selectmode="browse"
        )
        self.tree.heading("#0", text="Группа / Элемент")
        self.tree.heading("type", text="Тип")
        self.tree.column("#0", width=150, minwidth=100)
        self.tree.column("type", width=80, anchor="center")

        vsb = ttk.Scrollbar(tree_frame, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=vsb.set)
        self.tree.pack(side="left", fill="both", expand=True)
        vsb.pack(side="right", fill="y")

        self.tree.bind("<<TreeviewSelect>>", self._on_tree_select)
        self.tree.bind("<Double-Button-1>", self._on_tree_double_click)

        # ── Кнопки ────────────────────────────────────────────────────────
        ttk.Separator(self.frame, orient="horizontal").pack(fill="x", padx=5, pady=4)

        # Первая строка — группы
        row1 = ttk.Frame(self.frame)
        row1.pack(fill="x", padx=5, pady=2)
        ttk.Label(row1, text="Группа:", width=8).pack(side="left")
        ttk.Button(row1, text="➕ Добавить", command=self._add_group
                   ).pack(side="left", padx=2)
        ttk.Button(row1, text="✏ Переим.", command=self._rename_group
                   ).pack(side="left", padx=2)
        ttk.Button(row1, text="🗑 Удалить", command=self._remove_group
                   ).pack(side="left", padx=2)

        # Вторая строка — элементы
        row2 = ttk.Frame(self.frame)
        row2.pack(fill="x", padx=5, pady=2)
        ttk.Label(row2, text="Элементы:", width=8).pack(side="left")
        ttk.Button(row2, text="➕ Добавить", command=self._add_elements_to_group
                   ).pack(side="left", padx=2)
        ttk.Button(row2, text="🗑 Убрать", command=self._remove_element_from_group
                   ).pack(side="left", padx=2)

        ttk.Separator(self.frame, orient="horizontal").pack(fill="x", padx=5, pady=4)

        # Статус — показывает группы выделенного элемента
        self._status_var = tk.StringVar(value="")
        ttk.Label(self.frame, textvariable=self._status_var,
                  foreground="#555", wraplength=240, justify="left"
                  ).pack(fill="x", padx=8, pady=(0, 4))

        self._refresh_groups()

    # ── Обновление дерева ─────────────────────────────────────────────────

    def _refresh_groups(self):
        # Сохраняем раскрытые группы
        expanded = {
            self.tree.item(iid, "text")
            for iid in self.tree.get_children()
            if self.tree.item(iid, "open")
        }

        for iid in self.tree.get_children():
            self.tree.delete(iid)

        for g in self.network.get_groups():
            gname = g['name']
            cnt = len(g['elements'])
            group_iid = self.tree.insert(
                "", "end",
                text=f"📁 {gname}",
                values=(f"{cnt} эл.",),
                open=(gname in expanded),
                tags=("group",)
            )
            for elem_name in sorted(g['elements']):
                if elem_name in self.network.places:
                    etype = "Позиция"
                    tag = "place_elem"
                elif elem_name in self.network.transitions:
                    etype = "Переход"
                    tag = "transition_elem"
                else:
                    etype = "⚠ удалён"
                    tag = "dead_elem"
                self.tree.insert(
                    group_iid, "end",
                    text=f"  {elem_name}",
                    values=(etype,),
                    tags=(tag,)
                )

        self.tree.tag_configure("group",          font=("Arial", 9, "bold"))
        self.tree.tag_configure("place_elem",     foreground="#1565c0")
        self.tree.tag_configure("transition_elem", foreground="#2e7d32")
        self.tree.tag_configure("dead_elem",      foreground="#c62828")

    # ── Обработчики выбора ────────────────────────────────────────────────

    def _get_selected_group_and_element(self):
        """
        Возвращает (group_name, element_name_or_None) для выделенного узла.
        Если выделена группа — element_name=None.
        Если ничего — оба None.
        """
        sel = self.tree.selection()
        if not sel:
            return None, None
        iid = sel[0]
        parent = self.tree.parent(iid)
        if parent:
            # Это дочерний элемент (элемент сети)
            group_name = self.tree.item(parent, "text").lstrip("📁 ")
            elem_name = self.tree.item(iid, "text").strip()
            return group_name, elem_name
        else:
            # Это группа
            group_name = self.tree.item(iid, "text").lstrip("📁 ")
            return group_name, None

    def _on_tree_select(self, _event=None):
        group_name, elem_name = self._get_selected_group_and_element()

        if group_name is None:
            self.network.clear_highlight()
            self._status_var.set("")
            return

        # Найти группу
        group = next((g for g in self.network.groups if g['name'] == group_name), None)
        if group is None:
            return

        if elem_name is None:
            # Выделена группа — подсвечиваем все её элементы
            self.network.highlight_group(group['elements'])
            self._status_var.set(
                f"Группа «{group_name}»: {len(group['elements'])} элем."
            )
        else:
            # Выделен конкретный элемент — выделяем его на canvas
            if elem_name in self.network.places:
                self.network.select_element('place', elem_name)
            elif elem_name in self.network.transitions:
                self.network.select_element('transition', elem_name)
            # Показываем, в каких ещё группах состоит элемент
            in_groups = self.network.get_element_groups(elem_name)
            if in_groups:
                self._status_var.set(
                    f"«{elem_name}» в группах:\n" + ", ".join(in_groups)
                )
            else:
                self._status_var.set(f"«{elem_name}» не состоит в группах")

    def _on_tree_double_click(self, _event=None):
        """Двойной клик на группе — переименование."""
        group_name, elem_name = self._get_selected_group_and_element()
        if group_name and elem_name is None:
            self._rename_group()

    # ── Действия с группами ───────────────────────────────────────────────

    def _add_group(self):
        name = simpledialog.askstring(
            "Новая группа", "Введите имя группы:",
            parent=self.frame
        )
        if not name or not name.strip():
            return

        elements = self._select_elements_dialog(
            title=f"Выберите элементы для группы «{name.strip()}»",
            preselected=set()
        )
        # elements может быть пустым — разрешаем создавать пустые группы
        if elements is None:
            return  # отмена

        self.network.add_group(name.strip(), elements)

    def _remove_group(self):
        group_name, _ = self._get_selected_group_and_element()
        if not group_name:
            messagebox.showwarning("Группы", "Выберите группу для удаления.", parent=self.frame)
            return
        if messagebox.askyesno(
            "Удалить группу",
            f"Удалить группу «{group_name}»?\nЭлементы сети останутся нетронутыми.",
            parent=self.frame
        ):
            self.network.remove_group(group_name)
            self.network.clear_highlight()
            self._status_var.set("")

    def _rename_group(self):
        group_name, _ = self._get_selected_group_and_element()
        if not group_name:
            messagebox.showwarning("Группы", "Выберите группу для переименования.", parent=self.frame)
            return
        new_name = simpledialog.askstring(
            "Переименовать группу",
            f"Новое имя для группы «{group_name}»:",
            initialvalue=group_name,
            parent=self.frame
        )
        if new_name and new_name.strip():
            self.network.rename_group(group_name, new_name.strip())

    # ── Действия с элементами ─────────────────────────────────────────────

    def _add_elements_to_group(self):
        group_name, _ = self._get_selected_group_and_element()
        if not group_name:
            messagebox.showwarning("Группы", "Сначала выберите группу.", parent=self.frame)
            return

        group = next((g for g in self.network.groups if g['name'] == group_name), None)
        if group is None:
            return

        elements = self._select_elements_dialog(
            title=f"Добавить элементы в группу «{group_name}»",
            preselected=set(group['elements'])
        )
        if elements is None:
            return  # отмена

        new_elements = elements - group['elements']
        if new_elements:
            self.network.add_elements_to_group(group_name, new_elements)
        else:
            messagebox.showinfo("Группы", "Новых элементов не выбрано.", parent=self.frame)

    def _remove_element_from_group(self):
        group_name, elem_name = self._get_selected_group_and_element()
        if not group_name or not elem_name:
            messagebox.showwarning(
                "Группы", "Выберите элемент внутри группы для удаления.",
                parent=self.frame
            )
            return
        # Убираем предупреждение об удалённых элементах без подтверждения
        elem_name = elem_name.strip()
        self.network.remove_element_from_group(group_name, elem_name)
        self.network.clear_highlight()
        self._status_var.set(f"«{elem_name}» удалён из группы «{group_name}»")

    # ── Диалог выбора элементов ───────────────────────────────────────────

    def _select_elements_dialog(self, title: str, preselected: set) -> set | None:
        """
        Показывает диалог с чекбоксами для выбора элементов сети.
        Возвращает set выбранных имён или None при отмене.
        """
        all_places = sorted(self.network.places.keys())
        all_transitions = sorted(self.network.transitions.keys())
        if not all_places and not all_transitions:
            messagebox.showinfo("Группы", "В сети нет элементов.", parent=self.frame)
            return None

        dialog = tk.Toplevel(self.frame)
        dialog.title(title)
        dialog.geometry("320x420")
        dialog.resizable(False, True)
        dialog.grab_set()
        dialog.transient(self.frame)

        result = [None]  # None = отмена, set = выбор

        # ── Контент ───────────────────────────────────────────────────────
        main_frame = ttk.Frame(dialog, padding=8)
        main_frame.pack(fill="both", expand=True)

        ttk.Label(main_frame, text="Позиции:", font=("Arial", 9, "bold")).pack(anchor="w")
        place_vars = {}
        if all_places:
            pf = ttk.Frame(main_frame)
            pf.pack(fill="x", pady=(0, 6))
            for name in all_places:
                var = tk.BooleanVar(value=(name in preselected))
                place_vars[name] = var
                ttk.Checkbutton(pf, text=name, variable=var).pack(anchor="w")
        else:
            ttk.Label(main_frame, text="  (нет позиций)", foreground="#888").pack(anchor="w")

        ttk.Label(main_frame, text="Переходы:", font=("Arial", 9, "bold")).pack(anchor="w")
        trans_vars = {}
        if all_transitions:
            tf = ttk.Frame(main_frame)
            tf.pack(fill="x", pady=(0, 6))
            for name in all_transitions:
                var = tk.BooleanVar(value=(name in preselected))
                trans_vars[name] = var
                ttk.Checkbutton(tf, text=name, variable=var).pack(anchor="w")
        else:
            ttk.Label(main_frame, text="  (нет переходов)", foreground="#888").pack(anchor="w")

        # Быстрый выбор всех / сброс
        quick_frame = ttk.Frame(main_frame)
        quick_frame.pack(fill="x", pady=4)

        def _select_all():
            for v in list(place_vars.values()) + list(trans_vars.values()):
                v.set(True)

        def _clear_all():
            for v in list(place_vars.values()) + list(trans_vars.values()):
                v.set(False)

        ttk.Button(quick_frame, text="Выбрать все", command=_select_all).pack(side="left", padx=2)
        ttk.Button(quick_frame, text="Снять все", command=_clear_all).pack(side="left", padx=2)

        # ── Кнопки OK/Отмена ─────────────────────────────────────────────
        ttk.Separator(dialog, orient="horizontal").pack(fill="x")
        btn_frame = ttk.Frame(dialog, padding=(8, 6))
        btn_frame.pack(fill="x")

        def _ok():
            chosen = set()
            for name, var in {**place_vars, **trans_vars}.items():
                if var.get():
                    chosen.add(name)
            result[0] = chosen
            dialog.destroy()

        def _cancel():
            result[0] = None
            dialog.destroy()

        ttk.Button(btn_frame, text="OK", command=_ok, width=10).pack(side="left", padx=4)
        ttk.Button(btn_frame, text="Отмена", command=_cancel, width=10).pack(side="left")

        dialog.protocol("WM_DELETE_WINDOW", _cancel)
        dialog.wait_window()
        return result[0]