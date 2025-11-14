"""Door interaction handler for PCG level system."""

import pygame
import os
import sys
from typing import Optional, Tuple

# Add project root to path for imports
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))

from src.core.interaction import handle_proximity_interactions, find_spawn_point
from src.tiles.tile_types import TileType
from src.level.level_loader import (
    get_room_tiles, get_room_exits, get_room_entrance_from
)

import logging
logger = logging.getLogger(__name__)  # module logger; application config controls output level


class DoorSystem:
    """Handles door interactions and room transitions in PCG levels."""
    
    def __init__(self):
        self.current_level_id = 1
        self.current_room_code = "1A"
        self.current_tiles = None
        # Holds last successful transition info set by _process_door_interaction
        # Format: {"level_id": int, "room_code": str, "spawn": (x,y) or None}
        self._last_transition: Optional[dict] = None
    
    def load_room(self, level_id: int, room_code: str) -> bool:
        """
        Load a specific room.
        
        Args:
            level_id: The level number (1-based)
            room_code: Room code like "1A", "2B", etc.
            
        Returns:
            True if room loaded successfully, False otherwise
        """
        tiles = get_room_tiles(level_id, room_code)
        if tiles:
            prev = (self.current_level_id, self.current_room_code)
            self.current_level_id = level_id
            self.current_room_code = room_code
            self.current_tiles = tiles
            logger.debug("DoorSystem load_room: %s -> (%s, %s)", prev, self.current_level_id, self.current_room_code)
            
            # Place entrance door if this room has an entrance
            from src.level.level_loader import level_loader
            room = level_loader.get_room(level_id, room_code)
            if room and room.entrance_from:
                self._place_entrance_door(room.entrance_from)
            else:
                # Ensure left door tile cleared if no entrance
                if self.current_tiles:
                    h = len(self.current_tiles)
                    w = len(self.current_tiles[0]) if h > 0 else 0
                    entrance_y = h // 2
                    if 0 < entrance_y < h - 1 and 1 < w - 1:
                        from config import TILE_AIR
                        self.current_tiles[entrance_y][1] = TILE_AIR
            
            return True
        return False
    
    def _place_entrance_door(self, entrance_from: str):
        """Place entrance door in current room tiles."""
        if not self.current_tiles:
            return
            
        from src.tiles.tile_types import TileType
        
        h = len(self.current_tiles)
        w = len(self.current_tiles[0]) if h > 0 else 0
        
        # Place entrance door on left wall
        entrance_y = h // 2
        if 0 < entrance_y < h - 1 and 1 < w - 1:
            self.current_tiles[entrance_y][1] = TileType.DOOR_ENTRANCE.value
    
    def handle_door_interaction(
        self, 
        player_rect: pygame.Rect, 
        tile_size: int,
        is_e_pressed: bool
    ) -> Optional[Tuple[str, int, int]]:
        """Handle proximity interactions and record transitions.

        Returns the usual (prompt, x, y) tuple for HUD display. If an actual
        room transition occurs as a result of the interaction, this object
        records details in `self.last_transition` as a dict:
            {"level_id": int, "room_code": str, "spawn": (x,y) | None}
        """
        # reset last transition before checking
        self.last_transition = None
        """
        Handle door interactions for current room.
        
        Args:
            player_rect: Player's collision rectangle
            tile_size: Size of each tile (usually 24)
            is_e_pressed: Whether E key was pressed this frame
            
        Returns:
            Tuple of (prompt_text, world_x, world_y) for UI display,
            or None if no interactable tile is nearby.
        """
        if not self.current_tiles:
            return None
        
        def on_interact(tile_data, tile_coords):
            """Handle door interaction."""
            self._process_door_interaction(tile_data, tile_coords)
        
        return handle_proximity_interactions(
            player_rect=player_rect,
            tile_grid=self.current_tiles,
            tile_size=tile_size,
            is_e_pressed=is_e_pressed,
            on_interact=on_interact
        )
    
    def _process_door_interaction(self, tile_data, tile_coords: Tuple[int, int]):
        """Process a door interaction and perform room transition."""
        tile_type = tile_data.tile_type
        on_interact_id = tile_data.interaction.on_interact_id
        
        # Handle different door types
        if tile_type == TileType.DOOR_EXIT_1:
            exit_key = "door_exit_1"
        elif tile_type == TileType.DOOR_EXIT_2:
            exit_key = "door_exit_2"
        else:
            # Not a door exit we handle
            return
        
        # Get target room from current room's exit mapping
        exits = get_room_exits(self.current_level_id, self.current_room_code)
        target = exits.get(exit_key)

        # Support both normalized structured exits and legacy string exits
        target_level_id = None
        target_room_code_full = None

        if isinstance(target, dict):
            # normalized form: {"level_id": X, "room_code": "..."}
            try:
                target_level_id = int(target.get("level_id"))
                target_room_code_full = str(target.get("room_code"))
            except Exception:
                logger.warning("Invalid structured target for %s: %s", exit_key, target)
                return
        elif isinstance(target, str):
            # Legacy string like '11A'
            import re
            m = re.match(r"^(\d+)(.+)$", target)
            if not m:
                logger.warning("Invalid room code format: %s", target)
                return
            target_level_id = int(m.group(1))
            target_room_code_full = m.group(0)
        else:
            logger.debug("No target room for %s in %s", exit_key, self.current_room_code)
            return

        # Verify target exists and is not the current room
        from src.level.level_loader import level_loader
        if not level_loader.get_room(target_level_id, target_room_code_full):
            logger.warning("No such target room: %s/%s", target_level_id, target_room_code_full)
            return
        if target_level_id == self.current_level_id and target_room_code_full == self.current_room_code:
            logger.info("Target equals current room (%s/%s), ignoring interaction", target_level_id, target_room_code_full)
            return

        # Load target room
        if self.load_room(target_level_id, target_room_code_full):
            logger.info("Transitioned to %s", target_room_code_full)
            
            # Find spawn point in new room
            spawn_coords = find_spawn_point(self.current_tiles)
            if spawn_coords:
                spawn_tx, spawn_ty = spawn_coords
                from config import TILE
                spawn_x = spawn_tx * TILE
                spawn_y = spawn_ty * TILE
                logger.debug("Spawn point: (%s, %s)", spawn_x, spawn_y)
                # In actual game, you would move player here
                return spawn_x, spawn_y
            else:
                logger.info("No spawn point found in target room")
        else:
            logger.warning("Failed to load room: %s", target_room_code_full)
    
    def get_spawn_point(self) -> Optional[Tuple[int, int]]:
        """Get spawn point for current room."""
        if not self.current_tiles:
            return None
        
        from config import TILE
        # First try to find spawn point matching entrance_from
        entrance_from = get_room_entrance_from(self.current_level_id, self.current_room_code)
        if entrance_from:
            spawn_coords = find_spawn_point(self.current_tiles, entrance_from)
            if spawn_coords:
                spawn_tx, spawn_ty = spawn_coords
                return (spawn_tx * TILE, spawn_ty * TILE)  # Convert to world coordinates
        
        # Fallback to any spawn point
        spawn_coords = find_spawn_point(self.current_tiles)
        if spawn_coords:
            spawn_tx, spawn_ty = spawn_coords
            return (spawn_tx * TILE, spawn_ty * TILE)  # Convert to world coordinates
        return None
    
    def get_current_room_info(self) -> dict:
        """Get information about current room."""
        if not self.current_tiles:
            return {}
        
        exits = get_room_exits(self.current_level_id, self.current_room_code)
        entrance_from = get_room_entrance_from(self.current_level_id, self.current_room_code)
        
        return {
            "level_id": self.current_level_id,
            "room_code": self.current_room_code,
            "entrance_from": entrance_from,
            "exits": exits,
            "room_size": f"{len(self.current_tiles)}x{len(self.current_tiles[0])}"
        }


def test_door_system():
    """Test the door system with generated levels."""
    import logging
    logger = logging.getLogger(__name__)
    from src.level.pcg_generator_simple import generate_and_save_simple_pcg
    
    logger.info("=== Generating test levels ===")
    level_set = generate_and_save_simple_pcg()
    
    logger.info("\n=== Testing Door System ===")
    door_system = DoorSystem()
    
    # Load first room
    if door_system.load_room(1, "1A"):
        logger.info("✓ Loaded room 1A")
        
        # Show room info
        info = door_system.get_current_room_info()
        logger.info("Room info: %s", info)
        
        # Test spawn point
        spawn = door_system.get_spawn_point()
        if spawn:
            logger.info("✓ Spawn point: %s", spawn)
        
        # Test door exits
        exits = info.get("exits", {})
        for exit_key, target_room in exits.items():
            logger.info("  %s → %s", exit_key, target_room)
    
    logger.info("\n=== Testing room transitions ===")
    # Simulate door interaction
    door_system.load_room(1, "1A")
    
    # Simulate using door_exit_1
    logger.info("Simulating door_exit_1 interaction...")
    # Create fake tile data for testing
    from src.tiles.tile_data import TileData, InteractionProperties
    from src.tiles.tile_types import TileType
    
    fake_door_tile = TileData(
        tile_type=TileType.DOOR_EXIT_1,
        name="Test Door",
        interaction=InteractionProperties(
            on_interact_id="door_exit_1"
        )
    )
    
    door_system._process_door_interaction(fake_door_tile, (38, 13))  # Approx door position
    
    # Show current room after transition
    info = door_system.get_current_room_info()
    logger.info("After transition: %s", info)


if __name__ == "__main__":
    test_door_system()