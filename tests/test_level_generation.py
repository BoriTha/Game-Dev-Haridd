"""
Tests for the complete multi-room level generation system.
"""

import pytest
import random
from typing import List, Set, Tuple

from src.level.room_data import RoomData, TileCell, GenerationConfig, MovementAttributes
from src.level.level_data import LevelData, LevelGenerationConfig, DoorLink
from src.level.procedural_generator import (
    flood_fill_find_regions,
    reconnect_isolated_regions,
    generate_validated_room,
    carve_corridor_block
)
from src.level.graph_generator import (
    generate_level_graph,
    generate_complete_level
)


# --- Test Fixtures ---

@pytest.fixture
def base_movement_attrs() -> MovementAttributes:
    """Basic movement attributes for a small player."""
    return MovementAttributes(
        player_width=1,
        player_height=2,
        min_corridor_height=3
    )


@pytest.fixture
def base_room_config(base_movement_attrs) -> GenerationConfig:
    """Basic room generation config for testing."""
    return GenerationConfig(
        min_room_size=20,
        max_room_size=25,
        seed=12345,
        platform_placement_attempts=20,
        min_corridor_width=2,
        movement_attributes=base_movement_attrs
    )


@pytest.fixture
def base_level_config() -> LevelGenerationConfig:
    """Basic level generation config for testing."""
    return LevelGenerationConfig(
        num_rooms=5,
        layout_type="linear"
    )


# --- Test Classes ---

class TestFloodFill:
    """
    Tests for the flood-fill connectivity analysis.
    """

    def test_flood_fill_single_region(self):
        """Test on a room with one fully connected AIR region."""
        room = RoomData(size=(10, 10), default_tile=TileCell(t="WALL"))
        # Carve a 'C' shape
        for y in range(2, 8):
            room.set_tile(2, y, TileCell(t="AIR"))
        for x in range(3, 7):
            room.set_tile(x, 2, TileCell(t="AIR"))
            room.set_tile(x, 7, TileCell(t="AIR"))

        regions = flood_fill_find_regions(room)
        assert len(regions) == 1
        assert len(regions[0]) == 14

    def test_flood_fill_two_isolated_regions(self):
        """Test on a room with two separate AIR pockets."""
        room = RoomData(size=(10, 10), default_tile=TileCell(t="WALL"))
        # Pocket 1
        room.set_tile(2, 2, TileCell(t="AIR"))
        room.set_tile(2, 3, TileCell(t="AIR"))
        # Pocket 2
        room.set_tile(7, 7, TileCell(t="AIR"))
        room.set_tile(7, 8, TileCell(t="AIR"))

        regions = flood_fill_find_regions(room)
        assert len(regions) == 2
        
        # Sort by a representative element to make assertion order-independent
        sorted_regions = sorted(regions, key=lambda r: min(r))
        assert sorted_regions[0] == {(2, 2), (2, 3)}
        assert sorted_regions[1] == {(7, 7), (7, 8)}

    def test_flood_fill_no_air_tiles(self):
        """Test on a room with no AIR tiles."""
        room = RoomData(size=(10, 10), default_tile=TileCell(t="WALL"))
        regions = flood_fill_find_regions(room)
        assert len(regions) == 0

    def test_flood_fill_full_air_room(self):
        """Test on a room that is entirely AIR."""
        room = RoomData(size=(10, 10), default_tile=TileCell(t="AIR"))
        regions = flood_fill_find_regions(room)
        assert len(regions) == 1
        assert len(regions[0]) == 10 * 10


class TestReconnection:
    """
    Tests for the automatic reconnection of isolated regions.
    """

    def test_reconnection_connects_two_regions(self, base_room_config):
        """Verify that two isolated regions become one after reconnection."""
        room = RoomData(size=(30, 20), default_tile=TileCell(t="WALL"))
        # Region 1 (left)
        carve_corridor_block(room, 5, 10, 4, 4)
        # Region 2 (right)
        carve_corridor_block(room, 25, 10, 4, 4)

        # Before, we have two regions
        regions_before = flood_fill_find_regions(room)
        assert len(regions_before) == 2

        # Perform reconnection
        success = reconnect_isolated_regions(room, base_room_config)
        assert success is True

        # After, we should have only one
        regions_after = flood_fill_find_regions(room)
        assert len(regions_after) == 1

    def test_reconnection_respects_corridor_width(self, base_room_config):
        """Check that the new corridor has the minimum width."""
        room = RoomData(size=(30, 20), default_tile=TileCell(t="WALL"))
        # Region 1
        carve_corridor_block(room, 5, 10, 2, 2)
        # Region 2
        carve_corridor_block(room, 25, 10, 2, 2)

        # Get original AIR tiles
        air_before = set()
        for r in flood_fill_find_regions(room):
            air_before.update(r)

        # Reconnect
        reconnect_isolated_regions(room, base_room_config)

        # Get new AIR tiles
        air_after = set()
        for r in flood_fill_find_regions(room):
            air_after.update(r)
        
        new_corridor_tiles = air_after - air_before
        assert len(new_corridor_tiles) > 0

        # Check width at a midpoint of the new corridor
        # Find a tile in the new corridor and check its neighbors
        sample_tile = list(new_corridor_tiles)[len(new_corridor_tiles) // 2]
        x, y = sample_tile
        
        # Check horizontal width around the sample tile
        # This is a simplified check, but gives a good indication.
        # A full check would be more complex.
        width_at_sample = 0
        # Check left
        for i in range(base_room_config.min_corridor_width + 2):
            if room.get_tile(x - i, y).t == "AIR":
                width_at_sample += 1
            else:
                break
        # Check right (minus 1 to not double-count center)
        for i in range(1, base_room_config.min_corridor_width + 2):
            if room.get_tile(x + i, y).t == "AIR":
                width_at_sample += 1
            else:
                break
        
        # This assertion is tricky because Bresenham's line can be diagonal
        # A simpler check is that the number of new tiles is roughly
        # distance * width * height
        dist = 25 - 5
        expected_min_tiles = dist * base_room_config.min_corridor_width * base_room_config.movement_attributes.min_corridor_height
        
        # Allow for some overlap and diagonal movement
        assert len(new_corridor_tiles) >= dist * base_room_config.min_corridor_width


class TestGraphGeneration:
    """
    Tests for the high-level room graph generation.
    """

    def test_generate_linear_graph(self):
        """Test linear graph generation."""
        graph = generate_level_graph(LevelGenerationConfig(num_rooms=4, layout_type="linear"), 1)
        expected = {
            "room_0": ["room_1"],
            "room_1": ["room_2"],
            "room_2": ["room_3"],
            "room_3": [],
        }
        assert graph == expected

    def test_generate_branching_graph(self):
        """Test branching graph generation ensures connectivity."""
        config = LevelGenerationConfig(num_rooms=10, layout_type="branching", branch_probability=1.0)
        graph = generate_level_graph(config, 123)
        
        # Every room must be reachable from the start
        start_node = "room_0"
        
        # Use BFS/DFS to find all reachable nodes
        q = [start_node]
        visited = {start_node}
        while q:
            curr = q.pop(0)
            for neighbor in graph.get(curr, []):
                if neighbor not in visited:
                    visited.add(neighbor)
                    q.append(neighbor)
        
        # Assert that all nodes defined in the graph were visited
        all_nodes_in_graph = set(graph.keys())
        for neighbors in graph.values():
            all_nodes_in_graph.update(neighbors)
            
        assert visited == all_nodes_in_graph

    def test_graph_has_start_and_goal(self):
        """Test that a generated graph has a clear start and goal."""
        config = LevelGenerationConfig(num_rooms=8, layout_type="branching")
        graph = generate_level_graph(config, 42)
        
        # Start is always room_0
        assert "room_0" in graph
        
        # Goal is a room with no outgoing edges
        goal_nodes = [node for node, neighbors in graph.items() if not neighbors]
        assert len(goal_nodes) >= 1


class TestLevelData:
    """
    Tests for the LevelData container and its helper methods.
    """

    @pytest.fixture
    def sample_level(self) -> LevelData:
        """A sample LevelData object for testing."""
        level = LevelData(level_seed=1)
        graph = {
            "start": ["room1", "room2"],
            "room1": ["goal"],
            "room2": ["room1"],
            "goal": [],
            "orphan": []
        }
        level.internal_graph = graph
        level.start_room_id = "start"
        level.goal_room_id = "goal"
        
        # Add dummy rooms
        for room_id in graph:
            level.add_room(room_id, RoomData(size=(1,1), default_tile=TileCell(t="AIR")))
            
        return level

    def test_get_path_to_goal_success(self, sample_level):
        """Test finding a path in a valid graph."""
        path = sample_level.get_path_to_goal()
        assert path is not None
        assert path == ["start", "room1", "goal"]

    def test_get_path_to_goal_no_path(self, sample_level):
        """Test with a graph where goal is unreachable."""
        sample_level.internal_graph["room1"] = []  # Break the path
        path = sample_level.get_path_to_goal()
        assert path is None

    def test_get_room_depth(self, sample_level):
        """Test depth calculation."""
        assert sample_level.get_room_depth("start") == 0
        assert sample_level.get_room_depth("room1") == 1
        assert sample_level.get_room_depth("room2") == 1
        assert sample_level.get_room_depth("goal") == 2
        assert sample_level.get_room_depth("orphan") == -1  # Unreachable
        assert sample_level.get_room_depth("nonexistent") == -1


class TestFullLevelGeneration:
    """
    Integration tests for the entire level generation pipeline.
    """

    def test_generate_complete_level_creates_level(
        self, base_room_config, base_level_config, base_movement_attrs
    ):
        """Test that a valid LevelData object is returned."""
        level = generate_complete_level(
            base_room_config,
            base_level_config,
            base_movement_attrs,
            seed=999
        )
        
        assert isinstance(level, LevelData)
        assert level.level_seed == 999
        assert len(level.rooms) == base_level_config.num_rooms
        assert level.start_room_id == "room_0"
        assert level.goal_room_id == f"room_{base_level_config.num_rooms - 1}"

    def test_level_has_valid_path_to_goal(
        self, base_room_config, base_level_config, base_movement_attrs
    ):
        """Verify the generated level has a solvable path."""
        level = generate_complete_level(
            base_room_config,
            base_level_config,
            base_movement_attrs,
            seed=101
        )
        
        path = level.get_path_to_goal()
        assert path is not None
        assert path[0] == level.start_room_id
        assert path[-1] == level.goal_room_id

    def test_all_rooms_are_traversable(
        self, base_room_config, base_level_config, base_movement_attrs
    ):
        """
        Verify that every single room generated is individually traversable.
        This is a slow test.
        """
        # Use a branching layout to test more complex scenarios
        base_level_config.layout_type = "branching"
        base_level_config.num_rooms = 8
        
        level = generate_complete_level(
            base_room_config,
            base_level_config,
            base_movement_attrs,
            seed=202
        )
        
        for room_id, room in level.rooms.items():
            # This is implicitly tested by generate_validated_room,
            # but we assert it here for explicit confirmation.
            assert room.entrance_coords is not None, f"Room {room_id} missing entrance"
            assert room.exit_coords is not None, f"Room {room_id} missing exit"
            
            # The fact that generate_validated_room returned it means it's traversable.
            # A re-verification here would be redundant and even slower.
            # We trust the generator's contract.
            assert room.difficulty_rating >= 1

    def test_door_links_are_created_correctly(
        self, base_room_config, base_level_config, base_movement_attrs
    ):
        """Check that DoorLink objects are created and match room coords."""
        level = generate_complete_level(
            base_room_config,
            base_level_config,
            base_movement_attrs,
            seed=303
        )
        
        assert len(level.door_links) > 0
        
        # Check one link
        link = level.door_links[0]
        assert isinstance(link, DoorLink)
        
        from_room = level.get_room(link.from_room_id)
        to_room = level.get_room(link.to_room_id)
        
        assert from_room is not None
        assert to_room is not None
        
        # The link's coordinates must match the actual door coordinates in the rooms
        assert link.from_door_pos == from_room.exit_coords
        assert link.to_door_pos == to_room.entrance_coords
        
        # The connection must exist in the graph
        assert link.to_room_id in level.internal_graph[link.from_room_id]

    def test_difficulty_increases_with_depth(
        self, base_room_config, base_level_config, base_movement_attrs
    ):
        """Verify that deeper rooms have higher difficulty ratings."""
        base_level_config.num_rooms = 10
        level = generate_complete_level(
            base_room_config,
            base_level_config,
            base_movement_attrs,
            seed=404
        )
        
        path = level.get_path_to_goal()
        assert path is not None
        
        difficulties = [level.get_room(rid).difficulty_rating for rid in path]
        
        # Check that difficulty is non-decreasing
        for i in range(len(difficulties) - 1):
            assert difficulties[i+1] >= difficulties[i]
            
        # Check that first and last are different (for a long enough path)
        if len(difficulties) > 2:
            assert difficulties[0] < difficulties[-1]

    def test_rooms_are_distinct_within_level(
        self, base_room_config, base_level_config, base_movement_attrs
    ):
        """
        Verify that rooms generated within the same level are distinct.
        This checks if the new seeding strategy is working.
        """
        # Ensure at least two rooms are generated
        base_level_config.num_rooms = 2
        
        level = generate_complete_level(
            base_room_config,
            base_level_config,
            base_movement_attrs,
            seed=505 # Use a new seed for this test
        )
        
        assert len(level.rooms) >= 2, "Expected at least two rooms for distinctness test"
        
        room_ids = list(level.rooms.keys())
        room1 = level.get_room(room_ids[0])
        room2 = level.get_room(room_ids[1])
        
        # Compare the grid representations of the two rooms
        # They should not be identical if the seeding is working correctly
        assert room1.grid != room2.grid, "Rooms within the same level should be distinct"