"""
HUD drawing utilities for Haridd.
This module contains one main entrypoint: `draw_hud(game, screen)` which draws
all player-facing HUD elements (HP, cooldown bars, skill slots, consumable hotbar, status text,
coins, class label, interactive prompts previously in `main.py`).

Guidelines:
- Use absolute imports.
- Accept the Game instance and read-only access its attributes.
- Keep draw-only logic here; avoid mutating `game` except for purely visual helper calls.
"""
from typing import Tuple
import logging
import pygame

from config import WIDTH, HEIGHT, FPS, CYAN, WHITE, WALL_JUMP_COOLDOWN, TILE
from src.core.utils import draw_text

logger = logging.getLogger(__name__)


def draw_hud(game, screen: pygame.Surface) -> None:
    """Draw HUD elements using `game`'s state.

    Args:
        game: The running Game instance (read-only for HUD purposes).
        screen: Pygame surface to draw onto.
    """
    try:
        x, y = 16, 16

        # HP boxes
        for i in range(game.player.max_hp):
            c = (80, 200, 120) if i < game.player.hp else (60, 80, 60)
            pygame.draw.rect(screen, c, pygame.Rect(x + i * 18, y, 16, 10), border_radius=3)
        y += 16

        # Dash cooldown bar (cyan)
        if getattr(game.player, 'dash_cd', 0):
            pct = 1 - (game.player.dash_cd / 24)
            pygame.draw.rect(screen, (80, 80, 80), pygame.Rect(x, y, 120, 6), border_radius=3)
            pygame.draw.rect(screen, CYAN, pygame.Rect(x, y, int(120 * pct), 6), border_radius=3)
            y += 12

        # Wall jump cooldown bar (orange)
        if getattr(game.player, 'wall_jump_cooldown', 0) > 0:
            pct = 1 - (game.player.wall_jump_cooldown / WALL_JUMP_COOLDOWN)
            pygame.draw.rect(screen, (80, 80, 80), pygame.Rect(x, y, 120, 6), border_radius=3)
            pygame.draw.rect(screen, (255, 165, 0), pygame.Rect(x, y, int(120 * pct), 6), border_radius=3)
        y += 12

        # Stamina bar
        if hasattr(game.player, 'stamina') and hasattr(game.player, 'max_stamina'):
            spct = max(0.0, min(1.0, game.player.stamina / max(1e-6, game.player.max_stamina)))
            pygame.draw.rect(screen, (60, 60, 60), pygame.Rect(x, y, 120, 6), border_radius=3)
            stamina_col = (120, 230, 160) if getattr(game.player, 'stamina_boost_timer', 0) > 0 else (200, 180, 60)
            pygame.draw.rect(screen, stamina_col, pygame.Rect(x, y, int(120 * spct), 6), border_radius=3)
            y += 12

        # Mana bar
        if hasattr(game.player, 'mana') and hasattr(game.player, 'max_mana'):
            mpct = max(0.0, min(1.0, game.player.mana / max(1e-6, game.player.max_mana)))
            pygame.draw.rect(screen, (60, 60, 60), pygame.Rect(x, y, 120, 6), border_radius=3)
            pygame.draw.rect(screen, CYAN, pygame.Rect(x, y, int(120 * mpct), 6), border_radius=3)
            y += 12

        # Ranger charge bar
        if getattr(game.player, 'cls', '') == 'Ranger' and getattr(game.player, 'charging', False):
            pct = max(0.0, min(1.0, game.player.charge_time / max(1, game.player.charge_threshold)))
            pygame.draw.rect(screen, (60, 60, 60), pygame.Rect(x, y, 120, 6), border_radius=3)
            pygame.draw.rect(screen, (200, 180, 60), pygame.Rect(x, y, int(120 * pct), 6), border_radius=3)
            if pct >= 1.0:
                draw_text(screen, "!", (x + 124, y - 6), (255, 80, 80), size=18, bold=True)
            y += 12

        # Room/Level info (PCG-aware)
        if getattr(game, 'use_pcg', False) and hasattr(game.level, 'room_code'):
            try:
                import re
                code = str(game.level.room_code)
                m = re.match(r"^(\d+?)([1-6][A-Za-z])$", code)
                if m:
                    lvl = int(m.group(1))
                    room_str = m.group(2)
                    draw_text(screen, f"Level:{lvl} Room:{room_str}", (WIDTH - 220, 8), WHITE, size=16)
                else:
                    m2 = re.match(r"^(\d+)(.+)$", code)
                    if m2:
                        lvl = int(m2.group(1))
                        room_str = m2.group(2)
                        draw_text(screen, f"Level:{lvl} Room:{room_str}", (WIDTH - 220, 8), WHITE, size=16)
                    else:
                        draw_text(screen, f"PCG: {game.level.room_code}", (WIDTH - 220, 8), WHITE, size=16)
            except Exception:
                draw_text(screen, f"PCG: {game.level.room_code}", (WIDTH - 220, 8), WHITE, size=16)
        else:
            from src.level.legacy_level import ROOM_COUNT
            draw_text(screen, f"Room {getattr(game, 'level_index', 0) + 1}/{ROOM_COUNT}", (WIDTH - 220, 8), WHITE, size=16)

        # Class and coins
        draw_text(screen, f"Class: {getattr(game.player, 'cls', 'Unknown')}", (WIDTH - 220, 28), (200, 200, 200), size=16)
        draw_text(screen, f"Coins: {game.player.money}", (WIDTH - 220, 48), (255, 215, 0), bold=True)

        # Skill bar (3 slots)
        sbx, sby = 16, HEIGHT - 80
        slot_w, slot_h = 46, 46
        if game.player.cls == 'Knight':
            names = ['Shield', 'Power', 'Charge']
            actives = [getattr(game.player.combat, 'shield_timer', 0) > 0, getattr(game.player.combat, 'power_timer', 0) > 0, False]
        elif game.player.cls == 'Ranger':
            names = ['Triple', 'Sniper', 'Speed']
            actives = [game.player.triple_timer > 0, game.player.sniper_ready, game.player.speed_timer > 0]
        else:
            names = ['Fireball', 'Cold', 'Missile']
            actives = [False, False, False]
        cds = [game.player.skill_cd1, game.player.skill_cd2, game.player.skill_cd3]
        maxcds = [max(1, game.player.skill_cd1_max), max(1, game.player.skill_cd2_max), max(1, game.player.skill_cd3_max)]
        for i in range(3):
            rx = sbx + i * (slot_w + 8)
            ry = sby
            pygame.draw.rect(screen, (40, 40, 50), pygame.Rect(rx, ry, slot_w, slot_h), border_radius=6)
            if actives[i]:
                pygame.draw.rect(screen, (120, 210, 220), pygame.Rect(rx - 2, ry - 2, slot_w + 4, slot_h + 4), width=2, border_radius=8)
            if cds[i] > 0:
                pct = cds[i] / maxcds[i]
                h = int(slot_h * pct)
                overlay = pygame.Rect(rx, ry + (slot_h - h), slot_w, h)
                try:
                    # try to draw semi-transparent overlay if supported
                    pygame.draw.rect(screen, (0, 0, 0, 120), overlay)
                except Exception:
                    pygame.draw.rect(screen, (0, 0, 0), overlay)
                secs = max(0.0, cds[i] / FPS)
                draw_text(screen, f"{secs:.0f}", (rx + 12, ry + 12), (220, 220, 220), size=18, bold=True)
            draw_text(screen, str(i + 1), (rx + 2, ry + 2), (200, 200, 200), size=14)
            draw_text(screen, names[i], (rx + 2, ry + slot_h - 14), (180, 180, 200), size=12)

        # Consumable hotbar (delegated to inventory)
        try:
            game.inventory.draw_consumable_hotbar()
        except Exception:
            logger.exception("Inventory hotbar draw failed")

        # Timed status texts (speed, jump boost etc.)
        if getattr(game.player, 'speed_potion_timer', 0) > 0:
            secs = max(0, int(game.player.speed_potion_timer / FPS))
            draw_text(screen, f"Haste {secs}s", (WIDTH - 180, HEIGHT - 120), (255, 220, 140), size=16, bold=True)
        if getattr(game.player, 'jump_boost_timer', 0) > 0:
            secs = max(0, int(game.player.jump_boost_timer / FPS))
            draw_text(screen, f"Skybound {secs}s", (WIDTH - 180, HEIGHT - 140), (200, 220, 255), size=16, bold=True)
        if getattr(game.player, 'stamina_boost_timer', 0) > 0:
            secs = max(0, int(game.player.stamina_boost_timer / FPS))
            draw_text(screen, f"Cavern Brew {secs}s", (WIDTH - 180, HEIGHT - 160), (150, 255, 180), size=16, bold=True)

        # Other special labels
        if getattr(game.player, 'lucky_charm_timer', 0) > 0:
            secs = max(0, int(game.player.lucky_charm_timer / FPS))
            draw_text(screen, f"Lucky! {secs}s", (WIDTH - 180, HEIGHT - 180), (255, 215, 0), size=16, bold=True)
        if getattr(game.player, 'phoenix_feather_active', False):
            draw_text(screen, "Phoenix Blessing", (WIDTH - 180, HEIGHT - 200), (255, 150, 50), size=16, bold=True)

        # Time crystal enemy effect
        time_crystal_active = any(getattr(e, 'slow_remaining', 0) > 0 for e in game.enemies if getattr(e, 'alive', False))
        if time_crystal_active:
            draw_text(screen, "Time Distorted", (WIDTH - 180, HEIGHT - 220), (150, 150, 255), size=16, bold=True)

        # Gameplay hint text
        draw_text(screen,
                  "Move A/D | Jump Space/K | Dash Shift/J | Attack L/Mouse | Up/Down+Attack for Up/Down slash (Down=Pogo) | Shop F6 | God F1 | No-clip: Double-space in god mode (WASD to float)",
                  (12, HEIGHT - 28), (180, 180, 200), size=16)

        # God/no-clip tags
        hud_x = WIDTH - 64
        if getattr(game.player, 'no_clip', False):
            draw_text(screen, "NO-CLIP", (hud_x, 8), (200, 100, 255), bold=True)
            hud_x -= 8
            if getattr(game.player, 'floating_mode', False):
                draw_text(screen, "FLOAT", (hud_x, 8), (100, 255, 200), bold=True)
                hud_x -= 8
        if getattr(game.player, 'god', False):
            draw_text(screen, "GOD", (hud_x, 8), (255, 200, 80), bold=True)

        # Area overlay label
        if getattr(game, 'debug_show_area_overlay', False):
            try:
                area_label = game._get_player_area_labels()
                if area_label:
                    draw_text(screen, f"AREA: {area_label}", (WIDTH - 260, 8), (160, 220, 255), size=12)
                else:
                    draw_text(screen, "AREA: NONE", (WIDTH - 260, 8), (120, 160, 200), size=12)
            except Exception:
                pass

        # Boss hint
        if getattr(game.level, 'is_boss_room', False) and any(getattr(e, 'alive', False) for e in game.enemies):
            draw_text(screen, "Defeat the boss to open the door", (WIDTH // 2 - 160, 8), (255, 120, 120), size=16)

    except Exception:
        logger.exception("Unhandled exception in HUD draw")
