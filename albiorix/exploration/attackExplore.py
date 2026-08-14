import random
import math
import sys
from cambc import Controller, Direction, Position
from pathing.pathing import find_path
from terrain.map import Map
from util import *



def attackExplore(player) -> None:
   
        
    ct = player.ct
    map_instance = player.map

    core_offset_x=(map_instance.width-1)-player.core_pos.x
    core_offset_y=(map_instance.height-1)-player.core_pos.y

    player.attackExploreVariables["turns_since_last_choice"]+=1
    if (player.attackExploreVariables["turns_since_last_choice"] > 20 or player.attackExploreVariables["nextLoc"] is None or 
            ((ct.get_position().x - player.attackExploreVariables["nextLoc"].x)**2 + (ct.get_position().y - player.attackExploreVariables["nextLoc"].y)**2) < 9 or 
            map_instance.get_cost(player.attackExploreVariables["nextLoc"]) == float('inf')):
        player.attackExploreVariables["currentSymmetryExploring"]=random.choice(player.possibleSymmetries)
        if(player.attackExploreVariables["currentSymmetryExploring"]=="rotational"):
            player.attackExploreVariables["nextLoc"]=Position(core_offset_x,core_offset_y)
        elif(player.attackExploreVariables["currentSymmetryExploring"]=="horizontal"):
            player.attackExploreVariables["nextLoc"]=Position(player.core_pos.x,core_offset_y)
        elif(player.attackExploreVariables["currentSymmetryExploring"]=="vertical"):
            player.attackExploreVariables["nextLoc"]=Position(core_offset_x,player.core_pos.y)
        else:
            print("Attack Explore Bad: Probably assuming we don't know symmetry",file=sys.stderr)
            
        player.attackExploreVariables["turns_since_last_choice"] = 0
        # Set indicator dot for target
        ct.draw_indicator_dot(player.attackExploreVariables["nextLoc"], 255, 0, 255)
        # Path to player.attackExploreVariables["nextLoc"] using A*
        move_via_path(player, player.attackExploreVariables["nextLoc"])

    else:
        # Set indicator dot
        ct.draw_indicator_dot(player.attackExploreVariables["nextLoc"], 10, 0, 10)
        move_via_path(player, player.attackExploreVariables["nextLoc"])

def move_via_path(player, target: Position) -> None:
    ct = player.ct
    map_instance = player.map
    start = (ct.get_position().x, ct.get_position().y)
    goal = (target.x, target.y)
    print(f"Calculating path from {start} to {goal}")
    path = find_path(player, start, goal)
    print(f"Path found: {path}")
    if path and len(path) > 1:
        next_step = path[1]
        next_pos = Position(next_step[0], next_step[1])
        print(f"Moving towards {target} via {next_pos} with cost {map_instance.get_cost(next_pos)}")
        try_move_with_build(player, next_pos)