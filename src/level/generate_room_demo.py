from src.level.procedural_generator import GenerationConfig, generate_procedural_room, TileCell
from src.tiles.tile_types import TileType

def print_room(room):
    """Prints a textual representation of the room."""
    width, height = room.size
    print(f"Room Size: {width}x{height}")
    print(f"Entrance: {room.entrance_coords}")
    print(f"Exit: {room.exit_coords}")
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
    generated_room = generate_procedural_room(config)
    
    # Print the room
    print_room(generated_room)

    print("\n--- Generating a smaller room with more iterations ---")
    small_config = GenerationConfig(
        min_room_size=15,
        max_room_size=15,
        drunkard_walk_iterations=2000,
        drunkard_walk_fill_percentage=0.6
    )
    small_room = generate_procedural_room(small_config)
    print_room(small_room)

    print("\n--- Generating a room that forces fallback (low iterations, small size) ---")
    fallback_config = GenerationConfig(
        min_room_size=5,
        max_room_size=5,
        drunkard_walk_iterations=10,
        drunkard_walk_fill_percentage=0.1
    )
    fallback_room = generate_procedural_room(fallback_config, max_attempts=3)
    print_room(fallback_room)
