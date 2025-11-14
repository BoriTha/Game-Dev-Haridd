#!/usr/bin/env python3
"""Validate generated PCG JSON for consistency.

Checks:
- door_exits targets exist
- entrance_from targets exist

Usage: python tools/pcg_validate.py
"""
from pathlib import Path
import json
import sys

LEVELS_FILE = Path('data/levels/generated_levels.json')

if not LEVELS_FILE.exists():
    import logging
    logging.getLogger(__name__).error("Levels file not found: %s", LEVELS_FILE)
    sys.exit(1)

data = json.loads(LEVELS_FILE.read_text())
rooms_map = {}

for level in data.get('levels', []):
    for r in level.get('rooms', []):
        rooms_map[r['room_code']] = r

errors = []

for level in data.get('levels', []):
    for r in level.get('rooms', []):
        rc = r.get('room_code')
        door_exits = r.get('door_exits') or {}
        for key, target in door_exits.items():
            # target may be a string like '11A' or a structured dict
            if isinstance(target, dict):
                tcode = target.get('room_code')
            else:
                tcode = target
            if tcode not in rooms_map:
                errors.append(f"{rc}: door_exits[{key}] -> missing target '{tcode}'")
        entr = r.get('entrance_from')
        if entr and entr not in rooms_map:
            errors.append(f"{rc}: entrance_from -> missing source '{entr}'")

if errors:
    import logging
    logger = logging.getLogger(__name__)
    logger.error('Validation FAILED:')
    for e in errors:
        logger.error(' - %s', e)
    sys.exit(2)

print('Validation OK: no missing targets found')
sys.exit(0)
