import random

from cambc import Controller, Direction, EntityType, Environment, Position
from terrain.map import Map
from exploration.exploration import explore
from util import try_move_with_road, get_direction, distance_squared, get_adjacent_builders

DIRECTIONS = [d for d in Direction if d != Direction.CENTRE]
ORTHOGONAL_DIRECTIONS = [Direction.NORTH, Direction.SOUTH, Direction.EAST, Direction.WEST]

def run_launcher(ct: Controller, map_instance: Map, player) -> None:
    #First thing is to make a list of jail cells we can throw units into
    #A jail cell must be entirely surround by solid tiles
    #These include map edges, walls, harvesters, guns, launchers 
    #it cannot have a jail cell
    map=player.map
    my_pos=ct.get_position()
    nearby_tiles=ct.get_nearby_tiles()
    valid_jails=[] #locations we can launch to that will jail the unit
    enemy_harvester_adjacent=[] #list of tiles we can launch to adjacent to an enemy harvester
    my_team=ct.get_team()
    best_enemy_throw_tile = None
    best_enemy_throw_value = 0
    for pos in nearby_tiles:

        is_valid_jail=True
        build_id=ct.get_tile_building_id(pos)
        #don't put enemy onto our bridge, make sure that we can drop them there (is passable, no bulder on tile)
        # if(# ct.is_in_vision(pos) and  # must be in vision
        #     map.is_walkable(pos)
        #     and
        #     (ct.get_tile_builder_bot_id(pos) is None) and
        #         ((build_id is None) or (ct.get_entity_type(build_id)!=EntityType.BRIDGE and ct.get_team(build_id)!=ct.get_team()))
        #         ):
        #     for dir in DIRECTIONS:                    
        #         new_pos=pos.add(dir)
        #         if((not ct.is_in_vision(new_pos)) or map.is_passable(new_pos)):
        #             is_valid_jail=False
        #             break
        #         else:
        #             pass
        #     if(is_valid_jail):
        #         valid_jails.append(pos)
        if map.is_walkable(pos) and ct.get_tile_builder_bot_id(pos) is None and (map.buildings[pos.x][pos.y] is None or map.buildings[pos.x][pos.y]['team'] != ct.get_team()):
            enemy_throw_value = distance_squared(my_pos, pos)
            if enemy_throw_value > best_enemy_throw_value:
                best_enemy_throw_value = enemy_throw_value
                best_enemy_throw_tile = pos


        if(ct.get_entity_type(build_id)==EntityType.HARVESTER and ct.get_team(build_id)!=my_team):
            for direction in ORTHOGONAL_DIRECTIONS:
                pos2=pos.add(direction)
                build_id2=ct.get_tile_building_id(pos)
                if(map.is_walkable(pos2) and build_id2 is not None and ct.get_team(build_id2)!=my_team and ct.get_tile_builder_bot_id(pos2) is None):
                    enemy_harvester_adjacent.append(pos2)
                elif  build_id2 is None:
                    for direction in DIRECTIONS:
                        pos2=pos.add(direction)
                        if(ct.is_in_vision(pos2) and map.is_walkable(pos2) and ct.get_tile_builder_bot_id(pos2) is None):
                            enemy_harvester_adjacent.append(pos2)
                    break
                
                
    print(enemy_harvester_adjacent)
    nearby_units = get_adjacent_builders(player.ct)
    best_target=None
    best_destination=None
    best_score=0
    if(len(valid_jails)>0):
        next_valid_jail=valid_jails[0]
    else:
        next_valid_jail=None
    if(len(enemy_harvester_adjacent)>0):
        next_enemy_harvest_pos=enemy_harvester_adjacent[0]
    else:
        next_enemy_harvest_pos=None
    for unit in nearby_units:
        score=-1
        destination=None
        
        if(ct.get_entity_type(unit)!=EntityType.BUILDER_BOT):
            continue
        #Only builder bots can we throw
        if(my_team!=ct.get_team(unit) and (next_valid_jail is not None)):
            score += 10
            destination=next_valid_jail
        elif(my_team==ct.get_team(unit) and (next_enemy_harvest_pos is not None)
             and (unit>=5 or ct.get_current_round()>100) #please stop throwing our econ bots
             ):
            score += 8.1
            destination=next_enemy_harvest_pos
        elif(my_team!=ct.get_team(unit) and (best_enemy_throw_tile is not None)):
            score += best_enemy_throw_value
            destination = best_enemy_throw_tile


        if(score>best_score):
            best_target=ct.get_position(unit)
            best_destination=destination
            best_score=score
    print(best_destination)
    if(best_score>0 and (best_target is not None) and ct.can_launch(best_target,best_destination)):
        ct.launch(best_target,best_destination)