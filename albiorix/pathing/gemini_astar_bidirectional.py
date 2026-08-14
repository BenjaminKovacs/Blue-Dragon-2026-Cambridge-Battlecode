"""
Implements Bidirectional A* pathfinding with time-slicing.
Paths from both sides and pauses if the elapsed time exceeds a limit.
"""
import heapq
import math
from cambc import Position

DIAGONAL_COST = 1
ASTAR_TIME_LIMIT = 500000  # Pause after this many time units (e.g., nanoseconds)

class BidirectionalAStarState:
    def __init__(self):
        self.backward_dist = None
        self.backward_dist_previous = None
        self.goal_previous = None
        self.best_cost = float('inf')
        self.best_node = None
        self.best_map_is_previous = False
        self.reset()
        
    def reset(self):
        self.start = None
        self.goal = None
        self.forward_open = []
        self.backward_open = []
        self.forward_came_from = {}
        self.forward_g = {}
        self.finished = False
        self.path = None
        self.best_cost = float('inf')
        self.best_node = None
        self.best_map_is_previous = False

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

def astar_bidirectional(ct, cost_grid, start, goal, blocked=None):
    """
    Bidirectional A* that pauses if CPU time exceeds ASTAR_TIME_LIMIT.
    The backward search from the previous goal is saved for partial path reconstruction.
    """
    global _astar_states
    
    unit_id = ct.get_id()
    if unit_id not in _astar_states:
        _astar_states[unit_id] = BidirectionalAStarState()
    
    state = _astar_states[unit_id]
    
    if blocked is None:
        blocked = set()
        
    rows, cols = len(cost_grid), len(cost_grid[0])
    
    def h(a, b):
        return max(abs(a[0] - b[0]), abs(a[1] - b[1]))

    # --- State Management ---
    # Initialize distance arrays on first run
    if state.backward_dist is None:
        state.backward_dist = [[float('inf')] * cols for _ in range(rows)]
        state.backward_dist_previous = [[float('inf')] * cols for _ in range(rows)]

    old_path = None
    if state.finished:
        old_path = state.path
        state.reset()

    # If goal has changed, swap current and previous backward searches
    if state.goal is None or h(state.goal, goal) > 2:
        # The current backward search becomes the previous one.
        state.backward_dist, state.backward_dist_previous = state.backward_dist_previous, state.backward_dist
        state.goal_previous = state.goal
        state.goal = goal

        # Reset the new 'current' distance array for the new search.
        for r in range(rows):
            for c in range(cols):
                state.backward_dist[r][c] = float('inf')
        
        heapq.heappush(state.backward_open, (h(goal, start), goal))
        gx, gy = goal
        state.backward_dist[gx][gy] = 0
        state.backward_open = [(0, goal)]
    
    # Reset best tracking for this run
    state.best_cost = float('inf')
    state.best_node = None
    state.best_map_is_previous = False

    # Always reset the forward search
    state.start = start
    state.forward_open = []
    state.forward_came_from = {start: None}
    state.forward_g = {start: 0}
    heapq.heappush(state.forward_open, (h(start, state.goal), start))
    state.finished = False
    state.path = None

    neighbors = [
        (1,0,1),(-1,0,1),(0,1,1),(0,-1,1),
        (1,1,DIAGONAL_COST),(1,-1,DIAGONAL_COST),
        (-1,1,DIAGONAL_COST),(-1,-1,DIAGONAL_COST)
    ]

    start_time = ct.get_cpu_time_elapsed()
    visited_backward_this_turn = set()

    while state.forward_open and state.backward_open:
        # Time check
        if ct.get_cpu_time_elapsed() - start_time > ASTAR_TIME_LIMIT:
            if old_path:
                candidate = None
                try:
                    idx = old_path.index(start)
                    candidate = old_path[idx:]
                except ValueError:
                    candidate = [start] + old_path
                
                if len(candidate) > 1 and candidate[1] in blocked:
                    return _reconstruct_partial_path(state, start, goal)
                return candidate
            return _reconstruct_partial_path(state, start, goal)

        # Expand Forward
        if state.forward_open:
            _, curr = heapq.heappop(state.forward_open)
            
            # Intersection check
            if curr in visited_backward_this_turn:
                state.finished = True
                state.path = _reconstruct_full_path(state, curr, start, state.goal, rows, cols)
                return state.path
            
            # Check for best path via previous map
            if state.backward_dist_previous[r][c] != float('inf'):
                total = state.forward_g[curr] + state.backward_dist_previous[r][c]
                if total < state.best_cost:
                    state.best_cost = total
                    state.best_node = curr
                    state.best_map_is_previous = True
            
            # Check for best path via current map (in case we miss the exact intersection event)
            if state.backward_dist[r][c] != float('inf'):
                total = state.forward_g[curr] + state.backward_dist[r][c]
                if total < state.best_cost:
                    state.best_cost = total
                    state.best_node = curr
                    state.best_map_is_previous = False
            
            curr_g = state.forward_g[curr]
            for dr, dc, cost_mult in neighbors:
                nr, nc = curr[0] + dr, curr[1] + dc
                neighbor = (nr, nc)
                
                if not (0 <= nr < rows and 0 <= nc < cols): continue
                if cost_grid[nr][nc] == float('inf'): continue
                if neighbor in blocked: continue
                
                new_g = curr_g + cost_grid[nr][nc] * cost_mult
                if new_g < state.forward_g.get(neighbor, float('inf')):
                    state.forward_g[neighbor] = new_g
                    priority = new_g + h(neighbor, state.goal)
                    heapq.heappush(state.forward_open, (priority, neighbor))
                    state.forward_came_from[neighbor] = curr
                    
                    # Check update for best path
                    if state.backward_dist_previous[nr][nc] != float('inf'):
                        total = new_g + state.backward_dist_previous[nr][nc]
                        if total < state.best_cost:
                            state.best_cost = total
                            state.best_node = neighbor
                            state.best_map_is_previous = True
                    
                    if state.backward_dist[nr][nc] != float('inf'):
                        total = new_g + state.backward_dist[nr][nc]
                        if total < state.best_cost:
                            state.best_cost = total
                            state.best_node = neighbor
                            state.best_map_is_previous = False

                    if neighbor in visited_backward_this_turn:
                        state.finished = True
                        state.path = _reconstruct_full_path(state, neighbor, start, state.goal, rows, cols)
                        return state.path

        # Expand Backward
        if state.backward_open:
            _, curr = heapq.heappop(state.backward_open)
            visited_backward_this_turn.add(curr)
            r, c = curr
            
            if curr in state.forward_g:
                state.finished = True
                state.path = _reconstruct_full_path(state, curr, start, state.goal, rows, cols)
                return state.path
            
            curr_dist = state.backward_dist[r][c]
            for dr, dc, cost_mult in neighbors:
                nr, nc = curr[0] + dr, curr[1] + dc
                neighbor = (nr, nc)
                
                if not (0 <= nr < rows and 0 <= nc < cols): continue
                if cost_grid[nr][nc] == float('inf'): continue
                
                move_cost = cost_grid[nr][nc] * cost_mult
                new_dist = curr_dist + move_cost
                
                if new_dist < state.backward_dist[nr][nc]:
                    state.backward_dist[nr][nc] = new_dist
                    priority = new_dist # Dijkstra-like for reusable backward search
                    heapq.heappush(state.backward_open, (priority, neighbor))
                    
                    # Check if this node connects to forward path
                    if neighbor in state.forward_g:
                        total = new_dist + state.forward_g[neighbor]
                        if total < state.best_cost:
                            state.best_cost = total
                            state.best_node = neighbor
                            state.best_map_is_previous = False

                        state.finished = True
                        state.path = _reconstruct_full_path(state, neighbor, start, state.goal, rows, cols)
                        return state.path

    # If loops finish without meeting (unreachable), returns best guess
    return _reconstruct_partial_path(state, start, goal)

def _reconstruct_full_path(state, meeting_node, start, goal, rows, cols):
    # Forward part: Start -> Meeting
    path_f = []
    curr = meeting_node
    while curr is not None:
        path_f.append(curr)
        if curr == start: break
        curr = state.forward_came_from.get(curr)
    path_f.reverse()
    
    # Backward part: Meeting -> Goal
    path_b = []
    curr = meeting_node
    curr = _get_best_backward_neighbor(state.backward_dist, curr, rows, cols)
    while curr is not None:
        path_b.append(curr)
        if curr == goal: break
        curr = _get_best_backward_neighbor(state.backward_dist, curr, rows, cols)
        
    return path_f + path_b

def _get_best_backward_neighbor(dist_map, curr, rows, cols):
    """Find neighbor with lowest distance in the given distance map."""
    r, c = curr
    best_n = None
    best_dist = dist_map[r][c]
    
    neighbors = [
        (1,0),(-1,0),(0,1),(0,-1),
        (1,1),(1,-1),(-1,1),(-1,-1)
    ]
    
    for dr, dc in neighbors:
        nr, nc = r + dr, c + dc
        if 0 <= nr < rows and 0 <= nc < cols:
            d = dist_map[nr][nc]
            if d < best_dist:
                best_dist = d
                best_n = (nr, nc)
    
    return best_n

def _reconstruct_partial_path(state, start, goal, rows, cols):
    """
    Connects the best node reached by forward search to the best node reached by backward search.
    """
    # Find node in forward_g closest to goal
    best_f = start
    best_f_h = float('inf')
    for node in state.forward_g:
        dist = max(abs(node[0]-goal[0]), abs(node[1]-goal[1]))
        if dist < best_f_h:
            best_f_h = dist
            best_f = node
            
    # Find best connection point from current and previous backward searches
    best_b_current, h_current = None, float('inf')
    for r in range(rows):
        for c in range(cols):
            if state.backward_dist[r][c] != float('inf'):
                dist = h((r,c), start)
                if dist < h_current:
                    h_current = dist
                    best_b_current = (r, c)

    best_b_previous, h_previous = None, float('inf')
    for r in range(rows):
        for c in range(cols):
            if state.backward_dist_previous[r][c] != float('inf'):
                dist = h((r,c), start)
                if dist < h_previous:
                    h_previous = dist
                    best_b_previous = (r, c)

    # Choose the overall best backward node and which dist map/goal to use
    best_b = best_b_current or goal
    dist_map_to_use = state.backward_dist
    goal_to_use = state.goal
    if h_previous < h_current and best_b_previous:
        best_b = best_b_previous
        dist_map_to_use = state.backward_dist_previous
        goal_to_use = state.goal_previous

    # Reconstruct Forward -> BestF
    path_f = []
    curr = best_f
    while curr is not None:
        path_f.append(curr)
        if curr == start: break
        curr = state.forward_came_from.get(curr)
    path_f.reverse()
    
    # Reconstruct BestB -> Goal
    # Use current backward map since we picked best_b from backward_open
    path_b = []
    curr = best_b
    rows, cols = len(state.backward_dist), len(state.backward_dist[0])
    while curr is not None:
        path_b.append(curr)
        if curr == goal: break
        curr = _get_best_backward_neighbor(state.backward_dist, curr, rows, cols)
        
    # Fill gap
    gap_points = get_line(best_f, best_b)
    # path_f includes best_f. gap_points includes best_f and best_b.
    # We slice to avoid duplicates
    mid_segment = gap_points[1:-1] if len(gap_points) > 2 else []
    
    return path_f + mid_segment + path_b

def astar_bidirectional_with_blocked(ct, map_instance, start, goal):
    blocked = set()
    current_pos = ct.get_position()
    nearby_positions = ct.get_nearby_tiles(2)
    for pos in nearby_positions:
        dist_sq = (pos.x - current_pos.x)**2 + (pos.y - current_pos.y)**2
        if dist_sq > 0 and ct.get_tile_builder_bot_id(pos) is not None:
            blocked.add((pos.x, pos.y))
            
    # start/goal as tuples for logic
    start_tuple = (start.x, start.y) if isinstance(start, Position) else start
    goal_tuple = (goal.x, goal.y) if isinstance(goal, Position) else goal
    
    result = astar_bidirectional(ct, map_instance.cost_grid, start_tuple, goal_tuple, blocked)
    
    return [Position(x,y) for x, y in result] if result else None