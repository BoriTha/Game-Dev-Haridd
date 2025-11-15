"""New centralized door placement utilities.

This module provides a simple, deterministic API that PCG generator
and loader can call to place door tiles into a room tile grid. It
ensures placed door metadata is always recorded and avoids any legacy
fixed-position logic.
"""
from typing import List, Dict, Optional, Tuple
import random
from src.tiles.tile_types import TileType
from src.level.pcg_level_data import RoomData


def _place_single_door_from_carve(tile_grid: List[List[int]], door_key: str, room: RoomData, rng: Optional[random.Random] = None) -> Optional[Dict]:
    """Place a single-block door tile for `door_key` into `tile_grid`."""
    rng = rng or random.Random()
    h = len(tile_grid)
    w = len(tile_grid[0]) if h > 0 else 0
    if h == 0 or w == 0:
        return None

    from src.tiles.tile_types import TileType as _TT
    from config import TILE_AIR

    def _record(tx: int, ty: int, tile_type: _TT, role: str, key: str):
        entry = {"tx": tx, "ty": ty, "tile": tile_type.value, "role": role}
        if role == "exit":
            entry["exit_key"] = key
            entry["target"] = (room.door_exits or {}).get(key)
        elif role == "entrance":
            entry["source"] = room.entrance_from
        
        if not hasattr(room, 'placed_doors') or room.placed_doors is None:
            room.placed_doors = []
        if not isinstance(room.placed_doors, list):
            room.placed_doors = []
        room.placed_doors.append(entry)
        return entry
    
    # occupied positions from metadata
    placed_doors = getattr(room, 'placed_doors', None)
    if placed_doors is None:
        placed_doors = []
        room.placed_doors = placed_doors
    occupied = set(( (d.get('tx'), d.get('ty')) for d in placed_doors ))

    # 1) Try generator-carved areas first
    try:
        areas = getattr(room, 'areas', []) or []
        for area in areas:
            kind = area.get('kind') if isinstance(area, dict) else getattr(area, 'kind', None)
            
            # For door_carve areas, door_key is inside rects
            if kind == 'door_carve':
                rect = None
                if isinstance(area, dict):
                    rects = area.get('rects', [])
                    if rects:
                        rect = rects[0]
                else:
                    rects = getattr(area, 'rects', None)
                    if rects:
                        rect = rects[0]
                
                # Get door_key from rect itself
                rect_door_key = None
                if rect and isinstance(rect, dict):
                    rect_door_key = rect.get('door_key')
                elif rect:
                    rect_door_key = getattr(rect, 'door_key', None)
                
                # Use the passed 'door_key' to find the matching carve area
                if rect_door_key == door_key and rect:
                    rx = rect.get('x') if isinstance(rect, dict) else getattr(rect, 'x', None)
                    ry = rect.get('y') if isinstance(rect, dict) else getattr(rect, 'y', None)
                    rw = rect.get('w') if isinstance(rect, dict) else getattr(rect, 'w', None)
                    rh = rect.get('h') if isinstance(rect, dict) else getattr(rect, 'h', None)
                    
                    # Validate all values are numeric and reasonable
                    try:
                        rx_val = float(rx) if rx is not None else None
                        ry_val = float(ry) if ry is not None else None
                        rw_val = float(rw) if rw is not None else None
                        rh_val = float(rh) if rh is not None else None
                        
                        if (rx_val is not None and ry_val is not None and 
                            rw_val is not None and rh_val is not None and
                            rx_val >= 0 and ry_val >= 0 and rw_val > 0 and rh_val > 0):
                            tx = int(rx_val + rw_val // 2)
                            ty = int(ry_val + rh_val - 1)
                            
                            # Avoid placing directly on immediate wall columns; shift inward if needed
                            if tx == 1 and tx + 1 < w:
                                tx = 2
                            elif tx == w - 2 and tx - 1 >= 0:
                                tx = w - 3
                            
                            if 0 <= tx < w and 0 <= ty < h and (tx, ty) not in occupied and tile_grid[ty][tx] == TILE_AIR:
                                
                                # Select tile type based on door_key
                                if door_key == 'entrance':
                                    tile_type = _TT.DOOR_ENTRANCE
                                    role = 'entrance'
                                elif door_key == 'door_exit_2':
                                    tile_type = _TT.DOOR_EXIT_2
                                    role = 'exit'
                                else: # default to exit 1
                                    tile_type = _TT.DOOR_EXIT_1
                                    role = 'exit'
                                
                                tile_grid[ty][tx] = tile_type.value
                                return _record(tx, ty, tile_type, role, door_key)
                        else:
                            continue
                    except (ValueError, TypeError):
                        continue
    except Exception:
        pass

    # NO FALLBACK
    return None


def place_all_doors_for_room(room: RoomData, rng: Optional[random.Random] = None) -> None:
    """Place entrance and any exits into room tiles and record metadata."""
    rng = rng or random.Random()
    h = len(room.tiles)
    w = len(room.tiles[0]) if h>0 else 0
    if h == 0 or w == 0:
        return

    # Initialize placed_doors if needed
    if not hasattr(room, 'placed_doors') or room.placed_doors is None:
        room.placed_doors = []
    elif not isinstance(room.placed_doors, list):
        room.placed_doors = []

    # Place entrance if present and not already recorded
    # Also place entrance for first room of first level even without entrance_from
    from src.level.pcg_generator_simple import is_first_room_first_level
    should_place_entrance = room.entrance_from or is_first_room_first_level(room)
    
    if should_place_entrance:
        placed_doors_list = room.placed_doors if isinstance(room.placed_doors, list) else []
        if not any(d.get('role') == 'entrance' for d in placed_doors_list):
            # Use the carve-aware function for the entrance
            _place_single_door_from_carve(room.tiles, 'entrance', room, rng=rng)

    # Update the exit loop to call the new function
    for exit_key in list((room.door_exits or {}).keys()):
        # skip if already present
        placed_doors_list = room.placed_doors if isinstance(room.placed_doors, list) else []
        if any(d.get('exit_key') == exit_key for d in placed_doors_list):
            continue
        # Call the renamed function
        _place_single_door_from_carve(room.tiles, exit_key, room, rng=rng)


# Small helper to clear legacy placements (not used by default)
def clear_legacy_doors(tile_grid: List[List[int]]) -> None:
    from config import TILE_AIR
    from src.tiles.tile_types import TileType as _TileType
    door_values = {_TileType.DOOR_ENTRANCE.value, _TileType.DOOR_EXIT_1.value, _TileType.DOOR_EXIT_2.value}
    h = len(tile_grid)
    w = len(tile_grid[0]) if h>0 else 0
    for ty in range(h):
        for tx in range(w):
            if tile_grid[ty][tx] in door_values:
                tile_grid[ty][tx] = TILE_AIR