from config import DIRECTIONS
from util import try_heal, move_anywhere

def is_damaged_enemy_tile(player, position):
    tile = player.map.get_building_info(position)
    return tile and tile['team'] != player.ct.get_team() and tile['hp'] < tile['max_hp']

def heal_adjacent_builders(player):
    adjacent_builders = player.ct.get_nearby_units(2)
    for id in adjacent_builders:
        if (player.ct.get_hp(id) <= player.ct.get_max_hp(id) - 4) and player.ct.get_team(id) == player.ct.get_team():
            position = player.ct.get_position(id)
            if is_damaged_enemy_tile(player, position):
                continue
            if try_heal(player, position, money_efficient=False):
                return True
    return False

def heal_self(player):
    if player.ct.get_hp() > player.ct.get_max_hp() - 4:
        return False

    my_pos = player.ct.get_position()
    if not is_damaged_enemy_tile(player, my_pos):
        try_heal(player, my_pos, money_efficient=False)
        move_anywhere(player)
        return True

    for d in DIRECTIONS:
        if player.ct.can_move(d) and not is_damaged_enemy_tile(player, my_pos.add(d)):
            player.ct.move(d)
            try_heal(player, player.ct.get_position(), money_efficient=False)
            return True
    
    return False

def heal_builders(player):
    tile = player.map.get_building_info(player.ct.get_position())
    if tile and tile['team'] != player.ct.get_team():
        if tile['hp'] <= 2:
            return False
        if tile['hp'] <= 6 and player.ct.get_hp() > 18:
            return False
    if heal_adjacent_builders(player):
        return True
    elif heal_self(player):
        return True
    return False
    