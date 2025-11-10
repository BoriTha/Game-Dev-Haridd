from dataclasses import dataclass, field
from typing import Optional, Dict, Any
import json
import hashlib
import math

@dataclass(frozen=True)
class PhysicsAttributes:
    g: float
    v0: float
    v_term: float

@dataclass(frozen=True)
class AirControlAttributes:
    accel: float
    vx_max: float
    friction: float
    wall_control_mult: float

@dataclass(frozen=True)
class DashAttributes:
    v: float
    frames: int
    uses: int
    allowed_in_air: bool

@dataclass(frozen=True)
class Footprint:
    width: int
    height: int

@dataclass(frozen=True)
class MovementAttributes:
    tile_px: int
    fps: int
    physics: PhysicsAttributes
    air_control: AirControlAttributes
    coyote_frames: int
    dash: DashAttributes
    footprint_tiles: Footprint
    baseline_class: str
    caps_derived: Optional[Dict[str, Any]] = field(default=None, compare=False)
    motion_version: Optional[str] = field(default=None, compare=False)

    def __post_init__(self):
        caps, version = self._compute_derived_caps_and_version()
        # Use object.__setattr__ to assign to frozen fields
        object.__setattr__(self, 'caps_derived', caps)
        object.__setattr__(self, 'motion_version', version)

    def _compute_derived_caps_and_version(self):
        # --- Physics Calculations (Discrete Simulation) ---
        caps = {}

        # Vertical Jump Simulation
        y, vy = 0.0, self.physics.v0
        t_apex = 0
        while vy < 0:
            y += vy
            vy += self.physics.g
            t_apex += 1
        
        # Use floor (int conversion of positive float) for tiles fully cleared
        caps['max_upstep_tiles'] = int(abs(y / self.tile_px))

        # Horizontal Movement Simulation (during a full jump)
        t_flight = t_apex * 2  # Approximation for jump from/to same height
        vx = 0.0
        x = 0.0
        for _ in range(t_flight):
            vx += self.air_control.accel
            vx *= self.air_control.friction  # Apply friction
            if vx > self.air_control.vx_max:
                vx = self.air_control.vx_max
            x += vx
        
        coyote_drift_px = self.coyote_frames * self.air_control.vx_max
        
        # Use floor to get the number of full tiles crossed
        caps['max_gap_no_dash_tiles'] = int((x + coyote_drift_px) / self.tile_px)

        dash_px = self.dash.v * self.dash.frames
        caps['max_gap_with_dash_tiles'] = int((x + coyote_drift_px + dash_px) / self.tile_px)
        
        # --- Simplified estimations for other caps based on requirements ---
        # These would require more complex simulations (e.g., for wall jumps or specific ledge grab scenarios)
        # For now, we'll use the recommended values as placeholders to show the structure.
        caps['alt_ledge_step_v_tiles'] = 3
        caps['alt_ledge_step_h_tiles'] = 2
        caps['headroom_tiles'] = self.footprint_tiles.height
        caps['landing_len_tiles'] = 2
        caps['long_gap_landing_tiles'] = 3


        # --- Versioning ---
        # Create a dictionary of the core attributes for hashing
        core_attrs = {
            'tile_px': self.tile_px,
            'fps': self.fps,
            'physics': self.physics.__dict__,
            'air_control': self.air_control.__dict__,
            'coyote_frames': self.coyote_frames,
            'dash': self.dash.__dict__,
            'footprint_tiles': self.footprint_tiles.__dict__,
            'baseline_class': self.baseline_class,
        }
        # Use sorted keys to ensure consistent hash
        core_attrs_str = json.dumps(core_attrs, sort_keys=True)
        version_hash = hashlib.sha256(core_attrs_str.encode('utf-8')).hexdigest()
        
        return caps, f"m-{version_hash[:12]}"


def load_movement_attributes(
    tile_px, fps, physics, air_control, coyote_frames, dash, footprint_tiles, baseline_class
):
    """Factory to create and compute MovementAttributes."""
    return MovementAttributes(
        tile_px=tile_px,
        fps=fps,
        physics=PhysicsAttributes(**physics),
        air_control=AirControlAttributes(**air_control),
        coyote_frames=coyote_frames,
        dash=DashAttributes(**dash),
        footprint_tiles=Footprint(**footprint_tiles),
        baseline_class=baseline_class,
    )

# --- Test Block ---
if __name__ == "__main__":
    # Inputs from the requirements
    knight_attrs_inputs = {
        "tile_px": 24,
        "fps": 60,
        "physics": {"g": 0.45, "v0": -10.2, "v_term": 18},
        "air_control": {"accel": 0.4, "vx_max": 5.5, "friction": 0.98, "wall_control_mult": 1.5},
        "coyote_frames": 8,
        "dash": {"v": 12, "frames": 10, "uses": 1, "allowed_in_air": True},
        "footprint_tiles": {"width": 1, "height": 2},
        "baseline_class": "Knight",
    }

    print("--- Loading Movement Attributes for 'Knight' ---")
    knight_movement = load_movement_attributes(**knight_attrs_inputs)
    
    print("\n--- Generated MovementAttributes Instance ---")
    print(knight_movement)

    print("\n--- Verifying Immutability ---")
    try:
        knight_movement.fps = 120
    except Exception as e:
        print(f"Successfully caught error when trying to modify a frozen attribute: {e}")

    print("\n--- Final Computed Capabilities ---")
    if knight_movement.caps_derived:
        for key, computed_val in knight_movement.caps_derived.items():
            print(f"  - {key}: {computed_val}")

