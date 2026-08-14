from util import *
from pathing.pathing import make_move
import random
from cambc import *

def get_conveyor_path_up(player, position):
    path = []
    conveyors = [position]
    while len(conveyors) > 0:
        random.shuffle(conveyors)
        position = conveyors[0]
        conveyors = get_conveyors_leading_here(player, position)
        if position in path:
            break
        path.append(position)
    return path

SCOUT_DISTANCE = 4

def get_conveyors_to_core(player):
    return sum([get_conveyors_leading_here(player, player.core_pos.add(d)) for d in Direction], [])

def run_patrol(player):
    my_position = player.ct.get_position()
    if player.patrol_path_top:
        if distance_squared(my_position, player.patrol_path_top) > SCOUT_DISTANCE:
            make_move(player, player.patrol_path_top)
            return True
        else:
            conveyors = get_conveyors_leading_here(player, player.patrol_path_top)
            if len(conveyors) == 0:
                player.patrol_path_top = None
                player.patrol_path = []
                make_move(player, player.core_pos)
                return True
            else:
                while len(conveyors) > 0 and distance_squared(my_position, player.patrol_path_top) <= SCOUT_DISTANCE:
                    random.shuffle(conveyors)
                    player.patrol_path_top = conveyors[0]
                    conveyors = get_conveyors_leading_here(player, player.patrol_path_top)
                    if player.patrol_path_top in player.patrol_path:
                        # path has a loop, go home and follow a different one
                        player.patrol_path_top = None
                        player.patrol_path = []
                        make_move(player, player.core_pos)
                        return True
                    player.patrol_path.append(player.patrol_path_top)
                make_move(player, player.patrol_path_top)
                return True
    else:
        if (my_position == player.core_pos) or (distance_squared(my_position, player.core_pos) <= 8 and not player.ct.can_move(my_position.direction_to(player.core_pos))):
            conveyors = get_conveyors_to_core(player)
            if len(conveyors) > 0:
                random.shuffle(conveyors)
                player.patrol_path_top = conveyors[0]
                player.patrol_path = []
                make_move(player, player.patrol_path_top)
                return True
            else:
                return False
        else:
            make_move(player, player.core_pos)
            return True