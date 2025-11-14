"""Simple PCG level generator using pcg_level_data structures.

This module:
- Loads PCGConfig from JSON via config_loader
- Generates 1..num_levels levels
- For each level, creates 6 "room numbers" (1-6)
  - Each number spawns 1 or 2 rooms (A, or A and B)
- Assigns room_code as f"{level_id}{slot}{letter}" (e.g. 11A, 12B)
- Fills tiles with wall boundary + air interior
- Wires doors according to rules:
  - Only transitions from number N -> N+1
  - No same-number transitions (no 1A -> 1B)
  - If next number has only A: exit_1 -> A, no exit_2
  - If next number has A and B: exit_1 -> A, exit_2 -> B
  - End of last number in level N routes to first number in level N+1
    using same rule as above
  - Last level's last number has no exits
- Computes entrance_from as the first room that leads into a room

Door tiles are NOT placed in the tile grid here; this module only
manages logical connectivity via door_exits and entrance_from.
"""

from __future__ import annotations

import random
from typing import List, Dict, Optional
import os
import sys

# Ensure project root is on path when running this module directly
if __name__ == "__main__":
    sys.path.append(os.path.join(os.path.dirname(__file__), "..", ".."))

from src.level.config_loader import load_pcg_config
from src.level.pcg_level_data import (
    PCGConfig,
    RoomData,
    LevelData,
    LevelSet,
)


def generate_simple_room_tiles(config: PCGConfig) -> List[List[int]]:
    """Generate a room with wall boundary and air interior.

    Uses tile IDs from PCGConfig (loaded from config/pcg_config.json).
    """
    from src.level.pcg_level_data import generate_room_tiles
    # Delegate to helper to keep generation logic centralized
    return generate_room_tiles(
        level_id=1, room_index=0, room_letter="A",
        width=config.room_width,
        height=config.room_height,
        config=config
    )


def generate_rooms_for_level(
    level_id: int,
    config: PCGConfig,
    rng: random.Random,
) -> List[RoomData]:
    """Generate 6-12 rooms for a single level.

    For numeric slots 1..6 (room_index 0..5):
    - Each slot spawns 1 or 2 rooms:
      - A only, or A and B
    - room_code = f"{level_id}{slot}{letter}" (e.g. 11A, 12B)
    """
    rooms: List[RoomData] = []

    for room_index in range(6):
        slot = room_index + 1
        count = rng.randint(1, 2)  # 1 or 2 rooms

        letters = ["A"] if count == 1 else ["A", "B"]

        for letter in letters:
            room_code = f"{level_id}{slot}{letter}"
            # Generate tiles using the centralized helper so room tiles vary by room
            from src.level.pcg_level_data import generate_room_tiles
            tiles = generate_room_tiles(
                level_id=level_id,
                room_index=room_index,
                room_letter=letter,
                width=config.room_width,
                height=config.room_height,
                config=config,
            )

            rooms.append(
                RoomData(
                    level_id=level_id,
                    room_index=room_index,
                    room_letter=letter,
                    room_code=room_code,
                    tiles=tiles,
                )
            )

    # Sort for deterministic order: by (room_index, room_letter)
    rooms.sort(key=lambda r: (r.room_index, r.room_letter))

    return rooms


def _group_rooms_by_index(level_rooms: List[RoomData]) -> Dict[int, List[RoomData]]:
    by_index: Dict[int, List[RoomData]] = {}
    for room in level_rooms:
        by_index.setdefault(room.room_index, []).append(room)
    # Ensure A before B in each group
    for rooms in by_index.values():
        rooms.sort(key=lambda r: r.room_letter)
    return by_index


def _wire_intra_level_doors(level_rooms: List[RoomData]) -> None:
    """Wire doors within a single level based on N -> N+1 rule.

    For each index i (0..4):
      - Look at rooms of i+1 (next index):
        - If only A:
            all rooms of i: exit_1 -> (i+1)A
        - If A and B:
            all rooms of i: exit_1 -> (i+1)A, exit_2 -> (i+1)B
    Index 5 (last) is handled by cross-level routing.
    """
    by_index = _group_rooms_by_index(level_rooms)
    indices = sorted(by_index.keys())

    # Clear any existing exits
    for r in level_rooms:
        r.door_exits = {}

    for pos, idx in enumerate(indices):
        # Skip last index here; cross-level routing will handle it
        if pos == len(indices) - 1:
            continue

        current_group = by_index[idx]
        next_idx = indices[pos + 1]
        next_group = by_index.get(next_idx, [])
        if not next_group:
            continue

        # Determine primary (A) and secondary (B if exists)
        primary = next_group[0]
        secondary = next_group[1] if len(next_group) > 1 else None

        for room in current_group:
            room.door_exits["door_exit_1"] = {"level_id": primary.level_id, "room_code": primary.room_code}
            if secondary is not None:
                room.door_exits["door_exit_2"] = {"level_id": secondary.level_id, "room_code": secondary.room_code}


def _wire_cross_level_doors(all_levels_rooms: List[List[RoomData]]) -> None:
    """Wire doors from last index of level N to first index of level N+1.

    Uses same branching rules as intra-level:
      - If next level's first index has only A:
            exit_1 -> A
      - If it has A and B:
            exit_1 -> A, exit_2 -> B
    Last level's last index has no exits added here.
    """
    num_levels = len(all_levels_rooms)

    for level_idx in range(num_levels - 1):
        current_rooms = all_levels_rooms[level_idx]
        next_rooms = all_levels_rooms[level_idx + 1]

        if not current_rooms or not next_rooms:
            continue

        current_by_index = _group_rooms_by_index(current_rooms)
        next_by_index = _group_rooms_by_index(next_rooms)

        # Last index in current level (room_index 5 if present)
        if not current_by_index:
            continue
        last_index = max(current_by_index.keys())
        last_group = current_by_index.get(last_index, [])
        if not last_group:
            continue

        # First index in next level (room_index 0 if present)
        if not next_by_index:
            continue
        first_index = min(next_by_index.keys())
        first_group = next_by_index.get(first_index, [])
        if not first_group:
            continue

        primary = first_group[0]
        secondary = first_group[1] if len(first_group) > 1 else None

        for room in last_group:
            room.door_exits["door_exit_1"] = {"level_id": primary.level_id, "room_code": primary.room_code}
            if secondary is not None:
                room.door_exits["door_exit_2"] = {"level_id": secondary.level_id, "room_code": secondary.room_code}


def _compute_entrances(all_levels_rooms: List[List[RoomData]]) -> None:
    """Compute entrance_from based on door_exits across all levels."""
    code_to_room: Dict[str, RoomData] = {
        room.room_code: room
        for level_rooms in all_levels_rooms
        for room in level_rooms
    }

    # Reset entrances
    for room in code_to_room.values():
        room.entrance_from = None

    # First source that points to a room becomes its entrance_from
    for source in code_to_room.values():
        if not source.door_exits:
            continue
        for target_entry in source.door_exits.values():
            # target_entry may be a structured dict or legacy string
            if isinstance(target_entry, dict):
                target_code = target_entry.get('room_code')
            else:
                target_code = target_entry
            target = code_to_room.get(target_code)
            if target is not None and target.entrance_from is None:
                target.entrance_from = source.room_code


def generate_simple_pcg_level_set(
    seed: Optional[int] = None,
) -> LevelSet:
    """Generate a LevelSet following the agreed simple PCG rules.

    - Uses PCGConfig loaded from config/pcg_config.json
    - Generates config.num_levels levels
    - Each level: 6 room indices, each with 1-2 rooms (A/B)
    - Applies intra-level and cross-level door routing
    """
    rng = random.Random(seed)
    config = load_pcg_config()

    num_levels = config.num_levels
    if num_levels <= 0:
        raise ValueError("PCGConfig.num_levels must be positive")

    all_levels_rooms: List[List[RoomData]] = []

    for level_id in range(1, num_levels + 1):
        level_rooms = generate_rooms_for_level(level_id, config, rng)
        _wire_intra_level_doors(level_rooms)
        all_levels_rooms.append(level_rooms)

    _wire_cross_level_doors(all_levels_rooms)
    _compute_entrances(all_levels_rooms)

    # Place door tiles into room tile grids and record placed_doors metadata
    try:
        from src.level.door_utils import choose_wall_position, place_exit_with_metadata, place_entrance
    except Exception:
        # If helper not available, skip placement
        choose_wall_position = None
        place_exit_with_metadata = None
        place_entrance = None

    for level_rooms in all_levels_rooms:
        for room in level_rooms:
            # Ensure placed_doors is initialized
            room.placed_doors = getattr(room, 'placed_doors', None)
            if room.placed_doors is None:
                room.placed_doors = []

            # Place entrance if present
            if room.entrance_from and choose_wall_position and place_entrance:
                pos = choose_wall_position(room.tiles, "left", rng)
                if pos:
                    tx, ty = pos
                    place_entrance(room, room.tiles, tx, ty, room.entrance_from)

            # Place exits
            if room.door_exits and choose_wall_position and place_exit_with_metadata:
                for exit_key, target in room.door_exits.items():
                    # Skip if we already placed this logical exit for the room
                    already = False
                    for pd in getattr(room, 'placed_doors', []) or []:
                        if pd.get('exit_key') == exit_key:
                            already = True
                            break
                    if already:
                        continue

                    pos = choose_wall_position(room.tiles, "right", rng)
                    if pos:
                        tx, ty = pos
                        place_exit_with_metadata(room, room.tiles, tx, ty, exit_key, target)

    levels: List[LevelData] = []
    for level_id, rooms in enumerate(all_levels_rooms, start=1):
        levels.append(LevelData(level_id=level_id, rooms=rooms))

    return LevelSet(levels=levels)


def generate_and_save_simple_pcg(
    output_path: str = "data/levels/generated_levels.json",
    seed: Optional[int] = None,
) -> LevelSet:
    """Generate the simple PCG level set and save it to JSON."""
    level_set = generate_simple_pcg_level_set(seed=seed)
    level_set.save_to_json(output_path)
    return level_set


if __name__ == "__main__":
    import logging
    logger = logging.getLogger(__name__)
    # Quick manual test: generate and log summary
    ls = generate_and_save_simple_pcg()
    for level in ls.levels:
        logger.info("Level %d: %d rooms", level.level_id, len(level.rooms))
        # Show a couple of rooms for inspection
        shown = set()
        for room in level.rooms:
            if room.room_index not in shown:
                logger.info("  Room %s: index=%d, letter=%s, entrance_from=%s, exits=%s",
                            room.room_code, room.room_index, room.room_letter, room.entrance_from, room.door_exits)
                shown.add(room.room_index)
        logger.info("")
