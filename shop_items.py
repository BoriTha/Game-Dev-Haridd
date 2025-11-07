from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Tuple

from config import FPS, GREEN, CYAN, WHITE
from entities import floating, DamageNumber


Color = Tuple[int, int, int]


@dataclass(frozen=True)
class ShopConsumable:
    key: str
    name: str
    color: Color
    price: int
    max_stack: int = 3
    effect_text: str = ""
    description: str = ""
    flavor: str = ""
    icon_letter: str = ""

    def use(self, game) -> bool:
        """Apply the consumable effect to the running game. Returns True when consumed."""
        raise NotImplementedError

    def tooltip_lines(self) -> List[str]:
        lines = [f"{self.name} - {self.price} coins"]
        if self.effect_text:
            lines.append(self.effect_text)
        if self.description:
            lines.append(self.description)
        if self.flavor:
            lines.append(self.flavor)
        return lines


@dataclass(frozen=True)
class ShopEquipment:
    key: str
    name: str
    color: Color
    price: int
    icon_letter: str
    description: str
    modifiers: Dict[str, float]
    flavor: str = ""

    def tooltip_lines(self) -> List[str]:
        lines = [f"{self.name} - {self.price} coins"]
        lines.append(self.description)
        if self.flavor:
            lines.append(self.flavor)
        return lines


# Shop-Only Consumables
class PhoenixFeather(ShopConsumable):
    def __init__(self):
        super().__init__(
            key="phoenix_feather",
            name="Phoenix Feather",
            color=(255, 150, 50),
            price=150,
            max_stack=1,
            effect_text="Auto-revive with 50% HP on death",
            description="A mystical feather that ignites when life fades.",
            flavor="Reborn from ashes, just like the legendary phoenix.",
            icon_letter="P"
        )
    
    def use(self, game) -> bool:
        player = game.player
        if not hasattr(player, 'phoenix_feather_active'):
            player.phoenix_feather_active = False
        
        if player.phoenix_feather_active:
            floating.append(DamageNumber(player.rect.centerx, player.rect.top - 12, "Already Active", WHITE))
            return False
            
        player.phoenix_feather_active = True
        floating.append(DamageNumber(player.rect.centerx, player.rect.top - 12, "Phoenix Blessing", (255, 150, 50)))
        return True


class TimeCrystal(ShopConsumable):
    def __init__(self):
        super().__init__(
            key="time_crystal",
            name="Time Crystal",
            color=(150, 150, 255),
            price=80,
            max_stack=2,
            effect_text="Slows all enemies for 10 seconds",
            description="Crystallized time that bends reality around foes.",
            flavor="Feel time itself slow to a crawl.",
            icon_letter="T"
        )
    
    def use(self, game) -> bool:
        # Apply slow effect to all enemies
        for enemy in game.enemies:
            if getattr(enemy, 'alive', False):
                enemy.slow_mult = 0.3
                enemy.slow_remaining = 10 * FPS
                floating.append(DamageNumber(enemy.rect.centerx, enemy.rect.top - 6, "SLOWED", CYAN))
        
        floating.append(DamageNumber(game.player.rect.centerx, game.player.rect.top - 12, "Time Distorted", (150, 150, 255)))
        return True


class LuckyCharm(ShopConsumable):
    def __init__(self):
        super().__init__(
            key="lucky_charm",
            name="Lucky Charm",
            color=(255, 215, 0),
            price=120,
            max_stack=1,
            effect_text="+50% money drops for 2 minutes",
            description="A charm that attracts wealth from defeated foes.",
            flavor="Fortune favors the bold... and the charmed.",
            icon_letter="L"
        )
    
    def use(self, game) -> bool:
        player = game.player
        if not hasattr(player, 'lucky_charm_timer'):
            player.lucky_charm_timer = 0
        
        if player.lucky_charm_timer > 0:
            floating.append(DamageNumber(player.rect.centerx, player.rect.top - 12, "Already Active", WHITE))
            return False
            
        player.lucky_charm_timer = 120 * FPS  # 2 minutes
        floating.append(DamageNumber(player.rect.centerx, player.rect.top - 12, "Lucky!", (255, 215, 0)))
        return True


# Shop-Only Equipment
class GoldPlatedArmor(ShopEquipment):
    def __init__(self):
        super().__init__(
            key="gold_plated_armor",
            name="Gold-Plated Armor",
            color=(255, 215, 0),
            price=200,
            icon_letter="G",
            description="+2 HP, +10% damage resistance",
            modifiers={'max_hp': 2, 'damage_resistance': 0.1},
            flavor="Heavy armor that turns aside lethal blows."
        )


class SwiftBoots(ShopEquipment):
    def __init__(self):
        super().__init__(
            key="swift_boots",
            name="Swift Boots",
            color=(100, 200, 255),
            price=180,
            icon_letter="S",
            description="+0.3 speed, +0.2 air speed, -20% dash cooldown",
            modifiers={
                'player_speed': 0.3, 
                'player_air_speed': 0.2, 
                'dash_cooldown_reduction': 0.2
            },
            flavor="Light as air, swift as the wind."
        )


class ManaSiphon(ShopEquipment):
    def __init__(self):
        super().__init__(
            key="mana_siphon",
            name="Mana Siphon",
            color=(200, 100, 255),
            price=220,
            icon_letter="M",
            description="+15 max mana, +0.3 mana regen, spell lifesteal",
            modifiers={
                'max_mana': 15, 
                'mana_regen': 0.3 / FPS,
                'spell_lifesteal': 0.2
            },
            flavor="Draw power from both the ether and your foes."
        )


def build_shop_consumables() -> Dict[str, ShopConsumable]:
    consumables = [
        PhoenixFeather(),
        TimeCrystal(),
        LuckyCharm(),
    ]
    return {item.key: item for item in consumables}


def build_shop_equipment() -> Dict[str, ShopEquipment]:
    equipment = [
        GoldPlatedArmor(),
        SwiftBoots(),
        ManaSiphon(),
    ]
    return {item.key: item for item in equipment}