import pytest
import math
from src.level.procedural_generator import (
    calculate_spawn_density,
    generate_random_spawn_area,
    areas_too_close,
    place_spawn_areas,
    configure_room_difficulty,
    generate_validated_room
)
from src.level.room_data import (
    RoomData,
    TileCell,
    SpawnArea,
    GenerationConfig,
    MovementAttributes
)


class TestSpawnDensityCalculation:
    """Test spawn area density calculation."""
    
    def test_small_room_minimum_spawns(self):
        """Small room gets at least min_spawn_areas"""
        room = RoomData(
            size=(10, 10),
            default_tile=TileCell(t="AIR"),
            difficulty_rating=1
        )
        config = GenerationConfig(min_spawn_areas_per_room=2)
        
        num = calculate_spawn_density(room, config)
        
        assert num >= config.min_spawn_areas_per_room
    
    def test_large_room_more_spawns(self):
        """Larger room gets more spawn areas"""
        small_room = RoomData(
            size=(10, 10),
            default_tile=TileCell(t="AIR"),
            difficulty_rating=1
        )
        large_room = RoomData(
            size=(30, 30),
            default_tile=TileCell(t="AIR"),
            difficulty_rating=1
        )
        config = GenerationConfig()
        
        small_spawns = calculate_spawn_density(small_room, config)
        large_spawns = calculate_spawn_density(large_room, config)
        
        assert large_spawns > small_spawns
    
    def test_difficulty_increases_spawns(self):
        """Higher difficulty increases spawn count"""
        room_easy = RoomData(
            size=(20, 20),
            default_tile=TileCell(t="AIR"),
            difficulty_rating=1
        )
        room_hard = RoomData(
            size=(20, 20),
            default_tile=TileCell(t="AIR"),
            difficulty_rating=8
        )
        config = GenerationConfig()
        
        easy_spawns = calculate_spawn_density(room_easy, config)
        hard_spawns = calculate_spawn_density(room_hard, config)
        
        assert hard_spawns >= easy_spawns
    
    def test_respects_maximum(self):
        """Spawn count doesn't exceed max_spawn_areas_per_room"""
        room = RoomData(
            size=(50, 50),  # Very large
            default_tile=TileCell(t="AIR"),
            difficulty_rating=10  # Max difficulty
        )
        config = GenerationConfig(max_spawn_areas_per_room=5)
        
        num = calculate_spawn_density(room, config)
        
        assert num <= config.max_spawn_areas_per_room


class TestSpawnAreaSpacing:
    """Test spawn area spacing logic."""
    
    def test_areas_overlapping_are_too_close(self):
        """Overlapping areas violate spacing"""
        area1 = SpawnArea(position=(5, 5), size=(3, 3))
        area2 = SpawnArea(position=(6, 6), size=(3, 3))  # Overlaps
        
        assert areas_too_close(area1, area2, min_spacing=1) is True
    
    def test_areas_far_apart_not_too_close(self):
        """Distant areas don't violate spacing"""
        area1 = SpawnArea(position=(5, 5), size=(3, 3))
        area2 = SpawnArea(position=(15, 15), size=(3, 3))
        
        assert areas_too_close(area1, area2, min_spacing=5) is False
    
    def test_areas_exact_spacing_not_too_close(self):
        """Areas at exact minimum spacing are acceptable"""
        area1 = SpawnArea(position=(5, 5), size=(2, 2))
        area2 = SpawnArea(position=(12, 5), size=(2, 2))  # 5 tiles apart
        
        assert areas_too_close(area1, area2, min_spacing=5) is False
    
    def test_adjacent_areas_too_close(self):
        """Adjacent areas violate spacing"""
        area1 = SpawnArea(position=(5, 5), size=(2, 2))
        area2 = SpawnArea(position=(7, 5), size=(2, 2))  # Right next to area1
        
        assert areas_too_close(area1, area2, min_spacing=3) is True


class TestSpawnAreaPlacement:
    """Test spawn area placement function."""
    
    def test_places_spawn_areas(self):
        """place_spawn_areas adds areas to room"""
        room = RoomData(
            size=(20, 20),
            default_tile=TileCell(t="AIR"),
            entrance_coords=(2, 10),
            exit_coords=(18, 10),
            difficulty_rating=1
        )
        config = GenerationConfig(
            min_spawn_areas_per_room=2,
            seed=42
        )
        
        num_placed = place_spawn_areas(room, config)
        
        assert num_placed >= 1
        assert len(room.spawn_areas) == num_placed
    
    def test_spawn_areas_avoid_doors(self):
        """Spawn areas don't overlap door exclusion zones"""
        room = RoomData(
            size=(30, 30),
            default_tile=TileCell(t="AIR"),
            entrance_coords=(5, 5),
            exit_coords=(25, 25),
            difficulty_rating=1
        )
        config = GenerationConfig(seed=123)
        
        place_spawn_areas(room, config)
        
        # Check no spawn area overlaps door coords
        entrance_x, entrance_y = room.entrance_coords
        exit_x, exit_y = room.exit_coords
        
        for area in room.spawn_areas:
            # Check area doesn't contain door coords
            assert not area.contains_point(entrance_x, entrance_y)
            assert not area.contains_point(exit_x, exit_y)
    
    def test_spawn_areas_have_rules(self):
        """Placed spawn areas have spawn_rules set"""
        room = RoomData(
            size=(20, 20),
            default_tile=TileCell(t="AIR"),
            entrance_coords=(2, 10),
            exit_coords=(18, 10),
            difficulty_rating=3
        )
        config = GenerationConfig(seed=999)
        
        place_spawn_areas(room, config)
        
        for area in room.spawn_areas:
            assert 'allow_enemies' in area.spawn_rules


class TestDifficultyConfiguration:
    """Test difficulty scaling system."""
    
    def test_depth_zero_low_difficulty(self):
        """Depth 0 (start) has low difficulty"""
        room = RoomData(
            size=(20, 20),
            default_tile=TileCell(t="AIR")
        )
        config = GenerationConfig()
        
        configure_room_difficulty(room, depth_from_start=0, config=config)
        
        assert room.depth_from_start == 0
        assert room.difficulty_rating == 1
    
    def test_depth_increases_difficulty(self):
        """Greater depth increases difficulty rating"""
        room1 = RoomData(size=(20, 20), default_tile=TileCell(t="AIR"))
        room2 = RoomData(size=(20, 20), default_tile=TileCell(t="AIR"))
        config = GenerationConfig()
        
        configure_room_difficulty(room1, depth_from_start=1, config=config)
        configure_room_difficulty(room2, depth_from_start=10, config=config)
        
        assert room2.difficulty_rating > room1.difficulty_rating
    
    def test_logarithmic_scaling(self):
        """Difficulty scales logarithmically, not linearly"""
        rooms = [
            RoomData(size=(20, 20), default_tile=TileCell(t="AIR"))
            for _ in range(20)
        ]
        config = GenerationConfig()
        
        for i, room in enumerate(rooms):
            configure_room_difficulty(room, depth_from_start=i, config=config)
        
        # Check that difficulty growth slows down
        diff_0_to_5 = rooms[5].difficulty_rating - rooms[0].difficulty_rating
        diff_10_to_15 = rooms[15].difficulty_rating - rooms[10].difficulty_rating
        
        # Later growth should be smaller (logarithmic)
        assert diff_10_to_15 <= diff_0_to_5
    
    def test_difficulty_capped(self):
        """Difficulty doesn't exceed max_difficulty_rating"""
        room = RoomData(size=(20, 20), default_tile=TileCell(t="AIR"))
        config = GenerationConfig(max_difficulty_rating=10)
        
        configure_room_difficulty(room, depth_from_start=1000, config=config)
        
        assert room.difficulty_rating <= config.max_difficulty_rating
    
    def test_spawn_areas_get_enemy_limits(self):
        """Spawn areas have max_enemies set based on difficulty"""
        room = RoomData(
            size=(20, 20),
            default_tile=TileCell(t="AIR")
        )
        # Add some spawn areas first
        room.spawn_areas.append(SpawnArea(
            position=(5, 5),
            size=(3, 3),
            spawn_rules={'allow_enemies': True}
        ))
        
        config = GenerationConfig()
        configure_room_difficulty(room, depth_from_start=5, config=config)
        
        # Check spawn area got max_enemies set
        assert 'max_enemies' in room.spawn_areas[0].spawn_rules
        assert room.spawn_areas[0].spawn_rules['max_enemies'] > 0


class TestIntegration:
    """Test complete spawn area system integration."""
    
    def test_generated_room_has_spawn_areas(self):
        """generate_validated_room creates spawn areas"""
        config = GenerationConfig(
            min_room_size=20,
            max_room_size=25,
            min_spawn_areas_per_room=2,
            seed=42
        )
        movement = MovementAttributes()
        
        room = generate_validated_room(config, movement, depth_from_start=3)
        
        assert len(room.spawn_areas) >= 2
        assert room.difficulty_rating > 1  # Depth 3 should have difficulty > 1
        assert room.depth_from_start == 3
    
    def test_difficulty_progression_across_rooms(self):
        """Sequential rooms show difficulty progression"""
        config = GenerationConfig(seed=777)
        movement = MovementAttributes()
        
        rooms = [
            generate_validated_room(config, movement, depth_from_start=i)
            for i in range(5)
        ]
        
        # Check difficulty increases
        difficulties = [r.difficulty_rating for r in rooms]
        
        assert difficulties[0] == 1  # Start room
        assert difficulties[-1] > difficulties[0]  # End room harder
    
    def test_spawn_areas_scaled_with_difficulty(self):
        """Higher difficulty rooms have more/stronger spawn areas"""
        config = GenerationConfig(
            min_room_size=25,
            max_room_size=30,
            seed=111
        )
        movement = MovementAttributes()
        
        easy_room = generate_validated_room(config, movement, depth_from_start=0)
        hard_room = generate_validated_room(config, movement, depth_from_start=15)
        
        # Count total max enemies
        easy_enemies = sum(
            area.spawn_rules.get('max_enemies', 0)
            for area in easy_room.spawn_areas
        )
        hard_enemies = sum(
            area.spawn_rules.get('max_enemies', 0)
            for area in hard_room.spawn_areas
        )
        
        assert hard_enemies >= easy_enemies
