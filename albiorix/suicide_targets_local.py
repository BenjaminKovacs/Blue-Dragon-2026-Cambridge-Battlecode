
import random

from cambc import Controller, Direction, EntityType, Environment, Position
from terrain.map import Map
from exploration.exploration import explore
from util import try_move_with_road, get_direction

DIRECTIONS = [d for d in Direction if d != Direction.CENTRE]
priority_buildings={
    EntityType.GUNNER:10,EntityType.SENTINEL:10,EntityType.BREACH:10,
                                        EntityType.CORE:50, EntityType.FOUNDRY:0,
    EntityType.BRIDGE:30,EntityType.SPLITTER:39,EntityType.CONVEYOR:10
                
}
def get_priority_target(ent_type):
    if(ent_type in priority_buildings):
        return priority_buildings[ent_type]
    else:
        return 0 

def simple_suicide_target_choice(ct: Controller, map_instance: Map, player) -> Position:
    buildings=ct.get_nearby_buildings()

    enemy_conveyers=[]
    enemy_destinations={}
    for b in buildings:
        if(ct.getTeam(b)!=ct.getTeam()):
            ent_type=ct.get_entity_type(b)
            if(ent_type in [EntityType.GUNNER,EntityType.SENTINEL,EntityType.BREACH,
                                        EntityType.CORE, #FOUNDRY 
                                        ]):
                pos=ct.get_position(b)
                if(ent_type==EntityType.CORE):
                    for D in DIRECTIONS:
                        enemy_destinations[pos.add(D)]=(b,ent_type)
                else:
                        enemy_destinations[pos]=(b,ent_type)


            if(ent_type in [EntityType.BRIDGE]):
                bridge_target=ct.get_bridge_target(b)
                enemy_conveyers.append((b,ent_type,ct.get_position(b),bridge_target))
            if(ent_type in [EntityType.CONVEYOR]):
                enemy_conveyers.append((b,ent_type,ct.get_position(b),ct.get_position(b).add(ct.get_direction(b))))
            if(ent_type in [EntityType.SPLITTER]):
                pos=ct.get_position(b)
                D=ct.get_direction(b)
                enemy_conveyers.append((b,ent_type,pos,pos.add(D)))
                enemy_conveyers.append((b,ent_type,pos,pos.add(D.rotate_right().rotate_right())))
                enemy_conveyers.append((b,ent_type,pos,pos.add(D.rotate_left().rotate_left())))
    best_target= None
    best_score=-10
    for conv in enemy_conveyers:
        if(enemy_conveyers[3] in enemy_destinations):
            dest=enemy_destinations[enemy_conveyers[3]]
            score=get_priority_target(dest[1])+get_priority_target(conv[1])-conv[2].distance_squared(ct.get_position())
            if(score>best_score):
                best_score=score
                best_target=conv[2]
    return best_target
            