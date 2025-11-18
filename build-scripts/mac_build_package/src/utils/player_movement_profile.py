from __future__ import annotations
from dataclasses import dataclass, asdict
from typing import Optional, Tuple, Dict
import math

# Import project defaults so the profile matches the game's tuning by default
from config import (
    PLAYER_SPEED, PLAYER_AIR_SPEED, PLAYER_JUMP_V, GRAVITY, TERMINAL_VY,
    DASH_SPEED, DASH_TIME, DASH_COOLDOWN, DOUBLE_JUMPS,
    AIR_ACCEL, AIR_FRICTION, MAX_AIR_SPEED,
    WALL_JUMP_H_ACCEL, WALL_JUMP_H_MAX_SPEED, WALL_JUMP_V_SPEED, WALL_JUMP_GRAVITY_SCALE,
    WALL_LEAVE_H_BOOST, WALL_SLIDE_SPEED, WALL_SLIDE_GRAVITY_SCALE,
)


@dataclass
class PlayerMovementProfile:
    """
    Holds player movement tuning and provides convenience metrics for a map validator.

    Velocities are in pixels/frame. Gravity is positive (e.g. 0.45). jump_velocity
    is negative for upward (consistent with the project's convention).

    Usage (validator):
      profile = PlayerMovementProfile.from_defaults_for('knight')
      h, d = profile.compute_single_jump_metrics(use_horizontal='air')
      ok = profile.can_cross_gap(gap_px, mode='double', use_horizontal='air')
    """

    # Identity
    name: str = "default"

    # Basic movement
    walk_speed: float = PLAYER_SPEED
    air_speed: float = PLAYER_AIR_SPEED

    # Jumping
    jump_velocity: float = PLAYER_JUMP_V  # negative = upward
    gravity: float = GRAVITY              # positive value
    terminal_vy: float = TERMINAL_VY

    # Jump counts / extras
    double_jumps: int = DOUBLE_JUMPS
    extra_jump_charges: int = 0

    # Dash
    dash_speed: float = DASH_SPEED
    dash_time_frames: int = DASH_TIME
    dash_cooldown_frames: int = DASH_COOLDOWN
    can_dash: bool = True

    # Wall jump / slide
    can_wall_jump: bool = True
    wall_jump_h_accel: float = WALL_JUMP_H_ACCEL
    wall_jump_h_max_speed: float = WALL_JUMP_H_MAX_SPEED
    wall_jump_v_speed: float = WALL_JUMP_V_SPEED
    wall_jump_gravity_scale: float = WALL_JUMP_GRAVITY_SCALE
    wall_leave_h_boost: float = WALL_LEAVE_H_BOOST
    wall_slide_speed: float = WALL_SLIDE_SPEED
    wall_slide_gravity_scale: float = WALL_SLIDE_GRAVITY_SCALE

    # Air control
    air_accel: float = AIR_ACCEL
    air_friction: float = AIR_FRICTION
    max_air_speed: float = MAX_AIR_SPEED

    # Cached/computed metrics (filled by compute functions)
    max_jump_height: Optional[float] = None
    max_jump_distance: Optional[float] = None

    # --- Construction helpers ---
    @classmethod
    def from_dict(cls, data: Dict) -> "PlayerMovementProfile":
        allowed = set(cls.__dataclass_fields__.keys())
        filtered = {k: v for k, v in data.items() if k in allowed}
        return cls(**filtered)

    def to_dict(self) -> Dict:
        return asdict(self)

    @classmethod
    def from_defaults_for(cls, name: str) -> "PlayerMovementProfile":
        """
        Convenience factory for named presets. Keep lightweight — validator may extend.
        """
        name = name.lower()
        # Simple presets; validator/game can expand/override as needed
        if name == 'knight':
            return cls(name='knight', walk_speed=3.6, air_speed=3.0, jump_velocity=-10.2)
        if name == 'ranger':
            return cls(name='ranger', walk_speed=4.6, air_speed=4.0, jump_velocity=-10.2)
        if name == 'wizard':
            return cls(name='wizard', walk_speed=3.8, air_speed=3.2, jump_velocity=-9.8)
        if name == 'assassin':
            return cls(name='assassin', walk_speed=5.0, air_speed=4.5, jump_velocity=-10.6)
        return cls(name=name)

    # --- Core metrics ---
    def compute_single_jump_metrics(self, horizontal_speed: Optional[float] = None) -> Tuple[float, float]:
        """
        Compute approximate maximum single-jump apex height (pixels) and horizontal range (pixels).

        horizontal_speed: if None, uses `air_speed` as a realistic in-air horizontal speed. For
        conservative "walk"-based checks pass `walk_speed`.

        Returns (max_height_px, max_distance_px) and caches values on the profile.
        """
        g = float(self.gravity)
        if g <= 0:
            self.max_jump_height = 0.0
            self.max_jump_distance = 0.0
            return self.max_jump_height, self.max_jump_distance

        v = abs(float(self.jump_velocity))
        # Vertical max height: h = v^2 / (2*g)
        h = (v * v) / (2.0 * g)

        # Time to apex = v / g; total airtime ~= 2 * v / g
        t_total = 2.0 * (v / g)

        # Horizontal speed to use
        if horizontal_speed is None:
            horiz = float(self.air_speed)
        else:
            horiz = float(horizontal_speed)

        d = horiz * t_total

        self.max_jump_height = h
        self.max_jump_distance = d
        return h, d

    def compute_double_jump_metrics(self, horizontal_speed: Optional[float] = None) -> Tuple[float, float]:
        """
        Approximate maximum vertical height and horizontal distance using one additional jump
        (double-jump). This uses a simple, conservative model where the second jump is applied
        at the apex of the first jump (which is a common conservative assumption for reach).

        Returns (total_height_px, total_distance_px) and does not overwrite single-jump cache.
        """
        g = float(self.gravity)
        if g <= 0:
            return 0.0, 0.0

        v1 = abs(float(self.jump_velocity))
        # Allow possibility that wall_jump_v_speed is used as a double-jump (some systems differ)
        # but for now use the same jump_velocity for the second jump.
        v2 = v1

        # Height contributions are independent if second jump happens at apex: h_total = h1 + h2
        h1 = (v1 * v1) / (2.0 * g)
        h2 = (v2 * v2) / (2.0 * g)
        total_h = h1 + h2

        # Time estimate: time to apex of first = v1/g. After second jump at apex, airtime from second = 2*v2/g.
        t_total = (v1 / g) + (2.0 * v2 / g)

        horiz = float(horizontal_speed) if horizontal_speed is not None else float(self.air_speed)
        total_d = horiz * t_total

        return total_h, total_d

    def compute_wall_jump_metrics(self, horizontal_speed: Optional[float] = None) -> Tuple[float, float]:
        """
        Conservative estimate of reach when performing a wall-jump.

        Model used:
          - Immediate horizontal boost: `wall_leave_h_boost` (px/frame)
          - Additional horizontal acceleration during ascent: `wall_jump_h_accel`, clamped by `wall_jump_h_max_speed`.
          - Vertical jump velocity: `wall_jump_v_speed` (negative upward). gravity may be scaled during ascent
            using `wall_jump_gravity_scale`.
          - After active ascent+fall due to wall-jump, assume normal falling and horizontal control uses `air_speed`.

        This function returns (approx_height_px, approx_horizontal_range_px).
        """
        g = float(self.gravity)
        if g <= 0:
            return 0.0, 0.0

        v_wall = abs(float(self.wall_jump_v_speed))
        # Ascend time (using wall jump gravity scale during ascent)
        ascent_g = g * float(max(1e-6, self.wall_jump_gravity_scale))
        t_ascent = v_wall / ascent_g

        # Height from vertical wall jump (apex above jump start)
        h_wall = (v_wall * v_wall) / (2.0 * ascent_g)

        # Horizontal: initial boost + acceleration during ascent (clamped)
        initial_horiz = float(self.wall_leave_h_boost)
        # If wall_jump_h_accel is present, compute increase over ascent time up to max speed
        accel = float(self.wall_jump_h_accel)
        h_max_speed = float(self.wall_jump_h_max_speed)

        # assume starting horizontal after boost is initial_horiz; accelerate towards h_max_speed
        # time to reach max speed (from initial) under accel
        if accel > 0:
            time_to_max = max(0.0, (h_max_speed - abs(initial_horiz)) / accel)
        else:
            time_to_max = float('inf')

        # horizontal gained during ascent due to accel (integrate v from initial to either max or end of ascent)
        if t_ascent <= 0:
            accel_distance = 0.0
            accel_final_speed = abs(initial_horiz)
        else:
            if time_to_max >= t_ascent:
                # won't reach max; final speed = initial + accel * t_ascent
                accel_final_speed = abs(initial_horiz) + accel * t_ascent
                # distance = initial * t + 0.5 * accel * t^2
                accel_distance = abs(initial_horiz) * t_ascent + 0.5 * accel * (t_ascent ** 2)
            else:
                # reaches max before ascent ends
                accel_distance = abs(initial_horiz) * time_to_max + 0.5 * accel * (time_to_max ** 2)
                # remaining ascent at max speed
                accel_distance += h_max_speed * (t_ascent - time_to_max)
                accel_final_speed = h_max_speed

        # After ascent, descent time roughly equals time to fall from apex: t_descent ~= v_wall / g (using normal gravity)
        t_descent = v_wall / g

        # During descent we assume player may apply `air_speed` horizontal control (or provided horizontal_speed)
        horiz_during_descent = float(horizontal_speed) if horizontal_speed is not None else float(self.air_speed)

        # total horizontal range: contribution during ascent (initial/accel) + during descent (air control)
        range_px = accel_distance + horiz_during_descent * t_descent

        return h_wall, range_px

    # --- Validator helpers ---
    def gap_pixels_from_tiles(self, gap_tiles: int, tile_size: int) -> int:
        return int(gap_tiles * tile_size)

    def can_cross_gap(self,
                      gap_px: int,
                      mode: str = 'single',
                      use_horizontal: str = 'air') -> bool:
        """
        Determine if the profile can cross a horizontal gap of `gap_px` pixels.

        mode: 'single', 'double', 'wall', 'wall_double'
        use_horizontal: 'air', 'walk', 'max' -> selects horizontal speed used for range computation.

        Returns True if estimated reachable horizontal distance >= gap_px.
        """
        if use_horizontal == 'air':
            horiz = self.air_speed
        elif use_horizontal == 'walk':
            horiz = self.walk_speed
        elif use_horizontal == 'max':
            # choose whichever is larger between burst/horizontal boosts
            horiz = max(self.air_speed, self.max_air_speed, abs(self.wall_leave_h_boost))
        else:
            try:
                horiz = float(use_horizontal)
            except Exception:
                horiz = self.air_speed

        if mode == 'single':
            _, d = self.compute_single_jump_metrics(horizontal_speed=horiz)
            return d + 1e-6 >= gap_px
        elif mode == 'double':
            if self.double_jumps + self.extra_jump_charges <= 0:
                return False
            _, d = self.compute_double_jump_metrics(horizontal_speed=horiz)
            return d + 1e-6 >= gap_px
        elif mode == 'wall':
            if not self.can_wall_jump:
                return False
            _, d = self.compute_wall_jump_metrics(horizontal_speed=horiz)
            return d + 1e-6 >= gap_px
        elif mode == 'wall_double':
            # Conservative: wall jump + extra double jump after wall
            if not self.can_wall_jump:
                return False
            h_wall, d_wall = self.compute_wall_jump_metrics(horizontal_speed=horiz)
            # add double jump horizontal from remaining potential (very rough)
            # approximate as doubling the double-jump horizontal (this is intentionally conservative)
            _, d_double = self.compute_double_jump_metrics(horizontal_speed=horiz)
            return (d_wall + d_double) + 1e-6 >= gap_px
        else:
            raise ValueError(f"Unknown mode: {mode}")


# Lightweight module-level helpers a map validator might call directly
def can_cross_tiles(profile: PlayerMovementProfile, gap_tiles: int, tile_size: int = 24,
                    mode: str = 'single', use_horizontal: str = 'air') -> bool:
    gap_px = profile.gap_pixels_from_tiles(gap_tiles, tile_size)
    return profile.can_cross_gap(gap_px, mode=mode, use_horizontal=use_horizontal)


# Example usage comment for validators
#
# from src.level.player_movement_profile import PlayerMovementProfile, can_cross_tiles
# p = PlayerMovementProfile.from_defaults_for('knight')
# # single jump
# h, d = p.compute_single_jump_metrics()
# ok = p.can_cross_gap(96, mode='single', use_horizontal='air')
# # tiles
# ok_tiles = can_cross_tiles(p, gap_tiles=4, tile_size=24, mode='double', use_horizontal='air')
