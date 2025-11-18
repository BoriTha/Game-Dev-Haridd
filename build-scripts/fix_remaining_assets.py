#!/usr/bin/env python3
"""Fix remaining asset loading paths"""
import re

files_to_fix = {
    'src/entities/enemy_entities.py': [774, 800, 816, 2858],
    'src/tiles/tile_renderer.py': [82, 161, 189],
    'src/ui/hud.py': [256],
}

def fix_file(filepath, line_numbers):
    """Fix pygame.image.load calls on specific lines"""
    with open(filepath, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    
    changes = 0
    for line_num in line_numbers:
        idx = line_num - 1  # Convert to 0-based index
        if idx < len(lines):
            original = lines[idx]
            # Replace pygame.image.load(path) with pygame.image.load(resource_path(path))
            # But only if not already wrapped
            if 'resource_path' not in original:
                # Pattern: pygame.image.load(anything)
                fixed = re.sub(
                    r'pygame\.image\.load\(([^)]+)\)',
                    r'pygame.image.load(resource_path(\1))',
                    original
                )
                if fixed != original:
                    lines[idx] = fixed
                    changes += 1
                    print(f"  Line {line_num}: Fixed")
    
    if changes > 0:
        with open(filepath, 'w', encoding='utf-8') as f:
            f.writelines(lines)
        return changes
    return 0

print("Fixing remaining asset paths...")
total = 0
for filepath, line_nums in files_to_fix.items():
    print(f"\n{filepath}:")
    count = fix_file(filepath, line_nums)
    total += count
    if count > 0:
        print(f"  ✅ Fixed {count} lines")
    else:
        print(f"  ⚠️  No changes needed")

print(f"\n✅ Total fixes: {total} lines")
