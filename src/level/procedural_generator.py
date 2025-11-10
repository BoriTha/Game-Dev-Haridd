from dataclasses import dataclass, field
import random
import math
from typing import Tuple, List, Set, Optional

from src.level.room_data import RoomData, TileCell, GenerationConfig, MovementAttributes, SpawnArea
from src.level.traversal_verification import find_valid_ground_locations, verify_traversable
from src.core.utils import bresenham_line


@dataclass
class Platform:
    """
    Represents a rectangular platform in the room.

    Attributes:
        top_left: Top-left corner coordinate (x, y)
        width: Width in tiles
        height: Height in tiles (usually 1 for flat platforms)
    """
    top_left: Tuple[int, int]
    width: int
    height: int = 1

    def get_all_coords(self) -> List[Tuple[int, int]]:
        """Return all (x, y) coordinates occupied by this platform."""
        coords = []
        x, y = self.top_left
        for dy in range(self.height):
            for dx in range(self.width):
                coords.append((x + dx, y + dy))
        return coords


def add_platform(room_data: RoomData, platform: Platform) -> None:
    """
    Add a platform to the room by setting tiles to WALL.

    Args:
        room_data: Room to modify
        platform: Platform definition

    Modifies room_data.grid in place.
    """
    for x, y in platform.get_all_coords():
        if room_data.is_in_bounds(x, y):
            room_data.set_tile(x, y, TileCell(t="WALL", flags={"PLATFORM"}))


def remove_platform(room_data: RoomData, platform: Platform) -> None:
    """
    Remove a platform from the room by restoring tiles to default.

    Args:
        room_data: Room to modify
        platform: Platform to remove

    Modifies room_data.grid in place by deleting entries.
    """
    for x, y in platform.get_all_coords():
        if (x, y) in room_data.grid:
            # Remove from sparse grid (reverts to default_tile)
            del room_data.grid[(x, y)]


def generate_random_platform(
    room_data: RoomData,
    config: GenerationConfig,
    rng: random.Random
) -> Platform:
    """
    Generate a random platform that fits within room bounds.

    Args:
        room_data: Room to place platform in
        config: Generation configuration
        rng: Random number generator (for seeded generation)

    Returns:
        A Platform object with random position and size
    """
    # Platform size constraints
    min_platform_width = 2
    max_platform_width = 6
    platform_height = 1  # Flat platforms only for now

    # Random size
    width = rng.randint(min_platform_width, max_platform_width)

    # Random position (ensure it fits in room)
    max_x = room_data.size[0] - width
    max_y = room_data.size[1] - 2  # Don't place on floor or ceiling

    if max_x <= 0 or max_y <= 0:
        # Room too small for platforms
        return Platform(top_left=(0, 0), width=1, height=1)

    x = rng.randint(1, max_x)
    y = rng.randint(1, max_y)

    return Platform(
        top_left=(x, y),
        width=width,
        height=platform_height
    )


def create_exclusion_map(room_data: RoomData, config: GenerationConfig) -> Set[Tuple[int, int]]:
    """
    Create a set of coordinates where platforms should NOT be placed.

    Exclusion zones:
    - 3x3 area around entrance
    - 3x3 area around exit
    - Direct line between entrance and exit (critical path)

    Args:
        room_data: Room with door coordinates
        config: Generation configuration

    Returns:
        Set of (x, y) coordinates to avoid
    """
    excluded = set()

    # Exclude area around entrance
    if room_data.entrance_coords:
        ex, ey = room_data.entrance_coords
        for dx in range(-1, 2):
            for dy in range(-1, 2):
                excluded.add((ex + dx, ey + dy))

    # Exclude area around exit
    if room_data.exit_coords:
        ex, ey = room_data.exit_coords
        for dx in range(-1, 2):
            for dy in range(-1, 2):
                excluded.add((ex + dx, ey + dy))

    # Exclude direct line between entrance and exit (critical path hint)
    if room_data.entrance_coords and room_data.exit_coords:
        line_coords = bresenham_line(room_data.entrance_coords[0], room_data.entrance_coords[1], room_data.exit_coords[0], room_data.exit_coords[1])
        for coord in line_coords:
            # Exclude 1 tile above and below line
            excluded.add(coord)
            excluded.add((coord[0], coord[1] - 1))
            excluded.add((coord[0], coord[1] + 1))

    return excluded


def platform_overlaps_exclusion(
    platform: Platform,
    exclusion_map: Set[Tuple[int, int]]
) -> bool:
    """
    Check if platform overlaps any excluded coordinates.

    Args:
        platform: Platform to check
        exclusion_map: Set of excluded coordinates

    Returns:
        True if any overlap exists, False otherwise
    """
    platform_coords = set(platform.get_all_coords())
    return bool(platform_coords & exclusion_map)  # Set intersection


def place_platforms(
    room_data: RoomData,
    config: GenerationConfig,
    movement_attrs: MovementAttributes
) -> int:
    """
    Place platforms in room with per-platform validation and rollback.

    Strategy:
    1. Create exclusion map to protect doors
    2. Loop max_platform_attempts times
    3. For each attempt:
       - Generate random platform
       - Check if it overlaps exclusions (skip if yes)
       - Add platform to room
       - Validate traversability
       - If invalid: rollback (remove platform)
       - If valid: keep platform

    Args:
        room_data: Room to modify
        config: Generation configuration
        movement_attrs: Player movement capabilities for validation

    Returns:
        Number of platforms successfully added

    Modifies room_data.grid in place.
    """
    # Initialize seeded RNG for reproducibility
    rng = random.Random(config.seed)

    # Create exclusion zones around doors
    exclusion_map = create_exclusion_map(room_data, config)

    platforms_added = 0

    for attempt in range(config.platform_placement_attempts):
        # Generate random platform
        platform = generate_random_platform(room_data, config, rng)

        # Skip if overlaps exclusion zones
        if platform_overlaps_exclusion(platform, exclusion_map):
            continue

        # Add platform to room
        add_platform(room_data, platform)

        # CRITICAL: Validate traversability after EACH platform
        if verify_traversable(room_data, movement_attrs):
            # Platform is valid - keep it
            platforms_added += 1

            # Optional: Add this platform's coords to exclusion map
            # to ensure spacing between platforms
            exclusion_map.update(platform.get_all_coords())
        else:
            # Platform breaks traversability - ROLLBACK
            remove_platform(room_data, platform)
            # Continue trying other platforms

    return platforms_added


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
    
    left_edge_candidates = [pos for pos in valid_ground if pos[0] == 1]
    right_edge_candidates = [pos for pos in valid_ground if pos[0] == room.size[0] - 2]

    if not left_edge_candidates or not right_edge_candidates:
        return False # Not a valid room for doors

    # Place entrance door (AIR tile above the ground)
    entrance_ground = random.choice(left_edge_candidates)
    room.entrance_coords = (entrance_ground[0], entrance_ground[1] - 1)
    room.grid[room.entrance_coords] = TileCell(t="AIR", flags={"DOOR_ENTRANCE"})

    # Place exit door (AIR tile above the ground)
    exit_ground = random.choice(right_edge_candidates)
    room.exit_coords = (exit_ground[0], exit_ground[1] - 1)
    room.grid[room.exit_coords] = TileCell(t="AIR", flags={"DOOR_EXIT"})
    
    return True

def carve_corridor_block(
    room_data: RoomData,
    center_x: int,
    center_y: int,
    width: int,
    height: int
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
    
    Modifies room_data.grid in place.
    """
    # Calculate block boundaries (centered on walker position)
    half_width = width // 2
    half_height = height // 2
    
    start_x = center_x - half_width
    end_x = center_x + half_width + (width % 2)  # Add 1 if odd width
    start_y = center_y - half_height
    end_y = center_y + half_height + (height % 2)  # Add 1 if odd height
    
    # Carve the block
    for x in range(start_x, end_x):
        for y in range(start_y, end_y):
            if room_data.is_in_bounds(x, y):
                room_data.set_tile(x, y, TileCell(t="AIR"))

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
            if room_data.get_tile(x, y).t == "AIR":
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
                height=config.movement_attributes.min_corridor_height
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
        default_tile=TileCell(t="WALL"),
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
    
    # Initialize walker at room center
    walker_x = width // 2
    walker_y = height // 2
    
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
        # Carve a block centered on walker (not just single tile)
        carve_corridor_block(
            room,
            walker_x,
            walker_y,
            carve_width,
            carve_height
        )
        
        # Count carved tiles for stopping condition
        carved_tiles = len([t for t in room.grid.values() if t.t == "AIR"])
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
            room.set_tile(1 + x_offset, door_ground_y, TileCell(t="WALL"))
            # Carve clearance above it
            for y_offset in range(1, player_height + 2):
                 room.set_tile(1 + x_offset, door_ground_y - y_offset, TileCell(t="AIR"))

        # Carve a 3-wide platform for the exit
        for x_offset in range(3):
            room.set_tile(width - 4 + x_offset, door_ground_y, TileCell(t="WALL"))
            # Carve clearance above it
            for y_offset in range(1, player_height + 2):
                 room.set_tile(width - 4 + x_offset, door_ground_y - y_offset, TileCell(t="AIR"))

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
        room.grid[(x, y)] = TileCell(t="WALL")
        
        # Carve out space above for the player
        for h in range(1, player_height + 1):
            if y - h > 0: # Check bounds
                room.grid[(x, y - h)] = TileCell(t="AIR")


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
        
        # Phase 3: Place PLATFORMS *SECOND*
        # Now, verify_traversable (inside place_platforms) will use
        # the *real* coordinates and can validate paths correctly.
        num_platforms = place_platforms(room, config, movement_attrs)
        
        # Phase 4: Final validation
        if verify_traversable(room, movement_attrs):
            # Phase 5: Configure difficulty
            configure_room_difficulty(room, depth_from_start, config)
            
            # Phase 6: Place spawn areas
            num_spawn_areas = place_spawn_areas(room, config)
            
            return room
    
    # Fallback
    fallback = generate_fallback_room(config)
    configure_room_difficulty(fallback, depth_from_start, config)
    place_spawn_areas(fallback, config)
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
        default_tile=TileCell(t="AIR"),
        grid={}
    )

    # Create solid floor at the bottom
    floor_y = fallback_height - 1
    for x in range(fallback_width):
        room.grid[(x, floor_y)] = TileCell(t="WALL")

    # Place entrance and exit on opposite sides, one tile above the floor
    room.entrance_coords = (1, floor_y - 1)
    room.exit_coords = (fallback_width - 2, floor_y - 1)

    # Ensure the entrance and exit spots are AIR (door openings)
    room.grid[room.entrance_coords] = TileCell(t="AIR", flags={"DOOR_ENTRANCE"})
    room.grid[room.exit_coords] = TileCell(t="AIR", flags={"DOOR_EXIT"})

    return room