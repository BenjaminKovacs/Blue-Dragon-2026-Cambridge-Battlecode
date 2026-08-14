import random
import math

from cambc import Controller, Direction, Position
from pathing.pathing import find_path
from terrain.map import Map
from util import *
from config import *

# Exploration variables
next_loc = None
turns_since_last_choice = 0
distance_to_wander = 10.0

def initial_explore(player, vertical=0) -> None:
    global next_loc, turns_since_last_choice, distance_to_wander

    ct = player.ct
    map_instance = player.map
    turns_since_last_choice += 1
    numberTries=0
    if turns_since_last_choice > 10 or next_loc is None or ((ct.get_position().x - next_loc.x)**2 + (ct.get_position().y - next_loc.y)**2) < 3 or map_instance.get_cost(next_loc) == float('inf'):
        next_loc = Position(-10, -10)
        while (next_loc.x < 0 or next_loc.y < 0 or next_loc.x >= map_instance.width or next_loc.y >= map_instance.height or
               map_instance.get_cost(next_loc) == float('inf')):
            
            upDown=random.randint(0,1)
            theta = random.random() * math.pi/2
            if(vertical==0):
                theta=theta+upDown*math.pi+math.pi/4
            elif(vertical==1):
                theta=theta+upDown*math.pi-math.pi/4
            else:
                theta = random.random() * math.pi*2
            if(numberTries>5):
                #Stop trying direction
                vertical=-1
            next_loc = Position(
                ct.get_position().x + int(round(math.cos(theta) * distance_to_wander)),
                ct.get_position().y + int(round(math.sin(theta) * distance_to_wander))
            )
            if distance_to_wander >= map_instance.width / 2 or distance_to_wander >= map_instance.height / 2:
                distance_to_wander -= 1.0
            numberTries+=1

        turns_since_last_choice = 0
        # Set indicator dot for target
        ct.draw_indicator_dot(next_loc, 255, 0, 255)
        # Path to next_loc using A*
        move_via_path(player, next_loc)

    else:
        # Set indicator dot
        ct.draw_indicator_dot(next_loc, 10, 0, 10)
        move_via_path(player, next_loc)

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
        if ct.get_global_resources()[0] < MINIMUM_MONEY_TO_EXPLORE:
            #if not try_move(ct, next_pos): #  and ct.get_global_resources()[0] < MINIMUM_MONEY_TO_EXPLORE - 10
            scramble_direction=DIRECTIONS
            random.shuffle(scramble_direction)
            mypos=ct.get_position()
            moved=False
            for dir in scramble_direction:
                if(try_move(ct, mypos.add(dir))):
                    moved=True
                    break
        else:
            try_move_with_build(player, next_pos)