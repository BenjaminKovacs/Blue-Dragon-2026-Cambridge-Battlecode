from enum import Enum
from cambc import EntityType, Position

class Symmetry(Enum):
    HORIZONTAL = 1
    VERTICAL = 2
    ROTATIONAL = 3

class SymmetryCalculator:
    def __init__(self, width: int, height: int):
        self.width = width
        self.height = height
        self.possible_symmetries = {Symmetry.HORIZONTAL, Symmetry.VERTICAL, Symmetry.ROTATIONAL}

    def update(self, terrain: list[list], buildings: list[list], updated_positions: list[Position]) -> list[Symmetry]:
        """
        Updates the possible symmetries based on new map information.
        
        Args:
            terrain: The current terrain grid.
            buildings: The current buildings grid.
            updated_positions: A list of positions that have been updated this turn.
            
        Returns:
            A list of currently possible symmetries.
        """
        if not self.possible_symmetries:
            return []

        invalid_symmetries = set()
        core_matched_symmetries = set()

        for sym in self.possible_symmetries:
            is_valid = True
            for pos in updated_positions:
                if not (0 <= pos.x < self.width and 0 <= pos.y < self.height):
                    continue

                # Get symmetric position
                if sym == Symmetry.HORIZONTAL:
                    sx, sy = self.width - 1 - pos.x, pos.y
                elif sym == Symmetry.VERTICAL:
                    sx, sy = pos.x, self.height - 1 - pos.y
                elif sym == Symmetry.ROTATIONAL:
                    sx, sy = self.width - 1 - pos.x, self.height - 1 - pos.y
                else:
                    continue

                # We can only check consistency if we know both tiles
                t1 = terrain[pos.x][pos.y]
                t2 = terrain[sx][sy]

                # If either is unknown (None), we can't rule out symmetry yet
                if t1 is None or t2 is None:
                    continue

                # Check Terrain equality
                if t1 != t2:
                    is_valid = False
                    break

                # Check Cores
                # Symmetry implies that if one is a core, the other is a core.
                # Other buildings are ignored as they are player-placed.
                b1 = buildings[pos.x][pos.y]
                b2 = buildings[sx][sy]

                is_core1 = b1 is not None and b1['type'] == EntityType.CORE
                is_core2 = b2 is not None and b2['type'] == EntityType.CORE and (b2['team'] != b1['team'] if is_core1 else True)

                if is_core1 != is_core2:
                    is_valid = False
                    break

                elif is_core1 and is_core2:
                    core_matched_symmetries.add(sym)

            
            if not is_valid:
                invalid_symmetries.add(sym)
                
        if len(core_matched_symmetries) >= 1:
            self.possible_symmetries = core_matched_symmetries

        for sym in invalid_symmetries:
            self.possible_symmetries.discard(sym)
            
        return list(self.possible_symmetries)
    
    def get_enemy_core_pos(self, player):
        if not player.core_pos: return None
        width = player.map.width
        height = player.map.height
        
        symmetries = self.possible_symmetries
        
        # Priority: Rotational > others
        if Symmetry.ROTATIONAL in symmetries:
            return Position(width - 1 - player.core_pos.x, height - 1 - player.core_pos.y)
        elif Symmetry.HORIZONTAL in symmetries:
            return Position(width - 1 - player.core_pos.x, player.core_pos.y)
        elif Symmetry.VERTICAL in symmetries:
            return Position(player.core_pos.x, height - 1 - player.core_pos.y)
        
        return Position(width - 1 - player.core_pos.x, height - 1 - player.core_pos.y)

    def get_all_enemy_core_pos(self, player):
        if not player.core_pos: return None
        width = player.map.width
        height = player.map.height
        
        symmetries = self.possible_symmetries
        result = set()
        for s in symmetries:
            if s is Symmetry.ROTATIONAL:
                result.add(Position(width - 1 - player.core_pos.x, height - 1 - player.core_pos.y))
            elif s is Symmetry.HORIZONTAL:
                result.add(Position(width - 1 - player.core_pos.x, player.core_pos.y))
            elif s is Symmetry.VERTICAL:
                result.add(Position(player.core_pos.x, height - 1 - player.core_pos.y))
        print("possible enemy core pos", result)
        return result