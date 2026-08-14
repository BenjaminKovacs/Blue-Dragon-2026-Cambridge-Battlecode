import random

from cambc import *
from builder_actions.repair import *
from config import *
from builder_actions.rush_attack import *
from builder_actions.harvest_ore import *
from builder_actions.build_conveyors import *
from exploration.exploration import explore
from exploration.initial_exploration import initial_explore

from util import *
from builder_actions.heal import *
from builder_actions.patrol import run_patrol
from builder_actions.heal_builders import heal_builders
from builder_actions.remove_enemy_sentinels import build_adjacent_gunners
from builder_actions.construct_foundry import run_construct_foundry

def block_gunners_with_walls(player):
    start_time = player.ct.get_cpu_time_elapsed()
    nearby_positions = player.ct.get_nearby_tiles(8)
    my_pos = player.ct.get_position()
    for pos in nearby_positions:
        if distance_squared(pos, player.core_pos) <= 8:
            move_required = distance_squared(pos, my_pos) > 2
            if move_required and not player.ct.can_move(my_pos.direction_to(pos)):
                continue
            for d in DIRECTIONS:
                new_pos = pos.add(d)
                b = player.map.get_building_info(new_pos)
                if b and b['type'] == EntityType.GUNNER and b['team'] != player.ct.get_team() and distance_squared(pos.add(d.opposite()), player.core_pos) <= 2:
                    if move_required:
                        player.ct.move(my_pos.direction_to(pos))
                    if try_build_barrier(player, pos) or try_build_road(player, pos) or move_required:
                        return True
    end_time = player.ct.get_cpu_time_elapsed()
    print("block_gunners_with_walls run time:", end_time - start_time)
    return False

def destroy_leads_to_enemy(player):
    nearby_positions = player.ct.get_nearby_tiles(2)
    for pos in nearby_positions:
        if player.map.leads_to_enemy_building(pos) and player.ct.can_destroy(pos):
            player.ct.destroy(pos)
            if player.ct.can_build_road(pos):
                player.ct.build_road(pos)
                return True
    return False

def replace_harvester_adjacent_tiles(player):
    nearby_positions = player.ct.get_nearby_tiles(2)
    for pos in nearby_positions:
        if pos in player.map.adjacent_to_harvester and not player.map.get_building_info(pos) and player.map.get_terrain(pos) != Environment.WALL:
            if is_loose_end(player, pos):
                build_conveyor_to_core(player, pos)
                return True
            elif player.ct.can_build_road(pos):
                player.ct.build_road(pos)
                return True
    return False

def try_build_sentinel_with_destroy(player, build_pos, direction) -> bool:
    ct = player.ct
    if not can_afford_unit(ct, EntityType.SENTINEL):
        return False
    b = player.map.get_building_info(build_pos)
    if b and b['type'] == EntityType.ROAD:
        if ct.can_destroy(build_pos):
            ct.destroy(build_pos)
    if ct.can_build_sentinel(build_pos, direction):
        ct.build_sentinel(build_pos, direction)
        return True
    return False

def forced_resume_conveyors(player):
    return player.bridge_target and not player.ct.in_vision(player.bridge_target)

def run(ct: Controller, map_instance, player) -> None:
    if(player.myRole is None):
        #FIrst turn we need to set an initial role
        #rush_attacker, economy
        #conveyer attacker,
        #defender?
        role_number = random.random()
        if(ct.get_current_round()>10):
            if(role_number < 0.3 or (ct.get_current_round() < 200 and role_number < 0.6) or (ct.get_current_round() < 20 and role_number < 1)):
                player.myRole="patrol"
            elif(role_number < 0.7):
                player.myRole="rush_attacker"
            else:
                player.myRole="economy"
        else:
            # bot doesn't run on turn it's built, 
            # so if it's the first unit built it will see the core, itself, and the builder built the turn after it
            build_position = ct.get_unit_count() - 3
            if(build_position < 1):
                player.myRole="economy" 
                player.initial_patrol_bot = True # TODO: rename variable
                player.initial_explorer=True
                player.initial_explore_direction=0
            elif(build_position < 2):
                player.myRole="economy"
                player.initial_explorer=True
                player.initial_explore_direction=1
            elif(build_position < 3):
                player.myRole="patrol"
                player.initial_patrol_bot = True
            elif(build_position < 6):
                player.myRole="rush_attacker"
            else:
                player.myRole="economy"
    if(ct.get_current_round()>25):
        player.initial_explorer=False

    
    roleRandomNumber=random.random()
    if(player.turnsSinceRoleLastSet > 150 and ct.get_current_round()>400 and 
        (not player.initial_patrol_bot)):
        player.turnsSinceRoleLastSet=0
        if((roleRandomNumber> .4 and player.myRole!="patrol") 
           or roleRandomNumber>.9
            ):
            player.myRole="rush_attacker"
            player.turnsSinceRoleLastSet = -300

        elif(roleRandomNumber>1000 and False):
            #NO ATTACKERS FOR NOW
            player.myRole="attacker"
        elif(((roleRandomNumber>.35 and player.myRole=="economy") and ct.get_current_round()>100)
             or (player.myRole=="patrol" and roleRandomNumber>.1)
             ):
            player.myRole="patrol"

        else:
            player.myRole="economy"
            
    player.turnsSinceRoleLastSet+=1

    if player.myRole == "rush_attacker":
        if build_adjacent_gunners(player):
            print("attacker built a gunner to destroy enemy sentinel")
        elif run_heal(player):
            print("trying to heal", player.heal_target)
        elif heal_builders(player):
            print("trying to heal builders")
        else:
            run_attack(player)
        return

    # Builder bot logic: builds a harvester on adjacent ore tile, then prioritizes building conveyor to core, then seeks resources or explores
    
    start_time = player.ct.get_cpu_time_elapsed()
    # Check if we are on a loose end or leading conveyor
    my_pos = ct.get_position()
    if is_loose_end(player, my_pos):
        player.loose_end_target = my_pos
    else:
        b_here = map_instance.get_building_info(my_pos)
        if b_here and b_here['type'] in [EntityType.CONVEYOR, EntityType.ARMOURED_CONVEYOR]:
            d = b_here['direction']
            target = my_pos.add(d)
            if is_loose_end(player, target):
                player.loose_end_target = target
        else:
            for d in DIRECTIONS:
                n = my_pos.add(d)
                if is_loose_end(player, n):
                    player.loose_end_target = n
                    break
    if player.bridge_target:
        player.loose_end_target = player.bridge_target
    elif player.loose_end_target is None or not is_loose_end(player, player.loose_end_target):
        player.loose_end_target = check_for_loose_ends(player)
    
    end_time = player.ct.get_cpu_time_elapsed()
    print("loose ends check run time:", end_time - start_time)

    start_time = player.ct.get_cpu_time_elapsed()
    # Check if we have a valid target ore, or find one
    potential_ore_target = get_best_ore_target(player)
    if not player.target_ore or not is_safe_ore(player, player.target_ore) or (potential_ore_target and distance_squared(potential_ore_target, my_pos) <= 2 and distance_squared(player.target_ore, my_pos) > 2):
        player.target_ore = potential_ore_target

    end_time = player.ct.get_cpu_time_elapsed()
    print("ore targetting run time:", end_time - start_time)

    # Prioritize building conveyor to core if active
    if block_gunners_with_walls(player):
        print("blocked enemy gunner with wall")
    elif build_adjacent_gunners(player):
        print("built a gunner to destroy enemy sentinel")
    elif destroy_leads_to_enemy(player):
        print("replaced conveyor leading to enemy with road")
    elif replace_harvester_adjacent_tiles(player):
        print("replaced broken tile next to harvester")
    elif player.not_loose_path_start and distance_squared(my_pos, player.not_loose_path_start) <= 2 and build_conveyor_to_core(player, player.not_loose_path_start):
        print("building conveyor to core from adjacent not_loose_path_start")
    elif player.loose_end_target and distance_squared(my_pos, player.loose_end_target) <= 2 and build_conveyor_to_core(player, player.loose_end_target):
        print("building conveyor to core from adjacent loose_end_target")
    elif run_heal(player):
        print("trying to heal", player.heal_target)
    elif heal_builders(player):
        print("trying to heal builders")
    elif player.not_loose_path_start and build_conveyor_to_core(player, player.not_loose_path_start):
       print("building conveyor to core from non-adjacent not_loose_path_start")
    elif player.loose_end_target and build_conveyor_to_core(player, player.loose_end_target):
        print("building conveyor to core from non-adjacent loose_end_target")
    elif player.should_produce_axionite and run_construct_foundry(player):
        print("trying to build a foundry")
    elif player.myRole == "patrol" and not can_afford_unit(player.ct, EntityType.HARVESTER) and run_patrol(player): #  and len(player.map.adjacent_to_harvester) > 0
        print("used patrol")
    elif ct.get_current_round() < HARVESTER_STOP_ROUND and player.target_ore and process_ore_construction(player, player.target_ore):
        print("used process_ore_construction")
    elif player.myRole == "patrol" and len(player.map.adjacent_to_harvester) > 0 and run_patrol(player):
        print("used patrol")
    # elif player.attack_path or (player.myRole == "attack_builder" and player.ct.get_current_round() > 100):
    #     run_attack(player)
    elif(player.myRole == "attacker" and (player.enemy_core_pos is None)):
        attackExplore(player) #try to find the enemy base
    elif(player.myRole=="attacker" ):
        #we know where the enemy core is
        #attack. 
        pass
    elif(player.suicidal and random.random()<.2 and ct.get_team(ct.get_tile_building_id(ct.get_position()))!=ct.get_team() and ct.get_current_round()>100) and ct.can_fire(ct.get_position()):
        #Blow up
        ct.fire(ct.get_position())
    elif(ct.get_global_resources()[0]>100):
        if(player.initial_explorer and player.initial_explore_direction!=None):
            initial_explore(player,player.initial_explore_direction)

        else:
            explore(player)
    else:
        scramble_direction=DIRECTIONS
        random.shuffle(scramble_direction)
        mypos=ct.get_position()
        moved=False
        for dir in scramble_direction:
            if(try_move(ct, mypos.add(dir))):
                moved=True
                break
        if(not moved):
            for dir in scramble_direction:
                if(try_move_with_road(ct, mypos.add(dir),map_instance)):
                    break
    #End Turn   
    #No reason not to heal if we aren't using actions for anything else
    nearbyUnits1=ct.get_nearby_units()
    nearbyUnits=[]
    mypos=ct.get_position()
    for unit in nearbyUnits1:
        if(ct.get_position(unit).distance_squared(mypos)<=2):
            nearbyUnits.append(unit)
        elif(ct.get_entity_type(unit)==EntityType.CORE):
                nearbyUnits.append(unit)

    currentPosition=ct.get_position()
    if (ct.can_heal(currentPosition) and ct.get_hp()<ct.get_max_hp()):
        ct.heal(currentPosition)
    for unit in nearbyUnits:
        if(ct.get_entity_type(unit)==EntityType.CORE):
            centerloc=ct.get_position(unit)
            for dir in DIRECTIONS:
                heal_loc=centerloc.add(dir)
                if(ct.can_heal(heal_loc) and 
                    ct.get_team(unit)==ct.get_team() and 
                        ct.get_hp(unit)<ct.get_max_hp(unit)
                    ):
                    ct.heal(heal_loc)
    
        if(ct.can_heal(ct.get_position(unit)) and 
           ct.get_team(unit)==ct.get_team() and 
            ct.get_hp(unit)<ct.get_max_hp(unit)
           ):
            ct.heal(ct.get_position(unit))
