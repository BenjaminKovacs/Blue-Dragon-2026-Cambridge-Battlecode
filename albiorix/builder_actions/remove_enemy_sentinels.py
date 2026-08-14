from config import *
from util import *
from cambc import *

def get_gunner_direction(player, position):
    if not (position in player.map.adjacent_to_titanium_harvester):
        return None
    if not player.map.is_buildable(position):
        return None
    b = player.map.get_building_info(position)
    if b and b['type'] in [EntityType.SENTINEL, EntityType.GUNNER]:
        return None
    if not player.map.on_the_map(position) or not player.ct.is_in_vision(position):
        return None
    builder = player.ct.get_tile_builder_bot_id(position)
    if builder is not None and builder != player.ct.get_id():
        return None
    print("Position is adjacent to harvester and buildable")
    for d in DIRECTIONS:
        target = player.map.get_building_info(position.add(d))
        if target and target['team'] != player.ct.get_team() and target['type'] in [EntityType.SENTINEL, EntityType.GUNNER]:
            print("Found a target, confirming harvester direction:", d)
            for harvester_direction in ORTHOGONAL_DIRECTIONS:
                if harvester_direction != d:
                    b = player.map.get_building_info(position.add(harvester_direction))
                    if b and b['type'] == EntityType.HARVESTER:
                        print("Valid gunner position", position.add(harvester_direction))
                        return d
    return None

def get_sentinel_direction(player, position):
    if not player.map.nearest_enemy_turret or distance_squared(position, player.map.nearest_enemy_turret) > GameConstants.SENTINEL_VISION_RADIUS_SQ:
        return None
    if not (position in player.map.adjacent_to_titanium_harvester):
        return None
    if not player.map.is_buildable(position):
        return None
    b = player.map.get_building_info(position)
    if b and ((b['type'] in TURRETS) or ((b['type'] in CONVEYOR_BUILDINGS) and not maybe_securing_conveyor(player, b))):
        return None
    if not player.map.on_the_map(position) or not player.ct.is_in_vision(position):
        return None
    builder = player.ct.get_tile_builder_bot_id(position)
    if builder is not None and builder != player.ct.get_id():
        return None

    d = position.direction_to(player.map.nearest_enemy_turret)
    found_harvester = False
    for harvester_direction in ORTHOGONAL_DIRECTIONS:
        if harvester_direction != d:
            b = player.map.get_building_info(position.add(harvester_direction))
            if b and b['type'] == EntityType.HARVESTER:
                found_harvester = True
    if not found_harvester:
        return None
    
    shootable_tiles = player.ct.get_attackable_tiles_from(position, d, EntityType.SENTINEL)
    if player.map.nearest_enemy_turret in shootable_tiles:
        return d
    return None

def build_adjacent_sentinels(player):
    my_pos = player.ct.get_position()
    for d in DIRECTIONS:
        test_position = my_pos.add(d)
        result = get_sentinel_direction(player, test_position)
        if result != None:
            return try_build_sentinel(player, test_position, result)
    result = get_sentinel_direction(player, my_pos)
    if result and move_anywhere(player):
        try_build_sentinel(player, my_pos, result)
        return True
    return False

def build_adjacent_gunners(player):
    start_time = player.ct.get_cpu_time_elapsed()
    my_pos = player.ct.get_position()
    for d in DIRECTIONS:
        test_position = my_pos.add(d)
        result = get_gunner_direction(player, test_position)
        if result != None:
            return try_build_gunner(player, test_position, result)
    result = get_gunner_direction(player, my_pos)
    if result and move_anywhere(player):
        try_build_gunner(player, my_pos, result)
        return True
    end_time = player.ct.get_cpu_time_elapsed()
    print("build_adjacent_gunners run time:", end_time - start_time)

    start_time = player.ct.get_cpu_time_elapsed()
    result = build_adjacent_sentinels(player) #False
    end_time = player.ct.get_cpu_time_elapsed()
    print("build_adjacent_sentinels run time:", end_time - start_time)
    return result