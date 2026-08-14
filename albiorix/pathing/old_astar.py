import heapq
import math
from cambc import Position

DIAGONAL_COST = 1
ASTAR_TIME_LIMIT = 500000  # Pause after this many time units (e.g., nanoseconds)

def astar(cost_grid, start, goal, blocked=None):
    if blocked is None:
        blocked = set()
    rows, cols = len(cost_grid), len(cost_grid[0])

    # Octile heuristic (best for 8-direction grids)
    # def h(a, b):
    #     dx = abs(a[0] - b[0])
    #     dy = abs(a[1] - b[1])
    #     return (dx + dy) + (DIAGONAL_COST - 2) * min(dx, dy)

    def h(a, b):
        dx = abs(a[0] - b[0])
        dy = abs(a[1] - b[1])
        return max(dx, dy)

    neighbors = [
        (1,0,1),(-1,0,1),(0,1,1),(0,-1,1),     # straight
        (1,1,DIAGONAL_COST),(1,-1,DIAGONAL_COST),
        (-1,1,DIAGONAL_COST),(-1,-1,DIAGONAL_COST)  # diagonals
    ]

    open_heap = []
    heapq.heappush(open_heap, (0, start))

    came_from = {}
    g_score = {start: 0}

    while open_heap:
        _, current = heapq.heappop(open_heap)

        # if current == goal:
        #     path = []
        #     while current in came_from:
        #         path.append(current)
        #         current = came_from[current]
        #     path.append(start)
        #     return path[::-1]

        r, c = current

        for dr, dc, dist_cost in neighbors:
            nr, nc = r + dr, c + dc

            if (nr, nc) == goal:
                path = [goal]
                while current in came_from:
                    path.append(current)
                    current = came_from[current]
                path.append(start)
                return path[::-1]

            if not (0 <= nr < rows and 0 <= nc < cols):
                continue
            if cost_grid[nr][nc] == float('inf'):
                continue
            if (nr, nc) in blocked:
                continue

            neighbor = (nr, nc)
            move_cost = cost_grid[nr][nc] * dist_cost
            tentative_g = g_score[current] + move_cost

            if tentative_g < g_score.get(neighbor, float("inf")):
                came_from[neighbor] = current
                g_score[neighbor] = tentative_g
                f = tentative_g + h(neighbor, goal)
                heapq.heappush(open_heap, (f, neighbor))

    return None

def astar_with_blocked(ct, map_instance, start, goal):
    blocked = set()
    current_pos = ct.get_position()
    nearby_positions = ct.get_nearby_tiles(2)
    for pos in nearby_positions:
        dist_sq = (pos.x - current_pos.x)**2 + (pos.y - current_pos.y)**2
        if dist_sq > 0 and ct.get_tile_builder_bot_id(pos) is not None:
            blocked.add((pos.x, pos.y))
    result = astar(map_instance.cost_grid, start, goal, blocked)
    return [Position(x,y) for x, y in result] if result else None

# --- Bidirectional Time-Limited A* ---

class BidirectionalAStarState:
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

def astar_bidirectional(ct, cost_grid, start, goal, blocked=None):
    """
    Bidirectional A* that pauses if CPU time exceeds ASTAR_TIME_LIMIT.
    Resumes if called again with the same (or very nearby) goal.
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

    # Reset logic:
    # 1. If goal changed significantly (>2 tiles), full reset.
    # 2. If goal is same/close but start changed, reset forward search only (keep backward tree).
    should_full_reset = True
    should_reset_forward = True
    
    if state.goal is not None:
        dist_goal = h(state.goal, goal)
        if dist_goal <= 2:
            should_full_reset = False
            if state.start == start:
                should_reset_forward = False
            else:
                should_reset_forward = True # Start changed, must reset forward
        
    if should_full_reset:
        state.reset()
        state.start = start
        state.goal = goal
        
        # Init Forward
        heapq.heappush(state.forward_open, (h(start, goal), start))
        state.forward_came_from[start] = None
        state.forward_g[start] = 0
        
        # Init Backward
        heapq.heappush(state.backward_open, (h(goal, start), goal))
        state.backward_came_from[goal] = None
        state.backward_g[goal] = 0
        
    elif should_reset_forward:
        # Keep backward search state, reset forward
        state.start = start
        state.forward_open = []
        state.forward_came_from = {}
        state.forward_g = {}
        state.finished = False
        state.path = None
        
        heapq.heappush(state.forward_open, (h(start, state.goal), start))
        state.forward_came_from[start] = None
        state.forward_g[start] = 0

    # If we already have a finished path for this setup, return it
    if state.finished and state.path:
        return state.path

    neighbors = [
        (1,0,1),(-1,0,1),(0,1,1),(0,-1,1),
        (1,1,DIAGONAL_COST),(1,-1,DIAGONAL_COST),
        (-1,1,DIAGONAL_COST),(-1,-1,DIAGONAL_COST)
    ]

    start_time = ct.get_cpu_time_elapsed()

    while state.forward_open and state.backward_open:
        # Time check
        if ct.get_cpu_time_elapsed() - start_time > ASTAR_TIME_LIMIT:
            return _reconstruct_partial_path(state, start, state.goal)

        # Expand Forward
        if state.forward_open:
            _, curr = heapq.heappop(state.forward_open)
            
            # Intersection check
            if curr in state.backward_came_from:
                state.finished = True
                state.path = _reconstruct_full_path(state, curr, start, state.goal)
                return state.path
            
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
                    
                    # Optimization: check intersection on generation
                    if neighbor in state.backward_g:
                        state.finished = True
                        state.path = _reconstruct_full_path(state, neighbor, start, state.goal)
                        return state.path

        # Expand Backward
        if state.backward_open:
            _, curr = heapq.heappop(state.backward_open)
            
            if curr in state.forward_came_from:
                state.finished = True
                state.path = _reconstruct_full_path(state, curr, start, state.goal)
                return state.path
            
            curr_g = state.backward_g[curr]
            for dr, dc, cost_mult in neighbors:
                nr, nc = curr[0] + dr, curr[1] + dc
                neighbor = (nr, nc)
                
                if not (0 <= nr < rows and 0 <= nc < cols): continue
                if cost_grid[nr][nc] == float('inf'): continue
                if neighbor in blocked: continue
                
                new_g = curr_g + cost_grid[nr][nc] * cost_mult
                if new_g < state.backward_g.get(neighbor, float('inf')):
                    state.backward_g[neighbor] = new_g
                    priority = new_g + h(neighbor, start)
                    heapq.heappush(state.backward_open, (priority, neighbor))
                    state.backward_came_from[neighbor] = curr
                    
                    if neighbor in state.forward_g:
                        state.finished = True
                        state.path = _reconstruct_full_path(state, neighbor, start, state.goal)
                        return state.path

    # If loops finish without meeting (unreachable), returns best guess
    return _reconstruct_partial_path(state, start, state.goal)

def _reconstruct_full_path(state, meeting_node, start, goal):
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
    # meeting_node is already in path_f, skip it in path_b
    curr = state.backward_came_from.get(curr)
    while curr is not None:
        path_b.append(curr)
        if curr == goal: break
        curr = state.backward_came_from.get(curr)
        
    return path_f + path_b

def _reconstruct_partial_path(state, start, goal):
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
            
    # Find node in backward_g closest to start (or closest to best_f)
    best_b = goal
    best_b_h = float('inf')
    for node in state.backward_g:
        # Minimal heuristic to the best forward node is ideal, but expensive to scan. 
        # Using heuristic to start is a decent proxy for "progress towards start"
        dist = max(abs(node[0]-start[0]), abs(node[1]-start[1]))
        if dist < best_b_h:
            best_b_h = dist
            best_b = node

    # Reconstruct Forward -> BestF
    path_f = []
    curr = best_f
    while curr is not None:
        path_f.append(curr)
        if curr == start: break
        curr = state.forward_came_from.get(curr)
    path_f.reverse()
    
    # Reconstruct BestB -> Goal
    path_b = []
    curr = best_b
    while curr is not None:
        path_b.append(curr)
        if curr == goal: break
        curr = state.backward_came_from.get(curr)
        
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