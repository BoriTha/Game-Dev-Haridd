from typing import List, Optional, Tuple, Dict, Any
import random
from src.tiles.tile_types import TileType
from src.level.pcg_level_data import RoomData


def place_door(tile_grid: List[List[int]], tx: int, ty: int, door_type: TileType) -> None:
    """Place a door tile (enum -> numeric) at tile coords (tx, ty)."""
    if not tile_grid:
        return
    h = len(tile_grid)
    w = len(tile_grid[0]) if h > 0 else 0
    if ty < 0 or ty >= h:
        return
    if tx < 0 or tx >= w:
        return
    tile_grid[ty][tx] = door_type.value


def choose_wall_position(tile_grid: List[List[int]], side: str = "left", rng: Optional[random.Random] = None) -> Optional[Tuple[int, int]]:
    """Choose a safe tile on `side` wall. Prefers middle; falls back to random valid interior edge."""
    rng = rng or random.Random()
    if not tile_grid:
        return None
    h = len(tile_grid)
    w = len(tile_grid[0]) if h > 0 else 0
    if w < 3 or h < 3:
        return None

    candidates: List[Tuple[int, int]] = []
    if side == "left":
        x = 1
        for y in range(1, h - 1):
            # Ensure adjacent interior tile is air (safe entry)
            if tile_grid[y][x] >= 0 and tile_grid[y][x + 1] == 0:
                candidates.append((x, y))
    elif side == "right":
        x = w - 2
        for y in range(1, h - 1):
            if tile_grid[y][x] >= 0 and tile_grid[y][x - 1] == 0:
                candidates.append((x, y))
    elif side == "top":
        y = 1
        for x in range(1, w - 1):
            if tile_grid[y][x] >= 0 and tile_grid[y + 1][x] == 0:
                candidates.append((x, y))
    elif side == "bottom":
        y = h - 2
        for x in range(1, w - 1):
            if tile_grid[y][x] >= 0 and tile_grid[y - 1][x] == 0:
                candidates.append((x, y))

    if not candidates:
        # fallback: any interior tile adjacent to either vertical walls (x==1 or x==w-2)
        for y in range(1, h - 1):
            for x in (1, w - 2):
                if 0 <= x < w and tile_grid[y][x] == 0:
                    candidates.append((x, y))

    if not candidates:
        return None
    # Prefer the middle candidate if present
    mid = len(candidates) // 2
    return rng.choice(candidates) if len(candidates) > 1 else candidates[0]


def place_exit_with_metadata(
    room: RoomData,
    tile_grid: List[List[int]],
    tx: int,
    ty: int,
    exit_key: str,
    target: Dict[str, Any]
) -> None:
    """Place a door exit tile and update room.door_exits and room.placed_doors metadata."""
    if exit_key == "door_exit_1":
        door_tile = TileType.DOOR_EXIT_1
    elif exit_key == "door_exit_2":
        door_tile = TileType.DOOR_EXIT_2
    else:
        door_tile = TileType.DOOR_EXIT

    place_door(tile_grid, tx, ty, door_tile)

    if getattr(room, "door_exits", None) is None:
        room.door_exits = {}
    room.door_exits[exit_key] = target

    room.placed_doors = getattr(room, "placed_doors", []) or []
    room.placed_doors.append({
        "tx": tx,
        "ty": ty,
        "tile": door_tile.value,
        "role": "exit",
        "exit_key": exit_key,
        "target": target,
    })


def place_entrance(room: RoomData, tile_grid: List[List[int]], tx: int, ty: int, entrance_from: Optional[str]) -> None:
    """Place a door entrance tile and update room.entrance_from and placed_doors."""
    place_door(tile_grid, tx, ty, TileType.DOOR_ENTRANCE)
    room.entrance_from = entrance_from
    room.placed_doors = getattr(room, "placed_doors", []) or []
    room.placed_doors.append({
        "tx": tx,
        "ty": ty,
        "tile": TileType.DOOR_ENTRANCE.value,
        "role": "entrance",
        "source": entrance_from,
    })
