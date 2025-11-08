"""
Generation Algorithms - Implements BSP, cellular automata, and Perlin noise for level generation
"""

import random
import math
from typing import List, Tuple, Optional, Dict, Any
from dataclasses import dataclass


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
            2D grid where 1 = wall, 0 = floor
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
        
        return grid
    
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
        
        return grid
    
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
        """Generate dungeon-style level using BSP with sealed boundaries"""
        rooms = self.bsp.generate(seed)

        # Convert rooms to grid (1 = wall, 0 = floor)
        grid = [[1 for _ in range(self.width)] for _ in range(self.height)]

        for room in rooms:
            # Clamp room carving to stay within 1-tile margin to avoid touching outer boundary
            start_y = max(1, room.y)
            end_y = min(room.y + room.height, self.height - 1)
            start_x = max(1, room.x)
            end_x = min(room.x + room.width, self.width - 1)

            for y in range(start_y, end_y):
                for x in range(start_x, end_x):
                    grid[y][x] = 0  # Floor

        # Final safety: ensure outer ring is fully sealed as walls
        self._seal_boundaries(grid)

        return {
            'grid': grid,
            'rooms': rooms,
            'type': 'dungeon',
            'spawn_points': self._find_spawn_points(grid, rooms)
        }
    
    def _generate_cave(self, seed: int) -> Dict[str, Any]:
        """Generate cave-style level using cellular automata"""
        grid = self.cellular.generate(seed)
        
        return {
            'grid': grid,
            'rooms': [],  # Caves don't have explicit rooms
            'type': 'cave',
            'spawn_points': self._find_spawn_points(grid, [])
        }
    
    def _generate_outdoor(self, seed: int) -> Dict[str, Any]:
        """Generate outdoor-style level using Perlin noise"""
        grid = self.perlin.generate(seed, threshold=0.3)
        
        return {
            'grid': grid,
            'rooms': [],  # Outdoor areas don't have explicit rooms
            'type': 'outdoor',
            'spawn_points': self._find_spawn_points(grid, [])
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
            'spawn_points': bsp_data['spawn_points']
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