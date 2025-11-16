# Universal Sprite & Animation Guide for Enemies & Player

This guide explains how to add sprites and animations to any enemy OR the player character in the game using both the legacy system and the new enhanced AnimationManager.

**📖 For Player-Specific Setup:** See **`docs/PLAYER_ANIMATION_GUIDE.md`** for detailed player animation instructions.

---

## Table of Contents

1. [Quick Start - Legacy System](#quick-start---legacy-system)
2. [Enhanced System - AnimationManager](#enhanced-system---animationmanager)
3. [Asset Organization](#asset-organization)
4. [Step-by-Step Examples](#step-by-step-examples)
5. [Animation States Reference](#animation-states-reference)
6. [Troubleshooting](#troubleshooting)
7. [Player Animation Support](#player-animation-support)

---

## Quick Start - Legacy System

The legacy system is simple and already integrated into the Enemy base class. Use this for basic enemies with idle + attack animations.

### 1. Add Sprites in Enemy `__init__`

```python
class MyEnemy(Enemy):
    def __init__(self, x, ground_y):
        combat_config = {
            'max_hp': 100,
            'money_drop': (20, 40)
        }
        super().__init__(x, ground_y, width=56, height=44, combat_config=combat_config)
        
        # ===== SPRITE SETUP =====
        # Load idle sprite
        self.load_sprite_system(
            idle_path="assets/monster/MyEnemy_Idle.png",
            sprite_size=(96, 128),  # Width, Height
            offset_y=55             # Vertical offset from collision rect
        )
        
        # Load attack animation (optional)
        self.load_attack_animation(
            frame_paths=[
                "assets/monster/atk/MyEnemy_ATK1.png",
                "assets/monster/atk/MyEnemy_ATK2.png",
                "assets/monster/atk/MyEnemy_ATK3.png",
                "assets/monster/atk/MyEnemy_ATK4.png"
            ],
            sprite_size=(96, 128),
            anim_speed=4  # Frames per animation frame
        )
        
        # Load projectile sprite (for ranged enemies)
        self.load_projectile_sprite(
            sprite_path="assets/monster/atk/MyEnemy_Projectile.png",
            sprite_size=(42, 42)
        )
        
        # Initialize projectile tracking
        self.projectile_hitboxes = []
```

### 2. Update Animation in `tick()`

```python
def tick(self, level, player):
    if not self.combat.alive:
        return
    
    self.combat.update()
    self.handle_status_effects()
    
    # Your enemy AI logic here...
    
    # Update facing direction
    self.update_facing_from_player(player)
    
    # Update attack animation if playing
    self.update_attack_animation()
    
    # Clean up dead projectiles
    self.clean_projectile_hitboxes()
    
    # Sync sprite position with collision rect
    self.sync_sprite_position()
```

### 3. Draw Sprites in `draw()`

```python
def draw(self, surf, camera, show_los=False, show_nametags=False):
    if not self.combat.alive:
        return
    
    # Draw vision rays (debug)
    self.draw_debug_vision(surf, camera, show_los)
    
    # Draw sprite with animation
    sprite_drawn = self.draw_sprite_with_animation(surf, camera)
    
    if not sprite_drawn:
        # Fallback to colored rectangle if sprite failed
        base_color = self.get_base_color()
        status_color = self.get_status_effect_color(base_color)
        pygame.draw.rect(surf, status_color, camera.to_screen_rect(self.rect), 
                        border_radius=4)
    
    # Draw projectile sprites
    self.draw_projectile_sprites(surf, camera)
    
    # Draw telegraph indicator
    if self.tele_t > 0:
        from src.core.utils import draw_text
        draw_text(surf, self.tele_text, 
                 camera.to_screen((self.rect.centerx-4, self.rect.top-10)), 
                 (255,200,80), size=18, bold=True)
    
    # Draw nametag and HP bar
    self.draw_nametag(surf, camera, show_nametags)
```

### 4. Trigger Attack Animation

```python
# When enemy attacks, start the animation
if self.action == "attack":
    self.start_attack_animation()  # or: self.play_attack_anim = True
```

### 5. Create Projectiles with Sprites

```python
# When creating a projectile hitbox
hb = pygame.Rect(0, 0, 26, 26)
hb.center = self.rect.center
new_hb = Hitbox(
    hb,
    120,  # lifetime
    4,    # damage
    self,
    dir_vec=(nx, ny),
    vx=nx * 8,
    vy=ny * 8,
    has_sprite=True  # This tells the system a sprite will be drawn separately
)
hitboxes.append(new_hb)
self.projectile_hitboxes.append(new_hb)
```

---

## Enhanced System - AnimationManager

The new AnimationManager supports multiple animation states, priorities, and advanced features. Use this for complex enemies with many animations.

### 1. Import the System

```python
from src.entities.animation_system import (
    AnimationManager, 
    AnimationState,
    create_simple_animation_manager,
    load_numbered_frames
)
```

### 2. Setup in Enemy `__init__`

```python
class AdvancedEnemy(Enemy):
    def __init__(self, x, ground_y):
        super().__init__(x, ground_y, width=56, height=44, combat_config={...})
        
        # ===== ANIMATION MANAGER SETUP =====
        self.anim_manager = AnimationManager(self, default_state=AnimationState.IDLE)
        self.anim_manager.set_sprite_offset_y(55)
        
        # Load idle animation (single frame or multi-frame)
        self.anim_manager.load_single_frame_animation(
            AnimationState.IDLE,
            "assets/monster/AdvancedEnemy_Idle.png",
            sprite_size=(96, 128),
            priority=0
        )
        
        # Load walk animation
        self.anim_manager.load_animation(
            AnimationState.WALK,
            frame_paths=[
                "assets/monster/walk/AdvancedEnemy_Walk1.png",
                "assets/monster/walk/AdvancedEnemy_Walk2.png",
                "assets/monster/walk/AdvancedEnemy_Walk3.png",
                "assets/monster/walk/AdvancedEnemy_Walk4.png"
            ],
            sprite_size=(96, 128),
            frame_duration=6,
            loop=True,
            priority=1
        )
        
        # Load attack animation with auto-return to idle
        self.anim_manager.load_animation(
            AnimationState.ATTACK,
            frame_paths=load_numbered_frames(
                "assets/monster/atk/AdvancedEnemy_ATK", 1, 5, ".png"
            ),
            sprite_size=(96, 128),
            frame_duration=4,
            loop=False,
            priority=10,
            next_state=AnimationState.IDLE  # Return to idle after attack
        )
        
        # Load special skill animation
        self.anim_manager.load_animation(
            AnimationState.SKILL_1,
            frame_paths=load_numbered_frames(
                "assets/monster/skill/AdvancedEnemy_Skill", 1, 6, ".png"
            ),
            sprite_size=(96, 128),
            frame_duration=5,
            loop=False,
            priority=15,
            on_complete_callback=self._on_skill_complete,
            next_state=AnimationState.IDLE
        )
        
        # Load death animation
        self.anim_manager.load_animation(
            AnimationState.DEATH,
            frame_paths=load_numbered_frames(
                "assets/monster/death/AdvancedEnemy_Death", 1, 8, ".png"
            ),
            sprite_size=(96, 128),
            frame_duration=6,
            loop=False,
            priority=100  # Highest priority - nothing interrupts death
        )
```

### 3. Update in `tick()`

```python
def tick(self, level, player):
    if not self.combat.alive:
        if not hasattr(self, '_death_anim_started'):
            self.anim_manager.play(AnimationState.DEATH, force=True)
            self._death_anim_started = True
        self.anim_manager.update()
        return
    
    self.combat.update()
    self.handle_status_effects()
    
    # Update animation based on state
    if self.attacking:
        self.anim_manager.play(AnimationState.ATTACK)
    elif abs(self.vx) > 0.5:
        self.anim_manager.play(AnimationState.WALK)
    else:
        self.anim_manager.play(AnimationState.IDLE)
    
    # Update animation frame
    self.anim_manager.update()
    
    # Rest of tick logic...
```

### 4. Draw in `draw()`

```python
def draw(self, surf, camera, show_los=False, show_nametags=False):
    # Draw debug vision
    self.draw_debug_vision(surf, camera, show_los)
    
    # Draw animation
    sprite_drawn = self.anim_manager.draw(surf, camera, show_invincibility=True)
    
    if not sprite_drawn:
        # Fallback to colored rect
        base_color = self.get_base_color()
        status_color = self.get_status_effect_color(base_color)
        pygame.draw.rect(surf, status_color, camera.to_screen_rect(self.rect))
    
    # Draw nametag
    self.draw_nametag(surf, camera, show_nametags)
```

### 5. Trigger Animations

```python
# In your AI logic
if enemy_should_attack:
    self.anim_manager.play(AnimationState.ATTACK)
    
if enemy_uses_skill:
    self.anim_manager.play(AnimationState.SKILL_1)
    
# Force play (interrupt current animation)
if enemy_gets_hit:
    self.anim_manager.play(AnimationState.HURT, force=True)
```

---

## Asset Organization

### Recommended Directory Structure

```
assets/
└── monster/
    ├── MyEnemy_Idle.png              # Idle sprite
    ├── MyEnemy.png                   # Alternative idle name
    │
    ├── atk/                          # Attack animations
    │   ├── MyEnemy_ATK1.png
    │   ├── MyEnemy_ATK2.png
    │   ├── MyEnemy_ATK3.png
    │   ├── MyEnemy_ATK4.png
    │   └── MyEnemy_Projectile.png    # Projectile sprite
    │
    ├── walk/                         # Walk animations
    │   ├── MyEnemy_Walk1.png
    │   ├── MyEnemy_Walk2.png
    │   ├── MyEnemy_Walk3.png
    │   └── MyEnemy_Walk4.png
    │
    ├── skill/                        # Special skill animations
    │   ├── MyEnemy_Skill1.png
    │   ├── MyEnemy_Skill2.png
    │   └── MyEnemy_Skill3.png
    │
    └── death/                        # Death animations
        ├── MyEnemy_Death1.png
        ├── MyEnemy_Death2.png
        └── MyEnemy_Death3.png
```

### Sprite Size Guidelines

- **Small enemies** (Bug, Bee): 64x64 to 96x96
- **Medium enemies** (Archer, Frog): 96x128
- **Large enemies** (Golem, Boss): 128x160 or larger
- **Projectiles**: 32x32 to 64x64

---

## Step-by-Step Examples

### Example 1: Basic Enemy with Idle Sprite Only

```python
from src.entities.enemy_entities import Enemy

class SimpleSlime(Enemy):
    def __init__(self, x, ground_y):
        combat_config = {'max_hp': 20, 'money_drop': (5, 10)}
        super().__init__(x, ground_y, width=24, height=20, combat_config=combat_config)
        
        # Just load idle sprite
        self.load_sprite_system(
            idle_path="assets/monster/Slime_Idle.png",
            sprite_size=(64, 64),
            offset_y=40
        )
        
        self.type = "Slime"
        self.vx = 1.0
    
    def tick(self, level, player):
        if not self.combat.alive:
            return
        
        self.combat.update()
        
        # Simple movement
        self.rect.x += int(self.vx)
        for s in level.solids:
            if self.rect.colliderect(s):
                self.vx *= -1
        
        # Update sprite position
        self.sync_sprite_position()
    
    def draw(self, surf, camera, show_los=False, show_nametags=False):
        if not self.combat.alive:
            return
        
        # Draw sprite or fallback to rect
        sprite_drawn = self.draw_sprite_with_animation(surf, camera)
        if not sprite_drawn:
            pygame.draw.rect(surf, (100, 200, 100), 
                           camera.to_screen_rect(self.rect))
        
        self.draw_nametag(surf, camera, show_nametags)
    
    def get_base_color(self):
        return (100, 200, 100)
```

### Example 2: Melee Enemy with Attack Animation

```python
class Warrior(Enemy):
    def __init__(self, x, ground_y):
        combat_config = {'max_hp': 80, 'money_drop': (15, 30)}
        super().__init__(x, ground_y, width=48, height=56, combat_config=combat_config)
        
        # Load idle sprite
        self.load_sprite_system(
            idle_path="assets/monster/Warrior_Idle.png",
            sprite_size=(96, 128),
            offset_y=55
        )
        
        # Load attack animation
        self.load_attack_animation(
            frame_paths=[
                "assets/monster/atk/Warrior_ATK1.png",
                "assets/monster/atk/Warrior_ATK2.png",
                "assets/monster/atk/Warrior_ATK3.png"
            ],
            sprite_size=(96, 128),
            anim_speed=5
        )
        
        self.type = "Warrior"
        self.attack_cooldown = 0
    
    def tick(self, level, player):
        if not self.combat.alive:
            return
        
        self.combat.update()
        
        # Attack logic
        if self.attack_cooldown > 0:
            self.attack_cooldown -= 1
        
        # Check if player in range
        dist = abs(player.rect.centerx - self.rect.centerx)
        if dist < 100 and self.attack_cooldown == 0:
            self.start_attack_animation()
            self.attack_cooldown = 60
            # Create melee hitbox
            self._create_melee_attack()
        
        # Update animation
        self.update_facing_from_player(player)
        self.update_attack_animation()
        self.sync_sprite_position()
    
    def _create_melee_attack(self):
        hb_rect = pygame.Rect(0, 0, 60, 40)
        hb_rect.center = (
            self.rect.centerx + (40 * self.facing),
            self.rect.centery
        )
        from src.entities.entity_common import Hitbox, hitboxes
        hitboxes.append(Hitbox(hb_rect, 10, 8, self))
    
    def draw(self, surf, camera, show_los=False, show_nametags=False):
        if not self.combat.alive:
            return
        
        sprite_drawn = self.draw_sprite_with_animation(surf, camera)
        if not sprite_drawn:
            pygame.draw.rect(surf, (180, 80, 60), 
                           camera.to_screen_rect(self.rect))
        
        self.draw_nametag(surf, camera, show_nametags)
    
    def get_base_color(self):
        return (180, 80, 60)
```

### Example 3: Ranged Enemy with Projectiles (Like Golem)

```python
class Mage(Enemy):
    def __init__(self, x, ground_y):
        combat_config = {'max_hp': 60, 'money_drop': (20, 40)}
        super().__init__(x, ground_y, width=40, height=48, combat_config=combat_config)
        
        # Load sprites
        self.load_sprite_system(
            idle_path="assets/monster/Mage_Idle.png",
            sprite_size=(96, 128),
            offset_y=55
        )
        
        self.load_attack_animation(
            frame_paths=[
                "assets/monster/atk/Mage_Cast1.png",
                "assets/monster/atk/Mage_Cast2.png",
                "assets/monster/atk/Mage_Cast3.png"
            ],
            sprite_size=(96, 128),
            anim_speed=6
        )
        
        self.load_projectile_sprite(
            sprite_path="assets/monster/atk/Mage_Fireball.png",
            sprite_size=(32, 32)
        )
        
        self.projectile_hitboxes = []
        self.type = "Mage"
        self.cast_cooldown = 0
        self.telegraph_timer = 0
        self.tele_text = ""
    
    def tick(self, level, player):
        if not self.combat.alive:
            return
        
        self.combat.update()
        
        # Telegraph countdown
        if self.telegraph_timer > 0:
            self.telegraph_timer -= 1
            if self.telegraph_timer == 0:
                self._shoot_projectile(player)
        
        # Cast logic
        if self.cast_cooldown > 0:
            self.cast_cooldown -= 1
        
        # Check if should cast
        dist = ((player.rect.centerx - self.rect.centerx)**2 + 
                (player.rect.centery - self.rect.centery)**2)**0.5
        
        if dist < 400 and self.cast_cooldown == 0:
            self.start_attack_animation()
            self.telegraph_timer = 20
            self.tele_text = "!!"
            self.cast_cooldown = 90
        
        # Update
        self.update_facing_from_player(player)
        self.update_attack_animation()
        self.clean_projectile_hitboxes()
        self.sync_sprite_position()
    
    def _shoot_projectile(self, player):
        # Calculate direction to player
        dx = player.rect.centerx - self.rect.centerx
        dy = player.rect.centery - self.rect.centery
        dist = max(1.0, (dx*dx + dy*dy)**0.5)
        nx, ny = dx/dist, dy/dist
        
        # Create projectile hitbox
        hb = pygame.Rect(0, 0, 28, 28)
        hb.center = self.rect.center
        
        from src.entities.entity_common import Hitbox, hitboxes
        new_hb = Hitbox(
            hb,
            90,  # lifetime
            6,   # damage
            self,
            dir_vec=(nx, ny),
            vx=nx * 6,
            vy=ny * 6,
            has_sprite=True  # Important: tells system sprite will be drawn
        )
        hitboxes.append(new_hb)
        self.projectile_hitboxes.append(new_hb)
        
        self.tele_text = ""
    
    def draw(self, surf, camera, show_los=False, show_nametags=False):
        if not self.combat.alive:
            return
        
        sprite_drawn = self.draw_sprite_with_animation(surf, camera)
        if not sprite_drawn:
            pygame.draw.rect(surf, (120, 100, 200), 
                           camera.to_screen_rect(self.rect))
        
        # Draw projectiles
        self.draw_projectile_sprites(surf, camera)
        
        # Draw telegraph
        if self.telegraph_timer > 0:
            from src.core.utils import draw_text
            draw_text(surf, self.tele_text, 
                     camera.to_screen((self.rect.centerx-4, self.rect.top-10)),
                     (255, 200, 80), size=18, bold=True)
        
        self.draw_nametag(surf, camera, show_nametags)
    
    def get_base_color(self):
        return (120, 100, 200)
```

### Example 4: Advanced Enemy with AnimationManager

```python
from src.entities.animation_system import (
    AnimationManager, AnimationState, load_numbered_frames
)

class AdvancedKnight(Enemy):
    def __init__(self, x, ground_y):
        combat_config = {'max_hp': 150, 'money_drop': (50, 100)}
        super().__init__(x, ground_y, width=56, height=64, combat_config=combat_config)
        
        # Setup animation manager
        self.anim_manager = AnimationManager(self, default_state=AnimationState.IDLE)
        self.anim_manager.set_sprite_offset_y(60)
        
        # Load all animations
        self.anim_manager.load_single_frame_animation(
            AnimationState.IDLE,
            "assets/monster/Knight_Idle.png",
            sprite_size=(128, 160),
            priority=0
        )
        
        self.anim_manager.load_animation(
            AnimationState.WALK,
            load_numbered_frames("assets/monster/walk/Knight_Walk", 1, 6),
            sprite_size=(128, 160),
            frame_duration=5,
            loop=True,
            priority=1
        )
        
        self.anim_manager.load_animation(
            AnimationState.ATTACK,
            load_numbered_frames("assets/monster/atk/Knight_ATK", 1, 5),
            sprite_size=(128, 160),
            frame_duration=4,
            loop=False,
            priority=10,
            next_state=AnimationState.IDLE
        )
        
        self.anim_manager.load_animation(
            AnimationState.SKILL_1,
            load_numbered_frames("assets/monster/skill/Knight_Skill", 1, 8),
            sprite_size=(128, 160),
            frame_duration=5,
            loop=False,
            priority=15,
            on_complete_callback=self._on_skill_complete,
            next_state=AnimationState.IDLE
        )
        
        self.type = "Knight"
        self.state = "idle"
    
    def tick(self, level, player):
        if not self.combat.alive:
            return
        
        self.combat.update()
        
        # State machine
        if self.state == "idle":
            self.anim_manager.play(AnimationState.IDLE)
            # Check for player proximity
            if self._player_in_range(player, 300):
                self.state = "walking"
        
        elif self.state == "walking":
            self.anim_manager.play(AnimationState.WALK)
            self._move_toward_player(player, level)
            
            if self._player_in_range(player, 80):
                self.state = "attacking"
        
        elif self.state == "attacking":
            self.anim_manager.play(AnimationState.ATTACK)
            if self.anim_manager.is_animation_complete():
                self._create_melee_attack()
                self.state = "walking"
        
        # Update animation
        self.anim_manager.update()
    
    def _player_in_range(self, player, range_val):
        dist = ((player.rect.centerx - self.rect.centerx)**2 + 
                (player.rect.centery - self.rect.centery)**2)**0.5
        return dist < range_val
    
    def _move_toward_player(self, player, level):
        direction = 1 if player.rect.centerx > self.rect.centerx else -1
        self.facing = direction
        self.vx = direction * 2.0
        self.rect.x += int(self.vx)
        
        # Collision
        for s in level.solids:
            if self.rect.colliderect(s):
                if self.vx > 0:
                    self.rect.right = s.left
                else:
                    self.rect.left = s.right
                self.vx = 0
    
    def _create_melee_attack(self):
        hb_rect = pygame.Rect(0, 0, 70, 50)
        hb_rect.center = (
            self.rect.centerx + (50 * self.facing),
            self.rect.centery
        )
        from src.entities.entity_common import Hitbox, hitboxes
        hitboxes.append(Hitbox(hb_rect, 12, 12, self))
    
    def _on_skill_complete(self):
        print("[Knight] Skill complete!")
        self.state = "walking"
    
    def draw(self, surf, camera, show_los=False, show_nametags=False):
        if not self.combat.alive:
            return
        
        sprite_drawn = self.anim_manager.draw(surf, camera)
        if not sprite_drawn:
            pygame.draw.rect(surf, (200, 180, 140), 
                           camera.to_screen_rect(self.rect))
        
        self.draw_nametag(surf, camera, show_nametags)
    
    def get_base_color(self):
        return (200, 180, 140)
```

---

## Animation States Reference

### Available States (AnimationState enum)

| State | Use Case | Typical Loop | Priority |
|-------|----------|--------------|----------|
| `IDLE` | Standing still | True | 0 |
| `WALK` | Walking/moving | True | 1 |
| `RUN` | Running fast | True | 2 |
| `ATTACK` | Basic attack | False | 10 |
| `SKILL_1` | Special skill 1 | False | 15 |
| `SKILL_2` | Special skill 2 | False | 15 |
| `SKILL_3` | Special skill 3 | False | 15 |
| `HURT` | Taking damage | False | 20 |
| `DEATH` | Dying | False | 100 |
| `TELEGRAPH` | Attack warning | True | 5 |
| `DASH` | Dashing | False | 12 |
| `JUMP` | Jumping | False | 3 |
| `FALL` | Falling | True | 2 |

### Priority System

- Higher priority animations interrupt lower ones
- Use `force=True` to override priority
- Death animation should have highest priority (100)
- Attack/skill animations typically 10-20
- Movement animations typically 1-5
- Idle should be lowest (0)

---

## Troubleshooting

### Sprite Not Showing

**Problem**: Enemy shows as colored rectangle instead of sprite

**Solutions**:
1. Check file path is correct
2. Ensure sprite file exists in `assets/monster/`
3. Check console for "[ERROR]" messages
4. Verify sprite size is reasonable
5. Make sure `draw_sprite_with_animation()` is called in `draw()`

### Animation Not Playing

**Problem**: Sprite shows but doesn't animate

**Solutions**:
1. Verify `update_attack_animation()` is called in `tick()`
2. Check `start_attack_animation()` is called when attacking
3. Ensure `atk_frames` list is not empty
4. Verify `anim_speed` is reasonable (4-8 is typical)

### Projectile Sprite Not Showing

**Problem**: Projectile hitbox visible but sprite not showing

**Solutions**:
1. Check `has_sprite=True` is set when creating hitbox
2. Verify projectile added to `self.projectile_hitboxes`
3. Ensure `draw_projectile_sprites()` is called in `draw()`
4. Check projectile sprite loaded correctly
5. Press F3 to see hitbox outline for debugging

### Sprite Positioned Incorrectly

**Problem**: Sprite appears offset from where it should be

**Solutions**:
1. Adjust `offset_y` parameter in `load_sprite_system()`
2. Call `sync_sprite_position()` in `tick()` after movement
3. Check sprite anchor point (should be midbottom)
4. Verify collision rect size matches sprite conceptually

### Animation Stuck on One Frame

**Problem**: Animation doesn't progress through frames

**Solutions**:
1. Ensure `self.play_attack_anim = True` is set
2. Check `anim_speed` is not too large
3. Verify `update_attack_animation()` is called every frame
4. Check if animation already completed (non-looping)

### Sprite Flipped Wrong Direction

**Problem**: Sprite faces wrong way

**Solutions**:
1. Update `self.facing` based on movement direction
2. Call `update_facing_from_player(player)` in `tick()`
3. Check facing is set to 1 (right) or -1 (left)
4. Sprite flip happens automatically in `draw_sprite_with_animation()`

### F3 Hitbox Debug Not Working

**Problem**: Pressing F3 doesn't show hitboxes

**Solutions**:
1. Ensure game is running (not paused)
2. Check `main.py` has F3 handler implemented
3. Verify `debug_show_hitboxes` flag exists in game class
4. Make sure hitboxes are being created and added to `hitboxes` list

---

## Best Practices

1. **Always provide fallback rendering**: If sprite fails to load, draw colored rect
2. **Use consistent sprite sizes** within enemy type categories
3. **Keep animation speeds consistent**: 4-6 frames per sprite frame is standard
4. **Test with F3 hitbox debug** to ensure sprites align with collision
5. **Handle errors gracefully**: Wrap sprite loading in try/except
6. **Use descriptive file names**: `EnemyName_AnimationType_FrameNumber.png`
7. **Sync sprite position** after any movement in `tick()`
8. **Clean up projectile hitboxes** to prevent memory leaks

---

## Quick Reference - Method Cheat Sheet

### Legacy System Methods

| Method | Where to Call | Purpose |
|--------|---------------|---------|
| `load_sprite_system()` | `__init__` | Load idle sprite |
| `load_attack_animation()` | `__init__` | Load attack frames |
| `load_projectile_sprite()` | `__init__` | Load projectile sprite |
| `start_attack_animation()` | `tick()` | Trigger attack animation |
| `update_attack_animation()` | `tick()` | Update animation frame |
| `update_facing_from_player()` | `tick()` | Update facing direction |
| `sync_sprite_position()` | `tick()` | Sync sprite to rect |
| `clean_projectile_hitboxes()` | `tick()` | Remove dead projectiles |
| `draw_sprite_with_animation()` | `draw()` | Draw sprite |
| `draw_projectile_sprites()` | `draw()` | Draw projectile sprites |

### AnimationManager Methods

| Method | Where to Call | Purpose |
|--------|---------------|---------|
| `AnimationManager()` | `__init__` | Create manager |
| `load_animation()` | `__init__` | Load multi-frame animation |
| `load_single_frame_animation()` | `__init__` | Load static sprite |
| `play()` | `tick()` | Request animation |
| `update()` | `tick()` | Update frame |
| `draw()` | `draw()` | Render sprite |
| `is_animation_complete()` | `tick()` | Check if done |
| `set_sprite_offset_y()` | `__init__` | Set vertical offset |

---

## Additional Resources

- **Example Enemies**: See `src/entities/enemy_entities.py`
  - `Golem` class (line 1497) - Full sprite system example
  - `Bug` class (line 839) - Simple enemy example
  
- **Animation System**: `src/entities/animation_system.py`
  - Full AnimationManager implementation
  - Helper functions and examples

- **Entity Common**: `src/entities/entity_common.py`
  - Hitbox class and drawing logic
  
- **Developer Cheat Sheet**: `docs/developer_cheat(must read).txt`
  - General development guidelines

---

**Remember**: Start simple with idle sprites, then add attack animations, then move to the full AnimationManager for complex enemies!

---

## Player Animation Support

**✅ Yes! The AnimationManager works for the Player class too!**

The AnimationManager is universal and supports:
- Player character sprites (Knight, Ranger, Wizard, Assassin)
- All player states (idle, walk, jump, attack, skills, dash, hurt, death)
- Class-specific animations
- Combo systems
- Skill animations (Q, E, R)

**📖 See Full Guide:** `docs/PLAYER_ANIMATION_GUIDE.md` for complete player animation setup instructions.

### Quick Player Setup

```python
# In Player.__init__:
from src.entities.animation_system import AnimationManager, AnimationState

self.anim_manager = AnimationManager(self, default_state=AnimationState.IDLE)
self._load_player_sprites(cls)

# In Player.tick():
self._update_animation_state()
self.anim_manager.update()

# In Player.draw():
self.anim_manager.draw(surf, camera)
```

The same system, same API, works for both enemies and players!
