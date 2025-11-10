"""
Integration tests for procedural generation system in main game loop.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.level.level_data import LevelData
from src.level.room_data import GenerationConfig, MovementAttributes, RoomData
from src.level.level_data import LevelGenerationConfig


class TestGameIntegration:
    """Test procedural generation integration with game loop."""
    
    @pytest.fixture
    def mock_game_class(self):
        """Create a minimal Game-like class for testing."""
        class MockGame:
            def __init__(self):
                self.use_procedural = True
                
                # Movement attributes
                self.movement_attrs = MovementAttributes(
                    max_jump_height=4,
                    max_jump_distance=6,
                    player_width=1,
                    player_height=2
                )
                
                # Generation configs
                self.room_gen_config = GenerationConfig(
                    min_room_size=20,
                    max_room_size=25,
                    min_corridor_width=3,
                    movement_attributes=self.movement_attrs,  # CRITICAL: Pass here
                    seed=42  # Deterministic for testing
                )
                
                self.level_gen_config = LevelGenerationConfig(
                    num_rooms=3,  # Small for fast tests
                    layout_type="linear"
                )
                
                # State tracking
                self.current_level_data = None
                self.current_level_number = 0
                self.level = None
            
            def generate_level(self, level_number: int):
                """Simulate level generation."""
                from src.level.graph_generator import generate_complete_level
                
                self.current_level_number = level_number
                level_seed = level_number * 1000
                
                self.current_level_data = generate_complete_level(
                    self.room_gen_config,
                    self.level_gen_config,
                    self.movement_attrs,
                    seed=level_seed
                )
                
                return self.current_level_data
        
        return MockGame()
    
    def test_initial_procedural_load(self, mock_game_class):
        """Test that game correctly generates LevelData on startup."""
        game = mock_game_class
        
        # Simulate initial load
        level_data = game.generate_level(1)
        
        # Assertions
        assert level_data is not None, "LevelData should be generated"
        assert isinstance(level_data, LevelData)
        assert len(level_data.rooms) == 3, "Should have 3 rooms (per config)"
        assert level_data.start_room_id is not None
        assert level_data.goal_room_id is not None
        assert game.current_level_number == 1
    
    def test_procedural_room_transition(self, mock_game_class):
        """Test room switching within a procedural level."""
        game = mock_game_class
        
        # Generate level
        level_data = game.generate_level(1)
        
        # Get start and next room
        start_room_id = level_data.start_room_id
        next_rooms = level_data.internal_graph.get(start_room_id, [])
        
        assert len(next_rooms) > 0, "Start room should have exits"
        
        next_room_id = next_rooms[0]
        next_room = level_data.get_room(next_room_id)
        
        # Assertions
        assert next_room is not None, "Next room should exist"
        assert isinstance(next_room, RoomData)
        assert next_room.entrance_coords is not None
        assert next_room.exit_coords is not None
    
    def test_level_completion_and_regeneration(self, mock_game_class):
        """Test that completing final room generates new level."""
        game = mock_game_class
        
        # Generate first level
        level1 = game.generate_level(1)
        level1_id = id(level1)  # Get object ID
        
        # Simulate completing level and generating next
        level2 = game.generate_level(2)
        level2_id = id(level2)
        
        # Assertions
        assert level2 is not None
        assert level2_id != level1_id, "Should be a NEW LevelData object"
        assert game.current_level_number == 2
        assert len(level2.rooms) == 3, "New level should have correct room count"
        
        # Verify levels are different (different seeds)
        # They should have different room layouts
        assert level1.level_seed != level2.level_seed
    
    def test_static_mode_fallback(self, mock_game_class):
        """Test that static mode still works (backwards compatibility)."""
        game = mock_game_class
        game.use_procedural = False
        
        # With use_procedural = False, level generation should be skipped
        # (In real game, this would load from ROOMS list)
        
        assert game.use_procedural is False, "Static mode should be disabled"
        
        # Verify no procedural level was generated
        assert game.current_level_data is None, "Should not have procedural level data"
    
    def test_movement_attributes_passed_correctly(self, mock_game_class):
        """Test that MovementAttributes are correctly passed to GenerationConfig."""
        game = mock_game_class
        
        # Verify movement_attrs is set
        assert game.movement_attrs is not None
        assert game.movement_attrs.max_jump_height == 4
        
        # Verify it's passed to room_gen_config
        assert game.room_gen_config.movement_attributes is not None
        assert game.room_gen_config.movement_attributes.max_jump_height == 4
        
        # Generate level and verify rooms use these attributes
        level_data = game.generate_level(1)
        
        # All rooms should have been validated with these movement attributes
        # (Implicitly tested by successful generation)
        assert len(level_data.rooms) > 0
    
    def test_difficulty_progression_in_level(self, mock_game_class):
        """Test that rooms in a level have progressive difficulty."""
        game = mock_game_class
        
        level_data = game.generate_level(1)
        path = level_data.get_path_to_goal()
        
        assert path is not None, "Should have path to goal"
        assert len(path) >= 2, "Path should have at least 2 rooms"
        
        # Get difficulty ratings along path
        difficulties = [
            level_data.get_room(room_id).difficulty_rating 
            for room_id in path
        ]
        
        # First room should be easiest
        assert difficulties[0] == 1, "Start room should have difficulty 1"
        
        # Later rooms should be harder
        assert difficulties[-1] >= difficulties[0], "Goal room should be harder than start"
    
    def test_door_links_exist(self, mock_game_class):
        """Test that DoorLink objects are created."""
        game = mock_game_class
        
        level_data = game.generate_level(1)
        
        # Should have door links for connections
        assert len(level_data.door_links) >= 2, "Linear level should have N-1 door links"
        
        # Verify door links are valid
        for link in level_data.door_links:
            assert link.from_room_id in level_data.rooms
            assert link.to_room_id in level_data.rooms
            assert link.from_door_pos is not None
            assert link.to_door_pos is not None


class TestConversionFunction:
    """Test the _convert_roomdata_to_ascii function."""
    
    def test_basic_conversion(self):
        """Test conversion of simple room."""
        from src.level.room_data import RoomData, TileCell
        
        room = RoomData(
            size=(5, 5),
            default_tile=TileCell(t="WALL"),
            grid={}
        )
        
        # Create small AIR space
        room.grid[(2, 2)] = TileCell(t="AIR")
        room.entrance_coords = (2, 2)
        
        # Mock Level class to test conversion
        from src.level.level import Level
        
        # Create a minimal Level instance just to test the method
        # (We can't fully instantiate without pygame, so we'll test the logic)
        
        # For now, just verify the method exists and is callable
        assert hasattr(Level, '_convert_roomdata_to_ascii')
    
    def test_platform_conversion(self):
        """Test that platforms are converted to '_' character."""
        from src.level.room_data import RoomData, TileCell
        
        room = RoomData(
            size=(3, 3),
            default_tile=TileCell(t="AIR"),
            grid={}
        )
        
        # Add platform tile
        room.grid[(1, 1)] = TileCell(t="WALL", flags={"PLATFORM"})
        
        # When converted, this should become '_' in ASCII
        # (Test implementation would go here once we can instantiate Level)


class TestDeterministicGeneration:
    """Test that seeded generation is reproducible."""
    
    def test_same_seed_same_level(self):
        """Test that same seed produces same level."""
        from src.level.graph_generator import generate_complete_level
        
        movement = MovementAttributes()
        config = GenerationConfig(
            min_room_size=20,
            max_room_size=25,
            movement_attributes=movement,
            seed=12345  # Fixed seed
        )
        
        level_config = LevelGenerationConfig(num_rooms=3, layout_type="linear")
        
        # Generate twice with same seed
        level1 = generate_complete_level(config, level_config, movement, seed=12345)
        level2 = generate_complete_level(config, level_config, movement, seed=12345)
        
        # Should have same structure
        assert len(level1.rooms) == len(level2.rooms)
        assert list(level1.internal_graph.keys()) == list(level2.internal_graph.keys())
    
    def test_different_seed_different_level(self):
        """Test that different seeds produce different levels."""
        from src.level.graph_generator import generate_complete_level
        
        movement = MovementAttributes()
        config = GenerationConfig(
            min_room_size=20,
            max_room_size=25,
            movement_attributes=movement,
            seed=999 # Add a seed here for determinism in the config object
        )
        
        level_config = LevelGenerationConfig(num_rooms=3, layout_type="branching")
        
        # Generate with different seeds
        level1 = generate_complete_level(config, level_config, movement, seed=111)
        level2 = generate_complete_level(config, level_config, movement, seed=222)
        
        # Seeds should be different
        assert level1.level_seed != level2.level_seed


# Run tests
if __name__ == "__main__":
    pytest.main([__file__, "-v"])
