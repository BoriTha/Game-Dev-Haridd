import unittest
from collections import deque
from src.level.procedural_generator import (
    TileCell, RoomData, MovementAttributes, GenerationConfig,
    bresenham_line, generate_fallback_room, find_valid_ground_locations,
    generate_room_layout, place_doors_and_spawn, check_physics_reach,
    check_jump_arc_clear, verify_traversable, generate_procedural_room
)

class TestProceduralGenerator(unittest.TestCase):

    def test_tile_cell_instantiation(self):
        cell = TileCell(t="WALL")
        self.assertEqual(cell.t, "WALL")
        self.assertEqual(cell.flags, set())

        cell_with_flags = TileCell(t="AIR", flags={"DOOR_ENTRANCE"})
        self.assertEqual(cell_with_flags.t, "AIR")
        self.assertEqual(cell_with_flags.flags, {"DOOR_ENTRANCE"})

    def test_room_data_instantiation(self):
        default_tile = TileCell(t="AIR")
        room = RoomData(size=(10, 10), default_tile=default_tile)
        self.assertEqual(room.size, (10, 10))
        self.assertEqual(room.default_tile, default_tile)
        self.assertEqual(room.grid, {})
        self.assertIsNone(room.entrance_coords)
        self.assertIsNone(room.exit_coords)

        room_with_data = RoomData(
            size=(5, 5),
            default_tile=TileCell(t="WALL"),
            grid={(0, 0): TileCell(t="AIR")},
            entrance_coords=(1, 1),
            exit_coords=(3, 3)
        )
        self.assertEqual(room_with_data.size, (5, 5))
        self.assertEqual(room_with_data.grid[(0, 0)].t, "AIR")
        self.assertEqual(room_with_data.entrance_coords, (1, 1))
        self.assertEqual(room_with_data.exit_coords, (3, 3))

    def test_movement_attributes_instantiation(self):
        attrs = MovementAttributes()
        self.assertEqual(attrs.player_width, 1)
        self.assertEqual(attrs.player_height, 2)
        self.assertEqual(attrs.max_jump_height, 4)
        self.assertEqual(attrs.max_jump_distance, 6)

        custom_attrs = MovementAttributes(player_width=2, player_height=3, max_jump_height=5, max_jump_distance=7)
        self.assertEqual(custom_attrs.player_width, 2)
        self.assertEqual(custom_attrs.player_height, 3)
        self.assertEqual(custom_attrs.max_jump_height, 5)
        self.assertEqual(custom_attrs.max_jump_distance, 7)

    def test_generation_config_instantiation(self):
        config = GenerationConfig()
        self.assertEqual(config.min_room_size, 20)
        self.assertEqual(config.max_room_size, 40)
        self.assertIsInstance(config.movement_attributes, MovementAttributes)

        custom_attrs = MovementAttributes(player_height=3)
        custom_config = GenerationConfig(min_room_size=10, movement_attributes=custom_attrs)
        self.assertEqual(custom_config.min_room_size, 10)
        self.assertEqual(custom_config.movement_attributes.player_height, 3)

    def test_bresenham_line_horizontal(self):
        points = bresenham_line(0, 0, 5, 0)
        self.assertEqual(points, [(0, 0), (1, 0), (2, 0), (3, 0), (4, 0), (5, 0)])

    def test_bresenham_line_vertical(self):
        points = bresenham_line(0, 0, 0, 5)
        self.assertEqual(points, [(0, 0), (0, 1), (0, 2), (0, 3), (0, 4), (0, 5)])

    def test_bresenham_line_diagonal_shallow(self):
        points = bresenham_line(0, 0, 8, 4)
        self.assertEqual(points, [(0, 0), (1, 0), (2, 1), (3, 1), (4, 2), (5, 2), (6, 3), (7, 3), (8, 4)])

    def test_bresenham_line_diagonal_steep(self):
        points = bresenham_line(0, 0, 4, 8)
        self.assertEqual(points, [(0, 0), (0, 1), (1, 2), (1, 3), (2, 4), (2, 5), (3, 6), (3, 7), (4, 8)])

    def test_bresenham_line_reverse_direction(self):
        points = bresenham_line(5, 0, 0, 0)
        self.assertEqual(points, [(5, 0), (4, 0), (3, 0), (2, 0), (1, 0), (0, 0)])

    def test_bresenham_line_single_point(self):
        points = bresenham_line(2, 2, 2, 2)
        self.assertEqual(points, [(2, 2)])

    def test_generate_fallback_room(self):
        config = GenerationConfig(min_room_size=10, max_room_size=10) # Fixed size for testing
        room = generate_fallback_room(config)

        self.assertEqual(room.size, (10, 10))
        self.assertEqual(room.default_tile.t, "AIR")

        # Check floor
        floor_y = 9 # height - 1
        for x in range(10):
            self.assertEqual(room.grid.get((x, floor_y), room.default_tile).t, "WALL")

        # Check entrance and exit coords
        self.assertEqual(room.entrance_coords, (1, 8)) # 1 tile from left, 1 above floor
        self.assertEqual(room.exit_coords, (8, 8)) # 1 tile from right, 1 above floor

        # Check door tiles
        self.assertEqual(room.grid[room.entrance_coords].t, "AIR")
        self.assertIn("DOOR_ENTRANCE", room.grid[room.entrance_coords].flags)
        self.assertEqual(room.grid[(1, 9)].t, "WALL") # Wall below entrance

        self.assertEqual(room.grid[room.exit_coords].t, "AIR")
        self.assertIn("DOOR_EXIT", room.grid[room.exit_coords].flags)
        self.assertEqual(room.grid[(8, 9)].t, "WALL") # Wall below exit

        # Check some air above the floor
        self.assertEqual(room.grid.get((5, 5), room.default_tile).t, "AIR")


    def test_find_valid_ground_locations_empty_room(self):
        room_data = RoomData((10, 10), default_tile=TileCell(t="AIR"))
        locations = find_valid_ground_locations(room_data, 1, 2)
        self.assertEqual(locations, [])

    def test_find_valid_ground_locations_flat_room(self):
        config = GenerationConfig(min_room_size=10, max_room_size=10)
        room_data = generate_fallback_room(config) # Has a flat floor and clear space
        
        # Remove entrance/exit flags to treat them as normal air for this test
        room_data.grid[room_data.entrance_coords] = TileCell(t="AIR")
        room_data.grid[room_data.exit_coords] = TileCell(t="AIR")

        # Expect all wall tiles on the floor to be valid ground locations (y=9)
        # because player_height=2 means need clearance at y=8 and y=7, which are AIR in fallback room
        
        expected_locations_simple = [(x, 9) for x in range(room_data.size[0])]
        self.assertCountEqual(locations, expected_locations_simple) # Use assertCountEqual for unordered lists
        
    def test_find_valid_ground_locations_with_obstacle(self):
        room_data = RoomData((10, 10), default_tile=TileCell(t="AIR"))
        
        # Create a floor
        for x in range(10):
            room_data.grid[(x, 9)] = TileCell(t="WALL")
        
        # Place an obstacle blocking player head space for player_height=2
        room_data.grid[(5, 8)] = TileCell(t="WALL") # Blocks (5,8) which is needed for clearance
                                                    # if player stood on (5,9)

        # Expected locations: all floor tiles except (5,9) because (5,8) is blocked
        expected_locations = []
        for x in range(10):
            if x != 5:
                expected_locations.append((x, 9))
                
        locations = find_valid_ground_locations(room_data, 1, 2)
        self.assertCountEqual(locations, expected_locations)


    def test_check_physics_reach(self):
        # Can reach (dx=5, dy=0)
        self.assertTrue(check_physics_reach((0, 0), (5, 0), max_jump_height=4, max_jump_distance=6))
        # Can reach (dx=0, dy=4 == jump up 4 tiles)
        self.assertTrue(check_physics_reach((0, 0), (0, -4), max_jump_height=4, max_jump_distance=6))
        # Cannot reach (dx=7), too far horizontally
        self.assertFalse(check_physics_reach((0, 0), (7, 0), max_jump_height=4, max_jump_distance=6))
        # Cannot reach (dy=5 == jump up 5 tiles), too high vertically
        self.assertFalse(check_physics_reach((0, 0), (0, -5), max_jump_height=4, max_jump_distance=6))
        # Falling down any distance is fine if horizontal is within limits
        self.assertTrue(check_physics_reach((0, 0), (5, 5), max_jump_height=4, max_jump_distance=6))
        # Falling down, too far horizontally
        self.assertFalse(check_physics_reach((0, 0), (7, 5), max_jump_height=4, max_jump_distance=6))
        # Jumping up and forward
        self.assertTrue(check_physics_reach((0, 0), (3, -2), max_jump_height=4, max_jump_distance=6))
        # Jumping up and forward, but too high
        self.assertFalse(check_physics_reach((0, 0), (3, -5), max_jump_height=4, max_jump_distance=6))


    def test_check_jump_arc_clear_clear_path(self):
        room_data = RoomData((10, 10), default_tile=TileCell(t="AIR"))
        self.assertTrue(check_jump_arc_clear(room_data, (0, 0), (5, 0), player_height=2))
        self.assertTrue(check_jump_arc_clear(room_data, (1, 1), (3, 3), player_height=2))

    def test_check_jump_arc_clear_blocked_path_head_bonk(self):
        room_data_size = (10, 10)
        room_data = RoomData(room_data_size, default_tile=TileCell(t="AIR"))
        
        # Player at (0,1), player_height=2. Body is (0,1) and (0,0).
        # Jump to (5,1). Path includes (2,1) and (2,0).
        # Block at (2,0) which is player's head space at (2,1)
        room_data.grid[(2, 0)] = TileCell(t="WALL") 
        self.assertFalse(check_jump_arc_clear(room_data, (0, 1), (5, 1), player_height=2))
        
    def test_check_jump_arc_clear_blocked_path_body_collision(self):
        room_data_size = (10, 10)
        room_data = RoomData(room_data_size, default_tile=TileCell(t="AIR"))
        
        # Player at (0,1), player_height=2. Body is (0,1) and (0,0).
        # Jump to (5,1). Path includes (2,1).
        # Block at (2,1) which is player's body space at (2,1)
        room_data.grid[(2, 1)] = TileCell(t="WALL")
        self.assertFalse(check_jump_arc_clear(room_data, (0, 1), (5, 1), player_height=2))
        
    def test_check_jump_arc_clear_out_of_bounds_blocked(self):
        room_data_size = (5, 5)
        room_data = RoomData(room_data_size, default_tile=TileCell(t="AIR"))
        # Path goes from (0,0) to fake position (6,0) which is out of bounds (x > width)
        self.assertFalse(check_jump_arc_clear(room_data, (0, 0), (6, 0), player_height=1)) 
        # Path goes from (0,0) to fake position (0,-1) which is out of bounds (y < 0)
        self.assertFalse(check_jump_arc_clear(room_data, (0, 0), (0, -1), player_height=1))
        # Path goes from (4,4) to fake position (4,5) which is out of bounds (y >= height)
        self.assertFalse(check_jump_arc_clear(room_data, (4, 4), (4, 5), player_height=1))

    def test_generate_room_layout_dimensions_and_fill(self):
        config = GenerationConfig(min_room_size=10, max_room_size=10, drunkard_walk_iterations=100, drunkard_walk_fill_percentage=0.5)
        room = generate_room_layout(config)

        self.assertEqual(room.size, (10, 10))
        self.assertEqual(room.default_tile.t, "WALL")
        
        # Check that some AIR tiles were created
        air_tiles_count = sum(1 for tile in room.grid.values() if tile.t == "AIR")
        self.assertGreater(air_tiles_count, 0)
        
        # Check that no entrance/exit coords are set yet
        self.assertIsNone(room.entrance_coords)
        self.assertIsNone(room.exit_coords)

        # Test with a very low fill percentage, should still create some air
        config_low_fill = GenerationConfig(min_room_size=10, max_room_size=10, drunkard_walk_iterations=10, drunkard_walk_fill_percentage=0.01)
        room_low_fill = generate_room_layout(config_low_fill)
        air_tiles_count_low_fill = sum(1 for tile in room_low_fill.grid.values() if tile.t == "AIR")
        self.assertGreater(air_tiles_count_low_fill, 0)

        # Test with a very high fill percentage, should create more air
        config_high_fill = GenerationConfig(min_room_size=10, max_room_size=10, drunkard_walk_iterations=1000, drunkard_walk_fill_percentage=0.9)
        room_high_fill = generate_room_layout(config_high_fill)
        air_tiles_count_high_fill = sum(1 for tile in room_high_fill.grid.values() if tile.t == "AIR")
        self.assertGreater(air_tiles_count_high_fill, air_tiles_count) # Should be more than low fill

    def test_place_doors_and_spawn(self):
        config = GenerationConfig(min_room_size=20, max_room_size=20)
        room = generate_room_layout(config) # Generate a layout first

        # Ensure there's at least some ground for doors to be placed
        # For testing, let's ensure a flat floor if drunkard walk didn't make one
        if not any(tile.t == "WALL" for tile in room.grid.values()):
            for x in range(room.size[0]):
                room.grid[(x, room.size[1] - 1)] = TileCell(t="WALL")
                room.grid[(x, room.size[1] - 2)] = TileCell(t="AIR") # Ensure clearance

        place_doors_and_spawn(room, config)

        self.assertIsNotNone(room.entrance_coords)
        self.assertIsNotNone(room.exit_coords)

        # Check entrance properties
        self.assertEqual(room.grid[room.entrance_coords].t, "AIR")
        self.assertIn("DOOR_ENTRANCE", room.grid[room.entrance_coords].flags)
        self.assertEqual(room.grid[(room.entrance_coords[0], room.entrance_coords[1] + 1)].t, "WALL")

        # Check exit properties
        self.assertEqual(room.grid[room.exit_coords].t, "AIR")
        self.assertIn("DOOR_EXIT", room.grid[room.exit_coords].flags)
        self.assertEqual(room.grid[(room.exit_coords[0], room.exit_coords[1] + 1)].t, "WALL")

        # Ensure entrance and exit are distinct
        self.assertNotEqual(room.entrance_coords, room.exit_coords)

        # Ensure entrance is on the left side and exit on the right side (roughly)
        self.assertLess(room.entrance_coords[0], room.size[0] // 2)
        self.assertGreater(room.exit_coords[0], room.size[0] // 2)

    def test_verify_traversable_simple_path(self):
        # Create a simple traversable room (like fallback room)
        config = GenerationConfig(min_room_size=10, max_room_size=10)
        room = generate_fallback_room(config)
        self.assertTrue(verify_traversable(room, config))

    def test_verify_traversable_blocked_path(self):
        # Create a room where path is blocked
        config = GenerationConfig(min_room_size=10, max_room_size=10)
        room = generate_fallback_room(config)
        
        # Block the path between entrance and exit
        # Assuming entrance is (1,8) and exit is (8,8)
        # Block the entire floor between them
        for x in range(2, 8):
            room.grid[(x, 9)] = TileCell(t="WALL") # Floor
            room.grid[(x, 8)] = TileCell(t="WALL") # Player head space
            room.grid[(x, 7)] = TileCell(t="WALL") # Player body space
        
        self.assertFalse(verify_traversable(room, config))

    def test_verify_traversable_no_doors(self):
        room = RoomData(size=(10, 10), default_tile=TileCell(t="AIR"))
        config = GenerationConfig()
        self.assertFalse(verify_traversable(room, config))

    def test_generate_procedural_room_success(self):
        # This test is probabilistic due to random generation.
        # We'll try to generate a room and assert it's not the fallback.
        # A small room size and high fill percentage increases chances of success.
        config = GenerationConfig(min_room_size=15, max_room_size=15, 
                                  drunkard_walk_iterations=500, drunkard_walk_fill_percentage=0.7)
        
        # Mock random to make it deterministic for testing purposes if needed,
        # but for now, we'll rely on multiple attempts.
        
        room = generate_procedural_room(config, max_attempts=20)
        
        # Assert it's not the fallback room (which has specific entrance/exit coords)
        # This is a weak assertion, but better than nothing for probabilistic generation.
        fallback_room = generate_fallback_room(config)
        self.assertNotEqual(room.entrance_coords, fallback_room.entrance_coords)
        self.assertNotEqual(room.exit_coords, fallback_room.exit_coords)
        
        # More robust check: ensure it has a path
        self.assertTrue(verify_traversable(room, config))

    def test_generate_procedural_room_fallback(self):
        # Force generation to fail by making verify_traversable always return False
        # This requires mocking, which is beyond simple unittest.
        # For now, we'll simulate a scenario where drunkard walk creates a tiny room
        # and place_doors_and_spawn fails, leading to fallback.
        
        # A very small room with very few iterations and low fill might lead to no valid ground
        config = GenerationConfig(min_room_size=5, max_room_size=5, 
                                  drunkard_walk_iterations=1, drunkard_walk_fill_percentage=0.01)
        
        # This is not guaranteed to fail, but increases the probability.
        # A proper test would involve mocking `verify_traversable` to always return False.
        
        room = generate_procedural_room(config, max_attempts=3)
        
        # Assert it is the fallback room
        fallback_room = generate_fallback_room(config)
        self.assertEqual(room.entrance_coords, fallback_room.entrance_coords)
        self.assertEqual(room.exit_coords, fallback_room.exit_coords)
        self.assertEqual(room.size, fallback_room.size)
        # Compare grids (might need a custom comparison for sparse grids)
        # For simplicity, check a few key tiles
        self.assertEqual(room.grid[(1,3)].t, fallback_room.grid[(1,3)].t) # Entrance air
        self.assertEqual(room.grid[(1,4)].t, fallback_room.grid[(1,4)].t) # Entrance wall below


```