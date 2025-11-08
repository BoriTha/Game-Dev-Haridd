"""
Seed Manager - Handles deterministic seed management for procedural generation
"""

import hashlib
import random
from typing import Dict, Optional


class SeedManager:
    """Manages deterministic seeds for procedural level generation"""
    
    def __init__(self, world_seed: Optional[int] = None):
        """
        Initialize seed manager with optional world seed
        
        Args:
            world_seed: Master seed for entire playthrough. If None, generates random seed.
        """
        self.world_seed = world_seed if world_seed is not None else random.randint(0, 2**31 - 1)
        self.current_level_seed = None
        self.sub_seeds = {}
        self._rng_instances = {}

    def generate_level_seed(self, level_index: int) -> int:
        """
        Generate deterministic seed for specific level
        
        Args:
            level_index: Index of the level
            
        Returns:
            Deterministic seed for this level
        """
        # Combine world seed with level index for deterministic level seed
        seed_string = f"{self.world_seed}_level_{level_index}"
        seed_hash = hashlib.md5(seed_string.encode()).hexdigest()
        level_seed = int(seed_hash[:8], 16)
        
        self.current_level_seed = level_seed
        # Reset sub-seeds and RNGs whenever a new level seed is generated
        self.sub_seeds = {}
        self._rng_instances = {}
        return level_seed
    
    def generate_sub_seeds(self, level_seed: int) -> Dict[str, int]:
        """
        Generate sub-seeds for different generation components
        
        Args:
            level_seed: Base seed for current level
            
        Returns:
            Dictionary of sub-seeds for different generation phases
        """
        sub_seeds = {}
        
        # Generate deterministic sub-seeds for each component
        components = ['structure', 'terrain', 'enemies', 'items', 'details']
        
        for component in components:
            seed_string = f"{level_seed}_{component}"
            seed_hash = hashlib.md5(seed_string.encode()).hexdigest()
            sub_seeds[component] = int(seed_hash[:8], 16)
        
        self.sub_seeds = sub_seeds
        return sub_seeds
    
    def get_random(self, component: str) -> random.Random:
        """
        Get deterministic random instance for specific component
        
        Args:
            component: Component name ('structure', 'terrain', 'enemies', etc.)
            
        Returns:
            Random instance seeded for this component
        """
        if component not in self._rng_instances:
            if component not in self.sub_seeds:
                # This can happen if get_random is called before generate_sub_seeds
                # For robustness, we can generate it on-the-fly.
                seed_string = f"{self.current_level_seed}_{component}"
                seed_hash = hashlib.md5(seed_string.encode()).hexdigest()
                self.sub_seeds[component] = int(seed_hash[:8], 16)

            self._rng_instances[component] = random.Random(self.sub_seeds[component])

        return self._rng_instances[component]
    
    def get_world_seed(self) -> int:
        """Get the master world seed"""
        return self.world_seed
    
    def get_level_seed(self) -> Optional[int]:
        """Get the current level seed"""
        return self.current_level_seed
    
    def set_world_seed(self, seed: int):
        """Set a new world seed"""
        self.world_seed = seed
        self.current_level_seed = None
        self.sub_seeds = {}
    
    def get_seed_info(self) -> Dict[str, int]:
        """Get information about current seeds"""
        info = {
            'world_seed': self.world_seed,
            'sub_seeds': self.sub_seeds.copy()
        }
        if self.current_level_seed is not None:
            info['level_seed'] = self.current_level_seed
        return info