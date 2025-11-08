"""
Integration tests for the procedural generation system.

Focus:
- End-to-end generation via LevelGenerator and generate_procedural_level
- Menu/Game configuration integration (without opening real windows)
- Backward compatibility: legacy Level fallback remains functional
- Graceful behavior when generation fails
- Full generation + validation pipeline testing
- Testing the three critical fixes: boundary, portal, enemies
"""

import types

from level_generator import (
    LevelGenerator,
    GeneratedLevel,
    generate_procedural_level,
)
from level import Level as LegacyLevel
from level_validator import LevelValidator
from menu import Menu
from main import Game
from config import (
    LEVEL_WIDTH,
    LEVEL_HEIGHT,
    LEVEL_TYPE,
    DIFFICULTY,
    TILE,
)


def _assert_generated_level_shape(level: GeneratedLevel):
    assert isinstance(level, GeneratedLevel)
    assert level.grid, "GeneratedLevel.grid is empty"
    h = len(level.grid)
    w = len(level.grid[0])
    assert h == LEVEL_HEIGHT, f"Generated grid height {h} != {LEVEL_HEIGHT}"
    assert w == LEVEL_WIDTH, f"Generated grid width {w} != {LEVEL_WIDTH}"
    assert hasattr(level, "solids") and level.solids, "GeneratedLevel must expose solids"
    assert hasattr(level, "spawn"), "GeneratedLevel must expose spawn"
    assert hasattr(level, "doors"), "GeneratedLevel must expose doors"
    assert isinstance(level.w, int) and isinstance(level.h, int)


def test_generate_procedural_level_function():
    """Smoke test the convenience wrapper used by external systems."""
    level = generate_procedural_level(
        level_index=0,
        level_type=LEVEL_TYPE,
        difficulty=DIFFICULTY,
        seed=42,
    )
    _assert_generated_level_shape(level)


def test_level_generator_end_to_end():
    """Direct LevelGenerator end-to-end generation with validation/terrain."""
    gen = LevelGenerator(width=LEVEL_WIDTH, height=LEVEL_HEIGHT)
    gen.set_world_seed(1234)

    lvl = gen.generate_level(
        level_index=1,
        level_type="dungeon",
        difficulty=2,
        seed=1234,
    )
    _assert_generated_level_shape(lvl)

    # Ensure stats are populated
    stats = gen.get_generation_stats()
    assert "generation_time_ms" in stats
    assert "validation_attempts" in stats
    assert "world_seed" in stats
    assert "seed_info" in stats


# NEW INTEGRATION TESTS FOR CRITICAL FIXES

def test_generation_pipeline_critical_fixes():
    """Test that the full generation pipeline produces levels that pass all critical validations"""
    gen = LevelGenerator(width=LEVEL_WIDTH, height=LEVEL_HEIGHT)
    gen.set_world_seed(999)
    validator = LevelValidator()
    
    # Test multiple configurations
    for level_type in ["dungeon", "hybrid"]:
        for difficulty in [1, 2, 3]:
            level = gen.generate_level(
                level_index=0,
                level_type=level_type,
                difficulty=difficulty,
                seed=999,
            )
            
            # Test basic shape
            _assert_generated_level_shape(level)
            
            # Test that level has required attributes
            assert hasattr(level, "spawn_points"), "GeneratedLevel missing spawn_points"
            assert hasattr(level, "enemies"), "GeneratedLevel missing enemies attribute"
            assert hasattr(level, "portal_pos"), "GeneratedLevel missing portal_pos"
            
            # Create validation data
            level_data = {
                "grid": level.grid,
                "rooms": getattr(level, "rooms", []),
                "spawn_points": level.spawn_points,
                "type": level_type,
                "terrain_grid": getattr(level, "terrain_grid", []),
                "enemy_spawns": level.enemies,
                "portal_pos": level.portal_pos,
                "enemies": level.enemies
            }
            
            # Validate the level
            result = validator.validate(level_data)
            
            # Should pass all critical validations
            assert result.is_valid, (
                f"Generated level failed validation for {level_type}/D{difficulty}: {result.issues[:5]}"
            )
            
            # Check that no critical issues are present
            issues_text = " ".join(result.issues).lower()
            assert "boundary" not in issues_text or "sealed" in issues_text, "Boundary issues found"
            assert "portal" not in issues_text or "not reachable" not in issues_text, "Portal reachability issues found"
            assert "enemy" not in issues_text or "reachable" not in issues_text, "Enemy reachability issues found"


def test_generation_with_enforced_boundary_sealing():
    """Test that generation now enforces strict boundary sealing"""
    gen = LevelGenerator(width=LEVEL_WIDTH, height=LEVEL_HEIGHT)
    gen.set_world_seed(123)
    validator = LevelValidator()
    
    # Generate multiple levels
    for i in range(10):
        level = gen.generate_level(
            level_index=i,
            level_type="dungeon",
            difficulty=2,
            seed=123,
        )
        
        grid = level.grid
        assert len(grid) == LEVEL_HEIGHT
        assert len(grid[0]) == LEVEL_WIDTH
        
        # Check all boundaries are sealed
        # Top and bottom boundaries
        for x in range(LEVEL_WIDTH):
            assert grid[0][x] == 1, f"Top boundary hole at ({x}, 0) in level {i}"
            assert grid[LEVEL_HEIGHT-1][x] == 1, f"Bottom boundary hole at ({x}, {LEVEL_HEIGHT-1}) in level {i}"
        
        # Left and right boundaries
        for y in range(LEVEL_HEIGHT):
            assert grid[y][0] == 1, f"Left boundary hole at (0, {y}) in level {i}"
            assert grid[y][LEVEL_WIDTH-1] == 1, f"Right boundary hole at ({LEVEL_WIDTH-1}, {y}) in level {i}"
        
        # Validate with validator
        level_data = {
            "grid": grid,
            "rooms": getattr(level, "rooms", []),
            "spawn_points": level.spawn_points,
            "type": "dungeon",
            "terrain_grid": getattr(level, "terrain_grid", []),
            "enemy_spawns": level.enemies,
            "portal_pos": level.portal_pos,
            "enemies": level.enemies
        }
        
        result = validator.validate(level_data)
        assert result.is_valid, f"Level {i} failed validation: {result.issues[:3]}"


def test_generation_with_reachable_portal():
    """Test that generation ensures portal is reachable from player spawn"""
    gen = LevelGenerator(width=LEVEL_WIDTH, height=LEVEL_HEIGHT)
    gen.set_world_seed(456)
    validator = LevelValidator()
    
    for i in range(5):
        level = gen.generate_level(
            level_index=i,
            level_type="dungeon",
            difficulty=2,
            seed=456,
        )
        
        # Check portal exists and is accessible
        assert hasattr(level, "portal_pos"), f"Level {i} missing portal_pos"
        assert level.portal_pos is not None, f"Level {i} portal_pos is None"
        portal_x, portal_y = level.portal_pos
        assert portal_x > 0 and portal_y > 0, f"Portal at invalid position ({portal_x}, {portal_y})"
        
        # Convert to tile coordinates for validation
        portal_tx = portal_x // TILE
        portal_ty = portal_y // TILE
        assert 0 <= portal_tx < LEVEL_WIDTH, f"Portal X out of bounds: {portal_tx}"
        assert 0 <= portal_ty < LEVEL_HEIGHT, f"Portal Y out of bounds: {portal_ty}"
        
        # Check portal is on floor
        assert level.grid[portal_ty][portal_tx] == 0, f"Portal not on floor at ({portal_tx}, {portal_ty})"
        
        # Validate with strict portal reachability
        level_data = {
            "grid": level.grid,
            "rooms": getattr(level, "rooms", []),
            "spawn_points": level.spawn_points,
            "type": "dungeon",
            "terrain_grid": getattr(level, "terrain_grid", []),
            "enemy_spawns": level.enemies,
            "portal_pos": level.portal_pos,
            "enemies": level.enemies
        }
        
        result = validator.validate(level_data)
        assert result.is_valid, f"Level {i} portal reachability failed: {result.issues[:3]}"


def test_generation_with_reachable_enemies():
    """Test that generation ensures at least one enemy is reachable from player"""
    gen = LevelGenerator(width=LEVEL_WIDTH, height=LEVEL_HEIGHT)
    gen.set_world_seed(789)
    validator = LevelValidator()
    
    for i in range(5):
        level = gen.generate_level(
            level_index=i,
            level_type="dungeon",
            difficulty=2,
            seed=789,
        )
        
        # Check enemies exist
        assert hasattr(level, "enemies"), f"Level {i} missing enemies"
        assert len(level.enemies) > 0, f"Level {i} has no enemies"
        
        # Check all enemies have required attributes
        for j, enemy in enumerate(level.enemies):
            assert hasattr(enemy, "x"), f"Enemy {j} missing x attribute"
            assert hasattr(enemy, "y"), f"Enemy {j} missing y attribute"
            assert hasattr(enemy, "type"), f"Enemy {j} missing type attribute"
            assert enemy.x > 0 and enemy.y > 0, f"Enemy {j} at invalid position ({enemy.x}, {enemy.y})"
        
        # Validate with strict enemy reachability
        level_data = {
            "grid": level.grid,
            "rooms": getattr(level, "rooms", []),
            "spawn_points": level.spawn_points,
            "type": "dungeon",
            "terrain_grid": getattr(level, "terrain_grid", []),
            "enemy_spawns": level.enemies,
            "portal_pos": level.portal_pos,
            "enemies": level.enemies
        }
        
        result = validator.validate(level_data)
        assert result.is_valid, f"Level {i} enemy reachability failed: {result.issues[:3]}"
        
        # Count reachable enemies
        if level.spawn_points:
            spawn_x, spawn_y = level.spawn_points[0]
            reachable_count = 0
            for enemy in level.enemies:
                enemy_tx = enemy.x // TILE
                enemy_ty = enemy.y // TILE
                if _can_pathfind(level.grid, (spawn_x, spawn_y), (enemy_tx, enemy_ty)):
                    reachable_count += 1
            
            assert reachable_count > 0, f"Level {i} has no reachable enemies (total: {len(level.enemies)})"


def test_generated_level_data_structure():
    """Test that GeneratedLevel objects have proper data structure for validation"""
    level = generate_procedural_level(
        level_index=0,
        level_type="dungeon",
        difficulty=2,
        seed=555,
    )
    
    # Test required attributes
    required_attrs = [
        "grid", "solids", "spawn", "doors", "spawn_points",
        "enemies", "portal_pos", "terrain_grid", "rooms"
    ]
    
    for attr in required_attrs:
        assert hasattr(level, attr), f"GeneratedLevel missing {attr} attribute"
    
    # Test attribute types and basic validity
    assert isinstance(level.grid, list), "grid should be a list"
    assert isinstance(level.enemies, list), "enemies should be a list"
    assert isinstance(level.spawn_points, list), "spawn_points should be a list"
    assert isinstance(level.portal_pos, tuple), "portal_pos should be a tuple"
    assert len(level.portal_pos) == 2, "portal_pos should be a 2-tuple"
    
    # Test grid dimensions
    assert len(level.grid) == LEVEL_HEIGHT, f"Grid height should be {LEVEL_HEIGHT}"
    if len(level.grid) > 0:
        assert len(level.grid[0]) == LEVEL_WIDTH, f"Grid width should be {LEVEL_WIDTH}"
    
    # Test that spawn_points contain valid coordinates
    for sp in level.spawn_points:
        assert isinstance(sp, tuple), "Spawn point should be a tuple"
        assert len(sp) == 2, "Spawn point should be a 2-tuple"
        assert 0 <= sp[0] < LEVEL_WIDTH, f"Spawn X out of bounds: {sp[0]}"
        assert 0 <= sp[1] < LEVEL_HEIGHT, f"Spawn Y out of bounds: {sp[1]}"
    
    # Test that enemies have valid pixel coordinates
    for enemy in level.enemies:
        assert isinstance(enemy.x, (int, float)), f"Enemy X should be numeric: {type(enemy.x)}"
        assert isinstance(enemy.y, (int, float)), f"Enemy Y should be numeric: {type(enemy.y)}"
        assert enemy.x >= 0 and enemy.y >= 0, f"Enemy at negative coordinates: ({enemy.x}, {enemy.y})"


def _can_pathfind(grid, start, end):
    """Simple pathfinding helper for testing"""
    if start == end:
        return True
    
    # Use BFS for pathfinding
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


def test_validation_integration_failure_cases():
    """Test that validation properly catches and reports the three critical issues"""
    validator = LevelValidator()
    
    # Test 1: Boundary holes
    grid = [[1 for _ in range(LEVEL_WIDTH)] for _ in range(LEVEL_HEIGHT)]
    # Create interior floor
    for y in range(2, LEVEL_HEIGHT - 2):
        for x in range(2, LEVEL_WIDTH - 2):
            grid[y][x] = 0
    
    # Create boundary hole
    grid[0][5] = 0
    
    level_data = {
        "grid": grid,
        "rooms": [],
        "spawn_points": [(5, 5)],
        "type": "dungeon",
        "terrain_grid": [["normal" for _ in range(LEVEL_WIDTH)] for _ in range(LEVEL_HEIGHT)],
        "enemy_spawns": [],
        "enemies": [],
        "portal_pos": (10 * TILE, 10 * TILE)
    }
    
    result = validator.validate(level_data)
    assert not result.is_valid
    assert any("boundary" in issue.lower() for issue in result.issues)
    
    # Test 2: Unreachable portal
    grid = [[1 for _ in range(LEVEL_WIDTH)] for _ in range(LEVEL_HEIGHT)]
    # Create two separate areas
    for y in range(2, 8):
        for x in range(2, 8):
            grid[y][x] = 0  # Area 1
    
    for y in range(12, 18):
        for x in range(12, 18):
            grid[y][x] = 0  # Area 2
    
    level_data["grid"] = grid
    level_data["spawn_points"] = [(3, 3)]
    level_data["portal_pos"] = (15 * TILE, 15 * TILE)  # In isolated area
    
    result = validator.validate(level_data)
    assert not result.is_valid
    assert any("portal" in issue.lower() and "reachable" in issue.lower() for issue in result.issues)
    
    # Test 3: No enemies
    level_data["enemies"] = []
    level_data["enemy_spawns"] = []
    
    result = validator.validate(level_data)
    assert not result.is_valid
    assert any("enemy" in issue.lower() and "no enemies" in issue.lower() for issue in result.issues)


def test_legacy_level_still_constructs():
    """Ensure legacy Level (fallback) remains constructible and drawable."""
    lvl = LegacyLevel(0)
    assert lvl.solids, "Legacy Level must have solids"
    assert hasattr(lvl, "spawn")
    assert hasattr(lvl, "doors")


def test_game_procedural_initialization_monkeypatched_menu_and_quit():
    """
    Instantiate Game in a controlled way:

    - Monkeypatch Menu.title_screen to avoid real UI loop.
    - Force procedural generation ON.
    - Verify initial level is GeneratedLevel or legacy Level fallback without crashing.
    """
    # Monkeypatch Menu.title_screen to a no-op
    original_title = Menu.title_screen

    def fake_title(self):
        # Configure some deterministic options without blocking:
        self.game.use_procedural = True
        self.game.level_type = LEVEL_TYPE
        self.game.difficulty = DIFFICULTY
        # Leave world_seed as whatever SeedManager picks or already has.

    Menu.title_screen = fake_title

    try:
        g = Game()
        # On init, _load_level should have been called
        assert hasattr(g, "level")
        # Either procedural GeneratedLevel or legacy Level; both are acceptable.
        assert isinstance(g.level, (GeneratedLevel, LegacyLevel))
        assert hasattr(g.level, "solids")
        assert hasattr(g.level, "spawn")
        assert hasattr(g.level, "doors")
        # Ensure seed info wired
        assert hasattr(g, "world_seed")
    finally:
        # Restore original title_screen to avoid side effects
        Menu.title_screen = original_title


def test_game_fallback_to_legacy_on_failure(monkeypatch=None):
    """
    Simulate failure inside LevelGenerator.generate_level and confirm Game falls
    back to static Level without crashing.
    """
    # Monkeypatch LevelGenerator.generate_level to raise once
    original_generate = LevelGenerator.generate_level

    def failing_generate(self, *args, **kwargs):
        raise RuntimeError("Simulated generation failure")

    LevelGenerator.generate_level = failing_generate

    # Monkeypatch Menu.title_screen to skip UI
    original_title = Menu.title_screen

    def fake_title(self):
        self.game.use_procedural = True

    Menu.title_screen = fake_title

    try:
        g = Game()
        # Since procedural failed, use_procedural should be False and level a LegacyLevel
        assert g.use_procedural is False
        assert isinstance(g.level, LegacyLevel)
    finally:
        LevelGenerator.generate_level = original_generate
        Menu.title_screen = original_title