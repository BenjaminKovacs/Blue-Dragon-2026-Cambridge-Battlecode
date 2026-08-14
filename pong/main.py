from cambc import *
from builder_actions import data

test_mode = True

road_clean_up_rounds = {
    (7, 21): 655,
    (13, 22): 626,
    (15, 21): 618,
    (16, 20): 617,
    (13, 11): 599,
    (5, 13): 96,
    (5, 14): 95,
    (5, 15): 94,
    (2, 18): 91,
    (5, 19): 82,
    (6, 19): 76,
    (7, 19): 75,
    (7, 15): 79,

}

spawn_turn_to_index = {
    1: 0,
    2: 1,
    3000: 2,
}
wanted_build_turns=list(sorted(list(spawn_turn_to_index.keys())))
wanted_bots=[0+sum([1 if i>=k else 0 for k in wanted_build_turns]) for i in range(2000)]

flicker_foundry_round = 1815
flicker_foundry_location = (20, 16)
splitter_locations = [(12,20),(4,22), (8,15), (4,12), (5,8),(6, 16),  (10,17),(3,17),(1,15),(0,12),(10,12), (14,12),(15,15),(17,17), (2,4),(6,4), (18,18),(19,15),(20,16),(20,12)]
#splitter_locations = [(10,17),(3,17),(1,15),(0,12),(10,12), (14,12),(15,15),(17,17)]
more_splitter_locations=[]
for s in splitter_locations:
    more_splitter_locations.append((49-s[0],s[1]))
splitter_locations=more_splitter_locations+splitter_locations

def symmetry_pos(pos,isLeft):
    if(pos is None):
        return None
    if(isLeft):
        return pos
    else:
        return Position(49-pos[0],pos[1])
def symmetry_dir(dir,isLeft):
    if(dir is None):
        return None
    if(isLeft):
        return dir
    else:
        return {
            Direction.EAST:Direction.WEST,
            Direction.SOUTHEAST:Direction.SOUTHWEST,
            Direction.NORTHEAST:Direction.NORTHWEST,

            Direction.WEST:Direction.EAST,
            Direction.SOUTHWEST:Direction.SOUTHEAST,
            Direction.NORTHWEST:Direction.NORTHEAST,

            Direction.NORTH:Direction.NORTH,
            Direction.SOUTH:Direction.SOUTH,
            Direction.CENTRE:Direction.CENTRE,

        }[dir]



def building_string_to_entity_type(building_string):
    match building_string:
        case "ROAD":
            return EntityType.ROAD
        case "CONVEYOR":
            return EntityType.CONVEYOR
        case "HARVESTER":
            return EntityType.HARVESTER
        case "BRIDGE":
            return EntityType.BRIDGE
        case "FOUNDRY":
            return EntityType.FOUNDRY
        case "SPLITTER":
            return EntityType.SPLITTER
        case _:
            return None
        
def can_afford_unit(ct, unit_type) -> bool:
    """Check if the player can afford to build a unit of the given type."""
    titanium = ct.get_global_resources()[0]
    scaling = ct.get_scale_percent() / 100
    match unit_type:
        case EntityType.ROAD:
            return titanium >= GameConstants.ROAD_BASE_COST[0] * scaling
        case EntityType.CONVEYOR:
            return titanium >= GameConstants.CONVEYOR_BASE_COST[0] * scaling
        case EntityType.HARVESTER:
            return titanium >= GameConstants.HARVESTER_BASE_COST[0] * scaling
        case EntityType.BRIDGE:
            return titanium >= GameConstants.BRIDGE_BASE_COST[0] * scaling
        case EntityType.FOUNDRY:
            return titanium >= GameConstants.FOUNDRY_BASE_COST[0] * scaling
        case EntityType.SPLITTER:
            return titanium >= GameConstants.SPLITTER_BASE_COST[0] * scaling
        case _:
            print("TODO: not yet implemented for type", unit_type)
    return False

def convert_build_target(build_location, target_location,myTeamSide):
    if target_location is None:
        return None
    
    target_location = symmetry_pos(Position(target_location[0], target_location[1]),myTeamSide)
    if build_location.distance_squared(target_location) <= 1:
        return build_location.direction_to(target_location)
    return target_location

def do_road_cleanup(ct):
    my_location = ct.get_position()
    if (my_location.x, my_location.y) in road_clean_up_rounds and ct.get_current_round() >= road_clean_up_rounds[(my_location.x, my_location.y)]:
        building = ct.get_tile_building_id(my_location)
        building_type = ct.get_entity_type(building) if building else None
        if building_type == EntityType.ROAD and ct.can_destroy(my_location):
           ct.destroy(my_location)

class Player:
    def __init__(self):
        self.builder_index = -1
        self.action_index = 0
        self.ct = None
        self.axionite_collection = []
        self.previous_axionite = 0
        self.myTeamSide=False
    def run_core(self):
        
        if (wanted_bots[self.ct.get_current_round()]>self.builder_index)and self.ct.can_spawn(symmetry_pos(data[self.builder_index]['spawn_location'],self.myTeamSide)):
            self.ct.spawn_builder(symmetry_pos(data[self.builder_index]['spawn_location'],self.myTeamSide))
            self.builder_index += 1

        titanium, axionite = self.ct.get_global_resources()
        if self.ct.get_current_round() < 84: # 97 #titanium < self.ct.get_scale_percent()/100 * 60:
            self.ct.convert(axionite)
        elif self.ct.get_current_round() == 85:
            print(axionite)
            self.ct.convert(min(47, axionite))

        self.axionite_collection.append(axionite - self.previous_axionite)
        titanium, axionite = self.ct.get_global_resources()
        self.previous_axionite = axionite
        print(self.axionite_collection)

    def handle_builder_action(self, moved, built):
        my_actions = data[self.builder_index]['actions']
        next_action = my_actions[self.action_index]
        do_road_cleanup(self.ct)
        match next_action['type']:
            case 'MOVE':
                if moved:
                    return False
                move_location = symmetry_pos(Position(*next_action['move_location']),self.myTeamSide)
                direction = self.ct.get_position().direction_to(move_location)
                if self.ct.can_move(direction):
                    self.ct.move(direction)
                    self.action_index += 1
                    return (True, built)
                else:
                    print(f"Error: cannot move to {move_location}")
                    return False
                
            case 'BUILD':
                build_location = symmetry_pos(Position(*next_action['build_location']),self.myTeamSide)
                building_type = building_string_to_entity_type(next_action['building_type'])
                target_location = convert_build_target(build_location, next_action['target_location'],self.myTeamSide)
                
                if (self.ct.get_current_round() < flicker_foundry_round) and (building_type == EntityType.FOUNDRY) and (next_action['build_location'] == flicker_foundry_location):
                    return False
                
                if build_location in splitter_locations and building_type == EntityType.CONVEYOR:
                    building_type = EntityType.SPLITTER

                if built:
                    return False

                # if build_location == Position(7, 5) and self.builder_index == 0:
                #     titanium, axionite = self.ct.get_global_resources()
                #     if titanium >= self.ct.get_scale_percent()/100 * 20 and self.ct.get_stored_resource(self.ct.get_tile_building_id(Position(7,6))) is None:
                #         if self.ct.can_destroy(build_location):
                #             self.ct.destroy(build_location)
                #         if self.ct.can_build(building_type, build_location, target_location):
                #             self.ct.build(building_type, build_location, target_location)
                #             self.action_index += 1
                #     return False

                if self.ct.can_destroy(build_location) and can_afford_unit(self.ct, building_type):
                    self.ct.destroy(build_location)
                    print(f"Destroying {build_location} before building")
                
                if self.ct.can_build(building_type, build_location, target_location):
                    self.ct.build(building_type, build_location, target_location)
                    if test_mode or not (self.builder_index == 0 and self.action_index == len(my_actions) - 1):
                        self.action_index += 1
                    return (moved, True)
                else:
                    print(f"Error: cannot build {building_type} at {build_location}")
                    return False
                
            case "WAIT":
                self.action_index += 1
                return False

    def run_builder(self):
        actions_taken = (False, False)
        while actions_taken := self.handle_builder_action(*actions_taken):
            pass

    def run(self, ct: Controller) -> None:
        self.ct = ct
        self.myTeamSide=ct.get_position().x<24
        
        
        print(f"Turn {ct.get_current_round()}, builder index: {self.builder_index}, action index: {self.action_index}")
        match ct.get_entity_type():
            case EntityType.CORE:
                if self.builder_index == -1:
                    self.builder_index = 0
                self.run_core()
            case EntityType.BUILDER_BOT:
                if self.builder_index == -1:
                    
                    self.builder_index = spawn_turn_to_index[
                        max([x for x in wanted_build_turns if x < ct.get_current_round()])
                            ]
                    print(self.builder_index)
                self.run_builder()