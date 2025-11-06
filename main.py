import sys
import pygame
from config import WIDTH, HEIGHT, FPS, BG, WHITE, CYAN
from utils import draw_text, get_font
from camera import Camera
from level import Level
from entities import Player, hitboxes, floating

class Game:
    def __init__(self):
        pygame.init()
        self.screen = pygame.display.set_mode((WIDTH, HEIGHT))
        # Window caption — show game title
        pygame.display.set_caption("Haridd")
        self.clock = pygame.time.Clock()
        self.font_small = get_font(18)
        self.font_big = get_font(32, bold=True)
        self.camera = Camera()

        # Title flow first: How to Play -> Class Select -> Play Game
        self.selected_class = 'Knight'  # default if player skips class select
        # Developer cheat toggles
        self.cheat_infinite_mana = False
        self.cheat_zero_cooldown = False
        self.title_screen()

        self.level_index = 0
        self.level = Level(self.level_index)
        sx, sy = self.level.spawn
        # create player with chosen class
        self.player = Player(sx, sy, cls=self.selected_class)
        self.enemies = self.level.enemies

    def switch_room(self, delta):
        # wrap using Level.ROOM_COUNT so new rooms are handled
        self.level_index = (self.level_index + delta) % Level.ROOM_COUNT
        self.level = Level(self.level_index)
        sx, sy = self.level.spawn
        self.player.rect.topleft = (sx, sy)
        self.enemies = self.level.enemies
        hitboxes.clear(); floating.clear()

    def select_class(self):
        """Blocking title + class selection screen. Returns chosen class name."""
        options = ["Knight", "Ranger", "Wizard"]
        idx = 0
        while True:
            self.clock.tick(FPS)
            for ev in pygame.event.get():
                if ev.type == pygame.QUIT:
                    pygame.quit(); sys.exit()
                elif ev.type == pygame.KEYDOWN:
                    if ev.key == pygame.K_ESCAPE:
                        pygame.quit(); sys.exit()
                    elif ev.key == pygame.K_UP:
                        idx = (idx - 1) % len(options)
                    elif ev.key == pygame.K_DOWN:
                        idx = (idx + 1) % len(options)
                    elif ev.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
                        return options[idx]
                    elif ev.key == pygame.K_1:
                        return options[0]
                    elif ev.key == pygame.K_2:
                        return options[1]
                    elif ev.key == pygame.K_3:
                        return options[2]

            # draw
            self.screen.fill(BG)
            title_font = get_font(48, bold=True)
            draw_text(self.screen, "HARIDD", (WIDTH//2 - 120, 60), (255,220,140), size=48, bold=True)
            draw_text(self.screen, "Choose your class:", (WIDTH//2 - 120, 140), (200,200,220), size=22)
            for i, opt in enumerate(options):
                y = 200 + i*48
                col = (255,220,140) if i == idx else (200,200,200)
                draw_text(self.screen, f"{i+1}. {opt}", (WIDTH//2 - 80, y), col, size=28)
            draw_text(self.screen, "Use Up/Down or 1-3, Enter to confirm", (WIDTH//2 - 160, HEIGHT-64), (160,160,180), size=16)
            pygame.display.flip()

    def how_to_play_screen(self):
        """Blocking help/instructions screen. Return to caller on Esc/Enter."""
        lines = [
            "Goal: Clear rooms and defeat the boss to progress.",
            "",
            "Controls:",
            "  Move: A / D",
            "  Jump: Space or K",
            "  Dash: Left Shift or J",
            "  Attack: L or Left Mouse",
            "  Up/Down + Attack: Up/Down slash (Down = Pogo)",
            "",
            "Classes:",
            "  Knight: Tanky melee; shield/power/charge skills.",
            "  Ranger: Arrows, charge shot, triple-shot.",
            "  Wizard: Fireball, cold field, homing missiles.",
            "",
            "Tips:",
            "  - Invulnerability frames protect after getting hit.",
            "  - Doors in boss rooms stay locked until the boss is defeated.",
            "  - Enemies don't hurt each other; watch telegraphs (! / !!).",
            "",
            "Dev Cheats:",
            "  F1: Toggle God Mode",
            "  F2: Teleport to Boss Room",
        ]
        while True:
            self.clock.tick(FPS)
            for ev in pygame.event.get():
                if ev.type == pygame.QUIT:
                    pygame.quit(); sys.exit()
                elif ev.type == pygame.KEYDOWN:
                    if ev.key in (pygame.K_ESCAPE, pygame.K_RETURN, pygame.K_KP_ENTER):
                        return

            self.screen.fill((12, 12, 18))
            draw_text(self.screen, "HOW TO PLAY", (WIDTH//2 - 140, 40), (255,220,140), size=48, bold=True)
            y = 120
            for s in lines:
                draw_text(self.screen, s, (64, y), (200,200,210), size=20)
                y += 28
            draw_text(self.screen, "Press Esc or Enter to return", (WIDTH//2 - 180, HEIGHT-48), (160,160,180), size=16)
            pygame.display.flip()

    def title_screen(self):
        """Blocking title menu: How to Play / Class Select / Play Game / Quit.
        Sets self.selected_class and returns when Play Game is chosen.
        """
        options = ["How to Play", "Class Select", "Play Game", "Quit"]
        idx = 0
        while True:
            self.clock.tick(FPS)
            for ev in pygame.event.get():
                if ev.type == pygame.QUIT:
                    pygame.quit(); sys.exit()
                elif ev.type == pygame.KEYDOWN:
                    if ev.key == pygame.K_ESCAPE:
                        pygame.quit(); sys.exit()
                    elif ev.key == pygame.K_UP:
                        idx = (idx - 1) % len(options)
                    elif ev.key == pygame.K_DOWN:
                        idx = (idx + 1) % len(options)
                    elif ev.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
                        choice = options[idx]
                        if choice == "How to Play":
                            self.how_to_play_screen()
                        elif choice == "Class Select":
                            self.selected_class = self.select_class()
                        elif choice == "Play Game":
                            return
                        elif choice == "Quit":
                            pygame.quit(); sys.exit()
                    elif ev.key in (pygame.K_1, pygame.K_h):
                        self.how_to_play_screen()
                    elif ev.key in (pygame.K_2, pygame.K_c):
                        self.selected_class = self.select_class()
                    elif ev.key in (pygame.K_3, pygame.K_p):
                        return
                    elif ev.key in (pygame.K_4, pygame.K_q):
                        pygame.quit(); sys.exit()

            # draw title menu
            self.screen.fill((8, 8, 12))
            draw_text(self.screen, "HARIDD", (WIDTH//2 - 120, 60), (255,220,140), size=60, bold=True)
            draw_text(self.screen, "A tiny action roguelite", (WIDTH//2 - 150, 112), (180,180,200), size=20)
            for i, opt in enumerate(options):
                y = 200 + i*52
                col = (255,220,140) if i == idx else (200,200,200)
                draw_text(self.screen, f"{i+1}. {opt}", (WIDTH//2 - 120, y), col, size=28)
            draw_text(self.screen, f"Selected Class: {self.selected_class}", (WIDTH//2 - 150, HEIGHT-96), (180,200,220), size=20)
            draw_text(self.screen, "Use Up/Down, Enter to select • 1-4 hotkeys", (WIDTH//2 - 210, HEIGHT-64), (160,160,180), size=16)
            pygame.display.flip()

    def goto_room(self, index):
        # go to an absolute room index (wrapped)
        self.level_index = index % Level.ROOM_COUNT
        self.level = Level(self.level_index)
        sx, sy = self.level.spawn
        self.player.rect.topleft = (sx, sy)
        self.enemies = self.level.enemies
        hitboxes.clear(); floating.clear()

    def update(self):
        self.player.input(self.level, self.camera)
        self.player.physics(self.level)

        # If player died, show restart menu
        if getattr(self.player, 'dead', False):
            self.game_over_screen()
            return

        # Apply developer cheats each frame
        if self.cheat_infinite_mana and hasattr(self.player, 'max_mana'):
            self.player.mana = getattr(self.player, 'max_mana', self.player.mana)
        if self.cheat_zero_cooldown:
            # Force cooldowns to zero if present
            for attr in ('skill_cd1', 'skill_cd2', 'skill_cd3'):
                if hasattr(self.player, attr):
                    setattr(self.player, attr, 0)

        for d in self.level.doors:
            if self.player.rect.colliderect(d):
                # Gate boss rooms: require boss defeat before door works
                if getattr(self.level, 'is_boss_room', False):
                    if any(getattr(e, 'alive', False) for e in self.enemies):
                        # door locked; stay in room
                        pass
                    else:
                        self.switch_room(+1)
                        break
                else:
                    self.switch_room(+1)
                    break

        for e in self.enemies:
            e.tick(self.level, self.player)

        for hb in list(hitboxes):
            hb.tick()
            # if projectile hits solids, explode or die
            collided_solid = False
            for s in self.level.solids:
                if hb.rect.colliderect(s):
                    collided_solid = True
                    break
            if collided_solid:
                if getattr(hb, 'aoe_radius', 0) > 0 and not getattr(hb, 'visual_only', False):
                    cx, cy = hb.rect.center
                    for e2 in self.enemies:
                        if getattr(e2, 'alive', False):
                            dx = e2.rect.centerx - cx
                            dy = e2.rect.centery - cy
                            if (dx*dx + dy*dy) ** 0.5 <= hb.aoe_radius:
                                e2.hit(hb, self.player)
                # remove visual-only hitboxes or projectiles
                if hb in hitboxes:
                    hitboxes.remove(hb)
                continue
            # enemy hitboxes can affect player (damage/stun). Ignore player's own.
            if getattr(hb, 'owner', None) is not self.player:
                # AOE against player
                if getattr(hb, 'aoe_radius', 0) > 0 and not getattr(hb, 'visual_only', False):
                    cx, cy = hb.rect.center
                    dx = self.player.rect.centerx - cx
                    dy = self.player.rect.centery - cy
                    if (dx*dx + dy*dy) ** 0.5 <= getattr(hb, 'aoe_radius', 0):
                        # apply stun tag if present
                        if getattr(hb, 'tag', None) == 'stun':
                            self.player.stunned = max(self.player.stunned, int(0.8 * FPS))
                        # apply damage if any
                        if getattr(hb, 'damage', 0) > 0:
                            kx, ky = hb.dir_vec if getattr(hb, 'dir_vec', None) else (0, -1)
                            self.player.damage(hb.damage, (int(kx*3), -6))
                        # consume the AOE
                        hb.alive = False
                # direct projectile/contact against player
                elif hb.rect.colliderect(self.player.rect) and not getattr(hb, 'visual_only', False):
                    if getattr(hb, 'tag', None) == 'stun':
                        self.player.stunned = max(self.player.stunned, int(0.8 * FPS))
                    if getattr(hb, 'damage', 0) > 0:
                        kx, ky = hb.dir_vec if getattr(hb, 'dir_vec', None) else (0, -1)
                        self.player.damage(hb.damage, (int(kx*3), -6))
                    # non-piercing projectiles disappear after hitting player
                    if (getattr(hb, 'vx', 0) or getattr(hb, 'vy', 0)) and not getattr(hb, 'pierce', False):
                        hb.alive = False
            # moving/projectile hitboxes may hit enemies; support AOE hitboxes
            # Only allow player-owned hitboxes to damage enemies (no enemy friendly-fire)
            if getattr(hb, 'aoe_radius', 0) > 0 and getattr(hb, 'owner', None) is self.player:
                # visual-only AOE (e.g., cold feet) should not apply instant damage
                if getattr(hb, 'visual_only', False):
                    if not hb.alive:
                        hitboxes.remove(hb)
                    continue
                # check collision with any enemy, explode on first hit
                exploded = False
                for e in self.enemies:
                    if getattr(e, 'alive', False) and hb.rect.colliderect(e.rect):
                        # explode: apply damage to all enemies within radius
                        cx, cy = hb.rect.center
                        for e2 in self.enemies:
                            if getattr(e2, 'alive', False):
                                dx = e2.rect.centerx - cx
                                dy = e2.rect.centery - cy
                                if (dx*dx + dy*dy) ** 0.5 <= hb.aoe_radius:
                                    e2.hit(hb, self.player)
                        exploded = True
                        hb.alive = False
                        break
                if not hb.alive:
                    hitboxes.remove(hb)
                continue

            # Only player-owned hitboxes damage enemies
            if getattr(hb, 'owner', None) is self.player:
                for e in self.enemies:
                    if getattr(e, 'alive', False) and hb.rect.colliderect(e.rect):
                        e.hit(hb, self.player)
                        # moving projectiles should disappear after first enemy hit unless they can pierce
                        if getattr(hb, 'vx', 0) or getattr(hb, 'vy', 0):
                            if not getattr(hb, 'pierce', False):
                                hb.alive = False
                                break
            if not hb.alive:
                hitboxes.remove(hb)

        for dn in list(floating):
            dn.tick()
            if dn.life <= 0:
                floating.remove(dn)

        self.camera.update(self.player.rect)

    def draw(self):
        self.screen.fill(BG)
        self.level.draw(self.screen, self.camera)
        for e in self.enemies:
            e.draw(self.screen, self.camera)
        for hb in hitboxes:
            hb.draw(self.screen, self.camera)
        self.player.draw(self.screen, self.camera)
        for dn in floating:
            dn.draw(self.screen, self.camera, self.font_small)

        # HUD
        x, y = 16, 16
        for i in range(self.player.max_hp):
            c = (80,200,120) if i < self.player.hp else (60,80,60)
            pygame.draw.rect(self.screen, c, pygame.Rect(x+i*18, y, 16, 10), border_radius=3)
        y += 16
        if self.player.dash_cd:
            pct = 1 - (self.player.dash_cd / 24)
            pygame.draw.rect(self.screen, (80,80,80), pygame.Rect(x, y, 120, 6), border_radius=3)
            pygame.draw.rect(self.screen, CYAN, pygame.Rect(x, y, int(120*pct), 6), border_radius=3)
        # stamina bar (if player has stamina)
        y += 12
        if hasattr(self.player, 'stamina') and hasattr(self.player, 'max_stamina'):
            spct = max(0.0, min(1.0, self.player.stamina / max(1e-6, self.player.max_stamina)))
            pygame.draw.rect(self.screen, (60,60,60), pygame.Rect(x, y, 120, 6), border_radius=3)
            pygame.draw.rect(self.screen, (200,180,60), pygame.Rect(x, y, int(120*spct), 6), border_radius=3)
            y += 12
        # mana bar
        if hasattr(self.player, 'mana') and hasattr(self.player, 'max_mana'):
            mpct = max(0.0, min(1.0, self.player.mana / max(1e-6, self.player.max_mana)))
            pygame.draw.rect(self.screen, (60,60,60), pygame.Rect(x, y, 120, 6), border_radius=3)
            pygame.draw.rect(self.screen, CYAN, pygame.Rect(x, y, int(120*mpct), 6), border_radius=3)
            y += 12

        # show ranger charge bar when charging
        if getattr(self.player, 'cls', '') == 'Ranger' and getattr(self.player, 'charging', False):
            pct = max(0.0, min(1.0, self.player.charge_time / max(1, self.player.charge_threshold)))
            pygame.draw.rect(self.screen, (60,60,60), pygame.Rect(x, y, 120, 6), border_radius=3)
            pygame.draw.rect(self.screen, (200,180,60), pygame.Rect(x, y, int(120*pct), 6), border_radius=3)
            # show '!' when fully charged
            if pct >= 1.0:
                draw_text(self.screen, "!", (x + 124, y-6), (255,80,80), size=18, bold=True)
            y += 12

        # show selected class on HUD
        draw_text(self.screen, f"Class: {getattr(self.player, 'cls', 'Unknown')}", (WIDTH-220, 8), (200,200,200), size=16)

        # Skill bar (MOBA-style): show 1/2/3 cooldowns and active highlights
        sbx, sby = 16, HEIGHT - 80
        slot_w, slot_h = 46, 46
        # Names per class
        if self.player.cls == 'Knight':
            names = ['Shield', 'Power', 'Charge']
            actives = [self.player.shield_timer>0, self.player.power_timer>0, False]
        elif self.player.cls == 'Ranger':
            names = ['Triple', 'Sniper', 'Speed']
            actives = [self.player.triple_timer>0, self.player.sniper_ready, self.player.speed_timer>0]
        else:
            names = ['Fireball', 'Cold', 'Missile']
            actives = [False, False, False]
        cds = [self.player.skill_cd1, self.player.skill_cd2, self.player.skill_cd3]
        maxcds = [max(1,self.player.skill_cd1_max), max(1,self.player.skill_cd2_max), max(1,self.player.skill_cd3_max)]
        for i in range(3):
            rx = sbx + i*(slot_w+8)
            ry = sby
            # slot background
            pygame.draw.rect(self.screen, (40,40,50), pygame.Rect(rx, ry, slot_w, slot_h), border_radius=6)
            # active border glow
            if actives[i]:
                pygame.draw.rect(self.screen, (120,210,220), pygame.Rect(rx-2, ry-2, slot_w+4, slot_h+4), width=2, border_radius=8)
            # cooldown overlay
            if cds[i] > 0:
                pct = cds[i] / maxcds[i]
                h = int(slot_h * pct)
                overlay = pygame.Rect(rx, ry + (slot_h - h), slot_w, h)
                pygame.draw.rect(self.screen, (0,0,0,120), overlay)
                # remaining seconds text
                secs = max(0.0, cds[i]/FPS)
                draw_text(self.screen, f"{secs:.0f}", (rx + 12, ry + 12), (220,220,220), size=18, bold=True)
            # key label and name
            draw_text(self.screen, str(i+1), (rx+2, ry+2), (200,200,200), size=14)
            draw_text(self.screen, names[i], (rx+2, ry+slot_h-14), (180,180,200), size=12)

        draw_text(self.screen,
                  "Move A/D | Jump Space/K | Dash Shift/J | Attack L/Mouse | Up/Down+Attack for Up/Down slash (Down=Pogo)",
                  (12, HEIGHT-28), (180,180,200), size=16)
        draw_text(self.screen, f"Room {self.level_index+1}/{Level.ROOM_COUNT}", (12, 8), WHITE)
        if getattr(self.player, 'god', False):
            draw_text(self.screen, "GOD", (WIDTH-64, 8), (255,200,80), bold=True)
        # Boss room hint: lock door until boss defeated
        if getattr(self.level, 'is_boss_room', False) and any(getattr(e, 'alive', False) for e in self.enemies):
            draw_text(self.screen, "Defeat the boss to open the door", (WIDTH//2 - 160, 8), (255,120,120), size=16)

    def run(self):
        while True:
            self.clock.tick(FPS)
            for ev in pygame.event.get():
                if ev.type == pygame.QUIT:
                    pygame.quit(); sys.exit()
                elif ev.type == pygame.KEYDOWN:
                    if ev.key == pygame.K_ESCAPE:
                        # open pause menu instead of quitting
                        self.pause_menu()
                    # Developer cheats
                    elif ev.key == pygame.K_F1:
                        # toggle god mode
                        self.player.god = not getattr(self.player, 'god', False)
                        print(f"God mode {'ON' if self.player.god else 'OFF'}")
                    elif ev.key == pygame.K_F2:
                        # teleport to boss room (last room)
                        self.goto_room(Level.ROOM_COUNT - 1)
                    elif ev.key == pygame.K_F3:
                        # toggle infinite mana
                        self.cheat_infinite_mana = not self.cheat_infinite_mana
                        state = 'ON' if self.cheat_infinite_mana else 'OFF'
                        print(f"Cheat: Infinite Mana {state}")
                    elif ev.key == pygame.K_F4:
                        # toggle zero cooldown
                        self.cheat_zero_cooldown = not self.cheat_zero_cooldown
                        state = 'ON' if self.cheat_zero_cooldown else 'OFF'
                        print(f"Cheat: Zero Cooldown {state}")
                    elif ev.key == pygame.K_F5:
                        self.goto_room(0)
                    elif ev.key == pygame.K_F6:
                        self.goto_room(1)
                    elif ev.key == pygame.K_F7:
                        self.goto_room(2)
                    elif ev.key == pygame.K_F8:
                        self.goto_room(3)
                    elif ev.key == pygame.K_F9:
                        self.goto_room(4)
                    elif ev.key == pygame.K_F10:
                        self.goto_room(5)

            self.update()
            self.draw()
            pygame.display.flip()

    def game_over_screen(self):
        """Blocking game over / restart menu. Restart keeps the selected class."""
        font_big = get_font(48, bold=True)
        font_med = get_font(28)
        while True:
            self.clock.tick(FPS)
            for ev in pygame.event.get():
                if ev.type == pygame.QUIT:
                    pygame.quit(); sys.exit()
                elif ev.type == pygame.KEYDOWN:
                    if ev.key in (pygame.K_ESCAPE, pygame.K_q):
                        pygame.quit(); sys.exit()
                    if ev.key in (pygame.K_r, pygame.K_RETURN, pygame.K_KP_ENTER):
                        # restart: reset level, player and containers
                        self.level_index = 0
                        self.level = Level(self.level_index)
                        sx, sy = self.level.spawn
                        self.player = Player(sx, sy, cls=self.selected_class)
                        self.enemies = self.level.enemies
                        hitboxes.clear(); floating.clear()
                        self.camera = Camera()
                        return

            # draw overlay
            self.screen.fill((10, 10, 16))
            draw_text(self.screen, "YOU DIED", (WIDTH//2 - 120, HEIGHT//2 - 80), (220,80,80), size=48, bold=True)
            draw_text(self.screen, "Press R or Enter to Restart", (WIDTH//2 - 160, HEIGHT//2 - 8), (200,200,200), size=24)
            draw_text(self.screen, "Press Q or Esc to Quit", (WIDTH//2 - 140, HEIGHT//2 + 36), (180,180,180), size=20)
            pygame.display.flip()

    def pause_menu(self):
        """Blocking pause menu with Resume / Settings / Main Menu / Quit."""
        options = ["Resume", "Settings", "Main Menu", "Quit"]
        idx = 0
        while True:
            self.clock.tick(FPS)
            for ev in pygame.event.get():
                if ev.type == pygame.QUIT:
                    pygame.quit(); sys.exit()
                elif ev.type == pygame.KEYDOWN:
                    if ev.key in (pygame.K_ESCAPE, pygame.K_r):
                        return  # resume
                    elif ev.key == pygame.K_UP:
                        idx = (idx - 1) % len(options)
                    elif ev.key == pygame.K_DOWN:
                        idx = (idx + 1) % len(options)
                    elif ev.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
                        choice = options[idx]
                        if choice == "Resume":
                            return
                        elif choice == "Settings":
                            self.settings_screen()
                        elif choice == "Main Menu":
                            # go back to title menu (how-to/class select) and reset
                            self.selected_class = 'Knight'
                            self.title_screen()
                            self.level_index = 0
                            self.level = Level(self.level_index)
                            sx, sy = self.level.spawn
                            self.player = Player(sx, sy, cls=self.selected_class)
                            self.enemies = self.level.enemies
                            hitboxes.clear(); floating.clear()
                            self.camera = Camera()
                            return
                        elif choice == "Quit":
                            pygame.quit(); sys.exit()
                        # Show cheats status
                        cheat_msgs = []
                        if getattr(self.player, 'god', False):
                            cheat_msgs.append('GOD')
                        if getattr(self, 'cheat_infinite_mana', False):
                            cheat_msgs.append('IM')
                        if getattr(self, 'cheat_zero_cooldown', False):
                            cheat_msgs.append('ZCD')
                        if cheat_msgs:
                            draw_text(self.screen, ' '.join(cheat_msgs), (WIDTH-120, 28), (255,200,80), size=16, bold=True)
                    elif ev.key == pygame.K_q:
                        pygame.quit(); sys.exit()

            # draw pause overlay
            self.screen.fill((12, 12, 18))
            draw_text(self.screen, "PAUSED", (WIDTH//2 - 80, 60), (255,200,140), size=48, bold=True)
            for i, opt in enumerate(options):
                y = 180 + i*48
                col = (255,220,140) if i == idx else (200,200,200)
                draw_text(self.screen, f"{i+1}. {opt}", (WIDTH//2 - 80, y), col, size=28)
            draw_text(self.screen, "Use Up/Down, Enter to select, Esc/R to resume", (WIDTH//2 - 220, HEIGHT-64), (160,160,180), size=16)
            pygame.display.flip()

    def settings_screen(self):
        """Simple settings placeholder. Press Esc to go back."""
        while True:
            self.clock.tick(FPS)
            for ev in pygame.event.get():
                if ev.type == pygame.QUIT:
                    pygame.quit(); sys.exit()
                elif ev.type == pygame.KEYDOWN:
                    if ev.key in (pygame.K_ESCAPE, pygame.K_RETURN, pygame.K_KP_ENTER):
                        return

            self.screen.fill((10, 10, 14))
            draw_text(self.screen, "SETTINGS", (WIDTH//2 - 80, 60), (220,220,220), size=40, bold=True)
            draw_text(self.screen, "(No settings yet)", (WIDTH//2 - 120, HEIGHT//2 - 8), (180,180,180), size=22)
            draw_text(self.screen, "Press Esc or Enter to return", (WIDTH//2 - 160, HEIGHT-64), (140,140,140), size=16)
            pygame.display.flip()

if __name__ == '__main__':
    Game().run()
