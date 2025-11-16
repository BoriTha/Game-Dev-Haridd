# Haridd

A small action roguelite built with Python and Pygame. Fight through rooms, defeat the boss, and progress to the next area. ASCII room layouts map 1:1 to terrain in-game.

## Quick start (Windows)

```powershell
# From the project root
python -m pip install --upgrade pip
python -m pip install pygame
python main.py
```

If you have multiple Python versions installed, ensure you're using the right one:
```powershell
py -V            # shows Python version
py -m pip install pygame
py d:\game_dev\main.py
```

## Controls

- Move: A / D
- Jump: Space or K
- Dash: Left Shift or J
- Attack: L or Left Mouse
- Up/Down + Attack: Up/Down slash (Down = Pogo)
- Inventory: I (opens the mid-run inventory overlay)
- Consume slot 1 / 2 / 3: 4 / 5 / 6
- Pause: Esc

Dev cheats (for testing):
- F1: Toggle God Mode
- F2: Refill Consumables
- F3: Toggle Enemy Vision Rays
- F4: Toggle Enemy Nametags
- F5: Open the debugger menu
- F6: Toggle Shop
- F7: Add 1000 Money
- F8: Toggle Tile Inspector
- F9: Toggle Wall Jump Debug Visualization
- F10: Toggle Area Overlay (PCG room areas)
- F11: Follow door_exit_1 (PCG mode) / Reserved (Legacy mode)
- F12: Follow door_exit_2 (PCG mode) / Go to Boss Room (Legacy mode)
- Z: Toggle Camera Zoom
- Double-tap Space (in God Mode): Toggle No-clip + Floating Mode

## Menu flow

1. Title
   - How to Play: Controls, tips, and class overview
   - Class Select: Choose Knight / Ranger / Wizard
   - Play Game: Start with the selected class (defaults to Knight)
2. In-game
   - Pause (Esc): Resume, Settings (placeholder), Main Menu, or Quit

## Classes

- Knight: Tanky melee. Shield/Power/Charge skills. Lower mobility, strong survivability. Can parry attacks with shield skill.
- Ranger: Ranged damage. Charge shot, triple-shot that can bypass enemy i-frames, speed boost skill.
- Wizard: Spells. Fireball, cold field (area slow), homing magic missiles, plus teleport skill for mobility.

Each class has unique resource bars (stamina/mana) and cooldowns shown on the HUD.

### Inventory & consumables

- Press `I` in-game to open the inventory overlay. It shows:
  - Player stats, gear slots, a model preview, and a list of consumables.
  - Three consumable slots mapped to keys `4/5/6` with icons and names inside each slot.
  - A reminder footer explaining how to close the overlay.
- Default consumables:
  - **Health Flask** — restores 3 HP.
  - **Mana Vial** — restores 10 MP.
  - **Haste Draught** — grants a temporary "Haste" buff that speeds up attack/dash/skill cooldown recovery. A HUD label appears while it is active.
  - **Skyroot Elixir** — Higher jumps and triple-jump for 12s.
  - **Cavern Brew** — +25% stamina for 30s. Bar glows green.
- Consumables can also be refilled instantly from the debugger menu (F5 ➜ "Refill Consumables").

### Debugger menu

Press `F5` at any time during gameplay to open the debugger overlay. From there you can:

- Toggle God Mode, Infinite Mana, Zero Cooldown, and No-clip Mode without remembering individual hotkeys.
- Jump directly to any room or level via a teleport picker (works for both PCG and legacy modes).
- Enable/disable enemy vision rays to visualize their current line-of-sight target.
- Enable/disable enemy nametags to see enemy types above their sprites.
- Enable/disable area overlay to visualize PCG room areas and spawn zones.
- Instantly refill all consumable slots for quick testing of the hotbar interactions.
- Spawn items and equipment directly into inventory via the "Give Items" menu.
- Toggle PCG mode on/off (switch between procedural and static legacy levels).

## Gameplay notes

- Enemies telegraph strong attacks with `!` or `!!`.
- Enemy projectiles are visible. Enemy friendly-fire is disabled.
- Boss rooms lock doors until the boss is defeated (doors turn red; HUD shows a hint).
- Enemy line-of-sight (vision) rays can be toggled on/off from the debugger menu (F5) or with F3.
- Press `E` near doors to transition between rooms (proximity-based interaction).
- ASCII maps are parsed directly; each character is one tile wide.
  - `#` = solid wall
  - `.` = empty/air (floor in legacy mode)
  - `_` = platform (one-way collision from above)
  - `@` = breakable wall
  - `S` = player spawn point
  - `D` = door (entrance or exit)
   - `E` = Bug (basic enemy)
   - `f` = Frog
   - `r` = Archer
   - `w` = Wizard Caster
   - `a` = Assassin
   - `b` = Bee
   - `k` = Knight Monster (armored melee enemy)
   - `B` = Boss (classic)
   - `G` = Golem (boss)

## Monsters

Each enemy is drawn as a colored rectangle; during their invulnerability frames (shortly after being hit), they briefly use a darker variant of their color.

- Bug (`E`) — smart ground enemy
   - Color: RGB(180, 70, 160) violet; i-frames: RGB(120, 40, 100)
   - Behavior: Patrol/search/pursue using LOS; contact damage; can be slowed and take DOT; parry reflects damage.

- Frog (`f`) — telegraphed lunge
   - Color: RGB(80, 200, 80) green; i-frames: RGB(60, 120, 60)
   - Behavior: Shows `!` then performs a longer diagonal dash toward the player; touch damage on contact.

- Archer (`r`) — ranged shooter
   - Color: RGB(200, 200, 80) yellow; i-frames: RGB(120, 120, 60)
   - Skills: `!!` telegraph then fires an arrow (visible projectile) roughly matching player Ranger speed (10.0) and lifetime (120). Sidesteps if too close.

- Wizard Caster (`w`) — spellcaster
   - Color: RGB(180, 120, 220) lavender; i-frames: RGB(110, 80, 140)
   - Skills (with `!!` telegraph):
      - Bolt: fast, light projectile.
      - Missile: very fast, high-damage projectile.
      - Fireball: slower projectile that explodes with AoE (radius ~48).

- Assassin (`a`) - melee specialist
   - Color: RGB(60, 60, 80) dark slate; i-frames: RGB(40, 40, 60)
   - Patterns: Randomly chooses between `!` dash (diagonal dash, spawns short sword hitboxes while dashing) and `!!` forward slash (short sword hitbox).

- Bee (`b`) — hybrid dasher/shooter
   - Color: RGB(240, 180, 60) amber; i-frames: RGB(140, 120, 50)
   - Patterns: Chooses between `!` dash and `!!` ranged shot (arrow-like projectile; visible).

- Boss (`B`) — classic heavy
   - Color: RGB(200, 100, 40) orange-brown; i-frames: RGB(140, 80, 30)
   - Behavior: High HP, slow pursuit, strong contact damage; affected by slow/DOT; doors lock in boss rooms until defeated.

- Golem (`G`) — boss with multiple patterns
   - Color: RGB(140, 140, 160) steel; i-frames: RGB(100, 100, 120)
   - Patterns: `!` diagonal dash, `!!` shoot, `!!` radial stun (AoE) that applies a stun tag within ~72 radius.

- Knight Monster (`k`) — armored melee enemy
   - Color: RGB(100, 120, 140) dark blue-gray; i-frames: RGB(70, 85, 100)
   - Behavior: Armored ground enemy with shield and sword. Can block attacks from the front. Telegraphs strong sword strikes with `!` or `!!`.

## Project Structure

The codebase is organized into logical modules for better maintainability:

```
├── main.py                    # Entry point, game loop, menus, HUD
├── config.py                  # Game configuration constants
├── README.md                  # This file
├── guide.txt                  # Quick reference guide
├── arument_item.json          # Armament item definitions
│
├── config/                    # Configuration files
│   └── pcg_config.json       # PCG runtime settings (seed, use_pcg flag)
│
├── src/                       # Core source code
│   ├── entities/             # Entity system
│   │   ├── entities.py       # Entity factory and exports
│   │   ├── player_entity.py  # Player class
│   │   ├── enemy_entities.py # All enemy types
│   │   ├── entity_common.py  # Shared entity utilities
│   │   └── components/       # Component system
│   │       ├── physics_component.py
│   │       ├── combat_component.py
│   │       └── vision_component.py
│   │
│   ├── systems/              # Game systems
│   │   ├── inventory.py      # Inventory management
│   │   ├── items.py          # Item definitions and icon loading
│   │   ├── shop.py           # Shop system
│   │   ├── menu.py           # Menu system
│   │   ├── camera.py         # Camera management with zoom
│   │   ├── area_effects.py   # Area effect system (slow, DOT, etc.)
│   │   └── on_hit_effects.py # On-hit effect system
│   │
│   ├── level/                # Level generation
│   │   ├── pcg_generator_simple.py  # Procedural generation
│   │   ├── pcg_level_data.py        # PCG level data structures
│   │   ├── pcg_postprocess.py       # Post-processing for PCG
│   │   ├── level_loader.py          # Level loading singleton
│   │   ├── config_loader.py         # PCG config loader
│   │   ├── door_system.py           # Door interaction system
│   │   ├── door_placement.py        # Door placement logic
│   │   ├── door_utils.py            # Door utilities
│   │   └── legacy_level.py          # Legacy static levels (preserved, do not modify)
│   │
│   ├── tiles/                # Tile system
│   │   ├── tile_types.py      # TileType enum definitions
│   │   ├── tile_data.py       # TileData dataclass
│   │   ├── tile_registry.py   # TileRegistry singleton
│   │   ├── tile_parser.py     # ASCII map parser
│   │   ├── tile_renderer.py   # Tile rendering
│   │   └── tile_collision.py  # Tile collision detection
│   │
│   ├── ai/                   # AI and behaviors
│   │   └── enemy_movement.py # Enemy AI patterns
│   │
│   ├── core/                 # Core utilities
│   │   ├── utils.py          # Helper functions
│   │   ├── input.py          # InputHandler for centralized event processing
│   │   ├── interaction.py    # Proximity interaction system
│   │   ├── movement.py       # Movement utilities
│   │   └── constants.py      # Additional constants
│   │
│   ├── debug/                # Debug tools
│   │   └── overlays.py       # Debug overlay rendering
│   │
│   └── ui/                   # UI components
│       └── hud.py            # HUD rendering
│
├── docs/                     # Documentation
│   ├── developer_cheat(must read).txt
│   └── (other documentation)
│
├── assets/                   # Game assets
│   ├── consumable/           # Consumable item icons
│   └── armament/             # Armament item icons
│
└── tests/                    # Test suite
    └── test_lifesteal.py
```

### Key Files:
- **`main.py`** — Game loop, menus (Title/How to Play/Class Select/Pause), HUD, collisions, level loading
- **`config.py`** — Config constants (sizes, colors, FPS, physics parameters, tile constants)
- **`src/entities/`** — All player and enemy code with component-based architecture (CombatComponent, PhysicsComponent, VisionComponent)
- **`src/level/`** — Procedural level generation system (PCG) and legacy static levels
- **`src/systems/`** — Inventory, shop, menu, camera, and area effect systems
- **`src/tiles/`** — Complete tile system with types, registry, collision, rendering
- **`src/core/input.py`** — Centralized input/event handling via InputHandler class
- **`config/pcg_config.json`** — Runtime PCG configuration (seed, use_pcg flag)

## Collaboration tips

- Use a consistent Python version (3.11+ recommended, 3.13+ supported) and Pygame 2.6+.
- Before pushing, run the game locally to verify no errors (`python main.py`).
- Keep rooms ASCII-aligned (each line same width). Unknown characters are treated as empty.
- When adding enemies or skills, tag hitboxes with an `owner` and use `visual_only` for telegraphs or non-damaging areas.
- Prefer small focused commits with clear messages (e.g., "Add wizard teleport skill", not "Update code").
- If you change controls or UI, update this README, guide.txt, and the How to Play screen in-game.
- When you introduce new consumables or buffs, wire them through the catalog in `src/systems/items.py` so the HUD and inventory automatically pick them up.
- **Legacy level system** (`src/level/legacy_level.py`) is preserved for compatibility — **DO NOT MODIFY**. Work with PCG files instead.
- PCG configuration is loaded from `config/pcg_config.json` at runtime. Use `use_pcg: true` for procedural generation, `false` for legacy static levels.

### Suggested workflow for pair dev

- Create a branch per feature (e.g., `feature/wizard-teleport-skill`).
- Coordinate room edits: agree on which room index or PCG room code each person is editing to avoid conflicts.
- Test the boss-door locking logic if you change boss spawns (rooms with `G`/`B` are considered boss rooms).
- Keep projectile lifetimes bounded (< 180 frames) to avoid performance spikes.
- Use the debug tools (F5 menu, F8 tile inspector, F9 wall jump debug, F10 area overlay) to verify changes.
- For PCG changes, use `tools/pcg_validate.py` to validate level files before committing.

## Troubleshooting

- If the window doesn’t open, verify that Pygame installed successfully and Python can import it.
- If fonts look off-size, the fallback font is used; adjust sizes in `utils.get_font` if needed.
- On very small displays, reduce `WIDTH`/`HEIGHT` in `config.py`.
