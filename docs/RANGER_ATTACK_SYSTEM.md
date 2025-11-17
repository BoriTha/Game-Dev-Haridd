# Ranger 3-State Bow Attack System

## Overview

The Ranger class uses a **reusable 3-state animation system** for bow attacks that combines charging, holding, and shooting into a clean, maintainable pattern. This system can be easily adapted for other charge-based attacks in the future.

## The Three States

```
CHARGE → CHARGED → SHOOT → IDLE
```

### 1. **CHARGE** - Drawing the Bow
- **Frames:** 4 progressive frames (`na-1.png` to `na-4.png`)
- **Duration:** 5 frames per sprite (20 total frames)
- **Loop:** No (transitions to CHARGED when complete)
- **Trigger:** When `self.charging = True` and attack button is held
- **Purpose:** Shows the bow being progressively drawn back

### 2. **CHARGED** - Holding at Full Draw
- **Frames:** 1 frame (`na-5.png`)
- **Duration:** 1 frame per sprite (loops indefinitely)
- **Loop:** Yes (holds this pose)
- **Trigger:** When `self.charge_time >= self.charge_threshold`
- **Purpose:** Looping hold pose while waiting for player to release

### 3. **SHOOT** - Releasing the Arrow
- **Frames:** 2 frames (`na-5.png`, `na-6.png`)
- **Duration:** 4 frames per sprite (8 total frames)
- **Loop:** No (transitions to IDLE when complete)
- **Trigger:** When attack button is released while `self.charging = True`
- **Purpose:** Release animation, arrow projectile spawns during this state

## Code Integration

### Animation Loading (in `_load_ranger_animations()`)

```python
# CHARGE - Drawing bow (progressive 4-frame animation)
self.anim_manager.load_animation(
    AnimationState.CHARGE,
    [f"assets/Player/Ranger/attk-adjust/charge/na-{i}.png" for i in range(1, 5)],
    sprite_size=(48, 64),
    frame_duration=5,
    loop=False,
    priority=4,
    next_state=AnimationState.CHARGED  # Auto-transition!
)

# CHARGED - Holding at full draw (looping hold pose)
self.anim_manager.load_animation(
    AnimationState.CHARGED,
    ["assets/Player/Ranger/attk-adjust/charged/na-5.png"],
    sprite_size=(48, 64),
    frame_duration=1,
    loop=True,  # Loops indefinitely
    priority=4
)

# SHOOT - Releasing arrow
self.anim_manager.load_animation(
    AnimationState.SHOOT,
    ["assets/Player/Ranger/attk-adjust/shoot/na-5.png", 
     "assets/Player/Ranger/attk-adjust/shoot/na-6.png"],
    sprite_size=(48, 64),
    frame_duration=4,
    loop=False,
    priority=4,
    next_state=AnimationState.IDLE  # Auto-transition back to idle!
)
```

### Animation State Machine (in `_update_ranger_animations()`)

```python
# Priority 3: CHARGE/CHARGED (3-state bow attack system)
if self.charging:
    # Check if we've reached full charge
    if self.charge_time >= self.charge_threshold:
        # Transition to CHARGED (holding at full draw)
        if current != AnimationState.CHARGED:
            self.anim_manager.play(AnimationState.CHARGED, force=True)
    else:
        # Still drawing the bow
        if current != AnimationState.CHARGE:
            self.anim_manager.play(AnimationState.CHARGE, force=True)
    return
```

### Input Handling (in `input()`)

```python
# Attack / Ranger charge handling
lmb = pygame.mouse.get_pressed()[0]
if not stunned and self.attack_cd == 0:
    if self.cls == 'Ranger':
        # Start charging on press
        if lmb and not self._prev_lmb:
            self.charging = True
            self.charge_time = 0
        
        # Increment charge timer while holding
        if self.charging and lmb:
            self.charge_time += 1
        
        # Fire arrow on release
        if self.charging and not lmb and self._prev_lmb:
            charged = self.charge_time >= self.charge_threshold
            # Fire arrow logic...
            self.fire_arrow(damage, speed, camera, pierce=charged)
            self.attack_cd = ATTACK_COOLDOWN
            self.charging = False  # Reset charging state
            
# Update prev mouse state
self._prev_lmb = lmb
```

### Arrow Firing (in `fire_arrow()`)

```python
def fire_arrow(self, damage, speed, camera, pierce=False):
    # Trigger SHOOT animation when firing
    if self.anim_manager:
        self.anim_manager.play(AnimationState.SHOOT)
    
    # Spawn arrow projectile...
    # (rest of arrow spawning logic)
```

## Key Variables

| Variable | Type | Purpose |
|----------|------|---------|
| `self.charging` | bool | True when bow is being drawn |
| `self.charge_time` | int | Frames spent charging (increments while holding) |
| `self.charge_threshold` | int | Frames needed for full charge (default: `0.5 * FPS` = 30) |
| `self._prev_lmb` | bool | Previous frame's left mouse button state (for edge detection) |
| `self.attack_cd` | float | Attack cooldown timer (prevents spam) |

## Animation Priority System

The Ranger animation state machine uses a **priority-based system** to determine which animation plays:

1. **Priority 1:** DASH (active dash movement)
2. **Priority 2:** SHOOT (must complete, no interrupt)
3. **Priority 3:** CHARGE/CHARGED (based on charge_time)
4. **Priority 4:** RUN (ground movement)
5. **Priority 5:** IDLE (grounded, stationary)
6. **Priority 6:** WALL_SLIDE (airborne on wall)
7. **Priority 7:** JUMP/FALL (airborne vertical movement)

Higher priority animations **override** lower priority ones. The SHOOT animation **cannot be interrupted** until it completes.

## How to Adapt This System for Other Characters

### Example: Creating a Spell Charge System for Wizard

```python
# 1. Load animations (in _load_wizard_animations)
self.anim_manager.load_animation(
    AnimationState.CHARGE,      # Spell channeling
    ["wizard/charge_1.png", "wizard/charge_2.png", "wizard/charge_3.png"],
    frame_duration=6,
    loop=False,
    priority=4,
    next_state=AnimationState.CHARGED
)

self.anim_manager.load_animation(
    AnimationState.CHARGED,     # Spell ready
    ["wizard/charged_hold.png"],
    frame_duration=1,
    loop=True,
    priority=4
)

self.anim_manager.load_animation(
    AnimationState.SHOOT,       # Spell cast
    ["wizard/cast_1.png", "wizard/cast_2.png"],
    frame_duration=4,
    loop=False,
    priority=4,
    next_state=AnimationState.IDLE
)

# 2. Update animation state machine (in _update_wizard_animations)
if self.casting:
    if self.cast_time >= self.cast_threshold:
        if current != AnimationState.CHARGED:
            self.anim_manager.play(AnimationState.CHARGED, force=True)
    else:
        if current != AnimationState.CHARGE:
            self.anim_manager.play(AnimationState.CHARGE, force=True)
    return

# 3. Input handling (in input)
if skill_key and not self._prev_skill_key:
    self.casting = True
    self.cast_time = 0

if self.casting and skill_key:
    self.cast_time += 1

if self.casting and not skill_key and self._prev_skill_key:
    self.cast_spell(self.cast_time >= self.cast_threshold)
    self.casting = False
```

## Troubleshooting

### Animation doesn't transition from CHARGE to CHARGED
- Check that `next_state=AnimationState.CHARGED` is set in CHARGE animation config
- Verify `loop=False` for CHARGE animation
- Ensure `charge_time` is incrementing properly

### SHOOT animation doesn't play
- Check that `self.anim_manager.play(AnimationState.SHOOT)` is called in `fire_arrow()`
- Verify SHOOT has higher priority than movement animations
- Ensure `is_playing` check prevents interruption

### Character facing wrong direction while charging
- Check the facing update logic in `input()` method
- Ranger locks facing to mouse direction during charge/shoot:
```python
if self.cls == 'Ranger':
    if getattr(self, 'charging', False) or is_shooting:
        mx, my = pygame.mouse.get_pos()
        world_x = (mx / camera.zoom) + camera.x
        if world_x < self.rect.centerx:
            self.facing = -1
        elif world_x > self.rect.centerx:
            self.facing = 1
```

## Benefits of This System

✅ **Reusable** - Easy to adapt for other charge-based attacks  
✅ **Clean State Management** - Clear progression: CHARGE → CHARGED → SHOOT → IDLE  
✅ **Auto-Transitions** - `next_state` parameter handles transitions automatically  
✅ **No Animation Interruption** - Priority system prevents flickering  
✅ **Visual Feedback** - Progressive draw gives clear charging indicator  
✅ **Flexible Timing** - Adjust `frame_duration` to speed up/slow down animations  

## File Locations

- **Animation System:** `src/entities/animation_system.py`
- **Player Implementation:** `src/entities/player_entity.py`
  - `_load_ranger_animations()` - Animation loading (lines 312-420)
  - `_update_ranger_animations()` - State machine (lines 483-555)
  - `input()` - Input handling (lines 791-829)
  - `fire_arrow()` - Arrow spawning (lines 984-1008)
- **Animation Assets:** `assets/Player/Ranger/attk-adjust/`
  - `charge/na-1.png` to `na-4.png` - Progressive draw frames
  - `charged/na-5.png` - Full draw hold frame
  - `shoot/na-5.png`, `na-6.png` - Release frames

## Quick Reference

```python
# Start charging
self.charging = True
self.charge_time = 0

# While charging (increment every frame)
if self.charging and attack_button_held:
    self.charge_time += 1

# Fire when released
if self.charging and not attack_button_held:
    self.fire_arrow(...)
    self.charging = False
```

---

**Last Updated:** January 2025  
**System Version:** v0.7
