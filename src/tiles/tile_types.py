from enum import IntEnum, auto


class TileType(IntEnum):
    """Enumeration of all tile types in the game."""

    # Basic tiles
    AIR = 0
    WALL = 1

    # Special tiles
    PLATFORM = 2
    BREAKABLE_WALL = 3
    DOOR = 4  # NEW: PCG door tile

    @property
    def is_solid(self) -> bool:
        """Return True if tile blocks movement completely."""
        return self in (TileType.WALL, TileType.BREAKABLE_WALL)

    @property
    def is_platform(self) -> bool:
        """Return True if tile is a jump-through platform."""
        return self in (TileType.PLATFORM,)

    @property
    def is_breakable(self) -> bool:
        """Return True if tile can be destroyed."""
        return self in (TileType.BREAKABLE_WALL,)

    @property
    def is_door(self) -> bool:
        return self == TileType.DOOR

    @property
    def has_collision(self) -> bool:
        """Return True if tile has any collision."""
        return self != TileType.AIR

    @property
    def name(self) -> str:
        """Return human-readable name."""
        return {
            TileType.AIR: "Air",
            TileType.WALL: "Wall",
            TileType.PLATFORM: "Platform",
            TileType.BREAKABLE_WALL: "Breakable Wall",
            TileType.DOOR: "Door",  # NEW
        }.get(self, f"Tile_{self.value}")