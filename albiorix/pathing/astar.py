import heapq
import math
from cambc import Position
from array import array
from util import distance_squared
import random

ASTAR_TIME_LIMIT = 1700
KEEP_TARGET_DISTANCE_SQUARED = 25
neighbors = [(1,0),(-1,0),(0,1),(0,-1),(1,1),(1,-1),(-1,1),(-1,-1)]
random.shuffle(neighbors)

global distances, no_path, visited, q, rows, cols
global finished, running_target, prev_complete_target, prev_visited, prev_no_path, reached_from
global unreachable_locations
distances = None
finished = True
prev_complete_target = None
unreachable_locations = dict()

def initialize(player):
    global distances, rows, cols, reached_from
    rows, cols = player.map.width, player.map.height
    distances = array('f', [float('inf')] * (rows * cols))
    reached_from = dict()

def reset(player, target):
    global distances, no_path, visited, q, finished, reached_from
    if not distances:
        initialize(player)
    no_path = False
    visited = bytearray((player.map.width * player.map.height + 7)//8)
    q = []
    if target != prev_complete_target:
        reached_from = dict()

def extract_path(player, start, target):
    cost_grid = player.map.cost_grid
    path = []
    current = start
    while current != target:
        if Position(current[0], current[1]) in path:
            print("Error: current position in path in extract_path")
            print(current)
            print(path)
            break
        path.append(Position(current[0], current[1]))
        r, c = current
        min_dist = float('inf')
        for dr, dc in neighbors:
            nr, nc = r + dr, c + dc
            index = nr * cols + nc
            if 0 <= nr < rows and 0 <= nc < cols and (prev_visited[index // 8] & (1 << (index % 8))) and cost_grid[index] != float('inf'):
                dist = distances[index]
                if dist < min_dist:
                    min_dist = dist
                    current = (nr, nc)
        
        if min_dist == float('inf'):
            return None

    path.append(Position(target[0], target[1]))
    return path

def fast_extract_path(player, start, target):
    global reached_from
    cost_grid = player.map.cost_grid
    path = []
    path_nodes = set()
    current = start
    steps = 0
    while current != target:
        if current in path_nodes:
            path.append(Position(target[0], target[1]))
            print("Error: current position in path in fast_extract_path")
            print(current)
            print(path)
            return path
        r, c = current
        path.append(Position(r, c))
        path_nodes.add(current)
        if current not in reached_from:
            if steps < 1:
                return False
            return None
        current = reached_from[current]
        r, c = current
        index = r * cols + c
        if (steps < 2) and cost_grid[index] == float('inf'):
            return False
        steps += 1
    path.append(Position(target[0], target[1]))
    return path

def run(player, start, goal):
    global distances, no_path, visited, q, finished, reached_from
        
    cost_grid = player.map.cost_grid
    
    def h(a, b):
        dx = abs(a[0] - b[0])
        dy = abs(a[1] - b[1])
        return max(dx, dy) + 0.00001 * (dx + dy)
        
    heapq.heappush(q, (0, goal))
    r, c = goal
    index = r * cols + c
    distances[index] = 0
    visited[index // 8] |= 1 << (index % 8)

    while q:
        _, current = heapq.heappop(q)
        r, c = current
        if (r, c) == start:
            return True
        
        if player.ct.get_cpu_time_elapsed() > ASTAR_TIME_LIMIT:
            return False
        
        current_distance = distances[r * cols + c]
        for dr, dc in neighbors:
            nr, nc = r + dr, c + dc
            if not (0 <= nr < rows and 0 <= nc < cols):
                continue

            index = nr * cols + nc
            if not visited[index // 8] & (1 << (index % 8)):
                visited[index // 8] |= 1 << (index % 8)
                move_cost = cost_grid[index]
                if move_cost == float('inf'):
                    continue
                new_distance = current_distance + move_cost
                distances[index] = new_distance
                neighbor = (nr, nc)
                reached_from[neighbor] = current
                f = new_distance + h(neighbor, start)
                heapq.heappush(q, (f, neighbor))

    no_path = True
    return True

def astar(player, start, target):
    start_time = player.ct.get_cpu_time_elapsed()

    global finished, running_target, prev_complete_target, prev_visited, prev_no_path
    global unreachable_locations
    if finished or distance_squared(target, running_target) > KEEP_TARGET_DISTANCE_SQUARED:
        reset(player, target)
    else:
        target = running_target

    running_target = target
    finished = run(player, start, target)

    if finished:
        prev_visited = visited
        prev_complete_target = target
        prev_no_path = no_path
        if no_path:
            unreachable_locations[target] = player.ct.get_current_round()

    end_time = player.ct.get_cpu_time_elapsed()

    print("astar search run time:", end_time - start_time, "finished:", finished)
    if prev_complete_target:
        target_difference = distance_squared(target, prev_complete_target)
        if target_difference <= KEEP_TARGET_DISTANCE_SQUARED and target_difference < distance_squared(start, target):
            if no_path:
                return None
            start_time = player.ct.get_cpu_time_elapsed()
            path = fast_extract_path(player, start, target)
            if path is False:
                print("terrain changed, falling back to slow extract path")
                path = extract_path(player, start, target)
            end_time = player.ct.get_cpu_time_elapsed()
            print("extract path time:", end_time - start_time)
            return path
    return None

def astar_with_blocked(player, start, goal):
    start_time = player.ct.get_cpu_time_elapsed()
    old_distances = []
    nearby_positions = player.ct.get_nearby_tiles(2)
    print("astar_with_blocked called with start:",start,"target:",goal)
    for pos in nearby_positions:
        if player.ct.get_tile_builder_bot_id(pos) is not None and pos != start:
            x, y = pos.x, pos.y
            index = x * player.map.height + y
            old_distances.append((index, player.map.cost_grid[index]))
            player.map.cost_grid[index] = float('inf')
    result = astar(player, start, goal)
    for index, distance in old_distances:
        player.map.cost_grid[index] = distance
    print("astar_with_blocked (new) run time:", player.ct.get_cpu_time_elapsed() - start_time)
    print("result:",result)
    return result