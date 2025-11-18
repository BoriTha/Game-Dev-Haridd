"""
Physics Component - Shared physics and collision handling for all entities
Eliminates code duplication across player and enemy classes
"""

import pygame
from typing import Optional
from config import GRAVITY, TERMINAL_VY, TILE
from ...tiles import TileCollision, TileType


class PhysicsComponent:
    """Handles physics and collision detection for entities"""
    
    def __init__(self, entity):
        self.entity = entity
        self.gravity_multiplier = 1.0
        self.terminal_velocity = TERMINAL_VY
        self.friction = 0.8
        self.bounce_factor = 0.5
        self.tile_collision = TileCollision(TILE)
        
    def apply_gravity(self, gravity_multiplier=None):
        """Apply gravity to entity's vertical velocity"""
        if gravity_multiplier is None:
            gravity_multiplier = self.gravity_multiplier
            
        # Only apply if entity is gravity affected
        if getattr(self.entity, 'gravity_affected', True):
            self.entity.vy = min(
                self.entity.vy + GRAVITY * gravity_multiplier, 
                self.terminal_velocity
            )
    
    def handle_horizontal_movement(self, level):
        """Handle horizontal movement and collision"""
        if not hasattr(self.entity, 'vx') or self.entity.vx == 0:
            return
            
        old_x = self.entity.rect.x
        self.entity.rect.x += int(self.entity.vx)
        
        # Check collisions with solids
        for solid in level.solids:
            if self.entity.rect.colliderect(solid):
                if self.entity.vx > 0:
                    # Moving right, hit left side of solid
                    self.entity.rect.right = solid.left
                    self.entity.vx *= -self.bounce_factor
                    # Set wall collision flags for entities that need them
                    if hasattr(self.entity, 'on_right_wall'):
                        self.entity.on_right_wall = True
                else:
                    # Moving left, hit right side of solid
                    self.entity.rect.left = solid.right
                    self.entity.vx *= -self.bounce_factor
                    # Set wall collision flags for entities that need them
                    if hasattr(self.entity, 'on_left_wall'):
                        self.entity.on_left_wall = True
    
    def handle_vertical_movement(self, level):
        """Handle vertical movement and collision"""
        if not hasattr(self.entity, 'vy'):
            return
            
        old_y = self.entity.rect.y
        was_on_ground = getattr(self.entity, 'on_ground', False)
        self.entity.on_ground = False  # Reset ground detection
        
        self.entity.rect.y += int(self.entity.vy)
        
        # Check collisions with solids
        for solid in level.solids:
            if self.entity.rect.colliderect(solid):
                if self.entity.vy > 0:
                    # Moving down, hit top of solid
                    if self.entity.rect.bottom > solid.top and old_y + self.entity.rect.height <= solid.top:
                        self.entity.rect.bottom = solid.top
                        self.entity.vy = 0
                        self.entity.on_ground = True
                elif self.entity.vy < 0:
                    # Moving up, hit bottom of solid
                    if self.entity.rect.top < solid.bottom and old_y >= solid.bottom:
                        self.entity.rect.top = solid.bottom
                        self.entity.vy = 0
    
    def handle_ground_collision(self, level):
        """Check and handle ground collision specifically"""
        was_on_ground = getattr(self.entity, 'on_ground', False)
        self.entity.on_ground = False
        
        # Check if entity is standing on any solid
        for solid in level.solids:
            if self.entity.rect.colliderect(solid):
                if self.entity.rect.bottom > solid.top and self.entity.vy >= 0:
                    self.entity.rect.bottom = solid.top
                    self.entity.vy = 0
                    self.entity.on_ground = True
                    break
    
    def handle_wall_collision(self, level):
        """Check and handle wall collision specifically"""
        # Reset wall flags if they exist
        if hasattr(self.entity, 'on_left_wall'):
            self.entity.on_left_wall = False
        if hasattr(self.entity, 'on_right_wall'):
            self.entity.on_right_wall = False
            
        # Check for wall collisions
        expanded_rect = self.entity.rect.inflate(2, 0)  # Expand horizontally by 1 pixel each side
        for solid in level.solids:
            if expanded_rect.colliderect(solid):
                # Determine which side the wall is on
                if self.entity.rect.centerx < solid.centerx:  # Wall is to the right
                    if abs(self.entity.rect.right - solid.left) <= 2:  # Within 2 pixels
                        if hasattr(self.entity, 'on_right_wall'):
                            self.entity.on_right_wall = True
                else:  # Wall is to the left
                    if abs(self.entity.rect.left - solid.right) <= 2:  # Within 2 pixels
                        if hasattr(self.entity, 'on_left_wall'):
                            self.entity.on_left_wall = True
    
    def apply_friction(self):
        """Apply friction to horizontal movement"""
        if getattr(self.entity, 'on_ground', False) and hasattr(self.entity, 'vx'):
            self.entity.vx *= self.friction
            # Stop very small movement
            if abs(self.entity.vx) < 0.1:
                self.entity.vx = 0
    
    def clamp_to_level_bounds(self, level):
        """Keep entity within level boundaries"""
        level_width_px = getattr(level, "w", 0) * TILE if hasattr(level, "w") else 0
        level_height_px = getattr(level, "h", 0) * TILE if hasattr(level, "h") else 0
        
        # Horizontal bounds
        if level_width_px > 0:
            if self.entity.rect.left < 0:
                self.entity.rect.left = 0
                self.entity.vx = abs(getattr(self.entity, "vx", 0))
            elif self.entity.rect.right > level_width_px:
                self.entity.rect.right = level_width_px
                self.entity.vx = -abs(getattr(self.entity, "vx", 0))
        
        # Vertical bounds
        if self.entity.rect.top < 0:
            self.entity.rect.top = 0
            self.entity.vy = max(0, getattr(self.entity, "vy", 0))
        # Don't clamp bottom - allow falling off screen if that's intended
    
    def update_physics(self, level, gravity_multiplier=1.0, use_tile_collision=False):
        """Complete physics update for one frame"""
        # Apply gravity
        self.apply_gravity(gravity_multiplier)

        # Handle movement and collisions
        if use_tile_collision and hasattr(level, 'grid'):
            self.handle_tile_horizontal_collision(level)
            self.handle_tile_vertical_collision(level)
        else:
            self.handle_horizontal_movement(level)
            self.handle_vertical_movement(level)

        # Apply friction if on ground
        self.apply_friction()

        # Keep in bounds
        self.clamp_to_level_bounds(level)
    
    def update_physics_simple(self, level, gravity_multiplier=1.0):
        """Simplified physics update for entities with custom movement logic"""
        # Apply gravity only
        self.apply_gravity(gravity_multiplier)

        # Handle ground collision
        self.handle_ground_collision(level)

        # Handle wall collision if entity has wall flags
        if hasattr(self.entity, 'on_left_wall') or hasattr(self.entity, 'on_right_wall'):
            self.handle_wall_collision(level)

        # Keep in bounds
        self.clamp_to_level_bounds(level)

    def get_tile_at_pos(self, x: int, y: int, level) -> Optional[int]:
        """Get tile value at pixel position."""
        if hasattr(level, 'grid'):
            tile_x = x // TILE
            tile_y = y // TILE
            if 0 <= tile_y < len(level.grid) and 0 <= tile_x < len(level.grid[0]):
                return level.grid[tile_y][tile_x]
        return None

    def check_tile_collision_horizontal(self, level, new_x: int) -> bool:
        """Check if moving to new_x would cause horizontal collision with tiles."""
        if not hasattr(level, 'grid'):
            # Fall back to solid list for backward compatibility
            temp_rect = self.entity.rect.copy()
            temp_rect.x = new_x
            for solid in level.solids:
                if temp_rect.colliderect(solid):
                    return True
            return False

        # Use new tile collision system
        temp_rect = self.entity.rect.copy()
        temp_rect.x = new_x
        collisions = self.tile_collision.check_tile_collision(temp_rect, level.grid)

        for collision in collisions:
            if collision['collision_type'] in ('full',):
                return True

        return False

    def check_tile_collision_vertical(self, level, new_y: int, vy: float) -> bool:
        """Check if moving to new_y would cause vertical collision with tiles."""
        if not hasattr(level, 'grid'):
            # Fall back to solid list for backward compatibility
            temp_rect = self.entity.rect.copy()
            temp_rect.y = new_y
            for solid in level.solids:
                if temp_rect.colliderect(solid):
                    return True
            return False

        # Use new tile collision system
        temp_rect = self.entity.rect.copy()
        temp_rect.y = new_y
        velocity = pygame.Vector2(0, vy)
        collisions = self.tile_collision.check_tile_collision(temp_rect, level.grid, velocity)

        for collision in collisions:
            collision_type = collision['collision_type']
            # Check based on movement direction and collision type
            if vy > 0 and collision_type in ('full', 'top_only'):
                return True
            elif vy < 0 and collision_type == 'full':
                return True

        return False

    def handle_tile_horizontal_collision(self, level):
        """Handle horizontal collision using new tile system."""
        velocity = pygame.Vector2(self.entity.vx, 0)
        self.entity.rect, self.entity.vx, collisions = self.tile_collision.resolve_collisions(
            self.entity.rect, velocity, level.grid, 1/60
        )

        # Set wall flags
        if hasattr(self.entity, 'on_left_wall'):
            self.entity.on_left_wall = False
        if hasattr(self.entity, 'on_right_wall'):
            self.entity.on_right_wall = False

        for collision in collisions:
            if collision['side'] == 'left' and hasattr(self.entity, 'on_right_wall'):
                self.entity.on_right_wall = True
            elif collision['side'] == 'right' and hasattr(self.entity, 'on_left_wall'):
                self.entity.on_left_wall = True

    def handle_tile_vertical_collision(self, level):
        """Handle vertical collision using new tile system."""
        velocity = pygame.Vector2(0, self.entity.vy)
        old_on_ground = getattr(self.entity, 'on_ground', False)
        self.entity.on_ground = False

        self.entity.rect, self.entity.vy, collisions = self.tile_collision.resolve_collisions(
            self.entity.rect, velocity, level.grid, 1/60
        )

        # Check if landed on ground
        for collision in collisions:
            if collision['side'] == 'top':
                self.entity.on_ground = True
                # Apply tile properties
                tile_data = collision.get('tile_data')
                if tile_data:
                    # Apply friction from tile
                    self.friction = tile_data.physics.friction
                    # Apply damage if tile deals damage
                    if tile_data.get_damage() > 0:
                        if hasattr(self.entity, 'take_damage'):
                            self.entity.take_damage(tile_data.get_damage())

    def get_tile_at_pos(self, x: int, y: int, level) -> Optional[int]:
        """Get tile value at pixel position using new tile system."""
        return self.tile_collision.get_tile_at_pos(x, y, level.grid)
    