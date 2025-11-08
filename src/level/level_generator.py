"""
Level Generator - Main orchestrator for procedural level generation
"""

import time
from typing import Dict, List, Tuple, Optional, Any
import pygame

from config import TILE, TILE_AIR, TILE_FLOOR, TILE_WALL, TILE_SOLID, TILE_COLORS
from .seed_manager import SeedManager
from .generation_algorithms import HybridGenerator
from .level_validator import LevelValidator
from .terrain_system import TerrainTypeRegistry, TerrainBaseType, init_defaults as init_terrain_defaults
from .area_system import AreaMap, AreaType, AreaRegistry, build_default_areas, init_defaults as init_area_defaults
from .area_builder import build_enhanced_areas

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
                 level_type: str,
                 terrain_grid: Optional[List[List[str]]] = None,
                 areas: Optional[AreaMap] = None):
        """
        terrain_grid:
            2D list of terrain_id strings. If None, a trivial mapping is created.
        areas:
            AreaMap describing logical areas (spawn zones, portal zone, water, etc.).
            Optional for backward compatibility.
        """
        self.grid = grid
        self.rooms = rooms
        self.spawn_points = spawn_points
        self.level_type = level_type
        self.terrain_grid = terrain_grid or self._create_default_terrain(grid)
        self.areas: AreaMap = areas or AreaMap()
        
        # Core gameplay/physics data expected by the game
        self.solids: List[pygame.Rect] = []
        self.enemies: List = []
        self.doors: List[pygame.Rect] = []
        self.spawn: Tuple[int, int] = (TILE * 2, TILE * 2)

        # Portal position in pixel coordinates (x, y)
        self.portal_pos: Optional[Tuple[int, int]] = None

        # Meta
        self.is_procedural: bool = True
        self.level_type: str = level_type
        self.level_index: int = 0  # Will be set later via setattr

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
        """
        Create a default terrain grid from level grid.

        This uses TerrainTypeRegistry defaults:
        - Walls (2) -> "wall_solid"
        - Floors (1) -> "floor_normal"
        - Solid (3) -> "ceiling_solid"
        - Air (0) -> "floor_normal" (for backward compatibility)
        """
        # Ensure defaults are initialized (idempotent).
        init_terrain_defaults()

        terrain_grid: List[List[str]] = []
        for row in grid:
            terrain_row: List[str] = []
            for tile in row:
                if tile == TILE_WALL:
                    terrain_row.append("wall_solid")
                elif tile == TILE_FLOOR:
                    terrain_row.append("floor_normal")
                elif tile == TILE_SOLID:
                    terrain_row.append("ceiling_solid")
                else:  # TILE_AIR or unknown
                    terrain_row.append("floor_normal")
            terrain_grid.append(terrain_row)
        return terrain_grid
    
    def _validate_terrain_support(self, x: int, y: int, entity_width: int, entity_height: int,
                                entity_name: str = "Entity") -> Tuple[bool, List[str]]:
        """
        Validate that an entity has adequate multi-tile terrain support under its bottom area.

        Hard design requirements (confirmed):
        - Entity must stand on platform-like tiles (grid == TILE_FLOOR and TerrainTypeRegistry.is_platform_like).
        - Beneath those tiles there must be a real supporting column, not a thin ledge:
          * For all non-flying entities (including Player), require at least 2 tiles of
            structural support depth (either:
              - platform/floor base terrain, or
              - a solid collision tile in (TILE_WALL, TILE_SOLID))
            directly below the standing tiles.
        """
        from .terrain_system import TerrainTypeRegistry, TerrainBaseType

        height = len(self.grid)
        width = len(self.grid[0]) if height > 0 else 0
        issues: List[str] = []

        # Convert pixel coordinates to tile coordinates
        left_tile = x // TILE
        right_tile = (x + entity_width - 1) // TILE  # Inclusive
        bottom_tile = (y + entity_height - 1) // TILE  # Tile where entity's feet touch

        # Check bounds
        if not (0 <= left_tile < width and 0 <= right_tile < width and 0 <= bottom_tile < height):
            issues.append(f"{entity_name}: Out of bounds")
            return False, issues

        def is_platform_like_floor(tx: int, ty: int) -> bool:
            """
            Standing tile must:
            - be floor in collision grid (TILE_FLOOR)
            - and terrain base must be platform-like.
            """
            if not (0 <= tx < width and 0 <= ty < height):
                return False
            if self.grid[ty][tx] != TILE_FLOOR:
                return False
            if hasattr(self, "terrain_grid") and self.terrain_grid:
                tid = self.terrain_grid[ty][tx]
                tag = TerrainTypeRegistry.get_terrain(tid) if isinstance(tid, str) else tid
                if tag is None:
                    return False
                return TerrainTypeRegistry.is_platform_like(tag)
            # If no terrain grid provided, treat floor as platform-like by default.
            return True

        def has_structural_support_column(tx: int, start_y: int, required_depth: int) -> bool:
            """
            Require a continuous column of support of length required_depth starting
            immediately below start_y (exclusive). Each supporting tile may be:
            - A solid collision tile (grid == 1), or
            - A terrain tile whose base_type is FLOOR or PLATFORM.
            """
            for dy in range(1, required_depth + 1):
                sy = start_y + dy
                if not (0 <= sy < height):
                    return False
                # Solid collision counts as support.
                if self.grid[sy][tx] in (TILE_WALL, TILE_SOLID):
                    continue
                # Otherwise, check terrain semantics.
                if hasattr(self, "terrain_grid") and self.terrain_grid:
                    tid = self.terrain_grid[sy][tx]
                    tag = TerrainTypeRegistry.get_terrain(tid) if isinstance(tid, str) else tid
                    if tag and tag.base_type in (TerrainBaseType.FLOOR, TerrainBaseType.PLATFORM):
                        continue
                # No valid support at this depth.
                return False
            return True

        # 1) Standing band: every tile under the feet must be platform-like floor.
        for tx in range(left_tile, right_tile + 1):
            if not is_platform_like_floor(tx, bottom_tile):
                issues.append(f"{entity_name}: No platform-like floor at ({tx}, {bottom_tile})")

        # 2) Structural support: enforce multi-tile depth for non-flying entities.
        #    Flying entities are exempt; they can hover.
        if entity_name != "FlyingEnemy":
            # Require at least 2 tiles of depth where possible; clamp by bounds.
            required_depth = min(2, max(0, height - bottom_tile - 1))
            if required_depth <= 0:
                issues.append(f"{entity_name}: Not enough space below for required support depth at row {bottom_tile}")
            else:
                for tx in range(left_tile, right_tile + 1):
                    if not has_structural_support_column(tx, bottom_tile, required_depth):
                        issues.append(
                            f"{entity_name}: Insufficient support depth under column {tx} starting at row {bottom_tile}"
                        )

        # Removed debug spam - validation failures are handled by fallback systems

        return len(issues) == 0, issues

    def _process_level(self):
        """Process generated level into game-compatible format.

        Guarantees:
        - Player spawn:
            - Only placed on walkable floor tiles (grid == TILE_FLOOR).
            - Prefer tiles inside AreaType.PLAYER_SPAWN areas if provided.
        - Enemy spawns:
            - Never inside PLAYER_SPAWN areas or overlapping the player safety zone.
        """
        from .area_system import AreaType  # local import to avoid cycles

        height = len(self.grid)
        width = len(self.grid[0]) if height > 0 else 0

        # Convert grid to solid rectangles
        for y, row in enumerate(self.grid):
            for x, tile in enumerate(row):
                # Create collision rectangles for solid tiles (walls and solid tiles)
                if tile in (TILE_WALL, TILE_SOLID):
                    rect = pygame.Rect(x * TILE, y * TILE, TILE, TILE)
                    self.solids.append(rect)

        # Compute helper: tiles that belong to PLAYER_SPAWN areas (if any)
        player_spawn_area_tiles = set()
        if hasattr(self, "areas") and self.areas:
            try:
                spawn_areas = self.areas.find_areas_by_type(getattr(AreaType, "PLAYER_SPAWN", "PLAYER_SPAWN"))
                for a in spawn_areas:
                    for tx, ty in a.tiles():
                        if 0 <= tx < width and 0 <= ty < height:
                            player_spawn_area_tiles.add((tx, ty))
            except Exception:
                # Defensive: area issues must not break generation.
                player_spawn_area_tiles = set()

        # Initialize terrain registry for validation
        init_terrain_defaults()

        def is_platform_terrain(x: int, y: int) -> bool:
            """Check if tile at (x, y) is platform-like terrain."""
            if not (0 <= y < height and 0 <= x < width):
                return False
            # Check collision grid - floor tiles (1) are walkable
            tile = self.grid[y][x]
            if tile != TILE_FLOOR:
                return False
            # Then check terrain grid is platform-like
            if hasattr(self, 'terrain_grid') and self.terrain_grid:
                terrain_id = self.terrain_grid[y][x]
                if isinstance(terrain_id, str):
                    terrain_tag = TerrainTypeRegistry.get_terrain(terrain_id)
                else:
                    terrain_tag = terrain_id
                return TerrainTypeRegistry.is_platform_like(terrain_tag)
            # If no terrain grid, assume floor is platform-like
            return True

        def has_2x2_direct_support(tx: int, ty: int) -> bool:
            """
            Stricter grounding rule for player spawn tiles:

            - (tx, ty) is interpreted as the FLOOR tile directly under the player's feet band.
            - Require a 2x2 block of platform-like tiles at (tx, ty) and (tx+1, ty)
              that are directly touching the spawn band (no gaps).
            - Additionally, require that directly below those tiles (ty+1) we either:
                * have PLATFORM/FLOOR base terrain, or
                * have a solid collision tile (grid == 1)
              so we never treat a thin ledge over pure void as a valid spawn band.
            """
            # Check in-bounds for 2x2 footprint (two tiles wide, one tile tall band, plus support below)
            if not (0 <= tx < width - 1 and 0 <= ty < height - 1):
                return False

            # Top row: both tiles must be platform terrain the player can stand on
            if not (is_platform_terrain(tx, ty) and is_platform_terrain(tx + 1, ty)):
                return False

            # Direct support row: ensure the tiles directly beneath provide real support
            support_y = ty + 1
            for sx in (tx, tx + 1):
                if not (0 <= support_y < height):
                    return False

                # Prefer terrain semantics when available
                supported = False
                if hasattr(self, "terrain_grid") and self.terrain_grid:
                    tid = self.terrain_grid[support_y][sx]
                    tag = TerrainTypeRegistry.get_terrain(tid) if isinstance(tid, str) else tid
                    if tag and tag.base_type in (TerrainBaseType.PLATFORM, TerrainBaseType.FLOOR):
                        supported = True

                # Fallback: grid solid counts as structural support
                if not supported and self.grid[support_y][sx] in (TILE_WALL, TILE_SOLID):
                    supported = True

                if not supported:
                    return False

            return True

        # Store terrain registry for enemy spawning
        self._terrain_registry = TerrainTypeRegistry

        # Set spawn point in pixels:
        # - Prefer first spawn_point that is on platform-like terrain.
        # - If PLAYER_SPAWN areas exist, restrict to tiles within those areas.
        # - Fallback: any valid platform-like spawn_point.
        # - Final rule for feel: spawn the player so feet rest exactly on the platform tile
        #   (never floating above PLAYER_SPAWN band).
        if self.spawn_points:
            chosen = None

            # 1) Prefer spawn points that lie inside a PLAYER_SPAWN area AND satisfy strict 2x2 support.
            #    Interpret (sx, sy) as the FLOOR tile directly under the player's feet band.
            if player_spawn_area_tiles:
                for sx, sy in self.spawn_points:
                    if (sx, sy) in player_spawn_area_tiles and has_2x2_direct_support(sx, sy):
                        chosen = (sx, sy)
                        break

            # 2) Otherwise, pick first spawn point that meets 2x2 support (even if not flagged as PLAYER_SPAWN).
            if chosen is None:
                for sx, sy in self.spawn_points:
                    if has_2x2_direct_support(sx, sy):
                        chosen = (sx, sy)
                        break

            # 3) Fallback: search for any platform-like terrain tile near spawn points
            if chosen is None:
                for sx, sy in self.spawn_points:
                    for dx in range(-2, 3):
                        for dy in range(-2, 3):
                            tx, ty = sx + dx, sy + dy
                            if is_platform_terrain(tx, ty):
                                chosen = (tx, ty)
                                break
                        if chosen:
                            break

            # 4) Last resort: scan entire map bottom-up for any tile with 2x2 support.
            if chosen is None:
                for ty in range(height - 2, 0, -1):
                    for tx in range(1, width - 2):
                        if has_2x2_direct_support(tx, ty):
                            chosen = (tx, ty)
                            break
                    if chosen is not None:
                        break

            strict_spawn = None

            # Run STRICT validation on chosen candidate (full support check)
            if chosen:
                sx, sy = chosen

                # Interpret (sx, sy) as the floor tile at the BOTTOM of the PLAYER_SPAWN band:
                # Player feet must rest exactly on top of this tile.
                spawn_x = sx * TILE
                spawn_y = (sy + 1) * TILE - 30  # 30 = player height

                is_valid, issues = self._validate_terrain_support(
                    spawn_x,
                    spawn_y,
                    18,  # Player width
                    30,  # Player height
                    "Player"
                )

                if is_valid:
                    strict_spawn = (spawn_x, spawn_y)
                    self.spawn = strict_spawn

            # RELAXED but SAFE fallback when strict spawn not found
            # IMPORTANT:
            # - All relaxed candidates MUST pass the same multi-depth validation used by strict spawn.
            # - has_direct_support now only pre-filters obvious non-candidates; final check uses
            #   _validate_terrain_support to enforce 2+ tile deep support.
            if strict_spawn is None:
                def has_direct_support(tx: int, ty: int) -> bool:
                    """
                    Cheap pre-check before full _validate_terrain_support:

                    - Require at least 2-wide platform-like band at (tx, ty) and (tx+1, ty)
                      for the player's feet.
                    - Quickly ensure there is at least 1 row below within bounds (full depth
                      validation is delegated to _validate_terrain_support).
                    """
                    if not (0 <= tx < width - 1 and 0 <= ty < height - 1):
                        return False
                    if not (is_platform_terrain(tx, ty) and is_platform_terrain(tx + 1, ty)):
                        return False
                    return True  # Detailed deep support is checked later.

                relaxed_spawn = None

                # Helper to validate and set a relaxed spawn candidate in pixels.
                def _try_set_relaxed_spawn_from_tile(tx: int, ty: int) -> Optional[Tuple[int, int]]:
                    """
                    Convert (tx, ty) candidate into pixel spawn and run full terrain validation.
                    Returns (spawn_x, spawn_y) if valid, else None.
                    """
                    spawn_x = tx * TILE
                    spawn_y = (ty + 1) * TILE - 30  # feet on top of tile ty
                    ok, issues = self._validate_terrain_support(
                        spawn_x,
                        spawn_y,
                        18,
                        30,
                        "Player",
                    )
                    if ok:
                        return (spawn_x, spawn_y)
                return None

                # a) Try PLAYER_SPAWN tiles first (sorted bottom-up/left-to-right)
                if player_spawn_area_tiles:
                    for (tx, ty) in sorted(player_spawn_area_tiles, key=lambda p: (p[1], p[0]), reverse=True):
                        if 0 <= tx < width and 0 <= ty < height and self.grid[ty][tx] == TILE_FLOOR:
                            if has_direct_support(tx, ty):
                                candidate = _try_set_relaxed_spawn_from_tile(tx, ty)
                                if candidate:
                                    relaxed_spawn = candidate
                                    print(f"[SPAWN] Relaxed fallback using PLAYER_SPAWN area bottom tile ({tx}, {ty})")
                                    break

                # b) Around original spawn_points in small radius
                if relaxed_spawn is None and self.spawn_points:
                    for sx, sy in self.spawn_points:
                        for dy in range(-4, 5):
                            for dx in range(-4, 5):
                                tx, ty = sx + dx, sy + dy
                                if 0 <= tx < width and 0 <= ty < height and self.grid[ty][tx] == TILE_FLOOR:
                                    if has_direct_support(tx, ty):
                                        candidate = _try_set_relaxed_spawn_from_tile(tx, ty)
                                        if candidate:
                                            relaxed_spawn = candidate
                                            print(f"[SPAWN] Relaxed fallback near spawn_points at ({tx}, {ty})")
                                            break
                            if relaxed_spawn is not None:
                                break
                        if relaxed_spawn is not None:
                            break

                # c) Global bottom-up scan for any safe tile (more robust than giving up)
                if relaxed_spawn is None:
                    for ty in range(height - 2, 0, -1):
                        for tx in range(1, width - 1):
                            if self.grid[ty][tx] == TILE_FLOOR and has_direct_support(tx, ty):
                                candidate = _try_set_relaxed_spawn_from_tile(tx, ty)
                                if candidate:
                                    relaxed_spawn = candidate
                                    print(f"[SPAWN] Global relaxed fallback chose ({tx}, {ty})")
                                    break
                        if relaxed_spawn is not None:
                            break

                if relaxed_spawn is not None:
                    self.spawn = relaxed_spawn
                else:
                    # Absolute last guard: clamp existing spawn inside bounds so it cannot be OOB.
                    clamped_x = max(0, min(self.spawn[0], (width - 2) * TILE))
                    # Clamp Y but also snap so player feet are above bottom bound.
                    clamped_bottom = max(1, min((height - 1) * TILE, self.spawn[1] + 30))
                    clamped_y = clamped_bottom - 30
                    self.spawn = (clamped_x, clamped_y)
                    print(f"[SPAWN] CRITICAL: No valid strict/relaxed spawn found; using clamped in-bounds fallback {self.spawn}")

        # Place portal strictly inside a PORTAL_ZONE area if available and reachable.
        self.portal_pos = self._place_portal()

        # Spawn at least one enemy (reachable from player, not on portal, and not in PLAYER_SPAWN areas)
        self._spawn_enemies(player_spawn_area_tiles=player_spawn_area_tiles)

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
        # Check if both start and target are floor tiles (walkable)
        if self.grid[sy][sx] != TILE_FLOOR or self.grid[ty][tx] != TILE_FLOOR:
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
                        self.grid[ny][nx] == TILE_FLOOR and (nx, ny) not in visited):
                    visited.add((nx, ny))
                    q.append((nx, ny))

        return False

    def _place_portal(self) -> Optional[Tuple[int, int]]:
        """
        Select a portal position:

        - Prefer tiles inside AreaType.PORTAL_ZONE areas when defined.
        - Otherwise, fall back to legacy behavior: any interior floor tile.
        - Must be on a floor tile (grid == TILE_FLOOR).
        - Must be reachable from player spawn via local BFS.
        - Prefer tiles far from player.

        Returns pixel coordinates (x, y) if successful, else None.
        """
        height = len(self.grid)
        width = len(self.grid[0]) if height > 0 else 0
        if width == 0 or height == 0 or not self.spawn_points:
            return None

        # Player spawn tile from authoritative pixel spawn
        spawn_tile_x = self.spawn[0] // TILE
        spawn_tile_y = self.spawn[1] // TILE
        sx, sy = spawn_tile_x, spawn_tile_y
        if not (0 <= sx < width and 0 <= sy < height):
            return None
        if self.grid[sy][sx] != TILE_FLOOR:
            return None

        candidates: List[Tuple[int, int, int]] = []

        def is_valid_portal_tile(tx: int, ty: int) -> bool:
            if not (0 <= tx < width and 0 <= ty < height):
                return False
            # Must be floor tile in grid; tests/validator expect this.
            if self.grid[ty][tx] != TILE_FLOOR:
                return False
            return True

        # Prefer tiles inside PORTAL_ZONE areas if any exist.
        portal_zones = self.areas.find_areas_by_type(getattr(AreaType, "PORTAL_ZONE", "PORTAL_ZONE"))
        if portal_zones:
            for zone in portal_zones:
                for tx, ty in zone.tiles():
                    if is_valid_portal_tile(tx, ty):
                        dist = abs(tx - sx) + abs(ty - sy)
                        candidates.append((dist, tx, ty))

        # Fallback: legacy behavior across all interior floor tiles if no zone candidates.
        if not candidates:
            for y in range(1, height - 1):
                for x in range(1, width - 1):
                    if is_valid_portal_tile(x, y):
                        dist = abs(x - sx) + abs(y - sy)
                        candidates.append((dist, x, y))

        if not candidates:
            return None

        # Prefer farthest distance first
        candidates.sort(reverse=True)

        for _, px, py in candidates:
            if self._is_reachable((sx, sy), (px, py)):
                # Portal should sit on top of the tile like ground entities
                # Portals are typically 32x32 pixels (same as TILE size)
                portal_x = px * TILE
                portal_y = py * TILE  # Top of tile, portal sits on this tile
                portal_height = TILE

                is_valid, issues = self._validate_terrain_support(
                    portal_x,
                    portal_y,
                    TILE,  # Portal width
                    portal_height,  # Portal height
                    "Portal"
                )

                if is_valid:
                    return (portal_x, portal_y)
                else:
                    # Skip this location due to insufficient terrain support
                    continue

        return None

    def _spawn_enemies(self, player_spawn_area_tiles: Optional[set] = None) -> None:
        """
        Populate self.enemies with at least one enemy:

        Constraints:
        - Only on valid floor tiles.
        - Never on/overlapping player spawn tile.
        - Never inside PLAYER_SPAWN areas (player-safe zone).
        - Never overlapping the player safety rect.
        - Never on portal tile.
        - Must be reachable from player spawn by local BFS.
        - Do not stack enemies on top of each other.
        Keep simple and deterministic; uses a small fixed set of candidates.
        """
        from ..entities.enemy_entities import Bug, Frog, Archer, WizardCaster, Assassin, Bee, Golem, Boss
        from .area_system import AreaType
        from .level_progression import LevelProgress

        if player_spawn_area_tiles is None:
            player_spawn_area_tiles = set()

        height = len(self.grid)
        width = len(self.grid[0]) if height > 0 else 0
        if width == 0 or height == 0 or not self.spawn_points:
            return

        # Player spawn tile (from authoritative pixel spawn)
        spawn_tile_x = self.spawn[0] // TILE
        spawn_tile_y = self.spawn[1] // TILE
        spawn_tile = (spawn_tile_x, spawn_tile_y)
        sx, sy = spawn_tile

        # Safety rect around player spawn
        player_spawn_x, player_spawn_y = self.spawn
        player_width, player_height = 18, 30
        player_spawn_rect = pygame.Rect(player_spawn_x, player_spawn_y, player_width, player_height)
        player_safety_rect = player_spawn_rect.inflate(
            PLAYER_SAFETY_PAD_X * 2,
            PLAYER_SAFETY_PAD_Y * 2,
        )

        portal_tile: Optional[Tuple[int, int]] = None
        if self.portal_pos:
            portal_tile = (self.portal_pos[0] // TILE, self.portal_pos[1] // TILE)

        # Get enemy spawn areas
        ground_enemy_areas = self.areas.find_areas_by_type(AreaType.GROUND_ENEMY_SPAWN)
        flying_enemy_areas = self.areas.find_areas_by_type(AreaType.FLYING_ENEMY_SPAWN)

        # Create sets of valid spawn tiles for each area type
        ground_spawn_tiles = set()
        flying_spawn_tiles = set()

        for area in ground_enemy_areas:
            for tile in area.tiles():
                ground_spawn_tiles.add(tile)

        for area in flying_enemy_areas:
            for tile in area.tiles():
                flying_spawn_tiles.add(tile)

        # Get level progression and enemy pool
        level_progress = LevelProgress()
        level_type = getattr(self, 'level_type', 'dungeon')  # Default to dungeon if not set
        level_index = getattr(self, 'level_index', 0)

        enemy_config = level_progress.get_enemy_spawn_config(level_index, level_type)
        available_enemies = enemy_config.get('enemy_types', ['Bug'])

        # Separate enemies by ground/flying
        ground_enemies = ['Bug', 'Frog', 'Archer', 'Assassin', 'Golem', 'Boss']
        flying_enemies = ['Bee', 'WizardCaster']

        available_ground = [e for e in available_enemies if e in ground_enemies]
        available_flying = [e for e in available_enemies if e in flying_enemies]

        # Enemy class mapping
        enemy_classes = {
            'Bug': Bug,
            'Frog': Frog,
            'Archer': Archer,
            'WizardCaster': WizardCaster,
            'Assassin': Assassin,
            'Bee': Bee,
            'Golem': Golem,
            'Boss': Boss
        }

        # Enemy size mapping
        enemy_sizes = {
            'Bug': (28, 22),
            'Frog': (28, 22),
            'Archer': (28, 22),
            'WizardCaster': (28, 22),
            'Assassin': (28, 22),
            'Bee': (24, 20),
            'Golem': (56, 44),
            'Boss': (64, 48)
        }

        # Collect candidates for each area type
        ground_candidates: List[Tuple[int, int, int]] = []
        flying_candidates: List[Tuple[int, int, int]] = []

        def is_adjacent_to_spawn(tx: int, ty: int) -> bool:
            return abs(tx - sx) + abs(ty - sy) == 1

        # Find valid spawn positions in appropriate areas
        for y in range(1, height - 1):
            for x in range(1, width - 1):
                if self.grid[y][x] != TILE_FLOOR:
                    continue
                # Check terrain validity based on enemy type
                if hasattr(self, 'terrain_grid') and self.terrain_grid:
                    terrain_id = self.terrain_grid[y][x]
                    if isinstance(terrain_id, str):
                        terrain_tag = TerrainTypeRegistry.get_terrain(terrain_id)
                    else:
                        terrain_tag = terrain_id

                    # Skip solid walls for all enemy types
                    if terrain_tag and terrain_tag.base_type == TerrainBaseType.WALL:
                        continue

                if (x, y) == spawn_tile:
                    continue
                if is_adjacent_to_spawn(x, y):
                    continue
                if portal_tile and (x, y) == portal_tile:
                    continue
                if (x, y) in player_spawn_area_tiles:
                    continue

                # Check reachability
                if not self._is_reachable(spawn_tile, (x, y)):
                    continue

                dist = abs(x - sx) + abs(y - sy)

                # Add to appropriate candidate list based on area
                if (x, y) in ground_spawn_tiles and available_ground:
                    ground_candidates.append((dist, x, y))
                elif (x, y) in flying_spawn_tiles and available_flying:
                    flying_candidates.append((dist, x, y))

        # Sort candidates by distance (closest first)
        ground_candidates.sort()
        flying_candidates.sort()

        # Combine candidates, preferring ground spawns
        all_candidates = ground_candidates + flying_candidates

        if not all_candidates:
            return

        placed_enemy_rects: List[pygame.Rect] = []
        placed = 0
        max_enemies = enemy_config.get('total_enemies', max(1, (width * height) // 300))

        # Create a rotating enemy selection with some deterministic randomness
        import random as rand
        # Create deterministic seed from level info
        seed_value = hash(f"{level_index}_{level_type}_spawn")
        rand.seed(seed_value)

        enemy_rotation = []
        if available_ground:
            rand.shuffle(available_ground)
            enemy_rotation.extend([(e, 'ground') for e in available_ground])
        if available_flying:
            rand.shuffle(available_flying)
            enemy_rotation.extend([(e, 'flying') for e in available_flying])

        if not enemy_rotation:
            enemy_rotation = [('Bug', 'ground')]  # Fallback

        rotation_index = rand.randint(0, max(0, len(enemy_rotation) - 1))

        for _, ex, ey in all_candidates:
            if placed >= max_enemies:
                break

            # Determine if this is a ground or flying spawn position
            is_ground_spawn = (ex, ey) in ground_spawn_tiles
            is_flying_spawn = (ex, ey) in flying_spawn_tiles

            # Select appropriate enemy type
            if is_ground_spawn and available_ground:
                enemy_type = available_ground[placed % len(available_ground)]
            elif is_flying_spawn and available_flying:
                enemy_type = available_flying[placed % len(available_flying)]
            else:
                # Fallback to rotation
                enemy_type, spawn_type = enemy_rotation[rotation_index % len(enemy_rotation)]
                rotation_index += 1
                if spawn_type == 'ground' and not is_ground_spawn:
                    continue
                if spawn_type == 'flying' and not is_flying_spawn:
                    continue

            # Get enemy class and size
            enemy_class = enemy_classes.get(enemy_type, Bug)
            enemy_width, enemy_height = enemy_sizes.get(enemy_type, (28, 22))

            # Position enemies differently based on type
            is_flying_enemy = enemy_type in flying_enemies
            if is_flying_enemy:
                # Flying enemies spawn in the air, within the tile space
                enemy_x = ex * TILE + TILE // 2
                enemy_y = ey * TILE + TILE // 2  # Center of tile
            else:
                # Ground enemies spawn on the ground
                enemy_x = ex * TILE + TILE // 2
                enemy_y = ey * TILE + TILE - enemy_height  # On top of tile

                # Apply comprehensive terrain validation for ground enemies
                is_valid, issues = self._validate_terrain_support(
                    enemy_x - enemy_width // 2,  # Entity top-left x
                    enemy_y - enemy_height,       # Entity top-left y
                    enemy_width,
                    enemy_height,
                    f"GroundEnemy_{enemy_type}"
                )

                if not is_valid:
                    # Skip this spawn location due to insufficient terrain support
                    continue

            enemy_rect = pygame.Rect(
                enemy_x - enemy_width // 2,
                enemy_y - enemy_height,
                enemy_width,
                enemy_height,
            )
            test_enemy_rect = enemy_rect.inflate(ENEMY_PADDING * 2, 0)

            # Do not overlap player safety zone
            if enemy_rect.colliderect(player_safety_rect):
                continue

            # Check collision with walls
            if hasattr(self, 'grid'):
                # Check all tiles that the enemy's rect would overlap
                left_tile = max(0, enemy_rect.left // TILE)
                right_tile = min(len(self.grid[0]) - 1, enemy_rect.right // TILE)
                top_tile = max(0, enemy_rect.top // TILE)
                bottom_tile = min(len(self.grid) - 1, enemy_rect.bottom // TILE)

                wall_collision = False
                for check_y in range(top_tile, bottom_tile + 1):
                    for check_x in range(left_tile, right_tile + 1):
                        if self.grid[check_y][check_x] != 0:  # Not a floor tile
                            wall_collision = True
                            break
                    if wall_collision:
                        break
                if wall_collision:
                    continue

            # Do not overlap previously placed enemies
            blocked = False
            for r in placed_enemy_rects:
                if test_enemy_rect.colliderect(r):
                    blocked = True
                    break
            if blocked:
                continue

            # Spawn enemy
            enemy = enemy_class(enemy_x, enemy_y)
            enemy.x = float(enemy.rect.centerx)
            enemy.y = float(enemy.rect.bottom)

            self.enemies.append(enemy)
            placed_enemy_rects.append(enemy_rect)
            placed += 1

        # If for some reason none were placed but candidates existed, place one safe fallback.
        if not self.enemies and all_candidates:
            # Pick the first candidate that still respects area/safety constraints.
            for _, ex, ey in all_candidates:
                enemy_x = ex * TILE + TILE // 2
                ground_y = (ey + 1) * TILE

                # Use a Bug as fallback
                enemy_width, enemy_height = enemy_sizes['Bug']
                enemy_rect = pygame.Rect(
                    enemy_x - enemy_width // 2,
                    ground_y - enemy_height,
                    enemy_width,
                    enemy_height,
                )
                if enemy_rect.colliderect(player_safety_rect):
                    continue

                bug = Bug(enemy_x, ground_y)
                bug.x = float(bug.rect.centerx)
                bug.y = float(bug.rect.bottom)
                self.enemies.append(bug)
                break


    def draw(self, surf, camera):
        """
        Enhanced renderer that draws tiles based on their type.
        Uses different colors for floors, walls, and solid tiles.
        """
        from config import TILE_COLORS, CYAN  # local import to avoid cycles
        from src.utils.tile_utils import should_render_tile, get_tile_color

        # Draw tiles based on grid if available (for generated levels)
        if hasattr(self, 'grid'):
            for y, row in enumerate(self.grid):
                for x, tile in enumerate(row):
                    if should_render_tile(tile):
                        color = get_tile_color(tile)
                        if color:
                            tile_rect = pygame.Rect(x * TILE, y * TILE, TILE, TILE)
                            screen_rect = camera.to_screen_rect(tile_rect)

                            # Draw different tile types with different styles
                            if tile == TILE_FLOOR:
                                # Draw floor as a thinner platform
                                platform_height = TILE // 3
                                platform_rect = pygame.Rect(
                                    screen_rect.x,
                                    screen_rect.y + TILE - platform_height,
                                    screen_rect.width,
                                    platform_height
                                )
                                pygame.draw.rect(surf, color, platform_rect, border_radius=2)
                            elif tile == TILE_WALL:
                                # Draw wall as full block
                                pygame.draw.rect(surf, color, screen_rect, border_radius=6)
                            elif tile == TILE_SOLID:
                                # Draw solid tile with different pattern
                                pygame.draw.rect(surf, color, screen_rect)
                                # Add pattern to distinguish from walls
                                inner_rect = screen_rect.inflate(-8, -8)
                                pygame.draw.rect(surf, color, inner_rect, width=2)
        else:
            # Fallback to rendering solids list (for backward compatibility)
            from config import TILE_COL
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
        
        # Initialize data-driven registries (idempotent safe).
        init_terrain_defaults()
        init_area_defaults()

        # Generate terrain IDs grid
        terrain_grid = self._generate_terrain(validated_data, sub_seeds['terrain'])

        # Build enhanced areas using the new area builder
        # Pass tile_size for correct portal conversion.
        level_data_with_meta = dict(validated_data)
        level_data_with_meta["terrain_grid"] = terrain_grid
        level_data_with_meta.setdefault("tile_size", TILE)
        areas = build_enhanced_areas(level_data_with_meta, terrain_grid, level_type)

        # Ensure enemy spawn metadata from validation is preserved if present.
        enemy_spawns = validated_data.get('enemy_spawns')

        # Create final level
        generated_level = GeneratedLevel(
            validated_data['grid'],
            validated_data['rooms'],
            validated_data['spawn_points'],
            validated_data['type'],
            terrain_grid,
            areas,
        )

        # Attach additional metadata for downstream systems.
        if enemy_spawns is not None:
            setattr(generated_level, 'enemy_spawns', enemy_spawns)
        setattr(generated_level, 'areas', areas)
        setattr(generated_level, 'terrain_grid', terrain_grid)
        setattr(generated_level, 'level_type', level_type)
        setattr(generated_level, 'level_index', level_index)
        
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
        """
        Validate and repair structural aspects of the level.

        IMPORTANT:
        - This runs BEFORE GeneratedLevel spawns real enemies/portal.
        - We therefore validate only structural properties (grid, rooms,
          boundaries, connectivity, spawn_points).
        - We DO NOT enforce presence/positions of enemies/portal here to avoid
          false failures and double-specifying behavior already covered by
          GeneratedLevel + tests.
        """
        max_attempts = 3
        current_data = level_data.copy()

        # Ensure required keys exist for structural checks
        current_data.setdefault("rooms", [])
        current_data.setdefault("spawn_points", current_data.get("spawn_points", []))
        current_data.setdefault("enemy_spawns", [])
        # Do NOT inject fake enemies/portal_pos; that is handled later.

        for attempt in range(max_attempts):
            self.validation_attempts += 1

            # Run validator but ignore issues that are explicitly about
            # missing enemies/portal, since those are populated post-process.
            result = self.validator.validate(current_data)

            if result.is_valid:
                return current_data

            # Filter issues to see if any structural problems remain.
            structural_issues = []
            for issue in result.issues:
                low = issue.lower()
                if ("no portal position found" in low) or ("no enemies found" in low):
                    # Defer these to GeneratedLevel/_spawn_enemies/_place_portal.
                    continue
                structural_issues.append(issue)

            if not structural_issues:
                # Only non-structural complaints (like missing portal/enemies); accept.
                return current_data

            # Attempt repair for structural problems if we have attempts left.
            if attempt < max_attempts - 1:
                current_data = self.validator.repair_level(current_data, result)

        # If still failing, fall back to the best structural data we have.
        return current_data
    
    def _generate_terrain(self, level_data: Dict[str, Any], terrain_seed: int) -> List[List[str]]:
        """Generate terrain for the level"""
        grid = level_data.get('grid', [])
        level_type = level_data.get('type', 'dungeon')

        if not grid:
            return []

        terrain_rng = self.seed_manager.get_random('terrain')
        terrain_rng.seed(terrain_seed)

        # First, detect floating structures that should be platforms
        platform_map = self._detect_floating_structures(grid)

        terrain_grid = []

        for y, row in enumerate(grid):
            terrain_row = []
            for x, tile in enumerate(row):
                if tile in (TILE_WALL, TILE_SOLID):  # Solid tile
                    # Check if this is part of a floating platform
                    if platform_map[y][x]:
                        # This is part of a platform - now determine if it's top, side, or internal
                        if self._is_platform_top_surface(grid, x, y):
                            # Top surface of platform
                            terrain_type = self._select_platform_terrain(x, y, level_type, terrain_rng)
                        elif self._is_platform_side(grid, x, y):
                            # Side of platform should be wall
                            terrain_type = self._select_wall_terrain(x, y, level_type, terrain_rng)
                        else:
                            # Internal platform tiles should be platform
                            terrain_type = self._select_platform_terrain(x, y, level_type, terrain_rng)
                        terrain_row.append(terrain_type)
                    else:
                        # This is a regular wall (connected to ground)
                        terrain_type = self._select_wall_terrain(x, y, level_type, terrain_rng)
                        terrain_row.append(terrain_type)
                else:  # Empty/air box
                    # Distinguish true empty air from walkable floor:
                    # - If there is a solid tile directly below -> this is a walkable floor surface.
                    # - Otherwise -> this is open air.
                    below_is_solid = False
                    if y + 1 < len(grid) and grid[y + 1][x] == 1:
                        below_is_solid = True

                    if below_is_solid:
                        terrain_type = self._select_floor_terrain(x, y, level_type, terrain_rng)
                    else:
                        # True empty space
                        terrain_type = "air"
                    terrain_row.append(terrain_type)
            terrain_grid.append(terrain_row)

        return terrain_grid

    def _detect_floating_structures(self, grid: List[List[int]]) -> List[List[bool]]:
        """
        Detect floating structures that should be platforms instead of walls.

        Returns a 2D boolean map where True indicates a platform tile.
        A platform is a solid structure that:
        - Is not connected to the ground (bottom of the map)
        - Has empty space directly below most of its tiles
        - Is part of a horizontally-oriented structure (suitable for jumping)
        """
        height = len(grid)
        width = len(grid[0]) if height > 0 else 0

        if width == 0 or height == 0:
            return [[False for _ in range(width)] for _ in range(height)]

        # Create a visited map for flood fill
        visited = [[False for _ in range(width)] for _ in range(height)]
        platform_map = [[False for _ in range(width)] for _ in range(height)]

        # First, mark all tiles at the bottom boundary as "grounded"
        grounded = [[False for _ in range(width)] for _ in range(height)]
        for x in range(width):
            if grid[height - 1][x] == 1:
                grounded[height - 1][x] = True

        # Flood fill to mark all grounded structures
        stack = [(x, height - 1) for x in range(width) if grid[height - 1][x] == 1]

        while stack:
            x, y = stack.pop()

            # Check 4-directional neighbors
            for dx, dy in [(0, 1), (0, -1), (1, 0), (-1, 0)]:
                nx, ny = x + dx, y + dy

                if (0 <= nx < width and 0 <= ny < height and
                    not visited[ny][nx] and grid[ny][nx] == 1):
                    visited[ny][nx] = True
                    grounded[ny][nx] = True
                    stack.append((nx, ny))

        # Reset visited for structure tracing
        visited = [[False for _ in range(width)] for _ in range(height)]

        # Now identify floating structures
        for y in range(height):
            for x in range(width):
                if grid[y][x] == 1 and not grounded[y][x] and not visited[y][x]:
                    # Found an ungrounded solid tile - trace its structure
                    structure_tiles = []
                    self._trace_structure(grid, x, y, visited, structure_tiles)

                    # Analyze the structure
                    if self._is_platform_structure(grid, structure_tiles, width, height):
                        for sx, sy in structure_tiles:
                            platform_map[sy][sx] = True

        return platform_map

    def _trace_structure(self, grid: List[List[int]], x: int, y: int,
                        visited: List[List[bool]], structure_tiles: List[Tuple[int, int]]):
        """Trace a connected structure using flood fill"""
        height = len(grid)
        width = len(grid[0]) if height > 0 else 0

        stack = [(x, y)]

        while stack:
            sx, sy = stack.pop()

            if (sx < 0 or sx >= width or sy < 0 or sy >= height or
                visited[sy][sx] or grid[sy][sx] != 1):
                continue

            visited[sy][sx] = True
            structure_tiles.append((sx, sy))

            # Check 4-directional neighbors
            for dx, dy in [(0, 1), (0, -1), (1, 0), (-1, 0)]:
                nx, ny = sx + dx, sy + dy
                if (0 <= nx < width and 0 <= ny < height and
                    not visited[ny][nx] and grid[ny][nx] == 1):
                    stack.append((nx, ny))

    def _is_platform_structure(self, grid: List[List[int]], structure_tiles: List[Tuple[int, int]],
                              width: int, height: int) -> bool:
        """
        Determine if a structure should be treated as a platform.

        A structure is a platform if it's floating (not connected to ground).
        No size restrictions - any floating chunk of solid boxes is a platform.
        """
        # Only requirement: it's a floating structure (not connected to ground)
        # The detection of floating structures is already done in _detect_floating_structures
        # So if we're called here, it's already confirmed to be floating
        return True

    def _is_platform_top_surface(self, grid: List[List[int]], x: int, y: int) -> bool:
        """
        Check if this solid tile is the top surface of a platform.
        A tile is a top surface if there's empty space above it.
        """
        height = len(grid)
        if y == 0:
            # At the top of the map - it's a top surface
            return True

        # Check if there's empty space above
        above_tile = grid[y - 1][x]
        return above_tile == TILE_AIR

    def _is_platform_side(self, grid: List[List[int]], x: int, y: int) -> bool:
        """
        Check if this solid tile is on the side of a platform.
        A tile is a side if there's empty space horizontally adjacent.
        """
        width = len(grid[0]) if grid else 0

        # Check left side
        if x > 0 and grid[y][x - 1] == TILE_AIR:
            return True

        # Check right side
        if x < width - 1 and grid[y][x + 1] == TILE_AIR:
            return True

        return False

    def _select_platform_terrain(self, x: int, y: int, level_type: str, rng):
        """Select terrain type for platform tiles based on level type"""
        if level_type == "dungeon":
            # Dungeon platforms - occasional hazards
            roll = rng.random()
            if roll < 0.06:
                return "platform_sticky"
            elif roll < 0.10:
                return "platform_icy"
            return "platform_normal"
        elif level_type == "cave":
            # Cave platforms - more natural hazards
            roll = rng.random()
            if roll < 0.10:
                return "platform_sticky"
            elif roll < 0.15:
                return "platform_icy"
            return "platform_normal"
        elif level_type == "outdoor":
            # Outdoor platforms - fewer hazards
            roll = rng.random()
            if roll < 0.04:
                return "platform_sticky"  # Mushrooms/vines
            return "platform_normal"
        elif level_type == "hybrid":
            # Hybrid platforms - mix of hazards
            roll = rng.random()
            if roll < 0.08:
                return "platform_sticky"
            elif roll < 0.13:
                return "platform_icy"
            elif roll < 0.16:
                return "platform_fire"
            return "platform_normal"
        else:
            return "platform_normal"

    def _select_wall_terrain(self, x: int, y: int, level_type: str, rng):
        """Select terrain type for wall tiles based on level type"""
        # Only one wall type exists currently, but we can vary density/patterns by level type
        return "wall_solid"

    def _select_floor_terrain(self, x: int, y: int, level_type: str, rng):
        """Select terrain type for floor tiles based on level type"""
        if level_type == "dungeon":
            # Dungeon floors - occasional hazards
            roll = rng.random()
            if roll < 0.05:
                return "floor_sticky"  # Rare sticky traps
            elif roll < 0.08:
                return "floor_icy"     # Rare icy patches
            return "floor_normal"
        elif level_type == "cave":
            # Cave floors - more natural hazards
            roll = rng.random()
            if roll < 0.08:
                return "floor_sticky"  # Sticky cave floor
            elif roll < 0.12:
                return "floor_icy"     # Icy cave sections
            return "floor_normal"
        elif level_type == "outdoor":
            # Outdoor floors - fewer hazards, more natural
            roll = rng.random()
            if roll < 0.03:
                return "floor_sticky"  # Mud patches
            return "floor_normal"
        elif level_type == "hybrid":
            # Hybrid levels - mix of everything
            roll = rng.random()
            if roll < 0.06:
                return "floor_sticky"
            elif roll < 0.10:
                return "floor_icy"
            elif roll < 0.13:
                return "floor_fire"    # Lava/crystal areas
            return "floor_normal"
        else:
            return "floor_normal"
    
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


def generate_terrain_test_level() -> GeneratedLevel:
    """
    Generate a deterministic test level that includes ALL terrain types and areas.

    This creates a fixed layout showcasing:
    - All terrain IDs: floor_normal, floor_sticky, floor_icy, floor_fire
                     platform_normal, platform_sticky, platform_icy, platform_fire
                     wall_solid, water
    - All area types: PLAYER_SPAWN, PORTAL_ZONE, GROUND_ENEMY_SPAWN,
                     FLYING_ENEMY_SPAWN, WATER_AREA, MERCHANT_AREA
    """
    # Initialize registries to ensure all types are available
    init_terrain_defaults()
    init_area_defaults()

    # Create a fixed 40x30 grid with predetermined layout
    width, height = 40, 30
    grid = [[1 for _ in range(width)] for _ in range(height)]  # Start with all walls

    # Define terrain grid with all terrain types
    terrain_grid = [["wall_solid" for _ in range(width)] for _ in range(height)]

    # Create different sections for each terrain type
    sections = [
        # (x_start, y_start, width, height, terrain_id, is_walkable)
        (2, 2, 8, 4, "floor_normal", True),
        (12, 2, 8, 4, "floor_sticky", True),
        (22, 2, 8, 4, "floor_icy", True),
        (32, 2, 6, 4, "floor_fire", True),

        (2, 8, 8, 3, "platform_normal", True),
        (12, 8, 8, 3, "platform_sticky", True),
        (22, 8, 8, 3, "platform_icy", True),
        (32, 8, 6, 3, "platform_fire", True),

        (2, 13, 10, 6, "water", False),
        (14, 13, 10, 6, "floor_normal", True),
        (26, 13, 12, 6, "floor_normal", True),

        (2, 21, 36, 7, "floor_normal", True),  # Main area
    ]

    # Apply sections to grid and terrain_grid
    for x, y, w, h, terrain_id, is_walkable in sections:
        for dy in range(h):
            for dx in range(w):
                if x + dx < width and y + dy < height:
                    grid[y + dy][x + dx] = 0 if is_walkable else 1
                    terrain_grid[y + dy][x + dx] = terrain_id

    # Create corridors to connect sections
    corridors = [
        # Horizontal corridors
        (10, 4, 2, 1),  # between floor_normal and floor_sticky
        (20, 4, 2, 1),  # between floor_sticky and floor_icy
        (30, 4, 2, 1),  # between floor_icy and floor_fire

        (10, 9, 2, 1),  # between platform sections
        (20, 9, 2, 1),
        (30, 9, 2, 1),

        # Vertical connections
        (6, 6, 1, 2),  # floor to platform
        (16, 6, 1, 2),
        (26, 6, 1, 2),
        (35, 6, 1, 2),

        # Connect to main area
        (6, 17, 1, 4),
        (16, 17, 1, 4),
        (31, 17, 1, 4),
    ]

    for x, y, w, h in corridors:
        for dy in range(h):
            for dx in range(w):
                if x + dx < width and y + dy < height:
                    grid[y + dy][x + dx] = 0
                    terrain_grid[y + dy][x + dx] = "floor_normal"

    # Define spawn points
    spawn_points = [
        (20, 24),  # Center of main area
    ]

    # Create areas for all area types
    from .area_system import AreaMap, Area, AreaType

    areas = AreaMap()

    # Define area rectangles
    area_definitions = [
        # (x, y, width, height, area_type)
        (4, 3, 4, 2, AreaType.PLAYER_SPAWN),
        (30, 3, 4, 2, AreaType.PORTAL_ZONE),
        (14, 3, 4, 2, AreaType.GROUND_ENEMY_SPAWN),
        (24, 3, 4, 2, AreaType.FLYING_ENEMY_SPAWN),
        (4, 15, 6, 4, AreaType.WATER_AREA),
        (28, 15, 8, 3, AreaType.MERCHANT_AREA),
        (16, 22, 8, 5, AreaType.GROUND_ENEMY_SPAWN),  # Additional enemy area
    ]

    # Add areas to the map
    area_id = 0
    for x, y, w, h, area_type in area_definitions:
        area_id_str = f"{area_type.lower()}_{area_id}"
        area = Area(area_id_str, area_type, x, y, w, h)
        areas.add_area(area)
        area_id += 1

    # Create empty rooms list (not used in test level)
    rooms = []

    # Create the test level
    test_level = GeneratedLevel(
        grid=grid,
        rooms=rooms,
        spawn_points=spawn_points,
        level_type="terrain_test",
        terrain_grid=terrain_grid,
        areas=areas
    )

    # Mark as test level (metadata attributes are optional and safe to set)
    test_level.is_procedural = True
    setattr(test_level, "is_test_level", True)

    # Set portal position in the PORTAL_ZONE
    if test_level.portal_pos is None:
        # Place portal in the designated PORTAL_ZONE
        test_level.portal_pos = (31 * TILE, 4 * TILE)

    return test_level