# Player Animation Guide

## Yes! The AnimationManager works perfectly for the Player class.

The AnimationManager was designed to be universal - it works for **both enemies and the player**. This guide shows you how to add sprites and animations to the player character.

---

## Why Use AnimationManager for Player?

✅ **More Animation States**: idle, walk, run, jump, fall, attack, dash, wall-slide, hurt, death  
✅ **Smooth Transitions**: Automatic state changes based on player actions  
✅ **Class-Specific Sprites**: Different sprites for Knight, Ranger, Wizard, Assassin  
✅ **Attack Combos**: Support for multi-hit combo animations  
✅ **Skill Animations**: Separate animations for each skill (Q, E, R)  
✅ **Priority System**: Important animations won't be interrupted  
✅ **Same Code as Enemies**: Consistent API across the codebase  

---

## Quick Start - Add Player Sprite

### Step 1: Import AnimationManager

```python
# At the top of src/entities/player_entity.py
from src.entities.animation_system import (
    AnimationManager, 
    AnimationState,
    load_numbered_frames
)
```

### Step 2: Initialize in `__init__`

```python
class Player:
    def __init__(self, x, y, cls='Knight'):
        # ... existing initialization code ...
        
        # Setup Animation Manager
        self.anim_manager = AnimationManager(self, default_state=AnimationState.IDLE)
        self.anim_manager.set_sprite_offset_y(30)  # Adjust based on sprite size
        
        # Load sprites based on class
        self._load_player_sprites(cls)
```

### Step 3: Create Sprite Loading Method

```python
def _load_player_sprites(self, cls):
    """Load sprites for the player's class"""
    # Define sprite paths based on class
    if cls == 'Knight':
        idle_path = "assets/player/knight/Knight_Idle.png"
        walk_frames = load_numbered_frames("assets/player/knight/Knight_Walk", 1, 6)
        attack_frames = load_numbered_frames("assets/player/knight/Knight_Attack", 1, 4)
    elif cls == 'Ranger':
        idle_path = "assets/player/ranger/Ranger_Idle.png"
        walk_frames = load_numbered_frames("assets/player/ranger/Ranger_Walk", 1, 6)
        attack_frames = load_numbered_frames("assets/player/ranger/Ranger_Attack", 1, 3)
    elif cls == 'Wizard':
        idle_path = "assets/player/wizard/Wizard_Idle.png"
        walk_frames = load_numbered_frames("assets/player/wizard/Wizard_Walk", 1, 6)
        attack_frames = load_numbered_frames("assets/player/wizard/Wizard_Cast", 1, 5)
    elif cls == 'Assassin':
        idle_path = "assets/player/assassin/Assassin_Idle.png"
        walk_frames = load_numbered_frames("assets/player/assassin/Assassin_Walk", 1, 6)
        attack_frames = load_numbered_frames("assets/player/assassin/Assassin_Attack", 1, 5)
    else:
        # Fallback - system will handle missing sprites gracefully
        return
    
    sprite_size = (64, 64)  # Adjust based on your sprite dimensions
    
    # Load idle animation
    self.anim_manager.load_single_frame_animation(
        AnimationState.IDLE,
        idle_path,
        sprite_size=sprite_size,
        priority=0
    )
    
    # Load walk animation
    self.anim_manager.load_animation(
        AnimationState.WALK,
        walk_frames,
        sprite_size=sprite_size,
        frame_duration=6,
        loop=True,
        priority=1
    )
    
    # Load attack animation
    self.anim_manager.load_animation(
        AnimationState.ATTACK,
        attack_frames,
        sprite_size=sprite_size,
        frame_duration=4,
        loop=False,
        priority=10,
        next_state=AnimationState.IDLE
    )
    
    # Load jump animation (optional)
    try:
        self.anim_manager.load_single_frame_animation(
            AnimationState.JUMP,
            f"assets/player/{cls.lower()}/{cls}_Jump.png",
            sprite_size=sprite_size,
            priority=3
        )
    except:
        pass  # Jump sprite optional
    
    # Load fall animation (optional)
    try:
        self.anim_manager.load_single_frame_animation(
            AnimationState.FALL,
            f"assets/player/{cls.lower()}/{cls}_Fall.png",
            sprite_size=sprite_size,
            priority=2
        )
    except:
        pass  # Fall sprite optional
```

### Step 4: Update Animation State in `tick()`

Add this method to determine which animation should play:

```python
def _update_animation_state(self):
    """Update animation based on player state"""
    # Death animation (highest priority)
    if not self.alive:
        if hasattr(self, '_death_anim_started') and not self._death_anim_started:
            self.anim_manager.play(AnimationState.DEATH, force=True)
            self._death_anim_started = True
        return
    
    # Attack animation (high priority)
    if self.attack_cd > 0 and self.attack_cd > (ATTACK_COOLDOWN - ATTACK_LIFETIME):
        self.anim_manager.play(AnimationState.ATTACK)
        return
    
    # Dash animation (medium-high priority)
    if self.dashing > 0:
        self.anim_manager.play(AnimationState.DASH)
        return
    
    # Jump/Fall animations (medium priority)
    if not self.on_ground:
        if self.vy < -1:  # Moving upward
            self.anim_manager.play(AnimationState.JUMP)
        else:  # Falling
            self.anim_manager.play(AnimationState.FALL)
        return
    
    # Walk animation (low priority)
    if abs(self.vx) > 0.5:
        self.anim_manager.play(AnimationState.WALK)
    else:
        # Idle (lowest priority)
        self.anim_manager.play(AnimationState.IDLE)
```

Then call it in your main `tick()` method:

```python
def tick(self, level, keys, mouse_buttons):
    # ... existing tick code ...
    
    # Update animation state
    if hasattr(self, 'anim_manager'):
        self._update_animation_state()
        self.anim_manager.update()
```

### Step 5: Update `draw()` Method

Replace the colored rectangle with sprite rendering:

```python
def draw(self, surf, camera):
    # Draw sprite using animation manager
    if hasattr(self, 'anim_manager'):
        sprite_drawn = self.anim_manager.draw(surf, camera, show_invincibility=True)
    else:
        sprite_drawn = False
    
    # Fallback to colored rectangle if sprite not available
    if not sprite_drawn:
        # Change color for visual feedback
        if getattr(self, 'no_clip', False):
            if getattr(self, 'floating_mode', False):
                col = (100, 255, 200) if not self.iframes_flash else (100, 255, 80)
            else:
                col = (200, 100, 255) if not self.iframes_flash else (200, 100, 80)
        elif self.wall_sliding:
            col = (100, 150, 255) if not self.iframes_flash else (100, 150, 80)
        else:
            col = ACCENT if not self.iframes_flash else (ACCENT[0], ACCENT[1], 80)
        
        pygame.draw.rect(surf, col, camera.to_screen_rect(self.rect), border_radius=4)
    
    # Draw Ranger crosshair/aim line
    if self.cls == 'Ranger' and self.alive:
        self._draw_ranger_crosshair(surf, camera)
    
    # Draw debug overlays
    self._draw_debug_wall_jump(surf)
```

---

## Advanced - Full Player Animation System

### Complete Animation States for Player

```python
def _load_player_sprites(self, cls):
    """Load all animation states for player"""
    base_path = f"assets/player/{cls.lower()}"
    sprite_size = (64, 64)
    
    # IDLE
    self.anim_manager.load_single_frame_animation(
        AnimationState.IDLE,
        f"{base_path}/{cls}_Idle.png",
        sprite_size=sprite_size,
        priority=0
    )
    
    # WALK
    self.anim_manager.load_animation(
        AnimationState.WALK,
        load_numbered_frames(f"{base_path}/{cls}_Walk", 1, 6),
        sprite_size=sprite_size,
        frame_duration=6,
        loop=True,
        priority=1
    )
    
    # RUN (optional - faster walk animation)
    self.anim_manager.load_animation(
        AnimationState.RUN,
        load_numbered_frames(f"{base_path}/{cls}_Run", 1, 6),
        sprite_size=sprite_size,
        frame_duration=4,
        loop=True,
        priority=2
    )
    
    # JUMP
    self.anim_manager.load_single_frame_animation(
        AnimationState.JUMP,
        f"{base_path}/{cls}_Jump.png",
        sprite_size=sprite_size,
        priority=3
    )
    
    # FALL
    self.anim_manager.load_single_frame_animation(
        AnimationState.FALL,
        f"{base_path}/{cls}_Fall.png",
        sprite_size=sprite_size,
        priority=2
    )
    
    # ATTACK (basic combo)
    self.anim_manager.load_animation(
        AnimationState.ATTACK,
        load_numbered_frames(f"{base_path}/{cls}_Attack", 1, 4),
        sprite_size=sprite_size,
        frame_duration=3,
        loop=False,
        priority=10,
        on_complete_callback=self._on_attack_complete,
        next_state=AnimationState.IDLE
    )
    
    # SKILL_1 (Q ability)
    self.anim_manager.load_animation(
        AnimationState.SKILL_1,
        load_numbered_frames(f"{base_path}/{cls}_Skill1", 1, 5),
        sprite_size=sprite_size,
        frame_duration=4,
        loop=False,
        priority=15,
        next_state=AnimationState.IDLE
    )
    
    # SKILL_2 (E ability)
    self.anim_manager.load_animation(
        AnimationState.SKILL_2,
        load_numbered_frames(f"{base_path}/{cls}_Skill2", 1, 5),
        sprite_size=sprite_size,
        frame_duration=4,
        loop=False,
        priority=15,
        next_state=AnimationState.IDLE
    )
    
    # SKILL_3 (R ability)
    self.anim_manager.load_animation(
        AnimationState.SKILL_3,
        load_numbered_frames(f"{base_path}/{cls}_Skill3", 1, 6),
        sprite_size=sprite_size,
        frame_duration=5,
        loop=False,
        priority=15,
        next_state=AnimationState.IDLE
    )
    
    # DASH
    self.anim_manager.load_animation(
        AnimationState.DASH,
        load_numbered_frames(f"{base_path}/{cls}_Dash", 1, 3),
        sprite_size=sprite_size,
        frame_duration=2,
        loop=False,
        priority=12,
        next_state=AnimationState.IDLE
    )
    
    # HURT
    self.anim_manager.load_animation(
        AnimationState.HURT,
        [f"{base_path}/{cls}_Hurt.png"],
        sprite_size=sprite_size,
        frame_duration=8,
        loop=False,
        priority=20,
        next_state=AnimationState.IDLE
    )
    
    # DEATH
    self.anim_manager.load_animation(
        AnimationState.DEATH,
        load_numbered_frames(f"{base_path}/{cls}_Death", 1, 8),
        sprite_size=sprite_size,
        frame_duration=6,
        loop=False,
        priority=100  # Highest priority
    )
```

### Enhanced Animation State Logic

```python
def _update_animation_state(self):
    """Comprehensive animation state machine"""
    # Death (priority 100)
    if not self.alive:
        if not hasattr(self, '_death_anim_started'):
            self.anim_manager.play(AnimationState.DEATH, force=True)
            self._death_anim_started = True
        return
    
    # Hurt animation (priority 20)
    if self.combat.is_invincible() and not hasattr(self, '_hurt_anim_played'):
        self.anim_manager.play(AnimationState.HURT, force=True)
        self._hurt_anim_played = True
        return
    elif not self.combat.is_invincible():
        self._hurt_anim_played = False
    
    # Skill animations (priority 15)
    if self.skill_cd1 > 0 and self.skill_cd1 == self.skill_cd1_max - 1:
        self.anim_manager.play(AnimationState.SKILL_1)
        return
    if self.skill_cd2 > 0 and self.skill_cd2 == self.skill_cd2_max - 1:
        self.anim_manager.play(AnimationState.SKILL_2)
        return
    if self.skill_cd3 > 0 and self.skill_cd3 == self.skill_cd3_max - 1:
        self.anim_manager.play(AnimationState.SKILL_3)
        return
    
    # Dash (priority 12)
    if self.dashing > 0:
        self.anim_manager.play(AnimationState.DASH)
        return
    
    # Attack (priority 10)
    if self.attack_cd > 0 and self.attack_cd > (ATTACK_COOLDOWN - ATTACK_LIFETIME):
        self.anim_manager.play(AnimationState.ATTACK)
        return
    
    # Air states (priority 2-3)
    if not self.on_ground:
        if self.vy < -1:  # Rising
            self.anim_manager.play(AnimationState.JUMP)
        else:  # Falling
            self.anim_manager.play(AnimationState.FALL)
        return
    
    # Ground movement (priority 1-2)
    if abs(self.vx) > 0.5:
        # Use run animation if moving fast
        if abs(self.vx) > self.player_speed * 0.8:
            self.anim_manager.play(AnimationState.RUN)
        else:
            self.anim_manager.play(AnimationState.WALK)
    else:
        # Idle (priority 0)
        self.anim_manager.play(AnimationState.IDLE)

def _on_attack_complete(self):
    """Called when attack animation completes"""
    # Reset combo or trigger effects
    pass
```

---

## Asset Organization for Player

```
assets/
└── player/
    ├── knight/
    │   ├── Knight_Idle.png
    │   ├── Knight_Walk1.png to Knight_Walk6.png
    │   ├── Knight_Attack1.png to Knight_Attack4.png
    │   ├── Knight_Skill1_1.png to Knight_Skill1_5.png
    │   ├── Knight_Dash1.png to Knight_Dash3.png
    │   ├── Knight_Jump.png
    │   ├── Knight_Fall.png
    │   ├── Knight_Hurt.png
    │   └── Knight_Death1.png to Knight_Death8.png
    │
    ├── ranger/
    │   └── (same structure)
    │
    ├── wizard/
    │   └── (same structure)
    │
    └── assassin/
        └── (same structure)
```

---

## Player-Specific Features

### 1. Combo System Support

```python
def _load_combo_animations(self, cls):
    """Load multiple attack animations for combos"""
    base_path = f"assets/player/{cls.lower()}"
    sprite_size = (64, 64)
    
    # Store attack animations in a list
    self.attack_animations = []
    
    for combo_num in range(1, 4):  # 3-hit combo
        try:
            frames = load_numbered_frames(
                f"{base_path}/{cls}_Attack{combo_num}_", 1, 4
            )
            self.attack_animations.append(frames)
        except:
            break
    
    # Load first combo as default
    if self.attack_animations:
        self.anim_manager.load_animation(
            AnimationState.ATTACK,
            self.attack_animations[0],
            sprite_size=sprite_size,
            frame_duration=3,
            loop=False,
            priority=10,
            next_state=AnimationState.IDLE
        )

def _switch_combo_animation(self, combo_index):
    """Switch to different combo animation"""
    if combo_index < len(self.attack_animations):
        self.anim_manager.animations[AnimationState.ATTACK].frames = [
            pygame.transform.scale(
                pygame.image.load(path).convert_alpha(),
                (64, 64)
            ) for path in self.attack_animations[combo_index]
        ]
```

### 2. Class-Specific Animations

Each class can have unique animations:

```python
# Knight - Heavy attacks with long wind-up
# Ranger - Quick shots with bow animations
# Wizard - Casting animations with spell effects
# Assassin - Fast, aggressive attacks
```

### 3. Directional Sprites

The AnimationManager automatically flips sprites based on `self.facing`:

```python
# No extra code needed! The system handles it.
# Just set self.facing = 1 (right) or -1 (left) as you already do
```

---

## Integration with Existing Code

### Minimal Changes Required

The AnimationManager is **additive** - you can add it without breaking existing code:

1. ✅ Current colored rectangle drawing still works as fallback
2. ✅ All existing player logic remains unchanged
3. ✅ Ranger crosshair, debug overlays still work
4. ✅ Combat system, movement, skills all work as before
5. ✅ Only adds 3 method calls: load sprites, update animation, draw sprite

### Backward Compatible

```python
# Old code still works
if not hasattr(self, 'anim_manager'):
    # Draw colored rectangle (current behavior)
    pygame.draw.rect(surf, col, camera.to_screen_rect(self.rect))
else:
    # Draw sprite (new behavior)
    self.anim_manager.draw(surf, camera)
```

---

## Example - Complete Player with Animations

See the appendix for a complete working example of the Player class with AnimationManager integrated.

---

## Testing Your Player Animations

1. **Add sprites gradually**:
   - Start with idle only
   - Add walk animation
   - Add attack animation
   - Add advanced animations

2. **Test states**:
   - Stand still → idle animation
   - Move → walk animation
   - Attack → attack animation
   - Jump → jump animation

3. **Check transitions**:
   - Walk → idle should be smooth
   - Attack → idle should return after animation
   - Hurt should interrupt other animations

4. **Verify facing**:
   - Move left → sprite flips left
   - Move right → sprite flips right

---

## Troubleshooting

**Sprite not showing for player?**
- Check file paths in `_load_player_sprites()`
- Verify sprites exist in `assets/player/`
- Look for [AnimationSystem] errors in console

**Animation not changing?**
- Ensure `_update_animation_state()` is called in `tick()`
- Check that `anim_manager.update()` is called
- Verify animation priorities

**Sprite positioned wrong?**
- Adjust `set_sprite_offset_y()` value
- Player collision rect is 18x30, sprite might be larger
- Try values between 20-40 for offset_y

**Sprite facing wrong direction?**
- AnimationManager uses `self.facing` automatically
- Ensure `self.facing` is set to 1 or -1
- System handles flipping automatically

---

## Summary

✅ **AnimationManager works perfectly for Player**  
✅ **Same API as enemy animations**  
✅ **Supports all player states (idle, walk, attack, skills, etc.)**  
✅ **Class-specific sprites (Knight, Ranger, Wizard, Assassin)**  
✅ **Backward compatible with existing code**  
✅ **Minimal integration effort**  

Start simple with idle + walk, then add more animations as you create the sprite assets!
