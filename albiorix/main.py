"""Starter bot - a simple example to demonstrate usage of the Controller API.

Each unit gets its own Player instance; the engine calls run() once per round.
Use Controller.get_entity_type() to branch on what kind of unit you are.

This bot:
  - Core: spawns up to 3 builder bots on random adjacent tiles
  - Builder bot: builds a harvester on any adjacent ore tile, then moves in a
    random direction (laying a road first so the tile is passable), and places
    a marker recording the current round number
"""

import random

from cambc import Controller, Direction, EntityType, Environment, Position

from bots.core_bot import run as run_core
from bots.builder_bot import run as run_builder
from bots.sentry import run_sentry as run_sentry
from bots.gunner import run_gunner as run_gunner
from bots.launcher import run_launcher as run_launcher

from terrain.map import Map
from util import find_core_pos, can_afford_unit
import traceback
import sys
from config import *
from communications import *

class Player:
    def __init__(self):
        self.ct = None
        self.conveyor_build_mode = False #True
        self.num_spawned = 0 # number of builder bots spawned so far (core)
        self.target_ore = None  # target ore position for builder
        self.core_pos = None  # position of the allied core
        self.building_conveyors = False  # whether currently building conveyor path to core
        self.previous_pos = None  # previous position for building conveyor
        self.bridge_target = None
        self.repair_target = None
        self.path_front = None
        self.turns_waited = 0
        self.myRole=None
        self.turnsSinceRoleLastSet=0
        self.attack_path = None
        self.attack_split_build_target = None

        self.loose_end_target = None
        self.not_loose_path_start = None
        self.heal_target = None
        self.healed_last_turn = True
        self.found_enemy_core = False
        
        self.rush_target = None
        self.turns_rushing_target = 0
        self.rush_target_launcher = None
        self.rush_without_launch_success = False

        self.patrol_path_top = None
        self.patrol_path = []
        self.initial_patrol_bot = False

        self.friendly_builder_positions = dict()
        self.heal_targets_last_seen_round = dict()

        self.suicidal=random.random()<.5
        self.final_build_phase_turns_trying = 0

        self.gunner_self_destruct_timer = 0
        self.conveyor_target = None

        #Core resource rate management
        self.resources_collected_recently=[0] * 16

        #for atta
        self.attackExploreVariables={
            "currentSymmetryExploring":None,
            "nextLoc":None,
            "turns_since_last_choice":0
         }
        self.initial_explorer=False
        self.initial_explore_direction=None
        
        self.symmetry=None #set when we figure out a single symmetry
        self.possibleSymmetries=["rotational","horizontal","vertical"] #rotational, horizontal, vertical 
        self.enemy_core_pos=None
        self.finished_turn = True
        self.targetBuilder = True


    def run(self, ct: Controller) -> None:
        try:
            self.ct = ct

            print("role:", self.myRole)

            # update map
            if not hasattr(self, 'map'):
                self.map = Map(ct.get_map_width(), ct.get_map_height())
            etype = ct.get_entity_type()

            if self.core_pos is None:
                self.core_pos = find_core_pos(self)

            if(etype in [EntityType.SENTINEL, EntityType.CORE]) or (not self.finished_turn):
                pass
            else:
                self.finished_turn = False
                self.should_produce_axionite = (ct.get_current_round() > AXIONITE_START_ROUND) and can_afford_unit(ct, EntityType.FOUNDRY)

                start_time = ct.get_cpu_time_elapsed()
                self.map.update(self)
                end_time = ct.get_cpu_time_elapsed()
                print("map update run time:", end_time - start_time)
                start_time = ct.get_cpu_time_elapsed()
                self.map.update_splittable_locations(self)
                end_time = ct.get_cpu_time_elapsed()
                print("map update_splittable_locations run time:", end_time - start_time)
            
            print("is building conveyors?", self.building_conveyors)
            if etype == EntityType.CORE:
                self.num_spawned = run_core(ct, self.num_spawned,self)
            elif etype == EntityType.BUILDER_BOT:
                run_builder(ct, self.map, self)
            elif etype == EntityType.SENTINEL:
                run_sentry(ct, self.map, self)
            elif etype == EntityType.GUNNER:
                run_gunner(ct, self.map, self)
            elif etype == EntityType.LAUNCHER:
                run_launcher(ct, self.map, self)
            else:
                print("Bot type", etype, "unimplemented in run function in main.py")

            communicate_symmetry(self)
            self.finished_turn = True
            print("Time used:", ct.get_cpu_time_elapsed())
        except Exception:
            try:
                print(traceback.format_exc(), file=sys.stderr)
            except Exception as e:
                print("print(traceback.format_exc()) failed")
                print(e)