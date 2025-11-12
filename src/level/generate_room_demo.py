import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from procedural_generator import GenerationConfig, generate_validated_room, generate_fallback_room
from room_data import MovementAttributes
from tiles.tile_types import TileType

def print_room(room):
    """Prints a textual representation of room with PCG doors."""
    width, height = room.size
    print(f"Room Size: {width}x{height}")
    
    # Print door information
    entrance_doors = [d for d in room.doors.values() if d.door_type == 'entrance']
    exit_doors = [d for d in room.doors.values() if d.door_type == 'exit']
    
    print(f"Entrance Doors: {len(entrance_doors)}")
    for door in entrance_doors:
        print(f"  Door {door.door_id}: {door.position} -> {door.destinations}")
    
    print(f"Exit Doors: {len(exit_doors)}")
    for door in exit_doors:
        print(f"  Door {door.door_id}: {door.position} -> {door.destinations}")
    
    print("-" * (width + 2))
    for y in range(height):
        row = ["|"]
        for x in range(width):
            tile = room.grid.get((x, y), room.default_tile)
            
            # Check if this position has a door
            door_at_pos = None
            for door in room.doors.values():
                if door.position == (x, y):
                    door_at_pos = door
                    break
            
            if door_at_pos:
                if door_at_pos.door_type == 'entrance':
                    row.append("E")  # Entrance door
                else:
                    row.append("X")  # Exit door
            elif tile.tile_type == TileType.WALL:
                row.append("#")
            elif tile.tile_type == TileType.AIR:
                row.append(".")
            elif tile.tile_type == TileType.DOOR:
                row.append("D")  # Door tile (fallback)
            else:
                row.append("?") # Unknown tile type
        row.append("|")
        print("".join(row))
    print("-" * (width + 2))
    for y in range(height):
        row = ["|"]
        for x in range(width):
            tile = room.grid.get((x, y), room.default_tile)
            if (x, y) == room.entrance_coords:
                row.append("E")
            elif (x, y) == room.exit_coords:
                row.append("X")
            elif tile.tile_type == TileType.WALL:
                row.append("#")
            elif tile.tile_type == TileType.AIR:
                row.append(".")
            else:
                row.append("?") # Unknown tile type
        row.append("|")
        print("".join(row))
    print("-" * (width + 2))

if __name__ == "__main__":
    print("--- Generating Procedural Room Demo ---")
    
    # Default configuration
    config = GenerationConfig()
    
    # Generate a room
    movement_attrs = MovementAttributes()
    generated_room = generate_validated_room(config, movement_attrs)
    
    # Print the room
    print_room(generated_room)
 
    print("\n--- Generating a smaller room with more iterations ---")
    small_config = GenerationConfig(
        min_room_size=15,
        max_room_size=15,
        drunkard_walk_iterations=2000,
        drunkard_walk_fill_percentage=0.6
    )
    small_room = generate_validated_room(small_config, movement_attrs)
    print_room(small_room)
 
    print("\n--- Generating a room that forces fallback (low iterations, small size) ---")
    fallback_config = GenerationConfig(
        min_room_size=5,
        max_room_size=5,
        drunkard_walk_iterations=10,
        drunkard_walk_fill_percentage=0.1
    )
    fallback_room = generate_fallback_room(fallback_config)
    print_room(fallback_room)
