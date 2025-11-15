"""New centralized door placement utilities.

This module provides a simple, deterministic API that the PCG generator
and loader can call to place door tiles into a room tile grid. It
ensures placed door metadata is always recorded and avoids any legacy
fixed-position logic.
"""
from typing import List, Dict, Optional, Tuple
import random
from src.tiles.tile_types import TileType
from src.level.pcg_level_data import RoomData


def place_single_exit(tile_grid: List[List[int]], exit_key: str, room: RoomData, rng: Optional[random.Random] = None) -> Optional[Dict]:
    """Place a single-block exit tile for `exit_key` into `tile_grid`.

    Simplified, strict placement:
    1) If generator recorded a `door_carve` area for this exit, place the door
       at the bottom-center of that carve (preferred).
    2) Otherwise, scan interior air tiles (avoid immediate wall-adjacent columns)
       and place the door at the first available interior AIR tile.

    This intentionally avoids legacy wall-fixed placements (left/right) so PCG
    carving determines door locations exclusively.
    """
    rng = rng or random.Random()
    h = len(tile_grid)
    w = len(tile_grid[0]) if h > 0 else 0
    if h == 0 or w == 0:
        return None

    from src.tiles.tile_types import TileType as _TT
    from config import TILE_AIR

    # helper to mark metadata
    def _record(tx: int, ty: int, tile_type: _TT):
        entry = {"tx": tx, "ty": ty, "tile": tile_type.value, "role": "exit", "exit_key": exit_key, "target": (room.door_exits or {}).get(exit_key)}
        room.placed_doors = getattr(room, 'placed_doors', []) or []
        room.placed_doors.append(entry)
        return entry

    # occupied positions from metadata
    occupied = set(( (d.get('tx'), d.get('ty')) for d in (getattr(room, 'placed_doors', []) or []) ))

    # 1) Try generator-carved areas first
    try:
        areas = getattr(room, 'areas', []) or []
        for area in areas:
            kind = area.get('kind') if isinstance(area, dict) else getattr(area, 'kind', None)
            door_key = area.get('door_key') if isinstance(area, dict) else getattr(area, 'door_key', None)
            if kind == 'door_carve' and door_key == exit_key:
                rect = None
                if isinstance(area, dict):
                    rects = area.get('rects', [])
                    if rects:
                        rect = rects[0]
                else:
                    rects = getattr(area, 'rects', None)
                    if rects:
                        rect = rects[0]
                if rect:
                    rx = rect.get('x') if isinstance(rect, dict) else getattr(rect, 'x', None)
                    ry = rect.get('y') if isinstance(rect, dict) else getattr(rect, 'y', None)
                    rw = rect.get('w') if isinstance(rect, dict) else getattr(rect, 'w', None)
                    rh = rect.get('h') if isinstance(rect, dict) else getattr(rect, 'h', None)
                    if None not in (rx, ry, rw, rh):
                        tx = int(rx + rw // 2)
                        ty = int(ry + rh - 1)
                        # Avoid placing directly on immediate wall columns; shift inward if needed
                        if tx == 1 and tx + 1 < w:
                            tx = 2
                        elif tx == w - 2 and tx - 1 >= 0:
                            tx = w - 3
                        if 0 <= tx < w and 0 <= ty < h and (tx, ty) not in occupied and tile_grid[ty][tx] == TILE_AIR:
                            tile_grid[ty][tx] = _TT.DOOR_EXIT_2.value if exit_key == 'door_exit_2' else _TT.DOOR_EXIT_1.value
                            return _record(tx, ty, _TT.DOOR_EXIT_2 if exit_key == 'door_exit_2' else _TT.DOOR_EXIT_1)
    except Exception:
        pass

    # 2) Fallback: scan interior AIR tiles (avoid x==1 and x==w-2 to not sit on walls)
    for yy in range(1, h - 1):
        for xx in range(2, max(2, w - 2)):
            if (xx, yy) in occupied:
                continue
            if tile_grid[yy][xx] == TILE_AIR:
                tile_grid[yy][xx] = _TT.DOOR_EXIT_2.value if exit_key == 'door_exit_2' else _TT.DOOR_EXIT_1.value
                return _record(xx, yy, _TT.DOOR_EXIT_2 if exit_key == 'door_exit_2' else _TT.DOOR_EXIT_1)

    # Nothing placed
    return None

    # helper to mark metadata
    def _record(tx, ty, tile_type: TileType):
        entry = {"tx": tx, "ty": ty, "tile": tile_type.value, "role": "exit", "exit_key": exit_key, "target": (room.door_exits or {}).get(exit_key)}
        room.placed_doors = getattr(room, 'placed_doors', []) or []
        room.placed_doors.append(entry)
        return entry

    # occupied positions from metadata or existing door tiles
    occupied = set(((d.get('tx'), d.get('ty')) for d in (getattr(room, 'placed_doors', []) or [])))
    from src.tiles.tile_types import TileType as _TT
    door_values = {_TT.DOOR_ENTRANCE.value, _TT.DOOR_EXIT_1.value, _TT.DOOR_EXIT_2.value, _TT.DOOR_EXIT.value}

    def _is_occupied(x, y):
        if (x, y) in occupied:
            return True
        try:
            if tile_grid[y][x] in door_values:
                return True
        except Exception:
            return False
        return False

    # Prefer carved door areas recorded by generator (3x3 rects).
    # STRICT MODE: do not place on walls unless the generator carved there.
    try:
        areas = getattr(room, 'areas', []) or []
        for area in areas:
            kind = area.get('kind') if isinstance(area, dict) else getattr(area, 'kind', None)
            if kind == 'door_carve' and (area.get('door_key') if isinstance(area, dict) else getattr(area, 'door_key', None)) == exit_key:
                rect = area.get('rects', [])[0] if isinstance(area, dict) else (area.rects[0] if getattr(area, 'rects', None) else None)
                if rect:
                    rx = rect.get('x') if isinstance(rect, dict) else getattr(rect, 'x', None)
                    ry = rect.get('y') if isinstance(rect, dict) else getattr(rect, 'y', None)
                    rw = rect.get('w') if isinstance(rect, dict) else getattr(rect, 'w', None)
                    rh = rect.get('h') if isinstance(rect, dict) else getattr(rect, 'h', None)
                    if None not in (rx, ry, rw, rh):
                        tx = int(rx + (rw // 2))
                        ty = int(ry + (rh - 1))
                        if 0 <= ty < h and 0 <= tx < w and not _is_occupied(tx, ty):
                            tile_grid[ty][tx] = _TT.DOOR_EXIT_2.value if exit_key == 'door_exit_2' else _TT.DOOR_EXIT_1.value
                            occupied.add((tx, ty))
                            # ensure interior tile is air
                            interior_x, interior_y = tx, ty
                            if tx == 1 and tx + 1 < w:
                                interior_x = tx + 1
                            elif tx == w - 2 and tx - 1 >= 0:
                                interior_x = tx - 1
                            elif ty == 1 and ty + 1 < h:
                                interior_y = ty + 1
                            elif ty == h - 2 and ty - 1 >= 0:
                                interior_y = ty - 1
                            if 0 <= interior_y < h and 0 <= interior_x < w:
                                from config import TILE_AIR
                                if tile_grid[interior_y][interior_x] != TILE_AIR:
                                    tile_grid[interior_y][interior_x] = TILE_AIR
                            return _record(tx, ty, _TT.DOOR_EXIT_2 if exit_key == 'door_exit_2' else _TT.DOOR_EXIT_1)
    except Exception:
        pass

    # No wall/perimeter heuristics: fall back to interior air only
    perim = []
    x_left = 1; x_right = w - 2
    for yy in range(1, h - 1):
        perim.append((x_left, yy)); perim.append((x_right, yy))
    y_top = 1; y_bot = h - 2
    for xx in range(1, w - 1):
        perim.append((xx, y_top)); perim.append((xx, y_bot))

    # shuffle deterministically
    rng.shuffle(perim)

    for tx, ty in perim:
        if _is_occupied(tx, ty):
            continue
        # skip areas marked no_carve/no_spawn
        try:
            from src.level.pcg_level_data import room_areas_from_raw
            areas = getattr(room, 'areas', []) or []
            skip = False
            for area in areas:
                kind = area.get('kind') if isinstance(area, dict) else getattr(area, 'kind', None)
                if kind in ('no_carve', 'no_spawn'):
                    for r in area.get('rects', []) if isinstance(area, dict) else []:
                        if r.get('x') <= tx < r.get('x') + r.get('w') and r.get('y') <= ty < r.get('y') + r.get('h'):
                            skip = True
                            break
                if skip:
                    break
            if skip:
                continue
        except Exception:
            pass

        try:
            tile_grid[ty][tx] = _TT.DOOR_EXIT_2.value if exit_key == 'door_exit_2' else _TT.DOOR_EXIT_1.value
            occupied.add((tx, ty))
            # carve adjacent interior tile to air so door is usable
            interior_x, interior_y = tx, ty
            if tx == 1 and tx + 1 < w:
                interior_x = tx + 1
            elif tx == w - 2 and tx - 1 >= 0:
                interior_x = tx - 1
            elif ty == 1 and ty + 1 < h:
                interior_y = ty + 1
            elif ty == h - 2 and ty - 1 >= 0:
                interior_y = ty - 1
            if 0 <= interior_y < h and 0 <= interior_x < w:
                from config import TILE_AIR
                if tile_grid[interior_y][interior_x] != TILE_AIR:
                    tile_grid[interior_y][interior_x] = TILE_AIR
            return _record(tx, ty, _TT.DOOR_EXIT_2 if exit_key == 'door_exit_2' else _TT.DOOR_EXIT_1)
        except Exception:
            continue

    # final fallback: any interior air tile not occupied
    from config import TILE_AIR
    for yy in range(1, h - 1):
        for xx in range(1, w - 1):
            if (xx, yy) in occupied:
                continue
            if tile_grid[yy][xx] == TILE_AIR:
                tile_grid[yy][xx] = _TT.DOOR_EXIT_2.value if exit_key == 'door_exit_2' else _TT.DOOR_EXIT_1.value
                occupied.add((xx, yy))
                return _record(xx, yy, _TT.DOOR_EXIT_2 if exit_key == 'door_exit_2' else _TT.DOOR_EXIT_1)

    return None


def place_all_doors_for_room(room: RoomData, rng: Optional[random.Random] = None) -> None:
    """Place entrance and any exits into the room tiles and record metadata.

    - Places `DOOR_ENTRANCE` at the recorded `room.entrance_from` location if present (bottom-center of carved area assumed to already be carved by generator).
    - For each exit key in `room.door_exits`, ensure a tile exists and record it in `room.placed_doors`.

    This function is idempotent: if `placed_doors` already contains entries for an exit key,
    it will not create duplicate placements.
    """
    rng = rng or random.Random()
    h = len(room.tiles)
    w = len(room.tiles[0]) if h>0 else 0
    if h == 0 or w == 0:
        return

    room.placed_doors = getattr(room, 'placed_doors', []) or []

    # Place entrance if present and not already recorded
    if room.entrance_from:
        # find existing entrance in placed_doors
        if not any(d.get('role') == 'entrance' for d in room.placed_doors):
            # attempt to find an air tile near center-bottom to place entrance
            cx = w // 2
            cy = min(h - 2, h // 2 + 1)
            tx, ty = cx, cy
            # clamp
            tx = max(1, min(w-2, tx))
            ty = max(1, min(h-2, ty))
            room.tiles[ty][tx] = TileType.DOOR_ENTRANCE.value
            room.placed_doors.append({"tx": tx, "ty": ty, "tile": TileType.DOOR_ENTRANCE.value, "role": "entrance", "source": room.entrance_from})

    # Ensure each logical exit has a placed tile
    for exit_key in list((room.door_exits or {}).keys()):
        # skip if already present
        if any(d.get('exit_key') == exit_key for d in room.placed_doors):
            continue
        place_single_exit(room.tiles, exit_key, room, rng=rng)


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
