#!/usr/bin/env python3
"""Quick boundary test without debug output."""

import sys
import os

# Suppress pygame output
os.environ['PYGAME_HIDE_SUPPORT_PROMPT'] = '1'

# Add project root to path
sys.path.append('.')

from src.level.pcg_generator_simple import generate_simple_pcg_level_set
from src.level.config_loader import load_pcg_config

def check_boundaries(room, config):
    """Check if any boundary tiles are air."""
    tiles = room.tiles
    h = len(tiles)
    w = len(tiles[0]) if h > 0 else 0
    
    # Check boundaries
    for x in range(w):
        if tiles[0][x] == config.air_tile_id:
            return f"top row at x={x}"
        if tiles[-1][x] == config.air_tile_id:
            return f"bottom row at x={x}"
    
    for y in range(h):
        if tiles[y][0] == config.air_tile_id:
            return f"left column at y={y}"
        if tiles[y][-1] == config.air_tile_id:
            return f"right column at y={y}"
    
    return None

def test_seeds():
    """Test multiple seeds for boundary holes."""
    config = load_pcg_config()
    seeds = [42, 123, 999, 2024, 1, 777]
    
    for seed in seeds:
        print(f"Testing seed {seed}...", end=" ")
        try:
            level_set = generate_simple_pcg_level_set(seed=seed)
            
            for level in level_set.levels:
                for room in level.rooms:
                    hole = check_boundaries(room, config)
                    if hole:
                        print(f"❌ FOUND HOLE: {hole}")
                        return True
                        
            print("✅ OK")
                        
        except Exception as e:
            print(f"💥 ERROR: {e}")
            return True
    
    return False

if __name__ == "__main__":
    print("Testing boundary protection...")
    print("=" * 50)
    
    found_holes = test_seeds()
    
    print("=" * 50)
    if found_holes:
        print("💥 BOUNDARY HOLES STILL EXIST!")
    else:
        print("🎉 NO BOUNDARY HOLES FOUND!")