# Ranger Attack System - Quick Start Guide

## What Was Changed

The Ranger's bow attack animation system has been **refactored and documented** to be a **reusable 3-state charge attack pattern** that can be easily adapted for future characters.

## Files Modified

1. **`src/entities/player_entity.py`**
   - `_load_ranger_animations()` - Added detailed documentation comments
   - `_update_ranger_animations()` - Added state machine documentation

2. **`docs/RANGER_ATTACK_SYSTEM.md`** (NEW)
   - Complete documentation of the 3-state system
   - How to adapt it for other characters
   - Troubleshooting guide

3. **`docs/RANGER_ATTACK_EXAMPLE.py`** (NEW)
   - Working example showing how to implement the pattern for a "Pyromancer" character
   - Side-by-side comparison with Ranger

## The 3-State Pattern

```
┌─────────┐      ┌──────────┐      ┌───────┐      ┌──────┐
│  IDLE   │ ──> │  CHARGE  │ ──> │ CHARGED│ ──> │ SHOOT│ ──> IDLE
└─────────┘      └──────────┘      └───────┘      └──────┘
                 (drawing bow)     (holding)      (release)
```

### Key Features

✅ **Auto-transitions** - Animations automatically flow from CHARGE → CHARGED → SHOOT → IDLE  
✅ **Priority-based** - Attack animations override movement, SHOOT can't be interrupted  
✅ **State tracking** - Simple `charging` flag and `charge_time` counter  
✅ **Visual feedback** - Progressive animation shows charge buildup  
✅ **Reusable** - Easy to copy for other charge-based attacks  

## How It Works

### State Variables
```python
self.charging = False        # Is attack being charged?
self.charge_time = 0         # How long charging (in frames)
self.charge_threshold = 30   # Frames needed for full charge
self._prev_lmb = False       # Previous mouse button state
```

### Input Flow
```python
# 1. Press attack button
if lmb and not self._prev_lmb:
    self.charging = True
    self.charge_time = 0

# 2. Hold to charge
if self.charging and lmb:
    self.charge_time += 1

# 3. Release to fire
if self.charging and not lmb and self._prev_lmb:
    charged = self.charge_time >= self.charge_threshold
    self.fire_arrow(damage, speed, camera, pierce=charged)
    self.charging = False
```

### Animation State Machine
```python
# Priority 1: SHOOT (must complete)
if current == AnimationState.SHOOT and self.anim_manager.is_playing:
    return

# Priority 2: CHARGE/CHARGED
if self.charging:
    if self.charge_time >= self.charge_threshold:
        self.anim_manager.play(AnimationState.CHARGED)  # Hold at full draw
    else:
        self.anim_manager.play(AnimationState.CHARGE)   # Drawing bow
    return

# Priority 3+: Movement animations...
```

## Testing the System

1. **Run the game:**
   ```bash
   python main.py
   ```

2. **Select Ranger** from the class selection menu

3. **Test the attack:**
   - **Quick shot:** Click and immediately release → plays CHARGE briefly → SHOOT → weak arrow
   - **Charged shot:** Hold click for 0.5 seconds → CHARGE → CHARGED (loops) → release → SHOOT → strong arrow
   - **Movement while charging:** Can move and charge at the same time
   - **Facing direction:** Character faces mouse cursor while charging/shooting

4. **Expected behavior:**
   - Smooth transition between animation states
   - No animation flickering
   - SHOOT animation always completes before returning to IDLE
   - Arrow spawns during SHOOT animation

## Adapting for Other Characters

See **`docs/RANGER_ATTACK_EXAMPLE.py`** for a complete example of implementing this system for a "Pyromancer" character with fireball charging.

### Quick Steps:

1. **Copy state variables** (`charging`, `charge_time`, `charge_threshold`)
2. **Load 3 animations** (CHARGE, CHARGED, SHOOT with proper `next_state`)
3. **Copy input handling pattern** (press → charge → release)
4. **Copy animation state machine** (priority-based with charge time check)
5. **Call `anim_manager.play(SHOOT)`** in your attack method

## Animation Assets

```
assets/Player/Ranger/attk-adjust/
├── charge/          # Progressive draw frames
│   ├── na-1.png    # Start drawing
│   ├── na-2.png    # Quarter drawn
│   ├── na-3.png    # Half drawn
│   └── na-4.png    # Almost fully drawn
├── charged/         # Hold pose
│   └── na-5.png    # Fully drawn (loops)
└── shoot/           # Release animation
    ├── na-5.png    # Release start
    └── na-6.png    # Follow-through
```

## Troubleshooting

| Issue | Solution |
|-------|----------|
| Animation doesn't transition from CHARGE to CHARGED | Check `next_state=AnimationState.CHARGED` in CHARGE config |
| SHOOT animation gets interrupted | Ensure SHOOT has higher priority and `is_playing` check |
| Character faces wrong direction | Lock facing to mouse during charge/shoot (see line 731-742) |
| Weak/strong arrow not working | Check `charged = self.charge_time >= self.charge_threshold` logic |

## Performance Notes

- **Charge threshold:** 30 frames (0.5 seconds at 60 FPS) - feels responsive
- **Frame durations:** CHARGE (5), CHARGED (1), SHOOT (4) - total ~8 frames release time
- **Animation priority:** 4 (overrides movement but not dash)

## Further Reading

- **Full documentation:** `docs/RANGER_ATTACK_SYSTEM.md`
- **Example implementation:** `docs/RANGER_ATTACK_EXAMPLE.py`
- **Animation system guide:** `docs/ANIMATION_SYSTEM_SUMMARY.txt`
- **Frame event guide:** `docs/FRAME_EVENT_QUICK_REF.md`

---

**Created:** January 2025  
**Version:** v0.7  
**Status:** ✅ Production Ready
