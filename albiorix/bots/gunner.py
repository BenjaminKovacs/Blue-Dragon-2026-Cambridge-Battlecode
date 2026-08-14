import random

from cambc import Controller, Direction, EntityType, Environment, Position
from terrain.map import Map
from exploration.exploration import explore
from util import get_conveyors_leading_here, get_nearby_builders
from config import *

GUNNER_SELF_DESTRUCT_TIME = 10

def get_gunner_target(player, direction, ignore_builders=False, my_pos=None):
    if not my_pos:
        my_pos = player.ct.get_position()
    target = my_pos.add(direction)
    while player.map.on_the_map(target) and player.ct.is_in_vision(target):
        if (not ignore_builders) and player.ct.get_tile_builder_bot_id(target):
            return target
        building = player.ct.get_tile_building_id(target)
        if building:
            building_type = player.ct.get_entity_type(building)
            if building_type != EntityType.MARKER:
                return target
        if player.map.get_terrain(target) == Environment.WALL:
            return None
        target = target.add(direction)
    return None

def run_gunner(ct: Controller, map_instance: Map, player) -> None:
    #All we can really decide is if and who to shoot
    dir=ct.get_direction()
    myPos=ct.get_position()
    pos_to_shoot = get_gunner_target(player, dir)
    building = ct.get_tile_building_id(pos_to_shoot) if pos_to_shoot else None
    builder = ct.get_tile_builder_bot_id(pos_to_shoot) if pos_to_shoot else None

    #When do we actually want to do this? We can't outdamage a heal without axionite?
    #But maybe assume whenever we build a turret we want to kill
    if (building and ct.get_team(building) != ct.get_team()) or (builder and ct.get_team(builder) != ct.get_team()):
        player.gunner_self_destruct_timer = 0
    elif player.map.nearest_enemy_turret:
        d = myPos.direction_to(player.map.nearest_enemy_turret)
        target = get_gunner_target(player, d, True)
        should_rotate = False
        while target:
            b = player.map.get_building_info(target)
            if (not b) or (b['team'] == ct.get_team()) or (b['type'] == EntityType.HARVESTER):
                break
            if b['type'] in (TURRETS + [EntityType.LAUNCHER]):
                should_rotate = True
            target = get_gunner_target(player, d, True, target)
        
        if should_rotate:
            if ct.can_rotate(d):
                ct.rotate(d)
                pos_to_shoot = get_gunner_target(player, ct.get_direction())
                building = ct.get_tile_building_id(pos_to_shoot) if pos_to_shoot else None
                builder = ct.get_tile_builder_bot_id(pos_to_shoot) if pos_to_shoot else None
        else:
            player.gunner_self_destruct_timer += 1
    else:
        player.gunner_self_destruct_timer += 1

    if(building and ct.can_fire(pos_to_shoot) and ct.get_team(building) != ct.get_team() and ct.get_entity_type(building) != EntityType.HARVESTER):
        ct.fire(pos_to_shoot)
    elif(builder and ct.can_fire(ct.get_position(builder)) and ct.get_team(builder) != ct.get_team()):
        ct.fire(ct.get_position(builder))


    conveyors = get_conveyors_leading_here(player, player.ct.get_position())
    on_friendly_line = False
    for c in conveyors:
        b = player.map.get_building_info(c)
        if b['team'] == ct.get_team():
            on_friendly_line = True
            break

    if not on_friendly_line:
        player.gunner_self_destruct_timer = 0

    if player.gunner_self_destruct_timer > GUNNER_SELF_DESTRUCT_TIME:
        nearby_builders = get_nearby_builders(player.ct)
        nearby_friendly_builder = False
        for builder_id in nearby_builders:
            if ct.get_team(builder_id) == ct.get_team():
                nearby_friendly_builder = True
            else:
                return
        if nearby_friendly_builder:
            ct.self_destruct()