from tkinter import messagebox, ttk
import tkinter as tk

from app.modules.petrinetwork import PetriNetwork

class analysis:
    def __init__(self, network: PetriNetwork, root: tk.Tk):
        self.network = network
        self.root = root
        
    def check_liveness(self):
        model = self.network.build_model()
        marking = self.network.get_marking()
        visited, edges, enabled_cache = model.reachability_graph(marking, max_states=5000)
        live_map = model.liveness_from_reachability(visited, edges, enabled_cache)

        is_net_live = all(bool(live_map.get(t, False)) for t in self.network.transitions)
        lines = [
            f"{'✓' if live_map.get(t, False) else '✗'}  {t}"
            for t in sorted(self.network.transitions.keys())
        ]
        status = "Сеть живая ✓" if is_net_live else "Сеть НЕ живая ✗"
        messagebox.showinfo("Живость", status + "\n\n" + "\n".join(lines), parent=self.root)
        return is_net_live

    def show_reachability_window(self):
        model = self.network.build_model()
        marking = self.network.get_marking()
        visited, edges, _ = model.reachability_graph(marking, max_states=5000)

        win = tk.Toplevel(self.root)
        win.title("Граф достижимости")
        win.geometry("900x600")

        nb = ttk.Notebook(win)
        nb.pack(fill="both", expand=True)

        tab_states = ttk.Frame(nb)
        nb.add(tab_states, text="Состояния")
        cols = ["id"] + sorted(self.network.places.keys())
        tv = ttk.Treeview(tab_states, columns=cols, show="headings")
        tv.pack(side="left", fill="both", expand=True)
        vs = ttk.Scrollbar(tab_states, orient="vertical", command=tv.yview)
        tv.configure(yscrollcommand=vs.set)
        vs.pack(side="right", fill="y")
        tv.heading("id", text="M#")
        tv.column("id", width=60, anchor="center")
        for p in sorted(self.network.places.keys()):
            tv.heading(p, text=p)
            tv.column(p, width=120, anchor="center")
        visited_sorted = sorted(visited)
        for i, m in enumerate(visited_sorted):
            tv.insert("", "end", values=[f"M{i}"] + list(m))

        tab_edges = ttk.Frame(nb)
        nb.add(tab_edges, text="Переходы")
        tv2 = ttk.Treeview(tab_edges, columns=("from", "t", "to"), show="headings")
        tv2.pack(side="left", fill="both", expand=True)
        vs2 = ttk.Scrollbar(tab_edges, orient="vertical", command=tv2.yview)
        tv2.configure(yscrollcommand=vs2.set)
        vs2.pack(side="right", fill="y")
        for col, label in [("from", "От"), ("t", "Переход"), ("to", "К")]:
            tv2.heading(col, text=label)
        tv2.column("from", width=100, anchor="center")
        tv2.column("t", width=200, anchor="w")
        tv2.column("to", width=100, anchor="center")
        idx = {m: i for i, m in enumerate(visited_sorted)}
        for a, t, b in edges:
            tv2.insert("", "end", values=(f"M{idx[a]}", t, f"M{idx[b]}"))

        ttk.Label(win,
                  text=f"Состояний: {len(visited)} | Рёбер: {len(edges)} | Ограничение: 5000"
                  ).pack(side="bottom", fill="x")