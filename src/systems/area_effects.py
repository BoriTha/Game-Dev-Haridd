from typing import Dict, List, Tuple, Any
from src.level.level_loader import level_loader
from src.level.pcg_level_data import AreaRegion


class AreaEffectsSystem:
    """Simple area effects system.

    Usage:
    - Create a single instance and call `update_entity(entity, dt)` for each
      entity each tick (or iterate entities and call update_entity).
    - Entities should expose `tile_x`, `tile_y`, `level_id`, `room_code` and
      optionally methods `apply_damage(amount)`, `apply_slow(pct, duration)`,
      `apply_heal(amount)`.
    """

    def __init__(self):
        # cache: (level_id, room_code) -> tile_map
        self._room_tile_maps: Dict[Tuple[int, str], Dict[Tuple[int, int], List[AreaRegion]]] = {}

    def ensure_room_map(self, level_id: int, room_code: str) -> None:
        key = (level_id, room_code)
        if key not in self._room_tile_maps:
            self._room_tile_maps[key] = level_loader.build_room_tile_region_map(level_id, room_code)

    def get_regions_for_entity_tile(self, level_id: int, room_code: str, tx: int, ty: int) -> List[AreaRegion]:
        self.ensure_room_map(level_id, room_code)
        tilemap = self._room_tile_maps.get((level_id, room_code), {})
        return tilemap.get((tx, ty), [])

    def update_entity(self, entity: Any, dt: float) -> None:
        if not hasattr(entity, "tile_x") or not hasattr(entity, "tile_y") or not hasattr(entity, "level_id") or not hasattr(entity, "room_code"):
            return
        tx, ty = entity.tile_x, entity.tile_y
        regs = self.get_regions_for_entity_tile(entity.level_id, entity.room_code, tx, ty)
        for reg in regs:
            self._apply_region_effect(entity, reg, dt)

    def _apply_region_effect(self, entity: Any, region: AreaRegion, dt: float) -> None:
        props = region.properties or {}
        effect = props.get("effect")
        if effect == "damage_over_time":
            dps = float(props.get("dps", 1.0))
            if hasattr(entity, "apply_damage"):
                try:
                    entity.apply_damage(dps * dt)
                except Exception:
                    pass
        elif effect == "slow":
            pct = float(props.get("slow_percent", 0.5))
            if hasattr(entity, "apply_slow"):
                try:
                    entity.apply_slow(pct, duration=None)
                except Exception:
                    pass
        elif effect == "heal_over_time":
            hps = float(props.get("hps", 1.0))
            if hasattr(entity, "apply_heal"):
                try:
                    entity.apply_heal(hps * dt)
                except Exception:
                    pass
        # Additional effect types (light, ambient_sound, buffs) can be read by
        # render/audio systems by inspecting region.properties.

    def clear_cache_for_room(self, level_id: int, room_code: str) -> None:
        self._room_tile_maps.pop((level_id, room_code), None)
