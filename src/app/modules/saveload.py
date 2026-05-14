import json
from tkinter import messagebox, filedialog

from app.modules.petrinetwork import PetriNetwork
import tkinter as tk


class saveload:
    def __init__(self, canvas: tk.Canvas, root: tk.Tk, network: PetriNetwork):
        self.canvas = canvas
        self.root = root
        self.network = network
        self.real_object_map = {}
        self.initial_marking = {}

    def get_network_data(self) -> dict:
        return {
            'places': {
                name: {'x': d['element'].x, 'y': d['element'].y, 'tokens': d['tokens']}
                for name, d in self.network.places.items()
            },
            'transitions': {
                name: {
                    'x': d['element'].x,
                    'y': d['element'].y,
                    'priority': d['element'].priority,
                    'label': d['element'].label,
                    'delay': d['element'].delay,
                    'rotated': d['element'].rotated,
                }
                for name, d in self.network.transitions.items()
            },
            'arcs': [
                {'source': a.source.name, 'target': a.target.name,
                 'weight': a.weight, 'type': a.arc_type}
                for a in self.network.arcs
            ],
            'groups': self.network.groups,
            'real_objects': self.real_object_map,
            'initial_marking': self.initial_marking,
        }

    def load_network_data(self, data: dict):
        self.canvas.delete('all')
        self.network.places.clear()
        self.network.transitions.clear()
        self.network.arcs.clear()
        self.real_object_map = data.get('real_objects', {})
        self.initial_marking = data.get('initial_marking', {})

        element_map = {}
        for name, pdata in data['places'].items():
            self.network.create_place(pdata['x'], pdata['y'], name, pdata['tokens'])
            element_map[name] = self.network.places[name]['element']

        for name, tdata in data['transitions'].items():
            self.network.create_transition(
                tdata['x'], tdata['y'], name,
                priority=tdata.get('priority', 1),
                label=tdata.get('label', ""),
                delay=tdata.get('delay', 0)
            )
            if tdata.get('rotated', False):
                self.network.transitions[name]['element'].rotate()
            element_map[name] = self.network.transitions[name]['element']

        for arc_data in data['arcs']:
            source = element_map.get(arc_data['source'])
            target = element_map.get(arc_data['target'])
            if source and target:
                self.network.create_arc(source, target,
                                        arc_data.get('weight', 1),
                                        arc_data.get('type', 'normal'))

        # Загрузить группы
        self.network.groups = data.get('groups', [])

    def save_to_file(self):
        filename = filedialog.asksaveasfilename(
            defaultextension=".json",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")],
            parent=self.root
        )
        if filename:
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(self.get_network_data(), f, ensure_ascii=False, indent=2)
            messagebox.showinfo("Сохранено", f"Сеть сохранена в {filename}", parent=self.root)

    def load_from_file(self):
        filename = filedialog.askopenfilename(
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")],
            parent=self.root
        )
        if filename:
            with open(filename, 'r', encoding='utf-8') as f:
                data = json.load(f)
            self.load_network_data(data)
            messagebox.showinfo("Загружено", f"Сеть загружена из {filename}", parent=self.root)