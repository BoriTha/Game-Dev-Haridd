"""PCG Level and Room Data System

Adds Area/Region dataclasses and helpers for PCG-driven area mappings
(spawn regions, biomes, exclusion zones, hazards, etc.).
"""

from dataclasses import dataclass, asdict, field
from typing import List, Dict, Any, Optional, Tuple
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
    # Optional areas metadata as a list of dicts (keeps JSON-compatible shape)
    areas: Optional[List[Dict[str, Any]]] = None
    
    def __post_init__(self):
        if self.door_exits is None:
            self.door_exits = {}
        # keep areas as-is (may be list of dicts)


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
        """Create from dictionary.

        Room `areas` are left as raw dict lists and can be converted by
        helper functions when needed by the loader.
        """
        levels: List[LevelData] = []
        for level_data in data.get("levels", []):
            rooms: List[RoomData] = []
            for room_data in level_data.get("rooms", []):
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


# ----- Area / Region dataclasses and helpers -----

@dataclass
class AreaRect:
    x: int
    y: int
    w: int
    h: int

    def tiles(self) -> List[Tuple[int, int]]:
        tiles: List[Tuple[int, int]] = []
        for yy in range(self.y, self.y + self.h):
            for xx in range(self.x, self.x + self.w):
                tiles.append((xx, yy))
        return tiles


@dataclass
class AreaRegion:
    region_id: str
    label: Optional[str] = None
    kind: str = "spawn"  # e.g. spawn, no_spawn, hazard, biome, player_spawn
    rects: List[AreaRect] = field(default_factory=list)
    properties: Dict[str, Any] = field(default_factory=dict)
    allowed_enemy_types: Optional[List[str]] = None
    banned_enemy_types: Optional[List[str]] = None
    spawn_cap: Optional[int] = None
    priority: int = 0

    def contains_tile(self, x: int, y: int) -> bool:
        for r in self.rects:
            if r.x <= x < r.x + r.w and r.y <= y < r.y + r.h:
                return True
        return False

    def area_size(self) -> int:
        s = 0
        for r in self.rects:
            s += r.w * r.h
        return s

    def to_dict(self) -> Dict[str, Any]:
        return {
            "region_id": self.region_id,
            "label": self.label,
            "kind": self.kind,
            "rects": [{"x": r.x, "y": r.y, "w": r.w, "h": r.h} for r in self.rects],
            "properties": self.properties,
            "allowed_enemy_types": self.allowed_enemy_types,
            "banned_enemy_types": self.banned_enemy_types,
            "spawn_cap": self.spawn_cap,
            "priority": self.priority,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "AreaRegion":
        rects = [AreaRect(**r) for r in data.get("rects", [])]
        return cls(
            region_id=str(data["region_id"]),
            label=data.get("label"),
            kind=str(data.get("kind", "spawn")),
            rects=rects,
            properties=data.get("properties", {}),
            allowed_enemy_types=data.get("allowed_enemy_types"),
            banned_enemy_types=data.get("banned_enemy_types"),
            spawn_cap=data.get("spawn_cap"),
            priority=int(data.get("priority", 0)),
        )


def expand_rects_to_tiles(rects: List[AreaRect]) -> List[Tuple[int, int]]:
    out: List[Tuple[int, int]] = []
    for r in rects:
        out.extend(r.tiles())
    return out


def build_tile_region_map(room_tiles_width: int, room_tiles_height: int, regions: List[AreaRegion]) -> Dict[Tuple[int,int], List[AreaRegion]]:
    """
    Build mapping: (x,y) -> list of AreaRegion sorted by priority (desc).
    Clamps rects to room bounds.
    """
    tile_map: Dict[Tuple[int,int], List[AreaRegion]] = {}
    for region in regions:
        for rect in region.rects:
            rx0 = max(0, rect.x)
            ry0 = max(0, rect.y)
            rx1 = min(room_tiles_width, rect.x + rect.w)
            ry1 = min(room_tiles_height, rect.y + rect.h)
            for yy in range(ry0, ry1):
                for xx in range(rx0, rx1):
                    tile_map.setdefault((xx, yy), []).append(region)
    # Sort region lists by priority (higher first)
    for coords, regs in tile_map.items():
        regs.sort(key=lambda r: r.priority, reverse=True)
    return tile_map


def top_region_for_tile(tile_map: Dict[Tuple[int,int], List[AreaRegion]], x: int, y: int) -> Optional[AreaRegion]:
    regs = tile_map.get((x, y))
    if not regs:
        return None
    return regs[0]


# ----- Room helper for legacy-friendly conversion -----

def room_areas_from_raw(raw: Optional[List[Dict[str, Any]]]) -> List[AreaRegion]:
    """Convert a raw list of dicts (as read from JSON) into AreaRegion objects."""
    if not raw:
        return []
    out: List[AreaRegion] = []
    for r in raw:
        if isinstance(r, AreaRegion):
            out.append(r)
        elif isinstance(r, dict):
            out.append(AreaRegion.from_dict(r))
    return out


# Generation helper remains unchanged

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

