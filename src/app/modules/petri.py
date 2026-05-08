from collections import deque
from dataclasses import dataclass
from typing import Dict, List, Tuple, Set


@dataclass(frozen=True)
class ModelArc:
    source: str
    target: str
    weight: int = 1
    arc_type: str = "normal"  # 'normal' или 'inhibitor'


class PetriNetModel:
    def __init__(self, places: List[str], transitions: List[str], arcs: List[ModelArc]):
        self.places = sorted(places)
        self.transitions = sorted(transitions)
        self.arcs = list(arcs)

        self._place_index = {p: i for i, p in enumerate(self.places)}
        self._in_arcs: Dict[str, List[ModelArc]] = {t: [] for t in self.transitions}
        self._out_arcs: Dict[str, List[ModelArc]] = {t: [] for t in self.transitions}

        for a in self.arcs:
            if a.arc_type not in ("normal", "inhibitor"):
                raise ValueError(f"Неизвестный тип дуги: {a.arc_type}")
            if a.weight < 0:
                raise ValueError(f"Вес дуги не может быть отрицательным: {a}")

            if a.source in self.places and a.target in self.transitions:
                self._in_arcs[a.target].append(a)
            elif a.source in self.transitions and a.target in self.places:
                self._out_arcs[a.source].append(a)
            else:
                raise ValueError(f"Некорректная дуга: {a}")

        # флаг обрезания графа достижимости
        self._last_rg_truncated = False

    def _validate_marking(self, marking: Tuple[int, ...]):
        if len(marking) != len(self.places):
            raise ValueError("Размер маркировки не совпадает с числом мест")
        if any(x < 0 for x in marking):
            raise ValueError("Маркировка содержит отрицательные значения")

    def enabled_transitions(self, marking: Tuple[int, ...]) -> Set[str]:
        self._validate_marking(marking)

        enabled: Set[str] = set()
        place_index = self._place_index

        for t in self.transitions:
            ok = True
            for a in self._in_arcs[t]:
                tokens = marking[place_index[a.source]]

                if a.arc_type == "inhibitor":
                    # поддержка веса: запрещает, если tokens >= weight
                    if tokens >= a.weight:
                        ok = False
                        break
                else:
                    if tokens < a.weight:
                        ok = False
                        break

            if ok:
                enabled.add(t)

        return enabled

    def fire(self, marking: Tuple[int, ...], transition: str) -> Tuple[int, ...]:
        self._validate_marking(marking)

        if transition not in self.transitions:
            raise KeyError(f"Неизвестный переход: {transition}")

        enabled = self.enabled_transitions(marking)
        if transition not in enabled:
            raise ValueError(f"Переход {transition} не разрешен в разметке {marking}")

        m = list(marking)
        place_index = self._place_index

        for a in self._in_arcs[transition]:
            if a.arc_type == "normal":
                idx = place_index[a.source]
                m[idx] -= a.weight

        for a in self._out_arcs[transition]:
            if a.arc_type == "normal":
                idx = place_index[a.target]
                m[idx] += a.weight

        # защита от некорректных состояний
        if any(x < 0 for x in m):
            raise RuntimeError("Отрицательная маркировка после firing — нарушение инварианта")

        return tuple(m)

    def reachability_graph(self, initial_marking: Tuple[int, ...], max_states: int = 5000):
        self._validate_marking(initial_marking)

        visited: Set[Tuple[int, ...]] = {initial_marking}
        queue = deque([initial_marking])
        edges: List[Tuple[Tuple[int, ...], str, Tuple[int, ...]]] = []
        enabled_cache: Dict[Tuple[int, ...], Set[str]] = {}

        self._last_rg_truncated = False

        while queue:
            if len(visited) >= max_states:
                self._last_rg_truncated = True
                break

            m = queue.popleft()
            en = self.enabled_transitions(m)
            enabled_cache[m] = en

            for t in en: 
                m2 = self.fire(m, t)
                edges.append((m, t, m2))

                if m2 not in visited:
                    visited.add(m2)
                    queue.append(m2)

        return visited, edges, enabled_cache

    def liveness_from_reachability(
        self,
        visited: Set[Tuple[int, ...]],
        edges: List[Tuple[Tuple[int, ...], str, Tuple[int, ...]]],
        enabled_cache: Dict[Tuple[int, ...], Set[str]]
    ):
        rev: Dict[Tuple[int, ...], List[Tuple[int, ...]]] = {m: [] for m in visited}

        for a, _, b in edges:
            if b in rev:
                rev[b].append(a)

        result: Dict[str, bool] = {}

        for t in self.transitions:
            enabling = {m for m in visited if t in enabled_cache.get(m, set())}

            if not enabling:
                result[t] = False
                continue

            can_reach = set(enabling)
            dq = deque(enabling)

            while dq:
                cur = dq.popleft()
                for prev in rev.get(cur, []):
                    if prev not in can_reach:
                        can_reach.add(prev)
                        dq.append(prev)

            result[t] = (len(can_reach) == len(visited))

        return result