# Animation Quick Reference Card

## TL;DR - Add Sprite to Enemy in 3 Steps

### Step 1: Load in `__init__`
```python
self.load_sprite_system(
    idle_path="assets/monster/MyEnemy.png",
    sprite_size=(96, 128),
    offset_y=55
)
```

### Step 2: Update in `tick()`
```python
self.update_attack_animation()
self.sync_sprite_position()
```

### Step 3: Draw in `draw()`
```python
sprite_drawn = self.draw_sprite_with_animation(surf, camera)
if not sprite_drawn:
    pygame.draw.rect(surf, self.get_base_color(), camera.to_screen_rect(self.rect))
```

---

## Add Attack Animation (4 Steps)

### 1. Load frames in `__init__`
```python
self.load_attack_animation(
    frame_paths=[
        "assets/monster/atk/Enemy_ATK1.png",
        "assets/monster/atk/Enemy_ATK2.png",
        "assets/monster/atk/Enemy_ATK3.png"
    ],
    sprite_size=(96, 128),
    anim_speed=4
)
```

### 2. Trigger when attacking
```python
if should_attack:
    self.start_attack_animation()
```

### 3. Update in `tick()`
```python
self.update_attack_animation()
```

### 4. Draw (same as idle)
```python
sprite_drawn = self.draw_sprite_with_animation(surf, camera)
```

---

## Add Projectile Sprite (5 Steps)

### 1. Load sprite in `__init__`
```python
self.load_projectile_sprite(
    sprite_path="assets/monster/atk/Projectile.png",
    sprite_size=(42, 42)
)
self.projectile_hitboxes = []
```

### 2. Create hitbox with sprite flag
```python
hb = pygame.Rect(0, 0, 26, 26)
hb.center = self.rect.center
new_hb = Hitbox(hb, 120, 4, self, vx=nx*8, vy=ny*8, has_sprite=True)
hitboxes.append(new_hb)
self.projectile_hitboxes.append(new_hb)
```

### 3. Clean in `tick()`
```python
self.clean_projectile_hitboxes()
```

### 4. Draw projectiles in `draw()`
```python
self.draw_projectile_sprites(surf, camera)
```

### 5. Debug with F3
Press F3 in-game to see hitboxes!

---

## Advanced: AnimationManager

### Setup in `__init__`
```python
from src.entities.animation_system import AnimationManager, AnimationState

self.anim_manager = AnimationManager(self)
self.anim_manager.load_single_frame_animation(
    AnimationState.IDLE, "assets/monster/Idle.png"
)
self.anim_manager.load_animation(
    AnimationState.ATTACK,
    ["assets/monster/atk/ATK1.png", "assets/monster/atk/ATK2.png"],
    loop=False,
    next_state=AnimationState.IDLE
)
```

### Update in `tick()`
```python
if attacking:
    self.anim_manager.play(AnimationState.ATTACK)
else:
    self.anim_manager.play(AnimationState.IDLE)

self.anim_manager.update()
```

### Draw in `draw()`
```python
self.anim_manager.draw(surf, camera)
```

---

## Common Sprite Sizes

- Small enemies: **64x64** to **96x96**
- Medium enemies: **96x128**
- Large enemies: **128x160**
- Projectiles: **32x32** to **64x64**

---

## Method Cheat Sheet

| Method | Where | What |
|--------|-------|------|
| `load_sprite_system()` | `__init__` | Load idle sprite |
| `load_attack_animation()` | `__init__` | Load attack frames |
| `load_projectile_sprite()` | `__init__` | Load projectile |
| `start_attack_animation()` | When attacking | Start animation |
| `update_attack_animation()` | `tick()` | Update frame |
| `sync_sprite_position()` | `tick()` | Sync position |
| `clean_projectile_hitboxes()` | `tick()` | Clean dead projectiles |
| `draw_sprite_with_animation()` | `draw()` | Draw sprite |
| `draw_projectile_sprites()` | `draw()` | Draw projectiles |

---

## Troubleshooting

**Sprite not showing?**
- Check file path
- Look for [ERROR] in console
- Ensure file exists

**Animation not playing?**
- Call `update_attack_animation()` in `tick()`
- Call `start_attack_animation()` when attacking
- Check `anim_speed` (should be 4-8)

**Projectile sprite missing?**
- Set `has_sprite=True` in Hitbox
- Add to `self.projectile_hitboxes`
- Call `draw_projectile_sprites()` in `draw()`

**Position wrong?**
- Adjust `offset_y` in `load_sprite_system()`
- Call `sync_sprite_position()` in `tick()`

---

## Full Example - Simple Enemy

```python
class SimpleEnemy(Enemy):
    def __init__(self, x, ground_y):
        super().__init__(x, ground_y, width=40, height=40, 
                        combat_config={'max_hp': 50})
        
        # Load sprite
        self.load_sprite_system(
            idle_path="assets/monster/Simple.png",
            sprite_size=(96, 128),
            offset_y=55
        )
        
        self.type = "Simple"
    
    def tick(self, level, player):
        if not self.combat.alive:
            return
        
        self.combat.update()
        
        # Your AI here...
        
        # Update sprite
        self.sync_sprite_position()
    
    def draw(self, surf, camera, show_los=False, show_nametags=False):
        if not self.combat.alive:
            return
        
        # Draw sprite or fallback
        sprite_drawn = self.draw_sprite_with_animation(surf, camera)
        if not sprite_drawn:
            pygame.draw.rect(surf, (100, 150, 200), 
                           camera.to_screen_rect(self.rect))
        
        self.draw_nametag(surf, camera, show_nametags)
    
    def get_base_color(self):
        return (100, 150, 200)
```

---

## See Full Guide

For detailed examples and advanced features, see:
**`docs/SPRITE_ANIMATION_GUIDE.md`**
