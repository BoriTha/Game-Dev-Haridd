#!/usr/bin/env python3
"""
Fix asset paths for PyInstaller by adding resource_path() wrapper
"""
import re
import os

def add_import_if_missing(content, filepath):
    """Add resource_path import if not present"""
    if 'from src.core.utils import resource_path' in content:
        return content
    if 'from src.core.utils import' in content:
        # Add to existing import
        content = re.sub(
            r'from src\.core\.utils import ([^\n]+)',
            r'from src.core.utils import \1, resource_path',
            content
        )
    elif 'import pygame' in content and 'main.py' not in filepath:
        # Add new import after pygame
        content = re.sub(
            r'(import pygame\n)',
            r'\1from src.core.utils import resource_path\n',
            content,
            count=1
        )
    return content

def fix_pygame_image_load(content):
    """Wrap pygame.image.load() paths with resource_path()"""
    # Match pygame.image.load("path") or pygame.image.load('path')
    pattern = r'pygame\.image\.load\((["' "'" r'])((?:assets|config)/[^"' "'" r']+)(["' "'" r'])\)'
    replacement = r'pygame.image.load(resource_path(\1\2\3))'
    return re.sub(pattern, replacement, content)

def process_file(filepath):
    """Process a single Python file"""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
        
        original = content
        
        # Check if file loads images
        if 'pygame.image.load' in content:
            # Add import
            content = add_import_if_missing(content, filepath)
            # Fix paths
            content = fix_pygame_image_load(content)
            
            if content != original:
                with open(filepath, 'w', encoding='utf-8') as f:
                    f.write(content)
                print(f"✅ Fixed: {filepath}")
                return True
    except Exception as e:
        print(f"❌ Error processing {filepath}: {e}")
    return False

def main():
    """Find and fix all Python files"""
    fixed_count = 0
    
    # Files to check
    patterns = [
        'src/**/*.py',
        'main.py',
    ]
    
    import glob
    files = []
    for pattern in patterns:
        files.extend(glob.glob(pattern, recursive=True))
    
    for filepath in files:
        if process_file(filepath):
            fixed_count += 1
    
    print(f"\n✅ Fixed {fixed_count} files")
    print("\nNow rebuild with: pyinstaller --clean DarkSoul_RPG.spec")

if __name__ == '__main__':
    main()
