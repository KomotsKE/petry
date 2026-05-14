import tkinter as tk
from app.modules.elements import Arc
from app.modules.event_handlers import EditorEventHandlers
from app.modules.petrinetwork import PetriNetwork
from app.modules.simulation import PetriSimulation
from app.ui.builder import UIBuilder
from app.modules.analysis import analysis
from app.modules.saveload import saveload


class PetriNetEditor:
    def __init__(self, root):
        self.root = root
        self.root.title("Визуальный редактор и эмулятор сетей Петри")
        self.root.geometry("1200x800")

        # 1. Строим UI до создания модулей — нужен self.canvas
        self.ui_builder = UIBuilder(self)

        # 2. Передаём canvas и root напрямую, без self
        self.petriNetwork = PetriNetwork(self.canvas, self.root, self)
        self.simulation = PetriSimulation(self.petriNetwork, self.root)
        self.handlers = EditorEventHandlers(self, self.canvas, self.petriNetwork, self.root)
        self.analysis = analysis(self.petriNetwork, self.root)
        self.saveload = saveload(self.canvas, self.root, self.petriNetwork)

        # 3. Завершаем сборку UI (создаёт вкладки и переменные)
        self.ui_builder.post_build()

        # 4. Биндим события canvas
        self.canvas.bind('<Button-1>', self.handlers.on_canvas_click)
        self.canvas.bind('<B1-Motion>', self.handlers.on_canvas_drag)
        self.canvas.bind('<ButtonRelease-1>', self.handlers.on_canvas_release)
        self.canvas.bind('<Delete>', self.petriNetwork.delete_selected)
        self.canvas.bind('<BackSpace>', self.petriNetwork.delete_selected)
        self.canvas.bind('<Button-3>', self.handlers.on_right_click)
        self.root.bind_all('<ButtonRelease-1>', self.handlers.on_global_button_release, add='+')
        
    def load_from_file(self):
        """Загружает сеть и перевешивает биндинги на новые элементы."""
        self.saveload.load_from_file()
        self._rebind_all_elements()

    def _bind_element(self, elem_type: str, name: str):
        """
        Навешивает события мыши на элемент после его создания или переименования.
        PetriNetwork не знает об editor — поэтому биндинги ставит editor.
        """
        data = self.petriNetwork.places[name] if elem_type == 'place' \
            else self.petriNetwork.transitions[name]
        elem = data['element']
        
        for cid in elem.canvas_ids:
            for seq in ['<Button-1>', '<Control-Button-1>', '<B1-Motion>',
                        '<ButtonRelease-1>', '<Button-3>', '<Enter>', '<Leave>',
                        '<Double-Button-1>']:
                self.canvas.tag_unbind(cid, seq)
        if elem.text_id:
            for seq in ['<Button-1>', '<Control-Button-1>', '<B1-Motion>',
                        '<ButtonRelease-1>', '<Button-3>', '<Enter>', '<Leave>',
                        '<Double-Button-1>']:
                self.canvas.tag_unbind(elem.text_id, seq)

        for cid in elem.canvas_ids + ([elem.text_id] if elem.text_id else []):
            self.canvas.tag_bind(
                cid, '<Button-1>',
                lambda e, n=name, t=elem_type: self.handlers.on_element_button1(t, n, e)
            )
            self.canvas.tag_bind(
                cid, '<Button-3>',
                lambda e, n=name, t=elem_type: self.handlers.on_right_click(e, t, n)
            )
            show_all = getattr(self, 'show_all_names', True)
            if not show_all:
                self.canvas.tag_bind(cid, '<Enter>', lambda e, el=elem: el.show_name())
                self.canvas.tag_bind(cid, '<Leave>', lambda e, el=elem: el.hide_name())

    def _rebind_all_elements(self):
        """Перевешивает биндинги на все элементы — нужно после load_from_file."""
        for name in self.petriNetwork.places:
            self._bind_element('place', name)
        for name in self.petriNetwork.transitions:
            self._bind_element('transition', name)

    def after_load(self):
        """Вызывается после загрузки сети — перевешивает биндинги на новые элементы."""
        self._rebind_all_elements()
        
    def rename_element(self, elem_type: str, name: str):
        """Обёртка: переименовывает элемент и обновляет биндинги + selection."""
        new_name = self.petriNetwork.rename_element(elem_type, name)
        if new_name:
            self._bind_element(elem_type, new_name)
            self.petriNetwork.select_element(elem_type, new_name)