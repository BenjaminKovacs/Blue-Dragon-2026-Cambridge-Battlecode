from cambc import *
from util import *
from config import *
from pathing.pathing import make_move

def is_valid_foundry_location(player, position):
    # Can build there
    if not player.map.is_buildable(position):
        return False
    # Don't replace a turret
    if player.map.is_friendly_turret(position):
        return False
    # Don't replace a bridge or harvester, can't build on core
    b = player.map.get_building_info(position)
    if b and b['type'] == EntityType.FOUNDRY:
        return True
    if b and b['type'] in [EntityType.BRIDGE, EntityType.CORE, EntityType.HARVESTER, EntityType.SPLITTER]:
        return False
    # No bridges to here
    for c in get_conveyors_leading_here(player, position):
        if distance_squared(position, c) > 1:
            return False
    adjacent_buildable = 0
    for d in ORTHOGONAL_DIRECTIONS:
        check_position = position.add(d)
        # Can build/has core next to it
        if player.map.is_buildable(check_position):
            adjacent_buildable += 1
        # Not adjacent to enemy building
        if player.map.is_enemy_building(check_position):
            return False
    return adjacent_buildable >= 2

def get_foundry_position(player, split_position):
    best = None
    best_distance = float('inf')
    for d in ORTHOGONAL_DIRECTIONS:
        test_position = split_position.add(d)
        distance = distance_squared(test_position, player.core_pos)
        if (distance < best_distance) and is_valid_foundry_location(player, test_position):
            best_distance = distance
            best = test_position
        b = player.map.get_building_info(test_position)
        if b and b['type'] == EntityType.FOUNDRY:
            return test_position
    return best

def check_split_to_foundry(player, split_position):
    if not player.map.is_buildable(split_position):
        return None
    enemy_building_count = 0
    split_to_existing_foundry = None
    for d in ORTHOGONAL_DIRECTIONS:
        test_position = split_position.add(d)
        b = player.map.get_building_info(test_position)
        if b and b['type'] == EntityType.FOUNDRY:
            split_to_existing_foundry = test_position
        if player.map.is_enemy_building(test_position):
            enemy_building_count += 1
    if enemy_building_count > 1:
        return None
    if split_to_existing_foundry:
        split_building = player.map.get_building_info(split_position)
        if (not split_building) or (split_building['type'] == EntityType.SPLITTER):
            return split_to_existing_foundry
    return get_foundry_position(player, split_position)

def get_foundry_split_position(player, distance_limit=float('inf')):
    best = None
    best_distance = distance_limit
    my_position = player.ct.get_position()
    for position in player.map.axionite_conveyors_adjacent_to_core:
        if not player.map.is_titanium_conveyor[position.x][position.y]:
            continue
        distance = distance_squared(my_position, position)
        if (distance < best_distance) and check_split_to_foundry(player, position):
            best = position
            best_distance = distance
    return best

def get_splitter_direction(player, split_position, foundry_position):
    # TODO: improve to take into account the core position and adjacent conveyors
    for d in ORTHOGONAL_DIRECTIONS:
        if player.map.is_enemy_building(split_position.add(d)):
            return d.opposite()
    result = split_position.direction_to(foundry_position)
    intake_position = split_position.add(result.opposite())
    if distance_squared(intake_position, player.core_pos) <= 2:
        result = result.rotate_right().rotate_right()
    return result

def construct_foundry(player, split_position):
    if not player.map.is_buildable(split_position):
        return False
    foundry_position = get_foundry_position(player, split_position)
    if foundry_position is None:
        return False
    current_building = player.map.get_building_info(split_position)
    splitter_built = current_building and current_building['type'] == EntityType.SPLITTER and current_building['direction'] != foundry_position.direction_to(split_position)
    splitter_direction = current_building['direction'] if splitter_built else get_splitter_direction(player, split_position, foundry_position)
    
    # Convert all conveyors going into the splitter in the wrong direction into bridges
    for d in ORTHOGONAL_DIRECTIONS:
        if d == splitter_direction.opposite():
            continue
        fix_position = split_position.add(d)
        if fix_position == foundry_position:
            continue
        b = player.map.get_building_info(fix_position)
        if b and b['team'] == player.ct.get_team() and b['type'] == EntityType.CONVEYOR and b['direction'] == d.opposite():
            if distance_squared(player.ct.get_position(), fix_position) > 2:
                make_move(player, fix_position)
            if distance_squared(player.ct.get_position(), fix_position) <= 2:
                try_build_bridge(player, fix_position, split_position)
            print("Trying to build bridge at",fix_position, "to", split_position,"for foundry at",foundry_position)
            return True
        elif (not b) and player.map.is_buildable(fix_position):
            if distance_squared(player.ct.get_position(), fix_position) > 2:
                make_move(player, fix_position)
            if distance_squared(player.ct.get_position(), fix_position) <= 2:
                try_build_road(player, fix_position)
            print("Trying to build road at",fix_position, "to secure it for splitter placement to build foundry at",foundry_position)
            return True

    foundry_building = player.map.get_building_info(foundry_position)

    # Convert all conveyors going into the foundry to bridges to the splitter
    for d in ORTHOGONAL_DIRECTIONS:
        fix_position = foundry_position.add(d)
        if fix_position == split_position:
            continue
        b = player.map.get_building_info(fix_position)
        if b and b['team'] == player.ct.get_team() and b['type'] == EntityType.CONVEYOR and b['direction'] == d.opposite():
            if distance_squared(player.ct.get_position(), fix_position) > 2:
                make_move(player, fix_position)
            if distance_squared(player.ct.get_position(), fix_position) <= 2:
                if player.map.line_load_counts[fix_position.x][fix_position.y] + player.map.line_load_counts[split_position.x][split_position.y] <= 4:
                    try_build_bridge(player, fix_position, split_position)
                    print("Trying to build bridge at",fix_position, "to", split_position,"for foundry at",foundry_position)
                else:
                    if foundry_building and foundry_building['type'] == EntityType.CONVEYOR:
                        bridge_end = foundry_position.add(foundry_building['direction'])
                    elif player.map.is_axionite_conveyor[fix_position.x][fix_position.y]:
                        bridge_end = split_position
                    else:
                        bridge_end = player.core_pos.add(player.core_pos.direction_to(fix_position))
                    if distance_squared(fix_position, bridge_end) > 9:
                        print("Error: foundry position too far from core to bridge to it")
                        bridge_end = split_position
                    try_build_bridge(player, fix_position, bridge_end)
                    print("(avoiding splitter) Trying to build bridge at",fix_position, "to", bridge_end,"for foundry at",foundry_position)
            return True
        elif (not b) and player.map.is_buildable(fix_position):
            if distance_squared(player.ct.get_position(), fix_position) > 2:
                make_move(player, fix_position)
            if distance_squared(player.ct.get_position(), fix_position) <= 2:
                try_build_road(player, fix_position)
            print("Trying to build road at",fix_position, "to secure it for foundry at",foundry_position)
            return True
        
    # Build splitter
    if not splitter_built:
        print("Trying to build splitter at",split_position,"for foundry at",foundry_position)
        moved = False
        if distance_squared(player.ct.get_position(), fix_position) > 2:
            make_move(player, split_position)
            moved = True
        if distance_squared(player.ct.get_position(), split_position) <= 2:
            try_build_splitter(player, split_position, splitter_direction)
        if not moved and player.ct.get_position() != fix_position:
            make_move(player, split_position)
        return True
    
    if foundry_building and foundry_building['type'] == EntityType.FOUNDRY:
        print("Foundry already exists at", foundry_position, "from split position", split_position)
        return False

    # Build foundry
    print("Trying to build foundry at", foundry_position, "from split position", split_position)
    if player.ct.get_position() == foundry_position:
        if move_anywhere(player):
            try_build_foundry(player, foundry_position)
        else:
            make_move(player, split_position)
        return True
    elif distance_squared(player.ct.get_position(), foundry_position) <= 2:
        try_build_foundry(player, foundry_position)
        return True
    else:
        make_move(player, split_position)
        return True

def run_construct_foundry(player):
    split_position = get_foundry_split_position(player)
    if split_position is None:
        return False
    return construct_foundry(player, split_position)
