"""
Example: How to implement a 3-state charge attack system
using the Ranger bow attack as a template.

This example shows how to adapt the Ranger's CHARGE → CHARGED → SHOOT system
for a hypothetical "Pyromancer" character with a fireball charge attack.
"""

from src.entities.animation_system import AnimationManager, AnimationState
import pygame

class PyromancerExample:
    """
    Example character that uses a 3-state charge attack system
    similar to the Ranger's bow attack.
    """
    
    def __init__(self, x, y):
        self.rect = pygame.Rect(x, y, 24, 32)
        self.facing = 1
        
        # === CHARGE ATTACK STATE VARIABLES ===
        # These track the current state of the charge attack
        self.charging = False  # Is player currently charging?
        self.charge_time = 0   # How long have we been charging?
        self.charge_threshold = 30  # Frames needed for full charge (0.5 seconds at 60 FPS)
        self.attack_cd = 0     # Attack cooldown timer
        
        # Previous input state for edge detection
        self._prev_attack_key = False
        
        # Setup animations
        self.anim_manager = AnimationManager(self, default_state=AnimationState.IDLE)
        self._load_pyromancer_animations()
    
    def _load_pyromancer_animations(self):
        """
        Load animations for Pyromancer.
        Uses the same 3-state pattern as Ranger: CHARGE → CHARGED → SHOOT
        """
        sprite_size = (48, 64)
        
        # Basic movement animations...
        self.anim_manager.load_animation(
            AnimationState.IDLE,
            ["assets/pyromancer/idle_1.png", "assets/pyromancer/idle_2.png"],
            sprite_size=sprite_size,
            frame_duration=10,
            loop=True,
            priority=0
        )
        
        # === 3-STATE FIREBALL CHARGE SYSTEM ===
        
        # CHARGE - Channeling fireball (hands glowing, progressive buildup)
        # This plays while the player holds the attack button
        self.anim_manager.load_animation(
            AnimationState.CHARGE,
            [
                "assets/pyromancer/charge_1.png",  # Hands starting to glow
                "assets/pyromancer/charge_2.png",  # Flames appearing
                "assets/pyromancer/charge_3.png",  # Fireball forming
                "assets/pyromancer/charge_4.png",  # Fireball getting larger
            ],
            sprite_size=sprite_size,
            frame_duration=6,  # 6 frames per sprite = 24 frames total
            loop=False,  # Don't loop - transition to CHARGED
            priority=4,  # High priority to override movement
            next_state=AnimationState.CHARGED  # Auto-transition when complete
        )
        
        # CHARGED - Holding fireball at full power (looping hold pose)
        # This single frame loops while waiting for player to release
        self.anim_manager.load_animation(
            AnimationState.CHARGED,
            ["assets/pyromancer/charged_hold.png"],  # Large fireball held in hands
            sprite_size=sprite_size,
            frame_duration=1,
            loop=True,  # Loop indefinitely while holding
            priority=4
        )
        
        # SHOOT - Releasing fireball (throw animation)
        # Plays when attack is released, spawns the projectile
        self.anim_manager.load_animation(
            AnimationState.SHOOT,
            [
                "assets/pyromancer/cast_1.png",  # Throwing motion start
                "assets/pyromancer/cast_2.png",  # Mid-throw
                "assets/pyromancer/cast_3.png",  # Follow-through
            ],
            sprite_size=sprite_size,
            frame_duration=3,  # 3 frames per sprite = 9 frames total
            loop=False,  # Don't loop
            priority=4,
            next_state=AnimationState.IDLE  # Return to idle after casting
        )
    
    def _update_pyromancer_animations(self):
        """
        Update animation state machine for Pyromancer.
        Follows the same priority structure as Ranger.
        """
        if not self.anim_manager:
            return
        
        current = self.anim_manager.current_state
        
        # Priority 1: SHOOT (must complete without interruption)
        if current == AnimationState.SHOOT and self.anim_manager.is_playing:
            return
        
        # Priority 2: CHARGE/CHARGED (3-state charge system)
        if self.charging:
            # Check if we've reached full charge
            if self.charge_time >= self.charge_threshold:
                # Fully charged - hold the CHARGED animation
                if current != AnimationState.CHARGED:
                    self.anim_manager.play(AnimationState.CHARGED, force=True)
            else:
                # Still charging - play CHARGE animation
                if current != AnimationState.CHARGE:
                    self.anim_manager.play(AnimationState.CHARGE, force=True)
            return
        
        # Priority 3: Movement animations (RUN, IDLE, etc.)
        # ... (similar to Ranger's movement logic)
        
        # Default fallback
        if current != AnimationState.IDLE:
            self.anim_manager.play(AnimationState.IDLE, force=True)
    
    def input(self, keys):
        """
        Handle input for charge attack system.
        Pattern matches Ranger's attack handling.
        """
        # Get current attack key state (e.g., left mouse button or 'F' key)
        attack_key = keys[pygame.K_f]  # Or pygame.mouse.get_pressed()[0]
        
        # Only allow attack if cooldown is finished
        if self.attack_cd == 0:
            # Start charging on button press (edge detection)
            if attack_key and not self._prev_attack_key:
                self.charging = True
                self.charge_time = 0
                print("[Pyromancer] Started charging fireball!")
            
            # Increment charge timer while holding button
            if self.charging and attack_key:
                self.charge_time += 1
                
                # Optional: Visual/audio feedback when fully charged
                if self.charge_time == self.charge_threshold:
                    print("[Pyromancer] Fireball fully charged!")
            
            # Fire spell on button release
            if self.charging and not attack_key and self._prev_attack_key:
                charged = self.charge_time >= self.charge_threshold
                self.fire_fireball(charged)
                self.charging = False
                self.attack_cd = 60  # 1 second cooldown at 60 FPS
        
        # Update previous key state for edge detection
        self._prev_attack_key = attack_key
    
    def fire_fireball(self, is_charged):
        """
        Fire a fireball projectile.
        Called when attack button is released.
        """
        # Trigger SHOOT animation
        if self.anim_manager:
            self.anim_manager.play(AnimationState.SHOOT)
        
        # Calculate damage based on charge level
        if is_charged:
            damage = 15  # Full damage for charged shot
            speed = 12
            size = 20    # Larger projectile
            print("[Pyromancer] Fired CHARGED fireball!")
        else:
            damage = 5   # Reduced damage for quick shot
            speed = 8
            size = 12    # Smaller projectile
            print("[Pyromancer] Fired quick fireball!")
        
        # Spawn fireball projectile...
        # (projectile spawning code here)
    
    def tick(self):
        """Update timers and animations every frame."""
        # Decrement cooldowns
        if self.attack_cd > 0:
            self.attack_cd -= 1
        
        # Update animation state machine
        self._update_pyromancer_animations()
        
        # Update animation manager
        if self.anim_manager:
            self.anim_manager.update()


# ============================================================================
# Comparison: Ranger vs Pyromancer
# ============================================================================

"""
RANGER BOW ATTACK:
------------------
State Variables:
- self.charging (bool)
- self.charge_time (int)
- self.charge_threshold (int) = 30 frames
- self._prev_lmb (bool)

Animations:
- CHARGE: 4 frames × 5 duration = 20 frames (bow draw)
- CHARGED: 1 frame looping (hold at full draw)
- SHOOT: 2 frames × 4 duration = 8 frames (arrow release)

Input:
- Left Mouse Button (hold to charge, release to shoot)

Projectile:
- Arrow with pierce capability when charged


PYROMANCER FIREBALL ATTACK:
----------------------------
State Variables:
- self.charging (bool)
- self.charge_time (int)
- self.charge_threshold (int) = 30 frames
- self._prev_attack_key (bool)

Animations:
- CHARGE: 4 frames × 6 duration = 24 frames (fireball channeling)
- CHARGED: 1 frame looping (hold charged fireball)
- SHOOT: 3 frames × 3 duration = 9 frames (fireball cast)

Input:
- 'F' key or Left Mouse Button (hold to charge, release to cast)

Projectile:
- Fireball with AOE explosion when charged


SHARED PATTERN:
---------------
1. Press attack → charging = True, charge_time = 0
2. Hold attack → charge_time increments
3. charge_time >= threshold → transition CHARGE → CHARGED
4. Release attack → fire_projectile(charged), charging = False
5. Play SHOOT animation → auto-transition to IDLE
"""


# ============================================================================
# Usage Example
# ============================================================================

def example_usage():
    """Example of using the Pyromancer in a game loop."""
    # Create character
    pyro = PyromancerExample(100, 100)
    
    # Game loop (simplified)
    clock = pygame.time.Clock()
    running = True
    
    while running:
        # Handle events
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
        
        # Get input
        keys = pygame.key.get_pressed()
        pyro.input(keys)
        
        # Update
        pyro.tick()
        
        # Draw (not shown in example)
        # pyro.anim_manager.draw(screen, camera)
        
        clock.tick(60)


# ============================================================================
# Key Takeaways
# ============================================================================

"""
To adapt this system for ANY charge-based attack:

1. **Add state variables:**
   - self.charging (bool)
   - self.charge_time (int)
   - self.charge_threshold (int)
   - self._prev_[input]_key (bool)

2. **Load 3 animations:**
   - CHARGE (progressive buildup, loop=False, next_state=CHARGED)
   - CHARGED (hold pose, loop=True)
   - SHOOT (release animation, loop=False, next_state=IDLE)

3. **Update input handling:**
   - Press: charging = True, charge_time = 0
   - Hold: charge_time += 1
   - Release: fire_attack(charged), charging = False

4. **Update animation state machine:**
   - Priority 1: SHOOT (must complete)
   - Priority 2: CHARGE/CHARGED (based on charge_time)
   - Priority 3+: Movement animations

5. **Trigger SHOOT animation in fire_attack():**
   - self.anim_manager.play(AnimationState.SHOOT)

That's it! The animation system handles all transitions automatically.
"""
