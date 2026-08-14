import random

from cambc import Controller, Direction, EntityType, Environment, Position
from terrain.map import Map
from exploration.exploration import explore
from util import try_move_with_road, get_direction

ORTHOGONAL_DIRECTIONS = [Direction.NORTH, Direction.SOUTH, Direction.EAST, Direction.WEST]

def run_sentry(ct: Controller, map_instance: Map, player) -> None:

    if(ct.get_current_round()>100 and ct.get_current_round()%10==0):
        roleRandomNumber=random.random()
        if(roleRandomNumber>.5):
            player.targetBuilder=1
        else:
            player.targetBuilder=0

    #All we can really decide is if and who to shoot
    if ct.get_action_cooldown() > 0:
        return

    my_team = ct.get_team()

    best_target = None
    best_score = -1

    myPos=ct.get_position()
    myDir=ct.get_direction()
    myID=ct.get_id()


    k=0
   
    
    possibleTargetTiles=ct.get_attackable_tiles()
    for tile in possibleTargetTiles:
        
        bbid=ct.get_tile_builder_bot_id(tile)
        buildid=ct.get_tile_building_id(tile) #presumably this includes non center core tiles?
        if(bbid is not None):
            entity=bbid
        elif(buildid is not None):
            entity=buildid
        else:
            continue
        enemyID=entity
        enemyPosition=tile
        enemyHP=ct.get_hp(enemyID)
        enemyType=ct.get_entity_type(enemyID)
        
        #Already checked before
        if ct.get_team(entity) == my_team:
            continue

        if enemyType == EntityType.MARKER:
            continue

        
        hp = enemyHP
        # Higher priority + lower HP = better
        #builder bots --hp<=20
        #full health builder bot(if second shooter)
        #enemy buildings (if can kill higher priority)
        entType=enemyType
        position=enemyPosition
       
        
        score=-1
        #shoot cores
        """
        one_step_closer = enemyPosition.add(enemyPosition.direction_to(myPos))
        if enemyType == EntityType.CORE and ct.can_fire(one_step_closer):
            # TODO: target builders on the enemy core and don't shoot it if there is a better target
            enemyPosition=one_step_closer
            score+=3
        """
        if not ct.can_fire(enemyPosition):
            continue


        if(entType==EntityType.BUILDER_BOT):
            if(hp<=18):
                score+=50 #always kill if we can
            elif(hp<37):
                score+=11
            else:
                score+=2+8*player.targetBuilder #p
        else:
            if(enemyType==EntityType.CONVEYOR or enemyType==EntityType.SPLITTER):
                outloc=position.add(ct.get_direction(enemyID))
                if(not ct.is_in_vision(outloc)):
                    #shoot the edges of my vision
                    score+=4
                else:
                    output_tile=ct.get_tile_building_id(outloc)
                    if(output_tile is None):
                        score+=5
                    else:
                        btype=ct.get_entity_type(output_tile)
                        if(ct.get_team(output_tile)!=my_team and 
                            (btype==EntityType.GUNNER or btype==EntityType.CORE or btype==EntityType.SENTINEL)): #TODO: MAKE IT SO THAT THE CORE ACTUALLY GETS PRIORITIZED
                                score+=10
                        elif(ct.get_team(output_tile)==my_team and 
                            (btype==EntityType.GUNNER or btype==EntityType.CORE or btype==EntityType.SENTINEL)):
                            score-=30
                        else:
                            score+=7
                if(hp<=18):
                    score+=5
            elif(enemyType==EntityType.BRIDGE):
                score+=9
                if(hp<=18):
                    score+=6
            elif(enemyType==EntityType.HARVESTER):
                score=-1
            elif(enemyType==EntityType.SENTINEL or enemyType==EntityType.GUNNER ):
                for direc in ORTHOGONAL_DIRECTIONS:
                    adTile=position.add(direc)
                    if(player.map.on_the_map(adTile) and ct.is_in_vision(adTile)):
                        bid_ad=ct.get_tile_building_id(adTile)
                        if((bid_ad is not None) and ct.get_entity_type(bid_ad)==EntityType.HARVESTER):
                            score+=17
                            break
                score+=9
                if(hp<=18):
                    score+=10
            elif(enemyType==EntityType.LAUNCHER):
                score+=7
               
            elif(enemyType==EntityType.CORE):
                score+=3
            else:
                score+=1

            builder_id=ct.get_tile_builder_bot_id(enemyPosition)
            if((builder_id is not None) and ct.get_team(builder_id)==my_team):
                score-=15 #Don't shoot friend
    
        #Might be a very bad idea
        if(hp<=18):
            score+=2

        if score > best_score:
            best_score = score
            best_target = enemyPosition

    if best_target is not None:
        ct.fire(best_target)
     
    