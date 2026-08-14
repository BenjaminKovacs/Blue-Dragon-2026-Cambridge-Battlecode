from cambc import Controller, Direction, Position, EntityType, GameConstants
from terrain.symmetry import Symmetry
from config import *
import random

ORTHOGONAL_DIRECTIONS = [Direction.NORTH, Direction.SOUTH, Direction.EAST, Direction.WEST]

def get_direction_delta(dx, dy) -> Direction | None:
    """Get the direction corresponding to a delta (dx, dy)."""
    if dx == 1 and dy == 0:
        return Direction.EAST
    elif dx == -1 and dy == 0:
        return Direction.WEST
    elif dx == 0 and dy == 1:
        return Direction.SOUTH
    elif dx == 0 and dy == -1:
        return Direction.NORTH
    elif dx == 1 and dy == 1:
        return Direction.SOUTHEAST
    elif dx == 1 and dy == -1:
        return Direction.NORTHEAST
    elif dx == -1 and dy == 1:
        return Direction.SOUTHWEST
    elif dx == -1 and dy == -1:
        return Direction.NORTHWEST
    return None

def get_direction_object(from_pos: Position, to_pos: Position) -> Direction | None:
    """Get the direction from from_pos to to_pos."""
    dx = to_pos.x - from_pos.x
    dy = to_pos.y - from_pos.y
    return get_direction_delta(dx, dy)

def direction_to(from_pos: Position, to_pos: Position) -> Direction | None:
    """Get the direction from from_pos to to_pos."""
    dx = to_pos.x - from_pos.x
    dy = to_pos.y - from_pos.y
    if dx == 0 and dy == 0:
        return None

    adx, ady = abs(dx), abs(dy)
    if adx > 2.414 * ady:
        return Direction.EAST if dx > 0 else Direction.WEST
    elif ady > 2.414 * adx:
        return Direction.SOUTH if dy > 0 else Direction.NORTH
    return get_direction_delta(1 if dx > 0 else -1, 1 if dy > 0 else -1)

def get_direction_tuple(from_pos: tuple, to_pos: tuple) -> Direction | None:
    dx = to_pos[0] - from_pos[0]
    dy = to_pos[1] - from_pos[1]
    return get_direction_delta(dx, dy)

def get_direction(from_pos, to_pos) -> Direction | None:
    """Get the direction from from_pos to to_pos."""
    if isinstance(from_pos, Position):
        if isinstance(to_pos, tuple):
            to_pos = Position(to_pos[0], to_pos[1])
        return get_direction_object(from_pos, to_pos)
    elif isinstance(from_pos, tuple):
        if isinstance(to_pos, Position):
            to_pos = (to_pos.x, to_pos.y)
        return get_direction_tuple(from_pos, to_pos)
    else:        raise ValueError("Invalid position type")

def try_move(ct: Controller, target_pos: Position) -> bool:
    """Compute direction to target_pos and attempt to move there."""
    dir = get_direction(ct.get_position(), target_pos)
    if dir is not None and ct.can_move(dir):
        ct.move(dir)
        return True
    return False

def try_move_with_road(ct: Controller, target_pos: Position, map_instance) -> bool:
    """Compute direction to target_pos, build road if necessary, and attempt to move there."""
    if map_instance.get_cost(target_pos) > 1 and ct.can_build_road(target_pos):
        ct.build_road(target_pos)
    return try_move(ct, target_pos)

def try_move_with_conveyor(player, target_pos: Position) -> bool:
    """Compute direction to target_pos, build conveyor if necessary, and attempt to move there."""
    ct = player.ct
    map_instance = player.map
    start_pos = ct.get_position()
    direction = get_direction(target_pos, start_pos)
    if direction in ORTHOGONAL_DIRECTIONS:
        if map_instance.get_cost(target_pos) > 1 and ct.can_build_conveyor(target_pos, direction):
            ct.build_conveyor(target_pos, direction)
    else:
        if map_instance.get_cost(target_pos) > 1 and ct.can_build_bridge(target_pos, start_pos):
            ct.build_bridge(target_pos, start_pos)
    return try_move(ct, target_pos)

def try_move_with_build(player, target_pos: Position) -> bool:
    if player.conveyor_build_mode:
        return try_move_with_conveyor(player, target_pos)
    else:
        return try_move_with_road(player.ct, target_pos, player.map)

def find_core_pos(player) -> Position | None:
    """Find the position of the allied core by checking adjacent tiles."""
    ct = player.ct
    for d in Direction:
        adj_pos = ct.get_position().add(d)
        if not player.map.on_the_map(adj_pos):
            continue
        building_id = ct.get_tile_building_id(adj_pos)
        if building_id and ct.get_entity_type(building_id) == EntityType.CORE and ct.get_team(building_id) == ct.get_team():
            return ct.get_position(building_id)
    return None

def move_distance(pos1: Position, pos2: Position) -> int:
    """Calculate the Chebyshev distance between two positions."""
    return max(abs(pos1.x - pos2.x), abs(pos1.y - pos2.y))

# def distance_squared(pos1: Position, pos2: Position) -> int:
#     """Calculate the squared Euclidean distance between two positions."""
#     return (pos1.x - pos2.x)**2 + (pos1.y - pos2.y)**2
def distance_squared(pos1: Position, pos2: Position) -> int:
    """Calculate the squared Euclidean distance between two positions."""
    x1, y1 = pos1
    x2, y2 = pos2
    return (x1 - x2)**2 + (y1 - y2)**2

def farthest_tile_on_path_within_distance_squared(path: list[tuple[int, int]], current_pos: Position, max_range: int) -> Position:
    """Given a path (list of (x,y) tuples), return the farthest tile on the path that is within max_range of current_pos."""
    for x, y in reversed(path):
        if distance_squared(current_pos, Position(x, y)) <= max_range**2:
            return Position(x, y)
    return current_pos  # If no tile on the path is within range, return current position

def is_enemy_building(player, pos: Position) -> bool:
    """Check if there is an enemy building at the given position."""
    building = player.map.get_building_info(pos)
    return building is not None and player.ct.get_team() != building['team']

def try_attack(player):
    position = player.ct.get_position()
    if player.ct.can_fire(position):
        player.ct.fire(position)
        return True
    return False

def try_build_barrier(player, position, destroy=True):
    if not can_afford_unit(player.ct, EntityType.BARRIER):
        return False
    if not player.ct.is_in_vision(position) or player.ct.get_tile_builder_bot_id(position):
        return False
    building_id = player.ct.get_tile_building_id(position)
    entity_type = player.ct.get_entity_type(building_id) if building_id else None
    if entity_type not in DESTROYABLE_BUILDINGS:
        print("warning: try_build_sentinel called at position", position, "with entity type", entity_type, "which should not be destroyed")
        return False
    if destroy and player.ct.can_destroy(position):
        player.ct.destroy(position)
    if player.ct.can_build_barrier(position):
        player.ct.build_barrier(position)
        return True
    return False

def try_build_foundry(player, position, destroy=True):
    if not can_afford_unit(player.ct, EntityType.FOUNDRY):
        return False
    if not player.ct.is_in_vision(position) or player.ct.get_tile_builder_bot_id(position):
        return False
    building_id = player.ct.get_tile_building_id(position)
    entity_type = player.ct.get_entity_type(building_id) if building_id else None
    if entity_type not in DESTROYABLE_BUILDINGS:
        print("warning: try_build_sentinel called at position", position, "with entity type", entity_type, "which should not be destroyed")
        return False
    if destroy and player.ct.can_destroy(position):
        player.ct.destroy(position)
    if player.ct.can_build_foundry(position):
        player.ct.build_foundry(position)
        return True
    return False

def try_build_sentinel(player, position, direction, destroy=True):
    if not can_afford_unit(player.ct, EntityType.SENTINEL):
        return False
    if not player.ct.is_in_vision(position) or player.ct.get_tile_builder_bot_id(position):
        return False
    building_id = player.ct.get_tile_building_id(position)
    entity_type = player.ct.get_entity_type(building_id) if building_id else None
    if entity_type not in DESTROYABLE_BUILDINGS+[EntityType.BARRIER]:
        print("warning: try_build_sentinel called at position", position, "with entity type", entity_type, "which should not be destroyed")
        return False
    if destroy and player.ct.can_destroy(position):
        player.ct.destroy(position)
    if player.ct.can_build_sentinel(position, direction):
        player.ct.build_sentinel(position, direction)
        return True
    return False

def try_build_gunner(player, position, direction, destroy=True):
    if not can_afford_unit(player.ct, EntityType.GUNNER):
        return False
    if not player.ct.is_in_vision(position) or player.ct.get_tile_builder_bot_id(position):
        return False
    building_id = player.ct.get_tile_building_id(position)
    entity_type = player.ct.get_entity_type(building_id) if building_id else None
    if entity_type not in DESTROYABLE_BUILDINGS+[EntityType.BARRIER]:
        print("warning: try_build_gunner called at position", position, "with entity type", entity_type, "which should not be destroyed")
        return False
    if destroy and player.ct.can_destroy(position):
        player.ct.destroy(position)
    if player.ct.can_build_gunner(position, direction):
        player.ct.build_gunner(position, direction)
        return True
    return False

def try_build_launcher(player, position, destroy=True):
    if not can_afford_unit(player.ct, EntityType.LAUNCHER):
        return False
    if not player.ct.is_in_vision(position) or player.ct.get_tile_builder_bot_id(position):
        return False
    building_id = player.ct.get_tile_building_id(position)
    entity_type = player.ct.get_entity_type(building_id) if building_id else None
    if entity_type not in [EntityType.ROAD]: # DESTROYABLE_BUILDINGS:
        print("warning: try_build_launcher called at position", position, "with entity type", entity_type, "which should not be destroyed")
        return False
    if destroy and player.ct.can_destroy(position):
        player.ct.destroy(position)
    if player.ct.can_build_launcher(position):
        player.ct.build_launcher(position)
        return True
    return False

def try_build_foundry(player, position, destroy=True):
    if not can_afford_unit(player.ct, EntityType.FOUNDRY):
        return False
    if not player.ct.is_in_vision(position) or player.ct.get_tile_builder_bot_id(position):
        return False
    building_id = player.ct.get_tile_building_id(position)
    entity_type = player.ct.get_entity_type(building_id) if building_id else None
    if entity_type not in DESTROYABLE_BUILDINGS:
        print("warning: try_build_foundry called at position", position, "with entity type", entity_type, "which should not be destroyed")
        return False
    if destroy and player.ct.can_destroy(position):
        player.ct.destroy(position)
    if player.ct.can_build_foundry(position):
        player.ct.build_foundry(position)
        return True
    return False

def try_build_bridge(player, position, target, destroy=True):
    if not can_afford_unit(player.ct, EntityType.BRIDGE):
        return False
    building_id = player.ct.get_tile_building_id(position)
    entity_type = player.ct.get_entity_type(building_id) if building_id else None
    if entity_type not in DESTROYABLE_BUILDINGS:
        print("warning: try_build_bridge called at position", position, "with entity type", entity_type, "which should not be destroyed")
        return False
    if destroy and player.ct.can_destroy(position):
        player.ct.destroy(position)
    if player.ct.can_build_bridge(position, target):
        player.ct.build_bridge(position, target)
        return True
    return False

def try_build_conveyor(player, position, direction, destroy=True):
    if not can_afford_unit(player.ct, EntityType.CONVEYOR):
        return False
    building_id = player.ct.get_tile_building_id(position)
    entity_type = player.ct.get_entity_type(building_id) if building_id else None
    if entity_type not in DESTROYABLE_BUILDINGS:
        print("warning: try_build_conveyor called at position", position, "with entity type", entity_type, "which should not be destroyed")
        return False
    if destroy and player.ct.can_destroy(position):
        player.ct.destroy(position)
    if player.ct.can_build_conveyor(position, direction):
        player.ct.build_conveyor(position, direction)
        return True
    return False

def try_build_splitter(player, position, direction, destroy=True):
    if not can_afford_unit(player.ct, EntityType.SPLITTER):
        return False
    building_id = player.ct.get_tile_building_id(position)
    entity_type = player.ct.get_entity_type(building_id) if building_id else None
    if entity_type not in DESTROYABLE_BUILDINGS:
        print("warning: try_build_splitter called at position", position, "with entity type", entity_type, "which should not be destroyed")
        return False
    if destroy and player.ct.can_destroy(position):
        player.ct.destroy(position)
    if player.ct.can_build_splitter(position, direction):
        player.ct.build_splitter(position, direction)
        return True
    return False

def try_build_road(player, position):
    if player.ct.can_build_road(position):
        player.ct.build_road(position)
        return True
    return False

def get_conveyors_leading_here(player, position):
    return player.map.get_conveyors_to_here(position)

# def find_junction(player, position):
#     start = position
#     conveyors = get_conveyors_leading_here(player, position)
#     while len(conveyors) == 1 and conveyors[0] != start:
#         position = conveyors[0]
#         conveyors = get_conveyors_leading_here(player, position)
#     if len(conveyors) == 1 and conveyors[0] == start:
#         return None
#     return position

def maybe_securing_conveyor(player, building):
    if (building is None) or building['type'] is not EntityType.CONVEYOR:
        return False
    pos = building['position']
    points_to_location = pos.add(building['direction'])
    test_building =  player.map.get_building_info(points_to_location)
    points_to_harvester = (test_building is not None) and (test_building['type'] is EntityType.HARVESTER)
    points_to_ore = player.map.get_terrain(points_to_location) in [Environment.ORE_TITANIUM, Environment.ORE_AXIONITE]
    return points_to_harvester or (points_to_ore and not player.map.is_titanium_conveyor[pos.x][pos.y] and not player.map.is_axionite_conveyor[pos.x][pos.y])

def get_conveyor_path_up(player, position, exclude_securing=True):
    path = [position]
    conveyors = get_conveyors_leading_here(player, position)
    while len(conveyors) > 0:
        if player.map.terrain[position.x][position.y] is not Environment.EMPTY and exclude_securing:
            for c in conveyors:
                if not maybe_securing_conveyor(player, player.map.buildings[c.x][c.y]):
                    position = c
                    break
        else:
            position = conveyors[0]
        conveyors = get_conveyors_leading_here(player, position)
        if position in path:
            break
        path.append(position)
    return path

# Returns the path of conveyors down from a specified point
# If target_head is specified, returns the path that contains target_head if a splitter is reached
# If target head is None, tries to find a new place to build next to the splitter if there is one
def get_conveyor_path_down(player, start_pos, target_head, path=[]):
    current_pos = start_pos
    while True:
        path.append(current_pos)
        conveyor = player.map.get_building_info(current_pos)
        if conveyor is None or conveyor['type'] not in [EntityType.CONVEYOR, EntityType.ARMOURED_CONVEYOR, EntityType.BRIDGE, EntityType.SPLITTER]:
            break
        if conveyor['type'] in [EntityType.CONVEYOR, EntityType.ARMOURED_CONVEYOR]:
            direction = conveyor['direction']
            current_pos = current_pos.add(direction)
        elif conveyor['type'] == EntityType.SPLITTER:
            for d in ORTHOGONAL_DIRECTIONS:
                if d == conveyor['direction'].opposite():
                    continue
                new_pos = current_pos.add(d)
                if target_head: # search for a path down containing target_head
                    new_path = get_conveyor_path_down(player, new_pos, target_head, path=path[:])
                    if new_path and target_head in new_path:
                        return new_path
                elif player.map.get_building_info(new_pos) is None: # search for a new place to build
                    path.append(new_pos)
                    return path
            direction = conveyor['direction']
            current_pos = current_pos.add(direction)
        else:
            current_pos = conveyor['bridge_target']
        if current_pos in path:  # Detect loops
            break
    return path

def is_split_path(player, start_pos):
    path = []
    current_pos = start_pos
    while True:
        path.append(current_pos)
        conveyors = player.map.get_conveyors_to_here(current_pos)
        if len(conveyors) > 1:
            return False
        if len(conveyors) == 0:
            break
        current_pos = conveyors[0]
        if current_pos in path:  # Detect loops
            return False
    return len(player.map.get_splitters_to_here(current_pos)) > 0

'''
get_scale_percent()
float
Return this team’s current cost scale as a percentage (100.0 = base cost).
'''

def can_afford_unit(ct: Controller, unit_type: EntityType) -> bool:
    """Check if the player can afford to build a unit of the given type."""
    if unit_type == EntityType.BUILDER_BOT:
        return ct.get_global_resources()[0] >= GameConstants.BUILDER_BOT_BASE_COST[0] * (1 + ct.get_scale_percent() / 100)
    elif unit_type == EntityType.HARVESTER:
        if ct.get_current_round() < 50:
            return ct.get_global_resources()[0] >= (GameConstants.HARVESTER_BASE_COST[0] + 10) * (0.5 + ct.get_scale_percent() / 100)
        return ct.get_global_resources()[0] >= (GameConstants.HARVESTER_BASE_COST[0] + 20) * (0.5 + ct.get_scale_percent() / 100)
    elif unit_type == EntityType.SENTINEL:
        return ct.get_global_resources()[0] >= (GameConstants.SENTINEL_BASE_COST[0]) * (0.5 + ct.get_scale_percent() / 100)
    elif unit_type == EntityType.LAUNCHER:
        return ct.get_global_resources()[0] >= (GameConstants.LAUNCHER_BASE_COST[0] + 15) * (0.5 + ct.get_scale_percent() / 100)
    elif unit_type == EntityType.CONVEYOR:
        return ct.get_global_resources()[0] >= GameConstants.CONVEYOR_BASE_COST[0] * (ct.get_scale_percent() / 100)
    elif unit_type == EntityType.BRIDGE:
        return ct.get_global_resources()[0] >= GameConstants.BRIDGE_BASE_COST[0] * (ct.get_scale_percent() / 100)
    elif unit_type == EntityType.SPLITTER:
        return ct.get_global_resources()[0] >= GameConstants.SPLITTER_BASE_COST[0] * (ct.get_scale_percent() / 100)
    elif unit_type == EntityType.BARRIER:
        return ct.get_global_resources()[0] >= GameConstants.BARRIER_BASE_COST[0] * (ct.get_scale_percent() / 100)
    elif unit_type == EntityType.GUNNER:
        return ct.get_global_resources()[0] >= GameConstants.GUNNER_BASE_COST[0] * (ct.get_scale_percent() / 100)
    elif unit_type == EntityType.FOUNDRY:
        return ct.get_global_resources()[0] >= GameConstants.FOUNDRY_BASE_COST[0] * (ct.get_scale_percent() / 100)
    else:
        print("TODO: not yet implemented for type", unit_type)
    return False

def orthogonal_positions(position):
    return [position.add(d) for d in ORTHOGONAL_DIRECTIONS]

def adjacent_positions(position):
    return [position.add(d) for d in DIRECTIONS]

def closest_building(position, buildings):
    if len(buildings) == 0: return None
    return min(buildings, key=lambda b: position.distance_squared(b['position']))

def try_heal(player, position, money_efficient=True):
    if money_efficient:
        b = player.map.get_building_info(player.heal_target['position'])
        if not b or b['hp'] > b['max_hp'] - 4:
            return False
    if player.ct.can_heal(position):
        player.ct.heal(position)
        return True
    return False

def closest(target, positions):
    if len(positions) == 0: return None
    return min(positions, key=lambda p: target.distance_squared(p))

def get_enemy_core_pos(player):
    if not player.core_pos: return None
    width = player.map.width
    height = player.map.height
    
    symmetries = player.map.symmetry_calculator.possible_symmetries
    
    # Priority: Rotational > others
    if Symmetry.ROTATIONAL in symmetries:
        return Position(width - 1 - player.core_pos.x, height - 1 - player.core_pos.y)
    elif Symmetry.HORIZONTAL in symmetries:
        return Position(width - 1 - player.core_pos.x, player.core_pos.y)
    elif Symmetry.VERTICAL in symmetries:
        return Position(player.core_pos.x, height - 1 - player.core_pos.y)
    
    return Position(width - 1 - player.core_pos.x, height - 1 - player.core_pos.y)

def move_anywhere(player):
    shuffled_directions = DIRECTIONS[:]
    random.shuffle(shuffled_directions)
    for direction in shuffled_directions:
        if player.ct.can_move(direction):
            player.ct.move(direction)
            return True
    return False

def get_nearby_builders(ct):
    return [b for b in ct.get_nearby_units() if ct.get_entity_type(b) is EntityType.BUILDER_BOT]

def get_adjacent_builders(ct):
    return [b for b in ct.get_nearby_units(2) if ct.get_entity_type(b) is EntityType.BUILDER_BOT]