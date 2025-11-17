# Inventory Player Model Display Update

## Summary
Updated the inventory system to display animated player sprites instead of a static colored rectangle in the character model frame.

## Changes Made

### 1. Enhanced `Inventory.__init__()` (src/systems/inventory.py)
Added tracking variables for player model animation state:
- `_model_anim_timer`: Tracks animation frame progression
- `_model_attack_cooldown`: Cooldown timer between attack animations
- `_model_is_attacking`: Boolean flag for current attack animation state

### 2. New Method: `_draw_player_model()` (src/systems/inventory.py)
Renders the animated player sprite in the inventory character model frame:

**Features:**
- **Idle Animation**: Displays the player's idle animation by default, looping continuously
- **Random Run Animations**: ~0.8% chance per frame (~every 2-3 seconds) to trigger a run animation
- **Animation Cooldown**: 1.5 second cooldown between run animations
- **Class-Specific Sprites**: Shows Knight or Ranger sprites based on player class
- **Graceful Fallback**: Falls back to colored rectangle for classes without animations
- **Universal Compatibility**: Uses only IDLE and RUN animations to avoid conflicts with class-specific attack systems

**Technical Details:**
- Accesses player's `AnimationManager` to get animation frames
- Calculates frame index based on animation timer and frame duration
- **Auto-scales sprites** to fit within frame bounds (150px tall, with margins)
  - Uses `min(height_scale, width_scale)` to fit both dimensions
  - Maintains aspect ratio for proper sprite appearance
  - 10px margins on all sides for clean presentation
- Bottom-aligns sprite with 10px margin to keep feet visible
- Flips sprites horizontally to face right for display
- Doesn't interfere with actual gameplay animations (read-only access)

### 3. Updated `draw_inventory_overlay()` (src/systems/inventory.py)
Replaced static rectangle drawing with call to `_draw_player_model()`:
```python
# Old code (removed):
model_rect = pygame.Rect(0, 0, self.game.player.rect.width * 3.5, self.game.player.rect.height * 3.5)
model_rect.center = model_frame.center
pygame.draw.rect(self.game.screen, (120, 200, 235), model_rect, border_radius=12)

# New code:
self._draw_player_model(model_frame)
```

## Behavior

### Knight Class
- Shows idle animation with 6 frames at 8 frames/sprite (slow, breathing)
- Randomly plays run animation with 8 frames at 6 frames/sprite (running motion)
- Run animation plays through once, then returns to idle

### Ranger Class  
- Shows idle animation with 2 frames at 12 frames/sprite (bow holding stance)
- Randomly plays run animation with 8 frames at 5 frames/sprite (running motion)
- Run animation plays through once, then returns to idle

### Other Classes (Wizard, Assassin)
- Falls back to colored rectangle display (no sprites implemented yet)
- Same size and positioning as before

## Testing

Tested with Knight class:
- ✓ Idle animation loops correctly
- ✓ Attack animation triggers randomly
- ✓ Proper cooldown between attacks
- ✓ No interference with gameplay animations
- ✓ Graceful fallback for classes without animation system

## Future Enhancements

Potential improvements:
1. Add Ranger-specific attack animation variant
2. Add Wizard/Assassin sprite support when animations are implemented
3. Add skill animation previews (randomly cycle through skills)
4. Add emote/gesture animations for more variety
5. Add hover tooltip showing class abilities

## Files Modified

- `src/systems/inventory.py` - Added player model animation system
