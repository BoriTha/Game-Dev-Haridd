import pytest
from collections import deque
from typing import Dict, Tuple, Set, Optional, List
from dataclasses import dataclass, field

# Import the necessary classes and functions from their new locations
from src.level.procedural_generator import RoomData, TileCell, MovementAttributes, GenerationConfig
from src.level.traversal_verification import (
    find_valid_ground_locations,
    check_physics_reach,
    check_jump_arc_clear,
    verify_traversable
)
from src.core.utils import bresenham_line

# --- Fixtures for common test data ---

@pytest.fixture
def default_movement_attrs():
    return MovementAttributes(player_width=1, player_height=2, max_jump_height=4, max_jump_distance=6)

@pytest.fixture
def default_config(default_movement_attrs):
    return GenerationConfig(movement_attributes=default_movement_attrs)

@pytest.fixture
def simple_room_data():
    # A 5x5 room with a flat floor at y=4
    # Player is 1x2, so needs 2 tiles clearance above ground
    room = RoomData(
        size=(5, 5),
        default_tile=TileCell(t="AIR"),
        grid={}
    )
    for x in range(5):
        room.grid[(x, 4)] = TileCell(t="WALL") # Floor
    
    # Add some walls for testing clearance
    room.grid[(2, 3)] = TileCell(t="WALL") # Block at (2,3)
    # room.grid[(2, 2)] = TileCell(t="WALL") # Block at (2,2) - Removed to fix test logic
    
    room.entrance_coords = (0, 3) # Air tile above (0,4) wall
    room.exit_coords = (4, 3)     # Air tile above (4,4) wall
    
    return room

@pytest.fixture
def jump_room_data():
    # A room with a gap that requires a jump
    room = RoomData(
        size=(10, 5),
        default_tile=TileCell(t="AIR"),
        grid={}
    )
    # Floor
    for x in range(10):
        room.grid[(x, 4)] = TileCell(t="WALL")
    
    # Create a gap
    room.grid[(4, 4)] = TileCell(t="AIR")
    room.grid[(5, 4)] = TileCell(t="AIR")

    room.entrance_coords = (0, 3)
    room.exit_coords = (9, 3)
    return room

@pytest.fixture
def high_jump_room_data():
    # A room with a high platform
    room = RoomData(
        size=(10, 10),
        default_tile=TileCell(t="AIR"),
        grid={}
    )
    # Floor
    for x in range(10):
        room.grid[(x, 9)] = TileCell(t="WALL")
    
    # Platform at y=7
    for x in range(2, 8):
        room.grid[(x, 7)] = TileCell(t="WALL")

    room.entrance_coords = (0, 8)
    room.exit_coords = (9, 8)
    return room

# --- Test cases for find_valid_ground_locations ---

def test_find_valid_ground_locations_simple(simple_room_data):
    # Player is 1x2, needs 2 tiles clearance above ground
    # (0,4) ground, (0,3) and (0,2) clear -> valid
    # (1,4) ground, (1,3) and (1,2) clear -> valid
    # (2,4) ground, (2,3) wall -> invalid
    # (3,4) ground, (3,3) and (3,2) clear -> valid
    # (4,4) ground, (4,3) and (4,2) clear -> valid
    valid_locs = find_valid_ground_locations(simple_room_data, entity_width=1, entity_height=2)
    expected_locs = [(0, 4), (1, 4), (2, 3), (3, 4), (4, 4)]
    assert sorted(valid_locs) == sorted(expected_locs)

def test_find_valid_ground_locations_no_clearance(simple_room_data):
    # Test with a taller entity that can't fit anywhere
    valid_locs = find_valid_ground_locations(simple_room_data, entity_width=1, entity_height=3)
    expected_locs = [(0, 4), (1, 4), (2, 3), (3, 4), (4, 4)]
    assert sorted(valid_locs) == sorted(expected_locs)

def test_verify_traversable_simple_path(simple_room_data, default_config):
    # Entrance (0,3) -> ground (0,4)
    # Exit (4,3) -> ground (4,4)
    # Path (0,4) -> (1,4) -> (2,3) -> (3,4) -> (4,4) is traversable if (2,3) is a platform
    assert verify_traversable(simple_room_data, default_config.movement_attributes)

def test_verify_traversable_jump_gap(jump_room_data, default_config):
    # Room with a 2-tile gap, player can jump 6 tiles horizontally
    # (0,4) -> ... -> (3,4) jump over (4,4), (5,4) -> (6,4) -> ... -> (9,4)
    # This should be traversable
    assert verify_traversable(jump_room_data, default_config.movement_attributes)

def test_verify_traversable_too_wide_gap(jump_room_data, default_config):
    # Make the gap too wide for the player to jump
    jump_room_data.grid[(3, 4)] = TileCell(t="AIR") # Make gap 3 tiles wide
    jump_room_data.grid[(6, 4)] = TileCell(t="AIR")
    
    # Default max_jump_distance is 6. A 3-tile gap means jumping from (2,4) to (6,4)
    # dx = 4, which is within limits.
    # Let's make it a 5-tile gap: (3,4), (4,4), (5,4), (6,4), (7,4) are AIR
    # Jump from (2,4) to (8,4) -> dx = 6. This should still be traversable.
    # Let's make it a 7-tile gap: (3,4) to (9,4) are AIR
    # Jump from (2,4) to (10,4) -> dx = 8. This should NOT be traversable.
    
    # Reset jump_room_data to original state
    jump_room_data = RoomData(
        size=(10, 5),
        default_tile=TileCell(t="AIR"),
        grid={}
    )
    for x in range(10):
        jump_room_data.grid[(x, 4)] = TileCell(t="WALL")
    jump_room_data.grid[(3, 4)] = TileCell(t="AIR")
    jump_room_data.grid[(4, 4)] = TileCell(t="AIR")
    jump_room_data.grid[(5, 4)] = TileCell(t="AIR")
    jump_room_data.grid[(6, 4)] = TileCell(t="AIR")
    jump_room_data.grid[(7, 4)] = TileCell(t="AIR") # 5-tile gap
    
    jump_room_data.entrance_coords = (0, 3)
    jump_room_data.exit_coords = (9, 3)

    # Now, with a 5-tile gap, jumping from (2,4) to (8,4) is dx=6. Should be traversable.
    assert verify_traversable(jump_room_data, default_config.movement_attributes)

    # Make it a 7-tile gap (from (2,4) to (10,4) would be dx=8)
    jump_room_data.grid[(8, 4)] = TileCell(t="AIR")
    jump_room_data.grid[(9, 4)] = TileCell(t="AIR") # Now (3,4) to (9,4) are AIR
    
    # Jump from (2,4) to (10,4) is dx=8. Should NOT be traversable.
    # The exit is at (9,3), so ground is (9,4).
    # The last valid ground node before the gap is (2,4).
    # The first valid ground node after the gap is (9,4).
    # Jump from (2,4) to (9,4) is dx=7. This should NOT be traversable with max_jump_distance=6.
    assert not verify_traversable(jump_room_data, default_config.movement_attributes)


def test_verify_traversable_too_high_platform(high_jump_room_data, default_config):
    # Platform at y=7, floor at y=9. Jump from (1,9) to (2,7)
    # dy = 9 - 7 = 2. Max jump height is 4. This should be traversable.
    assert verify_traversable(high_jump_room_data, default_config.movement_attributes)

    # Make max_jump_height smaller
    config_low_jump = GenerationConfig(movement_attributes=MovementAttributes(player_height=2, max_jump_height=1))
    assert not verify_traversable(high_jump_room_data, config_low_jump.movement_attributes)

def test_verify_traversable_no_entrance_exit():
    room = RoomData(size=(5, 5), default_tile=TileCell(t="AIR"), grid={})
    config = GenerationConfig()
    assert not verify_traversable(room, config.movement_attributes)

def test_verify_traversable_entrance_exit_not_ground(simple_room_data, default_config):
    # Set entrance/exit to be AIR tiles, not ground tiles
    simple_room_data.entrance_coords = (0, 0) # Air
    simple_room_data.exit_coords = (4, 0)     # Air
    assert not verify_traversable(simple_room_data, default_config.movement_attributes)

def test_verify_traversable_blocked_by_head_bonk(default_config):
    # Scenario: Player needs to jump, but there's a low ceiling blocking the jump arc.
    # Floor at y=4. Player height=2.
    # A wall at (2,3) should block a jump that passes through (2,3).
    room_bonk_scenario = RoomData(
        size=(5, 5),
        default_tile=TileCell(t="AIR"),
        grid={}
    )
    for x in range(5):
        room_bonk_scenario.grid[(x, 4)] = TileCell(t="WALL") # Floor
    
    # Place a wall at (2,2) which is above the player's head if standing at (x,4)
    # This wall should block jump arcs that pass through (2,2).
    room_bonk_scenario.grid[(2, 2)] = TileCell(t="WALL")
    
    actual_result = verify_traversable(room_bonk_scenario, default_config.movement_attributes)
    assert not actual_result
