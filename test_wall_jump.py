"""
Test script for the new physics-based wall jump mechanics
Run this to test and refine the wall jump system
"""

import pygame
import sys
from player_entity import Player
from config import FPS, WIDTH, HEIGHT, BG, WHITE, TILE

class TestLevel:
    """Test level with walls for wall jump testing"""
    def __init__(self):
        self.solids = []
        self.enemies = []
        self.doors = []
        
        # Create a test environment with walls for wall jumping
        # Ground
        self.solids.append(pygame.Rect(0, HEIGHT - 60, WIDTH, 60))
        
        # Left wall column
        self.solids.append(pygame.Rect(100, HEIGHT - 300, 40, 240))
        
        # Right wall column  
        self.solids.append(pygame.Rect(WIDTH - 140, HEIGHT - 300, 40, 240))
        
        # Middle platforms for vertical traversal testing
        self.solids.append(pygame.Rect(200, HEIGHT - 200, 120, 20))
        self.solids.append(pygame.Rect(WIDTH - 320, HEIGHT - 200, 120, 20))
        
        # Higher platforms
        self.solids.append(pygame.Rect(250, HEIGHT - 350, 100, 20))
        self.solids.append(pygame.Rect(WIDTH - 350, HEIGHT - 350, 100, 20))
        
        # Top platform
        self.solids.append(pygame.Rect(WIDTH//2 - 80, HEIGHT - 450, 160, 20))

class MockCamera:
    """Mock camera for testing"""
    def __init__(self):
        self.x = 0
        self.y = 0
    
    def update(self, target_rect):
        self.x = target_rect.x - WIDTH // 2
        self.y = target_rect.y - HEIGHT // 2
    
    def to_screen(self, pos):
        return (pos[0] - self.x, pos[1] - self.y)
    
    def to_screen_rect(self, rect):
        return pygame.Rect(rect.x - self.x, rect.y - self.y, rect.width, rect.height)

def test_wall_jump():
    """Test the wall jump mechanics"""
    pygame.init()
    screen = pygame.display.set_mode((WIDTH, HEIGHT))
    pygame.display.set_caption("Wall Jump Test - Touch wall + Space to jump")
    clock = pygame.time.Clock()
    font = pygame.font.Font(None, 24)
    
    # Create test environment
    level = TestLevel()
    player = Player(WIDTH // 2, HEIGHT - 100)
    camera = MockCamera()
    
    running = True
    
    print("Wall Jump Test")
    print("Controls:")
    print("A/D: Move left/right")
    print("Space/K: Jump")
    print("Shift/J: Dash")
    print("ESC: Exit")
    print("\nWall Jump Mechanics:")
    print("- Touch a wall while in mid-air to slide")
    print("- Press Space while touching wall to wall jump")
    print("- Chain wall jumps between walls for vertical traversal")
    print("- Immediate control like Super Meat Boy")
    
    while running:
        dt = clock.tick(FPS) / 1000.0
        
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    running = False
                elif event.key == pygame.K_r:
                    # Reset player position
                    player.rect.x = WIDTH // 2
                    player.rect.y = HEIGHT - 100
                    player.vx = 0
                    player.vy = 0
        
        # Update player
        player.input(level, camera)
        player.physics(level)
        camera.update(player.rect)
        
        # Draw everything
        screen.fill(BG)
        
        # Draw level solids
        for solid in level.solids:
            screen_solid = camera.to_screen_rect(solid)
            pygame.draw.rect(screen, (100, 100, 100), screen_solid)
            # Draw wall indicators
            if solid.width < solid.height:  # It's a wall
                pygame.draw.rect(screen, (150, 150, 200), screen_solid, 2)
        
        # Draw player
        player.draw(screen, camera)
        
        # Draw instructions and status
        instructions = [
            "A/D: Move | Space: Jump | Shift: Dash | R: Reset | ESC: Exit",
            f"Wall Sliding: {getattr(player, 'sliding_wall', 0) != 0 and not player.on_ground}",
            f"Sliding Wall: {getattr(player, 'sliding_wall', 0)}",
            f"Wall Jump Timer: {getattr(player, 'wall_jump_timer', 0)}",
            f"Position: ({player.rect.x}, {player.rect.y})",
            f"Velocity: ({player.vx:.1f}, {player.vy:.1f})"
        ]
        
        for i, instruction in enumerate(instructions):
            text = font.render(instruction, True, WHITE)
            screen.blit(text, (10, 10 + i * 25))
        
        # Draw wall jump tips
        if getattr(player, 'sliding_wall', 0) != 0 and not player.on_ground:
            tip_text = font.render("WALL SLIDE! Press Space to wall jump!", True, (100, 255, 100))
            screen.blit(tip_text, (WIDTH//2 - 150, 50))
        
        pygame.display.flip()
    
    pygame.quit()
    sys.exit()

if __name__ == "__main__":
    test_wall_jump()