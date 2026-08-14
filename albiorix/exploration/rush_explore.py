from util import *
import pathing.pathing as pathing
import exploration.exploration as exploration
import exploration.exploration2 as exploration2

import random


def rush_explore(player):
    enemy_core = get_enemy_core_pos(player)

    if player.ct.get_position().distance_squared(enemy_core) <= 20:
        player.found_enemy_core = True

    if not player.found_enemy_core:
        pathing.make_move(player, enemy_core)
    elif player.ct.get_position().distance_squared(enemy_core) <= 20:
        exploration2.explore(player)
    elif player.ct.get_global_resources()[0] >= (GameConstants.HARVESTER_BASE_COST[0] + 50) * (1 + player.ct.get_scale_percent() / 100):
        # TODO
        exploration2.explore(player)
    else:
        scramble_direction=DIRECTIONS
        random.shuffle(scramble_direction)
        mypos=player.ct.get_position()
        moved=False
        for dir in scramble_direction:
            if(try_move(player.ct, mypos.add(dir))):
                moved=True
                break