import heapq
import math
from cambc import *

def conveyor_load_to_cost(load):
    if load == 0:
        return 0
    elif load == 1:
        return 0.5
    elif load == 2:
        return 3.0
    elif load == 3:
        return 10.0
    else:
        return float('inf')

def astar_conveyor_run(map_instance, start, goal, blocked=None, diagonal_cost=4, use_load_cost=True, avoid_ore=False, avoid_conveyors=False, ct=None):
    if blocked is None:
        blocked = set()
    cost_grid = map_instance.cost_grid
    conveyor_loads = map_instance.belt_load_counts
    terrain = map_instance.terrain
    rows, cols = map_instance.width, map_instance.height

    # Octile heuristic (best for 8-direction grids)
    def h(a, b):
        dx = abs(a[0] - b[0])
        dy = abs(a[1] - b[1])
        return (dx + dy) + (diagonal_cost - 2) * min(dx, dy)

    neighbors = [
        (1,0,1),(-1,0,1),(0,1,1),(0,-1,1),     # straight
        (1,1,diagonal_cost),(1,-1,diagonal_cost),
        (-1,1,diagonal_cost),(-1,-1,diagonal_cost)  # diagonals
    ]

    open_heap = []
    heapq.heappush(open_heap, (0, start))

    came_from = {}
    g_score = {start: 0}

    while open_heap:
        _, current = heapq.heappop(open_heap)

        if current == goal:
            path = []
            while current in came_from:
                path.append(current)
                current = came_from[current]
            path.append(start)
            return path[::-1]

        r, c = current

        for dr, dc, dist_cost in neighbors:
            nr, nc = r + dr, c + dc

            if not (0 <= nr < rows and 0 <= nc < cols):
                continue
            if cost_grid[nr*cols + nc] == float('inf'):
                continue
            if (nr, nc) in blocked:
                continue
            if avoid_ore and terrain[nr][nc] in [Environment.ORE_TITANIUM, Environment.ORE_AXIONITE]:
                continue
            if avoid_conveyors and map_instance.buildings[nr][nc] is not None and map_instance.buildings[nr][nc]['type'] != EntityType.ROAD and map_instance.buildings[nr][nc]['team'] == ct.get_team():
                continue

            neighbor = (nr, nc)
            move_cost = cost_grid[nr*cols + nc] * dist_cost
            if use_load_cost:
                move_cost += conveyor_load_to_cost(conveyor_loads[nr][nc])
            
            tentative_g = g_score[current] + move_cost

            if tentative_g < g_score.get(neighbor, float("inf")):
                came_from[neighbor] = current
                g_score[neighbor] = tentative_g
                f = tentative_g + h(neighbor, goal)
                heapq.heappush(open_heap, (f, neighbor))

    return None

def astar_conveyor(player, start, goal, blocked=None, diagonal_cost=4, use_load_cost=True, avoid_ore=False, avoid_conveyors=False):
    start_time = player.ct.get_cpu_time_elapsed()
    map_instance = player.map
    path = astar_conveyor_run(map_instance, start, goal, blocked, diagonal_cost, use_load_cost, avoid_ore, avoid_conveyors, player.ct)
    print("astar_conveyor run time:", player.ct.get_cpu_time_elapsed() - start_time)
    return [Position(x, y) for x, y in path] if path else None

def astar_conveyor_with_blocked(player, start, goal):
    ct = player.ct
    map_instance = player.map
    blocked = set()
    current_pos = ct.get_position()
    vision_sq = ct.get_vision_radius_sq()
    nearby_positions = ct.get_nearby_tiles(vision_sq)
    for pos in nearby_positions:
        dist_sq = (pos.x - current_pos.x)**2 + (pos.y - current_pos.y)**2
        if dist_sq <= 2 and dist_sq > 0 and ct.get_tile_builder_bot_id(pos) is not None:
            blocked.add((pos.x, pos.y))
    result = astar_conveyor_run(map_instance, start, goal, blocked, use_load_cost=False)
    return [Position(x,y) for x, y in result] if result else None
