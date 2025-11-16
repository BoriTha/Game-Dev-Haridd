# Example: Migrating Golem to AnimationManager

## Current Code (Legacy System) - What Golem Uses Now

```python
class Golem(Enemy):
    def __init__(self, x, ground_y):
        super().__init__(...)
        
        # LEGACY: Manual sprite loading
        try:
            img = pygame.image.load("assets/monster/Dark_Knight.png").convert_alpha()
            self.sprite_idle = pygame.transform.scale(img, (96,128))
        except:
            print("[ERROR] Missing Dark_Knight.png")
            self.sprite_idle = None
        
        self.sprite = self.sprite_idle
        self.sprite_offset_y = 55
        
        # LEGACY: Manual attack animation loading
        self.atk_frames = []
        for i in range(1,5):
            path = f"assets/monster/atk/Dark_Knight_ATK{i}.png"
            try:
                frame = pygame.image.load(path).convert_alpha()
                self.atk_frames.append(pygame.transform.scale(frame,(96,128)))
            except:
                print(f"[ERROR] Cannot load {path}")
        
        self.play_attack_anim = False
        self.atk_index = 0
        self.atk_timer = 0
        self.atk_speed = 4
        
        # LEGACY: Manual projectile sprite
        try:
            aura_img = pygame.image.load("assets/monster/atk/Dark_Knight_Aura.png").convert_alpha()
            self.projectile_sprite = pygame.transform.scale(aura_img, (42,42))
        except:
            print("[ERROR] Missing Aura sprite")
            self.projectile_sprite = None
        
        self.projectile_hitboxes = []
    
    def tick(self, level, player):
        # ... AI logic ...
        
        # LEGACY: Manual animation updates
        self.update_attack_animation()
        self.clean_projectile_hitboxes()
        self.sync_sprite_position()
    
    def draw(self, surf, camera, show_los=False, show_nametags=False):
        # LEGACY: Manual sprite drawing
        sprite_drawn = self.draw_sprite_with_animation(surf, camera)
        if not sprite_drawn:
            # Fallback
            pygame.draw.rect(surf, self.get_base_color(), camera.to_screen_rect(self.rect))
        
        self.draw_projectile_sprites(surf, camera)
        # ... telegraph, nametags ...
```

---

## Migrated Code (AnimationManager) - How It Would Look

```python
from src.entities.animation_system import (
    AnimationManager, AnimationState, load_numbered_frames
)

class Golem(Enemy):
    def __init__(self, x, ground_y):
        super().__init__(...)
        
        # NEW: AnimationManager setup
        self.anim_manager = AnimationManager(self, default_state=AnimationState.IDLE)
        self.anim_manager.set_sprite_offset_y(55)
        
        # Load idle sprite
        self.anim_manager.load_single_frame_animation(
            AnimationState.IDLE,
            "assets/monster/Dark_Knight.png",
            sprite_size=(96, 128),
            priority=0
        )
        
        # Load attack animation with auto-return to idle
        self.anim_manager.load_animation(
            AnimationState.ATTACK,
            load_numbered_frames("assets/monster/atk/Dark_Knight_ATK", 1, 4),
            sprite_size=(96, 128),
            frame_duration=4,
            loop=False,
            priority=10,
            next_state=AnimationState.IDLE  # Auto-return to idle after attack
        )
        
        # Load telegraph animation (optional - could use this for "!!" warning)
        self.anim_manager.load_single_frame_animation(
            AnimationState.TELEGRAPH,
            "assets/monster/Dark_Knight.png",  # Could use different sprite
            sprite_size=(96, 128),
            priority=5
        )
        
        # Projectile sprite (still manual - AnimationManager is for entity sprites)
        self.load_projectile_sprite(
            "assets/monster/atk/Dark_Knight_Aura.png",
            sprite_size=(42, 42)
        )
        self.projectile_hitboxes = []
    
    def tick(self, level, player):
        if not self.combat.alive:
            return
        
        self.combat.update()
        self.handle_status_effects()
        
        # ... AI logic ...
        
        # NEW: Determine animation state
        if self.tele_t > 0:
            # Telegraphing attack
            self.anim_manager.play(AnimationState.TELEGRAPH)
        elif self.play_attack_anim:
            # Playing attack
            self.anim_manager.play(AnimationState.ATTACK)
        else:
            # Idle
            self.anim_manager.play(AnimationState.IDLE)
        
        # NEW: Update animation frame
        self.anim_manager.update()
        
        # Still needed for projectiles
        self.clean_projectile_hitboxes()
    
    def draw(self, surf, camera, show_los=False, show_nametags=False):
        if not self.combat.alive:
            return
        
        self.draw_debug_vision(surf, camera, show_los)
        
        # NEW: Draw using AnimationManager
        sprite_drawn = self.anim_manager.draw(surf, camera)
        
        if not sprite_drawn:
            # Fallback to colored rect
            base_color = self.get_base_color()
            status_color = self.get_status_effect_color(base_color)
            pygame.draw.rect(surf, status_color, camera.to_screen_rect(self.rect))
        
        # Projectiles still use legacy system
        self.draw_projectile_sprites(surf, camera)
        
        # Telegraph
        if self.tele_t > 0:
            from src.core.utils import draw_text
            draw_text(surf, self.tele_text, 
                     camera.to_screen((self.rect.centerx-6, self.rect.top-12)),
                     (255,120,90), size=22, bold=True)
        
        self.draw_status_effects(surf, camera)
        self.draw_nametag(surf, camera, show_nametags)
```

---

## Key Differences

### Legacy (Current)
- ~50 lines of manual sprite loading
- Manual frame tracking (`atk_index`, `atk_timer`)
- Must call `update_attack_animation()` every frame
- Must manually switch between `sprite_idle` and `atk_frames`
- No auto-transitions

### AnimationManager (New)
- ~30 lines with cleaner structure
- Automatic frame tracking
- Just call `anim_manager.update()` once
- Automatic sprite switching based on state
- Auto-transitions (attack → idle)
- Priority system prevents flickering
- Easier to add new animations (dash, special attacks, etc.)

---

## Code Reduction Comparison

| Task | Legacy Lines | AnimationManager Lines |
|------|--------------|------------------------|
| Load idle sprite | 8 | 5 |
| Load attack frames | 10 | 5 |
| Update animation | 3 method calls | 1 method call |
| Switch states | Manual if/else | Automatic |
| **Total Setup** | **~50 lines** | **~30 lines** |

---

## When to Migrate?

### Keep Legacy If:
- ✅ Enemy has 1-2 simple animations
- ✅ It's already working fine
- ✅ You don't plan to add more animations
- ✅ You want simplicity

### Migrate to AnimationManager If:
- ✅ You want to add more animations (dash, multiple attacks, skills)
- ✅ You need animation priorities (prevent flickering)
- ✅ You want auto-transitions
- ✅ You want consistency across all enemies
- ✅ Future enemy designs will be complex

---

## Recommendation

**For Golem specifically:** The legacy system is fine! It's working, it's simple, and Golem only needs idle + attack + projectiles.

**For future complex enemies:** Use AnimationManager from the start - it will save time and code.

**Both systems work together perfectly** - you can have some enemies using legacy and others using AnimationManager in the same game.
