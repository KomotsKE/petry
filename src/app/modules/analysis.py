from tkinter import messagebox, ttk
import tkinter as tk

from app.modules.petrinetwork import PetriNetwork
from app.modules.petri import OMEGA


def _fmt_marking(marking, place_names):
    """Форматирует маркировку: ω вместо inf."""
    parts = []
    for i, p in enumerate(place_names):
        v = marking[i]
        parts.append("ω" if v == OMEGA else str(int(v)))
    return "(" + ", ".join(parts) + ")"


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

        # ---- Строка статуса ----
        mode_label = "покрываемости" if use_coverability else "достижимости"
        omega_note = " | ω = неограниченное место" if is_unbounded else ""
        ttk.Label(
            win,
            text=f"Граф {mode_label}: состояний {len(visited)} | рёбер {len(edges)}{omega_note}"
        ).pack(side="bottom", fill="x", padx=6, pady=3)