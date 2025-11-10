import random
from config import WHITE, CYAN, GREEN, RED

# This component relies on a global 'floating' list for text effects and a 'DamageNumber' class.
# These are expected to be imported from elsewhere in the project.
# e.g., from ..entity_common import floating, DamageNumber

class CombatComponent:
    """
    A centralized, configuration-driven component that handles all combat logic
    for any entity in the game.
    """
    def __init__(self, entity, config: dict):
        self.entity = entity
        self.config = config

        # --- Core Attributes ---
        self.hp = self.config.get('max_hp', 1)
        self.max_hp = self.config.get('max_hp', 1)
        # Sync back to entity for any legacy access or display logic
        if hasattr(entity, 'hp'):
            self.entity.hp = self.hp
        if hasattr(entity, 'max_hp'):
            self.entity.max_hp = self.max_hp

        # Unified death state management
        self.alive = True
        if hasattr(entity, 'alive'):
            self.entity.alive = True

        # Unified invincibility frames
        self.invincible_frames = 0
        self.default_ifr = self.config.get('default_ifr', 8)

        # --- Player-Specific Attributes & State ---
        self.is_god_mode = self.config.get('god_mode', False)
        
        self.shield_hits_max = self.config.get('shield_hits_max', 0)
        self.shield_duration = self.config.get('shield_duration', 0)
        self.shield_hits_left = 0
        self.shield_timer = 0

        self.parry_duration = self.config.get('parry_duration', 0)
        self.parry_timer = 0

        # Lifesteal is now a temporary buff, not a default state.
        self.lifesteal_on_hit = 0

        self.power_buff_duration = self.config.get('power_buff_duration', 0)
        self.power_buff_atk_bonus = self.config.get('power_buff_atk_bonus', 0)
        self.power_timer = 0
        self.atk_bonus = 0

        # --- Enemy-Specific Attributes ---
        money_drop_config = self.config.get('money_drop', (0, 0))
        self.money_on_death_min = money_drop_config[0]
        self.money_on_death_max = money_drop_config[1]
        
        # --- Pogo Interaction ---
        self.pogoable = self.config.get('pogoable', True)

    def is_invincible(self) -> bool:
        """Checks if the entity is currently invincible."""
        return self.invincible_frames > 0

    def is_parrying(self) -> bool:
        """Checks if the entity is currently parrying."""
        return self.parry_timer > 0

    def take_damage(self, amount, knockback=(0, 0), source=None, bypass_ifr=False):
        """
        The single, unified method for processing incoming damage.
        'source' is the entity that dealt the damage.
        """
        from ..entity_common import floating, DamageNumber
        
        # 1. God Mode Check (check the entity's god attribute directly)
        if getattr(self.entity, 'god', False):
            return False

        # 2. Shield Check
        if self.shield_timer > 0 and self.shield_hits_left > 0:
            self.shield_hits_left -= 1
            floating.append(DamageNumber(self.entity.rect.centerx, self.entity.rect.top - 8, "BLOCK", CYAN))
            return False

        # 3. Invincibility Check
        if self.is_invincible() and not bypass_ifr:
            return False

        # 4. Apply Damage
        self.hp -= amount
        if hasattr(self.entity, 'hp'):
            self.entity.hp = self.hp

        # 5. Apply Knockback
        if knockback != (0, 0):
            if hasattr(self.entity, 'vx'):
                self.entity.vx += knockback[0]
            if hasattr(self.entity, 'vy'):
                self.entity.vy += knockback[1]

        # 6. Set Invincibility & Visuals
        self.invincible_frames = self.default_ifr
        if hasattr(self.entity, 'iframes_flash'):
            self.entity.iframes_flash = True
        
        # 7. Show Damage Number
        color = RED if self.entity.__class__.__name__ == 'Player' else WHITE
        floating.append(DamageNumber(self.entity.rect.centerx, self.entity.rect.top - 6, f"-{amount}", color))

        # 8. Death Check
        if self.hp <= 0:
            self.hp = 0
            self.alive = False
            if hasattr(self.entity, 'alive'):
                self.entity.alive = False
            
            self._on_death(source)
        
        return True

    def _on_death(self, attacker):
        """Handles all on-death logic."""
        from ..entity_common import floating, DamageNumber
        floating.append(DamageNumber(self.entity.rect.centerx, self.entity.rect.centery, "KO", CYAN))

        # Money Drop Logic
        if self.money_on_death_max > 0 and attacker and hasattr(attacker, 'money'):
            lucky_charm = hasattr(attacker, 'lucky_charm_timer') and attacker.lucky_charm_timer > 0
            bonus = 1.5 if lucky_charm else 1.0
            amount = int(random.randint(self.money_on_death_min, self.money_on_death_max) * bonus)
            
            attacker.money += amount
            floating.append(DamageNumber(self.entity.rect.centerx, self.entity.rect.top - 12, f"+{amount}", (255, 215, 0)))

    def handle_hit_by_player_hitbox(self, hitbox):
        """
        Called when this entity is hit by a player's attack hitbox.
        """
        from ..entity_common import floating, DamageNumber
        if not self.alive:
            return

        damage_taken = self.take_damage(
            hitbox.damage,
            knockback=(0, 0),
            source=hitbox.owner,
            bypass_ifr=getattr(hitbox, 'bypass_ifr', False)
        )

        if not damage_taken:
            return

        if not hasattr(hitbox.owner, 'combat'):
            return # Attacker has no combat component

        player_combat = hitbox.owner.combat

        # Handle Lifesteal for the player
        if player_combat.lifesteal_on_hit > 0 and hitbox.damage > 0:
            old_hp = player_combat.hp
            player_combat.hp = min(player_combat.max_hp, player_combat.hp + player_combat.lifesteal_on_hit)
            if player_combat.hp != old_hp:
                floating.append(DamageNumber(hitbox.owner.rect.centerx, hitbox.owner.rect.top - 10, f"+{player_combat.lifesteal_on_hit}", GREEN))

        # Handle Pogo effect for the player
        if self.pogoable and getattr(hitbox, 'pogo', False):
            from config import POGO_BOUNCE_VY
            hitbox.owner.vy = POGO_BOUNCE_VY
            hitbox.owner.on_ground = False

    def handle_collision_with_player(self, player_entity):
        """
        Called when this entity (an enemy) collides with the player.
        """
        from ..entity_common import floating, DamageNumber
        if not self.alive or not player_entity.combat.alive:
            return

        if self.entity.rect.colliderect(player_entity.rect):
            player_combat = player_entity.combat
            
            if player_combat.is_parrying():
                self.take_damage(1, (0, 0), player_entity)
                floating.append(DamageNumber(self.entity.rect.centerx, self.entity.rect.top - 6, "PARRY", CYAN))
                if hasattr(self.entity, 'vx'):
                    self.entity.vx = -((1 if player_entity.rect.centerx > self.entity.rect.centerx else -1) * 3)
                if hasattr(player_entity, 'vy'):
                    player_entity.vy = -6
            else:
                knockback_x = (1 if player_entity.rect.centerx > self.entity.rect.centerx else -1) * 2
                knockback_y = -6
                player_combat.take_damage(1, (knockback_x, knockback_y), self.entity)

    def update(self):
        """
        Called every frame to update timers and other states.
        """
        if self.invincible_frames > 0:
            self.invincible_frames -= 1
            if self.invincible_frames == 0 and hasattr(self.entity, 'iframes_flash'):
                self.entity.iframes_flash = False

        if self.shield_timer > 0:
            self.shield_timer -= 1
            if self.shield_timer == 0:
                self.shield_hits_left = 0
        
        if self.parry_timer > 0:
            self.parry_timer -= 1

        if self.power_timer > 0:
            self.power_timer -= 1
            if self.power_timer == 0:
                # Reset all power buff effects when the timer expires.
                self.atk_bonus = 0
                self.lifesteal_on_hit = 0


    # --- Ability Activation Methods ---

    def activate_shield(self):
        """Activates the shield if the entity is configured for it."""
        if self.shield_hits_max > 0 and self.shield_duration > 0:
            self.shield_timer = self.shield_duration
            self.shield_hits_left = self.shield_hits_max
            return True
        return False

    def activate_parry(self):
        """Activates the parry state."""
        if self.parry_duration > 0 and self.parry_timer == 0:
            self.parry_timer = self.parry_duration
            return True
        return False

    def activate_power_buff(self):
        """Activates the power buff if the entity is configured for it."""
        if self.power_buff_duration > 0:
            self.power_timer = self.power_buff_duration
            self.atk_bonus = self.power_buff_atk_bonus
            # Activate lifesteal from the config value for the duration of the buff.
            self.lifesteal_on_hit = self.config.get('power_buff_lifesteal', 0)
            return True
        return False
