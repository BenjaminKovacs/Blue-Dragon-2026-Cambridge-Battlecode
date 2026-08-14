from util import *
from cambc import *
from pathing.astar_conveyor import unreachable_locations
from pathing.astar_axionite import unreachable_locations as axionite_unreachable_locations

def is_loose_end(player, pos):
    map_instance = player.map
    ct = player.ct
    if not map_instance.on_the_map(pos): return False
    
    b = map_instance.buildings[pos.x][pos.y]
    if b is None:
        terrain = map_instance.terrain[pos.x][pos.y]
        if terrain == Environment.WALL:
            return False

    elif b['type'] is EntityType.CONVEYOR and b['team'] is ct.get_team():
        test_pos = pos.add(b['direction'])
        test_building = player.map.get_building_info(test_pos)
        if test_building is None:
            return False
        elif test_building['type'] is EntityType.CONVEYOR:
            if pos != test_pos.add(test_building['direction']):
                return False
        elif test_building['type'] is not EntityType.HARVESTER:
            return False
        
    elif b['type'] != EntityType.ROAD or b['team'] != ct.get_team():
        return False
    
    path_pair = (pos, player.core_pos)
    if (path_pair in unreachable_locations) and ((player.ct.get_current_round() - unreachable_locations[path_pair]) < UNREACHABLE_CONVEYOR_MEMORY_ROUNDS):
        return False

    if (path_pair in axionite_unreachable_locations) and ((player.ct.get_current_round() - axionite_unreachable_locations[path_pair]) < UNREACHABLE_CONVEYOR_MEMORY_ROUNDS):
        return False

    terrain = map_instance.terrain[pos.x][pos.y]
    # if terrain != Environment.EMPTY:
    #     conveyors = player.map.conveyors_to_here[pos.x][pos.y]
    #     for c in conveyors:
    #         if player.map.conveyors_to_here[c.x][c.y] or (c in player.map.adjacent_to_unconnected_harvester):
    #             return True
    if terrain != Environment.EMPTY:
        if player.map.conveyors_to_here[pos.x][pos.y] and (player.map.is_titanium_conveyor[pos.x][pos.y] or player.map.is_axionite_conveyor[pos.x][pos.y]):
            for c in player.map.conveyors_to_here[pos.x][pos.y]:
                if player.map.is_titanium_conveyor[c.x][c.y] or player.map.is_axionite_conveyor[c.x][c.y]:
                    return True

    elif player.map.conveyors_to_here[pos.x][pos.y]:
        for c in player.map.conveyors_to_here[pos.x][pos.y]:
            if player.map.is_titanium_conveyor[c.x][c.y] or player.map.is_axionite_conveyor[c.x][c.y] or player.map.is_buildable(c):
                return True

    return pos in player.map.adjacent_to_unconnected_harvester

def is_valid_loose_end_target(player, pos):
    ct = player.ct
    if not is_loose_end(player, pos): return False
    
    my_id = ct.get_id()
    if ct.is_in_vision(pos):
        bid = ct.get_tile_builder_bot_id(pos)
        friendly = ct.get_team(bid) == ct.get_team()
        if bid is not None and bid != my_id and friendly:
            return False
        
    leading = get_conveyors_leading_here(player, pos)
    for lpos in leading:
        if not ct.is_in_vision(lpos):
            continue
        lbid = ct.get_tile_builder_bot_id(lpos)
        friendly = ct.get_team(lbid) == ct.get_team()
        if lbid is not None and lbid != my_id and friendly:
            return False
    return True

# checks for conveyors that need to be repaired
def check_for_loose_ends(player):
    ct = player.ct
    vision_radius = ct.get_vision_radius_sq()
    nearby = ct.get_nearby_tiles(vision_radius)
    
    candidates = []
    for pos in nearby:
        if is_valid_loose_end_target(player, pos):
            candidates.append(pos)
            
    if not candidates:
        return None
    
    my_pos = ct.get_position()
    return closest(my_pos, candidates)