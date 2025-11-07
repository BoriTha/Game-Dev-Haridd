from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Tuple

from config import FPS, GREEN, CYAN, WHITE, DOUBLE_JUMPS
from entities import floating, DamageNumber


Color = Tuple[int, int, int]


@dataclass(frozen=True)
class Consumable:
    key: str
    name: str
    color: Color
    max_stack: int = 3
    effect_text: str = ""
    description: str = ""
    flavor: str = ""
    icon_letter: str = ""

    def use(self, game) -> bool:
        """Apply the consumable effect to the running game. Returns True when consumed."""
        raise NotImplementedError

    def tooltip_lines(self) -> List[str]:
        lines = [self.name]
        if self.effect_text:
            lines.append(self.effect_text)
        if self.description:
            lines.append(self.description)
        if self.flavor:
            lines.append(self.flavor)
        return lines


@dataclass(frozen=True)
class HealConsumable(Consumable):
    amount: int = 0

    def use(self, game) -> bool:
        player = game.player
        before = player.hp
        player.hp = min(player.max_hp, player.hp + self.amount)
        healed = player.hp - before
        if healed <= 0:
            return False
        floating.append(DamageNumber(player.rect.centerx, player.rect.top - 12, f"+{healed} HP", GREEN))
        return True


@dataclass(frozen=True)
class ManaConsumable(Consumable):
    amount: float = 0.0

    def use(self, game) -> bool:
        player = game.player
        if not hasattr(player, 'mana'):
            return False
        before = player.mana
        player.mana = min(player.max_mana, player.mana + self.amount)
        restored = player.mana - before
        if restored <= 0:
            return False
        floating.append(DamageNumber(player.rect.centerx, player.rect.top - 12, f"+{restored:.0f} MP", CYAN))
        return True


@dataclass(frozen=True)
class SpeedConsumable(Consumable):
    amount: float = 0.0
    duration: float = 0.0  # seconds

    def use(self, game) -> bool:
        player = game.player
        frames = int(self.duration * FPS)
        if frames <= 0 or self.amount <= 0:
            return False
        current = getattr(player, 'speed_potion_timer', 0)
        player.speed_potion_timer = max(current, frames)
        player.speed_potion_bonus = max(getattr(player, 'speed_potion_bonus', 0.0), self.amount)
        floating.append(DamageNumber(player.rect.centerx, player.rect.top - 12, "Haste", WHITE))
        return True


@dataclass(frozen=True)
class JumpBoostConsumable(Consumable):
    duration: float = 10.0
    jump_multiplier: float = 1.2
    extra_jumps: int = 2

    def use(self, game) -> bool:
        player = game.player
        frames = int(self.duration * FPS)
        if frames <= 0:
            return False
        player.jump_boost_timer = frames
        player.jump_force_multiplier = max(self.jump_multiplier, getattr(player, 'jump_force_multiplier', 1.0))
        player.extra_jump_charges = max(self.extra_jumps, getattr(player, 'extra_jump_charges', 0))
        player.double_jumps = max(player.double_jumps, DOUBLE_JUMPS + self.extra_jumps)
        floating.append(DamageNumber(player.rect.centerx, player.rect.top - 12, "Skybound", WHITE))
        return True


@dataclass(frozen=True)
class StaminaBoostConsumable(Consumable):
    bonus_pct: float = 0.25
    duration: float = 30.0

    def use(self, game) -> bool:
        player = game.player
        frames = int(self.duration * FPS)
        if frames <= 0:
            return False
        player.stamina_boost_timer = frames
        player.stamina_buff_mult = 1.0 + self.bonus_pct
        floating.append(DamageNumber(player.rect.centerx, player.rect.top - 12, "+Stamina", GREEN))
        if hasattr(game, 'recalculate_player_stats'):
            game.recalculate_player_stats()
        return True


# Shop-Only Consumables
class PhoenixFeather(Consumable):
    def __init__(self):
        super().__init__(
            key="phoenix_feather",
            name="Phoenix Feather",
            color=(255, 150, 50),
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


class TimeCrystal(Consumable):
    def __init__(self):
        super().__init__(
            key="time_crystal",
            name="Time Crystal",
            color=(150, 150, 255),
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


class LuckyCharm(Consumable):
    def __init__(self):
        super().__init__(
            key="lucky_charm",
            name="Lucky Charm",
            color=(255, 215, 0),
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


@dataclass(frozen=True)
class ArmamentItem:
    key: str
    name: str
    color: Color
    icon_letter: str
    description: str
    modifiers: Dict[str, float]
    flavor: str = ""

    def tooltip_lines(self) -> List[str]:
        lines = [self.name, self.description]
        if self.flavor:
            lines.append(self.flavor)
        return lines


def build_armament_catalog() -> Dict[str, ArmamentItem]:
    items = [
        ArmamentItem(
            key="tower_bulwark",
            name="Tower Bulwark",
            color=(120, 140, 200),
            icon_letter="B",
            description="+3 HP, +2 Stamina capacity.",
            modifiers={'max_hp': 3, 'max_stamina': 2},
            flavor="Plated shield core carried by royal sentries."
        ),
        ArmamentItem(
            key="gale_boots",
            name="Gale Boots",
            color=(180, 220, 255),
            icon_letter="G",
            description="+0.6 ground / +0.4 air speed.",
            modifiers={'player_speed': 0.6, 'player_air_speed': 0.4},
            flavor="Canvas shoes threaded with windglass fibers."
        ),
        ArmamentItem(
            key="ember_blade",
            name="Ember Blade",
            color=(250, 150, 90),
            icon_letter="E",
            description="+2 Attack Power.",
            modifiers={'attack_damage': 2},
            flavor="Still warm from the forge at Ashen Gate."
        ),
        ArmamentItem(
            key="sages_focus",
            name="Sage's Focus",
            color=(170, 140, 255),
            icon_letter="S",
            description="+20 Mana, +0.5 mana regen.",
            modifiers={'max_mana': 20, 'mana_regen': 0.5 / FPS},
            flavor="Crystal monocle tuned to astral tides."
        ),
        ArmamentItem(
            key="hunter_totem",
            name="Hunter's Totem",
            color=(120, 200, 160),
            icon_letter="H",
            description="+1 Attack, steadier stamina regen.",
            modifiers={'attack_damage': 1, 'stamina_regen': 0.02},
            flavor="Bone charm carved for tireless stalking."
        ),
        ArmamentItem(
            key="stone_idol",
            name="Stone Idol",
            color=(160, 150, 130),
            icon_letter="I",
            description="+1 HP, +4 Stamina.",
            modifiers={'max_hp': 1, 'max_stamina': 4},
            flavor="A heavy relic that steadies every breath."
        ),
        ArmamentItem(
            key="void_thread",
            name="Void Thread",
            color=(90, 110, 190),
            icon_letter="V",
            description="+10 Mana, +0.2 air speed.",
            modifiers={'max_mana': 10, 'player_air_speed': 0.2},
            flavor="Cloak strand cut from a leaper between worlds."
        ),
        ArmamentItem(
            key="aurora_band",
            name="Aurora Band",
            color=(220, 200, 120),
            icon_letter="A",
            description="+1 HP, warm stamina trickle.",
            modifiers={'max_hp': 1, 'stamina_regen': 0.03},
            flavor="Glows softly when danger is near."
        ),
        ArmamentItem(
            key="wyrm_scale",
            name="Wyrm Scale",
            color=(200, 120, 160),
            icon_letter="W",
            description="+1 Attack, +1 HP.",
            modifiers={'attack_damage': 1, 'max_hp': 1},
            flavor="Hard enough to parry dragonfire."
        ),
        # Shop-Only Equipment
        GoldPlatedArmor(),
        SwiftBoots(),
        ManaSiphon(),
    ]
    return {item.key: item for item in items}


# Shop-Only Equipment
class GoldPlatedArmor(ArmamentItem):
    def __init__(self):
        super().__init__(
            key="gold_plated_armor",
            name="Gold-Plated Armor",
            color=(255, 215, 0),
            icon_letter="G",
            description="+2 HP, +10% damage resistance",
            modifiers={'max_hp': 2, 'damage_resistance': 0.1},
            flavor="Heavy armor that turns aside lethal blows."
        )


class SwiftBoots(ArmamentItem):
    def __init__(self):
        super().__init__(
            key="swift_boots",
            name="Swift Boots",
            color=(100, 200, 255),
            icon_letter="S",
            description="+0.3 speed, +0.2 air speed, -20% dash cooldown",
            modifiers={
                'player_speed': 0.3,
                'player_air_speed': 0.2,
                'dash_cooldown_reduction': 0.2
            },
            flavor="Light as air, swift as the wind."
        )


class ManaSiphon(ArmamentItem):
    def __init__(self):
        super().__init__(
            key="mana_siphon",
            name="Mana Siphon",
            color=(200, 100, 255),
            icon_letter="M",
            description="+15 max mana, +0.3 mana regen, spell lifesteal",
            modifiers={
                'max_mana': 15,
                'mana_regen': 0.3 / FPS,
                'spell_lifesteal': 0.2
            },
            flavor="Draw power from both the ether and your foes."
        )


def build_consumable_catalog() -> Dict[str, Consumable]:
    consumables = [
        HealConsumable(
            key='health',
            name="Health Flask",
            color=(215, 110, 120),
            icon_letter="H",
            max_stack=5,
            amount=3,
            effect_text="Restore 3 HP instantly.",
            description="Distilled petals from palace gardens.",
        ),
        ManaConsumable(
            key='mana',
            name="Mana Vial",
            color=(120, 180, 240),
            icon_letter="M",
            max_stack=5,
            amount=10,
            effect_text="Restore 10 mana.",
            description="Clinks with crystallized star-salts.",
        ),
        SpeedConsumable(
            key='speed',
            name="Haste Draught",
            color=(255, 200, 120),
            icon_letter="S",
            max_stack=3,
            amount=0.05,
            duration=8.0,
            effect_text="Short burst of speed and cooldown haste.",
            description="Citrus fizz harvested from sun-basil.",
        ),
        JumpBoostConsumable(
            key='skyroot',
            name="Skyroot Elixir",
            color=(200, 220, 255),
            icon_letter="J",
            max_stack=3,
            duration=12.0,
            jump_multiplier=1.25,
            extra_jumps=1,
            effect_text="Higher jumps and triple-jump for 12s.",
            description="Sap of levitating Skyroot tree.",
            flavor="Feels like standing on stormclouds.",
        ),
        StaminaBoostConsumable(
            key='stamina',
            name="Cavern Brew",
            color=(120, 200, 140),
            icon_letter="C",
            max_stack=3,
            duration=30.0,
            bonus_pct=0.25,
            effect_text="+25% stamina for 30s. Bar glows green.",
            description="Hidden-cave tonic that stretches every breath.",
            flavor="Thick, earthy, stubborn.",
        ),
        # Shop-Only Consumables
        PhoenixFeather(),
        TimeCrystal(),
        LuckyCharm(),
    ]
    return {item.key: item for item in consumables}


def build_shop_consumables() -> Dict[str, Consumable]:
    consumables = [
        PhoenixFeather(),
        TimeCrystal(),
        LuckyCharm(),
    ]
    return {item.key: item for item in consumables}


def build_shop_equipment() -> Dict[str, ArmamentItem]:
    equipment = [
        GoldPlatedArmor(),
        SwiftBoots(),
        ManaSiphon(),
    ]
    return {item.key: item for item in equipment}
