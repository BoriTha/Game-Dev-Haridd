import pygame
from config import WIDTH, HEIGHT

class Camera:
    def __init__(self):
        self.x = 0
        self.y = 0
        self.lerp = 0.12
        # Available zoom levels
        self.zoom_levels = [1.0, 1.2, 1.5]  # Full view, slight zoom, current zoom
        self.current_zoom_index = 2  # Start with 1.0x zoom (Full View)
        self.zoom = self.zoom_levels[self.current_zoom_index]
        self.target_zoom = self.zoom
        self.zoom_transition_speed = 5.0  # Speed of smooth zoom transitions
        # Level boundaries (set by game)
        self.level_width = 0
        self.level_height = 0

    def update(self, target_rect: pygame.Rect, dt: float = 1/60):
        # Smooth zoom transition
        if abs(self.zoom - self.target_zoom) > 0.01:
            self.zoom += (self.target_zoom - self.zoom) * self.zoom_transition_speed * dt

        # center target in world coordinates taking zoom into account
        tx = target_rect.centerx - (WIDTH / (2 * self.zoom))
        ty = target_rect.centery - (HEIGHT / (2 * self.zoom))
        self.x += (tx - self.x) * self.lerp
        self.y += (ty - self.y) * self.lerp
        
        # Clamp camera to level boundaries
        if self.level_width > 0 and self.level_height > 0:
            # Calculate the visible area size in world coordinates
            view_width = WIDTH / self.zoom
            view_height = HEIGHT / self.zoom
            
            # Clamp camera position so it doesn't show outside level bounds
            # If level is smaller than view, center it
            if self.level_width <= view_width:
                self.x = (self.level_width - view_width) / 2
            else:
                self.x = max(0, min(self.x, self.level_width - view_width))
            
            if self.level_height <= view_height:
                self.y = (self.level_height - view_height) / 2
            else:
                self.y = max(0, min(self.y, self.level_height - view_height))

    def to_screen(self, p):
        return (int((p[0] - self.x) * self.zoom), int((p[1] - self.y) * self.zoom))

    def to_screen_rect(self, r: pygame.Rect):
        return pygame.Rect(
            int((r.x - self.x) * self.zoom),
            int((r.y - self.y) * self.zoom),
            int(r.w * self.zoom),
            int(r.h * self.zoom)
        )

    def toggle_zoom(self):
        """Cycle through available zoom levels."""
        self.current_zoom_index = (self.current_zoom_index + 1) % len(self.zoom_levels)
        self.target_zoom = self.zoom_levels[self.current_zoom_index]
        return self.zoom_levels[self.current_zoom_index]

    def get_zoom_label(self):
        """Get human-readable label for current zoom level."""
        zoom = self.zoom_levels[self.current_zoom_index]
        if zoom == 1.0:
            return "Full View"
        elif zoom == 1.2:
            return "Slight Zoom"
        elif zoom == 1.5:
            return "Normal Zoom"
        else:
            return f"{zoom}x"
