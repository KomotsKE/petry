import math
from typing import Dict, Tuple
import tkinter as tk

class PetriNetElement:
    def __init__(self, canvas: tk.Canvas, x, y, name, element_type, radius=25, width=5, height=40):
        self.canvas = canvas
        self.x = x
        self.y = y
        self.name = name
        self.type = element_type  # 'place' или 'transition'
        self.radius = radius          # для позиции
        self.width = width            # полуширина перехода
        self.height = height        # полувысота перехода
        self.token_radius = 3
        self.canvas_ids = []          # ID основных фигур
        self.text_id = None
        self.token_ids = []           # ID фишек (только для позиции)
        self.input_arcs : list[Arc] = []
        self.output_arcs : list[Arc] = []
        self.name_hidden = True 
        
    def draw(self, tokens=0):
        """Отрисовывает элемент на холсте"""
        if self.type == 'place':
            # Круг
            x1, y1 = self.x - self.radius, self.y - self.radius
            x2, y2 = self.x + self.radius, self.y + self.radius
            circle_id = self.canvas.create_oval(x1, y1, x2, y2,
                                                fill='white', outline='black', width=2)
            self.canvas_ids = [circle_id]
        else:
            # Прямоугольник
            x1, y1 = self.x - self.width, self.y - self.height
            x2, y2 = self.x + self.width, self.y + self.height
            rect_id = self.canvas.create_rectangle(x1, y1, x2, y2,
                                                   fill='lightgray', outline='black', width=2)
            self.canvas_ids = [rect_id]
        # Текст (имя) - изначально скрыто
        self._draw_name()
        # Фишки, если есть
        if self.type == 'place' and tokens > 0:
            self.redraw_tokens(tokens)
            
    def _draw_name(self):
        """Рисует имя элемента снизу по центру"""
        if self.text_id:
            self.canvas.delete(self.text_id)

        if self.name_hidden:
            self.text_id = None
            return

        # Позиция текста: снизу по центру элемента
        if self.type == 'place':
            text_x = self.x
            text_y = self.y + self.radius + 12
        else:
            text_x = self.x
            text_y = self.y + self.height + 12

        self.text_id = self.canvas.create_text(text_x, text_y, text=self.name,
                                               font=('Arial', 9, 'normal'), fill='black')
        
    def show_name(self):
        if not self.name_hidden:
            return
        self.name_hidden = False
        self._draw_name()

    def hide_name(self):
        if self.name_hidden:
            return
        self.name_hidden = True
        self._draw_name()
    
    def redraw_tokens(self, tokens):
        """Перерисовывает фишки позиции"""
        # Удаляем старые
        for tid in self.token_ids:
            self.canvas.delete(tid)
        self.token_ids.clear()
        if tokens == 0:
            return
        
        r = self.token_radius  # радиус фишки
        # Позиции фишек относительно центра
        positions = []
        if tokens == 1:
            positions = [(0, 0)]
        elif tokens == 2:
            positions = [(-6, 6), (6, -6)]
        elif tokens == 3:
            positions = [(0, -8), (-7, 5), (7, 5)]
        elif tokens == 4:
            positions = [(-6, -6), (6, -6), (-6, 6), (6, 6)]
        else:
            for i in range(tokens):
                angle = 2 * math.pi * i / tokens
                positions.append((self.radius * 0.32 * math.cos(angle),
                                  self.radius * 0.32 * math.sin(angle)))
        for dx, dy in positions:
            tid = self.canvas.create_oval(
                self.x + dx - r, self.y + dy - r,
                self.x + dx + r, self.y + dy + r,
                fill='black'
            )
            self.token_ids.append(tid)
    
    def move(self, dx, dy):
        self.x += dx
        self.y += dy
        for cid in self.canvas_ids:
            self.canvas.move(cid, dx, dy)
        if self.text_id:
            self.canvas.move(self.text_id, dx, dy)
        for tid in self.token_ids:
            self.canvas.move(tid, dx, dy)
        for arc in self.input_arcs + self.output_arcs:
            arc.update_position()
    
    def get_connection_point(self, target_x, target_y):
        """Точка на границе элемента для соединения с дугой"""
        if self.type == 'place':
            dx = target_x - self.x
            dy = target_y - self.y
            dist = math.hypot(dx, dy)
            if dist == 0:
                return self.x + self.radius, self.y
            return self.x + dx / dist * self.radius, self.y + dy / dist * self.radius
        else:  # transition
            dx = target_x - self.x
            dy = target_y - self.y
            if dx == 0 and dy == 0:
                return self.x + self.width, self.y
            # Параметры пересечения с вертикальной и горизонтальной гранями
            t_x = self.width / abs(dx) if dx != 0 else float('inf')
            t_y = self.height / abs(dy) if dy != 0 else float('inf')
            if t_x < t_y:
                x = self.x + (self.width if dx > 0 else -self.width)
                y = self.y + dy * t_x
            else:
                y = self.y + (self.height if dy > 0 else -self.height)
                x = self.x + dx * t_y
            return x, y
    
    def highlight(self, color='red', width=3):
        """Подсветка элемента"""
        
        for cid in self.canvas_ids:
            self.canvas.itemconfig(cid, outline=color, width=width)
    
    def clear_highlight(self):
        for cid in self.canvas_ids:
            self.canvas.itemconfig(cid, outline='black', width=2)


class Arc:
    """Дуга между элементами сети Петри"""
    def __init__(self, canvas, source, target, weight=1, arc_type='normal'):
        self.canvas = canvas
        self.source = source
        self.target = target
        self.weight = weight
        self.arc_type = arc_type  # 'normal' или 'inhibitor'
        self.uid = f"{id(self)}"
        self.offset_index = 0  # для визуального разведения параллельных/встречных дуг
        self.source_anchor = None
        self.target_anchor = None
        self.line_id = None
        self.arrow_id = None
        self.text_id = None
        self.selected = False
        
    def draw(self):
        """Рисует дугу со стрелкой и весом"""
        self.update_position()
        
    def update_position(self):
        """Обновляет позицию дуги при перемещении элементов"""
        if self.line_id:
            self.canvas.delete(self.line_id)
        if self.arrow_id:
            self.canvas.delete(self.arrow_id)
        if self.text_id:
            self.canvas.delete(self.text_id)
            
        start_x, start_y = self.source.get_connection_point(self.target.x, self.target.y)
        end_x, end_y = self.target.get_connection_point(self.source.x, self.source.y)
        
        # Визуальное разведение дуг (если есть встречная дуга — смещаем)
        dx = end_x - start_x
        dy = end_y - start_y
        length = math.sqrt(dx * dx + dy * dy) or 1.0
        nx = -dy / length
        ny = dx / length
        offset = 12 * self.offset_index
        if offset != 0:
            start_x += nx * offset
            start_y += ny * offset
            end_x += nx * offset
            end_y += ny * offset

        # Рисуем линию (всегда однонаправленная: стрелка только на конце)
        if self.arc_type == 'inhibitor':
            self.line_id = self.canvas.create_line(start_x, start_y, end_x, end_y,
                                                    fill='red', width=2, arrow=tk.LAST,
                                                    arrowshape=(10, 12, 5), dash=(5, 3),
                                                    tags=("arc", f"arc:{self.uid}"))
        else:
            self.line_id = self.canvas.create_line(start_x, start_y, end_x, end_y,
                                                    fill='black', width=2, arrow=tk.LAST,
                                                    arrowshape=(10, 12, 5),
                                                    tags=("arc", f"arc:{self.uid}"))
        
        # Рисуем вес
        mid_x = (start_x + end_x) / 2
        mid_y = (start_y + end_y) / 2
        if self.weight > 1:
            self.text_id = self.canvas.create_text(mid_x + 10, mid_y - 10, 
                                                    text=str(self.weight), 
                                                    fill='blue', font=('Arial', 10, 'bold'),
                                                    tags=("arc", f"arc:{self.uid}"))
    
    def delete(self):
        """Удаляет дугу с canvas"""
        if self.line_id:
            self.canvas.delete(self.line_id)
        if self.arrow_id:
            self.canvas.delete(self.arrow_id)
        if self.text_id:
            self.canvas.delete(self.text_id)

    def set_properties(self, weight: int, arc_type: str):
        self.weight = max(1, int(weight))
        self.arc_type = arc_type if arc_type in ("normal", "inhibitor") else "normal"
        self.update_position()
