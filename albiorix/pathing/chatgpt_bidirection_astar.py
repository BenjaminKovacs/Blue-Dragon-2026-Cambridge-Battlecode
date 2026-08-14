import heapq
import time
from math import hypot


def heuristic(a, b):
    # Euclidean works well on grids
    return hypot(a[0] - b[0], a[1] - b[1])


def neighbors(pos, grid):
    x, y = pos
    for dx, dy in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
        nx, ny = x + dx, y + dy
        if 0 <= nx < len(grid) and 0 <= ny < len(grid[0]):
            yield (nx, ny)


class BiAStarState:
    def __init__(self):
        self.prev_target = None
        self.dist_back = None
        self.parent_back = None
        self.open_back = []
        self.finished = False


def is_target_close(t1, t2, threshold=5):
    return heuristic(t1, t2) <= threshold


def reconstruct_path(parents, end):
    path = []
    cur = end
    while cur in parents:
        path.append(cur)
        cur = parents[cur]
    path.append(cur)
    return path[::-1]


def reconstruct_backward(parent_back, meet, target):
    path = []
    cur = meet
    while cur != target:
        path.append(cur)
        cur = parent_back.get(cur)
        if cur is None:
            break
    if cur:
        path.append(target)
    return path


def bidir_astar_step(state, start, target, grid, time_budget=0.01):
    t0 = time.time()

    # --- Reset backward search if needed ---
    if (
        state.prev_target is None
        or not is_target_close(state.prev_target, target)
        or state.finished
    ):
        state.dist_back = {target: 0}
        state.parent_back = {}
        state.open_back = [(0, target)]
        state.prev_target = target
        state.finished = False

    # --- Forward search always resets ---
    open_fwd = [(heuristic(start, target), 0, start)]
    dist_fwd = {start: 0}
    parent_fwd = {}

    meet_node = None
    best_meet_cost = float("inf")

    while time.time() - t0 < time_budget:
        # --- Forward step ---
        if open_fwd:
            _, g, cur = heapq.heappop(open_fwd)

            if cur in state.dist_back:
                total_cost = g + state.dist_back[cur]
                if total_cost < best_meet_cost:
                    best_meet_cost = total_cost
                    meet_node = cur

            for nb in neighbors(cur, grid):
                cost = grid[nb[0]][nb[1]]
                new_g = g + cost
                if nb not in dist_fwd or new_g < dist_fwd[nb]:
                    dist_fwd[nb] = new_g
                    parent_fwd[nb] = cur
                    heapq.heappush(
                        open_fwd,
                        (new_g + heuristic(nb, target), new_g, nb),
                    )

        # --- Backward step ---
        if state.open_back:
            g_back, cur_back = heapq.heappop(state.open_back)

            for nb in neighbors(cur_back, grid):
                cost = grid[cur_back[0]][cur_back[1]]
                new_g = g_back + cost

                if nb not in state.dist_back or new_g < state.dist_back[nb]:
                    state.dist_back[nb] = new_g
                    state.parent_back[nb] = cur_back
                    heapq.heappush(state.open_back, (new_g, nb))

        # --- Early exit if exact meet found ---
        if meet_node is not None and best_meet_cost < float("inf"):
            break

        if not open_fwd and not state.open_back:
            state.finished = True
            break

    # --- If exact path found ---
    if meet_node is not None:
        path_fwd = reconstruct_path(parent_fwd, meet_node)
        path_back = reconstruct_backward(state.parent_back, meet_node, target)
        state.finished = True
        return path_fwd[:-1] + path_back

    # --- Otherwise: construct best partial path ---

    # pick best forward node connected to backward field
    best_node = None
    best_score = float("inf")

    for node, g in dist_fwd.items():
        if node in state.dist_back:
            score = g + state.dist_back[node]
            if score < best_score:
                best_score = score
                best_node = node

    if best_node:
        path_fwd = reconstruct_path(parent_fwd, best_node)
        path_back = reconstruct_backward(state.parent_back, best_node, target)
        return path_fwd[:-1] + path_back

    # fallback: straight-line bridge
    # (rare case when searches haven't connected yet)
    best_node = min(dist_fwd, key=lambda n: heuristic(n, target))
    path_fwd = reconstruct_path(parent_fwd, best_node)

    # simple straight line to target
    line = []
    x, y = best_node
    tx, ty = target
    while (x, y) != (tx, ty):
        if x < tx:
            x += 1
        elif x > tx:
            x -= 1
        elif y < ty:
            y += 1
        elif y > ty:
            y -= 1
        line.append((x, y))

    return path_fwd + line