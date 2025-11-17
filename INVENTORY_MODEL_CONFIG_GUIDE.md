# Inventory Player Model Configuration Guide

## Quick Reference

To adjust how player sprites appear in the inventory screen, edit the configuration section at the top of `src/systems/inventory.py` (around line 16-38).

## Configuration Variables

### 1. `PLAYER_MODEL_SCALES` - Sprite Size

Controls how large the sprite appears in the inventory model frame.

```python
PLAYER_MODEL_SCALES = {
    'Knight': 1.8,      # Current: Good fit
    'Ranger': 2.2,      # Current: Good fit
    'Wizard': 2.0,      # Placeholder
    'Assassin': 2.0,    # Placeholder
}
```

**How to adjust:**
- **Increase value** (e.g., 1.8 → 2.0) = Larger sprite
- **Decrease value** (e.g., 2.2 → 2.0) = Smaller sprite
- **Recommended range:** 1.5 to 2.5

**Examples:**
```python
'Knight': 2.0,   # Make Knight 11% larger
'Ranger': 1.8,   # Make Ranger 18% smaller
```

### 2. `PLAYER_MODEL_OFFSETS` - Position Adjustment

Controls where the sprite is positioned within the model frame. Values are in pixels.

```python
PLAYER_MODEL_OFFSETS = {
    'Knight': (0, 0),      # Current: Perfectly centered
    'Ranger': (0, 0),      # Current: Perfectly centered
    'Wizard': (0, 0),      # Placeholder
    'Assassin': (0, 0),    # Placeholder
}
```

**How to adjust:**
- **First number (X)**: Horizontal position
  - Positive = Move RIGHT
  - Negative = Move LEFT
- **Second number (Y)**: Vertical position
  - Positive = Move DOWN
  - Negative = Move UP

**Examples:**
```python
'Knight': (5, 0),     # Move Knight 5 pixels right
'Ranger': (0, -10),   # Move Ranger 10 pixels up
'Wizard': (-3, 5),    # Move Wizard 3 pixels left and 5 pixels down
```

## Common Adjustments

### Problem: Sprite is too large and overflowing the frame
**Solution:** Reduce the scale value
```python
'YourClass': 1.8,  # Try reducing from 2.2 to 1.8
```

### Problem: Sprite is too small
**Solution:** Increase the scale value
```python
'YourClass': 2.5,  # Try increasing from 2.0 to 2.5
```

### Problem: Sprite is cut off at the top
**Solution:** Move sprite down with positive Y offset
```python
'YourClass': (0, 10),  # Move 10 pixels down
```

### Problem: Sprite is cut off at the bottom
**Solution:** Move sprite up with negative Y offset
```python
'YourClass': (0, -10),  # Move 10 pixels up
```

### Problem: Sprite needs to be more centered horizontally
**Solution:** Adjust X offset
```python
'YourClass': (-5, 0),  # Move 5 pixels left
'YourClass': (5, 0),   # Move 5 pixels right
```

## Model Frame Dimensions

The inventory model frame is approximately:
- **Width:** ~200 pixels
- **Height:** ~150 pixels
- **Margins:** 10-20 pixels from edges recommended

Keep sprites within these bounds for best appearance.

## Testing Your Changes

1. Edit `src/systems/inventory.py`
2. Modify the scale or offset values
3. Save the file
4. Run the game: `python main.py`
5. Open inventory (default: TAB key)
6. Check the appearance
7. Repeat until satisfied

## Current Sprite Sizes

Reference for calculating good scale values:

| Class    | Sprite Size (WxH) | Current Scale | Effective Size   |
|----------|-------------------|---------------|------------------|
| Knight   | 93x64            | 1.8           | 167x115          |
| Ranger   | 48x64            | 2.2           | 106x141          |
| Wizard   | TBD              | 2.0           | TBD              |
| Assassin | TBD              | 2.0           | TBD              |

## Tips

1. **Start with scale adjustments** before tweaking offsets
2. **Make small changes** (0.1 to 0.2 increments for scale, 2-5 pixels for offsets)
3. **Test with both idle and attack animations** - some animations may be larger
4. **Consider the bow/weapon** - Ranger bow extends beyond character body
5. **Keep it centered** - offsets of (0, 0) usually work best

## Troubleshooting

**Sprite not showing at all?**
- Check that the class name matches exactly (case-sensitive)
- Make sure the player class has animations loaded
- Check console for errors when opening inventory

**Sprite flickers or looks weird?**
- Scale values too extreme (try values between 1.5-2.5)
- Offset values too large (try keeping within ±20 pixels)

**Changes not taking effect?**
- Make sure you saved the file
- Restart the game (changes require reload)
- Check for syntax errors in the configuration

## Examples of Good Settings

### Knight (Heavy armor, sword)
```python
PLAYER_MODEL_SCALES = {'Knight': 1.8}
PLAYER_MODEL_OFFSETS = {'Knight': (0, 0)}
```
Result: Well-centered, good size, weapon visible

### Ranger (Bow and arrows)
```python
PLAYER_MODEL_SCALES = {'Ranger': 2.2}
PLAYER_MODEL_OFFSETS = {'Ranger': (0, 0)}
```
Result: Character visible, bow contained in frame

### Custom adjustment example
```python
# If you want Ranger slightly smaller and moved up:
PLAYER_MODEL_SCALES = {'Ranger': 2.0}
PLAYER_MODEL_OFFSETS = {'Ranger': (0, -8)}
```

Happy configuring!
