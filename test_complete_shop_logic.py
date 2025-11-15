#!/usr/bin/env python3
"""
Test script to verify the complete shop triggering logic including fallback.
"""

import sys
import os
import re

# Add project root to path
sys.path.append(os.path.join(os.path.dirname(__file__), '.'))

def test_fallback_logic():
    """Test the fallback room number parsing logic."""
    
    test_cases = [
        ("1A", 0),   # Should trigger shop (room number 1 -> index 0)
        ("2A", 1),   # Should trigger shop (room number 2 -> index 1)  
        ("2B", 1),   # Should trigger shop (room number 2 -> index 1)
        ("3A", 2),   # Should NOT trigger shop (room number 3 -> index 2)
        ("3B", 2),   # Should NOT trigger shop (room number 3 -> index 2)
        ("4A", 3),   # Should trigger shop (room number 4 -> index 3)
        ("4B", 3),   # Should trigger shop (room number 4 -> index 3)
        ("5A", 4),   # Should NOT trigger shop (room number 5 -> index 4)
        ("5B", 4),   # Should NOT trigger shop (room number 5 -> index 4)
        ("6A", 5),   # Should trigger shop (room number 6 -> index 5)
        ("6B", 5),   # Should trigger shop (room number 6 -> index 5)
    ]
    
    shop_room_indices = [0, 1, 3, 5]  # Room number indices that should have shops
    
    print("Testing fallback room number parsing logic:")
    print("=" * 60)
    
    for room_code, expected_index in test_cases:
        # Simulate the fallback logic
        match = re.match(r'(\d+)[A-Za-z]+', room_code)
        if match:
            room_number = int(match.group(1)) - 1  # Convert to 0-based room number index
            should_trigger = room_number in shop_room_indices
            
            status = "✓ SHOP" if should_trigger else "✗ NO SHOP"
            print(f"{room_code:4s} (room number {int(match.group(1))} -> index {room_number}) -> {status}")
            
            # Verify the index matches expected
            if room_number != expected_index:
                print(f"  ERROR: Expected index {expected_index}, got {room_number}")
        else:
            print(f"{room_code:4s} -> FAILED TO PARSE")

def test_complete_logic():
    """Test the complete logic with both room_index and fallback."""
    
    print("\nTesting complete shop triggering logic:")
    print("=" * 60)
    
    # Test cases that would use room_index from RoomData
    room_data_cases = [
        ("1A", 0, True),   # Shop
        ("2A", 1, True),   # Shop  
        ("2B", 1, True),   # Shop (same index as 2A)
        ("3A", 2, False),  # No shop
        ("3B", 2, False),  # No shop (same index as 3A)
        ("4A", 3, True),   # Shop
        ("4B", 3, True),   # Shop (same index as 4A)
    ]
    
    # Test cases that would use fallback logic
    fallback_cases = [
        ("5A", 4, False),  # No shop
        ("5B", 4, False),  # No shop (same index as 5A)
        ("6A", 5, True),   # Shop
        ("6B", 5, True),   # Shop (same index as 6A)
    ]
    
    shop_room_indices = [0, 1, 3, 5]
    
    print("Using room_index from RoomData:")
    for room_code, room_index, expected_shop in room_data_cases:
        should_trigger = room_index in shop_room_indices
        status = "✓" if should_trigger == expected_shop else "✗"
        shop_text = "SHOP" if should_trigger else "NO SHOP"
        print(f"  {room_code:4s} (index {room_index}) -> {shop_text} {status}")
    
    print("\nUsing fallback room number parsing:")
    for room_code, expected_index, expected_shop in fallback_cases:
        match = re.match(r'(\d+)[A-Za-z]+', room_code)
        if match:
            room_number = int(match.group(1)) - 1
            should_trigger = room_number in shop_room_indices
            status = "✓" if should_trigger == expected_shop else "✗"
            shop_text = "SHOP" if should_trigger else "NO SHOP"
            print(f"  {room_code:4s} (room number {int(match.group(1))} -> index {room_number}) -> {shop_text} {status}")

if __name__ == "__main__":
    test_fallback_logic()
    test_complete_logic()
    print("\nTest completed!")