import pygame
from src.core.utils import resource_path
from typing import List, Optional, Dict, Tuple
from .tile_types import TileType
from .tile_registry import tile_registry


class TileRenderer:
    """Handles rendering of tiles."""

    def __init__(self, tile_size: Optional[int] = None):
        from config import TILE
        # Use provided tile_size or fall back to configured TILE constant
        self.tile_size = tile_size if tile_size is not None else TILE
        self.tile_cache: Dict[TileType, pygame.Surface] = {}
        self.zoom_cache: Dict[str, pygame.Surface] = {}  # For zoom-scaled surfaces
        self.base_cache: Dict[TileType, pygame.Surface] = {}  # For base surfaces
        self.animation_cache: Dict[str, List[pygame.Surface]] = {}
        self.animation_timers: Dict[str, float] = {}
        # Pre-rendered level cache for PCG levels
        self.level_surface_cache: Dict[str, pygame.Surface] = {}
        self.cached_camera_offset: Tuple[float, float] = (0, 0)
        self.cached_zoom: float = 1.0
        
        # Chunk-based rendering cache for large PCG rooms
        self.chunk_size = 16  # 16x16 tile chunks
        self.chunk_cache: Dict[str, Optional[pygame.Surface]] = {}  # key: "room_code_cx_cy_zoom"
        self.max_chunk_cache_size = 100  # Limit memory usage

    def render_tile(self, surface: pygame.Surface, tile_type: TileType,
                   x: int, y: int, camera_offset: Tuple[float, float] = (0, 0),
                   time_delta: float = 0, zoom: float = 1.0):
        """Render a single tile at given position."""
        tile_data = tile_registry.get_tile(tile_type)
        if not tile_data or tile_type == TileType.AIR:
            return

        # Get or create tile surface at the correct size
        tile_surface = self._get_tile_surface_for_zoom(tile_data, time_delta, zoom)
        if tile_surface:
            # Calculate screen position, applying zoom.
            screen_x = int((x - camera_offset[0]) * zoom)
            screen_y = int((y - camera_offset[1]) * zoom)
            
            # Blit the tile (surface is already scaled to correct size)
            surface.blit(tile_surface, (screen_x, screen_y))

    def _get_tile_surface_for_zoom(self, tile_data, time_delta: float, zoom: float) -> Optional[pygame.Surface]:
        """Get or create tile surface at the correct size for the given zoom."""
        tile_type = tile_data.tile_type
        
        # Create a cache key that includes the zoom level
        cache_key = f"{tile_type.value}_{zoom}"
        
        # Check if we have animation
        if tile_data.visual.animation_frames:
            return self._get_animated_surface_for_zoom(tile_data, time_delta, zoom, cache_key)

        # Use cached surface for this zoom level
        if cache_key in self.zoom_cache:
            return self.zoom_cache[cache_key]

        # Get the base surface and scale it to the correct size
        base_surface = self._get_base_tile_surface(tile_data, time_delta)
        if base_surface:
            # Scale to the correct size for this zoom
            screen_size = int(self.tile_size * zoom)
            scaled_surface = pygame.transform.scale(base_surface, (screen_size, screen_size))
            
            # Cache it
            self.zoom_cache[cache_key] = scaled_surface
            return scaled_surface
            
        return None

    def _get_animated_surface_for_zoom(self, tile_data, time_delta: float, zoom: float, cache_key: str) -> Optional[pygame.Surface]:
        """Get animated surface for tile at the correct zoom."""
        # Initialize animation if needed
        if cache_key not in self.animation_timers:
            self.animation_timers[cache_key] = 0
            self.animation_cache[cache_key] = []

        # Load animation frames if not cached
        if not self.animation_cache[cache_key]:
            for frame_path in tile_data.visual.animation_frames:
                try:
                    frame = pygame.image.load(resource_path(frame_path)).convert_alpha()
                    # Scale frame to the correct size for this zoom
                    screen_size = int(self.tile_size * zoom)
                    frame = pygame.transform.scale(frame, (screen_size, screen_size))
                    self.animation_cache[cache_key].append(frame)
                except:
                    # Fallback to static surface if frame loading fails
                    base_surface = self._get_base_tile_surface(tile_data, time_delta)
                    if base_surface:
                        screen_size = int(self.tile_size * zoom)
                        frame = pygame.transform.scale(base_surface, (screen_size, screen_size))
                        self.animation_cache[cache_key] = [frame]
                    else:
                        self.animation_cache[cache_key] = []

        # Update animation timer
        self.animation_timers[cache_key] += time_delta

        # Get current frame
        frames = self.animation_cache[cache_key]
        if frames:
            frame_index = int(self.animation_timers[cache_key] / tile_data.visual.animation_speed) % len(frames)
            return frames[frame_index]

        # Fallback
        base_surface = self._get_base_tile_surface(tile_data, time_delta)
        if base_surface:
            screen_size = int(self.tile_size * zoom)
            return pygame.transform.scale(base_surface, (screen_size, screen_size))
        return None

    def _get_base_tile_surface(self, tile_data, time_delta: float):
        """Get the base tile surface (without zoom scaling)."""
        tile_type = tile_data.tile_type

        # Use cached base surface
        if tile_type in self.base_cache:
            return self.base_cache[tile_type]

        # Create new base surface
        surface = self._create_tile_surface(tile_data)
        if surface:
            # Cache the base surface
            self.base_cache[tile_type] = surface
            return surface
            
        return None

    def _get_tile_surface(self, tile_data, time_delta: float) -> Optional[pygame.Surface]:
        """Get cached or create new surface for tile."""
        tile_type = tile_data.tile_type

        # Check if we have animation
        if tile_data.visual.animation_frames:
            return self._get_animated_surface(tile_data, time_delta)

        # Use cached static surface
        if tile_type in self.tile_cache:
            return self.tile_cache[tile_type]

        # Create new surface
        surface = self._create_tile_surface(tile_data)
        self.tile_cache[tile_type] = surface
        return surface

    def _get_animated_surface(self, tile_data, time_delta: float) -> pygame.Surface:
        """Get animated surface for tile."""
        tile_type = tile_data.tile_type
        cache_key = f"{tile_type}_anim"

        # Initialize animation
        if cache_key not in self.animation_timers:
            self.animation_timers[cache_key] = 0
            self.animation_cache[cache_key] = []

        # Load animation frames if not cached
        if not self.animation_cache[cache_key]:
            for frame_path in tile_data.visual.animation_frames:
                try:
                    frame = pygame.image.load(resource_path(frame_path)).convert_alpha()
                    frame = pygame.transform.scale(frame, (self.tile_size, self.tile_size))
                    self.animation_cache[cache_key].append(frame)
                except:
                    # Fallback to static surface if frame loading fails
                    surface = self._create_tile_surface(tile_data)
                    self.animation_cache[cache_key] = [surface]

        # Update animation timer
        self.animation_timers[cache_key] += time_delta

        # Get current frame
        frames = self.animation_cache[cache_key]
        if frames:
            frame_index = int(self.animation_timers[cache_key] / tile_data.visual.animation_speed) % len(frames)
            return frames[frame_index]

        # Fallback
        return self._create_tile_surface(tile_data)

    def _create_tile_surface(self, tile_data) -> pygame.Surface:
        """Create surface for tile based on its visual properties."""
        surface = pygame.Surface((self.tile_size, self.tile_size), pygame.SRCALPHA)

        # Try to load sprite (but don't replace the background surface immediately)
        sprite = None
        if getattr(tile_data.visual, 'sprite_path', None):
            try:
                sprite = pygame.image.load(resource_path(tile_data.visual.sprite_path)).convert_alpha()
            except Exception:
                sprite = None

        # Create colored rectangle with border if needed
        color = tile_data.visual.base_color
        if len(color) == 3:
            color = (*color, 255)  # Add alpha if not present

        # Draw main tile
        if tile_data.visual.border_radius > 0:
            pygame.draw.rect(surface, color, surface.get_rect(),
                           border_radius=tile_data.visual.border_radius)
        else:
            pygame.draw.rect(surface, color, surface.get_rect())

        # Draw border if specified
        if tile_data.visual.render_border and tile_data.visual.border_color:
            border_color = tile_data.visual.border_color
            if len(border_color) == 3:
                border_color = (*border_color, 255)
            pygame.draw.rect(surface, border_color, surface.get_rect(), 2,
                           border_radius=tile_data.visual.border_radius)

        # If we loaded a sprite, composite it over the rounded background so
        # sprite per-pixel alpha is preserved and rounded corners show through.
        if sprite:
            try:
                # Ensure tile_size is an int
                size = int(self.tile_size)
                scaled = pygame.transform.scale(sprite, (size, size))
                surface.blit(scaled, (0, 0))
            except Exception:
                # Don't let sprite issues crash tile rendering
                pass

        return surface

    def render_tile_grid(
        self,
        surface: pygame.Surface,
        tile_grid: List[List[int]],
        camera_offset: Tuple[float, float] = (0, 0),
        visible_rect: Optional[pygame.Rect] = None,
        time_delta: float = 0,
        zoom: float = 1.0,
        room_code: Optional[str] = None,
    ):
        """
        Render all visible tiles in the grid for the given camera and zoom.
        Uses chunk-based caching to improve performance on large PCG levels.

        camera_offset: (camera_x, camera_y) in WORLD coordinates.
        zoom: current zoom factor.
        room_code: Optional room identifier for chunk caching.
        """
        if not tile_grid:
            return

        map_height = len(tile_grid)
        map_width = len(tile_grid[0])

        if visible_rect is None:
            visible_rect = surface.get_rect()

        screen_w = visible_rect.width
        screen_h = visible_rect.height

        cam_x, cam_y = camera_offset

        # Visible WORLD bounds based on camera + zoom
        world_left = cam_x
        world_top = cam_y
        world_right = cam_x + screen_w / zoom
        world_bottom = cam_y + screen_h / zoom

        # Convert world bounds to TILE indices with small buffer
        buffer_tiles = 2

        start_tx = max(0, int(world_left // self.tile_size) - buffer_tiles)
        end_tx = min(
            map_width,
            int(world_right // self.tile_size) + buffer_tiles,
        )

        start_ty = max(0, int(world_top // self.tile_size) - buffer_tiles)
        end_ty = min(
            map_height,
            int(world_bottom // self.tile_size) + buffer_tiles,
        )

        DEBUG_TILE_RENDERER = False
        if DEBUG_TILE_RENDERER:
            import logging
            logging.getLogger(__name__).debug(
                "[TileRenderer] zoom=%0.2f screen=(%dx%d) world=(%0.1f,%0.1f)-(%0.1f,%0.1f) tiles_x=[%d,%d) tiles_y=[%d,%d)",
                zoom, screen_w, screen_h, world_left, world_top, world_right, world_bottom, start_tx, end_tx, start_ty, end_ty
            )

        # Use chunk-based rendering if room_code is provided (for PCG levels)
        if room_code:
            self._render_tile_grid_chunked(
                surface, tile_grid, start_tx, end_tx, start_ty, end_ty,
                camera_offset, time_delta, zoom, room_code
            )
        else:
            # Fallback to traditional tile-by-tile rendering
            self._render_tile_grid_traditional(
                surface, tile_grid, start_tx, end_tx, start_ty, end_ty,
                camera_offset, time_delta, zoom
            )

    def _render_tile_grid_traditional(
        self,
        surface: pygame.Surface,
        tile_grid: List[List[int]],
        start_tx: int,
        end_tx: int,
        start_ty: int,
        end_ty: int,
        camera_offset: Tuple[float, float],
        time_delta: float,
        zoom: float,
    ):
        """Traditional tile-by-tile rendering (no caching)."""
        for ty in range(start_ty, end_ty):
            row = tile_grid[ty]
            for tx in range(start_tx, end_tx):
                tile_value = row[tx]
                # Skip air tiles entirely
                if tile_value < 0 or tile_value == 0:
                    continue

                tile_type = TileType(tile_value)
                
                # Additional check to skip AIR tiles by enum
                if tile_type == TileType.AIR:
                    continue
                
                world_x = tx * self.tile_size
                world_y = ty * self.tile_size

                self.render_tile(
                    surface=surface,
                    tile_type=tile_type,
                    x=world_x,
                    y=world_y,
                    camera_offset=camera_offset,
                    time_delta=time_delta,
                    zoom=zoom,
                )

    def _render_tile_grid_chunked(
        self,
        surface: pygame.Surface,
        tile_grid: List[List[int]],
        start_tx: int,
        end_tx: int,
        start_ty: int,
        end_ty: int,
        camera_offset: Tuple[float, float],
        time_delta: float,
        zoom: float,
        room_code: str,
    ):
        """Chunk-based rendering with caching for better performance."""
        # Calculate which chunks are visible
        start_chunk_x = start_tx // self.chunk_size
        end_chunk_x = (end_tx + self.chunk_size - 1) // self.chunk_size
        start_chunk_y = start_ty // self.chunk_size
        end_chunk_y = (end_ty + self.chunk_size - 1) // self.chunk_size

        # Render each visible chunk
        for chunk_y in range(start_chunk_y, end_chunk_y):
            for chunk_x in range(start_chunk_x, end_chunk_x):
                self._render_chunk(
                    surface, tile_grid, chunk_x, chunk_y,
                    camera_offset, time_delta, zoom, room_code
                )

    def _render_chunk(
        self,
        surface: pygame.Surface,
        tile_grid: List[List[int]],
        chunk_x: int,
        chunk_y: int,
        camera_offset: Tuple[float, float],
        time_delta: float,
        zoom: float,
        room_code: str,
    ):
        """Render a single chunk with caching."""
        # Round zoom to reduce cache variations
        zoom_key = round(zoom, 1)
        cache_key = f"{room_code}_{chunk_x}_{chunk_y}_{zoom_key}"

        # Check if chunk is already cached
        if cache_key in self.chunk_cache:
            chunk_surface = self.chunk_cache[cache_key]
        else:
            # Generate chunk surface
            chunk_surface = self._generate_chunk_surface(
                tile_grid, chunk_x, chunk_y, zoom
            )
            
            # Cache it
            self.chunk_cache[cache_key] = chunk_surface
            
            # Limit cache size
            if len(self.chunk_cache) > self.max_chunk_cache_size:
                # Remove oldest entries (simple FIFO)
                keys_to_remove = list(self.chunk_cache.keys())[:10]
                for key in keys_to_remove:
                    del self.chunk_cache[key]

        # Blit the cached chunk to screen
        if chunk_surface:
            world_x = chunk_x * self.chunk_size * self.tile_size
            world_y = chunk_y * self.chunk_size * self.tile_size
            screen_x = int((world_x - camera_offset[0]) * zoom)
            screen_y = int((world_y - camera_offset[1]) * zoom)
            surface.blit(chunk_surface, (screen_x, screen_y))

    def _generate_chunk_surface(
        self,
        tile_grid: List[List[int]],
        chunk_x: int,
        chunk_y: int,
        zoom: float,
    ) -> Optional[pygame.Surface]:
        """Generate a pre-rendered surface for a chunk."""
        map_height = len(tile_grid)
        map_width = len(tile_grid[0]) if map_height > 0 else 0

        # Calculate tile bounds for this chunk
        start_tx = chunk_x * self.chunk_size
        end_tx = min(start_tx + self.chunk_size, map_width)
        start_ty = chunk_y * self.chunk_size
        end_ty = min(start_ty + self.chunk_size, map_height)

        if start_tx >= map_width or start_ty >= map_height:
            return None

        # Create surface for chunk
        chunk_pixel_size = int(self.chunk_size * self.tile_size * zoom)
        chunk_surface = pygame.Surface(
            (chunk_pixel_size, chunk_pixel_size),
            pygame.SRCALPHA
        )

        # Render all tiles in chunk to surface
        for ty in range(start_ty, end_ty):
            row = tile_grid[ty]
            for tx in range(start_tx, end_tx):
                tile_value = row[tx]
                if tile_value <= 0:
                    continue

                try:
                    tile_type = TileType(tile_value)
                    if tile_type == TileType.AIR:
                        continue

                    tile_data = tile_registry.get_tile(tile_type)
                    if not tile_data:
                        continue

                    # Get tile surface
                    tile_surface = self._get_tile_surface_for_zoom(tile_data, 0, zoom)
                    if tile_surface:
                        # Position within chunk
                        local_x = (tx - start_tx) * int(self.tile_size * zoom)
                        local_y = (ty - start_ty) * int(self.tile_size * zoom)
                        chunk_surface.blit(tile_surface, (local_x, local_y))
                except (ValueError, KeyError):
                    continue

        return chunk_surface

    def render_debug_grid(self, surface: pygame.Surface, tile_grid: List[List[int]],
                         camera_offset: Tuple[float, float] = (0, 0),
                         show_collision_boxes: bool = False, zoom: float = 1.0):
        """Render debug information about tiles."""
        if not tile_grid:
            return

        grid_color = (100, 100, 100, 100)
        font = pygame.font.Font(None, 12)

        # Get visible area
        start_x = max(0, int(camera_offset[0] // self.tile_size))
        end_x = min(len(tile_grid[0]),
                   int((camera_offset[0] + surface.get_width() / zoom) // self.tile_size) + 1)
        start_y = max(0, int(camera_offset[1] // self.tile_size))
        end_y = min(len(tile_grid),
                   int((camera_offset[1] + surface.get_height() / zoom) // self.tile_size) + 1)

        # Draw grid lines
        for x in range(start_x, end_x + 1):
            screen_x = (x * self.tile_size - camera_offset[0]) * zoom
            pygame.draw.line(surface, grid_color, (screen_x, 0),
                           (screen_x, surface.get_height()), 1)

        for y in range(start_y, end_y + 1):
            screen_y = (y * self.tile_size - camera_offset[1]) * zoom
            pygame.draw.line(surface, grid_color, (0, screen_y),
                           (surface.get_width(), screen_y), 1)

        # Show collision boxes if requested (disabled to avoid Pylance issues)
        # TODO: Re-enable once collision system is fully type-safe
        if show_collision_boxes:
            pass  # Collision debug rendering temporarily disabled

    def clear_cache(self):
        """Clear all cached surfaces."""
        self.tile_cache.clear()
        self.zoom_cache.clear()
        self.base_cache.clear()
        self.animation_cache.clear()
        self.animation_timers.clear()
        self.level_surface_cache.clear()
        self.chunk_cache.clear()
    
    def clear_chunk_cache_for_room(self, room_code: str):
        """Clear chunk cache for a specific room."""
        keys_to_remove = [k for k in self.chunk_cache.keys() if k.startswith(f"{room_code}_")]
        for key in keys_to_remove:
            del self.chunk_cache[key]
    
    def preload_room_chunks(self, tile_grid: List[List[int]], room_code: str, zoom: float = 1.0):
        """Preload all chunks for a room (call during loading screen)."""
        if not tile_grid:
            return
        
        map_height = len(tile_grid)
        map_width = len(tile_grid[0]) if map_height > 0 else 0
        
        max_chunk_x = (map_width + self.chunk_size - 1) // self.chunk_size
        max_chunk_y = (map_height + self.chunk_size - 1) // self.chunk_size
        
        # Generate all chunks
        for chunk_y in range(max_chunk_y):
            for chunk_x in range(max_chunk_x):
                zoom_key = round(zoom, 1)
                cache_key = f"{room_code}_{chunk_x}_{chunk_y}_{zoom_key}"
                
                if cache_key not in self.chunk_cache:
                    chunk_surface = self._generate_chunk_surface(
                        tile_grid, chunk_x, chunk_y, zoom
                    )
                    # Only cache if generation succeeded
                    if chunk_surface:
                        self.chunk_cache[cache_key] = chunk_surface

    def preload_tiles(self):
        """Preload all tile surfaces for different zoom levels."""
        for tile_type in TileType:
            tile_data = tile_registry.get_tile(tile_type)
            if tile_data and tile_type != TileType.AIR:
                # Preload for each zoom level (only non-air tiles)
                for zoom in [1.0, 1.2, 1.5]:
                    self._get_tile_surface_for_zoom(tile_data, 0, zoom)