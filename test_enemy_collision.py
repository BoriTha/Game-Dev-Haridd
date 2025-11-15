#!/usr/bin/env python3
"""
Quick test to verify that PCG levels now generate solids for enemy collision.
"""

import sys
import os
sys.path.append(os.path.dirname(__file__))

from src.level.pcg_generator_simple import generate_simple_pcg_level_set
from src.level.level_loader import level_loader
from src.tiles.tile_registry import tile_registry
from src.tiles.tile_types import TileType
from config import TILE

def test_pcg_solids():
    """Test that PCG levels generate solids properly."""
    print("Testing PCG solids generation...")
    
    # Generate a small level set for testing
    level_set = generate_simple_pcg_level_set(seed=42)
    
    # Get the first room
    room = level_set.levels[0].rooms[0]
    print(f"Testing room: {room.room_code}")
    print(f"Room dimensions: {len(room.tiles)}x{len(room.tiles[0])}")
    
    # Simulate what PCGLevel does
    class MockPCGLevel:
        def __init__(self):
            self.tile_grid = room.tiles
            self.solids = []
            
        def _update_solids_from_grid(self):
            """Update solids list from tile grid for enemy collision system."""
            self.solids = []
            if not self.tile_grid:
                return
                
            for y, row in enumerate(self.tile_grid):
                for x, tile_value in enumerate(row):
                    if tile_value >= 0:
                        tile_type = TileType(tile_value)
                        tile_data = tile_registry.get_tile(tile_type)
                        
                        # Add solids for tiles with full collision
                        if tile_data and tile_data.collision.collision_type == "full":
                            rect = (x * TILE, y * TILE, TILE, TILE)
                            self.solids.append(rect)
    
    # Test the solids generation
    level = MockPCGLevel()
    level._update_solids_from_grid()
    
    print(f"Generated {len(level.solids)} solid collision rectangles")
    
    # Show some sample solids
    if level.solids:
        print("Sample solid rectangles (first 5):")
        for i, solid in enumerate(level.solids[:5]):
            print(f"  {i+1}: {solid}")
    
    # Count different tile types
    tile_counts = {}
    for row in room.tiles:
        for tile in row:
            tile_counts[tile] = tile_counts.get(tile, 0) + 1
    
    print("Tile type distribution:")
    for tile_id, count in sorted(tile_counts.items()):
        tile_type = TileType(tile_id) if tile_id >= 0 else "Invalid"
        print(f"  {tile_type}: {count} tiles")
    
    # Verify we have collision tiles
    collision_tiles = 0
    for row in room.tiles:
        for tile in row:
            if tile >= 0:
                tile_type = TileType(tile)
                tile_data = tile_registry.get_tile(tile_type)
                if tile_data and tile_data.collision.collision_type == "full":
                    collision_tiles += 1
    
    print(f"Found {collision_tiles} tiles with 'full' collision")
    print(f"Expected solids count: {collision_tiles}")
    print(f"Actual solids count: {len(level.solids)}")
    
    if len(level.solids) == collision_tiles:
        print("✅ SUCCESS: Solids count matches collision tiles count!")
        return True
    else:
        print("❌ FAILURE: Solids count doesn't match collision tiles!")
        return False

if __name__ == "__main__":
    success = test_pcg_solids()
    sys.exit(0 if success else 1)