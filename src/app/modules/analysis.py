from tkinter import messagebox, ttk
import tkinter as tk
import math

from app.modules.petrinetwork import PetriNetwork
from app.modules.petri import OMEGA


def _fmt_marking(marking, place_names):
    """Форматирует маркировку: ω вместо inf."""
    parts = []
    for i, p in enumerate(place_names):
        v = marking[i]
        parts.append("ω" if v == OMEGA else str(int(v)))
    return "(" + ", ".join(parts) + ")"


def _bfs_state_order(initial_marking, edges, visited):
    succ = {m: [] for m in visited}
    for a, _, b in edges:
        if a in succ:
            succ[a].append(b)

    order = []
    seen = {initial_marking}
    queue = [initial_marking]
    while queue:
        current = queue.pop(0)
        order.append(current)
        for nxt in succ.get(current, []):
            if nxt not in seen:
                seen.add(nxt)
                queue.append(nxt)

    for m in visited:
        if m not in seen:
            order.append(m)

    return order


def _draw_state_graph(canvas: tk.Canvas, graph_order, edges, initial_marking, place_names):
    canvas.delete('all')
    width = int(canvas.winfo_width() or 800)
    height = int(canvas.winfo_height() or 620)
    if width < 400:
        width = 800
    if height < 300:
        height = 620

    node_radius = 30
    if not graph_order:
        return

    succ = {m: [] for m in graph_order}
    for a, t, b in edges:
        if a in succ:
            succ[a].append((b, t))

    level = {initial_marking: 0}
    queue = [initial_marking]
    while queue:
        current = queue.pop(0)
        for nxt, _ in succ.get(current, []):
            if nxt not in level:
                level[nxt] = level[current] + 1
                queue.append(nxt)

    max_level = max(level.values(), default=0)
    for m in graph_order:
        if m not in level:
            level[m] = max_level + 1
    max_level = max(level.values())

    levels = [[] for _ in range(max_level + 1)]
    for m in graph_order:
        levels[level[m]].append(m)

    positions = {}
    vertical_step = max(120, (height - 140) / max(1, max_level))
    for lvl, nodes in enumerate(levels):
        count = len(nodes)
        if count == 0:
            continue
        horizontal_step = max(180, (width - 120) / count)
        for idx, m in enumerate(nodes):
            x = 60 + horizontal_step * (idx + 0.5)
            y = 60 + vertical_step * lvl
            positions[m] = (x, y)

    def draw_edge(a, t, b):
        x1, y1 = positions[a]
        x2, y2 = positions[b]
        if a == b:
            r = node_radius * 1.4
            canvas.create_arc(
                x1 - r, y1 - r, x1 + r, y1 + r,
                start=45, extent=270,
                style='arc', width=1.5, outline='#555'
            )
            canvas.create_text(x1 + r + 10, y1 - r - 10, text=t, fill='#555', font=('Arial', 8))
        else:
            dx = x2 - x1
            dy = y2 - y1
            ctrl_x = x1 + dx * 0.5
            ctrl_y = y1 + dy * 0.3
            canvas.create_line(x1, y1, ctrl_x, ctrl_y, x2, y2,
                               arrow=tk.LAST, fill='#555', width=1.5,
                               smooth=True)
            mx = x1 + (x2 - x1) * 0.55
            my = y1 + (y2 - y1) * 0.45
            canvas.create_text(mx, my, text=t, fill='#555', font=('Arial', 8))

    for a, t, b in edges:
        if a in positions and b in positions:
            draw_edge(a, t, b)

    def make_label(m):
        label = _fmt_marking(m, place_names)
        if len(label) > 24:
            label = label.replace(', ', ',\n')
        return label

    for i, m in enumerate(graph_order):
        x, y = positions[m]
        fill = '#e3f2fd' if m == initial_marking else '#f5f5f5'
        node_tag = f'state_node_{i}'
        canvas.create_oval(
            x - node_radius, y - node_radius,
            x + node_radius, y + node_radius,
            fill=fill, outline='#333', width=2,
            tags=(node_tag, 'state_node')
        )
        canvas.create_text(
            x, y, text=make_label(m), font=('Arial', 8, 'bold'), tags=(node_tag, 'state_node_label'), width=node_radius * 3
        )

    canvas.config(scrollregion=canvas.bbox('all'))


def _on_graph_double_click(event, canvas, graph_order, place_names, node_info_var):
    x = canvas.canvasx(event.x)
    y = canvas.canvasy(event.y)
    closest = canvas.find_closest(x, y)
    if not closest:
        return
    tags = canvas.gettags(closest[0])
    for tag in tags:
        if tag.startswith('state_node_'):
            try:
                idx = int(tag.split('_')[-1])
            except ValueError:
                continue
            if 0 <= idx < len(graph_order):
                m = graph_order[idx]
                node_info_var.set(f"Узел M{idx}: {_fmt_marking(m, place_names)}")
            return


class analysis:
    def __init__(self, network: PetriNetwork, root: tk.Tk):
        self.network = network
        self.root = root

    # ------------------------------------------------------------------ #
    #  Живость                                                            #
    # ------------------------------------------------------------------ #

    def check_liveness(self):
        model = self.network.build_model()
        marking = self.network.get_marking()

        # Всегда используем граф покрываемости — корректен и для ограниченных сетей
        visited, edges, is_unbounded = model.coverability_graph(marking)
        live_map = model.liveness_from_coverability(visited, edges, is_unbounded)

        is_net_live = all(live_map.get(t) is True for t in self.network.transitions)

        lines = []
        for t in sorted(self.network.transitions.keys()):
            val = live_map.get(t, False)
            if val is True:
                icon = "✓"
            elif val == "?":
                icon = "?"
            else:
                icon = "✗"
            lines.append(f"{icon}  {t}")

        if is_net_live:
            status = "Сеть живая ✓"
        elif any(live_map.get(t) == "?" for t in self.network.transitions):
            status = "Живость не определена (⚠ неограниченная сеть)"
        else:
            status = "Сеть НЕ живая ✗"

        extra = ""
        if is_unbounded:
            extra = "\n⚠ Сеть НЕОГРАНИЧЕНА — результат по графу покрываемости"
        
        # Проверяем наличие ингибиторных дуг
        has_inhibitor = any(a.arc_type == 'inhibitor' for a in self.network.arcs)
        if has_inhibitor:
            extra += "\n📍 В сети есть ингибиторные дуги (красные) — они блокируют переход при наличии достаточного количества токенов"

        messagebox.showinfo(
            "Живость",
            status + extra + "\n\n" + "\n".join(lines),
            parent=self.root
        )
        return is_net_live

    # ------------------------------------------------------------------ #
    #  Граф покрываемости / достижимости                                 #
    # ------------------------------------------------------------------ #

    def show_reachability_window(self):
        model = self.network.build_model()
        marking = self.network.get_marking()
        place_names = sorted(self.network.places.keys())

        # Пробуем граф достижимости (быстро, только для ограниченных)
        visited_r, edges_r, enabled_cache = model.reachability_graph(marking, max_states=500)
        truncated = model._last_rg_truncated

        if truncated:
            # Переключаемся на граф покрываемости
            visited, edges, is_unbounded = model.coverability_graph(marking)
            use_coverability = True
        else:
            visited, edges = visited_r, edges_r
            is_unbounded = False
            use_coverability = False

        win = tk.Toplevel(self.root)
        win.title("Граф покрываемости" if use_coverability else "Граф достижимости")
        win.geometry("900x620")

        # Заголовок с предупреждением
        if is_unbounded:
            banner = tk.Label(
                win,
                text="⚠  Сеть НЕОГРАНИЧЕНА — показан граф покрываемости (ω = бесконечность)",
                bg="#b71c1c", fg="white", font=("Arial", 10, "bold"), pady=6
            )
            banner.pack(fill="x")
        elif use_coverability:
            banner = tk.Label(
                win,
                text="⚠  Граф достижимости обрезан — показан граф покрываемости",
                bg="#e65100", fg="white", font=("Arial", 10, "bold"), pady=6
            )
            banner.pack(fill="x")

        nb = ttk.Notebook(win)
        nb.pack(fill="both", expand=True)

        # ---- Вкладка: состояния ----
        tab_states = ttk.Frame(nb)
        nb.add(tab_states, text="Состояния")

        cols = ["id"] + place_names
        tv = ttk.Treeview(tab_states, columns=cols, show="headings")
        tv.pack(side="left", fill="both", expand=True)
        vs = ttk.Scrollbar(tab_states, orient="vertical", command=tv.yview)
        tv.configure(yscrollcommand=vs.set)
        vs.pack(side="right", fill="y")

        tv.heading("id", text="M#")
        tv.column("id", width=60, anchor="center")
        for p in place_names:
            tv.heading(p, text=p)
            tv.column(p, width=max(60, 120 // max(1, len(place_names))), anchor="center")

        visited_sorted = sorted(
            visited,
            key=lambda m: tuple(
                (0 if v == OMEGA else 1, 0 if v == OMEGA else v)
                for v in m
            )
        )
        idx_map = {m: i for i, m in enumerate(visited_sorted)}

        for i, m in enumerate(visited_sorted):
            values = [f"M{i}"]
            for v in m:
                values.append("ω" if v == OMEGA else str(int(v)))
            # Подсвечиваем ω-маркировки
            tag = "omega" if any(v == OMEGA for v in m) else ""
            tv.insert("", "end", values=values, tags=(tag,))

        tv.tag_configure("omega", foreground="#b71c1c")

        graph_order = _bfs_state_order(marking, edges, visited)

        # ---- Вкладка: переходы ----
        tab_edges = ttk.Frame(nb)
        nb.add(tab_edges, text="Переходы")

        tv2 = ttk.Treeview(tab_edges, columns=("from", "t", "to"), show="headings")
        tv2.pack(side="left", fill="both", expand=True)
        vs2 = ttk.Scrollbar(tab_edges, orient="vertical", command=tv2.yview)
        tv2.configure(yscrollcommand=vs2.set)
        vs2.pack(side="right", fill="y")

        for col, label, w in [("from", "От", 80), ("t", "Переход", 200), ("to", "К", 80)]:
            tv2.heading(col, text=label)
            tv2.column(col, width=w, anchor="center" if col != "t" else "w")

        for a, t, b in edges:
            tv2.insert(
                "", "end",
                values=(f"M{idx_map[a]}", t, f"M{idx_map[b]}")
            )

        # ---- Вкладка: граф ----
        tab_graph = ttk.Frame(nb)
        nb.add(tab_graph, text="Граф")

        graph_caption = ttk.Label(
            tab_graph,
            text="Перетаскивайте граф левой кнопкой мыши. Двойной клик на узле — информация о маркировке.",
            anchor='w'
        )
        graph_caption.pack(fill='x', padx=6, pady=(6, 0))

        graph_frame = ttk.Frame(tab_graph)
        graph_frame.pack(fill='both', expand=True)

        node_info = tk.StringVar(value="Дважды кликните узел, чтобы увидеть маркировку")
        graph_canvas = tk.Canvas(graph_frame, bg='white', width=900, height=620)
        graph_canvas.pack(fill='both', expand=True)
        graph_canvas.bind('<Configure>', lambda e: _draw_state_graph(graph_canvas, graph_order, edges, marking, place_names))
        graph_canvas.bind('<ButtonPress-1>', lambda event: graph_canvas.scan_mark(event.x, event.y))
        graph_canvas.bind('<B1-Motion>', lambda event: graph_canvas.scan_dragto(event.x, event.y, gain=1))
        graph_canvas.bind('<Double-Button-1>', lambda event: _on_graph_double_click(event, graph_canvas, graph_order, place_names, node_info))
        graph_canvas.config(cursor='hand2')
        ttk.Label(tab_graph, textvariable=node_info, anchor='w').pack(fill='x', padx=6, pady=3)

        # ---- Строка статуса ----
        mode_label = "покрываемости" if use_coverability else "достижимости"
        omega_note = " | ω = неограниченное место" if is_unbounded else ""
        ttk.Label(
            win,
            text=f"Граф {mode_label}: состояний {len(visited)} | рёбер {len(edges)}{omega_note}"
        ).pack(side="bottom", fill="x", padx=6, pady=3)