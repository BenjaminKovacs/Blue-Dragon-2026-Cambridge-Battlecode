from pathing.astar_conveyor import astar_conveyor_with_blocked
from pathing.astar import astar_with_blocked
from pathing.bugpathing import bug_move_with_blocked
from util import *

def find_path(player, start, target):
    if player.conveyor_build_mode:
        path = astar_conveyor_with_blocked(player, start, target)
    else:
        path = astar_with_blocked(player, start, target)
    return path

def make_move(player, target):
    if player.ct.get_position() == target:
        return True

    path = find_path(player, (player.ct.get_position().x, player.ct.get_position().y), (target.x, target.y))
    print("make_move path:")
    print(path)
    if path and len(path) > 1:
        next_step = path[1]
        try_move_with_build(player, next_step)
        return True
    else:
        next_move = bug_move_with_blocked(player, target)
        if next_move:
            try_move_with_build(player, next_move)
            return True
    return False