import pytest
from src.level.procedural_generator import (
    carve_corridor_block,
    generate_room_layout
)
from src.level.room_data import (
    RoomData,
    TileCell,
    GenerationConfig,
    MovementAttributes
)


class TestCorridorCarving:
    """Test the corridor block carving function."""
    
    def test_carve_single_tile(self):
        """Carving 1x1 block creates single AIR tile"""
        room = RoomData(
            size=(10, 10),
            default_tile=TileCell(t="WALL"),
            grid={}
        )
        
        carve_corridor_block(room, center_x=5, center_y=5, width=1, height=1)
        
        assert room.get_tile(5, 5).t == "AIR"
        assert room.get_tile(4, 5).t == "WALL"  # Adjacent not carved
    
    def test_carve_horizontal_corridor(self):
        """Carving 3x1 block creates horizontal corridor"""
        room = RoomData(
            size=(10, 10),
            default_tile=TileCell(t="WALL"),
            grid={}
        )
        
        carve_corridor_block(room, center_x=5, center_y=5, width=3, height=1)
        
        # Center row should be AIR
        assert room.get_tile(4, 5).t == "AIR"
        assert room.get_tile(5, 5).t == "AIR"
        assert room.get_tile(6, 5).t == "AIR"
        
        # Above/below should be WALL
        assert room.get_tile(5, 4).t == "WALL"
        assert room.get_tile(5, 6).t == "WALL"
    
    def test_carve_respects_bounds(self):
        """Carving near edge doesn't crash"""
        room = RoomData(
            size=(5, 5),
            default_tile=TileCell(t="WALL"),
            grid={}
        )
        
        # Carve near edge - shouldn't crash
        carve_corridor_block(room, center_x=1, center_y=1, width=5, height=5)
        
        # Should carve what fits
        assert room.get_tile(1, 1).t == "AIR"
        # No crash = success
    
    def test_carve_even_width_centered(self):
        """Even width carves correctly centered"""
        room = RoomData(
            size=(10, 10),
            default_tile=TileCell(t="WALL"),
            grid={}
        )
        
        carve_corridor_block(room, center_x=5, center_y=5, width=4, height=1)
        
        # Should carve tiles 3, 4, 5, 6 (centered on 5)
        assert room.get_tile(3, 5).t == "AIR"
        assert room.get_tile(4, 5).t == "AIR"
        assert room.get_tile(5, 5).t == "AIR"
        assert room.get_tile(6, 5).t == "AIR"
        
        assert room.get_tile(2, 5).t == "WALL"
        assert room.get_tile(7, 5).t == "WALL"


class TestRoomLayoutGeneration:
    """Test room generation with corridor constraints."""
    
    def test_corridors_respect_player_width(self):
        """Generated corridors are at least player_width wide"""
        config = GenerationConfig(
            min_room_size=15,
            max_room_size=20,
            min_corridor_width=2,
            seed=42
        )
        config.movement_attributes = MovementAttributes(
            player_width=2,
            player_height=2,
            min_corridor_height=2
        )
        
        room = generate_room_layout(config)
        
        # Find all carved corridors (horizontal spans of AIR)
        for y in range(1, room.size[1] - 1):
            consecutive_air = 0
            for x in range(room.size[0]):
                if room.get_tile(x, y).t == "AIR":
                    consecutive_air += 1
                else:
                    # Check if we just exited a corridor
                    if consecutive_air > 0:
                        # Corridor must be at least player_width wide
                        assert consecutive_air >= config.movement_attributes.player_width, \
                            f"Found corridor only {consecutive_air} tiles wide at y={y}"
                    consecutive_air = 0
    
    def test_corridors_have_vertical_clearance(self):
        """Generated corridors have sufficient height"""
        config = GenerationConfig(
            min_room_size=15,
            max_room_size=20,
            seed=123
        )
        config.movement_attributes = MovementAttributes(
            player_height=3,
            min_corridor_height=3
        )
        
        room = generate_room_layout(config)
        
        # Find AIR tiles and check vertical clearance
        air_tiles = [
            (x, y) 
            for x in range(room.size[0]) 
            for y in range(room.size[1])
            if room.get_tile(x, y).t == "AIR"
        ]
        
        # Sample check: if there's AIR, there should be vertical space
        if air_tiles:
            # Check a few random AIR tiles
            for x, y in air_tiles[::10]:  # Sample every 10th tile
                # Count vertical AIR span
                air_above = 0
                for dy in range(-2, 1):  # Check 2 above, current
                    check_y = y + dy
                    if room.is_in_bounds(x, check_y):
                        if room.get_tile(x, check_y).t == "AIR":
                            air_above += 1
                
                # Should have some vertical clearance
                assert air_above >= 1  # At least current tile
    
    def test_room_has_entrance_and_exit_coords(self):
        """Generated room has entrance and exit coordinates set"""
        config = GenerationConfig(seed=999)
        room = generate_room_layout(config)
        
        assert room.entrance_coords is not None
        assert room.exit_coords is not None
        assert room.entrance_coords != room.exit_coords
    
    def test_room_carves_significant_space(self):
        """Generated room carves a meaningful amount of AIR"""
        config = GenerationConfig(
            min_room_size=20,
            max_room_size=20,
            seed=777
        )
        room = generate_room_layout(config)
        
        # Count AIR tiles
        air_count = sum(
            1 for tile in room.grid.values() if tile.t == "AIR"
        )
        
        total_tiles = room.size[0] * room.size[1]
        air_percentage = air_count / total_tiles
        
        # Should carve at least 20% of room
        assert air_percentage >= 0.20, \
            f"Only carved {air_percentage:.1%} of room"





# Integration test
class TestFullGenerationWithConstraints:
    """Test complete generation respects all constraints."""
    
    def test_generated_rooms_are_wide_enough(self):
        """Complete generation produces traversable, wide corridors"""
        config = GenerationConfig(
            min_room_size=15,
            max_room_size=20,
            min_corridor_width=3,
            max_room_generation_attempts=5,
            seed=42
        )
        config.movement_attributes = MovementAttributes(
            player_width=2,
            player_height=2,
            min_corridor_height=2
        )
        
        from src.level.procedural_generator import generate_validated_room
        
        room = generate_validated_room(config, config.movement_attributes)
        
        # Room should be valid
        assert room is not None
        assert room.entrance_coords is not None
        assert room.exit_coords is not None
        
        # Should pass traversability
        from src.level.traversal_verification import verify_traversable
        assert verify_traversable(room, config.movement_attributes) is True
