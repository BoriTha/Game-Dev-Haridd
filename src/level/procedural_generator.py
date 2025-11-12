from dataclasses import dataclass, field
import random
import math
from typing import Tuple, List, Set, Optional

from src.level.room_data import RoomData, TileCell, GenerationConfig, MovementAttributes, SpawnArea
# Removed: Platform import since platforms are no longer used
from src.level.traversal_verification import find_valid_ground_locations, verify_traversable
from src.core.utils import bresenham_line
from src.tiles.tile_types import TileType


# All legacy platform-related types and helpers (Platform/add/remove/generate/exclusion)
# have been fully removed from the procedural generation module.
# PCG no longer creates platform tiles; only corridors, spawn areas, and doors are used.


# REMOVED: create_exclusion_map was only used by place_platforms
# Since platforms are no longer placed, this exclusion logic is unused.
# Function kept for compatibility but no longer called by PCG pipeline.


# REMOVED: platform_overlaps_exclusion was only used by place_platforms
# Since platforms are no longer placed, this function is unused.
# Kept for compatibility in case other code references it.


# REMOVED: Platforms are no longer placed as part of PCG
# This function and its helpers are kept for compatibility but not called.


def create_exclusion_zone(
    room_data: RoomData,
    center_x: int,
    center_y: int,
    width: int,
    height: int,
    exclusion_type: str = "PROTECTED"
) -> set:
    """
    Create exclusion zone for rectangular area.
    
    Args:
        room_data: Room to modify
        center_x: Center X coordinate
        center_y: Center Y coordinate  
        width: Width of protected area
        height: Height of protected area
        exclusion_type: Type flag for protected tiles
        
    Returns:
        Set of protected tile coordinates
    """
    protected_tiles = set()
    half_width = width // 2
    half_height = height // 2
    
    for dx in range(-half_width, half_width + (width % 2)):
        for dy in range(-half_height, half_height + (height % 2)):
            tile_x = center_x + dx
            tile_y = center_y + dy
            
            if room_data.is_in_bounds(tile_x, tile_y):
                # Mark existing tile as protected
                existing_tile = room_data.get_tile(tile_x, tile_y)
                existing_tile.flags.add(exclusion_type)
                protected_tiles.add((tile_x, tile_y))
    
    return protected_tiles


def calculate_spawn_density(
    room_data: RoomData,
    config: GenerationConfig
) -> int:
    """
    Calculate optimal number of spawn areas for a room.
    
    Based on:
    - Room size (larger rooms = more spawn areas)
    - Difficulty rating (harder rooms = more spawns)
    - Configuration constraints
    
    Args:
        room_data: Room to calculate for
        config: Generation configuration
    
    Returns:
        Number of spawn areas to create
    """
    room_area = room_data.size[0] * room_data.size[1]
    
    # Base calculation: 1 spawn area per X tiles
    base_spawn_areas = room_area // 100  # 1 per 100 tiles
    
    # Scale by difficulty rating
    difficulty_multiplier = 1.0 + (room_data.difficulty_rating / 10.0)
    adjusted_spawn_areas = int(base_spawn_areas * difficulty_multiplier)
    
    # Clamp to configured range
    num_spawn_areas = max(
        config.min_spawn_areas_per_room,
        min(adjusted_spawn_areas, config.max_spawn_areas_per_room)
    )
    
    return num_spawn_areas


def areas_too_close(
    area1: SpawnArea,
    area2: SpawnArea,
    min_spacing: int
) -> bool:
    """
    Check if two spawn areas are too close together.
    
    Uses bounding box distance check.
    
    Args:
        area1: First spawn area
        area2: Second spawn area
        min_spacing: Minimum required distance between areas
    
    Returns:
        True if areas violate minimum spacing, False otherwise
    """
    # Get bounding boxes
    x1, y1 = area1.position
    w1, h1 = area1.size
    
    x2, y2 = area2.position
    w2, h2 = area2.size
    
    # Calculate distances between boxes
    # Horizontal distance
    if x1 + w1 < x2:
        dx = x2 - (x1 + w1)
    elif x2 + w2 < x1:
        dx = x1 - (x2 + w2)
    else:
        dx = 0  # Overlapping horizontally
    
    # Vertical distance
    if y1 + h1 < y2:
        dy = y2 - (y1 + h1)
    elif y2 + h2 < y1:
        dy = y1 - (y2 + h2)
    else:
        dy = 0  # Overlapping vertically
    
    # Check if distance is less than minimum
    return (dx < min_spacing and dy < min_spacing)


def generate_random_spawn_area(
    room_data: RoomData,
    config: GenerationConfig,
    rng: random.Random,
    existing_areas: List[SpawnArea]
) -> Optional[SpawnArea]:
    """
    Generate a random spawn area that doesn't overlap existing areas.
    
    Args:
        room_data: Room to place spawn area in
        config: Generation configuration
        rng: Random number generator
        existing_areas: Already placed spawn areas to avoid
    
    Returns:
        SpawnArea object, or None if no valid position found
    """
    max_attempts = 50
    
    for _ in range(max_attempts):
        # Random size
        width = rng.randint(config.spawn_area_min_size, config.spawn_area_max_size)
        height = rng.randint(config.spawn_area_min_size, config.spawn_area_max_size)
        
        # Random position (ensure it fits in room)
        if width >= room_data.size[0] or height >= room_data.size[1]:
            continue  # Spawn area too big for room
        
        x = rng.randint(0, room_data.size[0] - width)
        y = rng.randint(0, room_data.size[1] - height)
        
        new_area = SpawnArea(
            position=(x, y),
            size=(width, height),
            spawn_rules={'allow_enemies': True}  # Default to allowing enemies
        )
        
        # Check spacing from existing spawn areas
        valid = True
        for existing in existing_areas:
            if areas_too_close(new_area, existing, config.spawn_area_spacing):
                valid = False
                break
        
        if valid:
            return new_area
    
    return None  # Couldn't find valid position


def place_spawn_areas(
    room_data: RoomData,
    config: GenerationConfig
) -> int:
    """
    Place spawn areas in the room for enemy/item spawning.
    
    Strategy:
    1. Calculate how many spawn areas needed
    2. Create exclusion zones around doors
    3. Generate spawn areas avoiding exclusions and each other
    4. Add to room_data.spawn_areas
    
    Args:
        room_data: Room to modify
        config: Generation configuration
    
    Returns:
        Number of spawn areas successfully placed
    """
    # Initialize RNG
    rng = random.Random(config.seed)
    
    # Calculate target number
    target_num_areas = calculate_spawn_density(room_data, config)
    
    # Create exclusion zones around doors
    excluded_coords = set()
    if room_data.entrance_coords:
        ex, ey = room_data.entrance_coords
        for dx in range(-2, 3):
            for dy in range(-2, 3):
                excluded_coords.add((ex + dx, ey + dy))
    
    if room_data.exit_coords:
        ex, ey = room_data.exit_coords
        for dx in range(-2, 3):
            for dy in range(-2, 3):
                excluded_coords.add((ex + dx, ey + dy))
    
    # Place spawn areas
    placed_areas = []
    
    for _ in range(target_num_areas * 3):  # Try 3x target to account for failures
        if len(placed_areas) >= target_num_areas:
            break  # Got enough
        
        new_area = generate_random_spawn_area(
            room_data,
            config,
            rng,
            placed_areas
        )
        
        if new_area:
            # Check if it overlaps door exclusion zones
            overlaps_exclusion = False
            for coord in new_area.get_all_coords():
                if coord in excluded_coords:
                    overlaps_exclusion = True
                    break
            
            if not overlaps_exclusion:
                placed_areas.append(new_area)
    
    # Add to room data
    room_data.spawn_areas.extend(placed_areas)
    
    return len(placed_areas)


def configure_room_difficulty(
    room_data: RoomData,
    depth_from_start: int,
    config: GenerationConfig
) -> None:
    """
    Configure room difficulty based on depth from start.
    
    Applies logarithmic scaling to prevent exponential difficulty growth.
    Updates spawn area rules with enemy limits.
    
    Args:
        room_data: Room to configure
        depth_from_start: How many rooms from start (0-based)
        config: Generation configuration
    
    Modifies room_data in place.
    """
    # Set depth
    room_data.depth_from_start = depth_from_start
    
    # Calculate difficulty rating (logarithmic scale)
    if depth_from_start == 0:
        difficulty_rating = 1
    else:
        difficulty_rating = 1 + int(
            math.log(depth_from_start + 1) * config.difficulty_scale_factor * 10
        )
    
    # Cap difficulty
    difficulty_rating = min(difficulty_rating, config.max_difficulty_rating)
    room_data.difficulty_rating = difficulty_rating
    
    # Calculate enemy limits for this difficulty
    room_area = room_data.size[0] * room_data.size[1]
    base_density = config.base_enemy_density
    
    # Scale density by difficulty
    scaled_density = base_density * (1 + difficulty_rating * 0.2)
    
    # Calculate max enemies for room
    max_enemies_for_room = int(room_area * scaled_density)
    max_enemies_for_room = min(max_enemies_for_room, config.max_enemies_per_room)
    
    # Apply to spawn areas
    if room_data.spawn_areas:
        # Distribute enemies across spawn areas
        enemies_per_area = max(1, max_enemies_for_room // len(room_data.spawn_areas))
        
        for area in room_data.spawn_areas:
            if area.spawn_rules.get('allow_enemies', True):
                area.spawn_rules['max_enemies'] = enemies_per_area
                area.spawn_rules['difficulty_level'] = difficulty_rating


def place_doors(room: RoomData, movement_attrs: MovementAttributes):
    """
    Finds valid ground locations on the edges and places doors.
    """
    valid_ground = find_valid_ground_locations(room, movement_attrs.player_width, movement_attrs.player_height)
    
    # Look for ground specifically at door platform height (height - 5)
    door_platform_y = room.size[1] - 5
    edge_ground_at_platform = [pos for pos in valid_ground if pos[1] == door_platform_y]
    
    left_edge_candidates = [pos for pos in edge_ground_at_platform if pos[0] == 1]
    right_edge_candidates = [pos for pos in edge_ground_at_platform if pos[0] == room.size[0] - 2]

    # If no ground at platform height, fall back to any edge ground
    if not left_edge_candidates:
        left_edge_candidates = [pos for pos in valid_ground if pos[0] == 1]
    if not right_edge_candidates:
        right_edge_candidates = [pos for pos in valid_ground if pos[0] == room.size[0] - 2]

    if not left_edge_candidates or not right_edge_candidates:
        return False # Not a valid room for doors

    # Place entrance door (AIR tile above the ground)
    entrance_ground = random.choice(left_edge_candidates)
    room.entrance_coords = (entrance_ground[0], entrance_ground[1] - 1)
    room.grid[room.entrance_coords] = TileCell(tile_type=TileType.AIR, flags={"DOOR_ENTRANCE"})

    # Place exit door (AIR tile above the ground)
    exit_ground = random.choice(right_edge_candidates)
    room.exit_coords = (exit_ground[0], exit_ground[1] - 1)
    room.grid[room.exit_coords] = TileCell(tile_type=TileType.AIR, flags={"DOOR_EXIT"})
    
    return True

def carve_corridor_block(
    room_data: RoomData,
    center_x: int,
    center_y: int,
    width: int,
    height: int,
    force_carve: bool = False  # NEW: Override protection for reconnection
) -> None:
    """
    Carve a rectangular block of AIR tiles centered at (center_x, center_y).
    
    This ensures corridors are wide enough for player traversal.
    
    Args:
        room_data: Room to modify
        center_x: X coordinate of block center
        center_y: Y coordinate of block center
        width: Width of block to carve (in tiles)
        height: Height of block to carve (in tiles)
        force_carve: If True, override protection flags (for reconnection)
    
    Modifies room_data.grid in place.
    """
    # Calculate block boundaries (centered on walker position)
    half_width = width // 2
    half_height = height // 2
    
    start_x = center_x - half_width
    end_x = center_x + half_width + (width % 2)  # Add 1 if odd width
    start_y = center_y - half_height
    end_y = center_y + half_height + (height % 2)  # Add 1 if odd height
    
    carved_count = 0
    # Carve block, respecting protected tiles unless force_carve
    for x in range(start_x, end_x):
        for y in range(start_y, end_y):
            if room_data.is_in_bounds(x, y):
                existing_tile = room_data.get_tile(x, y)
                # Skip carving if tile has protection flags, unless force_carve
                if not force_carve and any(flag in existing_tile.flags for flag in ["SPAWN_PLATFORM", "DOOR_PLATFORM", "PROTECTED"]):
                    continue
                # Force carve: create new AIR tile, ignoring flags
                room_data.set_tile(x, y, TileCell(tile_type=TileType.AIR))
                carved_count += 1
            else:
                pass


def flood_fill_find_regions(room_data: RoomData) -> List[Set[Tuple[int, int]]]:
    """
    Find all disconnected AIR regions in the room using flood-fill.
    
    Returns a list where each element is a set of coordinates forming
    one connected region.
    
    Args:
        room_data: Room to analyze
    
    Returns:
        List of coordinate sets, one per connected region
    """
    # Find all AIR tiles
    air_tiles = set()
    for y in range(room_data.size[1]):
        for x in range(room_data.size[0]):
            if room_data.get_tile(x, y).tile_type == TileType.AIR:
                air_tiles.add((x, y))
    
    if not air_tiles:
        return []  # No AIR tiles at all
    
    regions = []
    unvisited = air_tiles.copy()
    
    while unvisited:
        # Start new region from any unvisited tile
        start = next(iter(unvisited))
        region = set()
        queue = [start]
        region.add(start)
        unvisited.remove(start)
        
        # Flood fill this region
        while queue:
            x, y = queue.pop(0)
            
            # Check 4 neighbors
            for dx, dy in [(0, 1), (0, -1), (1, 0), (-1, 0)]:
                nx, ny = x + dx, y + dy
                
                if (nx, ny) in unvisited:
                    region.add((nx, ny))
                    unvisited.remove((nx, ny))
                    queue.append((nx, ny))
        
        regions.append(region)
    
    return regions


def reconnect_isolated_regions(
    room_data: RoomData,
    config: GenerationConfig  # ADD THIS PARAMETER
) -> bool:
    """
    Connect isolated AIR regions by carving corridors between them.
    
    NOW RESPECTS corridor width constraints!
    """
    max_reconnection_attempts = 10
    
    for attempt in range(max_reconnection_attempts):
        regions = flood_fill_find_regions(room_data)
        
        if len(regions) <= 1:
            return True  # All connected!
        
        # Find two closest regions
        region1 = regions[0]
        region2 = regions[1]
        
        # Find closest points between them
        min_dist = float('inf')
        best_pair = None
        
        sample1 = list(region1)[::max(1, len(region1) // 20)]
        sample2 = list(region2)[::max(1, len(region2) // 20)]
        
        for p1 in sample1:
            for p2 in sample2:
                dist = abs(p1[0] - p2[0]) + abs(p1[1] - p2[1])
                if dist < min_dist:
                    min_dist = dist
                    best_pair = (p1, p2)
        
        if not best_pair:
            return False
        
        #  FIXED: Use carve_corridor_block instead of manual carving
        start, end = best_pair
        corridor_points = bresenham_line(start[0], start[1], end[0], end[1])
        
        for x, y in corridor_points:
            carve_corridor_block(
                room_data,
                center_x=x,
                center_y=y,
                width=max(config.min_corridor_width, config.movement_attributes.player_width),
                height=config.movement_attributes.min_corridor_height,
                force_carve=True  # Override protection for reconnection
            )
    
    return False

def generate_room_layout(config: GenerationConfig) -> RoomData:
    """
    Generate a room layout using constrained Drunkard's Walk.
    
    The walker carves corridors that respect min_corridor_width and
    player movement constraints.
    
    Args:
        config: Generation configuration
    
    Returns:
        RoomData with carved AIR paths (not yet validated)
    """
    # Initialize seeded RNG
    rng = random.Random(config.seed)
    
    # Random room dimensions
    width = rng.randint(config.min_room_size, config.max_room_size)
    height = rng.randint(config.min_room_size, config.max_room_size)
    
    # Create room filled with WALL (sparse: empty grid with WALL default)
    room = RoomData(
        size=(width, height),
        default_tile=TileCell(tile_type=TileType.WALL),
        grid={}
    )
    
    # Calculate required corridor dimensions
    # Must accommodate player width AND minimum corridor width
    carve_width = max(
        config.min_corridor_width,
        config.movement_attributes.player_width
    )
    carve_height = max(
        config.movement_attributes.min_corridor_height,
        config.movement_attributes.player_height
    )
    
    # === NEW: Choose spawn position within 10-tile radius of corner ===
    # Define 10x10 quadrant regions extending from each corner
    corner_regions = []
    
    # Calculate quadrant size, ensuring room is large enough for 3x3 spawn area
    min_room_size = 6  # Minimum size for 3x3 spawn area
    if width >= min_room_size and height >= min_room_size:
        # Top-left quadrant: (1,1) to (10,10) or room bounds
        corner_regions.append({
            'min_x': 1, 'max_x': min(10, width - 3),
            'min_y': 1, 'max_y': min(10, height - 3)
        })
        
        # Top-right quadrant: (width-10,1) to (width-1,10) or room bounds
        corner_regions.append({
            'min_x': max(width - 10, 2), 'max_x': width - 2,
            'min_y': 1, 'max_y': min(10, height - 3)
        })
        
        # Bottom-left quadrant: (1,height-10) to (10,height-1) or room bounds
        corner_regions.append({
            'min_x': 1, 'max_x': min(10, width - 3),
            'min_y': max(height - 10, 2), 'max_y': height - 2
        })
        
        # Bottom-right quadrant: (width-10,height-10) to (width-1,height-1) or room bounds
        corner_regions.append({
            'min_x': max(width - 10, 2), 'max_x': width - 2,
            'min_y': max(height - 10, 2), 'max_y': height - 2
        })
    
    # Generate random spawn position within chosen quadrant
    if corner_regions:
        chosen_region = rng.choice(corner_regions)
        spawn_center_x = rng.randint(chosen_region['min_x'], chosen_region['max_x'])
        spawn_center_y = rng.randint(chosen_region['min_y'], chosen_region['max_y'])
    else:
        # Fallback for very small rooms
        spawn_center_x = max(2, min(width // 2, width - 3))
        spawn_center_y = max(2, min(height // 2, height - 3))
    
    # === NEW: Boundary auto-adjustment to prevent out-of-bounds carving ===
    # Check if 3x3 area would go out of bounds and adjust if needed
    needs_adjustment = False
    adjust_x = 0
    adjust_y = 0

    if spawn_center_x - 1 < 0:  # Would carve left boundary
        adjust_x = 1 - spawn_center_x
        needs_adjustment = True
    elif spawn_center_x + 1 >= width:  # Would carve right boundary
        adjust_x = (width - 1) - spawn_center_x
        needs_adjustment = True

    if spawn_center_y - 1 < 0:  # Would carve top boundary
        adjust_y = 1 - spawn_center_y
        needs_adjustment = True
    elif spawn_center_y + 1 >= height:  # Would carve bottom boundary
        adjust_y = (height - 1) - spawn_center_y
        needs_adjustment = True

    # Auto-adjust to nearest valid position
    if needs_adjustment:
        spawn_center_x += adjust_x
        spawn_center_y += adjust_y
    
    # Store player spawn center for later use
    room.player_spawn = (spawn_center_x, spawn_center_y)
    
    # === NEW: Carve 3x3 spawn area (AIR space above ground) ===
    # Carve a 3x3 block of AIR tiles centered around spawn_center
    for dx in range(-1, 2):
        for dy in range(-1, 2):
            carve_x = spawn_center_x + dx
            carve_y = spawn_center_y + dy
            if room.is_in_bounds(carve_x, carve_y):
                room.set_tile(carve_x, carve_y, TileCell(tile_type=TileType.AIR))
    
    # === NEW: Create exclusion zone for ground platform only ===
    # Protect 3x1 ground platform below spawn area (existing WALL tiles)
    spawn_exclusion = set()
    ground_platform_exclusion = create_exclusion_zone(
        room_data=room,
        center_x=spawn_center_x,
        center_y=spawn_center_y + 2,  # One tile below 3x3 spawn area
        width=3,
        height=1,
        exclusion_type="SPAWN_PLATFORM"
    )
    spawn_exclusion.update(ground_platform_exclusion)
    
    # Initialize walker at spawn center instead of room center
    walker_x = spawn_center_x
    walker_y = spawn_center_y
    
    # Drunkard's Walk parameters
    max_steps = width * height // 2  # Carve ~50% of room
    carved_tiles = 0
    target_carved = (width * height) // 3  # Stop at ~33% carved
    
    # Biased random walk
    directions = [
        (1, 0),   # Right (more likely - horizontal bias)
        (1, 0),   # Right (duplicated for 2x weight)
        (-1, 0),  # Left
        (-1, 0),  # Left (duplicated for 2x weight)
        (0, 1),   # Down
        (0, -1),  # Up
    ]
    
    for step in range(max_steps):
        # === NEW: Prevent carving into spawn exclusion by clipping the block ===
        # We compute the intended carve block, then skip only the cells that
        # touch the protected spawn_exclusion area, instead of skipping the
        # entire step. This keeps a hard boundary but lets corridors pass nearby.
        half_width = carve_width // 2
        half_height = carve_height // 2
        start_x = walker_x - half_width
        end_x = walker_x + half_width + (carve_width % 2)
        start_y = walker_y - half_height
        end_y = walker_y + half_height + (carve_height % 2)

        # Carve corridor block, but skip any coordinates with protection flags
        for carve_x in range(start_x, end_x):
            for carve_y in range(start_y, end_y):
                if room.is_in_bounds(carve_x, carve_y):
                    existing_tile = room.get_tile(carve_x, carve_y)
                    # Skip carving if tile has any protection flag
                    if any(flag in existing_tile.flags for flag in ["SPAWN_PLATFORM", "DOOR_PLATFORM", "PROTECTED"]):
                        continue
                    room.set_tile(carve_x, carve_y, TileCell(tile_type=TileType.AIR))
        
        # Count carved tiles for stopping condition
        carved_tiles = len([t for t in room.grid.values() if t.tile_type == TileType.AIR])
        if carved_tiles >= target_carved:
            break
        
        # Move walker (biased random direction)
        dx, dy = rng.choice(directions)
        
        # Keep walker in bounds (with margin for carving)
        margin = max(carve_width, carve_height)
        walker_x = max(margin, min(width - margin - 1, walker_x + dx))
        walker_y = max(margin, min(height - margin - 1, walker_y + dy))
    
    # --- ADD THIS SECTION ---
    # Guarantee valid, flat ground for doors at a reasonable height
    door_ground_y = height - 5  # e.g., 5 tiles from bottom
    player_height = config.movement_attributes.player_height
    if door_ground_y > player_height: # Ensure it's not too high
        # Carve a 3-wide platform for the entrance
        for x_offset in range(3):
            room.set_tile(1 + x_offset, door_ground_y, TileCell(tile_type=TileType.WALL))
            # Carve clearance above it
            for y_offset in range(1, player_height + 2):
                 room.set_tile(1 + x_offset, door_ground_y - y_offset, TileCell(tile_type=TileType.AIR))

        # Carve a 3-wide platform for the exit
        for x_offset in range(3):
            room.set_tile(width - 4 + x_offset, door_ground_y, TileCell(tile_type=TileType.WALL))
            # Carve clearance above it
            for y_offset in range(1, player_height + 2):
                 room.set_tile(width - 4 + x_offset, door_ground_y - y_offset, TileCell(tile_type=TileType.AIR))

    # --- END ADDED SECTION ---

    # Designate general door areas (edges of room, in carved regions)
    # These are now just hints, place_doors will find the *real* spots
    room.entrance_coords = (1, door_ground_y - 1)
    room.exit_coords = (width - 2, door_ground_y - 1)
    
    return room


def carve_path(room: RoomData, start_pos: Tuple[int, int], end_pos: Tuple[int, int], player_height: int):
    """
    Ensures a walkable path with enough clearance exists between two points.
    It builds a floor and carves space above it.
    """
    path = bresenham_line(start_pos[0], start_pos[1], end_pos[0], end_pos[1])
    
    for (x, y) in path:
        # Place a solid floor tile
        room.grid[(x, y)] = TileCell(tile_type=TileType.WALL)
        
        # Carve out space above for the player
        for h in range(1, player_height + 1):
            if y - h > 0: # Check bounds
                room.grid[(x, y - h)] = TileCell(tile_type=TileType.AIR)


def generate_validated_room(
    config: GenerationConfig,
    movement_attrs: MovementAttributes,
    depth_from_start: int = 0
) -> RoomData:
    """Generate validated room with full connectivity guarantee."""
    
    for attempt in range(config.max_room_generation_attempts):
        # Phase 1: Generate basic layout

        room = generate_room_layout(config)

        
        # Phase 1.5: Full connectivity check and repair

        regions = flood_fill_find_regions(room)
        if len(regions) > 1:
            # Multiple disconnected regions - try to reconnect

            if not reconnect_isolated_regions(room, config):  #  Pass config

                continue  # Reconnection failed, try new room
            #  REMOVED redundant check_connectivity_basic call
            # If reconnection succeeded, we're guaranteed to be connected!
        

        
        #  HOWEVER: Still verify entrance/exit are accessible
        # (They might be in WALL tiles initially)
        if room.entrance_coords and room.exit_coords:
            entrance_tile = room.get_tile(*room.entrance_coords)
            exit_tile = room.get_tile(*room.exit_coords)
            
            # Quick sanity check
            if entrance_tile.t != "AIR" or exit_tile.t != "AIR":
                continue  # Doors not in AIR, regenerate
        
        # --- THIS IS THE NEW ORDER ---

        # Phase 2: Place DOORS *FIRST*
        # This establishes the *real* entrance/exit coords.
        if not place_doors(room, movement_attrs):
            continue

        
        # Phase 2.5: Create exclusion zones for door ground platforms
        # This ensures doors always have solid ground to stand on
        if room.entrance_coords:
            create_exclusion_zone(
                room_data=room,
                center_x=room.entrance_coords[0],
                center_y=room.entrance_coords[1] + 1,  # Below door
                width=3,
                height=1,
                exclusion_type="DOOR_PLATFORM"
            )
        
        if room.exit_coords:
            create_exclusion_zone(
                room_data=room,
                center_x=room.exit_coords[0],
                center_y=room.exit_coords[1] + 1,  # Below door
                width=3,
                height=1,
                exclusion_type="DOOR_PLATFORM"
            )
        

        
        # Phase 3: REMOVED - Platforms are no longer placed
        # Corridors and spawn area provide sufficient traversability
        
        # Phase 4: Final validation
        if verify_traversable(room, movement_attrs):
            # Phase 5: Configure difficulty
            configure_room_difficulty(room, depth_from_start, config)
            

            # Phase 6: Spawn areas disabled for PCG step flow; return validated room as-is
            return room
    
    # Fallback
    fallback = generate_fallback_room(config)
    configure_room_difficulty(fallback, depth_from_start, config)
    # Spawn areas disabled for fallback as well
    return fallback


def generate_fallback_room(config: GenerationConfig) -> RoomData:
    """
    Creates a simple rectangular room with a flat floor and no platforms.
    Guaranteed to be traversable.
    """
    fallback_width = config.min_room_size
    fallback_height = config.min_room_size

    room = RoomData(
        size=(fallback_width, fallback_height),
        default_tile=TileCell(tile_type=TileType.AIR),
        grid={}
    )

    # Create solid floor at the bottom
    floor_y = fallback_height - 1
    for x in range(fallback_width):
        room.grid[(x, floor_y)] = TileCell(tile_type=TileType.WALL)

    # Place entrance and exit on opposite sides, one tile above the floor
    room.entrance_coords = (1, floor_y - 1)
    room.exit_coords = (fallback_width - 2, floor_y - 1)

    # Ensure the entrance and exit spots are AIR (door openings)
    room.grid[room.entrance_coords] = TileCell(tile_type=TileType.AIR, flags={"DOOR_ENTRANCE"})
    room.grid[room.exit_coords] = TileCell(tile_type=TileType.AIR, flags={"DOOR_EXIT"})
    
    # Set player spawn in center of room, one tile above floor
    room.player_spawn = (fallback_width // 2, floor_y - 2)

    return room