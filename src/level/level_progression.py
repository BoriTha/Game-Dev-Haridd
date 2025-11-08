"""
Level Progression System - Handles dynamic difficulty scaling and level variety
"""

from typing import Dict, List, Tuple, Any
import random


class LevelProgress:
    """Manages level progression and difficulty scaling"""

    def __init__(self):
        # Define level themes and their properties
        self.level_themes = {
            0: {"type": "dungeon", "name": "Dungeon Depths", "difficulty_mult": 1.0},
            1: {"type": "cave", "name": "Crystal Caves", "difficulty_mult": 1.1},
            2: {"type": "outdoor", "name": "Forgotten Gardens", "difficulty_mult": 1.2},
            3: {"type": "hybrid", "name": "Ancient Ruins", "difficulty_mult": 1.3},
            4: {"type": "dungeon", "name": "Dark Fortress", "difficulty_mult": 1.4},
            5: {"type": "cave", "name": "Lava Tunnels", "difficulty_mult": 1.5},
            6: {"type": "outdoor", "name": "Haunted Forest", "difficulty_mult": 1.6},
            7: {"type": "hybrid", "name": "Sky Temple", "difficulty_mult": 1.7},
            8: {"type": "dungeon", "name": "Underground Labyrinth", "difficulty_mult": 1.8},
            9: {"type": "cave", "name": "Ice Caverns", "difficulty_mult": 1.9},
            # Repeat cycle with higher difficulty
            10: {"type": "dungeon", "name": "Dungeon Depths II", "difficulty_mult": 2.0},
            11: {"type": "cave", "name": "Crystal Caves II", "difficulty_mult": 2.2},
            12: {"type": "outdoor", "name": "Forgotten Gardens II", "difficulty_mult": 2.4},
            13: {"type": "hybrid", "name": "Ancient Ruins II", "difficulty_mult": 2.6},
            14: {"type": "dungeon", "name": "Dark Fortress II", "difficulty_mult": 2.8},
            15: {"type": "cave", "name": "Lava Tunnels II", "difficulty_mult": 3.0},
        }

        # Enemy difficulty scaling
        self.enemy_stats_by_level = {
            "health_mult": 1.0,
            "damage_mult": 1.0,
            "speed_mult": 1.0,
            "count_mult": 1.0,
        }

    def get_level_config(self, level_index: int) -> Dict[str, Any]:
        """
        Get configuration for a specific level

        Returns:
            Dictionary with level type, difficulty, and theme info
        """
        # Cycle through themes
        theme_index = level_index % len(self.level_themes)
        theme = self.level_themes[theme_index].copy()

        # Calculate base difficulty (1-3 scale)
        base_difficulty = min(3, 1 + level_index // 5)

        # Apply theme difficulty multiplier
        difficulty_mult = theme["difficulty_mult"]

        # Calculate final difficulty
        final_difficulty = min(3, base_difficulty * difficulty_mult)

        # Add progression to enemy stats
        level_progress = level_index + 1
        self.enemy_stats_by_level = {
            "health_mult": 1.0 + (level_progress * 0.1),
            "damage_mult": 1.0 + (level_progress * 0.08),
            "speed_mult": 1.0 + (level_progress * 0.05),
            "count_mult": 1.0 + (level_progress * 0.15),
        }

        return {
            "level_index": level_index,
            "level_type": theme["type"],
            "level_name": theme["name"],
            "difficulty": int(final_difficulty),
            "theme_index": theme_index,
            "enemy_stats": self.enemy_stats_by_level,
            "special_features": self._get_special_features(level_index),
        }

    def _get_special_features(self, level_index: int) -> List[str]:
        """Get special features for this level"""
        features = []

        # Every 5 levels introduces a new challenge
        if level_index >= 5 and level_index % 5 == 0:
            features.append("elite_enemies")

        if level_index >= 10 and level_index % 10 == 0:
            features.append("mini_boss")

        # Environmental hazards increase with level
        if level_index >= 3:
            features.append("environmental_hazards")

        if level_index >= 7:
            features.append("traps")

        if level_index >= 12:
            features.append("elite_traps")

        return features

    def get_enemy_spawn_config(self, level_index: int, level_type: str) -> Dict[str, Any]:
        """
        Get enemy spawn configuration for this level

        Returns:
            Dictionary with enemy types, counts, and spawn patterns
        """
        config = self.get_level_config(level_index)
        enemy_stats = config["enemy_stats"]

        # Base enemy pools by level type
        enemy_pools = {
            "dungeon": ["Bug", "Archer", "Assassin", "WizardCaster"],
            "cave": ["Bug", "Frog", "Bee", "Golem"],
            "outdoor": ["Bug", "Archer", "Bee", "Frog"],
            "hybrid": ["Bug", "Archer", "Assassin", "WizardCaster", "Frog", "Bee"]
        }

        # Get appropriate enemy pool
        available_enemies = enemy_pools.get(level_type, ["Bug"])

        # Increase enemy variety at higher levels
        if level_index >= 5:
            available_enemies.extend(["Golem"])
        if level_index >= 10:
            available_enemies.extend(["WizardCaster"])

        # Calculate spawn counts based on difficulty
        base_count = 3 + (level_index // 3)
        spawn_count = int(base_count * enemy_stats["count_mult"])

        # Determine enemy composition
        spawn_config = {
            "enemy_types": available_enemies,
            "total_enemies": min(spawn_count, 15),  # Cap to prevent lag
            "elite_chance": min(0.1 + (level_index * 0.02), 0.5),
            "boss_chance": 0.1 if level_index % 5 == 4 else 0.0,
            "spawn_pattern": "scattered" if level_type in ["outdoor", "cave"] else "strategic",
            "stats_multiplier": enemy_stats,
        }

        return spawn_config

    def get_treasure_config(self, level_index: int) -> Dict[str, Any]:
        """
        Get treasure/loot configuration for this level
        """
        # Better loot at higher levels
        treasure_rarity = min(1.0, 0.3 + (level_index * 0.05))
        treasure_count = 2 + (level_index // 4)

        return {
            "treasure_chance": treasure_rarity,
            "treasure_count": treasure_count,
            "rare_item_chance": min(0.2 + (level_index * 0.02), 0.6),
            "legendary_item_chance": min(0.05 + (level_index * 0.01), 0.3),
        }

    def should_spawn_boss(self, level_index: int) -> bool:
        """Determine if this level should have a boss"""
        # Boss every 5 levels
        return (level_index + 1) % 5 == 0

    def get_next_level_theme_hint(self, current_level: int) -> str:
        """Get a hint about the next level theme"""
        next_config = self.get_level_config(current_level + 1)
        return f"Next: {next_config['level_name']}"


# Singleton instance
level_progression = LevelProgress()