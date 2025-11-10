import pytest
from src.level.room_data import (
    TileCell,
    RoomData,
    SpawnArea,
    MovementAttributes,
    GenerationConfig
)


class TestTileCellComplete:
    """Test TileCell with all attributes."""
    
    def test_tilecell_with_entity_id(self):
        """TileCell can store entity reference"""
        tile = TileCell(t="FLOOR", entity_id="player_001")
        
        assert tile.t == "FLOOR"
        assert tile.entity_id == "player_001"
    
    def test_tilecell_with_metadata(self):
        """TileCell can store metadata"""
        tile = TileCell(
            t="WALL",
            metadata={"breakable": True, "health": 100}
        )
        
        assert tile.metadata["breakable"] is True
        assert tile.metadata["health"] == 100
    
    def test_tilecell_defaults(self):
        """TileCell has correct defaults"""
        tile = TileCell(t="AIR")
        
        assert tile.entity_id is None
        assert tile.metadata == {}
        assert tile.flags == set()
    
    def test_tilecell_repr_includes_all_fields(self):
        """TileCell repr shows all non-default fields"""
        tile = TileCell(
            t="DOOR",
            flags={"LOCKED"},
            entity_id="door_001",
            metadata={"key_id": "gold_key"}
        )
        
        repr_str = repr(tile)
        assert "DOOR" in repr_str
        assert "LOCKED" in repr_str
        assert "door_001" in repr_str
        assert "gold_key" in repr_str


class TestSpawnArea:
    """Test SpawnArea dataclass."""
    
    def test_spawn_area_creation(self):
        """SpawnArea can be created with basic params"""
        area = SpawnArea(
            position=(5, 5),
            size=(3, 3)
        )
        
        assert area.position == (5, 5)
        assert area.size == (3, 3)
        assert area.spawn_rules == {}
    
    def test_spawn_area_with_rules(self):
        """SpawnArea can store spawn rules"""
        area = SpawnArea(
            position=(10, 10),
            size=(5, 5),
            spawn_rules={
                'allow_enemies': True,
                'max_enemies': 3,
                'difficulty_min': 2
            }
        )
        
        assert area.spawn_rules['allow_enemies'] is True
        assert area.spawn_rules['max_enemies'] == 3
    
    def test_contains_point_inside(self):
        """contains_point returns True for points inside area"""
        area = SpawnArea(position=(10, 10), size=(5, 5))
        
        assert area.contains_point(10, 10) is True  # Top-left
        assert area.contains_point(12, 12) is True  # Center
        assert area.contains_point(14, 14) is True  # Bottom-right-1
    
    def test_contains_point_outside(self):
        """contains_point returns False for points outside area"""
        area = SpawnArea(position=(10, 10), size=(5, 5))
        
        assert area.contains_point(9, 10) is False   # Left of area
        assert area.contains_point(15, 10) is False  # Right of area
        assert area.contains_point(10, 15) is False  # Below area
    
    def test_get_all_coords(self):
        """get_all_coords returns all coordinates in area"""
        area = SpawnArea(position=(5, 5), size=(2, 2))
        
        coords = area.get_all_coords()
        expected = [(5, 5), (6, 5), (5, 6), (6, 6)]
        
        assert set(coords) == set(expected)
        assert len(coords) == 4
    
    def test_spawn_area_with_entity_list(self):
        """SpawnArea can specify allowed entities"""
        area = SpawnArea(
            position=(0, 0),
            size=(10, 10),
            possible_entities=["goblin", "slime", "bat"],
            allowed_entity_tags=["enemy", "common"]
        )
        
        assert "goblin" in area.possible_entities
        assert "enemy" in area.allowed_entity_tags


class TestRoomDataComplete:
    """Test RoomData with all attributes."""
    
    def test_roomdata_with_spawn_areas(self):
        """RoomData can store spawn areas"""
        room = RoomData(
            size=(20, 20),
            default_tile=TileCell(t="AIR")
        )
        
        spawn1 = SpawnArea(position=(5, 5), size=(3, 3))
        spawn2 = SpawnArea(position=(15, 15), size=(2, 2))
        
        room.spawn_areas.append(spawn1)
        room.spawn_areas.append(spawn2)
        
        assert len(room.spawn_areas) == 2
        assert room.spawn_areas[0].position == (5, 5)
        assert room.spawn_areas[1].position == (15, 15)
    
    def test_roomdata_difficulty_fields(self):
        """RoomData has difficulty rating and depth"""
        room = RoomData(
            size=(10, 10),
            default_tile=TileCell(t="AIR"),
            difficulty_rating=5,
            depth_from_start=3
        )
        
        assert room.difficulty_rating == 5
        assert room.depth_from_start == 3
    
    def test_roomdata_defaults(self):
        """RoomData has correct defaults for new fields"""
        room = RoomData(
            size=(10, 10),
            default_tile=TileCell(t="AIR")
        )
        
        assert room.spawn_areas == []
        assert room.difficulty_rating == 1
        assert room.depth_from_start == 0
    
    def test_roomdata_with_complex_spawn_areas(self):
        """RoomData can have spawn areas with rules"""
        room = RoomData(
            size=(30, 30),
            default_tile=TileCell(t="AIR"),
            difficulty_rating=3,
            depth_from_start=5
        )
        
        # Enemy spawn area
        enemy_area = SpawnArea(
            position=(10, 10),
            size=(5, 5),
            spawn_rules={'allow_enemies': True, 'max_enemies': 5}
        )
        
        # Exclusion zone (no spawns)
        exclusion = SpawnArea(
            position=(2, 2),
            size=(3, 3),
            spawn_rules={'allow_enemies': False}
        )
        
        room.spawn_areas.extend([enemy_area, exclusion])
        
        assert len(room.spawn_areas) == 2
        assert room.spawn_areas[0].spawn_rules['allow_enemies'] is True
        assert room.spawn_areas[1].spawn_rules['allow_enemies'] is False


class TestDataModelIntegration:
    """Test data models work together."""
    
    def test_tile_with_entity_in_room(self):
        """TileCell with entity_id can be added to RoomData"""
        room = RoomData(
            size=(10, 10),
            default_tile=TileCell(t="AIR")
        )
        
        # Place a tile with an entity
        enemy_tile = TileCell(
            t="FLOOR",
            entity_id="enemy_001",
            metadata={"enemy_type": "goblin"}
        )
        
        room.set_tile(5, 5, enemy_tile)
        
        retrieved = room.get_tile(5, 5)
        assert retrieved.entity_id == "enemy_001"
        assert retrieved.metadata["enemy_type"] == "goblin"
    
    def test_spawn_area_overlapping_check(self):
        """Can check if spawn areas overlap"""
        room = RoomData(
            size=(20, 20),
            default_tile=TileCell(t="AIR")
        )
        
        area1 = SpawnArea(position=(5, 5), size=(5, 5))
        area2 = SpawnArea(position=(8, 8), size=(5, 5))  # Overlaps with area1
        
        room.spawn_areas.extend([area1, area2])
        
        # Check if point is in any spawn area
        coords1 = set(area1.get_all_coords())
        coords2 = set(area2.get_all_coords())
        
        overlap = coords1 & coords2
        assert len(overlap) > 0  # Should have overlap


class TestGenerationConfigComplete:
    """Test GenerationConfig is complete."""
    
    def test_config_has_all_required_fields(self):
        """GenerationConfig has all necessary attributes"""
        config = GenerationConfig(
            min_room_size=10,
            max_room_size=30,
            seed=42
        )
        
        # Check all expected fields exist
        assert hasattr(config, 'movement_attributes')
        assert hasattr(config, 'min_corridor_width')
        assert hasattr(config, 'spawn_area_spacing')
        assert hasattr(config, 'base_enemy_density')
        assert hasattr(config, 'max_enemies_per_room')
        assert hasattr(config, 'platform_placement_attempts')
        assert hasattr(config, 'max_room_generation_attempts')
        assert hasattr(config, 'seed')
        
        assert config.seed == 42
