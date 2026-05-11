import math
import tkinter as tk


class PetriNetElement:
    def __init__(self, canvas: tk.Canvas, x, y, name, element_type, radius=25, width=5, height=40):
        self.canvas = canvas
        self.x = x
        self.y = y
        self.name = name
        self.type = element_type
        self.radius = radius
        self.width = width
        self.height = height
        self.token_radius = 3
        self.canvas_ids = []
        self.text_id = None
        self.label_id = None
        self.token_ids = []
        self.input_arcs: list = []
        self.output_arcs: list = []
        self.name_hidden = False

        # Свойства перехода
        self.priority = 1
        self.label = ""
        self.labels_hidden = False
        self.delay = 0
        self.rotated = False       # горизонтальная ориентация перехода

    # ── Теги для canvas-объектов ───────────────────────────────────────────

    def _priority_badge_tag(self) -> str:
        return f"pbadge:{id(self)}"

    def _delay_badge_tag(self) -> str:
        return f"dbadge:{id(self)}"

    # ── Отрисовка ──────────────────────────────────────────────────────────

    def draw(self, tokens=0):
        if self.type == 'place':
            x1, y1 = self.x - self.radius, self.y - self.radius
            x2, y2 = self.x + self.radius, self.y + self.radius
            circle_id = self.canvas.create_oval(x1, y1, x2, y2,
                                                fill='white', outline='black', width=2)
            self.canvas_ids = [circle_id]
        else:
            x1, y1 = self.x - self.width, self.y - self.height
            x2, y2 = self.x + self.width, self.y + self.height
            rect_id = self.canvas.create_rectangle(x1, y1, x2, y2,
                                                   fill='lightgray', outline='black', width=2)
            self.canvas_ids = [rect_id]

        self._draw_name()
        self._draw_priority_badge()
        self._draw_delay_badge()
        if self.type == 'place' and tokens > 0:
            self.redraw_tokens(tokens)

    def _name_bottom_y(self) -> float:
        if self.type == 'place':
            return self.y + self.radius + 12
        return self.y + self.height + 12

    def _draw_name(self):
        if self.text_id:
            self.canvas.delete(self.text_id)
            self.text_id = None
        if not self.name_hidden:
            self.text_id = self.canvas.create_text(
                self.x, self._name_bottom_y(),
                text=self.name, font=('Arial', 9, 'normal'), fill='black'
            )
        self._draw_label()

    def _draw_label(self):
        if self.label_id:
            self.canvas.delete(self.label_id)
            self.label_id = None
        if self.type != 'transition' or not self.label or self.labels_hidden:
            return
        base_y = self._name_bottom_y()
        label_y = base_y + (14 if not self.name_hidden else 0)
        self.label_id = self.canvas.create_text(
            self.x, label_y,
            text=f"[{self.label}]",
            font=('Arial', 8, 'italic'),
            fill='#444'
        )

    def _draw_priority_badge(self):
        tag = self._priority_badge_tag()
        for cid in self.canvas.find_withtag(tag):
            self.canvas.delete(cid)
        if self.type != 'transition' or self.priority <= 1:
            return
        bx = self.x + self.width - 1
        by = self.y - self.height + 1
        r = 8
        self.canvas.create_oval(bx - r, by - r, bx + r, by + r,
                                 fill='#e53935', outline='white', width=1, tags=(tag,))
        self.canvas.create_text(bx, by, text=str(self.priority),
                                 font=('Arial', 7, 'bold'), fill='white', tags=(tag,))

    def _draw_delay_badge(self):
        tag = self._delay_badge_tag()
        for cid in self.canvas.find_withtag(tag):
            self.canvas.delete(cid)
        if self.type != 'transition' or self.delay <= 0:
            return
        base_y = self._name_bottom_y()
        offset = 0
        if not self.name_hidden:
            offset += 14
        if self.label:
            offset += 14
        text = f"⏱{self.delay}ms" if self.delay < 1000 else f"⏱{self.delay // 1000}s"
        self.canvas.create_text(
            self.x, base_y + offset,
            text=text,
            font=('Arial', 10, 'bold'),
            fill='#1565c0',
            anchor='n',
            tags=(tag,)
        )

    # ── Публичные методы обновления ────────────────────────────────────────

    def redraw_label(self):
        self._draw_label()

    def redraw_priority(self):
        self._draw_priority_badge()

    def redraw_delay(self):
        self._draw_delay_badge()

    def rotate(self):
        """Поворачивает переход на 90°, меняя width и height местами."""
        if self.type != 'transition':
            return
        self.width, self.height = self.height, self.width
        self.rotated = not self.rotated
        # Обновляем прямоугольник без пересоздания
        x1, y1 = self.x - self.width, self.y - self.height
        x2, y2 = self.x + self.width, self.y + self.height
        self.canvas.coords(self.canvas_ids[0], x1, y1, x2, y2)
        # Перерисовываем бейджи и подписи
        self._draw_priority_badge()
        self._draw_delay_badge()
        self._draw_name()
        # Обновляем все дуги
        for arc in self.input_arcs + self.output_arcs:
            arc.update_position()

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
        for tid in self.token_ids:
            self.canvas.delete(tid)
        self.token_ids.clear()
        if tokens == 0:
            return
        r = self.token_radius
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
        if self.label_id:
            self.canvas.move(self.label_id, dx, dy)
        for tid in self.token_ids:
            self.canvas.move(tid, dx, dy)
        for cid in self.canvas.find_withtag(self._priority_badge_tag()):
            self.canvas.move(cid, dx, dy)
        for cid in self.canvas.find_withtag(self._delay_badge_tag()):
            self.canvas.move(cid, dx, dy)
        for arc in self.input_arcs + self.output_arcs:
            arc.update_position()

    def delete_from_canvas(self):
        """Удаляет все canvas-объекты элемента включая бейджи."""
        for cid in self.canvas_ids:
            self.canvas.delete(cid)
        if self.text_id:
            self.canvas.delete(self.text_id)
        if self.label_id:
            self.canvas.delete(self.label_id)
        for tid in self.token_ids:
            self.canvas.delete(tid)
        for cid in self.canvas.find_withtag(self._priority_badge_tag()):
            self.canvas.delete(cid)
        for cid in self.canvas.find_withtag(self._delay_badge_tag()):
            self.canvas.delete(cid)

    def get_connection_point(self, target_x, target_y):
        if self.type == 'place':
            dx = target_x - self.x
            dy = target_y - self.y
            dist = math.hypot(dx, dy)
            if dist == 0:
                return self.x + self.radius, self.y
            r = self.radius + 1  # внешний край обводки (border=2px)
            return round(self.x + dx / dist * r), round(self.y + dy / dist * r)
        else:
            dx = target_x - self.x
            dy = target_y - self.y
            if dx == 0 and dy == 0:
                return self.x + self.width, self.y
            t_x = self.width / abs(dx) if dx != 0 else float('inf')
            t_y = self.height / abs(dy) if dy != 0 else float('inf')
            if t_x < t_y:
                bx = self.x + (self.width if dx > 0 else -self.width)
                by = self.y + dy * t_x
            else:
                by = self.y + (self.height if dy > 0 else -self.height)
                bx = self.x + dx * t_y
            # Сдвигаем точку на 1px наружу от центра — равномерно по любому углу
            d = math.hypot(bx - self.x, by - self.y)
            if d > 0:
                bx += (bx - self.x) / d
                by += (by - self.y) / d
            return round(bx), round(by)

    def highlight(self, color='red', width=3):
        for cid in self.canvas_ids:
            self.canvas.itemconfig(cid, outline=color, width=width)

    def clear_highlight(self):
        for cid in self.canvas_ids:
            self.canvas.itemconfig(cid, outline='black', width=2)

    def show_pending(self):
        for cid in self.canvas_ids:
            self.canvas.itemconfig(cid, fill='#FFB300', outline='#E65100', width=2)

    def clear_pending(self):
        for cid in self.canvas_ids:
            self.canvas.itemconfig(cid, fill='lightgray', outline='black', width=2)


class Arc:
    def __init__(self, canvas, source, target, weight=1, arc_type='normal'):
        self.canvas = canvas
        self.source = source
        self.target = target
        self.weight = weight
        self.arc_type = arc_type
        self.uid = f"{id(self)}"
        self.offset_index = 0
        self.line_id = None
        self.arrow_id = None
        self.text_id = None
        self.selected = False

    def draw(self):
        self.update_position()

    def update_position(self):
        if self.line_id:
            self.canvas.delete(self.line_id)
        if self.arrow_id:
            self.canvas.delete(self.arrow_id)
        if self.text_id:
            self.canvas.delete(self.text_id)

        # Начальное приближение: направление центр→центр
        start_x, start_y = self.source.get_connection_point(self.target.x, self.target.y)
        end_x, end_y = self.target.get_connection_point(self.source.x, self.source.y)

        # Уточняем точки через реальное направление дуги (2 итерации)
        for _ in range(2):
            start_x, start_y = self.source.get_connection_point(end_x, end_y)
            end_x, end_y = self.target.get_connection_point(start_x, start_y)

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

        fill = 'red' if self.arc_type == 'inhibitor' else 'black'
        dash = (5, 3) if self.arc_type == 'inhibitor' else None
        kwargs = dict(fill=fill, width=2, arrow=tk.LAST, arrowshape=(10, 12, 5),
                      tags=("arc", f"arc:{self.uid}"))
        if dash:
            kwargs['dash'] = dash
        self.line_id = self.canvas.create_line(start_x, start_y, end_x, end_y, **kwargs)

        mid_x = (start_x + end_x) / 2
        mid_y = (start_y + end_y) / 2
        if self.weight > 1:
            self.text_id = self.canvas.create_text(
                mid_x + 10, mid_y - 10,
                text=str(self.weight),
                fill='blue', font=('Arial', 10, 'bold'),
                tags=("arc", f"arc:{self.uid}"))

    def delete(self):
        """Удаляет все canvas-объекты дуги."""
        for attr in ('line_id', 'arrow_id', 'text_id'):
            cid = getattr(self, attr)
            if cid:
                self.canvas.delete(cid)
                setattr(self, attr, None)

    def set_properties(self, weight: int, arc_type: str):
        self.weight = max(1, int(weight))
        self.arc_type = arc_type if arc_type in ("normal", "inhibitor") else "normal"
        self.update_position()