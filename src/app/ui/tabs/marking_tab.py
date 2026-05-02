from tkinter import ttk

class MarkingTab:
    def __init__(self, parent, editor):
        self.editor = editor
        self.frame = ttk.Frame(parent)
        parent.add(self.frame, text="Разметка")

        ttk.Label(self.frame, text="Начальная разметка:", font=('Arial', 10, 'bold')).pack(pady=5)
        ttk.Button(self.frame, text="Сохранить разметку", command=editor.petriNetwork.save_initial_state).pack(fill='x', padx=10, pady=2)
        ttk.Button(self.frame, text="Восстановить", command=editor.petriNetwork.load_initial_state).pack(fill='x', padx=10, pady=2)
        ttk.Button(self.frame, text="Сбросить", command=editor.petriNetwork.reset_marking).pack(fill='x', padx=10, pady=2)