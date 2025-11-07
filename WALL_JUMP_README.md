# Wall Jump and Wall Slide System

## Overview
This game now features a wall jump and wall slide system similar to Super Meat Boy.

## How It Works

### Wall Slide
- When the player jumps and touches a wall, they will stick to it for a brief moment
- While touching the wall, the player slides down at a reduced speed
- The player turns blue when wall sliding for visual feedback

### Wall Jump
- While wall sliding, press the jump button (Space/K) to jump away from the wall.
- The wall jump provides strong horizontal momentum away from the wall.
- After a wall jump, there's a brief cooldown before the player can stick to walls again.
- NEW: Immediately after a wall jump, there is a short "float window":
  - Duration: `WALL_JUMP_FLOAT_FRAMES` (default 8 frames).
  - During this window, upward movement uses reduced gravity (`WALL_JUMP_FLOAT_GRAVITY_SCALE`, default 0.35),
    giving a small airborne/slow-mo feel while preserving the strong outward push.
  - The float only applies while the player is still traveling upward; once they start falling or the timer ends,
    normal gravity resumes.
  - The float phase is canceled if:
    - The player re-enters a wall slide.
    - A dash ends while airborne.

## Controls
- **A/D**: Move left/right
- **Space/K**: Jump (also wall jump when sliding)
- **Shift/J**: Dash

## Configuration Parameters
- `WALL_SLIDE_SPEED`: Maximum speed while sliding down wall (2.0)
- `WALL_JUMP_H_SPEED`: Horizontal velocity for wall jump (6.0)
- `WALL_JUMP_V_SPEED`: Vertical velocity for wall jump (-8.0)
- `WALL_STICK_TIME`: Frames player sticks to wall after leaving ground (4)
- `WALL_JUMP_COOLDOWN`: Frames before player can stick to wall again after wall jump (10)

## Technical Implementation

### Wall Detection
The system detects wall collisions in the `move_and_collide()` method:
- `on_left_wall`: True when touching a wall on the left
- `on_right_wall`: True when touching a wall on the right

### Wall Slide State
The player enters wall slide state when:
- Not on ground
- Wall stick timer is active
- Touching either left or right wall

### Wall Jump Mechanics
When wall sliding and jump is pressed:
- Jump horizontally away from the wall
- Apply wall jump velocities
- Set cooldown to prevent immediate re-sticking

## Visual Feedback
- Player turns blue when wall sliding
- Normal color when not sliding
- Maintains invincibility flashing when damaged

## Testing Tips
1. Jump towards a wall to initiate wall slide
2. Press jump while sliding to perform wall jump
3. Try chaining wall jumps between parallel walls
4. Test different timing for optimal wall jumps