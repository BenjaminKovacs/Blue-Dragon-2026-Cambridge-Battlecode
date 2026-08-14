import random
from cambc import *

from cambc import Controller, Direction, EntityType, Environment, Position

# non-centre directions
DIRECTIONS = [d for d in Direction if d != Direction.CENTRE]
ORTHOGONAL_DIRECTIONS = [Direction.NORTH, Direction.SOUTH, Direction.EAST, Direction.WEST]

def run(ct: Controller, num_spawned: int,player) -> int:
    player.resources_collected_recently.pop(-1)
    player.resources_collected_recently.insert(0,0)
    pos=ct.get_position()
    resources=0
    for direction in DIRECTIONS:
        core_tile=pos.add(direction)
        for cd in ORTHOGONAL_DIRECTIONS:
            possible_conveyor=core_tile.add(cd)
            if player.map.on_the_map(possible_conveyor) and player.ct.is_in_vision(possible_conveyor):
                build_id=ct.get_tile_building_id(possible_conveyor)

                if(build_id is not None and 
                ct.get_entity_type(build_id)==EntityType.CONVEYOR and 
                ct.get_direction(build_id).opposite() ==cd and
                ct.get_stored_resource(build_id)==ResourceType.TITANIUM ):
                    resources+=1


    player.resources_collected_recently[0]=resources
    print("Resources Gathers",player.resources_collected_recently)
    approximate_number_harvester=sum(player.resources_collected_recently)/len(player.resources_collected_recently)*4
    print("Approximate number of harvesters:", approximate_number_harvester)

    if (num_spawned < 4 or
        (ct.get_current_round()>20 and approximate_number_harvester>(num_spawned - 5) and num_spawned<6) or
        (ct.get_current_round()>40 and approximate_number_harvester>1.2*(num_spawned - 5) and num_spawned<15) or

        (ct.get_current_round()>40 and ct.get_global_resources()[0]>(50+8*10*(ct.get_scale_percent()/100))) #Fix later
        ):
        # if we haven't spawned 3 builder bots yet, try to spawn one on a random tile
        d = random.choice(DIRECTIONS)
        
        for _ in range(8):
            spawn_pos = ct.get_position().add(d)
            if ct.can_spawn(spawn_pos):
                ct.spawn_builder(spawn_pos)
                num_spawned += 1
                break
            d = d.rotate_right()
        #try to build in center if we can't build elsewhere
        if(ct.can_spawn(ct.get_position())):
            ct.spawn_builder(ct.get_position())
            num_spawned += 1
    
    elif(ct.get_current_round()>100 and (ct.get_max_hp()-ct.get_hp()>30) and ct.get_global_resources()[0]>(20+35*(ct.get_scale_percent()/100))
        ):
        if(ct.can_spawn(ct.get_position())):
            ct.spawn_builder(ct.get_position())
            num_spawned += 1
    #Might want to convert if we have a bunch of axionite but low on titanium to give a titanium injects
    titanium,axionite=ct.get_global_resources()
    if(ct.get_current_round()<600):
        #just keep 41 axionite in reserve in case the flow gets cut off but it lets us win
        if(axionite>41 and titanium<2000):
            ct.convert(axionite-41)



    return num_spawned

    
