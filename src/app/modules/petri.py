from collections import deque
from dataclasses import dataclass
from typing import Dict, List, Tuple, Set, Optional

# ω — символ бесконечности для графа покрываемости
OMEGA = float('inf')


def _omega_ge(a, b) -> bool:
    """a >= b с учётом ω."""
    if a == OMEGA:
        return True
    if b == OMEGA:
        return False
    return a >= b


def _omega_sub(a, w) -> float:
    """a - w с учётом ω: ω - n = ω."""
    if a == OMEGA:
        return OMEGA
    return a - w


def _omega_add(a, w) -> float:
    """a + w с учётом ω: ω + n = ω."""
    if a == OMEGA:
        return OMEGA
    return a + w


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

        self._last_rg_truncated = False

    def _validate_marking(self, marking: Tuple):
        if len(marking) != len(self.places):
            raise ValueError("Размер маркировки не совпадает с числом мест")
        if any(x < 0 for x in marking if x != OMEGA):
            raise ValueError("Маркировка содержит отрицательные значения")

    def enabled_transitions(self, marking: Tuple) -> Set[str]:
        self._validate_marking(marking)

        enabled: Set[str] = set()
        place_index = self._place_index

        for t in self.transitions:
            # Переход без входных дуг никогда не активен
            if not self._in_arcs[t]:
                continue

            ok = True
            for a in self._in_arcs[t]:
                tokens = marking[place_index[a.source]]

                if a.arc_type == "inhibitor":
                    # inhibitor с ω: ω >= weight → заблокирован
                    if _omega_ge(tokens, a.weight):
                        ok = False
                        break
                else:
                    if not _omega_ge(tokens, a.weight):
                        ok = False
                        break

            if ok:
                enabled.add(t)

        return enabled

    def fire(self, marking: Tuple, transition: str) -> Tuple:
        """Срабатывание перехода. Поддерживает ω-маркировки."""
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
                m[idx] = _omega_sub(m[idx], a.weight)

        for a in self._out_arcs[transition]:
            if a.arc_type == "normal":
                idx = place_index[a.target]
                m[idx] = _omega_add(m[idx], a.weight)

        if any(x < 0 for x in m if x != OMEGA):
            raise RuntimeError("Отрицательная маркировка после firing — нарушение инварианта")

        return tuple(m)

    # ------------------------------------------------------------------ #
    #  Граф покрываемости (Карп-Миллер)                                  #
    # ------------------------------------------------------------------ #

    def coverability_graph(self, initial_marking: Tuple[int, ...]):
        """
        Строит граф покрываемости методом Карпа-Миллера.

        Возвращает:
            visited  – множество ω-маркировок (узлов)
            edges    – список (from, transition, to)
            is_unbounded – True если хоть одно место получило ω
        """
        self._validate_marking(initial_marking)

        # Каждый узел: (marking, ancestor_chain)
        # ancestor_chain — список маркировок от корня до текущего (включительно)
        root = tuple(initial_marking)
        visited: Set[Tuple] = {root}
        # Для каждого узла храним его предков (путь от корня)
        ancestors: Dict[Tuple, List[Tuple]] = {root: []}

        queue: deque = deque([root])
        edges: List[Tuple[Tuple, str, Tuple]] = []
        is_unbounded = False

        while queue:
            m = queue.popleft()
            anc = ancestors[m]

            for t in self.enabled_transitions(m):
                m_new_list = list(self.fire(m, t))

                # Проверяем, покрывает ли m_new какого-либо предка
                for m_anc in anc:
                    if all(_omega_ge(m_new_list[i], m_anc[i])
                           for i in range(len(self.places))):
                        # m_new >= m_anc → места, где строго больше, → ω
                        for i in range(len(self.places)):
                            if m_new_list[i] != OMEGA and m_new_list[i] > m_anc[i]:
                                m_new_list[i] = OMEGA
                                is_unbounded = True

                m_new = tuple(m_new_list)
                edges.append((m, t, m_new))

                if m_new not in visited:
                    visited.add(m_new)
                    ancestors[m_new] = anc + [m]
                    queue.append(m_new)

        return visited, edges, is_unbounded

    # ------------------------------------------------------------------ #
    #  Реграф достижимости (только для ограниченных сетей)               #
    # ------------------------------------------------------------------ #

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

    # ------------------------------------------------------------------ #
    #  Живость                                                            #
    # ------------------------------------------------------------------ #

    def is_self_sustaining(self, transition: str) -> bool:
        """
        Переход структурно самодостаточен, если для каждого входного места
        он возвращает не меньше токенов, чем забирает.
        Такой переход живой по структуре в неограниченных сетях.
        """
        place_index = self._place_index
        consume: Dict[int, int] = {}
        produce: Dict[int, int] = {}

        for a in self._in_arcs[transition]:
            if a.arc_type == "normal":
                idx = place_index[a.source]
                consume[idx] = consume.get(idx, 0) + a.weight

        for a in self._out_arcs[transition]:
            if a.arc_type == "normal":
                idx = place_index[a.target]
                produce[idx] = produce.get(idx, 0) + a.weight

        for idx, w in consume.items():
            if produce.get(idx, 0) < w:
                return False
        return True

    def liveness_from_coverability(
        self,
        visited: Set[Tuple],
        edges: List[Tuple[Tuple, str, Tuple]],
        is_unbounded: bool,
    ) -> Dict[str, object]:
        """
        Проверяет живость по графу покрываемости.
        Возвращает словарь {transition: True | False | '?'}
        '?' — переход не самодостаточен и граф был обрезан (неопределённо).
        """
        # Строим кеш: какие переходы активны в каждой маркировке
        enabled_cache: Dict[Tuple, Set[str]] = {}
        for m, t, m2 in edges:
            if m not in enabled_cache:
                enabled_cache[m] = self.enabled_transitions(m)

        # Для узлов без исходящих рёбер
        for m in visited:
            if m not in enabled_cache:
                enabled_cache[m] = self.enabled_transitions(m)

        # Обратные рёбра для обхода в ширину
        rev: Dict[Tuple, List[Tuple]] = {m: [] for m in visited}
        for a, _, b in edges:
            if b in rev:
                rev[b].append(a)

        result: Dict[str, object] = {}

        for t in self.transitions:
            enabling = {m for m in visited if t in enabled_cache.get(m, set())}

            if not enabling:
                # Если сеть неограничена и переход самодостаточен → живой
                if is_unbounded and self.is_self_sustaining(t):
                    result[t] = True
                else:
                    result[t] = False
                continue

            # BFS назад: из всех активирующих состояний
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

    def liveness_from_reachability(
        self,
        visited: Set[Tuple[int, ...]],
        edges: List[Tuple[Tuple[int, ...], str, Tuple[int, ...]]],
        enabled_cache: Dict[Tuple[int, ...], Set[str]]
    ) -> Dict[str, object]:
        rev: Dict[Tuple, List[Tuple]] = {m: [] for m in visited}

        for a, _, b in edges:
            if b in rev:
                rev[b].append(a)

        result: Dict[str, object] = {}

        for t in self.transitions:
            enabling = {m for m in visited if t in enabled_cache.get(m, set())}

            if not enabling:
                if self._last_rg_truncated and self.is_self_sustaining(t):
                    result[t] = True
                else:
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

            if len(can_reach) == len(visited):
                result[t] = True
            elif self._last_rg_truncated and self.is_self_sustaining(t):
                result[t] = True
            else:
                result[t] = len(can_reach) == len(visited)

        return result

    def is_unbounded(self, initial_marking: Tuple[int, ...]) -> bool:
        """Быстрая проверка: неограничена ли сеть."""
        _, _, unbounded = self.coverability_graph(initial_marking)
        return unbounded