from collections import deque

DIRS = [(1, 0), (-1, 0), (0, 1), (0, -1),
        (1, 1), (1, -1), (-1, 1), (-1, -1)]


def neighbors(pos):
    x, y = pos
    for dx, dy in DIRS:
        yield (x + dx, y + dy)


def bfs_all_distances(start, built):
    """
    Standard BFS that returns distance from start to every reachable built tile.
    """
    queue = deque([start])
    dist = {start: 0}

    while queue:
        cur = queue.popleft()
        for nxt in neighbors(cur):
            if nxt in built and nxt not in dist:
                dist[nxt] = dist[cur] + 1
                queue.append(nxt)

    return dist


def bfs_best_goal(start, goals, built, next_target=None):
    """
    First BFS: find all closest goals.
    Second BFS (if needed): choose goal closest to next_target.
    """
    queue = deque([start])
    parent = {start: None}
    dist = {start: 0}

    found_goals = []
    min_dist = None

    # --- First BFS: find all closest goals ---
    while queue:
        cur = queue.popleft()
        d = dist[cur]

        if min_dist is not None and d > min_dist:
            break

        if cur in goals:
            if min_dist is None:
                min_dist = d
            found_goals.append(cur)
            continue

        for nxt in neighbors(cur):
            if nxt in built and nxt not in dist:
                dist[nxt] = d + 1
                parent[nxt] = cur
                queue.append(nxt)

    if not found_goals:
        return None

    # --- Tie-break using second BFS ---
    if next_target is not None and len(found_goals) > 1:
        # Only consider tiles we could stand on to build next_target
        next_build_positions = {n for n in neighbors(next_target) if n in built}

        if next_build_positions:
            # Reverse BFS from all next build positions at once
            queue = deque(next_build_positions)
            dist2 = {pos: 0 for pos in next_build_positions}

            while queue:
                cur = queue.popleft()
                for nxt in neighbors(cur):
                    if nxt in built and nxt not in dist2:
                        dist2[nxt] = dist2[cur] + 1
                        queue.append(nxt)

            # Pick goal with smallest distance to next build region
            best_goal = min(
                found_goals,
                key=lambda g: dist2.get(g, float('inf'))
            )
        else:
            best_goal = found_goals[0]
    else:
        best_goal = found_goals[0]

    # --- Reconstruct path ---
    path = []
    cur = best_goal
    while cur is not None:
        path.append(cur)
        cur = parent[cur]

    return path[::-1]


def generate_bot_moves(start_pos, initial_built, build_order):
    built = set(initial_built)
    assert start_pos in built

    path_taken = [start_pos]
    current_pos = start_pos

    for i, target in enumerate(build_order):
        next_target = build_order[i + 1] if i + 1 < len(build_order) else None

        build_positions = {n for n in neighbors(target) if n in built}
        if not build_positions:
            raise ValueError(f"Cannot build {target}")

        path = bfs_best_goal(current_pos, build_positions, built, next_target)
        if path is None:
            raise ValueError(f"No path to build {target}")

        path_taken.extend(path[1:])
        current_pos = path[-1]

        built.add(target)

    return path_taken

path_0 = [
    ("pair", (7, 9), (7, 8)),
    ("pair", (7, 10), (7, 9)),
    ("pair", (7, 11), (7, 10)),
    ("single", (7, 12)),
    ("single", (6, 11)),
    ("single", (8, 11)),
    ("single", (6, 10)),
   # ("pair", (7, 10), (5, 10)),
    ("pair", (6, 10), (5, 11)),
    ("pair", (5, 10), (5, 11)),
    ("pair", (4, 11), (5, 11)),
    ("single", (4, 12)),
    ("pair", (3, 11), (3, 10)),
    ("single", (3, 12)),
    ("pair", (3, 10), (3, 9)),
    ("single", (2, 11)),
    ("pair", (2, 10), (3, 10)),
    ("pair", (1, 10), (2, 10)),
    ("pair", (1, 11), (1, 10)),
    ("single", (1, 12)),
    ("single", (0, 11)),
    ("pair", (4, 13), (4, 10)),
    ("pair", (4, 10), (6, 8)),
    ("pair", (4, 13), (4, 10)),
    ("pair", (3, 14), (4, 14)),
    ("pair", (3, 15), (3, 14)),
    ("pair", (2, 15), (3, 15)),
    ("pair", (1, 15), (2, 15)),
    ("single", (0, 15)),
    ("single", (1, 16)),
    ("single", (2, 16)),
    ("single", (1, 17)),
    ("pair", (1, 18), (2, 18)),
    ("pair", (1, 19), (1, 18)),
    ("single", (1, 20)),
    ("single", (0, 19)),
    ("pair", (2, 18), (3, 18)),
    ("pair", (3, 18), (4, 18)),
    ("single", (2, 19)),
    ("pair", (4, 18), (4, 17)),
    ("pair", (4, 19), (4, 16)),
    ("single", (4, 19)),
    ("pair", (4, 17), (4, 14)),
    ("single", (3, 16)),
    ("single", (5, 16)),
    ("single", (4, 15))
]

path_1 = [
    ("pair", (6, 5), (5, 5)),
    #("single", (5, 5)),
    ("pair", (5, 5), (5, 6)),
    ("pair", (5, 5), (4, 5)),
    #("single", (6, 5)),
    #("single", (5, 5)),
    ("pair", (5, 6), (5, 7)),
    ("pair", (5, 7), (5, 8)),
    ("pair", (5, 8), (5, 9)),
    ("pair", (5, 9), (6, 9)),
    ("pair", (6, 9), (7, 9)),
    ("single", (7, 9)),
    ("pair", (8, 10), (9, 10)),
    ("pair", (9, 10), (10, 10)),
    ("pair", (10, 10), (11, 10)),
    ("pair", (11, 10), (11, 9)),
    ("single", (10, 11)),
    ("pair", (11, 11), (11, 10)),
    ("single", (11, 12)),
    ("single", (12, 11)),
    ("pair", (11, 9), (11, 8)),
    ("pair", (11, 8), (11, 7)),
    ("pair", (11, 7), (11, 6)),
    ("pair", (12, 10), (11, 10)),
    ("pair", (13, 10), (12, 10)),
    ("pair", (13, 11), (13, 10))
]

path_2 = [
    ("pair", (4, 8), (6, 8)),
    ("single", (3, 7)),
    ("pair", (3, 7), (3, 8)),
    ("single", (3, 6)),
    ("single", (3, 8)),
    ("pair", (2, 7), (3, 7)),
    ("pair", (2, 6), (2, 7)),
    ("single", (2, 5)),
    ("pair", (1, 6), (2, 6)),
    ("pair", (1, 5), (1, 6)),
    ("single", (1, 4)),
    ("pair", (4, 4), (2, 6)),
    ("single", (4, 3)),
    ("pair", (5, 3), (5, 5)),
    ("single", (3, 4)),
    ("pair", (2, 3), (4, 1)),
    ("single", (2, 4)),
    ("single", (3, 3)),
    ("single", (2, 2)),
    ("single", (3, 2)),
    ("pair", (5, 2), (6, 2)),
    ("pair", (5, 1), (5, 2)),
    ("pair", (4, 1), (5, 1)),
    ("single", (3, 2)),
    ("pair", (3, 1), (4, 1)),
    ("pair", (6, 2), (7, 2)),
    ("pair", (7, 2), (8, 2)),
    ("pair", (8, 2), (9, 2)),
    ("pair", (9, 2), (10, 2)),
    ("pair", (10, 2), (11, 2)),
    ("pair", (11, 2), (11, 3)),
    ("pair", (11, 3), (11, 4)),
    ("pair", (11, 4), (11, 5)),
    ("pair", (11, 5), (11, 6)),
    ("single", (11, 6)),
    ("pair", (10, 6), (9, 6)),
    ("pair", (9, 6), (8, 6))
]

def preprocess_path(path):
    processed = []
    for item in path:
        processed.append(item[1])
    return processed

def run(path, addition_points=[]):
    processed_path = preprocess_path(path)
    start = (7,7)
    core = [(7,8), (7,7), (7,6), (6,8), (6,7), (6,6), (8,8), (8,7), (8,6)] + addition_points
    return generate_bot_moves(start, core, processed_path)

print(run(path_0))
print(run(path_1))
print(run(path_2, addition_points=preprocess_path(path_0)+preprocess_path(path_1)))