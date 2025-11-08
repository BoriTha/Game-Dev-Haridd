"""
Tile System Utilities
Helper functions for working with the new tile system.
"""

from typing import Tuple, Optional, List
import pygame
from config import TILE, TILE_AIR, TILE_FLOOR, TILE_WALL, TILE_SOLID, TILE_COLORS


def is_solid_tile(tile_value: int) -> bool:
    """Check if a tile has any collision."""
    return tile_value in (TILE_WALL, TILE_SOLID)


def is_platform_tile(tile_value: int) -> bool:
    """Check if a tile is a floor/platform (top-only collision)."""
    return tile_value == TILE_FLOOR


def is_wall_tile(tile_value: int) -> bool:
    """Check if a tile is a full wall."""
    return tile_value == TILE_WALL


def is_ceiling_tile(tile_value: int) -> bool:
    """Check if a tile is a ceiling/overhang (no top collision)."""
    return tile_value == TILE_SOLID


def has_top_collision(tile_value: int) -> bool:
    """Check if entity can land on top of this tile."""
    return tile_value in (TILE_FLOOR, TILE_WALL)


def has_side_collision(tile_value: int) -> bool:
    """Check if tile blocks horizontal movement."""
    return tile_value in (TILE_WALL, TILE_SOLID)


def has_bottom_collision(tile_value: int) -> bool:
    """Check if tile blocks upward movement."""
    return tile_value in (TILE_WALL, TILE_SOLID)


def get_tile_color(tile_value: int) -> Optional[Tuple[int, int, int]]:
    """Get the render color for a tile type."""
    return TILE_COLORS.get(tile_value)


def should_render_tile(tile_value: int) -> bool:
    """Check if a tile should be rendered."""
    return tile_value != TILE_AIR


def get_tile_rect(grid_x: int, grid_y: int) -> pygame.Rect:
    """Convert grid coordinates to pixel rectangle."""
    return pygame.Rect(grid_x * TILE, grid_y * TILE, TILE, TILE)


def check_collision_at_tile(grid: List[List[int]], tile_x: int, tile_y: int,
                           check_sides: bool = True, check_top: bool = True,
                           check_bottom: bool = True) -> bool:
    """
    Check collision at a specific tile position based on collision type.

    Args:
        grid: 2D grid of tile values
        tile_x, tile_y: Tile coordinates to check
        check_sides: Whether to check horizontal collision
        check_top: Whether to check top collision
        check_bottom: Whether to check bottom collision

    Returns:
        True if collision detected based on specified directions
    """
    if not (0 <= tile_y < len(grid) and 0 <= tile_x < len(grid[0])):
        return True  # Out of bounds = solid

    tile = grid[tile_y][tile_x]

    if check_sides and has_side_collision(tile):
        return True

    if check_top and has_top_collision(tile):
        return True

    if check_bottom and has_bottom_collision(tile):
        return True

    return False