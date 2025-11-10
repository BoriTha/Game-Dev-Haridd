from typing import Dict, Optional
from .tile_types import TileType
from .tile_data import (
    TileData,
    CollisionProperties,
    VisualProperties,
    PhysicalProperties,
    InteractionProperties,
    AudioProperties,
    LightingProperties
)


class TileRegistry:
    """Registry for storing and managing tile definitions."""

    def __init__(self):
        self._tiles: Dict[TileType, TileData] = {}
        self._initialize_default_tiles()

    def _initialize_default_tiles(self):
        """Initialize default tile types with their properties."""

        # Air tile
        self.register_tile(TileData(
            tile_type=TileType.AIR,
            name="Air",
            collision=CollisionProperties(
                collision_type="none",
                can_pass_through=True
            ),
            visual=VisualProperties(
                base_color=(0, 0, 0, 0)  # Transparent
            ),
            physics=PhysicalProperties(
                friction=0.0
            ),
            lighting=LightingProperties(
                transparency=1.0,
                blocks_light=False,
                casts_shadows=False
            )
        ))



        # Wall tile
        self.register_tile(TileData(
            tile_type=TileType.WALL,
            name="Wall",
            collision=CollisionProperties(
                collision_type="full",
                collision_box_size=(24, 24)
            ),
            visual=VisualProperties(
                base_color=(54, 60, 78),
                border_radius=4
            ),
            physics=PhysicalProperties(
                friction=0.8
            ),
            lighting=LightingProperties(
                blocks_light=True,
                casts_shadows=True
            ),
            audio=AudioProperties(
                contact_sound="hit_wall"
            )
        ))



        # Platform tile
        self.register_tile(TileData(
            tile_type=TileType.PLATFORM,
            name="Platform",
            collision=CollisionProperties(
                collision_type="top_only",
                can_walk_on=True,
                can_pass_through=True,
                collision_box_offset=(0, 20),
                collision_box_size=(24, 4)
            ),
            visual=VisualProperties(
                base_color=(139, 90, 43),
                border_radius=2
            ),
            physics=PhysicalProperties(
                friction=0.9
            ),
            audio=AudioProperties(
                footstep_sound="step_wood",
                contact_sound="land_wood"
            )
        ))

        # Breakable Wall tile
        self.register_tile(TileData(
            tile_type=TileType.BREAKABLE_WALL,
            name="Breakable Wall",
            collision=CollisionProperties(
                collision_type="full",
                collision_box_size=(24, 24)
            ),
            visual=VisualProperties(
                base_color=(139, 69, 19),
                border_radius=4,
                border_color=(101, 50, 14)
            ),
            physics=PhysicalProperties(
                friction=0.7,
                density=0.5
            ),
            interaction=InteractionProperties(
                breakable=True,
                health_points=3,
                resistance=0.5
            ),
            audio=AudioProperties(
                contact_sound="hit_crate",
                break_sound="break_wood"
            )
        ))



    def register_tile(self, tile_data: TileData):
        """Register a new tile type."""
        self._tiles[tile_data.tile_type] = tile_data

    def get_tile(self, tile_type: TileType) -> Optional[TileData]:
        """Get tile data by type."""
        return self._tiles.get(tile_type)

    def get_all_tiles(self) -> Dict[TileType, TileData]:
        """Get all registered tiles."""
        return self._tiles.copy()

    def tiles_with_property(self, property_name: str, value=True):
        """Get all tiles that have a specific property value."""
        matching_tiles = []
        for tile_data in self._tiles.values():
            if hasattr(tile_data, property_name):
                if getattr(tile_data, property_name) == value:
                    matching_tiles.append(tile_data)
        return matching_tiles

    def register_custom_tile(self, tile_data: TileData):
        """Register a custom tile type (for user-defined tiles)."""
        if tile_data.tile_type in self._tiles:
            raise ValueError(f"Tile type {tile_data.tile_type} already registered")
        self.register_tile(tile_data)


# Global tile registry instance
tile_registry = TileRegistry()