from cambc import *
from .symmetry import SymmetryCalculator
from array import array
from config import *
from builder_actions.construct_foundry import check_split_to_foundry

# Variable for road building cost, can be changed easily
ROAD_BUILD_COST = 1.1
ORTHOGONAL_DIRECTIONS = [Direction.NORTH, Direction.SOUTH, Direction.EAST, Direction.WEST]
PASSABLE_BUILDINGS = [EntityType.CONVEYOR, EntityType.ROAD, EntityType.SPLITTER, EntityType.ARMOURED_CONVEYOR, EntityType.BRIDGE]

CONVEYOR = EntityType.CONVEYOR
SPLITTER = EntityType.SPLITTER
BRIDGE = EntityType.BRIDGE


def conveyor_load_to_cost(load):
    if load == 0:
        return 0
    elif load == 1:
        return 0.5
    elif load == 2:
        return 3.0
    elif load == 3:
        return 10.0
    else:
        return float('inf') # 500.0

def is_splitable_location(player, pos):
    current_building = player.map.get_building_info(pos)
    if current_building is not None and (current_building['type'] not in [EntityType.CONVEYOR, EntityType.ROAD] or current_building['team'] != player.ct.get_team()):
        # only replace friendly roads and conveyors
        return False

    # only build splitters with one conveyor leading there
    conveyors = player.map.get_conveyors_to_here(pos)
    adjacent_conveyors = [c for c in conveyors if distance_squared(c, pos) <= 2]
    if len(adjacent_conveyors) > 1 or len(conveyors) < 1:
        return False
    buildable_count = 0
    for d in ORTHOGONAL_DIRECTIONS:
        new_pos = pos.add(d)
        existing_building = player.map.get_building_info(new_pos)
        if player.map.get_terrain(new_pos) == Environment.EMPTY and (existing_building is None or (existing_building['team'] == player.ct.get_team() and existing_building['type'] not in [EntityType.CONVEYOR, EntityType.BRIDGE, EntityType.SPLITTER])):
            buildable_count += 1

    if buildable_count < 1:
        return False
    return True

def distance_squared(pos1: Position, pos2: Position) -> int:
    """Calculate the squared Euclidean distance between two positions."""
    return (pos1.x - pos2.x)**2 + (pos1.y - pos2.y)**2

class Map:
    def __init__(self, width: int, height: int):
        self.width = width
        self.height = height
        self.team = None
        # 2D list to store terrain: None for unknown, Environment for known
        self.terrain = [[None for _ in range(height)] for _ in range(width)]
        # 2D list to store last seen building info: None for no building or unknown, dict for building
        self.buildings = [[None for _ in range(height)] for _ in range(width)]
        # 2D list to store movement cost: inf for impassable, positive for passable
        #self.cost_grid = [[1 for _ in range(height)] for _ in range(width)]
        self.cost_grid = array('f', [1.0] * (width * height))
        self.conveyor_cost_grid = array('f', [1.0] * (width * height))
        self.axionite_cost_grid = array('f', [1.0] * (width * height))

        self.belt_load_counts = [[0 for _ in range(height)] for _ in range(width)]
        self.line_load_counts = [[0 for _ in range(height)] for _ in range(width)]
        self.line_loads_computed = [[False for _ in range(height)] for _ in range(width)]
        # Closest ore without building
        self.closest_ore = None
        
        self.symmetry_calculator = SymmetryCalculator(width, height)

        self.conveyors_to_here = [[[] for _ in range(height)] for _ in range(width)]
        self.splitters_to_here = [[[] for _ in range(height)] for _ in range(width)]

        self.nearby_positions = []
        self.nearby_buildings = []
        self.healable_buildings = []
        self.adjacent_to_unconnected_harvester = set()
        self.adjacent_to_harvester = set()
        self.adjacent_to_titanium_harvester = set()
        self.adjacent_to_axionite_harvester = set()
        self.adjacent_to_enemy_launcher = set()
        self.adjacent_to_friendly_launcher = set()
        self.nearest_enemy_turret = None

        self.axionite_conveyors = set()
        self.axionite_conveyors_adjacent_to_core = set()

        self.closest_conveyor = None
        self.closest_titanium_conveyor = None

        self.is_titanium_conveyor = [[False for _ in range(height)] for _ in range(width)]
        self.is_axionite_conveyor = [[False for _ in range(height)] for _ in range(width)]
        self.valid_axionite_endpoint = [[False for _ in range(height)] for _ in range(width)]
        self.titanium_conveyor_computed = [[True for _ in range(height)] for _ in range(width)]
        self.valid_axionite_endpoint_computed = [[True for _ in range(height)] for _ in range(width)]

        self.closest_axionite_endpoint = None

    def update_conveyor_types(self, pos):
        x, y = pos.x, pos.y
        if self.titanium_conveyor_computed[x][y]:
            return (self.is_titanium_conveyor[x][y], self.is_axionite_conveyor[x][y])
        self.titanium_conveyor_computed[x][y] = True
        self.is_titanium_conveyor[x][y] = False
        self.is_axionite_conveyor[x][y] = False
        
        b = self.buildings[x][y]
        resource_type = b and b['stored_resource']
        titanium = (pos in self.adjacent_to_titanium_harvester) or (resource_type is ResourceType.TITANIUM)
        axionite = (pos in self.adjacent_to_axionite_harvester) or (resource_type is ResourceType.RAW_AXIONITE)
        
        for c in self.conveyors_to_here[x][y]:
            t, a = self.update_conveyor_types(c)
            titanium = titanium or t
            axionite = axionite or a

        self.is_titanium_conveyor[x][y] = titanium
        self.is_axionite_conveyor[x][y] = axionite
        return (titanium, axionite)

    def compute_axionite_endpoint(self, player, pos):
        x, y = pos.x, pos.y
        if self.valid_axionite_endpoint_computed[x][y]:
            return self.valid_axionite_endpoint[x][y]

        self.valid_axionite_endpoint_computed[x][y] = True

        if ((b := self.buildings[x][y]) is None) or (b['team'] is not self.team) or not ((b_type := b['type']) is CONVEYOR or b_type is SPLITTER or b_type is BRIDGE) or self.is_axionite_conveyor[x][y] or not self.is_titanium_conveyor[x][y]:
            self.valid_axionite_endpoint[x][y] = False
            return False

        core_pos = player.core_pos
        dx = x - core_pos.x
        dy = y - core_pos.y
        if dx*dx + dy*dy <= 5:
            self.valid_axionite_endpoint[x][y] = True
            return True
            # If foundry already exists, location is ok
            # for d in ORTHOGONAL_DIRECTIONS:
            #     b = self.get_building_info(pos.add(d))
            #     if b and b['type'] is EntityType.FOUNDRY and b['team'] is self.team:
            #         self.valid_axionite_endpoint[x][y] = True
            #         return True

            # # Otherwise, must have a valid location to build foundry
            # if check_split_to_foundry(player, pos):
            #     self.valid_axionite_endpoint[x][y] = True
            #     return True

            # self.valid_axionite_endpoint[x][y] = False
            # return False
            
        else:
            if b_type is EntityType.BRIDGE:
                next_point = b['bridge_target']
            else:
                # TODO: splitters?
                next_point = pos.add(b['direction'])
            if 0 <= next_point.x < self.width and 0 <= next_point.y < self.height:
                self.valid_axionite_endpoint[x][y] = False
                result = self.compute_axionite_endpoint(player, next_point)
                self.valid_axionite_endpoint[x][y] = result
                return result
            else:
                self.valid_axionite_endpoint[x][y] = False
                return False

    def update_line_load_counts(self, pos):
        x, y = pos.x, pos.y
        if not (0 <= x < self.width and 0 <= y < self.height):
            return 4
        if self.line_loads_computed[x][y]:
            return self.line_load_counts[x][y]
        self.line_loads_computed[x][y] = True

        building_info = self.buildings[x][y]
        building_type = (building_info is not None) and building_info['type']
        result = self.belt_load_counts[x][y]
        if building_type is EntityType.CONVEYOR or building_type is EntityType.ARMOURED_CONVEYOR:
            next_pos = pos.add(building_info['direction'])
            l = self.update_line_load_counts(next_pos)
            result = max(l, result)
        elif building_type is EntityType.BRIDGE:
            next_pos = building_info['bridge_target']
            l = self.update_line_load_counts(next_pos)
            result = max(l, result)
        
        self.line_load_counts[x][y] = result
        return result

    def update(self, player) -> None:
        """Update the map with visible tiles at the start of each turn."""
        ct = player.ct
        get_team = ct.get_team
        get_entity_type = ct.get_entity_type
        get_hp = ct.get_hp
        get_max_hp = ct.get_max_hp
        get_direction = ct.get_direction
        get_tile_env = ct.get_tile_env
        get_tile_building_id = ct.get_tile_building_id
        get_stored_resource = ct.get_stored_resource
        get_bridge_target = ct.get_bridge_target
        get_position = ct.get_position
        is_in_vision = ct.is_in_vision

        my_team = ct.get_team()
        self.team = my_team
        vision_sq = ct.get_vision_radius_sq()
        adjacent_vision = 10
        nearby_positions = ct.get_nearby_tiles(vision_sq)
        self.nearby_positions = nearby_positions
        self.nearby_buildings = []
        my_pos = ct.get_position()
        width, height = self.width, self.height

        self.healable_buildings = [b for b in self.healable_buildings if not is_in_vision(b['position'])] #list(filter(lambda b: not ct.is_in_vision(b['position']), self.healable_buildings))
        self.adjacent_to_enemy_launcher = set(p for p in self.adjacent_to_enemy_launcher if distance_squared(my_pos, p) <= adjacent_vision) #set(filter(lambda p: not ct.is_in_vision(p), self.adjacent_to_enemy_launcher))
        self.adjacent_to_friendly_launcher = set(p for p in self.adjacent_to_friendly_launcher if distance_squared(my_pos, p) <= adjacent_vision) # not is_in_vision(p) #set(filter(lambda p: not ct.is_in_vision(p), self.adjacent_to_friendly_launcher))

        # remove visible conveyors (they will be readded if they still exist)
        for pos in nearby_positions:
            if 0 <= pos.x < width and 0 <= pos.y < height:
                self.conveyors_to_here[pos.x][pos.y] = [p for p in self.conveyors_to_here[pos.x][pos.y] if not is_in_vision(p)] #list(filter(lambda p: not ct.is_in_vision(p), self.conveyors_to_here[pos.x][pos.y]))
                self.splitters_to_here[pos.x][pos.y] = [p for p in self.splitters_to_here[pos.x][pos.y] if not is_in_vision(p)] #list(filter(lambda p: not ct.is_in_vision(p), self.splitters_to_here[pos.x][pos.y]))

        start_time = ct.get_cpu_time_elapsed()
        for pos in nearby_positions:
            x, y = pos.x, pos.y
            terrain = get_tile_env(pos)
            self.terrain[x][y] = terrain
            building_id = get_tile_building_id(pos)
            building_type = get_entity_type(building_id)

            if building_id is not None and building_type is not EntityType.MARKER:
                entity_team = get_team(building_id)
                building_hp = get_hp(building_id)
                building_max_hp = get_max_hp(building_id)
                direction = None
                bridge_target = None
                stored_resource = None
                friendly = entity_team is my_team

                match building_type:
                    case EntityType.CONVEYOR:
                        direction = get_direction(building_id)
                        cost = 1.0
                        conveyor_cost = 1.0
                        axionite_cost = 1.0 if friendly else float('inf')
                        target_pos = pos.add(direction)
                        if 0 <= target_pos.x < width and 0 <= target_pos.y < height:
                            self.conveyors_to_here[target_pos.x][target_pos.y].append(pos)
                        stored_resource = get_stored_resource(building_id)
                        if stored_resource is None:
                            self.belt_load_counts[x][y] = 0
                        else:
                            self.belt_load_counts[x][y] += 1
                            if stored_resource is ResourceType.RAW_AXIONITE:
                                self.axionite_conveyors.add(pos)
                                if player.core_pos is None:
                                    print("player.core_pos is None in map update")
                                elif distance_squared(pos, player.core_pos) <= 5:
                                    self.axionite_conveyors_adjacent_to_core.add(pos)
                        if friendly and (self.closest_conveyor is None or distance_squared(my_pos, self.closest_conveyor) > distance_squared(my_pos, pos)):
                            self.closest_conveyor = pos

                    case EntityType.BRIDGE:
                        cost = 1.0
                        conveyor_cost = 1.0
                        axionite_cost = 1.0 if friendly else float('inf')
                        bridge_target = get_bridge_target(building_id)
                        target_pos = bridge_target
                        stored_resource = get_stored_resource(building_id)
                        if 0 <= target_pos.x < width and 0 <= target_pos.y < height:
                            self.conveyors_to_here[target_pos.x][target_pos.y].append(pos)
                        if stored_resource is None:
                            self.belt_load_counts[x][y] = 0
                        else:
                            self.belt_load_counts[x][y] += 1

                    case EntityType.SPLITTER:
                        direction = get_direction(building_id)
                        cost = 1.0
                        conveyor_cost = 1.0
                        axionite_cost = 1.0 if friendly else float('inf')
                        # For splitters, we treat them as conveyors in all 4 directions for pathfinding purposes
                        self.belt_load_counts[x][y] = 100
                        splitter_direction = direction
                        for d in [splitter_direction, splitter_direction.rotate_right().rotate_right(), splitter_direction.rotate_left().rotate_left()]:
                            target_pos = pos.add(d)
                            if 0 <= target_pos.x < width and 0 <= target_pos.y < height:
                                #self.conveyors_to_here[target_pos.x][target_pos.y].append(pos)
                                self.splitters_to_here[target_pos.x][target_pos.y].append(pos)
                
                    case EntityType.LAUNCHER:
                        cost = float('inf')
                        conveyor_cost = float('inf')
                        axionite_cost = float('inf')
                        if entity_team != ct.get_team():
                            for d in DIRECTIONS:
                                self.adjacent_to_enemy_launcher.add(pos.add(d))
                        else:
                            for d in DIRECTIONS:
                                self.adjacent_to_friendly_launcher.add(pos.add(d))
                
                    case EntityType.CORE:
                        if friendly:
                            cost = 1.0  # passable allied core
                            conveyor_cost = 1.0
                            axionite_cost = float('inf')
                        else:
                            cost = float('inf')  # Impassable building
                            conveyor_cost = 1.0
                            axionite_cost = float('inf')

                    case EntityType.ROAD:
                        cost = 1.0
                        conveyor_cost = 1.0
                        axionite_cost = 1.0 if friendly else float('inf')

                    case EntityType.ARMOURED_CONVEYOR:
                        cost = 1.0
                        conveyor_cost = 1.0
                        axionite_cost = 1.0 if friendly else float('inf')
                        direction = get_direction(building_id)

                    case _:
                        cost = float('inf')  # Impassable building
                        conveyor_cost = float('inf')
                        axionite_cost = float('inf')
                        if building_type is EntityType.GUNNER or building_type is EntityType.SENTINEL or building_type is EntityType.BREACH:
                            direction = get_direction(building_id)

                # Store all building info
                building_info = {
                    'id': building_id,
                    'type': building_type,
                    'position': get_position(building_id),
                    'hp': building_hp,
                    'max_hp': building_max_hp,
                    'team': entity_team,
                    'direction': direction,
                    'bridge_target': bridge_target,
                    'stored_resource': stored_resource
                }

                self.buildings[x][y] = building_info

                self.nearby_buildings.append(building_info)
                if building_hp < building_max_hp and friendly:
                    self.healable_buildings.append(building_info)
            else:
                self.buildings[x][y] = None
                cost = ROAD_BUILD_COST
                if terrain is Environment.WALL:
                    cost = float('inf')
                    conveyor_cost = float('inf')
                elif terrain is Environment.EMPTY:
                    conveyor_cost = 1
                else:
                    conveyor_cost = 50.0
                axionite_cost = conveyor_cost

            index = x * self.height + y
            self.cost_grid[index] = cost
            self.line_loads_computed[x][y] = False
            self.titanium_conveyor_computed[x][y] = False
            self.valid_axionite_endpoint_computed[x][y] = False
            self.conveyor_cost_grid[index] = conveyor_cost
            self.axionite_cost_grid[index] = axionite_cost

        end_time = ct.get_cpu_time_elapsed()
        print("main map update loop run time:", end_time - start_time)

        start_time = ct.get_cpu_time_elapsed()
        # Update symmetries based on newly seen tiles
        self.symmetry_calculator.update(self.terrain, self.buildings, nearby_positions)
        end_time = ct.get_cpu_time_elapsed()
        print("symmetry calculator run time:", end_time - start_time)

        start_time = ct.get_cpu_time_elapsed()
        # Update closest ore
        current_pos = ct.get_position()
        self.closest_ore = None
        min_dist = float('inf')
        for pos in nearby_positions:
            if self.terrain[pos.x][pos.y] in [Environment.ORE_TITANIUM, Environment.ORE_AXIONITE] and self.buildings[pos.x][pos.y] is None:
                dist = (pos.x - current_pos.x)**2 + (pos.y - current_pos.y)**2
                if dist < min_dist:
                    min_dist = dist
                    self.closest_ore = pos

        if self.nearest_enemy_turret:
            b = self.buildings[pos.x][pos.y]
            if not b or b['team'] is my_team or b['type'] not in TURRETS:
                self.nearest_enemy_turret = None
        min_dist = float('inf')
        for pos in nearby_positions:
            b = self.buildings[pos.x][pos.y]
            if b is not None and b['team'] != ct.get_team() and b['type'] in TURRETS:
                dist = (pos.x - current_pos.x)**2 + (pos.y - current_pos.y)**2
                if dist < min_dist:
                    min_dist = dist
                    self.nearest_enemy_turret = pos
        end_time = ct.get_cpu_time_elapsed()
        print("end map update run time:", end_time - start_time)

    def update_splittable_locations(self, player):
        ct = player.ct
        width, height = self.width, self.height
        my_pos = ct.get_position()
        my_team = ct.get_team()
        self.adjacent_to_unconnected_harvester = set(p for p in self.adjacent_to_unconnected_harvester if not ct.is_in_vision(p))
        self.adjacent_to_harvester = set(p for p in self.adjacent_to_harvester if not ct.is_in_vision(p))
        
        start_time = ct.get_cpu_time_elapsed()
        nearby_positions = self.nearby_positions
        for pos in nearby_positions:
            x, y = pos.x, pos.y
            building_info = self.buildings[x][y]
            if building_info and (((building_type := building_info['type']) is EntityType.HARVESTER) or (building_type is EntityType.FOUNDRY)):
                    building_info['adjacent_conveyor'] = False
                    for d in ORTHOGONAL_DIRECTIONS:
                        b = self.get_building_info(pos.add(d))
                        if b and (b['team'] is my_team) and ((b_type := b['type']) is EntityType.CONVEYOR or (b_type is EntityType.BRIDGE) or (b_type is EntityType.SPLITTER)or (b_type is EntityType.ARMOURED_CONVEYOR)) and (b_type is EntityType.BRIDGE or (b_direction := b['direction']) is not d.opposite()) and (b_type is not EntityType.SPLITTER or b_direction is d):
                            if b_type is EntityType.CONVEYOR:
                                test_pos = pos.add(d).add(b_direction)
                                test_building = self.get_building_info(test_pos)
                                if test_building is not None and test_building['type'] is EntityType.HARVESTER:
                                    continue
                            building_info['adjacent_conveyor'] = True
                            break
                    if (not building_info['adjacent_conveyor']) and ((not player.core_pos) or distance_squared(pos, player.core_pos) > 5):
                        for d in ORTHOGONAL_DIRECTIONS:
                            self.adjacent_to_unconnected_harvester.add(pos.add(d))
                    for d in ORTHOGONAL_DIRECTIONS:
                        new_pos = pos.add(d)
                        self.adjacent_to_harvester.add(new_pos)
                        if (terr := self.terrain[x][y]) is Environment.ORE_TITANIUM:
                            self.adjacent_to_titanium_harvester.add(new_pos)
                        elif terr is Environment.ORE_AXIONITE:
                            self.adjacent_to_axionite_harvester.add(new_pos)
            if pos in self.adjacent_to_enemy_launcher:
                self.cost_grid[x * height + y] += ENEMY_LAUNCHER_ADJACENCY_COST
            elif pos in self.adjacent_to_friendly_launcher and (player.myRole != "rush_attacker") and (player.ct.get_id() >= 5):
                self.cost_grid[x * height + y] += FRIENDLY_LAUNCHER_ADJACENCY_COST

            if building_info is not None and building_info['type'] in CONVEYOR_BUILDINGS and building_info['team'] is my_team:
                self.conveyor_cost_grid[x * height + y] += conveyor_load_to_cost(self.update_line_load_counts(pos))
        end_time = ct.get_cpu_time_elapsed()
        print("harvester update run time:", end_time - start_time)

        start_time = ct.get_cpu_time_elapsed()
        for pos in nearby_positions:
            self.update_conveyor_types(pos)
            if building_info and building_info['type'] is EntityType.CONVEYOR and (self.closest_titanium_conveyor is None or distance_squared(my_pos, self.closest_titanium_conveyor) > distance_squared(my_pos, pos)) and building_info['team'] == player.ct.get_team():
                self.closest_titanium_conveyor = pos

            axionite = self.is_axionite_conveyor[pos.x][pos.y]
            if axionite:
                self.axionite_cost_grid[pos.x * self.height + pos.y] = float('inf')

        end_time = ct.get_cpu_time_elapsed()
        print("conveyor type update run time:", end_time - start_time)

        start_time = ct.get_cpu_time_elapsed()
        if self.closest_axionite_endpoint and player.core_pos and not self.compute_axionite_endpoint(player, self.closest_axionite_endpoint):
            self.closest_axionite_endpoint = None

        best_distance = float('inf')
        if self.closest_axionite_endpoint is not None:
            best_distance = distance_squared(my_pos, self.closest_axionite_endpoint)

        if player.core_pos:
            for pos in nearby_positions:
                x, y = pos.x, pos.y
                b = self.buildings[x][y]
                if self.compute_axionite_endpoint(player, pos):
                    self.axionite_cost_grid[x * height + y] = 1.0
                    dx = x - my_pos.x
                    dy = y - my_pos.y
                    distance = dx*dx + dy*dy
                    if distance < best_distance:
                        self.closest_axionite_endpoint = pos
                        best_distance = distance
                elif b and b['type'] in CONVEYOR_BUILDINGS:
                    self.axionite_cost_grid[x * height + y] = float('inf')
        
        end_time = ct.get_cpu_time_elapsed()
        print("axionite endpoint update run time:", end_time - start_time)


    def on_the_map(self, pos: Position) -> bool:
        """Check if a position is on the map."""
        return 0 <= pos.x < self.width and 0 <= pos.y < self.height

    def get_terrain(self, pos: Position) -> Environment | None:
        """Get the terrain at a position, or None if unknown."""
        if self.on_the_map(pos):
            return self.terrain[pos.x][pos.y]
        return None

    def get_building_info(self, pos: Position) -> dict | None:
        """Get the last seen building info at a position, or None if no building or unknown."""
        if self.on_the_map(pos):
            return self.buildings[pos.x][pos.y]
        return None

    def get_cost(self, pos: Position) -> float:
        """Get the movement cost for a position."""
        if self.on_the_map(pos):
            return self.cost_grid[pos.x*self.height + pos.y]
        return float('inf')

    def is_passable(self, pos: Position) -> bool | None:
        """Check if a tile is passable, based on stored cost."""
        cost = self.get_cost(pos)
        if cost == float('inf'):
            return False
        elif cost < float('inf'):
            return True
        else:
            return None  # Unknown
        
    def is_walkable(self, pos: Position) -> bool | None:
        if not self.is_passable(pos):
            return False
        building_info = self.get_building_info(pos)
        return (building_info is not None) and (building_info['type'] in PASSABLE_BUILDINGS)

    def get_conveyors_to_here(self, pos: Position) -> list:
        if self.on_the_map(pos):
            return self.conveyors_to_here[pos.x][pos.y]
        return []

    def get_splitters_to_here(self, pos: Position) -> list:
        if self.on_the_map(pos):
            return self.splitters_to_here[pos.x][pos.y]
        return []

    def is_buildable(self, pos: Position) -> bool:
        if self.on_the_map(pos):
            building = self.buildings[pos.x][pos.y]
            return self.terrain[pos.x][pos.y] != Environment.WALL and (building is None or building['team'] == self.team)
        return False

    def is_buildable_without_replacement(self, pos: Position) -> bool:
        if self.on_the_map(pos):
            building = self.buildings[pos.x][pos.y]
            return self.terrain[pos.x][pos.y] != Environment.WALL and (building is None or (building['team'] is self.team and building['type'] is EntityType.ROAD))
        return False

    def is_friendly_turret(self, pos: Position) -> bool:
        if self.on_the_map(pos):
            building = self.buildings[pos.x][pos.y]
            return building is not None and building['team'] == self.team and building['type'] not in PASSABLE_BUILDINGS
        return False

    def is_enemy_building(self, pos: Position) -> bool:
        if self.on_the_map(pos):
            building = self.buildings[pos.x][pos.y]
            return building is not None and building['team'] != self.team
        return False

    def leads_to_enemy_building(self, pos: Position) -> bool:
        if self.on_the_map(pos):
            building = self.buildings[pos.x][pos.y]
            if building is None or building['team'] != self.team:
                return False

            if building['type'] == EntityType.CONVEYOR:
                output_location = pos.add(building['direction'])
            elif building['type'] == EntityType.BRIDGE:
                output_location = building['bridge_target']
            else:
                return False
            return self.is_enemy_building(output_location)
        return False

    def is_mixed_conveyor(self, pos):
        if self.on_the_map(pos):
            building = self.buildings[pos.x][pos.y]
            if building is not None and building['team'] == self.team and building['type'] == EntityType.CONVEYOR:
                return self.is_titanium_conveyor[pos.x][pos.y] and self.is_axionite_conveyor[pos.x][pos.y]
        return False

    def should_build_foundry(self, pos):
        if not self.is_mixed_conveyor(pos):
            return False
        conveyors = self.get_conveyors_to_here(pos)
        has_axionite = pos in self.adjacent_to_axionite_harvester or any(self.is_axionite_conveyor[c.x][c.y] for c in conveyors)
        has_titanium = pos in self.adjacent_to_titanium_harvester or any(self.is_titanium_conveyor[c.x][c.y] for c in conveyors)
        return has_axionite and has_titanium