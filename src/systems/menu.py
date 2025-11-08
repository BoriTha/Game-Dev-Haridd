import sys
import pygame
from config import WIDTH, HEIGHT, FPS, LEVEL_TYPE, DIFFICULTY, LEVEL_TYPES, DIFFICULTY_LEVELS
from ..core.utils import draw_text, get_font
from ..level.level import Level, ROOM_COUNT
from ..entities.entities import Player, hitboxes, floating
from .camera import Camera


class Menu:
    def __init__(self, game):
        self.game = game
        self.screen = game.screen
        self.clock = game.clock
        
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
            self.screen.fill((12, 12, 18))
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
            "  F2: Refill Consumables",
            "  F3: Toggle Enemy Vision Rays",
            "  F4: Open Debugger Menu",
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
        """Blocking title menu: Start Game / Class Select / How to Play / Quit.
        Sets self.game.selected_class and allows basic generation config.
        """
        # 1. Start Game, 2. Class Select, 3. Generation Options, 4. How to Play, 5. Quit
        options = ["Start Game", "Class Select", "Generation Options", "How to Play", "Quit"]
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
                        if choice == "Start Game":
                            return
                        elif choice == "Class Select":
                            self.game.selected_class = self.select_class()
                        elif choice == "Generation Options":
                            self.generation_options_menu()
                        elif choice == "How to Play":
                            self.how_to_play_screen()
                        elif choice == "Quit":
                            pygame.quit(); sys.exit()
                    # Hotkeys
                    elif ev.key in (pygame.K_1, pygame.K_s):
                        return
                    elif ev.key in (pygame.K_2, pygame.K_c):
                        self.game.selected_class = self.select_class()
                    elif ev.key in (pygame.K_3, pygame.K_g):
                        self.generation_options_menu()
                    elif ev.key in (pygame.K_4, pygame.K_h):
                        self.how_to_play_screen()
                    elif ev.key in (pygame.K_5, pygame.K_q):
                        pygame.quit(); sys.exit()

            # draw title menu
            self.screen.fill((8, 8, 12))
            draw_text(self.screen, "HARIDD", (WIDTH//2 - 120, 60), (255,220,140), size=60, bold=True)
            draw_text(self.screen, "A tiny action roguelite", (WIDTH//2 - 150, 112), (180,180,200), size=20)
            for i, opt in enumerate(options):
                y = 200 + i*52
                col = (255,220,140) if i == idx else (200,200,200)
                draw_text(self.screen, f"{i+1}. {opt}", (WIDTH//2 - 160, y), col, size=28)
            # Summary line with current class and generation settings
            gen_mode = "ON" if getattr(self.game, "user_wants_procedural", getattr(self.game, "use_procedural", True)) else "OFF"
            lt = getattr(self.game, "level_type", LEVEL_TYPE)
            diff = getattr(self.game, "difficulty", DIFFICULTY)
            ws = getattr(self.game, "world_seed", None)
            seed_txt = f"Seed: {ws}" if ws is not None else "Seed: (auto)"
            draw_text(self.screen,
                      f"Class: {self.game.selected_class} | Mode: {gen_mode} {lt} D{diff} | {seed_txt}",
                      (WIDTH//2 - 260, HEIGHT-96), (180,200,220), size=18)
            draw_text(self.screen,
                      "Use Up/Down, Enter to select • 1-5 hotkeys",
                      (WIDTH//2 - 210, HEIGHT-64), (160,160,180), size=16)
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
                        # Restart run via centralized logic so procedural vs legacy
                        # behavior is respected and all restarts go through _load_level.
                        self.game.restart_run()
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
                            # Go back to title menu, allow user to adjust options,
                            # then start fresh level 0 respecting user_wants_procedural.
                            self.title_screen()
                            self.game.level_index = 0
                            self.game._load_level(self.game.level_index, initial=True)
                            sx, sy = self.game.level.spawn
                            self.game.player = Player(sx, sy, cls=self.game.selected_class)
                            self.game.enemies = self.game.level.enemies
                            self.game.inventory._refresh_inventory_defaults()
                            hitboxes.clear(); floating.clear()
                            self.game.camera = Camera()
                            return
                        elif choice == "Quit":
                            pygame.quit(); sys.exit()
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

    def generation_options_menu(self):
        """
        Simple blocking menu to configure procedural generation:
        - Toggle procedural vs static (stores user intent)
        - Cycle level type
        - Cycle difficulty
        - Enter / randomize world seed
        """
        # Ensure defaults exist
        if not hasattr(self.game, "user_wants_procedural"):
            # Fallback to existing flag if present, else default True
            default_proc = getattr(self.game, "use_procedural", True)
            self.game.user_wants_procedural = bool(default_proc)
        if not hasattr(self.game, "level_type"):
            self.game.level_type = LEVEL_TYPE
        if not hasattr(self.game, "difficulty"):
            self.game.difficulty = DIFFICULTY
        # Keep internal use_procedural in sync for menus/HUD; actual loads derive per-call.
        self.game.use_procedural = bool(self.game.user_wants_procedural)

        idx = 0
        options = ["Use Procedural Generation", "Level Type", "Difficulty", "World Seed", "Randomize Seed", "Back"]
        typing_seed = False
        seed_str = str(getattr(self.game, "world_seed", ""))

        while True:
            self.clock.tick(FPS)
            for ev in pygame.event.get():
                if ev.type == pygame.QUIT:
                    pygame.quit(); sys.exit()
                elif ev.type == pygame.KEYDOWN:
                    if typing_seed:
                        if ev.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
                            # Commit typed seed
                            try:
                                if seed_str.strip():
                                    new_seed = int(seed_str.strip())
                                    self.game.seed_manager.set_world_seed(new_seed)
                                    self.game.world_seed = new_seed
                                else:
                                    # Empty: auto-generate by reinitializing SeedManager
                                    self.game.seed_manager = self.game.seed_manager.__class__()
                                    self.game.world_seed = self.game.seed_manager.get_world_seed()
                            except ValueError:
                                # Ignore invalid input, keep previous seed
                                pass
                            typing_seed = False
                        elif ev.key == pygame.K_ESCAPE:
                            typing_seed = False
                        elif ev.key == pygame.K_BACKSPACE:
                            seed_str = seed_str[:-1]
                        elif ev.unicode.isdigit():
                            if len(seed_str) < 10:
                                seed_str += ev.unicode
                        continue

                    if ev.key == pygame.K_ESCAPE:
                        return
                    elif ev.key == pygame.K_UP:
                        idx = (idx - 1) % len(options)
                    elif ev.key == pygame.K_DOWN:
                        idx = (idx + 1) % len(options)
                    elif ev.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
                        choice = options[idx]
                        if choice == "Use Procedural Generation":
                            # Update user intent only; actual load logic consults this flag.
                            self.game.user_wants_procedural = not bool(self.game.user_wants_procedural)
                            # Keep display/helper flag aligned for now.
                            self.game.use_procedural = bool(self.game.user_wants_procedural)
                        elif choice == "Level Type":
                            cur = getattr(self.game, "level_type", LEVEL_TYPE)
                            types = LEVEL_TYPES
                            if cur in types:
                                ni = (types.index(cur) + 1) % len(types)
                            else:
                                ni = 0
                            self.game.level_type = types[ni]
                        elif choice == "Difficulty":
                            cur = getattr(self.game, "difficulty", DIFFICULTY)
                            levels = DIFFICULTY_LEVELS
                            if cur in levels:
                                ni = (levels.index(cur) + 1) % len(levels)
                            else:
                                ni = 0
                            self.game.difficulty = levels[ni]
                        elif choice == "World Seed":
                            typing_seed = True
                            seed_str = str(getattr(self.game, "world_seed", ""))
                        elif choice == "Randomize Seed":
                            # Rebuild SeedManager with random seed
                            self.game.seed_manager = self.game.seed_manager.__class__()
                            self.game.world_seed = self.game.seed_manager.get_world_seed()
                        elif choice == "Back":
                            return

            # Draw menu UI
            self.screen.fill((10, 10, 16))
            draw_text(self.screen, "GENERATION OPTIONS", (WIDTH//2 - 210, 40), (255,220,140), size=40, bold=True)

            # Reflect user intent in UI; generation failures must not override this.
            gen_mode = "ON" if self.game.user_wants_procedural else "OFF"
            lt = getattr(self.game, "level_type", LEVEL_TYPE)
            diff = getattr(self.game, "difficulty", DIFFICULTY)
            ws = getattr(self.game, "world_seed", None)

            values = [
                f"Procedural Generation: {gen_mode}",
                f"Level Type: {lt}",
                f"Difficulty: {diff}",
                f"World Seed: {seed_str if typing_seed else (ws if ws is not None else '(auto)')}",
                "Randomize Seed",
                "Back"
            ]

            base_y = 140
            for i, label in enumerate(options):
                y = base_y + i * 40
                col_bg = (70, 70, 90) if i == idx else (40, 40, 60)
                col_fg = (255,220,140) if i == idx else (200,200,210)
                rect = pygame.Rect(WIDTH//2 - 260, y - 6, 520, 32)
                pygame.draw.rect(self.screen, col_bg, rect, border_radius=8)
                draw_text(self.screen, values[i], (rect.x + 16, y), col_fg, size=22)

            hint = "Enter: Apply  •  Esc: Back  •  Type digits for seed when 'World Seed' selected"
            draw_text(self.screen, hint, (WIDTH//2 - 320, HEIGHT - 56), (150,150,180), size=16)
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