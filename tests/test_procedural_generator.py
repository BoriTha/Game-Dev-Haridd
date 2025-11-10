import unittest
from src.level.room_data import GenerationConfig, MovementAttributes
from src.level.procedural_generator import (
    generate_room_layout,
    generate_validated_room,
)
from src.level.traversal_verification import verify_traversable

class TestProceduralGenerator(unittest.TestCase):

    def test_generate_room_layout_creates_air_tiles(self):
        """
        Tests that the Drunkard's Walk algorithm carves out AIR tiles.
        """
        config = GenerationConfig(
            min_room_size=20, 
            max_room_size=20, 
            drunkard_walk_iterations=100
        )
        room = generate_room_layout(config)

        # The default tile is WALL, so any AIR tiles must have been carved.
        air_tile_count = sum(1 for tile in room.grid.values() if tile.t == "AIR")
        
        self.assertGreater(air_tile_count, 0, "generate_room_layout should create at least one AIR tile.")
        self.assertEqual(room.default_tile.t, "WALL", "Default tile should be WALL for carving.")

    def test_generate_validated_room_returns_traversable_room(self):
        """
        Tests that the main generation function produces a valid, traversable room.
        This is an integration test for the whole process.
        """
        config = GenerationConfig(
            min_room_size=30,
            max_room_size=30,
            drunkard_walk_iterations=1000, # More iterations to ensure connectivity
            max_room_generation_attempts=50 # Give it enough attempts to succeed
        )
        movement_attrs = MovementAttributes()
        
        # This test can be slow and is probabilistic, but it's crucial.
        # It might fail occasionally if generation is unlucky.
        # If it fails consistently, there's a bug in the generation or validation logic.
        generated_room = generate_validated_room(config, movement_attrs)

        is_traversable = verify_traversable(generated_room, movement_attrs)
        
        self.assertTrue(
            is_traversable, 
            "generate_validated_room must return a traversable room, but validation failed."
        )

if __name__ == '__main__':
    unittest.main()
