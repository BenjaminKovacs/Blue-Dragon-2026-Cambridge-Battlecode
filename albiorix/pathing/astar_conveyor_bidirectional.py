"""
Implements Bidirectional A* pathfinding for conveyors with time-slicing.
Supports normal conveyors (orthogonal) and bridges (range 3).
"""
import heapq
import math
from cambc import Position, EntityType, Environment

ASTAR_TIME_LIMIT = 500000  # Pause after this many time units
BRIDGE_COST = 20           # Additional cost for using a bridge
ENEMY_COST = 100           # Additional cost for pathing through enemy buildings

class BidirectionalAStarConveyorState:
    def __init__(self):
        self.reset()
        
    def reset(self):
        self.start = None
        self.goal = None
        self.forward_open = []
        self.backward_open = []
        self.forward_came_from = {}
        self.backward_came_from = {}
        self.forward_g = {}
        self.backward_g = {}
        self.finished = False
        self.path = None

_astar_states = {}

def get_line(start, end):
    """Bresenham's Line Algorithm to generate points between start and end."""
    x1, y1 = start
    x2, y2 = end
    points = []
    dx = abs(x2 - x1)
    dy = abs(y2 - y1)
    sx = 1 if x1 < x2 else -1
    sy = 1 if y1 < y2 else -1
    err = dx - dy
    
    while True:
        points.append((x1, y1))
        if x1 == x2 and y1 == y2:
            break
        e2 = 2 * err
        if e2 > -dy:
            err -= dy
            x1 += sx
        if e2 < dx:
            err += dx
            y1 += sy
    return points

def conveyor_load_to_cost(load):
    if load == 0: return 0
    elif load == 1: return 0.5
    elif load == 2: return 3.0
    elif load == 3: return 10.0
    else: return float('inf')

def astar_conveyor_bidirectional(ct, map_instance, start, goal, blocked=None, avoid_ore=False, avoid_conveyors=False, use_load_cost=True):
    """
    Bidirectional A* for conveyors/bridges with time limits.
    """
    global _astar_states
    
    unit_id = ct.get_id()
    if unit_id not in _astar_states:
        _astar_states[unit_id] = BidirectionalAStarConveyorState()
    
    state = _astar_states[unit_id]
    
    if blocked is None:
        blocked = set()

    # Convert inputs to tuples if necessary
    start_tuple = (start.x, start.y) if isinstance(start, Position) else start
    goal_tuple = (goal.x, goal.y) if isinstance(goal, Position) else goal
        
    cost_grid = map_instance.cost_grid
    rows, cols = len(cost_grid), len(cost_grid[0])
    
    def h(a, b):
        return max(abs(a[0] - b[0]), abs(a[1] - b[1]))

    # Reset logic
    should_full_reset = True
    should_reset_forward = True
    
    if state.goal is not None:
        dist_goal = h(state.goal, goal_tuple)
        if dist_goal <= 2:
            should_full_reset = False
            if state.start == start_tuple:
                should_reset_forward = False
            else:
                should_reset_forward = True 
        
    if should_full_reset:
        state.reset()
        state.start = start_tuple
        state.goal = goal_tuple
        
        heapq.heappush(state.forward_open, (h(start_tuple, goal_tuple), start_tuple))
        state.forward_came_from[start_tuple] = None
        state.forward_g[start_tuple] = 0
        
        heapq.heappush(state.backward_open, (h(goal_tuple, start_tuple), goal_tuple))
        state.backward_came_from[goal_tuple] = None
        state.backward_g[goal_tuple] = 0
        
    elif should_reset_forward:
        state.start = start_tuple
        state.forward_open = []
        state.forward_came_from = {}
        state.forward_g = {}
        state.finished = False
        state.path = None
        
        heapq.heappush(state.forward_open, (h(start_tuple, state.goal), start_tuple))
        state.forward_came_from[start_tuple] = None
        state.forward_g[start_tuple] = 0

    if state.finished and state.path:
        return [Position(x,y) for x, y in state.path]

    # Generate offsets
    ortho_offsets = [(0, 1), (0, -1), (1, 0), (-1, 0)]
    bridge_offsets = []
    for dx in range(-3, 4):
        for dy in range(-3, 4):
            d2 = dx*dx + dy*dy
            if d2 <= 9 and d2 > 1: # Within 3, but not 0 or 1 (orthogonal/self)
                bridge_offsets.append((dx, dy))

    start_time = ct.get_cpu_time_elapsed()

    def is_valid_node(nr, nc):
        if not (0 <= nr < rows and 0 <= nc < cols): return False
        if cost_grid[nr][nc] == float('inf'): return False
        if (nr, nc) in blocked: return False
        
        if avoid_ore and map_instance.terrain[nr][nc] in [Environment.ORE_TITANIUM, Environment.ORE_AXIONITE]:
            return False
        
        if avoid_conveyors:
            b = map_instance.buildings[nr][nc]
            if b and b['type'] != EntityType.ROAD and b['team'] == ct.get_team():
                return False
        return True

    def get_node_cost(nr, nc, is_bridge):
        cost = cost_grid[nr][nc]
        if is_bridge:
            cost = BRIDGE_COST # Base cost for bridge edge
        
        # Enemy penalty
        b = map_instance.buildings[nr][nc]
        if b and b['team'] != ct.get_team():
            cost += ENEMY_COST
            
        # Load penalty
        if use_load_cost:
            cost += conveyor_load_to_cost(map_instance.belt_load_counts[nr][nc])
        
        return cost

    while state.forward_open and state.backward_open:
        if ct.get_cpu_time_elapsed() - start_time > ASTAR_TIME_LIMIT:
            res = _reconstruct_partial_path(state, start_tuple, state.goal)
            return [Position(x,y) for x, y in res]

        # Expand Forward
        if state.forward_open:
            _, curr = heapq.heappop(state.forward_open)
            
            if curr in state.backward_came_from:
                state.finished = True
                state.path = _reconstruct_full_path(state, curr, start_tuple, state.goal)
                return [Position(x,y) for x, y in state.path]
            
            curr_g = state.forward_g[curr]
            r, c = curr
            
            # Process neighbors (Orthogonal + Bridges)
            all_moves = [(dr, dc, False) for dr, dc in ortho_offsets] + [(dr, dc, True) for dr, dc in bridge_offsets]
            
            for dr, dc, is_bridge in all_moves:
                nr, nc = r + dr, c + dc
                if not is_valid_node(nr, nc): continue
                
                move_cost = get_node_cost(nr, nc, is_bridge)
                new_g = curr_g + move_cost
                neighbor = (nr, nc)
                
                if new_g < state.forward_g.get(neighbor, float('inf')):
                    state.forward_g[neighbor] = new_g
                    priority = new_g + h(neighbor, state.goal)
                    heapq.heappush(state.forward_open, (priority, neighbor))
                    state.forward_came_from[neighbor] = curr
                    
                    if neighbor in state.backward_g:
                        state.finished = True
                        state.path = _reconstruct_full_path(state, neighbor, start_tuple, state.goal)
                        return [Position(x,y) for x, y in state.path]

        # Expand Backward
        if state.backward_open:
            _, curr = heapq.heappop(state.backward_open)
            
            if curr in state.forward_came_from:
                state.finished = True
                state.path = _reconstruct_full_path(state, curr, start_tuple, state.goal)
                return [Position(x,y) for x, y in state.path]
            
            curr_g = state.backward_g[curr]
            r, c = curr
            
            all_moves = [(dr, dc, False) for dr, dc in ortho_offsets] + [(dr, dc, True) for dr, dc in bridge_offsets]
            
            for dr, dc, is_bridge in all_moves:
                nr, nc = r + dr, c + dc
                if not is_valid_node(nr, nc): continue
                
                # For backward, cost is entering 'curr' from 'neighbor'
                # So we use get_node_cost(r, c) instead of (nr, nc)
                move_cost = get_node_cost(r, c, is_bridge)
                new_g = curr_g + move_cost
                neighbor = (nr, nc)
                
                if new_g < state.backward_g.get(neighbor, float('inf')):
                    state.backward_g[neighbor] = new_g
                    priority = new_g + h(neighbor, start_tuple)
                    heapq.heappush(state.backward_open, (priority, neighbor))
                    state.backward_came_from[neighbor] = curr
                    
                    if neighbor in state.forward_g:
                        state.finished = True
                        state.path = _reconstruct_full_path(state, neighbor, start_tuple, state.goal)
                        return [Position(x,y) for x, y in state.path]

    res = _reconstruct_partial_path(state, start_tuple, state.goal)
    return [Position(x,y) for x, y in res]

def _reconstruct_full_path(state, meeting_node, start, goal):
    path_f = []
    curr = meeting_node
    while curr is not None:
        path_f.append(curr)
        if curr == start: break
        curr = state.forward_came_from.get(curr)
    path_f.reverse()
    
    path_b = []
    curr = meeting_node
    curr = state.backward_came_from.get(curr)
    while curr is not None:
        path_b.append(curr)
        if curr == goal: break
        curr = state.backward_came_from.get(curr)
        
    # meeting_node is in both, remove one duplicate
    return path_f + path_b[1:]

def _reconstruct_partial_path(state, start, goal):
    best_f = start
    best_f_h = float('inf')
    for node in state.forward_g:
        dist = max(abs(node[0]-goal[0]), abs(node[1]-goal[1]))
        if dist < best_f_h:
            best_f_h = dist
            best_f = node
            
    best_b = goal
    best_b_h = float('inf')
    for node in state.backward_g:
        dist = max(abs(node[0]-start[0]), abs(node[1]-start[1]))
        if dist < best_b_h:
            best_b_h = dist
            best_b = node

    path_f = []
    curr = best_f
    while curr is not None:
        path_f.append(curr)
        if curr == start: break
        curr = state.forward_came_from.get(curr)
    path_f.reverse()
    
    path_b = []
    curr = best_b
    while curr is not None:
        path_b.append(curr)
        if curr == goal: break
        curr = state.backward_came_from.get(curr)
        
    gap_points = get_line(best_f, best_b)
    mid_segment = gap_points[1:-1] if len(gap_points) > 2 else []
    
    return path_f + mid_segment + path_b