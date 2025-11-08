"""
Level Generator - Main orchestrator for procedural level generation
"""

import time
from typing import Dict, List, Tuple, Optional, Any
import pygame

from config import TILE
from seed_manager import SeedManager
from generation_algorithms import HybridGenerator
from level_validator import LevelValidator
from terrain_system import TerrainType, terrain_system

# Procedural enemy spawn tuning constants (used only in GeneratedLevel._spawn_enemies)
BUG_WIDTH = 28
BUG_HEIGHT = 22
ENEMY_PADDING = 4        # Horizontal margin between enemies for spacing checks
PLAYER_SAFETY_PAD_X = 32 # Extra horizontal buffer around player spawn
PLAYER_SAFETY_PAD_Y = 16 # Extra vertical buffer around player spawn


class GeneratedLevel:
    """
    Represents a procedurally generated level.

    This class is shaped to be drop-in compatible with the existing Level API
    used by main.py and other systems:
      - Attributes:
          solids: List[pygame.Rect]
          enemies: List[Enemy]
          doors: List[pygame.Rect]
          spawn: (x, y)
          w, h: pixel dimensions
          is_procedural: bool
      - Methods:
          draw(surf, camera): renders basic tiles/doors
    """
    
    def __init__(self, grid: List[List[int]], rooms: List, spawn_points: List[Tuple[int, int]],
                 level_type: str, terrain_grid: Optional[List[List[str]]] = None):
        self.grid = grid
        self.rooms = rooms
        self.spawn_points = spawn_points
        self.level_type = level_type
        self.terrain_grid = terrain_grid or self._create_default_terrain(grid)
        
        # Core gameplay/physics data expected by the game
        self.solids: List[pygame.Rect] = []
        self.enemies: List = []
        self.doors: List[pygame.Rect] = []
        self.spawn: Tuple[int, int] = (TILE * 2, TILE * 2)

        # Portal position in pixel coordinates (x, y)
        self.portal_pos: Optional[Tuple[int, int]] = None

        # Meta
        self.is_procedural: bool = True

        # Derived sizes in pixels for compatibility with camera/terrain_system
        if self.grid and len(self.grid) > 0 and len(self.grid[0]) > 0:
            self.w = len(self.grid[0]) * TILE
            self.h = len(self.grid) * TILE
        else:
            # Fallback to config sizes
            self.w = 40 * TILE
            self.h = 30 * TILE
        
        self._process_level()
    
    def _create_default_terrain(self, grid: List[List[int]]) -> List[List[str]]:
        """Create default terrain grid from level grid"""
        terrain_grid = []
        for row in grid:
            terrain_row = []
            for tile in row:
                if tile == 1:  # Wall
                    terrain_row.append(TerrainType.NORMAL.value)
                else:  # Floor
                    terrain_row.append(TerrainType.NORMAL.value)
            terrain_grid.append(terrain_row)
        return terrain_grid
    
    def _process_level(self):
        """Process generated level into game-compatible format."""
        height = len(self.grid)
        width = len(self.grid[0]) if height > 0 else 0

        # Convert grid to solid rectangles
        for y, row in enumerate(self.grid):
            for x, tile in enumerate(row):
                if tile == 1:  # Wall
                    rect = pygame.Rect(x * TILE, y * TILE, TILE, TILE)
                    self.solids.append(rect)

        # Set spawn point in pixels (must be on floor)
        if self.spawn_points:
            sx, sy = self.spawn_points[0]
            if 0 <= sy < height and 0 <= sx < width and self.grid[sy][sx] == 0:
                self.spawn = (sx * TILE, sy * TILE)

        # Place portal on a reachable floor tile
        self.portal_pos = self._place_portal()

        # Spawn at least one enemy (reachable from player, not on portal)
        self._spawn_enemies()

    def _is_reachable(self, start: Tuple[int, int], target: Tuple[int, int]) -> bool:
        """
        Lightweight BFS reachability on the tile grid.
        Used locally to avoid depending on validator and to prevent cycles.
        """
        if start == target:
            return True

        height = len(self.grid)
        width = len(self.grid[0]) if height > 0 else 0
        sx, sy = start
        tx, ty = target

        if not (0 <= sx < width and 0 <= sy < height and
                0 <= tx < width and 0 <= ty < height):
            return False
        if self.grid[sy][sx] != 0 or self.grid[ty][tx] != 0:
            return False

        from collections import deque
        q = deque()
        q.append((sx, sy))
        visited = { (sx, sy) }

        while q:
            x, y = q.popleft()
            if (x, y) == (tx, ty):
                return True
            for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                nx, ny = x + dx, y + dy
                if (0 <= nx < width and 0 <= ny < height and
                        self.grid[ny][nx] == 0 and (nx, ny) not in visited):
                    visited.add((nx, ny))
                    q.append((nx, ny))

        return False

    def _place_portal(self) -> Optional[Tuple[int, int]]:
        """
        Select a portal position:
        - On a floor tile inside bounds (not on outer wall ring).
        - Reachable from player spawn using local BFS.
        - Prefer tiles far from player to encourage traversal.
        Returns pixel coordinates (x, y) if successful, else None.
        """
        height = len(self.grid)
        width = len(self.grid[0]) if height > 0 else 0
        if width == 0 or height == 0 or not self.spawn_points:
            return None

        # Player spawn in tile coords derived from authoritative pixel spawn
        spawn_tile_x = self.spawn[0] // TILE
        spawn_tile_y = self.spawn[1] // TILE
        sx, sy = spawn_tile_x, spawn_tile_y
        if not (0 <= sx < width and 0 <= sy < height) or self.grid[sy][sx] != 0:
            return None

        # Collect candidate floor tiles with 1-tile safety margin from border
        candidates: List[Tuple[int, int, int]] = []
        for y in range(1, height - 1):
            for x in range(1, width - 1):
                if self.grid[y][x] == 0:
                    dist = abs(x - sx) + abs(y - sy)
                    candidates.append((dist, x, y))

        if not candidates:
            return None

        # Prefer farthest candidates first
        candidates.sort(reverse=True)

        for _, px, py in candidates:
            if self._is_reachable((sx, sy), (px, py)):
                # Store as pixel coordinates
                return (px * TILE, py * TILE)

        # Fallback: no reachable far candidate found
        return None

    def _spawn_enemies(self) -> None:
        """
        Populate self.enemies with at least one enemy:
        - Only on valid floor tiles.
        - Never on/overlapping player spawn area or portal tile.
        - Must be reachable from player spawn by local BFS.
        - Do not stack enemies on top of each other.
        Keep simple and deterministic; uses a small fixed set of candidates.
        """
        from enemy_entities import Bug  # lightweight, base enemy; avoids complex logic here
        from player_entity import Player

        height = len(self.grid)
        width = len(self.grid[0]) if height > 0 else 0
        if width == 0 or height == 0 or not self.spawn_points:
            return

        # Player spawn tile derived from authoritative pixel spawn
        spawn_tile_x = self.spawn[0] // TILE
        spawn_tile_y = self.spawn[1] // TILE
        spawn_tile = (spawn_tile_x, spawn_tile_y)
        sx, sy = spawn_tile

        # Derive player spawn rect from GeneratedLevel.spawn and Player size
        # self.spawn is top-left pixel position for the player
        player_spawn_x, player_spawn_y = self.spawn
        player_width, player_height = 18, 30  # from Player rect in player_entity.Player.__init__
        player_spawn_rect = pygame.Rect(player_spawn_x, player_spawn_y, player_width, player_height)

        # Inflated safety region around player spawn; used only for spawn rejection checks
        player_safety_rect = player_spawn_rect.inflate(
            PLAYER_SAFETY_PAD_X * 2,
            PLAYER_SAFETY_PAD_Y * 2,
        )

        portal_tile: Optional[Tuple[int, int]] = None
        if self.portal_pos:
            portal_tile = (self.portal_pos[0] // TILE, self.portal_pos[1] // TILE)

        # Gather candidate floor tiles excluding spawn/portal and immediate neighbors of spawn
        candidates: List[Tuple[int, int, int]] = []  # (dist, x, y)

        def is_adjacent_to_spawn(tx: int, ty: int) -> bool:
            # Manhattan distance 1 from spawn tile for safety buffer
            return abs(tx - sx) + abs(ty - sy) == 1

        for y in range(1, height - 1):
            for x in range(1, width - 1):
                if self.grid[y][x] != 0:
                    continue
                if (x, y) == spawn_tile:
                    continue
                if is_adjacent_to_spawn(x, y):
                    continue
                if portal_tile and (x, y) == portal_tile:
                    continue
                dist = abs(x - sx) + abs(y - sy)
                candidates.append((dist, x, y))

        if not candidates:
            return

        # Deterministic order: sort by distance (and then x,y implicitly)
        candidates.sort()

        placed_enemy_rects: List[pygame.Rect] = []
        placed = 0
        max_enemies = max(1, (width * height) // 300)  # simple density-based cap

        for _, ex, ey in candidates:
            if placed >= max_enemies:
                break

            # Ensure reachable from player
            if not self._is_reachable(spawn_tile, (ex, ey)):
                continue

            # Compute Bug-equivalent rect for this tile BEFORE instantiation using canonical footprint
            enemy_width = BUG_WIDTH
            enemy_height = BUG_HEIGHT
            enemy_x = ex * TILE + TILE // 2
            ground_y = (ey + 1) * TILE
            enemy_rect = pygame.Rect(
                enemy_x - enemy_width // 2,
                ground_y - enemy_height,
                enemy_width,
                enemy_height,
            )

            # Padded rect used only for spacing checks between enemies (does not affect physics)
            test_enemy_rect = enemy_rect.inflate(ENEMY_PADDING * 2, 0)

            # Do not spawn overlapping the (inflated) player safety area
            if enemy_rect.colliderect(player_safety_rect):
                continue

            # Do not stack on existing enemies; use padded rect for enforced personal space
            blocked = False
            for r in placed_enemy_rects:
                if test_enemy_rect.colliderect(r):
                    blocked = True
                    break
            if blocked:
                continue

            # Passed all checks; create the enemy and record its rect
            bug = Bug(enemy_x, ground_y)
            self.enemies.append(bug)
            placed_enemy_rects.append(enemy_rect)
            placed += 1

        # Guarantee at least one enemy if any candidate was viable (enforced by loop when possible).


    def draw(self, surf, camera):
        """
        Minimal renderer compatible with Level.draw used by main.py.
        Uses TILE_COL for solids and CYAN for doors/portal indicator.
        """
        from config import TILE_COL, CYAN  # local import to avoid cycles

        for r in self.solids:
            pygame.draw.rect(surf, TILE_COL, camera.to_screen_rect(r), border_radius=6)
        for d in self.doors:
            pygame.draw.rect(surf, CYAN, camera.to_screen_rect(d), width=2)

        # Optional simple portal visualization so it's obvious in debug:
        if self.portal_pos:
            px, py = self.portal_pos
            portal_rect = pygame.Rect(px, py, TILE, TILE)
            pygame.draw.rect(surf, CYAN, camera.to_screen_rect(portal_rect), width=2)

        # Note: enemies draw themselves; this method mirrors level.Level.draw.
        

class LevelGenerator:
    """Main level generation orchestrator"""
    
    def __init__(self, width: int = 40, height: int = 30):
        self.width = width
        self.height = height
        self.seed_manager = SeedManager()
        self.hybrid_generator = HybridGenerator(width, height)
        self.validator = LevelValidator()
        
        # Performance tracking
        self.generation_time_ms = 0
        self.validation_attempts = 0
    
    def generate_level(self, level_index: int, level_type: str = "dungeon", 
                    difficulty: int = 1, seed: Optional[int] = None) -> GeneratedLevel:
        """
        Generate a complete level
        
        Args:
            level_index: Index of level to generate
            level_type: Type of level ("dungeon", "cave", "outdoor", "hybrid")
            difficulty: Difficulty level (1-3)
            seed: Optional seed override
            
        Returns:
            GeneratedLevel instance
        """
        start_time = time.time()
        
        # Set seed if provided
        if seed is not None:
            self.seed_manager.set_world_seed(seed)
        
        # Generate level seed
        level_seed = self.seed_manager.generate_level_seed(level_index)
        
        # Generate sub-seeds
        sub_seeds = self.seed_manager.generate_sub_seeds(level_seed)
        
        # Generate raw level data
        level_data = self.hybrid_generator.generate(level_seed, level_type)
        
        # Apply difficulty modifications
        level_data = self._apply_difficulty(level_data, difficulty)
        
        # Validate and repair if needed
        validated_data = self._validate_and_repair(level_data)
        
        # Generate terrain
        terrain_grid = self._generate_terrain(validated_data, sub_seeds['terrain'])
        
        # Ensure enemy spawn metadata from validation is preserved if present.
        # Validator may attach 'enemy_spawns' for downstream systems.
        enemy_spawns = validated_data.get('enemy_spawns')

        # Create final level
        generated_level = GeneratedLevel(
            validated_data['grid'],
            validated_data['rooms'],
            validated_data['spawn_points'],
            validated_data['type'],
            terrain_grid
        )

        # If validator proposed explicit enemy_spawns structure and game expects it,
        # keep it attached on the GeneratedLevel for compatibility.
        if enemy_spawns is not None:
            setattr(generated_level, 'enemy_spawns', enemy_spawns)
        
        # Track performance
        self.generation_time_ms = (time.time() - start_time) * 1000
        
        return generated_level
    
    def _apply_difficulty(self, level_data: Dict[str, Any], difficulty: int) -> Dict[str, Any]:
        """Apply difficulty modifications to level data"""
        if difficulty == 1:  # Easy
            # Reduce enemy density (will be handled in entity placement)
            # Increase treasure frequency
            # Simplify terrain
            pass  # No modifications for easy
        elif difficulty == 2:  # Normal
            # Standard settings
            pass  # No modifications for normal
        elif difficulty == 3:  # Hard
            # Increase enemy density
            # Add more complex terrain
            # Reduce open space
            grid = level_data['grid']
            if grid:
                # Add some extra walls for complexity
                for _ in range(int(len(grid) * len(grid[0]) * 0.05)):  # 5% extra walls
                    y = self.seed_manager.get_random('terrain').randint(1, len(grid) - 2)
                    x = self.seed_manager.get_random('terrain').randint(1, len(grid[0]) - 2)
                    grid[y][x] = 1  # Wall
                
                level_data['grid'] = grid
        
        return level_data
    
    def _validate_and_repair(self, level_data: Dict[str, Any]) -> Dict[str, Any]:
        """Validate and repair level if needed"""
        max_attempts = 3
        current_data = level_data.copy()
        
        # Ensure we have all required fields for the validator
        if 'enemies' not in current_data:
            current_data['enemies'] = []
        if 'portal_pos' not in current_data:
            current_data['portal_pos'] = None
        
        for attempt in range(max_attempts):
            self.validation_attempts += 1
            
            # Validate current data
            result = self.validator.validate(current_data)
            
            if result.is_valid:
                return current_data
            
            # Try to repair issues
            if attempt < max_attempts - 1:
                current_data = self.validator.repair_level(current_data, result)
                # Update portal position from repaired data if it exists
                if 'portal_pos' in current_data:
                    level_data['portal_pos'] = current_data['portal_pos']
        
        # If all attempts failed, return original data
        return level_data
    
    def _generate_terrain(self, level_data: Dict[str, Any], terrain_seed: int) -> List[List[str]]:
        """Generate terrain for the level"""
        grid = level_data.get('grid', [])
        level_type = level_data.get('type', 'dungeon')
        
        if not grid:
            return []
        
        terrain_rng = self.seed_manager.get_random('terrain')
        terrain_rng.seed(terrain_seed)
        
        terrain_grid = []
        
        for y, row in enumerate(grid):
            terrain_row = []
            for x, tile in enumerate(row):
                if tile == 1:  # Wall
                    # Apply terrain variation to walls
                    terrain_type = self._select_wall_terrain(x, y, level_type, terrain_rng)
                    terrain_row.append(terrain_type.value)
                else:  # Floor
                    # Apply terrain variation to floors
                    terrain_type = self._select_floor_terrain(x, y, level_type, terrain_rng)
                    terrain_row.append(terrain_type.value)
            terrain_grid.append(terrain_row)
        
        return terrain_grid
    
    def _select_wall_terrain(self, x: int, y: int, level_type: str, rng) -> TerrainType:
        """Select terrain type for wall tiles"""
        if level_type == "dungeon":
            # Mix of normal and rough terrain
            if rng.random() < 0.8:
                return TerrainType.NORMAL
            else:
                return TerrainType.ROUGH
        elif level_type == "cave":
            # More rough terrain
            if rng.random() < 0.6:
                return TerrainType.ROUGH
            elif rng.random() < 0.8:
                return TerrainType.STEEP
            else:
                return TerrainType.NORMAL
        elif level_type == "outdoor":
            # More varied terrain
            rand = rng.random()
            if rand < 0.3:
                return TerrainType.NORMAL
            elif rand < 0.5:
                return TerrainType.ROUGH
            elif rand < 0.7:
                return TerrainType.MUD
            elif rand < 0.85:
                return TerrainType.WATER
            else:
                return TerrainType.ICE
        else:  # hybrid
            # Mix of all types
            rand = rng.random()
            if rand < 0.5:
                return TerrainType.NORMAL
            elif rand < 0.7:
                return TerrainType.ROUGH
            elif rand < 0.85:
                return TerrainType.STEEP
            else:
                return TerrainType.DESTRUCTIBLE
    
    def _select_floor_terrain(self, x: int, y: int, level_type: str, rng) -> TerrainType:
        """Select terrain type for floor tiles"""
        if level_type == "dungeon":
            # Mostly normal with some variation
            if rng.random() < 0.9:
                return TerrainType.NORMAL
            else:
                return TerrainType.ROUGH
        elif level_type == "cave":
            # More rough and steep
            if rng.random() < 0.4:
                return TerrainType.NORMAL
            elif rng.random() < 0.7:
                return TerrainType.ROUGH
            elif rng.random() < 0.9:
                return TerrainType.STEEP
            else:
                return TerrainType.MUD
        elif level_type == "outdoor":
            # Natural terrain
            rand = rng.random()
            if rand < 0.6:
                return TerrainType.NORMAL
            elif rand < 0.8:
                return TerrainType.ROUGH
            else:
                return TerrainType.MUD
        else:  # hybrid
            # Balanced mix
            rand = rng.random()
            if rand < 0.7:
                return TerrainType.NORMAL
            elif rand < 0.85:
                return TerrainType.ROUGH
            else:
                return TerrainType.STEEP
    
    def get_generation_stats(self) -> Dict[str, Any]:
        """Get statistics about last generation"""
        return {
            'generation_time_ms': self.generation_time_ms,
            'validation_attempts': self.validation_attempts,
            'world_seed': self.seed_manager.get_world_seed(),
            'seed_info': self.seed_manager.get_seed_info()
        }
    
    def set_world_seed(self, seed: int):
        """Set the world seed for deterministic generation"""
        self.seed_manager.set_world_seed(seed)
    
    def get_world_seed(self) -> int:
        """Get the current world seed"""
        return self.seed_manager.get_world_seed()


# Integration function for existing game
def generate_procedural_level(level_index: int, level_type: str = "dungeon", 
                           difficulty: int = 1, seed: Optional[int] = None) -> GeneratedLevel:
    """
    Convenience function for generating levels
    
    Args:
        level_index: Index of level to generate
        level_type: Type of level ("dungeon", "cave", "outdoor", "hybrid")
        difficulty: Difficulty level (1-3)
        seed: Optional seed override
        
    Returns:
        GeneratedLevel instance compatible with existing game
    """
    generator = LevelGenerator()
    return generator.generate_level(level_index, level_type, difficulty, seed)