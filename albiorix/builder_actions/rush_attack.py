import random

from cambc import *
import pathing.pathing as pathing
from exploration.rush_explore import *
from util import *

# non-centre directions
DIRECTIONS = [d for d in Direction if d != Direction.CENTRE]
ORTHOGONAL_DIRECTIONS = [Direction.NORTH, Direction.SOUTH, Direction.EAST, Direction.WEST]

def passable(player, positions):
    return list(filter(lambda p: player.map.is_passable(p), positions))

def passable_nonoccupied(player, positions):
    return list(filter(lambda p: player.map.is_passable(p) and (not player.ct.is_in_vision(p) or player.ct.get_tile_builder_bot_id(p) is None), positions))

def is_friendly_conveyor(player, position):
    current_building = player.map.get_building_info(position)
    return current_building and current_building['type'] in CONVEYOR_BUILDINGS and current_building['team'] == player.ct.get_team()

def not_friendly_conveyor(player, positions):
    def check_pos(pos):
        return not is_friendly_conveyor(player, pos)
    return list(filter(check_pos, positions))

def buildable(player, positions):
    return list(filter(lambda p: player.map.is_buildable(p) and not player.map.is_friendly_turret(p), positions))

def closest_enemy_builder(player):
    builders = player.ct.get_nearby_units()
    builder_positions = [player.ct.get_position(builder_id) for builder_id in builders if player.ct.get_team(builder_id) is not player.ct.get_team() and player.ct.get_entity_type(builder_id) is EntityType.BUILDER_BOT]
    if len(builder_positions) == 0:
        return None
    return closest(player.ct.get_position(), builder_positions)

def should_attack(player, building):
    enemy_builder = closest_enemy_builder(player)
    return (enemy_builder is None) or move_distance(player.ct.get_position(), enemy_builder) > 2 or building['hp'] <= building['max_hp'] - 4 or building['hp'] <= 4 or (move_distance(player.ct.get_position(), enemy_builder) > 1 and building['hp'] <= 6) or can_afford_unit(player.ct, EntityType.HARVESTER)

def build_sentinel_or_barrier(player, build_position, harvester_position):
    enemy_core = get_enemy_core_pos(player)
    direction = build_position.direction_to(enemy_core)
    if direction == build_position.direction_to(harvester_position):
        direction = direction.rotate_right()
    if player.map.get_terrain(harvester_position) is Environment.ORE_TITANIUM:
        num_existing_sentinels = 0
        for d in ORTHOGONAL_DIRECTIONS:
            b = player.map.get_building_info(harvester_position.add(d))
            if b and b['type'] == EntityType.SENTINEL and b['team'] == player.ct.get_team():
                num_existing_sentinels += 1
        if num_existing_sentinels < 2:
            return try_build_sentinel(player, build_position, direction)
        else:
            return try_build_barrier(player, build_position)
    elif player.map.get_terrain(harvester_position) is Environment.ORE_AXIONITE:
        return try_build_barrier(player, build_position)
    else:
        print("Harvester at pos", harvester_position, "on unknown resource type",player.map.get_terrain(target['position']))
        return try_build_barrier(player, build_position)

def build_adjacent_sentinels(player):
    my_pos = player.ct.get_position()
    for d in DIRECTIONS:
        test_pos = my_pos.add(d)
        if (test_pos not in player.map.adjacent_to_harvester) or not player.map.is_buildable(test_pos):
            continue
        test_building = player.map.buildings[test_pos.x][test_pos.y]
        if (test_building is not None) and ((test_building['team'] is not player.ct.get_team()) or (test_building['type'] is not EntityType.ROAD)):
            continue
        for harvester_direction in ORTHOGONAL_DIRECTIONS:
            harvester_position = test_pos.add(harvester_direction)
            b = player.map.get_building_info(harvester_position)
            if b is not None and b['type'] is EntityType.HARVESTER and b['team'] is not player.ct.get_team():
                return build_sentinel_or_barrier(player, test_pos, harvester_position)
    return False

def throw_enemy_healers(player):
    #TODO: FIx launchers and readd this
    return False
    """
    my_pos = player.ct.get_position()
    adjacent_to_enemy_builders = set()
    builders = get_nearby_builders(player.ct)
    for b in builders:
        if player.ct.get_team(b) is player.ct.get_team():
            continue
        pos = player.ct.get_position(b)
        if pos in player.map.adjacent_to_friendly_launcher:
            continue
        for d in DIRECTIONS:
            adjacent_to_enemy_builders.add(pos.add(d))
    
    for d in DIRECTIONS:
        test_pos = my_pos.add(d)
        if (test_pos in adjacent_to_enemy_builders) and player.map.is_buildable_without_replacement(test_pos) and (test_pos not in player.map.adjacent_to_friendly_launcher):
            return try_build_launcher(player, test_pos)

    # allow launchers to be adjacent if not possible to build non-adjacent
    for d in DIRECTIONS:
        test_pos = my_pos.add(d)
        if (test_pos in adjacent_to_enemy_builders) and player.map.is_buildable_without_replacement(test_pos):
            return try_build_launcher(player, test_pos)
    
    return False
    """
def run_attack(player) -> None:
    buildings = player.map.nearby_buildings
    team = player.ct.get_team()
    enemy_buildings = list(filter(lambda b: b["team"] != team, buildings))
    enemy_harvesters = list(filter(lambda b: b["type"] == EntityType.HARVESTER, enemy_buildings))

    def not_orthogonally_surrounded(position):
        for direction in ORTHOGONAL_DIRECTIONS:
            new_position = position.add(direction)
            builder = 1 #None
            if not player.map.on_the_map(new_position):
                continue
            if player.ct.is_in_vision(new_position):
                builder = player.ct.get_tile_builder_bot_id(new_position)
            occupied = builder is not None and builder != player.ct.get_id()
            if player.map.is_passable(position.add(direction)) and not occupied and not is_friendly_conveyor(player, position.add(direction)):
                return True
        return False

    open_harvesters = list(filter(lambda b: not_orthogonally_surrounded(b['position']), enemy_harvesters))

    if (player.turns_rushing_target > 25) or (player.rush_target and player.ct.is_in_vision(player.rush_target) and (not player.map.is_enemy_building(player.rush_target) or (not player.map.is_passable(player.rush_target)) or (player.ct.get_tile_builder_bot_id(player.rush_target) is not None and player.ct.get_tile_builder_bot_id(player.rush_target) != player.ct.get_id()))):
        player.rush_target = None
        player.rush_target_launcher = None
        player.turns_rushing_target = 0
    else:
        player.turns_rushing_target += 1

    if len(open_harvesters) > 0:
        target = closest_building(player.ct.get_position(), open_harvesters)
        current_building = player.map.get_building_info(player.ct.get_position())
        on_friendly_conveyor = current_building and current_building['type'] in CONVEYOR_BUILDINGS and current_building['team'] == player.ct.get_team()
        if player.ct.get_position().distance_squared(target['position']) == 1 and not on_friendly_conveyor:
            if player.map.is_enemy_building(player.ct.get_position()):
                target_building = player.map.get_building_info(player.ct.get_position())
                if build_adjacent_sentinels(player):
                    print("building sentinels next to enemy harvester")
                elif target_building is not None and target_building['hp'] > 2 and throw_enemy_healers(player):
                    print("built a launcher to throw enemy trying to heal")
                elif should_attack(player, target_building):
                    try_attack(player)
                player.rush_target = player.ct.get_position()
                player.turns_rushing_target = 0

            else:
                build_position = player.ct.get_position()
                move_anywhere(player)
                build_sentinel_or_barrier(player, build_position, target['position'])
                try_build_road(player, build_position)
                rush_explore(player)

        else:
            build_adjacent_sentinels(player)
            destination = closest(player.ct.get_position(), not_friendly_conveyor(player, passable_nonoccupied(player, orthogonal_positions(target['position']))))
            launcher_location = closest(destination, buildable(player, adjacent_positions(player.ct.get_position())))
            adjacent_launchers = [p for p in adjacent_positions(player.ct.get_position()) if player.map.get_building_info(p) is not None and player.map.get_building_info(p)['type'] == EntityType.LAUNCHER]
            best_adjacent_launcher = closest(destination, adjacent_launchers)
            if player.ct.get_position().distance_squared(destination) <= 2 or player.ct.get_position().distance_squared(target['position']) < 9:
                pathing.make_move(player, destination)
            elif best_adjacent_launcher and player.map.is_walkable(destination) and best_adjacent_launcher.distance_squared(best_adjacent_launcher) <= GameConstants.LAUNCHER_VISION_RADIUS_SQ:
                pass
            elif launcher_location and not best_adjacent_launcher and player.map.is_walkable(destination) and launcher_location.distance_squared(destination) <= GameConstants.LAUNCHER_VISION_RADIUS_SQ and try_build_launcher(player, launcher_location):
                player.rush_target_launcher = launcher_location
            elif player.rush_target_launcher and distance_squared(player.rush_target_launcher, player.ct.get_position()) < 25:
                pathing.make_move(player, player.rush_target_launcher)
            elif player.rush_target and distance_squared(player.rush_target, player.ct.get_position()) < 20:
                pathing.make_move(player, player.rush_target)
            else:
                pathing.make_move(player, target['position'])
            build_adjacent_sentinels(player)
        
        if player.ct.get_position().distance_squared(target['position']) == 1 and player.map.is_enemy_building(player.ct.get_position()):
            if should_attack(player, player.map.get_building_info(player.ct.get_position())):
                try_attack(player)
    elif player.rush_target and player.rush_target_launcher and player.map.get_building_info(player.rush_target_launcher)['type'] == EntityType.LAUNCHER and player.map.get_building_info(player.rush_target_launcher)['team'] == player.ct.get_team() and player.ct.get_position().distance_squared(player.rush_target) > 8:
        pathing.make_move(player, player.rush_target_launcher)
    elif player.rush_target:
        pathing.make_move(player, player.rush_target)
    else:
        rush_explore(player)