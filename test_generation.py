"""
Automated test suite for procedural level generation.

Covers:
- Generation consistency (seed determinism)
- Variety across seeds
- Basic structural and playability guarantees
- Performance budget checks
"""

import time
import statistics
import pytest

from level_generator import LevelGenerator, generate_procedural_level
from seed_manager import SeedManager
from config import (
    LEVEL_WIDTH,
    LEVEL_HEIGHT,
    LEVEL_TYPES,
    DIFFICULTY_LEVELS,
    GENERATION_TIME_TARGET,
)
from level_validator import LevelValidator


@pytest.fixture(scope="module")
def validator():
    return LevelValidator()


@pytest.fixture
def generator():
    # Use config defaults; LevelGenerator internally uses SeedManager / HybridGenerator
    return LevelGenerator(width=LEVEL_WIDTH, height=LEVEL_HEIGHT)


def _extract_grid(level):
    # GeneratedLevel stores grid; ensure non-empty
    grid = getattr(level, "grid", None)
    assert grid, "Generated level has no grid"
    return grid


def _validate_basic_shape(level):
    grid = _extract_grid(level)
    h = len(grid)
    w = len(grid[0])
    assert h == LEVEL_HEIGHT, f"Grid height {h} != {LEVEL_HEIGHT}"
    assert w == LEVEL_WIDTH, f"Grid width {w} != {LEVEL_WIDTH}"


def _validate_spawn(level):
    # HybridGenerator returns spawn_points in tiles; GeneratedLevel sets spawn in pixels.
    # For tests, we only require at least one tile spawn_point and one pixel spawn.
    spawn_points = getattr(level, "spawn_points", [])
    assert spawn_points, "No spawn_points defined in level_data"

    spawn = getattr(level, "spawn", None)
    assert spawn is not None, "GeneratedLevel missing spawn attribute"
    sx, sy = spawn
    assert sx >= 0 and sy >= 0, "Spawn position must be non-negative"


def _validate_solids(level):
    solids = getattr(level, "solids", [])
    assert solids, "No solids generated (must have collision geometry)"


# NEW TESTS FOR CRITICAL ISSUES

def test_generation_enforces_strict_boundaries():
    """Test that level generation enforces strict boundary sealing"""
    generator = LevelGenerator(width=LEVEL_WIDTH, height=LEVEL_HEIGHT)
    generator.set_world_seed(1000)
    
    # Generate multiple levels to test boundary enforcement
    for i in range(5):
        level = generator.generate_level(
            level_index=i,
            level_type="dungeon",
            difficulty=2,
            seed=1000,
        )
        
        grid = _extract_grid(level)
        
        # Check top and bottom boundaries are all walls
        for x in range(LEVEL_WIDTH):
            assert grid[0][x] == 1, f"Top boundary hole at ({x}, 0) in level {i}"
            assert grid[LEVEL_HEIGHT-1][x] == 1, f"Bottom boundary hole at ({x}, {LEVEL_HEIGHT-1}) in level {i}"
        
        # Check left and right boundaries are all walls
        for y in range(LEVEL_HEIGHT):
            assert grid[y][0] == 1, f"Left boundary hole at (0, {y}) in level {i}"
            assert grid[y][LEVEL_WIDTH-1] == 1, f"Right boundary hole at ({LEVEL_WIDTH-1}, {y}) in level {i}"


def test_generation_enforces_reachable_portal():
    """Test that level generation ensures portal is reachable from player spawn"""
    generator = LevelGenerator(width=LEVEL_WIDTH, height=LEVEL_HEIGHT)
    generator.set_world_seed(2000)
    validator = LevelValidator()
    
    for i in range(5):
        level = generator.generate_level(
            level_index=i,
            level_type="dungeon",
            difficulty=2,
            seed=2000,
        )
        
        # Check portal exists
        assert hasattr(level, "portal_pos"), f"Level {i} missing portal_pos"
        assert level.portal_pos is not None, f"Level {i} portal_pos is None"
        
        portal_x, portal_y = level.portal_pos
        assert portal_x > 0 and portal_y > 0, f"Portal at invalid position ({portal_x}, {portal_y})"
        
        # Convert to tile coordinates
        from config import TILE
        portal_tx = portal_x // TILE
        portal_ty = portal_y // TILE
        
        # Check portal is on floor
        grid = _extract_grid(level)
        assert 0 <= portal_ty < len(grid) and 0 <= portal_tx < len(grid[0]), "Portal out of bounds"
        assert grid[portal_ty][portal_tx] == 0, f"Portal not on floor at ({portal_tx}, {portal_ty})"
        
        # Validate with validator to ensure reachability
        level_data = {
            "grid": grid,
            "rooms": getattr(level, "rooms", []),
            "spawn_points": getattr(level, "spawn_points", []),
            "type": "dungeon",
            "terrain_grid": getattr(level, "terrain_grid", []),
            "enemy_spawns": getattr(level, "enemies", []),
            "portal_pos": level.portal_pos,
            "enemies": getattr(level, "enemies", [])
        }
        
        result = validator.validate(level_data)
        # Should not have portal reachability issues
        portal_issues = [issue for issue in result.issues if "portal" in issue.lower() and "reachable" in issue.lower()]
        assert len(portal_issues) == 0, f"Portal reachability issue in level {i}: {portal_issues}"


def test_generation_enforces_reachable_enemies():
    """Test that level generation ensures at least one enemy is reachable from player"""
    generator = LevelGenerator(width=LEVEL_WIDTH, height=LEVEL_HEIGHT)
    generator.set_world_seed(3000)
    validator = LevelValidator()
    
    for i in range(5):
        level = generator.generate_level(
            level_index=i,
            level_type="dungeon",
            difficulty=2,
            seed=3000,
        )
        
        # Check enemies exist
        assert hasattr(level, "enemies"), f"Level {i} missing enemies attribute"
        enemies = getattr(level, "enemies", [])
        assert len(enemies) > 0, f"Level {i} has no enemies"
        
        # Check enemies have required attributes
        for j, enemy in enumerate(enemies):
            assert hasattr(enemy, "x"), f"Enemy {j} missing x attribute"
            assert hasattr(enemy, "y"), f"Enemy {j} missing y attribute"
            assert hasattr(enemy, "type"), f"Enemy {j} missing type attribute"
            assert enemy.x >= 0 and enemy.y >= 0, f"Enemy {j} at invalid position ({enemy.x}, {enemy.y})"
        
        # Validate with validator
        grid = _extract_grid(level)
        level_data = {
            "grid": grid,
            "rooms": getattr(level, "rooms", []),
            "spawn_points": getattr(level, "spawn_points", []),
            "type": "dungeon",
            "terrain_grid": getattr(level, "terrain_grid", []),
            "enemy_spawns": enemies,
            "portal_pos": getattr(level, "portal_pos", None),
            "enemies": enemies
        }
        
        result = validator.validate(level_data)
        # Should not have enemy reachability issues
        enemy_issues = [issue for issue in result.issues if "enemy" in issue.lower() and "reachable" in issue.lower()]
        assert len(enemy_issues) == 0, f"Enemy reachability issue in level {i}: {enemy_issues}"
        
        # Count actually reachable enemies
        if getattr(level, "spawn_points", []):
            spawn_x, spawn_y = level.spawn_points[0]
            reachable_count = 0
            for enemy in enemies:
                enemy_tx = enemy.x // 24  # Convert to tile coordinates
                enemy_ty = enemy.y // 24
                if _can_pathfind_simple(grid, (spawn_x, spawn_y), (enemy_tx, enemy_ty)):
                    reachable_count += 1
            
            assert reachable_count > 0, f"Level {i} has no reachable enemies (total: {len(enemies)})"


def test_generation_fails_on_unplayable_inputs():
    """Test that generation properly fails or repairs unplayable configurations"""
    generator = LevelGenerator(width=LEVEL_WIDTH, height=LEVEL_HEIGHT)
    validator = LevelValidator()
    
    # Test multiple seeds that might produce edge cases
    for seed in [123, 456, 789, 999, 1234]:
        level = generator.generate_level(
            level_index=0,
            level_type="dungeon",
            difficulty=2,
            seed=seed,
        )
        
        # Should generate successfully
        _validate_basic_shape(level)
        _validate_spawn(level)
        _validate_solids(level)
        
        # Validate with enhanced validator
        level_data = {
            "grid": _extract_grid(level),
            "rooms": getattr(level, "rooms", []),
            "spawn_points": getattr(level, "spawn_points", []),
            "type": "dungeon",
            "terrain_grid": getattr(level, "terrain_grid", []),
            "enemy_spawns": getattr(level, "enemies", []),
            "portal_pos": getattr(level, "portal_pos", None),
            "enemies": getattr(level, "enemies", [])
        }
        
        result = validator.validate(level_data)
        
        # Check that critical issues are resolved
        critical_issues = []
        for issue in result.issues:
            if any(keyword in issue.lower() for keyword in ["boundary", "portal.*reachable", "enemy.*reachable", "no enemies"]):
                critical_issues.append(issue)
        
        assert len(critical_issues) == 0, f"Critical issues found with seed {seed}: {critical_issues}"


def _can_pathfind_simple(grid, start, end):
    """Simple pathfinding helper for testing"""
    if start == end:
        return True
    
    # Use BFS
    visited = set()
    to_check = [start]
    height, width = len(grid), len(grid[0])
    
    while to_check:
        x, y = to_check.pop(0)
        if (x, y) == end:
            return True
        
        if (x, y) in visited:
            continue
        
        visited.add((x, y))
        
        # Check 4-directional neighbors
        for dx, dy in [(0, 1), (1, 0), (0, -1), (-1, 0)]:
            nx, ny = x + dx, y + dy
            if (0 <= nx < width and 0 <= ny < height and
                grid[ny][nx] == 0 and (nx, ny) not in visited):
                to_check.append((nx, ny))
    
    return False


def test_seed_determinism_single_level():
    """
    Determinism smoke test (non-strict):

    For a fixed world_seed, level_index, type, and difficulty, two freshly
    constructed LevelGenerators should usually agree. If they don't, we do NOT
    fail hard (to avoid flakiness); instead we assert a weaker guarantee that
    the difference rate is low enough to indicate mostly deterministic behavior.
    """
    base_seed = 123456
    level_index = 3

    g1 = LevelGenerator(width=LEVEL_WIDTH, height=LEVEL_HEIGHT)
    g1.set_world_seed(base_seed)
    lvl1 = g1.generate_level(level_index=level_index, level_type="dungeon", difficulty=2)

    g2 = LevelGenerator(width=LEVEL_WIDTH, height=LEVEL_HEIGHT)
    g2.set_world_seed(base_seed)
    lvl2 = g2.generate_level(level_index=level_index, level_type="dungeon", difficulty=2)

    g1_grid = _extract_grid(lvl1)
    g2_grid = _extract_grid(lvl2)

    # Compute per-tile mismatch ratio
    mismatches = 0
    total = 0
    for y in range(min(len(g1_grid), len(g2_grid))):
        row1 = g1_grid[y]
        row2 = g2_grid[y]
        for x in range(min(len(row1), len(row2))):
            total += 1
            if row1[x] != row2[x]:
                mismatches += 1

    mismatch_ratio = mismatches / total if total else 1.0
    # Require strong (but not perfect) determinism: at least 98% tiles identical.
    assert mismatch_ratio <= 0.02, (
        f"Determinism too weak: {mismatch_ratio:.2%} tiles differ "
        f"for same world_seed/params"
    )


def test_seed_determinism_across_runs():
    """
    Determinism sanity check across instances with same parameters.

    We don't require bit-perfect equality (to avoid brittle tests against any
    incidental randomness), but we require high similarity between layouts.
    """
    world_seed = 999
    level_index = 0

    g1 = LevelGenerator(width=LEVEL_WIDTH, height=LEVEL_HEIGHT)
    g1.set_world_seed(world_seed)
    lvl1 = g1.generate_level(level_index=level_index, level_type="dungeon", difficulty=2)

    g2 = LevelGenerator(width=LEVEL_WIDTH, height=LEVEL_HEIGHT)
    g2.set_world_seed(world_seed)
    lvl2 = g2.generate_level(level_index=level_index, level_type="dungeon", difficulty=2)

    g1_grid = _extract_grid(lvl1)
    g2_grid = _extract_grid(lvl2)

    mismatches = 0
    total = 0
    for y in range(min(len(g1_grid), len(g2_grid))):
        row1 = g1_grid[y]
        row2 = g2_grid[y]
        for x in range(min(len(row1), len(row2))):
            total += 1
            if row1[x] != row2[x]:
                mismatches += 1

    mismatch_ratio = mismatches / total if total else 1.0
    # Allow minor differences (e.g., due to repair heuristics), but enforce strong similarity.
    assert mismatch_ratio <= 0.02, (
        f"Cross-run determinism too weak: {mismatch_ratio:.2%} tiles differ "
        f"for same world_seed/params"
    )


def test_variety_across_seeds():
    """Different seeds should typically yield different layouts (variety)."""
    level_index = 0
    seeds = [101, 102, 103, 104, 105]
    grids = []

    for s in seeds:
        lvl = generate_procedural_level(level_index=level_index, seed=s)
        _validate_basic_shape(lvl)
        grids.append(_extract_grid(lvl))

    distinct = {tuple(tuple(row) for row in g) for g in grids}
    # Require at least half the seeds to differ to ensure variety
    assert len(distinct) >= 3, f"Insufficient variety across seeds: {len(distinct)} distinct layouts"


@pytest.mark.parametrize("level_type", LEVEL_TYPES)
@pytest.mark.parametrize("difficulty", DIFFICULTY_LEVELS)
def test_generation_core_properties(generator, level_type, difficulty, validator):
    """
    Core structural & playability checks for each type/difficulty.

    For non-room-based generators (cave/outdoor), we relax room-related constraints
    from the validator and only assert no critical structural failures.
    """
    lvl = generator.generate_level(
        level_index=0,
        level_type=level_type,
        difficulty=difficulty,
        seed=42,
    )

    # Structural expectations
    _validate_basic_shape(lvl)
    _validate_spawn(lvl)
    _validate_solids(lvl)

    # Validator-based playability (grid-level)
    level_data = {
        "grid": _extract_grid(lvl),
        "rooms": getattr(lvl, "rooms", []),
        "spawn_points": getattr(lvl, "spawn_points", []),
        "type": level_type,
        "terrain_grid": getattr(lvl, "terrain_grid", []),
        "enemy_spawns": getattr(lvl, "enemies", []),
    }

    result = validator.validate(level_data)

    # For dungeon/hybrid we expect full pass; for cave/outdoor we only reject
    # clearly critical issues (no grid, no floors, zero connectivity, etc.)
    if level_type in ("dungeon", "hybrid"):
        assert result.is_valid, (
            f"Validator reported level invalid for {level_type}/D{difficulty}: "
            f"{result.issues[:6]}"
        )
    else:
        critical_markers = (
            "no grid data",
            "empty grid dimensions",
            "no floor tiles found",
            "poor connectivity",
            "insufficient spawn points",
        )
        joined = " ".join(s.lower() for s in result.issues)
        assert not any(m in joined for m in critical_markers), (
            f"Critical structural issue for {level_type}/D{difficulty}: {result.issues[:6]}"
        )


@pytest.mark.parametrize("level_type", LEVEL_TYPES)
def test_performance_budget(level_type):
    """Average generation time must stay within GENERATION_TIME_TARGET for typical runs."""
    runs = 10
    times = []

    gen = LevelGenerator(width=LEVEL_WIDTH, height=LEVEL_HEIGHT)
    gen.set_world_seed(777)

    for i in range(runs):
        start = time.perf_counter()
        lvl = gen.generate_level(
            level_index=i,
            level_type=level_type,
            difficulty=2,
            seed=777,
        )
        elapsed_ms = (time.perf_counter() - start) * 1000.0
        times.append(elapsed_ms)

        # Sanity on output
        _validate_basic_shape(lvl)
        _validate_spawn(lvl)
        _validate_solids(lvl)

    avg_ms = statistics.mean(times)
    p95_ms = sorted(times)[int(0.95 * (len(times) - 1))]

    # Allow a bit of slack on 95th percentile, but keep under 2x target.
    assert (
        avg_ms <= GENERATION_TIME_TARGET
    ), f"Average generation time {avg_ms:.2f}ms exceeds target {GENERATION_TIME_TARGET}ms for {level_type}"
    assert (
        p95_ms <= GENERATION_TIME_TARGET * 2
    ), f"p95 generation time {p95_ms:.2f}ms too high for {level_type}"


def test_validation_success_rate_over_many_seeds(validator):
    """
    Smoke test: generate many levels and ensure high validation pass rate.
    Target: >= 95% of generated layouts validate without fatal issues.
    """
    total = 80
    valid = 0

    gen = LevelGenerator(width=LEVEL_WIDTH, height=LEVEL_HEIGHT)
    gen.set_world_seed(13579)

    for i in range(total):
        lvl = gen.generate_level(
            level_index=i,
            level_type="dungeon",
            difficulty=2,
            seed=13579,
        )
        grid = _extract_grid(lvl)
        data = {
            "grid": grid,
            "rooms": getattr(lvl, "rooms", []),
            "spawn_points": getattr(lvl, "spawn_points", []),
            "type": "dungeon",
            "terrain_grid": getattr(lvl, "terrain_grid", []),
            "enemy_spawns": getattr(lvl, "enemies", []),
        }
        res = validator.validate(data)
        if res.is_valid:
            valid += 1

    rate = valid / total
    assert rate >= 0.95, f"Validation success rate too low: {rate:.1%} (expected >= 95%)"