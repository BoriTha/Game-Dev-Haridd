"""Door interaction and room transition system for PCG levels.

This module provides the DoorSystem class that handles door interactions,
room transitions, and spawn point management for the PCG level system.
"""

import logging
from typing import Optional, Tuple, Dict, Any, List
from src.level.level_loader import LevelLoader, get_room_exits, get_room_entrance_from
from src.tiles.tile_types import TileType
from src.core.interaction import find_spawn_point
from config import TILE

logger = logging.getLogger(__name__)


class DoorSystem:
    """Handles door interactions and room transitions for PCG levels."""
    
    def __init__(self):
        """Initialize the door system."""
        self.level_loader = LevelLoader()
        try:
            self.level_loader.load_levels()
        except Exception as e:
            logger.warning(f"Failed to load levels in DoorSystem: {e}")
        
        self.current_level_id: Optional[int] = None
        self.current_room_code: Optional[str] = None
        self.current_tile_grid: Optional[List[List[int]]] = None
        self._last_transition: Optional[Dict[str, Any]] = None
        
    def set_current_tiles(self, level_id: int, room_code: str, tile_grid: Optional[List[List[int]]] = None) -> None:
        """Set the current room tiles and update room state.
        
        Args:
            level_id: The level ID
            room_code: The room code  
            tile_grid: The tile grid for the current room
        """
        self.current_level_id = level_id
        self.current_room_code = room_code
        self.current_tile_grid = tile_grid
        self._last_transition = None
        
    def load_room(self, level_id: int, room_code: str) -> None:
        """Load a room and set it as current.
        
        Args:
            level_id: The level ID
            room_code: The room code
        """
        try:
            room = self.level_loader.get_room(level_id, room_code)
            if room:
                self.set_current_tiles(level_id, room_code, room.tiles)
            else:
                logger.warning(f"Room {level_id}/{room_code} not found")
        except Exception as e:
            logger.error(f"Failed to load room {level_id}/{room_code}: {e}")
            
    def handle_door_interaction(self, player_rect, tile_size: int, is_e_pressed: bool) -> Optional[Tuple[str, int, int]]:
        """Handle door interaction for the player.
        
        Args:
            player_rect: The player's rectangle
            tile_size: Size of tiles
            is_e_pressed: Whether the E key is pressed
            
        Returns:
            Tuple of (prompt_text, x, y) if near a door, None otherwise
        """
        if not self.current_tile_grid or self.current_level_id is None or self.current_room_code is None:
            return None
            
        # Get room exits
        try:
            exits = get_room_exits(self.current_level_id, self.current_room_code)
        except Exception as e:
            logger.error(f"Failed to get room exits: {e}")
            return None
            
        if not exits:
            return None
            
        # Check player proximity to doors
        player_center_x = player_rect.centerx
        player_center_y = player_rect.centery
        
        # Search for door tiles near the player
        search_radius = tile_size * 2
        door_found = False
        door_info = None
        
        for ty, row in enumerate(self.current_tile_grid):
            for tx, tile_val in enumerate(row):
                if tile_val in (TileType.DOOR_EXIT_1.value, TileType.DOOR_EXIT_2.value):
                    door_x = tx * tile_size + tile_size // 2
                    door_y = ty * tile_size + tile_size // 2
                    
                    # Check distance to player
                    dist = ((player_center_x - door_x) ** 2 + (player_center_y - door_y) ** 2) ** 0.5
                    if dist <= search_radius:
                        door_found = True
                        # Determine which exit key this door corresponds to
                        if tile_val == TileType.DOOR_EXIT_1.value:
                            exit_key = "door_exit_1"
                            prompt_text = "Press E to enter (Exit 1)"
                        else:
                            exit_key = "door_exit_2"
                            prompt_text = "Press E to enter (Exit 2)"
                            
                        door_info = (exit_key, prompt_text, door_x, door_y)
                        break
            if door_found:
                break
                
        if not door_info:
            return None
            
        exit_key, prompt_text, door_x, door_y = door_info
        
        # If E is pressed, plan the transition
        if is_e_pressed and exit_key in exits:
            target = exits[exit_key]
            if isinstance(target, dict):
                target_level_id = target.get('level_id', self.current_level_id)
                target_room_code = target.get('room_code')
            else:
                # Assume string format like "1A" or "2B"
                target_str = str(target)
                if len(target_str) >= 2 and target_str[:-1].isdigit():
                    target_level_id = int(target_str[:-1])
                    target_room_code = target_str[-1]
                else:
                    logger.warning(f"Invalid target format: {target}")
                    return None
                    
            self._last_transition = {
                'level_id': target_level_id,
                'room_code': target_room_code,
                'spawn': None  # Will be determined by spawn point finding
            }
            
        return (prompt_text, door_x, door_y)
        
    def pop_last_transition(self) -> Optional[Dict[str, Any]]:
        """Get and clear the last planned transition.
        
        Returns:
            The transition dict or None if no transition is planned
        """
        transition = self._last_transition
        self._last_transition = None
        return transition
        
    def get_current_room_info(self) -> Optional[Dict[str, Any]]:
        """Get information about the current room.
        
        Returns:
            Dict with room info or None if no room is loaded
        """
        if self.current_level_id is None or self.current_room_code is None:
            return None
            
        return {
            'level_id': self.current_level_id,
            'room_code': self.current_room_code,
            'tile_grid': self.current_tile_grid
        }
        
    def get_spawn_point(self) -> Optional[Tuple[int, int]]:
        """Find spawn point in the current room.
        
        Returns:
            Tuple of (x, y) pixel coordinates for spawn point, or None if not found
        """
        if not self.current_tile_grid:
            return None
            
        try:
            # Get entrance from to determine which entrance to look for
            entrance_from = get_room_entrance_from(self.current_level_id, self.current_room_code)
            spawn_tile = find_spawn_point(self.current_tile_grid, entrance_from)
            
            if spawn_tile:
                # Convert tile coordinates to pixel coordinates
                return (spawn_tile[0] * TILE, spawn_tile[1] * TILE)
        except Exception as e:
            logger.error(f"Failed to find spawn point: {e}")
            
        return None