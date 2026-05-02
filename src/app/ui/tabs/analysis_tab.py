from tkinter import ttk

class AnalysisTab:
    def __init__(self, parent, editor):
        self.editor = editor
        self.frame = ttk.Frame(parent)
        parent.add(self.frame, text="Анализ")

        ttk.Label(self.frame, text="Анализ:", font=('Arial', 10, 'bold')).pack(pady=5)
        ttk.Button(self.frame, text="Граф достижимости (окно)",
                   command=editor.analysis.show_reachability_window).pack(fill='x', padx=10, pady=2)
        ttk.Button(self.frame, text="Проверить живость",
                   command=editor.analysis.check_liveness).pack(fill='x', padx=10, pady=2)

        ttk.Separator(self.frame, orient='horizontal').pack(fill='x', pady=10)

        ttk.Label(self.frame, text="Файлы:", font=('Arial', 10, 'bold')).pack(pady=5)
        ttk.Button(self.frame, text="Сохранить модель...", command=editor.saveload.save_to_file).pack(fill='x', padx=10, pady=2)
        ttk.Button(self.frame, text="Загрузить модель...", command=editor.saveload.load_from_file).pack(fill='x', padx=10, pady=2)