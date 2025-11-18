from typing import List, Dict, Tuple, Optional
from .tile_types import TileType


from typing import List, Dict, Tuple, Optional
from .tile_types import TileType
from ..core.constants import TILE_CHAR_MAP, LEGACY_CHAR_ALIASES, ENTITY_CHAR_MAP


class TileParser:
    """Parses ASCII level definitions to tile grids."""

    def __init__(self):
        # Use canonical mappings from constants
        self.ascii_map: Dict[str, TileType] = TILE_CHAR_MAP
        self.entity_markers: Dict[str, str] = ENTITY_CHAR_MAP

    def parse_ascii_level(self, ascii_level: List[str], legacy: bool = False) -> Tuple[List[List[int]], Dict[str, List[Tuple[int, int]]]]:
        """
        Parse ASCII level definition to tile grid and entity positions.

        Args:
            ascii_level: The list of strings representing the level.
            legacy: If True, applies legacy parsing rules for characters.
        """
        if not ascii_level:
            return [], {}

        # Determine the correct tile map to use for this parsing operation
        active_tile_map = self.ascii_map
        if legacy:
            legacy_map = self.ascii_map.copy()
            legacy_map['.'] = TileType.AIR  # Legacy rule: '.' is AIR
            active_tile_map = legacy_map

        # Find max dimensions
        max_width = max(len(line) for line in ascii_level)
        height = len(ascii_level)

        # Initialize tile grid with air
        tile_grid = [[TileType.AIR.value for _ in range(max_width)] for _ in range(height)]
        entity_positions: Dict[str, List[Tuple[int, int]]] = {}

        # Parse each line
        for y, line in enumerate(ascii_level):
            for x, char in enumerate(line):
                # Handle legacy aliases before lookup
                lookup_char = char
                if legacy and char in LEGACY_CHAR_ALIASES:
                    lookup_char = LEGACY_CHAR_ALIASES[char]

                if lookup_char in active_tile_map:
                    # It's a tile
                    tile_type = active_tile_map[lookup_char]
                    tile_grid[y][x] = tile_type.value
                elif char in self.entity_markers:
                    # It's an entity (use original char for entities)
                    entity_type = self.entity_markers[char]
                    if entity_type not in entity_positions:
                        entity_positions[entity_type] = []
                    entity_positions[entity_type].append((x, y))
                # Unknown characters are ignored (treated as air)

        return tile_grid, entity_positions

    def set_custom_mapping(self, ascii_char: str, tile_type: TileType):
        """Set a custom ASCII character to tile type mapping."""
        self.ascii_map[ascii_char] = tile_type

    def set_entity_marker(self, ascii_char: str, entity_type: str):
        """Set a custom ASCII character as an entity marker."""
        self.entity_markers[ascii_char] = entity_type

    def get_ascii_representation(self, tile_grid: List[List[int]],
                                entity_positions: Optional[Dict[str, List[Tuple[int, int]]]] = None) -> List[str]:
        """
        Convert tile grid back to ASCII representation.
        Useful for debugging or saving levels.
        """
        if not tile_grid:
            return []

        # Create reverse mapping from the canonical map
        tile_to_ascii = {tile_type: char for char, tile_type in self.ascii_map.items()}

        # Initialize with spaces
        height = len(tile_grid)
        width = max(len(row) for row in tile_grid) if tile_grid else 0
        ascii_lines = [[' ' for _ in range(width)] for _ in range(height)]

        # Convert tiles
        for y in range(height):
            for x in range(len(tile_grid[y])):
                tile_value = tile_grid[y][x]
                tile_type = TileType(tile_value)
                if tile_type in tile_to_ascii:
                    ascii_lines[y][x] = tile_to_ascii[tile_type]

        # Add entity markers
        if entity_positions:
            # Create reverse mapping for entities
            entity_to_ascii = {v: k for k, v in self.entity_markers.items()}
            for entity_type, positions in entity_positions.items():
                if entity_type in entity_to_ascii:
                    entity_char = entity_to_ascii[entity_type]
                    for x, y in positions:
                        if 0 <= y < height and 0 <= x < width:
                            ascii_lines[y][x] = entity_char

        # Convert to strings
        return [''.join(line) for line in ascii_lines]

    def validate_ascii_level(self, ascii_level: List[str]) -> List[str]:
        """
        Validate ASCII level and return list of issues found.
        """
        issues = []

        if not ascii_level:
            issues.append("Level is empty")
            return issues

        # Check for consistent line lengths
        line_lengths = [len(line) for line in ascii_level]
        if len(set(line_lengths)) > 1:
            issues.append(f"Inconsistent line lengths: {line_lengths}")

        # Check for valid characters
        valid_chars = set(self.ascii_map.keys()) | set(self.entity_markers.keys()) | set(LEGACY_CHAR_ALIASES.keys())
        for y, line in enumerate(ascii_level):
            for x, char in enumerate(line):
                if char not in valid_chars and char != ' ':
                    issues.append(f"Unknown character '{char}' at position ({x}, {y})")

        # Check for spawn points
        has_spawn = any('S' in line for line in ascii_level)
        if not has_spawn:
            issues.append("No spawn point 'S' found")

        return issues

    def get_tile_info(self, ascii_char: str) -> Optional[str]:
        """Get information about what a character represents."""
        if ascii_char in self.ascii_map:
            tile_type = self.ascii_map[ascii_char]
            return f"Tile: {tile_type.name} ({tile_type.value})"
        elif ascii_char in self.entity_markers:
            return f"Entity: {self.entity_markers[ascii_char]}"
        elif ascii_char in LEGACY_CHAR_ALIASES:
            target_char = LEGACY_CHAR_ALIASES[ascii_char]
            return f"Legacy Alias for '{target_char}' ({self.get_tile_info(target_char)})"
        else:
            return "Unknown"

    def print_legend(self):
        """Print a legend of all recognized characters."""
        import logging
        logger = logging.getLogger(__name__)
        logger.info("=== Tile Legend ===")
        for char, tile_type in self.ascii_map.items():
            logger.info("  '%s' : %s", char, tile_type.name)
        logger.info("\n=== Entity Legend ===")
        for char, entity_type in self.entity_markers.items():
            logger.info("  '%s' : %s", char, entity_type)
        logger.info("\n=== Legacy Aliases ===")
        for char, target in LEGACY_CHAR_ALIASES.items():
            logger.info("  '%s' : Alias for '%s'", char, target)