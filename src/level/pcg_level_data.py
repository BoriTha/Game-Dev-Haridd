"""PCG Level and Room Data System"""

from dataclasses import dataclass, asdict
from typing import List, Dict, Any, Optional
import json
import os
import sys

# Add project root to path for imports
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))

from config import TILE_AIR, TILE_WALL


@dataclass
class PCGConfig:
    """Configuration for procedural level generation."""
    num_levels: int = 3
    rooms_per_level: int = 6
    room_width: int = 40
    room_height: int = 30
    
    # Tile IDs to use (aligned with config.py and tile system)
    air_tile_id: int = TILE_AIR
    wall_tile_id: int = TILE_WALL
    
    # Generation options
    add_doors: bool = True
    door_entrance_tile_id: int = 2  # DOOR_ENTRANCE
    door_exit_tile_id: int = 3     # DOOR_EXIT (legacy)
    door_exit_1_tile_id: int = 4   # DOOR_EXIT_1
    door_exit_2_tile_id: int = 5   # DOOR_EXIT_2


@dataclass
class RoomData:
    """Data structure for a single room."""
    level_id: int
    room_index: int
    room_letter: str
    room_code: str
    tiles: List[List[int]]  # 2D grid of tile IDs
    entrance_from: Optional[str] = None  # Which room this room's entrance comes from
    door_exits: Optional[Dict[str, Dict[str, object]]] = None  # Maps exit keys to structured targets
    
    def __post_init__(self):
        if self.door_exits is None:
            self.door_exits = {}


@dataclass
class LevelData:
    """Data structure for a single level containing multiple rooms."""
    level_id: int
    rooms: List[RoomData]


@dataclass
class LevelSet:
    """Complete set of levels with all rooms."""
    levels: List[LevelData]
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to JSON-serializable dictionary."""
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "LevelSet":
        """Create from dictionary."""
        levels = []
        for level_data in data["levels"]:
            rooms = []
            for room_data in level_data["rooms"]:
                rooms.append(RoomData(**room_data))
            levels.append(LevelData(
                level_id=level_data["level_id"],
                rooms=rooms
            ))
        return cls(levels=levels)
    
    def save_to_json(self, filepath: str) -> None:
        """Save level set to JSON file."""
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        with open(filepath, 'w') as f:
            json.dump(self.to_dict(), f, indent=2)
    
    @classmethod
    def load_from_json(cls, filepath: str) -> "LevelSet":
        """Load level set from JSON file."""
        with open(filepath, 'r') as f:
            data = json.load(f)
        return cls.from_dict(data)
    
    def get_room(self, level_id: int, room_code: str) -> Optional[RoomData]:
        """Get a specific room by level ID and room code."""
        for level in self.levels:
            if level.level_id == level_id:
                for room in level.rooms:
                    if room.room_code == room_code:
                        return room
        return None
    
    def get_level(self, level_id: int) -> Optional[LevelData]:
        """Get a specific level by ID."""
        for level in self.levels:
            if level.level_id == level_id:
                return level
        return None


def generate_room_tiles(
    level_id: int,
    room_index: int,
    room_letter: str,
    width: int,
    height: int,
    config: PCGConfig
) -> List[List[int]]:
    """
    Generate a 2D grid of tile IDs for a room.
    Replace this with your actual PCG algorithm.
    """
    # Simple placeholder: walls around border, floor inside
    grid: List[List[int]] = []
    
    for y in range(height):
        row: List[int] = []
        for x in range(width):
            # Border walls
            if x == 0 or x == width - 1 or y == 0 or y == height - 1:
                row.append(config.wall_tile_id)
            else:
                row.append(config.air_tile_id)
        grid.append(row)
    
    # Do not place door tiles here. Door tiles are placed at load time
    # based on the logical room.door_exits and room.entrance_from metadata.
    return grid

# Generation orchestration removed from this module.
# This file now provides dataclasses and helper functions only.
# Use `src/level/pcg_generator_simple.py` for full generation.

if __name__ == "__main__":
    import logging
    logger = logging.getLogger(__name__)
    # Test helpers when run directly (no full generation)
    from src.level.config_loader import load_pcg_config
    config = load_pcg_config()
    tiles = generate_room_tiles(
        level_id=1,
        room_index=0,
        room_letter="A",
        width=config.room_width,
        height=config.room_height,
        config=config
    )
    logger.info("Generated test room tiles: %dx%d", len(tiles), len(tiles[0]))
    logger.info("Helper functions work correctly.")
