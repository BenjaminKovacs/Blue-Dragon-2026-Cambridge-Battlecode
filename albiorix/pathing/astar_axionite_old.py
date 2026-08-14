import heapq
import math
from cambc import Position
from array import array
from util import distance_squared
import random

ASTAR_TIME_LIMIT = 1400
KEEP_TARGET_DISTANCE_SQUARED = 25
DIAGONAL_COST = 4

neighbors = [(1,0,0),(-1,0,0),(0,1,0),(0,-1,0),(1,1,DIAGONAL_COST),(1,-1,DIAGONAL_COST),(-1,1,DIAGONAL_COST),(-1,-1,DIAGONAL_COST)]
random.shuffle(neighbors)

global distances, no_path, visited, q, rows, cols
global finished, running_target, prev_complete_target, prev_visited, prev_no_path
distances = None
finished = True

def has_no_path(target):
    return target == prev_complete_target and prev_no_path

def initialize(player):
    global distances, rows, cols
    rows, cols = player.map.width, player.map.height
    distances = array('f', [float('inf')] * (rows * cols))

def reset(player):
    global distances, no_path, visited, q, finished
    if not distances:
        initialize(player)
    no_path = False
    visited = bytearray((player.map.width * player.map.height + 7)//8)
    q = []

def extract_path(player, start, target):
    cost_grid = player.map.axionite_cost_grid
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
        for dr, dc, additional_cost in neighbors:
            nr, nc = r + dr, c + dc
            index = nr * cols + nc
            dr_i, dc_i = dr, dc
            while (0 <= nr < rows and 0 <= nc < cols) and cost_grid[index] == float('inf') and dr**2 + dc**2 <= 4:
                dr += dr_i
                dc += dc_i
                nr, nc = r + dr, c + dc
                index = nr * cols + nc
                additional_cost = 2 * DIAGONAL_COST
            if 0 <= nr < rows and 0 <= nc < cols and (prev_visited[index // 8] & (1 << (index % 8))) and cost_grid[index] != float('inf'):
                dist = distances[index] + additional_cost
                if dist < min_dist:
                    min_dist = dist
                    current = (nr, nc)

    path.append(Position(target[0], target[1]))
    return path

def run(player, start):
    global distances, no_path, visited, q, finished
        
    cost_grid = player.map.axionite_cost_grid

    def h(a, b):
        dx = abs(a[0] - b[0])
        dy = abs(a[1] - b[1])
        return (dx + dy) + 0.00001 * (dx + dy)
        
    heapq.heappush(q, (0, start))
    r, c = start
    index = r * cols + c
    distances[index] = 0
    visited[index // 8] |= 1 << (index % 8)

    while q:
        _, current = heapq.heappop(q)
        r, c = current
        if player.map.valid_axionite_endpoint[r][c]:
            return True
        
        if player.ct.get_cpu_time_elapsed() > ASTAR_TIME_LIMIT:
            return False
        
        current_distance = distances[r * cols + c]
        for dr, dc, additional_cost in neighbors:
            nr, nc = r + dr, c + dc
            if not (0 <= nr < rows and 0 <= nc < cols):
                continue

            index = nr * cols + nc
            move_cost = cost_grid[index]
            dr_i, dc_i = dr, dc
            while move_cost == float('inf') and dr**2 + dc**2 <= 4:
                dr += dr_i
                dc += dc_i
                nr, nc = r + dr, c + dc
                index = nr * cols + nc
                if 0 <= nr < rows and 0 <= nc < cols:
                    move_cost = cost_grid[index]
                else:
                    move_cost = float('inf')
                    break
                additional_cost = 2 * DIAGONAL_COST
            
            if move_cost == float('inf'):
                continue

            if not visited[index // 8] & (1 << (index % 8)):
                distances[index] = float('inf')
            visited[index // 8] |= 1 << (index % 8)

            new_distance = current_distance + move_cost + additional_cost
            if new_distance < distances[index]:
                distances[index] = new_distance
                neighbor = (nr, nc)
                f = new_distance + h(neighbor, start)
                heapq.heappush(q, (f, neighbor))

    no_path = True
    return True

def astar_conveyor(player, start, target, avoid_conveyors=False):
    start_time = player.ct.get_cpu_time_elapsed()

    global finished, running_target, prev_complete_target, prev_visited, prev_no_path
    if finished or distance_squared(target, running_target) > KEEP_TARGET_DISTANCE_SQUARED:
        reset(player)
    else:
        target = running_target

    running_target = target
    finished = run(player, start, target)

    if finished:
        prev_visited = visited
        prev_complete_target = target
        prev_no_path = no_path

    end_time = player.ct.get_cpu_time_elapsed()

    print("astar_conveyor search run time:", end_time - start_time, "finished:", finished)
    target_difference = distance_squared(target, prev_complete_target)
    if target_difference <= KEEP_TARGET_DISTANCE_SQUARED and target_difference < distance_squared(start, target):
        if no_path:
            return None
        start_time = player.ct.get_cpu_time_elapsed()
        path = extract_path(player, start, target)
        end_time = player.ct.get_cpu_time_elapsed()
        print("extract path time:", end_time - start_time)
        return path
    return None

def astar_conveyor_with_blocked(player, start, goal, avoid_conveyors=False):
    start_time = player.ct.get_cpu_time_elapsed()
    old_distances = []
    nearby_positions = player.ct.get_nearby_tiles(2)
    print("astar_conveyor_with_blocked called with start:",start,"target:",goal)
    for pos in nearby_positions:
        if player.ct.get_tile_builder_bot_id(pos) is not None and pos != start:
            x, y = pos.x, pos.y
            index = x * player.map.height + y
            old_distances.append((index, player.map.conveyor_cost_grid[index]))
            player.map.conveyor_cost_grid[index] = float('inf')
    result = astar_conveyor(player, start, goal)
    for index, distance in old_distances:
        player.map.conveyor_cost_grid[index] = distance
    print("astar_conveyor_with_blocked (new) run time:", player.ct.get_cpu_time_elapsed() - start_time)
    print("result:",result)
    return result