# Procedural Level Generation: Parameters, Quality, and Performance

This document describes the procedural generation configuration, expected behavior, performance characteristics, and best practices. It is aligned with the implemented system:
- [`config.py`](config.py)
- [`seed_manager.py`](seed_manager.py)
- [`generation_algorithms.py`](generation_algorithms.py)
- [`level_generator.py`](level_generator.py)
- [`level_validator.py`](level_validator.py)
- [`menu.py`](menu.py)
- [`main.py`](main.py)
- Test / benchmark suites:
  - [`test_generation.py`](test_generation.py)
  - [`test_validation.py`](test_validation.py)
  - [`test_integration.py`](test_integration.py)
  - [`performance_benchmarks.py`](performance_benchmarks.py)

All automated tests currently pass, and the configuration below is tuned to provide:
- Stable, fast generation (<= 100ms target under typical settings)
- High validation success rate (>= 95% for dungeon/hybrid)
- Playable, varied layouts across seeds and level types
- Clean integration with menu / Game / legacy levels.

---

## 1. Parameter Reference

All parameters are defined in [`config.py`](config.py).

### 1.1 Core Display and Tile

- WIDTH, HEIGHT
  - Screen resolution in pixels (e.g. 960x540).
- TILE
  - Tile size in pixels (24).
- LEVEL_WIDTH, LEVEL_HEIGHT
  - Logical grid size in tiles for generated levels.
  - Current: 40x30 (good balance for visibility, traversal time, and performance).

Recommended:
- Keep LEVEL_WIDTH in [32, 48], LEVEL_HEIGHT in [24, 36].
- Larger sizes increase generation/validation cost and complexity; monitor via [`performance_benchmarks.py`](performance_benchmarks.py).

### 1.2 Generation Mode

- LEVEL_TYPE
  - Default level type.
  - One of: "dungeon", "cave", "outdoor", "hybrid".
- DIFFICULTY
  - Default difficulty: 1 (Easy), 2 (Normal), 3 (Hard).

These can be overridden at runtime via:
- Title screen Generation Options in [`menu.py`](menu.py).
- Calls to LevelGenerator / generate_procedural_level in [`main.py`](main.py).

### 1.3 Structural / Content Parameters

(Declared in [`config.py`](config.py), conceptually used by hybrid algorithms / validator.)

- ROOM_DENSITY
  - Target density of rooms in room-based layouts.
  - Higher → more rooms and corridors, more combat spaces.
- CORRIDOR_WIDTH
  - Logical corridor thickness (in tiles).
  - Wider corridors → better connectivity / flow, easier combat; narrower → more chokepoints.
- ENEMY_DENSITY
  - Global multiplier for enemy placement (used conceptually; real placement logic may live elsewhere).
- TREASURE_DENSITY
  - Similar multiplier for loot/treasure placement.

Recommended baselines:
- ROOM_DENSITY ≈ 0.5–0.7 for "dungeon"/"hybrid".
- CORRIDOR_WIDTH = 2 for readable navigation.
- ENEMY_DENSITY tuned in conjunction with difficulty (see Best Practices).

### 1.4 Terrain Parameters

Used by LevelGenerator’s terrain selection (`_select_wall_terrain`, `_select_floor_terrain`) and validated by [`level_validator.py`](level_validator.py):

- TERRAIN_VARIATION
  - Global 0–1 factor indicating how aggressively to vary terrain.
- SPECIAL_TERRAIN_CHANCE
  - Chance of placing special tiles (e.g. hazards, unique terrain).

Qualitative behavior:
- "dungeon"
  - Mostly NORMAL/ROUGH, focus on clarity and combat readability.
- "cave"
  - More ROUGH/STEEP, organic shapes.
- "outdoor"
  - Mix of NORMAL, ROUGH, MUD, some WATER/ICE.
- "hybrid"
  - Combines dungeon structure with noise-based variation; variety without breaking readability.

### 1.5 Validation Parameters

From [`config.py`](config.py) and [`level_validator.py`](level_validator.py):

- MAX_VALIDATION_ATTEMPTS
  - Max validation/repair cycles per generation.
- REPAIR_ATTEMPTS
  - Max internal repair passes in EnhancedLevelValidator.repair_level().
- GENERATION_TIME_TARGET
  - Soft budget (ms). Tests assert average time stays ≤ this.
- VALIDATION_SUCCESS_RATE
  - Target success rate for dungeon-style levels.

EnhancedLevelValidator thresholds (internal):
- min_spawn_points
- max_empty_ratio
- min_connectivity_ratio
- min_room_size
- max_isolated_tiles_ratio

These drive:
- Connectivity checks
- Room size checks (for room-based types)
- Hazard ratios
- Chokepoint density

---

## 2. Performance Guidelines

Validated via:
- [`test_generation.py`](test_generation.py) performance tests
- [`performance_benchmarks.py`](performance_benchmarks.py)

Key expectations (based on the current configuration):

- Generation Time
  - Average per-level generation: ≤ GENERATION_TIME_TARGET (100ms) for standard sizes (40x30) across level types.
  - 95th percentile: ≤ 2x GENERATION_TIME_TARGET.
- Validation Overhead
  - Typically small relative to generation.
- Memory Usage
  - Estimated in [`performance_benchmarks.py`](performance_benchmarks.py).
  - For 40x30 grid with terrain, comfortably < 10MB per level.

If you see slowdowns or spikes:
- Reduce LEVEL_WIDTH/LEVEL_HEIGHT.
- Simplify HybridGenerator: fewer Perlin octaves, slightly fewer cellular iterations.
- Lower ROOM_DENSITY and complexity of repair logic (fewer tunnels / less post-processing).

---

## 3. Quality Metrics and Guarantees

Quality is enforced via:
- Hybrid generation algorithms in [`generation_algorithms.py`](generation_algorithms.py)
- Enhanced validation in [`level_validator.py`](level_validator.py)
- Integrated tests (`test_generation.py`, `test_validation.py`)

### 3.1 Structural Integrity

Validator checks include:
- Consistent grid dimensions and row lengths.
- Boundary integrity:
  - Limited boundary gaps (exits); excessive gaps are flagged and repairable.
- Connectivity:
  - Main component covers large fraction of floor tiles.
  - Excessive tiny isolated components are flagged.
- Pathfinding:
  - Random pairs of floor tiles must be reachable with sufficient success rate.

Dungeon/hybrid:
- Strict expectations: rooms exist, connectivity >= min_connectivity_ratio.

Cave/outdoor:
- Treated as non-room-based:
  - Tests relax "must have rooms" requirement.
  - Focus on “no critical failure” (no empty grid, some floors, reasonable connectivity).

### 3.2 Gameplay Flow

Validator enforces:
- Valid spawn points:
  - On floor, within bounds, safe from excessive walls and hazards.
- Combat spaces:
  - Enough open areas (≥ 3x3 patches).
  - Not dominated by chokepoints (<= ~5% chokepoint coverage).
- Terrain traversal:
  - Terrain grid consistent with level grid.
  - Hazardous terrain ratio bounded (≤ 20% by default).

### 3.3 Terrain Variety

- Ensures at least some variety of terrain types.
- Flags:
  - Terrain grid dimension mismatch
  - Completely uniform terrain (insufficient variety)

Use TERRAIN_VARIATION and SPECIAL_TERRAIN_CHANCE carefully:
- Too low → visually boring maps.
- Too high → noisy / hard-to-read levels.

### 3.4 Enemy Placement

EnhancedLevelValidator performs structural checks:
- Enemies:
  - Spawn on floor, within bounds.
  - Terrain compatibility based on enemy traits.
  - Reachability to player (pathfinding-based).
- Test suite currently uses these rules primarily as structural guarantees; actual spawning logic may live in gameplay code.

Best practice:
- When adjusting ENEMY_DENSITY or spawn logic, run tests to ensure:
  - No enemies stuck inside walls or hazards.
  - Enemies can generally pathfind or function as intended.

---

## 4. Seed Management and Determinism

Implemented in [`seed_manager.py`](seed_manager.py) and used by [`level_generator.py`](level_generator.py).

Behavior:
- world_seed:
  - Stable across a run; controls all level seeds.
- generate_level_seed(level_index):
  - Derives a deterministic level_seed from world_seed + level_index.
  - Resets sub-seeds / RNG instances for clean per-level determinism.
- generate_sub_seeds(level_seed):
  - Derives deterministic sub-seeds for components: "structure", "terrain", "enemies", "items", "details".
- get_random(component):
  - Returns a cached Random instance seeded from sub_seeds.
  - Ensures consistent usage when used correctly.

Tests:
- [`test_generation.py`](test_generation.py) implements:
  - Determinism smoke checks: enforce high similarity for same seeds/params.
  - Variety checks: different seeds yield distinct layouts.

Note:
- Perfect bit-for-bit determinism is intentionally relaxed in tests to avoid brittleness if repair logic or heuristics evolve.
- If you add new randomness, always source it via SeedManager.get_random(component).

---

## 5. Integration Behavior

Verified by:
- [`test_integration.py`](test_integration.py)

Key scenarios:

- Menu Integration:
  - Title screen Generation Options toggle:
    - Procedural vs static.
    - Level type.
    - Difficulty.
    - World seed (manual or randomized).
  - Stored onto Game instance and used by LevelGenerator.

- Game Integration:
  - Game._load_level in [`main.py`](main.py):
    - If use_procedural:
      - Calls LevelGenerator.generate_level with configured type/difficulty/seed.
      - On success:
        - Wraps into GeneratedLevel (already matching Level API).
        - Updates terrain_system and enemies.
      - On failure:
        - Logs warning and falls back to legacy Level.
    - If not use_procedural:
      - Uses classic [`level.py`](level.py) rooms (backward compatibility).

- Transitions:
  - switch_room/goto_room:
    - Works for both procedural and legacy modes.
    - Clears transient effects appropriately.

- Backward Compatibility:
  - Legacy Level remains functional and is covered by integration tests.
  - Procedural failure routes cleanly to legacy without crashing.

---

## 6. Troubleshooting Guide

Use this section when tests fail, generation looks wrong, or runtime behavior regresses.

1. Failing Determinism / Inconsistent Layouts
   - Symptom:
     - Determinism tests in [`test_generation.py`](test_generation.py) start failing.
   - Causes:
     - Direct uses of random.random / random.randint without SeedManager.
     - Mutable state in generation algorithms not reset per-level.
   - Fix:
     - Route all randomness through SeedManager.get_random("component").
     - Ensure generate_level_seed and generate_sub_seeds are called once per level.

2. Low Validation Success Rate
   - Symptom:
     - validation_success_rate < 95% in [`test_generation.py`](test_generation.py) or [`performance_benchmarks.py`](performance_benchmarks.py).
   - Causes:
     - Overly dense walls / too narrow corridors.
     - Excessive hazards.
     - Misconfigured spawn logic (no/unsafe spawns).
   - Fix:
     - Increase CORRIDOR_WIDTH or adjust ROOM_DENSITY.
     - Reduce hazardous terrain chances.
     - Ensure spawn points are placed in safe, open areas.
     - Optionally relax validator thresholds for specific level types.

3. Performance Regression (Slow Generation)
   - Symptom:
     - Average generation time > GENERATION_TIME_TARGET.
   - Causes:
     - Larger LEVEL_WIDTH/HEIGHT.
     - Extra expensive noise or CA iterations.
   - Fix:
     - Reduce grid size or algorithmic complexity.
     - Re-run [`performance_benchmarks.py`](performance_benchmarks.py).

4. Structural Glitches
   - Symptom:
     - Gaps in boundaries, unreachable areas, weird tunnels.
   - Fix:
     - Check EnhancedLevelValidator suggestions (ValidationResult.suggestions).
     - Use repair_level as needed.
     - Ensure BSP/CA/Perlin steps respect map bounds.

5. Integration / Crash Issues
   - Symptom:
     - Crashes when loading procedural levels, or invalid attributes.
   - Fix:
     - Ensure GeneratedLevel exposes:
       - grid, rooms, spawn_points, solids, doors, enemies, spawn, w, h, is_procedural.
     - Confirm main.py uses GeneratedLevel correctly (already enforced by tests).

---

## 7. Best Practice Recommendations

These settings and patterns have been validated by the automated suite and are recommended defaults.

- Dimensions:
  - 40x30 tiles at TILE=24.
  - Do not exceed 64x48 without re-running performance benchmarks.

- Level Types:
  - "dungeon": Primary, strict validation, best for core runs.
  - "cave": Use for variety; allow organic corridors; rely on relaxed room checks.
  - "outdoor": Use for visual variety; ensure hazards not overused.
  - "hybrid": Use for advanced runs; combine dungeon structure and noise carefully.

- Difficulty:
  - D1: Fewer enemies, simpler shapes (no extra constraints currently; extend via generator as needed).
  - D2: Baseline, tuned to validation and tests.
  - D3: Can increase complexity; keep an eye on connectivity and chokepoints.

- Enemies:
  - Place enemies on safe, reachable tiles.
  - Respect terrain compatibility (flying vs ground, hazards, etc.).
  - Scale ENEMY_DENSITY with difficulty; validate via LevelValidator entity rules.

- Terrain:
  - Keep hazardous terrain under 20% of tiles.
  - Ensure spawn region and key traversal paths favor NORMAL/benign tiles.

- Seeds:
  - Expose world_seed in the UI for reproducibility (already shown in HUD in [`main.py`](main.py)).
  - Encourage bug reports with seed + level_index + type + difficulty so layouts can be reproduced.

---

## 8. How to Use the Tooling

- Run full automated suite:
  - `python -m pytest -q`
- Run performance benchmarks:
  - `python performance_benchmarks.py`
- Inspect specific failures:
  - Use `pytest -vv` to see detailed issue traces.
- Adjust tuning:
  - Edit [`config.py`](config.py) parameters.
  - If structural/validation-related issues appear, refer to this doc and rerun tests.

This setup ensures:
- High-quality, playable procedural levels.
- Measurable guarantees on performance and validation success rate.
- Safe evolution of parameters and algorithms with regression protection.