from util import *
from pathing.pathing import make_move

def best_healable_building(player):
    best = None
    best_value = 0
    for b in player.map.healable_buildings:
        turn_difference = b['hp']//2 - move_distance(player.ct.get_position(), b['position'])
        damage = b['max_hp'] - b['hp']
        if damage < 5 and distance_squared(player.ct.get_position(), b['position']) > 2:
            closer_friend = False
            for d in DIRECTIONS:
                test_position = b['position'].add(d)
                if player.map.on_the_map(test_position) and player.ct.is_in_vision(test_position):
                    builder = player.ct.get_tile_builder_bot_id(test_position)
                    if builder is not None and player.ct.get_team(builder) == player.ct.get_team():
                        closer_friend = True
                        player.friendly_builder_positions[test_position] = player.ct.get_current_round()
                    elif test_position in player.friendly_builder_positions:
                        del player.friendly_builder_positions[test_position]
                elif test_position in player.friendly_builder_positions and player.ct.get_current_round() - player.friendly_builder_positions[test_position] < 4:
                    closer_friend = True
            
            if closer_friend:
                if not player.ct.is_in_vision(b['position']):
                    b['hp'] = b['max_hp'] # assume friend healed it
                continue

        if damage < 4: # and turn_difference >= 2:
            value = 2
        elif turn_difference >= 0:
            value = damage * 1000 + turn_difference
        else:
            value = damage * 10 + turn_difference

        if value > best_value:
            best = b
            best_value = value
    player.map.healable_buildings = [b for b in player.map.healable_buildings if b['hp'] < b['max_hp']]
    return best

def best_adjacent_healable_building(player):
    best = None
    best_value = 0
    for b in player.map.healable_buildings:
        damage = b['max_hp'] - b['hp']
        if distance_squared(player.ct.get_position(), b['position']) > 2:
            continue
        if damage < 4: # and turn_difference >= 2:
            value = 2
        else:
            value = 1000 - b['hp']
        if value > best_value:
            best = b
            best_value = value
    return best


def run_heal(player):
    if player.heal_target and player.ct.is_in_vision(player.heal_target['position']):
        b = player.map.get_building_info(player.heal_target['position'])
        if b and b['hp'] < b['max_hp'] - 2 and b['team'] == player.ct.get_team():
            player.heal_target = b
        else:
            player.heal_target = None
    # TODO: prioritize lower health if multiple equidistant targets or target has < 4 damage!!!!!!!!!!!!
    #heal_target = closest_building(player.ct.get_position(), player.map.healable_buildings)
    heal_target = best_healable_building(player)
    if heal_target and distance_squared(heal_target['position'], player.ct.get_position()) <= 2 or not player.heal_target:
        player.heal_target = heal_target

    if not player.heal_target:
        return False
    
    being_attacked = False
    heal_position = player.heal_target['position']
    if player.ct.is_in_vision(heal_position):
        builder = player.ct.get_tile_builder_bot_id(heal_position)
        being_attacked = builder is not None and player.ct.get_team(builder) != player.ct.get_team()

    building_to_heal = best_adjacent_healable_building(player)
    save_money = being_attacked and player.healed_last_turn
    if building_to_heal:
        player.healed_last_turn = try_heal(player, building_to_heal['position'], money_efficient=save_money)
    else:
        player.healed_last_turn = False
    make_move(player, player.heal_target['position'])
    building_to_heal = best_adjacent_healable_building(player)
    if building_to_heal:
        player.healed_last_turn = try_heal(player, building_to_heal['position'], money_efficient=save_money) or player.healed_last_turn
    return True