"""
Generation Algorithms - Implements BSP, cellular automata, and Perlin noise for level generation
"""

import random
import math
from typing import List, Tuple, Optional, Dict, Any
from dataclasses import dataclass
from config import TILE_AIR, TILE_FLOOR, TILE_WALL, TILE_SOLID


def convert_legacy_grid(grid: List[List[int]]) -> List[List[int]]:
    """
    Convert legacy grid values to new tile system.
    Old system: 0 = floor, 1 = wall
    New system: 0 = air, 1 = floor, 2 = wall, 3 = solid
    """
    converted = []
    for row in grid:
        new_row = []
        for tile in row:
            if tile == 0:  # Old floor becomes new floor
                new_row.append(TILE_FLOOR)
            elif tile == 1:  # Old wall becomes new wall
                new_row.append(TILE_WALL)
            else:
                new_row.append(TILE_AIR)  # Unknown becomes air
        converted.append(new_row)
    return converted


@dataclass
class Room:
    """Represents a room in the level"""
    x: int
    y: int
    width: int
    height: int
    
    @property
    def center(self) -> Tuple[int, int]:
        """Get center coordinates of room"""
        return (self.x + self.width // 2, self.y + self.height // 2)
    
    @property
    def bounds(self) -> Tuple[int, int, int, int]:
        """Get bounds as (x, y, width, height)"""
        return (self.x, self.y, self.width, self.height)
    
    def intersects(self, other: 'Room') -> bool:
        """Check if this room intersects with another room"""
        return not (self.x + self.width < other.x or 
                  other.x + other.width < self.x or
                  self.y + self.height < other.y or
                  other.y + other.height < self.y)


class BSPNode:
    """Node in Binary Space Partitioning tree"""
    
    def __init__(self, x: int, y: int, width: int, height: int, horizontal: bool = True):
        self.x = x
        self.y = y
        self.width = width
        self.height = height
        self.horizontal = horizontal
        self.left: Optional['BSPNode'] = None
        self.right: Optional['BSPNode'] = None
        self.room: Optional[Room] = None


class BSPGenerator:
    """Binary Space Partitioning algorithm for room-based level generation"""
    
    def __init__(self, width: int, height: int, min_room_size: int = 5, max_room_size: int = 15):
        self.width = width
        self.height = height
        self.min_room_size = min_room_size
        self.max_room_size = max_room_size
        self.rng = random.Random()
    
    def generate(self, seed: int) -> List[Room]:
        """
        Generate rooms using BSP algorithm
        
        Args:
            seed: Random seed for generation
            
        Returns:
            List of generated rooms
        """
        self.rng.seed(seed)
        
        # Create root node
        root = BSPNode(0, 0, self.width, self.height)
        
        # Recursively split the space
        self._split_node(root, self.min_room_size)
        
        # Create rooms in leaf nodes
        rooms = []
        self._create_rooms(root, rooms)
        
        # Connect rooms with corridors
        connected_rooms = self._connect_rooms(rooms)
        
        return connected_rooms
    
    def _split_node(self, node: BSPNode, min_size: int):
        """Recursively split a BSP node"""
        if node.width < 2 * min_size or node.height < 2 * min_size:
            return
        
        # Choose split direction
        horizontal = node.horizontal
        
        # Determine split position
        if horizontal:
            if node.height < 2 * min_size:
                return
            split_pos = self.rng.randint(node.y + min_size, node.y + node.height - min_size)
            
            node.left = BSPNode(node.x, node.y, node.width, split_pos - node.y, False)
            node.right = BSPNode(node.x, split_pos, node.width, node.y + node.height - split_pos, False)
        else:
            if node.width < 2 * min_size:
                return
            split_pos = self.rng.randint(node.x + min_size, node.x + node.width - min_size)
            
            node.left = BSPNode(node.x, node.y, split_pos - node.x, node.height, True)
            node.right = BSPNode(split_pos, node.y, node.x + node.width - split_pos, node.height, True)
        
        # Recursively split child nodes
        self._split_node(node.left, min_size)
        self._split_node(node.right, min_size)
    
    def _create_rooms(self, node: BSPNode, rooms: List[Room]):
        """Create rooms in leaf nodes"""
        if node.left is None and node.right is None:
            # This is a leaf node, create a room
            room_width = min(self.rng.randint(self.min_room_size, min(node.width, self.max_room_size)), node.width)
            room_height = min(self.rng.randint(self.min_room_size, min(node.height, self.max_room_size)), node.height)
            
            room_x = node.x + self.rng.randint(0, max(0, node.width - room_width))
            room_y = node.y + self.rng.randint(0, max(0, node.height - room_height))
            
            node.room = Room(room_x, room_y, room_width, room_height)
            rooms.append(node.room)
        else:
            if node.left:
                self._create_rooms(node.left, rooms)
            if node.right:
                self._create_rooms(node.right, rooms)
    
    def _connect_rooms(self, rooms: List[Room]) -> List[Room]:
        """Connect rooms with corridors"""
        if not rooms:
            return rooms
        
        # Sort rooms by center position for better connectivity
        sorted_rooms = sorted(rooms, key=lambda r: (r.center[0], r.center[1]))
        
        # Connect each room to its nearest neighbor
        connected = [sorted_rooms[0]]
        
        for i in range(1, len(sorted_rooms)):
            current_room = sorted_rooms[i]
            
            # Find nearest connected room
            nearest_room = min(connected, key=lambda r: self._distance(current_room.center, r.center))
            
            # Create corridor between rooms (represented as a thin room)
            corridor = self._create_corridor(current_room, nearest_room)
            if corridor:
                connected.append(corridor)
            
            connected.append(current_room)
        
        return connected
    
    def _distance(self, p1: Tuple[int, int], p2: Tuple[int, int]) -> float:
        """Calculate Euclidean distance between two points"""
        return math.sqrt((p1[0] - p2[0])**2 + (p1[1] - p2[1])**2)
    
    def _create_corridor(self, room1: Room, room2: Room) -> Optional[Room]:
        """Create a corridor between two rooms"""
        x1, y1 = room1.center
        x2, y2 = room2.center
        
        # Create L-shaped corridor
        corridor_width = 2  # Corridor width in tiles
        
        # Horizontal then vertical
        if self.rng.random() < 0.5:
            # Horizontal segment
            h_x = min(x1, x2)
            h_width = abs(x2 - x1) + corridor_width
            h_y = y1 - corridor_width // 2
            h_height = corridor_width
            
            # Vertical segment
            v_x = x2 - corridor_width // 2
            v_width = corridor_width
            v_y = min(y1, y2)
            v_height = abs(y2 - y1) + corridor_width
            
            # Return the larger segment as the corridor room
            if h_width > v_height:
                return Room(h_x, h_y, h_width, h_height)
            else:
                return Room(v_x, v_y, v_width, v_height)
        else:
            # Vertical then horizontal
            v_x = x1 - corridor_width // 2
            v_width = corridor_width
            v_y = min(y1, y2)
            v_height = abs(y2 - y1) + corridor_width
            
            h_x = min(x1, x2)
            h_width = abs(x2 - x1) + corridor_width
            h_y = y2 - corridor_width // 2
            h_height = corridor_width
            
            # Return the larger segment as the corridor room
            if v_height > h_width:
                return Room(v_x, v_y, v_width, v_height)
            else:
                return Room(h_x, h_y, h_width, h_height)


class CellularAutomata:
    """Cellular automata algorithm for cave-like level generation"""
    
    def __init__(self, width: int, height: int):
        self.width = width
        self.height = height
        self.rng = random.Random()
    
    def generate(self, seed: int, iterations: int = 5, density: float = 0.45) -> List[List[int]]:
        """
        Generate cave using cellular automata
        
        Args:
            seed: Random seed for generation
            iterations: Number of smoothing iterations
            density: Initial wall density (0-1)
            
        Returns:
            2D grid where 1 = wall, 0 = floor (will be converted to new system)
        """
        self.rng.seed(seed)
        
        # Initialize random grid
        grid = [[1 if self.rng.random() < density else 0 for _ in range(self.width)] 
                 for _ in range(self.height)]
        
        # Apply cellular automata rules
        for _ in range(iterations):
            grid = self._smooth_grid(grid)
        
        # Ensure connectivity
        grid = self._ensure_connectivity(grid)

        # Convert to new tile system
        return convert_legacy_grid(grid)
    
    def _smooth_grid(self, grid: List[List[int]]) -> List[List[int]]:
        """Apply smoothing rules to grid"""
        new_grid = [[0 for _ in range(self.width)] for _ in range(self.height)]
        
        for y in range(self.height):
            for x in range(self.width):
                wall_count = self._count_walls(grid, x, y)
                
                # Apply rules
                if wall_count >= 5:
                    new_grid[y][x] = 1  # Wall
                else:
                    new_grid[y][x] = 0  # Floor
        
        return new_grid
    
    def _count_walls(self, grid: List[List[int]], x: int, y: int) -> int:
        """Count walls in 3x3 neighborhood"""
        count = 0
        for dy in range(-1, 2):
            for dx in range(-1, 2):
                nx, ny = x + dx, y + dy
                
                # Check bounds
                if 0 <= nx < self.width and 0 <= ny < self.height:
                    count += grid[ny][nx]
                else:
                    # Out of bounds counts as wall
                    count += 1
        
        return count
    
    def _ensure_connectivity(self, grid: List[List[int]]) -> List[List[int]]:
        """Ensure the cave has connectivity"""
        # Find all floor tiles
        floor_tiles = []
        for y in range(self.height):
            for x in range(self.width):
                if grid[y][x] == 0:
                    floor_tiles.append((x, y))
        
        if not floor_tiles:
            return grid
        
        # Find connected component from first floor tile
        visited = set()
        to_check = [floor_tiles[0]]
        
        while to_check:
            x, y = to_check.pop()
            if (x, y) in visited:
                continue
            
            visited.add((x, y))
            
            # Check neighbors
            for dx, dy in [(0, 1), (1, 0), (0, -1), (-1, 0)]:
                nx, ny = x + dx, y + dy
                if (0 <= nx < self.width and 0 <= ny < self.height and
                    grid[ny][nx] == 0 and (nx, ny) not in visited):
                    to_check.append((nx, ny))
        
        # If not all floor tiles are connected, create tunnels
        if len(visited) < len(floor_tiles):
            grid = self._create_tunnels(grid, visited, floor_tiles)
        
        return grid
    
    def _create_tunnels(self, grid: List[List[int]], visited: set, floor_tiles: List[Tuple[int, int]]) -> List[List[int]]:
        """Create tunnels to connect disconnected areas"""
        unvisited = [tile for tile in floor_tiles if tile not in visited]
        
        for tile in unvisited:
            # Find nearest visited tile
            nearest = min(visited, key=lambda v: self._distance(tile, v))
            
            # Create tunnel between tiles
            x1, y1 = tile
            x2, y2 = nearest
            
            # Simple L-shaped tunnel
            while x1 != x2:
                grid[y1][x1] = 0
                x1 += 1 if x2 > x1 else -1
            
            while y1 != y2:
                grid[y1][x1] = 0
                y1 += 1 if y2 > y1 else -1
        
        return grid
    
    def _distance(self, p1: Tuple[int, int], p2: Tuple[int, int]) -> float:
        """Calculate Manhattan distance between two points"""
        return abs(p1[0] - p2[0]) + abs(p1[1] - p2[1])


class PerlinNoise:
    """Perlin noise implementation for organic terrain generation"""
    
    def __init__(self, width: int, height: int, scale: float = 10.0, octaves: int = 4):
        self.width = width
        self.height = height
        self.scale = scale
        self.octaves = octaves
        self.rng = random.Random()
    
    def generate(self, seed: int, threshold: float = 0.5) -> List[List[int]]:
        """
        Generate terrain using Perlin noise
        
        Args:
            seed: Random seed for generation
            threshold: Threshold for determining solid vs empty (0-1)
            
        Returns:
            2D grid where 1 = solid, 0 = empty
        """
        self.rng.seed(seed)
        
        # Generate permutation table
        permutation = self._generate_permutation()
        
        grid = [[0 for _ in range(self.width)] for _ in range(self.height)]
        
        for y in range(self.height):
            for x in range(self.width):
                # Calculate noise value
                noise_value = self._perlin_noise(x / self.scale, y / self.scale, permutation)
                
                # Apply threshold
                grid[y][x] = 1 if noise_value > threshold else 0

        # Convert to new tile system
        return convert_legacy_grid(grid)
    
    def _generate_permutation(self) -> List[int]:
        """Generate permutation table for Perlin noise"""
        permutation = list(range(256))
        self.rng.shuffle(permutation)
        
        # Duplicate for overflow
        return permutation + permutation
    
    def _perlin_noise(self, x: float, y: float, permutation: List[int]) -> float:
        """Calculate Perlin noise at given coordinates"""
        total = 0
        amplitude = 1
        frequency = 1
        max_value = 0
        
        for _ in range(self.octaves):
            total += self._interpolated_noise(x * frequency, y * frequency, permutation) * amplitude
            max_value += amplitude
            amplitude *= 0.5  # Persistence
            frequency *= 2   # Lacunarity
        
        return total / max_value
    
    def _interpolated_noise(self, x: float, y: float, permutation: List[int]) -> float:
        """Calculate interpolated noise at given coordinates"""
        # Get integer coordinates
        x_int = int(x)
        y_int = int(y)
        
        # Get fractional parts
        x_frac = x - x_int
        y_frac = y - y_int
        
        # Get hash values for corners
        v1 = self._smooth_noise(x_int, y_int, permutation)
        v2 = self._smooth_noise(x_int + 1, y_int, permutation)
        v3 = self._smooth_noise(x_int, y_int + 1, permutation)
        v4 = self._smooth_noise(x_int + 1, y_int + 1, permutation)
        
        # Interpolate
        i1 = self._interpolate(v1, v2, x_frac)
        i2 = self._interpolate(v3, v4, x_frac)
        
        return self._interpolate(i1, i2, y_frac)
    
    def _smooth_noise(self, x: int, y: int, permutation: List[int]) -> float:
        """Generate smooth noise at integer coordinates"""
        # Hash coordinates
        h = permutation[(x + permutation[y % 256]) % 256]
        
        # Generate pseudo-random value
        return (h / 255.0) * 2 - 1  # Range: [-1, 1]
    
    def _interpolate(self, a: float, b: float, x: float) -> float:
        """Linear interpolation between a and b"""
        return a * (1 - x) + b * x


class HybridGenerator:
    """Combines multiple generation algorithms for varied level types"""
    
    def __init__(self, width: int, height: int):
        self.width = width
        self.height = height
        self.bsp = BSPGenerator(width, height)
        self.cellular = CellularAutomata(width, height)
        self.perlin = PerlinNoise(width, height)
    
    def generate(self, seed: int, level_type: str = "dungeon") -> Dict[str, Any]:
        """
        Generate level using hybrid approach
        
        Args:
            seed: Random seed for generation
            level_type: Type of level to generate ("dungeon", "cave", "outdoor", "hybrid")
            
        Returns:
            Dictionary containing level data
        """
        if level_type == "dungeon":
            return self._generate_dungeon(seed)
        elif level_type == "cave":
            return self._generate_cave(seed)
        elif level_type == "outdoor":
            return self._generate_outdoor(seed)
        elif level_type == "hybrid":
            return self._generate_hybrid(seed)
        else:
            # Default to dungeon
            return self._generate_dungeon(seed)
    
    def _generate_dungeon(self, seed: int) -> Dict[str, Any]:
        """Generate dungeon-style level using BSP with sealed boundaries and themed areas"""
        rooms = self.bsp.generate(seed)

        # Mark special room types
        special_rooms = self._assign_special_rooms(rooms, seed)

        # Convert rooms to grid (1 = wall, 0 = floor)
        grid = [[1 for _ in range(self.width)] for _ in range(self.height)]

        # Carve rooms and corridors
        for i, room in enumerate(rooms):
            # Clamp room carving to stay within 1-tile margin to avoid touching outer boundary
            start_y = max(1, room.y)
            end_y = min(room.y + room.height, self.height - 1)
            start_x = max(1, room.x)
            end_x = min(room.x + room.width, self.width - 1)

            for y in range(start_y, end_y):
                for x in range(start_x, end_x):
                    grid[y][x] = 0  # Floor

        # Add special features for different room types
        grid = self._add_dungeon_features(grid, special_rooms, seed)

        # Final safety: ensure outer ring is fully sealed as walls
        self._seal_boundaries(grid)

        # Find optimal spawn points based on room types
        spawn_points = self._find_optimal_spawn_points(grid, special_rooms)

        # Convert to new tile system before returning
        converted_grid = convert_legacy_grid(grid)

        return {
            'grid': converted_grid,
            'rooms': rooms,
            'type': 'dungeon',
            'spawn_points': spawn_points,
            'special_rooms': special_rooms
        }
    
    def _generate_cave(self, seed: int) -> Dict[str, Any]:
        """Generate cave-style level using cellular automata with special areas"""
        grid = self.cellular.generate(seed)

        # Create special areas in cave and convert to rooms for consistency
        special_areas = self._create_cave_areas(grid, seed)
        special_rooms = self._convert_areas_to_rooms(special_areas, seed)

        return {
            'grid': grid,
            'rooms': [],  # Caves don't have explicit rooms
            'type': 'cave',
            'spawn_points': self._find_cave_spawn_points(grid, special_areas),
            'special_rooms': special_rooms,  # Use consistent key name
            'special_areas': special_areas   # Keep for backwards compatibility
        }
    
    def _generate_outdoor(self, seed: int) -> Dict[str, Any]:
        """Generate outdoor-style level using Perlin noise with clearings"""
        grid = self.perlin.generate(seed, threshold=0.3)

        # Create clearings for special areas
        clearings = self._create_outdoor_clearings(grid, seed)

        # Convert some clearings to special rooms
        special_rooms = self._convert_clearings_to_special_rooms(clearings, seed)

        return {
            'grid': grid,
            'rooms': clearings,  # Store clearings as pseudo-rooms
            'type': 'outdoor',
            'spawn_points': self._find_outdoor_spawn_points(grid, clearings),
            'special_rooms': special_rooms,
            'clearings': clearings
        }
    
    def _generate_hybrid(self, seed: int) -> Dict[str, Any]:
        """Generate hybrid level combining multiple algorithms"""
        # Use BSP for main structure
        bsp_data = self._generate_dungeon(seed)
        
        # Add Perlin noise for terrain variation
        perlin_grid = self.perlin.generate(seed + 1000, threshold=0.6)
        
        # Combine grids
        combined_grid = bsp_data['grid']
        for y in range(self.height):
            for x in range(self.width):
                # Add some Perlin noise variation to dungeon
                if perlin_grid[y][x] == 1 and combined_grid[y][x] == 0:
                    # Add some walls in open areas
                    if random.Random(seed + x + y * self.width).random() < 0.1:
                        combined_grid[y][x] = 1
        
        return {
            'grid': combined_grid,
            'rooms': bsp_data['rooms'],
            'type': 'hybrid',
            'spawn_points': bsp_data['spawn_points'],
            'special_rooms': bsp_data.get('special_rooms', {})  # Pass through special rooms
        }

    def _seal_boundaries(self, grid: List[List[int]]) -> None:
        """
        Force all outer boundary tiles to be walls.

        This guarantees no path directly exits the map, while preserving
        internal connectivity carved earlier.
        """
        if not grid:
            return

        height = len(grid)
        width = len(grid[0]) if height > 0 else 0
        if width == 0:
            return

        # Top and bottom rows
        for x in range(width):
            grid[0][x] = 1
            grid[height - 1][x] = 1

        # Left and right columns
        for y in range(height):
            grid[y][0] = 1
            grid[y][width - 1] = 1
    
    def _find_spawn_points(self, grid: List[List[int]], rooms: List[Room]) -> List[Tuple[int, int]]:
        """Find suitable spawn points in the level"""
        spawn_points = []
        
        if rooms:
            # For room-based levels, spawn in room centers
            for room in rooms[:3]:  # Limit to first 3 rooms
                cx, cy = room.center
                if (0 <= cy < self.height and 0 <= cx < self.width and
                    grid[cy][cx] == 0):
                    spawn_points.append((cx, cy))
        else:
            # For non-room levels, find open areas
            for y in range(1, self.height - 1, 5):
                for x in range(1, self.width - 1, 5):
                    if grid[y][x] == 0:
                        # Check if area is clear
                        clear = True
                        for dy in range(-1, 2):
                            for dx in range(-1, 2):
                                ny, nx = y + dy, x + dx
                                if (0 <= ny < self.height and 0 <= nx < self.width and
                                    grid[ny][nx] == 1):
                                    clear = False
                                    break
                            if not clear:
                                break
                        
                        if clear and len(spawn_points) < 3:
                            spawn_points.append((x, y))
        
        return spawn_points

    def _assign_special_rooms(self, rooms: List[Room], seed: int) -> Dict[str, Room]:
        """Assign special purposes to rooms (spawn, portal, merchant, etc.)"""
        rng = random.Random(seed)
        special_rooms = {}

        if not rooms:
            return special_rooms

        # Sort rooms by distance from center for strategic placement
        center_x, center_y = self.width // 2, self.height // 2
        sorted_rooms = sorted(rooms, key=lambda r: abs(r.center[0] - center_x) + abs(r.center[1] - center_y))

        # Place spawn room - choose from rooms closer to center
        spawn_candidates = [r for r in sorted_rooms[:len(rooms)//2] if r.width >= 5 and r.height >= 5]
        if spawn_candidates:
            special_rooms['spawn'] = rng.choice(spawn_candidates)

        # Place portal room - choose from rooms far from spawn
        spawn_room = special_rooms.get('spawn')
        if spawn_room and len(rooms) > 2:
            far_rooms = [r for r in rooms if r != spawn_room and
                        (abs(r.center[0] - spawn_room.center[0]) +
                         abs(r.center[1] - spawn_room.center[1]) > 10)]
            if far_rooms:
                special_rooms['portal'] = rng.choice(far_rooms)

        # Place merchant room - medium distance from spawn
        if spawn_room and len(rooms) > 3:
            medium_rooms = [r for r in rooms if r != spawn_room and r != special_rooms.get('portal')]
            if medium_rooms:
                special_rooms['merchant'] = rng.choice(medium_rooms[:len(medium_rooms)//2])

        # Mark enemy spawn areas - remaining larger rooms
        for room in rooms:
            if room not in special_rooms.values() and room.width >= 4 and room.height >= 4:
                if not hasattr(room, 'room_type'):
                    room.room_type = 'enemy_area'

        return special_rooms

    def _add_dungeon_features(self, grid: List[List[int]], special_rooms: Dict[str, Room], seed: int) -> List[List[int]]:
        """Add special features to dungeon based on room types"""
        rng = random.Random(seed)

        # Add pillars in large rooms for variety
        portal_room = special_rooms.get('portal')
        if portal_room and portal_room.width >= 7 and portal_room.height >= 7:
            # Add central pillar
            px, py = portal_room.center
            if py < len(grid) - 1 and px < len(grid[0]) - 1:
                grid[py][px] = 1
                if py > 0 and px > 0:
                    grid[py-1][px] = 1
                    grid[py+1][px] = 1
                    grid[py][px-1] = 1
                    grid[py][px+1] = 1

        # Add decorative features in merchant room
        if 'merchant' in special_rooms:
            room = special_rooms['merchant']
            # Add a counter/stall
            counter_x = room.x + room.width // 2 - 1
            counter_y = room.y + room.height // 2
            for dx in range(3):
                if 0 <= counter_x + dx < len(grid[0]) and 0 <= counter_y < len(grid):
                    grid[counter_y][counter_x + dx] = 1

        return grid

    def _find_optimal_spawn_points(self, grid: List[List[int]], special_rooms: Dict[str, Room]) -> List[Tuple[int, int]]:
        """Find optimal spawn points based on special room locations"""
        spawn_points = []

        # Primary spawn point - center of spawn room
        if 'spawn' in special_rooms:
            room = special_rooms['spawn']
            cx, cy = room.center
            # Ensure it's on floor
            if 0 <= cy < len(grid) and 0 <= cx < len(grid[0]) and grid[cy][cx] == 0:
                spawn_points.append((cx, cy))

        # Portal location - center of portal room
        if 'portal' in special_rooms:
            room = special_rooms['portal']
            cx, cy = room.center
            # Ensure it's on floor
            if 0 <= cy < len(grid) and 0 <= cx < len(grid[0]) and grid[cy][cx] == 0:
                spawn_points.append((cx, cy))

        # Additional spawn points in different areas
        if len(spawn_points) < 3:
            # Find additional floor tiles
            for y in range(1, len(grid) - 1, 8):
                for x in range(1, len(grid[0]) - 1, 8):
                    if grid[y][x] == 0 and (x, y) not in spawn_points:
                        # Check area is reasonably clear
                        clear = True
                        for dy in range(-1, 2):
                            for dx in range(-1, 2):
                                ny, nx = y + dy, x + dx
                                if 0 <= ny < len(grid) and 0 <= nx < len(grid[0]):
                                    if grid[ny][nx] == 1:
                                        clear = False
                                        break
                            if not clear:
                                break
                        if clear:
                            spawn_points.append((x, y))
                            if len(spawn_points) >= 3:
                                break
                if len(spawn_points) >= 3:
                    break

        return spawn_points

    def _create_cave_areas(self, grid: List[List[int]], seed: int) -> Dict[str, List[Tuple[int, int]]]:
        """Create special areas within cave layout"""
        rng = random.Random(seed)
        special_areas = {}

        # Find large open areas
        open_areas = self._find_cave_chambers(grid)

        # Assign special purposes to chambers
        if open_areas:
            # Spawn area - largest chamber
            spawn_chamber = max(open_areas, key=len)
            special_areas['spawn'] = spawn_chamber

            # Portal area - chamber farthest from spawn
            if len(open_areas) > 1:
                spawn_center = self._get_area_center(spawn_chamber)
                farthest_chamber = max(
                    [c for c in open_areas if c != spawn_chamber],
                    key=lambda c: self._distance_centers(spawn_center, self._get_area_center(c))
                )
                special_areas['portal'] = farthest_chamber

            # Merchant area - medium-sized chamber
            if len(open_areas) > 2:
                medium_chambers = sorted(open_areas, key=len)[len(open_areas)//2]
                special_areas['merchant'] = medium_chambers[:min(20, len(medium_chambers))]

        return special_areas

    def _find_cave_chambers(self, grid: List[List[int]]) -> List[List[Tuple[int, int]]]:
        """Find distinct open chambers in the cave"""
        chambers = []
        visited = set()

        for y in range(1, len(grid) - 1):
            for x in range(1, len(grid[0]) - 1):
                if grid[y][x] == 0 and (x, y) not in visited:
                    # Found new chamber, explore it
                    chamber = []
                    to_check = [(x, y)]

                    while to_check:
                        cx, cy = to_check.pop()
                        if (cx, cy) in visited:
                            continue

                        if 0 <= cx < len(grid[0]) and 0 <= cy < len(grid) and grid[cy][cx] == 0:
                            visited.add((cx, cy))
                            chamber.append((cx, cy))

                            # Check neighbors
                            for dx, dy in [(0, 1), (1, 0), (0, -1), (-1, 0)]:
                                nx, ny = cx + dx, cy + dy
                                if (nx, ny) not in visited:
                                    to_check.append((nx, ny))

                    if len(chamber) >= 10:  # Only count significant chambers
                        chambers.append(chamber)

        return chambers

    def _get_area_center(self, area: List[Tuple[int, int]]) -> Tuple[int, int]:
        """Get approximate center of an area"""
        if not area:
            return (0, 0)
        cx = sum(x for x, y in area) // len(area)
        cy = sum(y for x, y in area) // len(area)
        return (cx, cy)

    def _distance_centers(self, c1: Tuple[int, int], c2: Tuple[int, int]) -> float:
        """Calculate distance between two center points"""
        return ((c1[0] - c2[0])**2 + (c1[1] - c2[1])**2)**0.5

    def _find_cave_spawn_points(self, grid: List[List[int]], special_areas: Dict[str, List[Tuple[int, int]]]) -> List[Tuple[int, int]]:
        """Find spawn points in cave special areas"""
        spawn_points = []

        # Spawn in spawn area
        if 'spawn' in special_areas:
            center = self._get_area_center(special_areas['spawn'])
            if grid[center[1]][center[0]] == 0:
                spawn_points.append(center)

        # Portal in portal area
        if 'portal' in special_areas:
            center = self._get_area_center(special_areas['portal'])
            if grid[center[1]][center[0]] == 0:
                spawn_points.append(center)

        # Additional spawn points
        while len(spawn_points) < 3:
            for y in range(1, len(grid) - 1, 5):
                for x in range(1, len(grid[0]) - 1, 5):
                    if grid[y][x] == 0 and (x, y) not in spawn_points:
                        spawn_points.append((x, y))
                        if len(spawn_points) >= 3:
                            break
                if len(spawn_points) >= 3:
                    break

        return spawn_points

    def _create_outdoor_clearings(self, grid: List[List[int]], seed: int) -> List[Room]:
        """Create clearings in outdoor level"""
        rng = random.Random(seed)
        clearings = []

        # Find potential clearing locations
        for _ in range(5 + rng.randint(0, 3)):
            cx = rng.randint(5, self.width - 5)
            cy = rng.randint(5, self.height - 5)
            radius = rng.randint(3, 6)

            # Create circular clearing
            clearing_tiles = []
            for y in range(max(1, cy - radius), min(self.height - 1, cy + radius)):
                for x in range(max(1, cx - radius), min(self.width - 1, cx + radius)):
                    if (x - cx)**2 + (y - cy)**2 <= radius**2:
                        grid[y][x] = 0  # Clear the tile
                        clearing_tiles.append((x, y))

            if len(clearing_tiles) >= 20:
                # Convert to Room object for consistency
                min_x = min(x for x, y in clearing_tiles)
                max_x = max(x for x, y in clearing_tiles)
                min_y = min(y for x, y in clearing_tiles)
                max_y = max(y for x, y in clearing_tiles)
                clearing = Room(min_x, min_y, max_x - min_x + 1, max_y - min_y + 1)
                clearings.append(clearing)

        return clearings

    def _find_outdoor_spawn_points(self, grid: List[List[int]], clearings: List[Room]) -> List[Tuple[int, int]]:
        """Find spawn points in outdoor clearings"""
        spawn_points = []

        if clearings:
            # Use centers of largest clearings
            sorted_clearings = sorted(clearings, key=lambda r: r.width * r.height, reverse=True)

            for i, clearing in enumerate(sorted_clearings[:3]):
                cx, cy = clearing.center
                if 0 <= cy < len(grid) and 0 <= cx < len(grid[0]) and grid[cy][cx] == 0:
                    spawn_points.append((cx, cy))

        return spawn_points

    def _convert_areas_to_rooms(self, special_areas: Dict[str, List[Tuple[int, int]]], seed: int) -> Dict[str, Room]:
        """Convert special areas to Room objects for consistency with area builder"""
        import random
        rng = random.Random(seed)
        special_rooms = {}

        for area_type, area_tiles in special_areas.items():
            if not area_tiles:
                continue

            # Find bounding box of area
            min_x = min(x for x, y in area_tiles)
            max_x = max(x for x, y in area_tiles)
            min_y = min(y for x, y in area_tiles)
            max_y = max(y for x, y in area_tiles)

            # Create room with some padding
            padding = 1
            x = max(0, min_x - padding)
            y = max(0, min_y - padding)
            width = min(self.width - x, max_x - min_x + 1 + 2 * padding)
            height = min(self.height - y, max_y - min_y + 1 + 2 * padding)

            # Ensure minimum size
            width = max(3, width)
            height = max(3, height)

            special_rooms[area_type] = Room(x, y, width, height)

        return special_rooms

    def _convert_clearings_to_special_rooms(self, clearings: List[Room], seed: int) -> Dict[str, Room]:
        """Convert some clearings to special rooms for outdoor levels"""
        import random
        rng = random.Random(seed)
        special_rooms = {}

        if len(clearings) < 3:
            # Not enough clearings, create minimal special rooms
            # Spawn area
            spawn_x, spawn_y = 5, 5
            special_rooms['spawn'] = Room(spawn_x, spawn_y, 4, 4)

            # Portal area
            portal_x, portal_y = self.width - 9, 5
            special_rooms['portal'] = Room(portal_x, portal_y, 4, 4)

            # Merchant area
            merchant_x, merchant_y = self.width // 2 - 2, self.height // 2 - 2
            special_rooms['merchant'] = Room(merchant_x, merchant_y, 4, 4)
        else:
            # Use largest clearings for special rooms
            sorted_clearings = sorted(clearings, key=lambda r: r.width * r.height, reverse=True)

            # Assign special rooms to best clearings
            if len(sorted_clearings) >= 1:
                special_rooms['spawn'] = sorted_clearings[0]
            if len(sorted_clearings) >= 2:
                special_rooms['portal'] = sorted_clearings[1]
            if len(sorted_clearings) >= 3:
                special_rooms['merchant'] = sorted_clearings[2]

        return special_rooms