from enum import IntEnum, auto


class TileType(IntEnum):
    """Enumeration of all tile types in the game."""

    # Basic tiles
    AIR = 0
    FLOOR = 1
    WALL = 2
    SOLID = 3

    # Special tiles
    PLATFORM = 4
    BREAKABLE_WALL = 5
    BREAKABLE_FLOOR = 6

    # Future extension slots
    ONE_WAY_PLATFORM = auto()
    MOVING_PLATFORM = auto()
    SLOPE_UP = auto()
    SLOPE_DOWN = auto()
    LADDER = auto()
    WATER = auto()
    LAVA = auto()
    SPIKE = auto()
    SWITCH = auto()
    DOOR = auto()

    @property
    def is_solid(self) -> bool:
        """Return True if tile blocks movement completely."""
        return self in (TileType.WALL, TileType.SOLID, TileType.BREAKABLE_WALL)

    @property
    def is_platform(self) -> bool:
        """Return True if tile is a jump-through platform."""
        return self in (TileType.PLATFORM, TileType.BREAKABLE_FLOOR, TileType.ONE_WAY_PLATFORM)

    @property
    def is_breakable(self) -> bool:
        """Return True if tile can be destroyed."""
        return self in (TileType.BREAKABLE_WALL, TileType.BREAKABLE_FLOOR)

    @property
    def has_collision(self) -> bool:
        """Return True if tile has any collision."""
        return self != TileType.AIR

    @property
    def name(self) -> str:
        """Return human-readable name."""
        return {
            TileType.AIR: "Air",
            TileType.FLOOR: "Floor",
            TileType.WALL: "Wall",
            TileType.SOLID: "Solid",
            TileType.PLATFORM: "Platform",
            TileType.BREAKABLE_WALL: "Breakable Wall",
            TileType.BREAKABLE_FLOOR: "Breakable Floor",
        }.get(self, f"Tile_{self.value}")