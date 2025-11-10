import pytest
from src.level.procedural_generator import (
    Platform, add_platform, remove_platform, place_platforms,
    create_exclusion_map, platform_overlaps_exclusion,
    generate_validated_room
)
from src.level.room_data import RoomData, TileCell, GenerationConfig, MovementAttributes

# Import traversal verification
try:
    from src.level.traversal_verification import verify_traversable
except ImportError:
    # If module doesn't exist or has different name, skip integration tests
    pytest.skip("traversal_verification module not available", allow_module_level=True)


class TestPlatformDataStructure:
    """Test the Platform dataclass."""

    def test_platform_get_all_coords_single_tile(self):
        """Platform at (5, 5) with width=1 returns [(5, 5)]"""
        platform = Platform(top_left=(5, 5), width=1, height=1)
        assert platform.get_all_coords() == [(5, 5)]

    def test_platform_get_all_coords_horizontal(self):
        """Platform at (3, 4) with width=3 returns correct coords"""
        platform = Platform(top_left=(3, 4), width=3, height=1)
        expected = [(3, 4), (4, 4), (5, 4)]
        assert platform.get_all_coords() == expected

    def test_platform_get_all_coords_rectangular(self):
        """2x2 platform returns all 4 coordinates"""
        platform = Platform(top_left=(0, 0), width=2, height=2)
        expected = [(0, 0), (1, 0), (0, 1), (1, 1)]
        assert set(platform.get_all_coords()) == set(expected)


class TestPlatformManipulation:
    """Test adding and removing platforms."""

    def test_add_platform_creates_wall_tiles(self):
        """Adding platform sets tiles to WALL"""
        room = RoomData(
            size=(10, 10),
            default_tile=TileCell(t="AIR"),
            grid={}
        )
        platform = Platform(top_left=(5, 5), width=2, height=1)

        add_platform(room, platform)

        assert room.get_tile(5, 5).t == "WALL"
        assert room.get_tile(6, 5).t == "WALL"
        assert "PLATFORM" in room.get_tile(5, 5).flags

    def test_remove_platform_restores_default(self):
        """Removing platform reverts to default_tile"""
        room = RoomData(
            size=(10, 10),
            default_tile=TileCell(t="AIR"),
            grid={}
        )
        platform = Platform(top_left=(5, 5), width=2, height=1)

        add_platform(room, platform)
        remove_platform(room, platform)

        # Should revert to default AIR
        assert room.get_tile(5, 5).t == "AIR"
        assert room.get_tile(6, 5).t == "AIR"
        assert (5, 5) not in room.grid  # Removed from sparse grid

    def test_add_remove_is_idempotent(self):
        """Multiple add/remove cycles work correctly"""
        room = RoomData(
            size=(10, 10),
            default_tile=TileCell(t="AIR"),
            grid={}
        )
        platform = Platform(top_left=(3, 3), width=1, height=1)

        for _ in range(3):
            add_platform(room, platform)
            assert room.get_tile(3, 3).t == "WALL"
            remove_platform(room, platform)
            assert room.get_tile(3, 3).t == "AIR"


class TestExclusionMap:
    """Test exclusion zone creation."""

    def test_exclusion_around_entrance(self):
        """3x3 zone around entrance is excluded"""
        room = RoomData(
            size=(20, 20),
            default_tile=TileCell(t="AIR"),
            grid={},
            entrance_coords=(10, 10)
        )
        config = GenerationConfig()

        exclusion = create_exclusion_map(room, config)

        # Check 3x3 area
        assert (10, 10) in exclusion  # Center
        assert (9, 9) in exclusion    # Top-left
        assert (11, 11) in exclusion  # Bottom-right
        assert (9, 10) in exclusion   # Corrected from (8, 10) which is outside 3x3

    def test_platform_overlaps_exclusion_true(self):
        """Platform overlapping exclusion zone detected"""
        platform = Platform(top_left=(9, 9), width=2, height=1)
        exclusion_map = {(10, 10), (10, 9), (11, 9)}

        assert platform_overlaps_exclusion(platform, exclusion_map) is True

    def test_platform_overlaps_exclusion_false(self):
        """Platform not overlapping exclusion zone"""
        platform = Platform(top_left=(5, 5), width=2, height=1)
        exclusion_map = {(10, 10), (10, 9), (11, 9)}

        assert platform_overlaps_exclusion(platform, exclusion_map) is False


class TestPlacePlatformsRollback:
    """Test the core rollback functionality."""

    def test_platform_blocking_path_is_removed(self):
        """Platform that blocks critical path is rolled back"""
        # Create simple room: entrance on left, exit on right
        room = RoomData(
            size=(10, 10),
            default_tile=TileCell(t="AIR"),
            grid={}
        )

        # Create floor
        for x in range(10):
            room.grid[(x, 9)] = TileCell(t="WALL")

        room.entrance_coords = (1, 8)
        room.exit_coords = (8, 8)

        config = GenerationConfig(
            platform_placement_attempts=5,
            seed=42  # Deterministic
        )
        movement = MovementAttributes(
            max_jump_height=2,
            max_jump_distance=3,
            player_width=1,
            player_height=2
        )

        # This test is probabilistic but with a seed, it should be deterministic.
        # We expect that if a blocking platform is placed, it gets removed.
        place_platforms(room, config, movement)

        # After placement, room should still be traversable
        assert verify_traversable(room, movement) is True

    def test_multiple_valid_platforms_added(self):
        """Multiple non-blocking platforms are kept"""
        room = RoomData(
            size=(20, 20),
            default_tile=TileCell(t="AIR"),
            grid={}
        )

        # Create large floor
        for x in range(20):
            room.grid[(x, 19)] = TileCell(t="WALL")

        room.entrance_coords = (2, 18)
        room.exit_coords = (17, 18)

        config = GenerationConfig(
            platform_placement_attempts=10,
            seed=123
        )
        movement = MovementAttributes()

        num_platforms = place_platforms(room, config, movement)

        # Should add some platforms
        assert num_platforms > 0
        assert num_platforms <= 10

    def test_no_platforms_near_doors(self):
        """Platforms don't overlap door exclusion zones"""
        room = RoomData(
            size=(15, 15),
            default_tile=TileCell(t="AIR"),
            grid={}
        )

        # Floor
        for x in range(15):
            room.grid[(x, 14)] = TileCell(t="WALL")

        room.entrance_coords = (2, 13)
        room.exit_coords = (12, 13)

        config = GenerationConfig(platform_placement_attempts=20, seed=999)
        movement = MovementAttributes()

        place_platforms(room, config, movement)

        # Check 3x3 area around entrance has no platforms
        for dx in range(-1, 2):
            for dy in range(-1, 2):
                x, y = room.entrance_coords[0] + dx, room.entrance_coords[1] + dy
                tile = room.get_tile(x, y)
                assert "PLATFORM" not in tile.flags


# Integration test
class TestFullGeneration:
    """Test complete room generation with new platform system."""

    def test_generated_room_always_traversable(self):
        """Generated rooms with platforms are always valid"""
        config = GenerationConfig(
            min_room_size=15,
            max_room_size=20,
            platform_placement_attempts=15,
            seed=42
        )
        movement = MovementAttributes()

        room = generate_validated_room(config, movement)

        assert verify_traversable(room, movement) is True

        # Room should have entrance and exit
        assert room.entrance_coords is not None
        assert room.exit_coords is not None
