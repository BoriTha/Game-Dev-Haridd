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
        # Percentage-based lifesteal and spell lifesteal (from equipment/modifiers)
        self.lifesteal_pct = float(self.config.get('lifesteal_pct', 0.0))
        self.spell_lifesteal_pct = float(self.config.get('spell_lifesteal', 0.0))
        # Accumulators to handle fractional lifesteal values across multiple hits
        self._lifesteal_accum = 0.0
        self._spell_lifesteal_accum = 0.0
        # Track temporary additions from power buffs so we can remove them later
        self._power_buff_lifesteal_add = 0.0
        self._power_buff_spell_lifesteal_add = 0.0

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

        # Handle Lifesteal for the player (flat and percentage-based)
        if player_combat.lifesteal_on_hit > 0 and hitbox.damage > 0:
            old_hp = player_combat.hp
            player_combat.hp = min(player_combat.max_hp, player_combat.hp + player_combat.lifesteal_on_hit)
            if player_combat.hp != old_hp:
                floating.append(DamageNumber(hitbox.owner.rect.centerx, hitbox.owner.rect.top - 10, f"+{player_combat.lifesteal_on_hit}", GREEN))

        # Percentage lifesteal (equipment-based) - physical attacks vs spells
        if hitbox.damage > 0:
            owner = hitbox.owner
            # Determine whether this was a spell - treat Wizard class attacks & tagged hits as spells
            is_spell = getattr(owner, 'cls', None) == 'Wizard' or getattr(hitbox, 'tag', None) == 'spell'
            owner_combat = getattr(owner, 'combat', None)
            physical_pct = float(getattr(owner_combat, 'lifesteal_pct', getattr(owner, 'lifesteal_pct', 0.0)) if owner_combat is not None else getattr(owner, 'lifesteal_pct', 0.0))
            spell_pct = float(getattr(owner_combat, 'spell_lifesteal_pct', getattr(owner, 'spell_lifesteal', 0.0)) if owner_combat is not None else getattr(owner, 'spell_lifesteal', 0.0))
            pct = spell_pct if is_spell else physical_pct
            if pct > 0 and owner_combat is not None:
                heal_float = hitbox.damage * pct
                if is_spell:
                    owner_combat._spell_lifesteal_accum = getattr(owner_combat, '_spell_lifesteal_accum', 0.0) + heal_float
                    heal_int = int(owner_combat._spell_lifesteal_accum)
                    if heal_int > 0:
                        old_hp = owner_combat.hp
                        owner_combat.hp = min(owner_combat.max_hp, owner_combat.hp + heal_int)
                        owner_combat._spell_lifesteal_accum -= heal_int
                        if owner_combat.hp != old_hp:
                            floating.append(DamageNumber(owner.rect.centerx, owner.rect.top - 10, f"+{heal_int}", GREEN))
                else:
                    owner_combat._lifesteal_accum = getattr(owner_combat, '_lifesteal_accum', 0.0) + heal_float
                    heal_int = int(owner_combat._lifesteal_accum)
                    if heal_int > 0:
                        old_hp = owner_combat.hp
                        owner_combat.hp = min(owner_combat.max_hp, owner_combat.hp + heal_int)
                        owner_combat._lifesteal_accum -= heal_int
                        if owner_combat.hp != old_hp:
                            floating.append(DamageNumber(owner.rect.centerx, owner.rect.top - 10, f"+{heal_int}", GREEN))

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
                # Remove temporary percentage lifesteal additions from power buff
                if hasattr(self, '_power_buff_lifesteal_add') and self._power_buff_lifesteal_add:
                    self.lifesteal_pct = max(0.0, self.lifesteal_pct - self._power_buff_lifesteal_add)
                    self._power_buff_lifesteal_add = 0.0
                if hasattr(self, '_power_buff_spell_lifesteal_add') and self._power_buff_spell_lifesteal_add:
                    self.spell_lifesteal_pct = max(0.0, self.spell_lifesteal_pct - self._power_buff_spell_lifesteal_add)
                    self._power_buff_spell_lifesteal_add = 0.0
                # Also clear accumulators to avoid carry-over
                self._lifesteal_accum = 0.0
                self._spell_lifesteal_accum = 0.0


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
            # Also temporarily set percentage-based lifesteal (if provided)
            # This allows buffs to grant percentage lifesteal as well.
            if 'power_buff_lifesteal_pct' in self.config:
                add_val = float(self.config.get('power_buff_lifesteal_pct', 0.0))
                self._power_buff_lifesteal_add = add_val
                self.lifesteal_pct = self.lifesteal_pct + add_val
            if 'power_buff_spell_lifesteal' in self.config:
                add_val = float(self.config.get('power_buff_spell_lifesteal', 0.0))
                self._power_buff_spell_lifesteal_add = add_val
                self.spell_lifesteal_pct = self.spell_lifesteal_pct + add_val
            return True
        return False
