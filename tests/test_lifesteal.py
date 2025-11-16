import os
os.environ.setdefault('SDL_VIDEODRIVER', 'dummy')
import pygame
pygame.init()

from src.entities.player_entity import Player
from src.entities.enemy_entities import Bug
from src.entities.entity_common import Hitbox


def test_percent_lifesteal_melee():
    p = Player(0, 0, cls='Knight')
    p.combat.hp = 2
    p.combat.max_hp = 10
    p.combat.lifesteal_pct = 0.05  # 5%

    e = Bug(200, 200)
    e.combat.hp = 100

    hb = Hitbox(pygame.Rect(0, 0, 8, 8), 1, 20, p, dir_vec=(1, 0))
    e.hit(hb, p)

    expected = min(p.combat.max_hp, 2 + int(20 * 0.05))
    assert p.combat.hp == expected


def test_spell_lifesteal_tagged_hit():
    p = Player(0, 0, cls='Wizard')
    p.combat.hp = 3
    p.combat.max_hp = 10
    p.combat.spell_lifesteal_pct = 0.2

    e = Bug(200, 200)
    e.combat.hp = 100

    hb = Hitbox(pygame.Rect(0, 0, 8, 8), 1, 10, p, dir_vec=(1, 0), tag='spell')
    e.hit(hb, p)

    expected = min(p.combat.max_hp, 3 + int(10 * 0.2))
    assert p.combat.hp == expected


def test_fractional_lifesteal_accumulates():
    p = Player(0, 0, cls='Knight')
    p.combat.hp = 1
    p.combat.max_hp = 10
    p.combat.lifesteal_pct = 0.03  # 3%

    e = Bug(200, 200)
    e.combat.hp = 100

    hb = Hitbox(pygame.Rect(0, 0, 8, 8), 1, 10, p, dir_vec=(1, 0), bypass_ifr=True)
    # Each hit yields 0.3 heal float; 4 hits -> 1.2 heal => 1 HP heal
    for _ in range(4):
        e.hit(hb, p)

    expected = min(p.combat.max_hp, 1 + 1)  # one integer heal should have been applied
    assert p.combat.hp == expected
