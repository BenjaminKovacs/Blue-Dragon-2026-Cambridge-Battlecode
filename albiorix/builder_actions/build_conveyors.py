from cambc import *
from util import *
from config import *
from terrain.map import is_splitable_location
from pathing.pathing import make_move
from pathing.astar_conveyor import astar_conveyor, has_no_path
from pathing.astar_axionite import astar_axionite, has_no_axionite_path
from builder_actions.conveyor_attack import *

def build_turret_to_clear_path(player, build_pos, target_pos):
    if build_pos == player.ct.get_position():
        # We are standing on the tile we want to build on, but can't build. Try to move off without building a road.
        for d in DIRECTIONS:
            if player.ct.can_move(d):
                player.ct.move(d)
                break

    if build_pos == player.ct.get_position():
        # We are standing on the tile we want to build on, but can't build. Try to move off with building a road.
        for d in DIRECTIONS:
            move_pos = player.ct.get_position().add(d)
            if try_move_with_build(player, move_pos):
                break

    direction = direction_to(build_pos, target_pos)
    return try_build_sentinel(player, build_pos, direction)

def build_gunner_at_enemy_core(player, start_pos):
    enemy_core = get_enemy_core_pos(player)
    to_enemy = start_pos.direction_to(enemy_core)
    test_pos = start_pos.add(to_enemy)
    if distance_squared(enemy_core, test_pos) > GameConstants.GUNNER_VISION_RADIUS_SQ:
        return False
    while distance_squared(start_pos, test_pos) <= GameConstants.GUNNER_VISION_RADIUS_SQ:
        if distance_squared(test_pos, enemy_core) <= 1:
            if start_pos == player.ct.get_position():
                # We are standing on the tile we want to build on, but can't build. Try to move off without building a road.
                for d in DIRECTIONS:
                    if player.ct.can_move(d):
                        player.ct.move(d)
                        break

            if start_pos == player.ct.get_position():
                # We are standing on the tile we want to build on, but can't build. Try to move off with building a road.
                for d in DIRECTIONS:
                    move_pos = player.ct.get_position().add(d)
                    if try_move_with_build(player, move_pos):
                        break
            try_build_gunner(player, start_pos, to_enemy)
            return True
        if not player.map.on_the_map(test_pos) or player.map.terrain[test_pos.x][test_pos.y] is Environment.WALL or ((b := player.map.buildings[test_pos.x][test_pos.y]) is not None and (b['team'] is player.ct.get_team()) and (b['type'] is not EntityType.ROAD)):
            return False
        test_pos = test_pos.add(to_enemy)
    return False

def build_conveyor(ct: Controller, start_pos, path, player, avoid_conveyors=False, axionite=False) -> bool:
    if not path:
        print("Error: build_conveyor called with no path")
        return False
    
    building_id = ct.get_tile_building_id(start_pos)
    entity_type = ct.get_entity_type(building_id) if building_id else None

    if player.core_pos and distance_squared(start_pos, player.core_pos) <= 5 and path[-1] == player.core_pos:
        # We are building conveyors to the core, and close enogh we can build a conveyor directly to it.
        # This will make sure we do that rather than pointing the conveyor somewhere else (needed since the core is 3x3)
        for d in ORTHOGONAL_DIRECTIONS:
            check_pos = start_pos.add(d)
            if distance_squared(check_pos, player.core_pos) <= 2:
                direction = d
                break
    else:
        direction = get_direction(start_pos, path[1])

    # Destroy something if we need to do so to place a conveyor
    if entity_type == EntityType.CONVEYOR: 
        if ct.get_direction(building_id) == direction:
            return True
    elif entity_type == EntityType.BRIDGE: 
        bridge_output = ct.get_bridge_target(building_id)
        if not ct.is_in_vision(bridge_output) or player.map.is_buildable(bridge_output):
            return True

    destination_building = ct.get_tile_building_id(path[1])
    destination_team = ct.get_team(destination_building) if destination_building else None
    destination_type = ct.get_entity_type(destination_building) if destination_building else None
    destination_is_marker = destination_type == EntityType.MARKER if destination_building else False

    if (not axionite) and build_gunner_at_enemy_core(player, start_pos):
        return True
    elif direction in ORTHOGONAL_DIRECTIONS and ((not destination_building) or destination_team == ct.get_team() or destination_is_marker) and player.map.get_terrain(path[1]) == Environment.EMPTY and distance_squared(start_pos, path[1]) == 1:
        if try_build_conveyor(player, start_pos, direction):
            return True
        else:
            print("Can't build conveyor in direction", direction, "from", start_pos)
            print("Maybe there's not enough money?")
            return False
    else:
        # diagonal move, need to build a bridge
        bridge_target = farthest_tile_on_path_within_distance_squared(path, start_pos, 3)
        if is_enemy_building(player, bridge_target):
            print("Enemy building at bridge target", bridge_target, "need to build turret first")
            if build_turret_to_clear_path(player, start_pos, bridge_target):
               player.not_loose_path_start = start_pos
            return False
        elif distance_squared(start_pos, bridge_target) == 1:
            # we might be trying to bridge over ore, but fail since paths no longer require adjacency
            return try_build_conveyor(player, start_pos, start_pos.direction_to(bridge_target))
        else:
            if try_build_bridge(player, start_pos, bridge_target):
                if move_distance(bridge_target, player.core_pos) > 1:
                    player.bridge_target = bridge_target
                return True
            else:
                print("Can't build bridge from", start_pos, "to", bridge_target, "TODO")
                return False

def lowest_split_location(player, path):
    for pos in path[::-1]:
        if is_splitable_location(player, pos):
            return pos
    return None

def split_position(player, pos):
    current_building = player.map.get_building_info(pos)
    if current_building is not None and current_building['type'] ==  EntityType.SPLITTER:
        # TODO: check it's in the correct direction
        return True

    for d in ORTHOGONAL_DIRECTIONS:
        new_pos = pos.add(d)
        existing_building = player.map.get_building_info(new_pos)
        if (player.map.get_terrain(new_pos) == Environment.EMPTY) and existing_building is None:
            if player.ct.can_build_road(new_pos):
                player.ct.build_road(new_pos)
                print("built a road")
                return False

    conveyors = player.map.get_conveyors_to_here(pos)
    adjacent_conveyors = [c for c in conveyors if distance_squared(c, pos) <= 1]
    if len(adjacent_conveyors) > 1 or len(conveyors) < 1:
        print("failed conveyor condition")
        return False
    if len(adjacent_conveyors) >= 1:
        splitter_direction = direction_to(adjacent_conveyors[0], pos)
    elif player.map.get_building_info(pos) and player.map.get_building_info(pos)['type'] == EntityType.CONVEYOR:
        splitter_direction = player.map.get_building_info(pos)['direction']
    else:
        splitter_direction = Direction.NORTH
    
    print("trying to build splitter")
    if not can_afford_unit(player.ct, EntityType.SPLITTER):
        print("can't afford splitter")
        return False
    if player.ct.can_destroy(pos):
        player.ct.destroy(pos)
    if player.ct.can_build_splitter(pos, splitter_direction):
        player.ct.build_splitter(pos, splitter_direction)
        return True
    print("failed to build splitter")
    print(pos)
    print(splitter_direction)

def build_conveyor_to_target(player, start, target, avoid_conveyors=False, axionite=False) -> None:
    ct = player.ct
    map_instance = player.map
    player.bridge_target = None
    player.not_loose_path_start = None
    
    if not target:
        player.building_conveyors = False
        print("Error: build_conveyor_to_target called with no target")
        return False
    
    if start == target:
        print("build_conveyor_to_target called with start == target", target)
        return False
    
    if move_distance(start, target) <= 1 and target == player.core_pos:
        print("build_conveyor_to_target called with move_distance(start, target) <= 1 when going to the core at", target)
        return False

    current_pos = ct.get_position()

    start_building = player.map.get_building_info(start)
    all_blocked = True
    if start_building and start_building['type'] == EntityType.SPLITTER:
        for d in ORTHOGONAL_DIRECTIONS:
            if d == start_building['direction'].opposite():
                continue
            new_pos = start.add(d)
            if player.map.is_buildable(new_pos):
                start = new_pos
                all_blocked = False
                break
    else:
        all_blocked = False

    built_conveyor_path = get_conveyor_path_up(player, start)
    if len(built_conveyor_path) < 1:
        print("Error: get_conveyor_path_down returned empty path (called from build_conveyor_to_target)")
        return False

    last_enemy_index = 0
    for i, pos in enumerate(built_conveyor_path):
        b = player.map.get_building_info(pos)
        if b and b['team'] is not player.ct.get_team():
            last_enemy_index = i + 1

    if last_enemy_index >= len(built_conveyor_path):
        last_enemy_index -= 1
    built_conveyor_path = built_conveyor_path[last_enemy_index:]

    # if len(built_conveyor_path) < 1:
    #     print("Error: built_conveyor_path only contains enemy tiles (start has an enemy building)")
    #     return False

    if player.map.is_friendly_turret(start) or all_blocked:
        split_location = lowest_split_location(player, built_conveyor_path)
        if split_location:
            make_move(player, split_location)
            if split_position(player, split_location):
                player.not_loose_path_start = split_location
            else:
                player.not_loose_path_start = start
        return

    if not player.map.is_passable(start):
        if len(built_conveyor_path) > 1:
            start = built_conveyor_path[1]
        else:
            print("Error: build_conveyor_to_target called with impassable start")
            return False

    print("built path:", built_conveyor_path)
    if len(built_conveyor_path) > 1 and player.map.get_terrain(start) != Environment.EMPTY:
        start = built_conveyor_path[1]
        print("changing start to", start, "environment not empty")

    if axionite:
        path = astar_axionite(player, start, target, avoid_conveyors=avoid_conveyors)
        print(start,target)
        print("astar_axionite path:",path)
    else:
        path = astar_conveyor(player, start, target, current_path=built_conveyor_path, avoid_conveyors=avoid_conveyors)
    print("astar_conveyor finished time", player.ct.get_cpu_time_elapsed())
    if path: # prevent loops
        path_start_index = 0
        for i, pos in enumerate(path):
            if pos in built_conveyor_path:
                start = pos
                path_start_index = i
        path = path[path_start_index:]

    print("loop check finished time", player.ct.get_cpu_time_elapsed())
    print("conveyor path:", path)
    if move_distance(current_pos, start) <= 1:
        no_path = has_no_axionite_path(target) if axionite else has_no_path(target)
        if (no_path and not path) or ((path is not None) and len(path) < 2):
            return False
        print("calling build_conveyor time", player.ct.get_cpu_time_elapsed())
        build_conveyor(ct, start, path, player, avoid_conveyors, axionite)
        print("build_conveyor finished time", player.ct.get_cpu_time_elapsed())
    make_move(player, start)
    return True

def build_conveyor_to_core(player, start) -> None:
    target = player.core_pos
    if not target:
        print("Error: builder does not know core_pos (build_conveyor_to_core)")
        return

    # path_up = get_conveyor_path_up(player, start)
    # top = path_up[-1] if path_up else start
    axionite = player.map.is_axionite_conveyor[start.x][start.y] #player.map.get_terrain(top) == Environment.ORE_AXIONITE
    titanium = player.map.is_titanium_conveyor[start.x][start.y]
    use_axionite = axionite and not titanium

    enemy_target = should_target_enemy_core(player, start)
    if (not use_axionite) and enemy_target is not None:
        target = enemy_target
        print("Targetting enemy core at",target,"when building conveyors starting at", start)

    if use_axionite:
        if player.map.closest_axionite_endpoint and (player.conveyor_target is None or distance_squared(start, player.map.closest_axionite_endpoint) <= 1):
            player.conveyor_target = player.map.closest_axionite_endpoint
        if player.conveyor_target is not None:
            target = player.conveyor_target
    return build_conveyor_to_target(player, start, target, axionite=use_axionite)