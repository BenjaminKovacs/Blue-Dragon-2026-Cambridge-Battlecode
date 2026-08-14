from util import *
from cambc import *
from config import *
from pathing.pathing import make_move
from pathing.astar import unreachable_locations
from pathing.astar_conveyor import astar_conveyor_with_blocked, astar_conveyor

def is_securing_conveyor(player, building):
    if (building is None) or building['type'] is not EntityType.CONVEYOR:
        return False
    pos = building['position']
    test_building =  player.map.get_building_info(pos.add(building['direction']))
    return (test_building is not None) and (test_building['type'] is EntityType.HARVESTER)

def is_safe_ore(player, pos):
    map_instance = player.map

    if pos in unreachable_locations:
        if player.ct.get_current_round() - unreachable_locations[pos] < UNREACHABLE_MEMORY_ROUNDS:
            return False
    
    b = map_instance.get_building_info(pos)
    if b:
        if b['type'] is EntityType.CONVEYOR:
            test_building =  map_instance.get_building_info(pos.add(b['direction']))
            if test_building is None or test_building['type'] is not EntityType.HARVESTER:
                return False
        elif b['type'] is not EntityType.ROAD:
            # TODO: conveyors?
            return False

    # chack if all orthogonal neighbors are impassable
    all_impassable = True
    for d in ORTHOGONAL_DIRECTIONS:
        n = pos.add(d)
        if map_instance.is_passable(n):
            all_impassable = False
            break

    if all_impassable:
        return False

    # Check for adjacent enemy buildings if enabled
    if not IGNORE_ENEMY_NEIGHBORS:
        for d in ORTHOGONAL_DIRECTIONS:
            n = pos.add(d)
            if map_instance.on_the_map(n):
                b = map_instance.get_building_info(n)
                if b and b['team'] != player.ct.get_team():
                    return False
    
    # Check if another worker is already on the ore (and it's not us)
    if player.ct.is_in_vision(pos):
        worker_id = player.ct.get_tile_builder_bot_id(pos)
        if worker_id is not None and worker_id != player.ct.get_id():
            return False
        
    return True

def get_best_ore_target(player):
    map_instance = player.map
    ct = player.ct
    current_pos = ct.get_position()
    
    best_target = None
    min_dist = float('inf')
    
    # Scan all known terrain for ore
    # for x in range(map_instance.width):
    #     for y in range(map_instance.height):
    for pos in ct.get_nearby_tiles():
        # pos = Position(x, y)
        terrain = map_instance.get_terrain(pos)
        
        if terrain in [Environment.ORE_TITANIUM] or (terrain == Environment.ORE_AXIONITE and player.should_produce_axionite and player.map.closest_axionite_endpoint): # Don't harvest Environment.ORE_AXIONITE for now
            # Check if it already has a harvester (friendly or enemy)
            b = map_instance.get_building_info(pos)
            if b and b['type'] == EntityType.HARVESTER:
                continue
            # If it has a non-road/non-harvester building, we probably can't use it easily
            if b and (b['type'] not in [EntityType.ROAD, EntityType.HARVESTER, None]) and not is_securing_conveyor(player, b):
                continue

            if is_safe_ore(player, pos):
                dist = distance_squared(current_pos, pos)
                if dist < min_dist:
                    min_dist = dist
                    best_target = pos
                        
    return best_target

def should_secure_with_road(player, position, ore_position):
    if not SECURE_WITH_CONVEYORS or player.map.is_enemy_building(ore_position):
        return True
    direction = position.direction_to(ore_position)
    ORE = [Environment.ORE_TITANIUM, Environment.ORE_AXIONITE]
    terrain_up = player.map.get_terrain(position.add(direction.opposite()))
    terrain_left = player.map.get_terrain(position.add(direction.rotate_left().rotate_left()))
    terrain_right = player.map.get_terrain(position.add(direction.rotate_right().rotate_right()))
    adjacent_ore = (terrain_up in ORE) or (terrain_left in ORE) or (terrain_right in ORE)
    return (player.map.get_terrain(position) is not Environment.EMPTY) and adjacent_ore

def secure_position(player, position, ore_position):
    if SECURE_WITH_CONVEYORS:
        direction = position.direction_to(ore_position)
        if should_secure_with_road(player, position, ore_position):
            if player.ct.can_build_road(position): # Adjacent
                player.ct.build_road(position) 
                return True
        elif try_build_conveyor(player, position, direction):
            return True
    else:
        if player.ct.can_build_road(position): # Adjacent
            player.ct.build_road(position) 
            return True
    return False

def try_build_harvester(player, position, destroy=True):
    if not can_afford_unit(player.ct, EntityType.HARVESTER):
        return False
    if not player.ct.is_in_vision(position) or player.ct.get_tile_builder_bot_id(position):
        return False
    building = player.map.get_building_info(position)
    entity_type = building['type'] if building else None
    if (entity_type is not EntityType.ROAD) and not is_securing_conveyor(player, building): # DESTROYABLE_BUILDINGS:
        print("warning: try_build_harvester called at position", position, "with entity type", entity_type, "which should not be destroyed")
        return False
    if destroy and player.ct.can_destroy(position):
        player.ct.destroy(position)
    if player.ct.can_build_harvester(position):
        player.ct.build_harvester(position)
        return True
    return False

def process_ore_construction(player, target_pos) -> bool:
    """
    Handles the logic for building a harvester at target_pos.
    Returns True if an action was taken (turn consumed), False otherwise.
    """
    ct = player.ct
    map_instance = player.map
    my_pos = ct.get_position()
    print("running process_ore_construction, time already used:", player.ct.get_cpu_time_elapsed())

    # Identify unpaved neighbors of the target ore
    neighbors = [target_pos.add(d) for d in ORTHOGONAL_DIRECTIONS]
    unpaved_neighbors = []
    for n in neighbors:
        if not map_instance.on_the_map(n): continue
        if map_instance.get_terrain(n) == Environment.WALL: continue
        
        # Check if it's already paved or has a building
        b = map_instance.get_building_info(n)
        if b is None or (b['type'] is EntityType.ROAD and not should_secure_with_road(player, n, target_pos)):
            # No building, no road (assuming buildings includes roads)
            # We need to make sure we don't count the tile we are standing on if we plan to pave it now
            unpaved_neighbors.append(n)

    # If we are standing on the target ore
    if my_pos == target_pos:
        # 1. Check for adjacent enemy buildings (safety check before working)
        if not is_safe_ore(player, target_pos):
            player.target_ore = None
            return False # Re-evaluate next turn

        # 2. Build roads on adjacent tiles
        for n in unpaved_neighbors:
            if n == my_pos: continue # Should not happen if my_pos == target_pos

            if secure_position(player, n, target_pos):
                return True

        # 3. Check resources
        if not can_afford_unit(ct, EntityType.HARVESTER):
            return True # Wait for money on the ore tile

        # 4. If there is a road on the ore, destroy it ONLY if we can move off
        b = map_instance.get_building_info(my_pos)
        if b and ((b['type'] is EntityType.ROAD) or is_securing_conveyor(player, b)):
            if ct.can_destroy(my_pos):
                # Check for a valid escape tile
                escape_tile = None
                escape_dir = None
                for d in ORTHOGONAL_DIRECTIONS:
                    check_pos = my_pos.add(d)
                    if ct.can_move(d):
                        escape_tile = check_pos
                        escape_dir = d
                        break
                
                if escape_tile:
                    ct.destroy(my_pos)
                else:
                    # Stuck, can't safely destroy road yet
                    return True
        
        # 5. No road (or destroyed), move off to an adjacent tile to build
        # Calculate preferred direction (towards core)
        preferred_dirs = []
        if player.core_pos:
            path = astar_conveyor(player, (my_pos.x, my_pos.y), (player.core_pos.x, player.core_pos.y)) #astar_conveyor_with_blocked(player, (my_pos.x, my_pos.y), (player.core_pos.x, player.core_pos.y))
            if path and len(path) > 1:
                next_pos = path[1] # Position object
                d = get_direction(my_pos, next_pos)
                if d: preferred_dirs.append(d)

        # Prioritize preferred directions
        ortho_preferred = [d for d in preferred_dirs if d in ORTHOGONAL_DIRECTIONS]
        ortho_others = [d for d in ORTHOGONAL_DIRECTIONS if d not in preferred_dirs]
        all_dirs = ortho_preferred + ortho_others

        for d in all_dirs:
            move_pos = my_pos.add(d)
            if map_instance.is_passable(move_pos) and ct.can_move(d):
                ct.move(d)
                # Try to build immediately
                if ct.can_build_harvester(target_pos):
                    ct.build_harvester(target_pos)
                    player.last_built_harvester = target_pos
                    player.target_ore = None
                return True
        
        return True # Stuck? Wait.

    # If we are not on the target, but adjacent
    elif distance_squared(my_pos, target_pos) <= 2:
        # 1. Check if neighbors need paving
        if unpaved_neighbors:
            # Can we pave any neighbor from here?
            for n in unpaved_neighbors:
                if distance_squared(my_pos, n) <= 2:
                    if secure_position(player, n, target_pos):
                        return True
            
            # If we can't pave from here, we need to move closer to the unpaved spot.
            # Should we move onto the ore?
            b_target = map_instance.get_building_info(target_pos)
            target_has_road = b_target and ((b_target['type'] is EntityType.ROAD) or is_securing_conveyor(player, b_target))
            
            if target_has_road:
                # Move onto target to pave surroundings easily
                if try_move_with_build(player, target_pos):
                    return True
            else:
                # Target is rough, try to move to unpaved neighbor directly
                target_n = unpaved_neighbors[0]
                make_move(player, target_n)
                # path = astar_conveyor_with_blocked(player, (my_pos.x, my_pos.y), (target_n.x, target_n.y))
                # if path and len(path) > 1:
                #     try_move_with_build(player, Position(path[1][0], path[1][1]))
                #     return True
            return True

        # 2. Neighbors are paved. Check Money.
        if not can_afford_unit(ct, EntityType.HARVESTER):
            # Move onto target to wait
            if try_move_with_build(player, target_pos):
                return True
            return True

        # 3. Neighbors paved, Money Good. Build.
        # Try to build harvester if the tile is clear (no road)
        b = map_instance.get_building_info(target_pos)
        has_road = b and b['type'] == EntityType.ROAD
        
        if distance_squared(my_pos, target_pos) <= 1 and try_build_harvester(player, target_pos):
            player.last_built_harvester = target_pos
            player.target_ore = None # Job done
            return True
        else:
            # Must be orthogonal to build to ensure conveyors start correctly
            if distance_squared(my_pos, target_pos) > 1:
                # We are diagonal, move to an orthogonal neighbor
                for d in ORTHOGONAL_DIRECTIONS:
                    ortho_pos = target_pos.add(d)
                    # Check if we can move there (must be adjacent to us and passable)
                    if map_instance.is_passable(ortho_pos) and distance_squared(my_pos, ortho_pos) <= 2:
                        if try_move_with_build(player, ortho_pos):
                            return True
                
                # Fallback: Move onto the ore
                if try_move_with_build(player, target_pos):
                    return True

                return True # Wait/Stuck if no orthogonal spot is reachable

            if ct.can_build_harvester(target_pos):
                ct.build_harvester(target_pos)
                player.last_built_harvester = target_pos
                player.target_ore = None # Job done
                return True
            
    # Move towards target
    return make_move(player, target_pos)