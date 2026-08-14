from config import *
from util import *

def should_target_enemy_core(player, position):
    possible_core_pos = player.map.symmetry_calculator.get_all_enemy_core_pos(player)
    if len(possible_core_pos) != 1:
        return None
    enemy_core_pos = next(iter(possible_core_pos))
    enemy_core_distance = distance_squared(position, enemy_core_pos)
    if enemy_core_distance <= ENEMY_CORE_CONVEYOR_TARGET_DISTANCE_SQUARED and enemy_core_distance < distance_squared(position, player.core_pos):
        return enemy_core_pos
    return None