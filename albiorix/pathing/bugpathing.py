"""
Implementation of the Bug2 navigation algorithm.
A lightweight pathfinding fallback that follows the m-line and circumnavigates obstacles.
"""
import math
from cambc import Position

MODE_GOAL_SEEK = 0
MODE_WALL_FOLLOW = 1

class BugState:
    def __init__(self, start, goal):
        self.mode = MODE_GOAL_SEEK
        self.start = start
        self.goal = goal
        self.hit_point = None
        self.last_pos = None
        # Direction for wall following: -1 for counter-clockwise, 1 for clockwise
        self.direction = 1 

_bug_states = {}

def get_dist(p1, p2):
    return max(abs(p1[0] - p2[0]), abs(p1[1] - p2[1]))

def is_on_m_line(curr, start, goal):
    """Checks if the current point lies on the line between start and goal."""
    # Cross product approach to check collinearity in discrete grid
    dx_total = goal[0] - start[0]
    dy_total = goal[1] - start[1]
    dx_curr = curr[0] - start[0]
    dy_curr = curr[1] - start[1]
    
    cross_product = abs(dy_curr * dx_total - dx_curr * dy_total)
    
    # Using a small threshold for discrete grid math
    if cross_product <= max(abs(dx_total), abs(dy_total)) // 2:
        # Ensure it's not behind the start or past the goal
        dot_product = dx_curr * dx_total + dy_curr * dy_total
        return dot_product > 0 and get_dist(curr, goal) < get_dist(start, goal)
    return False

def get_neighbors_sorted(curr, last_move_dir):
    """Returns neighbors relative to the last move direction for wall following."""
    offsets = [
        (0, 1), (1, 1), (1, 0), (1, -1),
        (0, -1), (-1, -1), (-1, 0), (-1, 1)
    ]
    # Find index of last move
    start_idx = 0
    if last_move_dir in offsets:
        start_idx = offsets.index(last_move_dir)
        
    # Reorder offsets starting from last move
    return offsets[start_idx:] + offsets[:start_idx]

def bug_move(player, target, blocked=None):
    global _bug_states

    ct = player.ct
    map_instance = player.map
    
    unit_id = ct.get_id()
    curr_pos = ct.get_position()
    curr = (curr_pos.x, curr_pos.y)
    target_tuple = (target.x, target.y) if isinstance(target, Position) else target

    if unit_id not in _bug_states or _bug_states[unit_id].goal != target_tuple:
        _bug_states[unit_id] = BugState(curr, target_tuple)
        
    state = _bug_states[unit_id]
    if blocked is None:
        blocked = set()

    cost_grid = map_instance.cost_grid
    rows, cols = map_instance.width, map_instance.height

    if curr == target_tuple:
        return None

    # Detect stuck state or teleportation
    if state.last_pos == curr and state.mode == MODE_GOAL_SEEK:
        state.mode = MODE_WALL_FOLLOW
        state.hit_point = curr

    state.last_pos = curr

    # mode logic
    if state.mode == MODE_GOAL_SEEK:
        # Try to move directly towards goal
        dx = target_tuple[0] - curr[0]
        dy = target_tuple[1] - curr[1]
        
        step_x = 0 if dx == 0 else (1 if dx > 0 else -1)
        step_y = 0 if dy == 0 else (1 if dy > 0 else -1)
        
        next_pos = (curr[0] + step_x, curr[1] + step_y)
        
        # Check if blocked
        if (0 <= next_pos[0] < rows and 0 <= next_pos[1] < cols and 
            cost_grid[next_pos[0]*cols + next_pos[1]] != float('inf') and
            next_pos not in blocked):
            return Position(next_pos[0], next_pos[1])
        else:
            state.mode = MODE_WALL_FOLLOW
            state.hit_point = curr
            # Continue into wall follow logic immediately

    if state.mode == MODE_WALL_FOLLOW:
        # 1. Check if we can leave the wall
        if is_on_m_line(curr, state.start, target_tuple):
            if get_dist(curr, target_tuple) < get_dist(state.hit_point, target_tuple):
                state.mode = MODE_GOAL_SEEK
                return bug_move(player, target, blocked) # Recurse once in new mode

        # 2. Perimeter following (Right-hand rule / Clockwise)
        # Directions in order
        dirs = [
            (0, 1), (1, 1), (1, 0), (1, -1),
            (0, -1), (-1, -1), (-1, 0), (-1, 1)
        ]
        
        # We want to find the first "free" tile after a "blocked" tile
        # to stay hugged against the wall.
        
        # Look for the last point we were at to determine rotation
        # Simple implementation: find the first available move rotating clockwise
        # relative to the direction of the goal.
        goal_dx = target_tuple[0] - curr[0]
        goal_dy = target_tuple[1] - curr[1]
        ideal_angle = math.atan2(goal_dy, goal_dx)
        
        # Sort directions by angle difference
        sorted_dirs = sorted(dirs, key=lambda d: abs(math.atan2(d[1], d[0]) - ideal_angle))
        
        # In a real bug algorithm, you hug the wall. Here we simplify to 
        # finding the neighbor that is not blocked and doesn't return to the m-line 
        # at a further distance.
        for dr, dc in sorted_dirs:
            nr, nc = curr[0] + dr, curr[1] + dc
            if not (0 <= nr < rows and 0 <= nc < cols): continue
            
            if cost_grid[nr*cols + nc] != float('inf') and (nr, nc) not in blocked:
                # Check if this move is actually "hugging" the obstacle
                # (Simplified: just take the first valid move in rotation)
                return Position(nr, nc)

    return None

def bug_move_with_blocked(player, target):
    """Wrapper that handles dynamic bot blocking."""
    blocked = set()
    current_pos = player.ct.get_position()
    nearby_positions = player.ct.get_nearby_tiles(2)
    for pos in nearby_positions:
        dist_sq = (pos.x - current_pos.x)**2 + (pos.y - current_pos.y)**2
        if dist_sq > 0 and player.ct.get_tile_builder_bot_id(pos) is not None:
            blocked.add((pos.x, pos.y))
            
    return bug_move(player, target, blocked)