import pygame
import random
from config import WIDTH, HEIGHT, WHITE, GREEN, CYAN, FPS
from ..core.utils import draw_text, get_font
from .items import build_consumable_catalog, build_armament_catalog, load_icon, icon_has_transparency, load_icon_masked, rarity_border_color
from typing import Optional, List, Dict, Tuple
from ..entities.entities import floating, DamageNumber


def _safe_load_icon(path: str, size: tuple = (24,24)) -> Optional[pygame.Surface]:
    """Return loaded surface only if the image contains transparent pixels."""
    if not path:
        return None
    try:
        surf = load_icon(path, size)
    except Exception:
        return None
    if not surf:
        return None
    try:
        if icon_has_transparency(path, size):
            return surf
    except Exception:
        return None
    return None

import random as _rnd

# Enhanced rarity weights for better distribution
RARITY_WEIGHTS = {
    'Normal': 50,
    'Rare': 30,
    'Epic': 15,
    'Legendary': 5,
}

# Consumable rarity weights for stock determination
CONSUMABLE_RARITY_WEIGHTS = {
    'Normal': 60,
    'Rare': 25,
    'Epic': 10,
    'Legendary': 5,
}


class Shop:
    def __init__(self, game):
        self.game = game
        self.shop_open = False
        self.selection = 0
        self.selection_category = 'gear'  # 'gear' or 'consumable'
        self.shop_consumables = build_consumable_catalog()
        self.shop_equipment = build_armament_catalog()
        
        # Track stock amounts for consumables
        self.consumable_stock = {}  # {item_key: available_stock}
        
        # Track which equipment has been purchased this shop visit
        self.purchased_equipment = set()  # {item_key}
        
        # New shop inventory with 5 gear slots and 3 consumable slots
        self.selected_gear = []  # 5 items
        self.selected_consumables = []  # 3 items
        
        # Scrolling support
        self.gear_scroll_offset = 0
        self.consumable_scroll_offset = 0
        self.max_visible_gear = 5  # Maximum gear items visible at once
        self.max_visible_consumables = 3  # Maximum consumable items visible at once
        
        # UI regions for interaction
        self.regions = []
        self.hover_item = None
        self.hover_button = None
        
        # Create initial inventory
        self.refresh_inventory()
    
    def _get_max_visible(self):
        """Get max visible items for current category"""
        if self.selection_category == 'gear':
            return self.max_visible_gear
        else:
            return self.max_visible_consumables
        
    def refresh_inventory(self):
        """Create random selection of 5 gear items and 3 consumables with rarity-based spawn rates"""
        # Clear previous stock and purchased equipment tracking
        self.consumable_stock = {}
        self.purchased_equipment = set()
        
        # Generate 5 gear items with enhanced rarity system
        self.selected_gear = self._generate_gear_selection(5)
        
        # Generate 3 consumables with improved stock system
        self.selected_consumables = self._generate_consumable_selection(3)
        
        # Combine for easier iteration
        self.shop_items = self.selected_gear + self.selected_consumables
        
    def _generate_gear_selection(self, count: int) -> List:
        """Generate gear selection with enhanced rarity distribution"""
        pool = list(self.shop_equipment.values())
        weights = [RARITY_WEIGHTS.get(getattr(item, 'rarity', 'Normal'), 1) for item in pool]
        selected = []
        
        for _ in range(min(count, len(pool))):
            if not pool:
                break
                
            total = sum(weights)
            if total <= 0:
                break
                
            r = _rnd.random() * total
            cum = 0.0
            idx = 0
            
            for i, w in enumerate(weights):
                cum += w
                if r <= cum:
                    idx = i
                    break
                    
            selected.append(pool.pop(idx))
            weights.pop(idx)
            
        return selected
    
    def _generate_consumable_selection(self, count: int) -> List:
        """Generate consumable selection with rarity-based spawning"""
        pool = list(self.shop_consumables.values())
        weights = [CONSUMABLE_RARITY_WEIGHTS.get(getattr(item, 'rarity', 'Normal'), 1) for item in pool]
        selected = []
        
        for _ in range(min(count, len(pool))):
            if not pool:
                break
                
            total = sum(weights)
            if total <= 0:
                break
                
            r = _rnd.random() * total
            cum = 0.0
            idx = 0
            
            for i, w in enumerate(weights):
                cum += w
                if r <= cum:
                    idx = i
                    break
                    
            selected.append(pool.pop(idx))
            weights.pop(idx)
            
            # Generate stock based on rarity for selected consumable
            item = selected[-1]
            rarity = getattr(item, 'rarity', 'Normal') if hasattr(item, 'rarity') else 'Normal'
            stock = self._generate_consumable_stock(rarity)
            self.consumable_stock[item.key] = stock
            
        return selected
    
    def _generate_consumable_stock(self, rarity: str) -> int:
        """Generate stock amount based on consumable rarity"""
        if rarity == 'Normal':
            return random.randint(3, 5)  # Common items have more stock
        elif rarity == 'Rare':
            return random.randint(2, 4)
        elif rarity == 'Epic':
            return random.randint(1, 3)
        elif rarity == 'Legendary':
            return random.randint(1, 2)  # Legendary items are rare
        else:
            return random.randint(1, 3)  # Default
    

    
    def open_shop(self):
        """Open shop interface"""
        self.shop_open = True
        self.selection = 0
        self.selection_category = 'gear'
        self.refresh_inventory()
        
    def close_shop(self):
        """Close shop interface"""
        self.shop_open = False
        self.selection = 0
        self.selection_category = 'gear'
        self.regions = []
        self.hover_item = None
    
    def can_afford(self, item):
        """Check if player can afford an item"""
        price = self._get_item_price(item)
        return self.game.player.money >= price
    
    def purchase_item(self, item):
        """Attempt to purchase an item"""
        price = self._get_item_price(item)
        
        if self.game.player.money < price:
            floating.append(DamageNumber(
                self.game.player.rect.centerx,
                self.game.player.rect.top - 12,
                "Not enough coins!",
                (255, 100, 100)
            ))
            return False
        
        # Check if consumable has stock available
        if hasattr(item, 'use'):  # Consumable
            if item.key in self.consumable_stock:
                if self.consumable_stock[item.key] <= 0:
                    floating.append(DamageNumber(
                        self.game.player.rect.centerx,
                        self.game.player.rect.top - 12,
                        "Out of stock!",
                        (255, 100, 100)
                    ))
                    return False
        # Check if equipment has already been purchased this shop visit or already owned
        elif hasattr(item, 'modifiers'):  # Equipment
            player_owns_item = False
            if hasattr(self.game, 'inventory'):
                player_owns_item = item.key in self.game.inventory.armament_order
                
            if item.key in self.purchased_equipment:
                floating.append(DamageNumber(
                    self.game.player.rect.centerx,
                    self.game.player.rect.top - 12,
                    "Already purchased this visit!",
                    (255, 200, 100)
                ))
                return False
            elif player_owns_item:
                floating.append(DamageNumber(
                    self.game.player.rect.centerx,
                    self.game.player.rect.top - 12,
                    "Already owned!",
                    (255, 200, 100)
                ))
                return False
        
        # Deduct money
        self.game.player.money -= price
        
        # Handle different item types
        if hasattr(item, 'use'):  # Consumable
            # Add to inventory
            if hasattr(self.game, 'inventory'):
                added = self.game.inventory.add_consumable(item.key, 1)
                if added > 0:
                    # Decrease stock
                    if item.key in self.consumable_stock:
                        self.consumable_stock[item.key] -= 1
                    
                    floating.append(DamageNumber(
                        self.game.player.rect.centerx,
                        self.game.player.rect.top - 12,
                        f"Purchased {item.name}",
                        GREEN
                    ))
                else:
                    # Refund if couldn't add to inventory
                    self.game.player.money += price
                    floating.append(DamageNumber(
                        self.game.player.rect.centerx,
                        self.game.player.rect.top - 12,
                        "Inventory full!",
                        (255, 100, 100)
                    ))
                    return False
            else:
                # Fallback: use immediately if no inventory system
                success = item.use(self.game)
                if success:
                    # Decrease stock
                    if item.key in self.consumable_stock:
                        self.consumable_stock[item.key] -= 1
                    
                    floating.append(DamageNumber(
                        self.game.player.rect.centerx,
                        self.game.player.rect.top - 12,
                        f"Purchased {item.name}",
                        GREEN
                    ))
                else:
                    # Refund if item couldn't be used
                    self.game.player.money += price
                    return False
        else:  # Equipment
            self._add_shop_item_to_inventory(item)
            # Mark this equipment as purchased for this shop visit
            self.purchased_equipment.add(item.key)
            floating.append(DamageNumber(
                self.game.player.rect.centerx,
                self.game.player.rect.top - 12,
                f"Purchased {item.name}",
                GREEN
            ))
        
        return True
    
    def _add_shop_item_to_inventory(self, equipment):
        """Add purchased equipment to inventory storage"""
        if hasattr(self.game, 'inventory'):
            # Add to armament order if not already there
            if equipment.key not in self.game.inventory.armament_order:
                self.game.inventory.armament_order.append(equipment.key)
        else:
            # Fallback: apply modifiers directly to player
            player = self.game.player
            for stat, value in equipment.modifiers.items():
                if hasattr(player, stat):
                    setattr(player, stat, getattr(player, stat) + value)
    
    def handle_input(self):
        """Handle shop input - this method is deprecated, use handle_event instead"""
        pass
    
    def handle_event(self, event):
        """Handle shop events properly using event-based input"""
        if event.type == pygame.MOUSEWHEEL:
            if event.y > 0:
                self._scroll_up()
            elif event.y < 0:
                self._scroll_down()
        elif event.type == pygame.KEYDOWN:
            # Navigation - LEFT/RIGHT switch between categories (spatial navigation)
            if event.key in [pygame.K_LEFT, pygame.K_a]:
                if self.selection_category == 'consumable':
                    # Consumables are on the right, LEFT goes to gear (left neighbor)
                    self.selection_category = 'gear'
                    # Keep same index if possible, otherwise clamp to valid range
                    self.selection = min(self.selection, len(self.selected_gear) - 1) if self.selected_gear else 0
                    self.gear_scroll_offset = max(0, self.selection - self.max_visible_gear + 1)
                # If already in gear, stay in gear (no wrap-around)
            elif event.key in [pygame.K_RIGHT, pygame.K_d]:
                if self.selection_category == 'gear':
                    # Gear is on the left, RIGHT goes to consumables (right neighbor)
                    self.selection_category = 'consumable'
                    # Keep same index if possible, otherwise clamp to valid range
                    self.selection = min(self.selection, len(self.selected_consumables) - 1) if self.selected_consumables else 0
                    self.consumable_scroll_offset = max(0, self.selection - self.max_visible_consumables + 1)
                # If already in consumables, stay in consumables (no wrap-around)
            elif event.key in [pygame.K_UP, pygame.K_w]:
                # Move up in current category
                if self.selection > 0:
                    self.selection -= 1
                    # Adjust scroll offset if selection moves off-screen
                    if self.selection_category == 'gear':
                        if self.selection < self.gear_scroll_offset:
                            self.gear_scroll_offset = max(0, self.selection)
                    else:  # consumable
                        if self.selection < self.consumable_scroll_offset:
                            self.consumable_scroll_offset = max(0, self.selection)
            elif event.key in [pygame.K_DOWN, pygame.K_s]:
                # Move down in current category
                max_items = len(self.selected_gear) if self.selection_category == 'gear' else len(self.selected_consumables)
                if self.selection < max_items - 1:
                    self.selection += 1
                    # Adjust scroll offset if selection moves off-screen
                    if self.selection_category == 'gear':
                        last_visible_index = self.gear_scroll_offset + self.max_visible_gear - 1
                        if self.selection > last_visible_index:
                            self.gear_scroll_offset = self.selection - (self.max_visible_gear - 1)
                            # Ensure scroll offset doesn't exceed maximum
                            max_scroll = max(0, len(self.selected_gear) - self.max_visible_gear)
                            self.gear_scroll_offset = min(self.gear_scroll_offset, max_scroll)
                    else:  # consumable
                        last_visible_index = self.consumable_scroll_offset + self.max_visible_consumables - 1
                        if self.selection > last_visible_index:
                            self.consumable_scroll_offset = self.selection - (self.max_visible_consumables - 1)
                            # Ensure scroll offset doesn't exceed maximum
                            max_scroll = max(0, len(self.selected_consumables) - self.max_visible_consumables)
                            self.consumable_scroll_offset = min(self.consumable_scroll_offset, max_scroll)
            
            # Purchase/Select action
            elif event.key in [pygame.K_RETURN, pygame.K_SPACE]:
                self._handle_selection()
            
            # Scrolling
            elif event.key == pygame.K_PAGEUP:
                self._scroll_up()
            elif event.key == pygame.K_PAGEDOWN:
                self._scroll_down()
            elif event.key == pygame.K_HOME:
                self._scroll_to_top()
            elif event.key == pygame.K_END:
                self._scroll_to_bottom()
            
            # Close shop
            elif event.key in [pygame.K_ESCAPE, pygame.K_i]:
                self.close_shop()
    
    def _handle_selection(self):
        """Handle current selection"""
        if self.selection_category == 'gear':
            if 0 <= self.selection < len(self.selected_gear):
                item = self.selected_gear[self.selection]
                self.purchase_item(item)
        elif self.selection_category == 'consumable':
            if 0 <= self.selection < len(self.selected_consumables):
                item = self.selected_consumables[self.selection]
                self.purchase_item(item)
    
    def _get_item_at_pos(self, pos):
        """Get shop item at mouse position"""
        for info in self.regions:
            if info['rect'].collidepoint(pos):
                return info.get('item')
        return None
    
    def _get_player_stats_with_preview(self, preview_item=None) -> Dict[str, Tuple[str, str]]:
        """Get player stats with optional preview of item effects"""
        player = self.game.player
        stats = {}
        
        # Base stats
        base_hp = getattr(player, 'max_hp', 0)
        base_attack = getattr(player, 'attack_damage', 0)
        base_mana = getattr(player, 'max_mana', 0)
        base_stamina = getattr(player, 'max_stamina', 0)
        base_speed = getattr(player, 'player_speed', 0)
        
        # Current stats (with equipment)
        current_hp = base_hp
        current_attack = base_attack
        current_mana = base_mana
        current_stamina = base_stamina
        current_speed = base_speed
        
        # Add current equipment effects
        if hasattr(self.game, 'inventory'):
            for key in self.game.inventory.gear_slots:
                if key and key in self.game.inventory.armament_catalog:
                    item = self.game.inventory.armament_catalog[key]
                    for stat, value in item.modifiers.items():
                        if stat == 'max_hp':
                            current_hp += value
                        elif stat == 'attack_damage':
                            current_attack += value
                        elif stat == 'max_mana':
                            current_mana += value
                        elif stat == 'max_stamina':
                            current_stamina += value
                        elif stat == 'player_speed':
                            current_speed += value
        
        # Preview item effects
        preview_hp = current_hp
        preview_attack = current_attack
        preview_mana = current_mana
        preview_stamina = current_stamina
        preview_speed = current_speed
        
        if preview_item and hasattr(preview_item, 'modifiers'):
            for stat, value in preview_item.modifiers.items():
                if stat == 'max_hp':
                    preview_hp += value
                elif stat == 'attack_damage':
                    preview_attack += value
                elif stat == 'max_mana':
                    preview_mana += value
                elif stat == 'max_stamina':
                    preview_stamina += value
                elif stat == 'player_speed':
                    preview_speed += value
        
        # Format stats
        stats['hp'] = (f"{player.hp}/{current_hp}", f"→ {player.hp}/{preview_hp}" if preview_hp != current_hp else "")
        stats['attack'] = (str(current_attack), f"→ {preview_attack}" if preview_attack != current_attack else "")
        stats['mana'] = (f"{player.mana:.1f}/{current_mana:.1f}", f"→ {player.mana:.1f}/{preview_mana:.1f}" if preview_mana != current_mana else "")
        stats['stamina'] = (f"{player.stamina:.1f}/{current_stamina:.1f}", f"→ {player.stamina:.1f}/{preview_stamina:.1f}" if preview_stamina != current_stamina else "")
        stats['speed'] = (f"{current_speed:.1f}", f"→ {preview_speed:.1f}" if preview_speed != current_speed else "")
        
        return stats
    
    def _draw_shop_tooltip(self, screen, item, mouse_pos):
        """Draw enhanced tooltip for shop item with stat comparisons"""
        if not item:
            return
        
        lines = item.tooltip_lines()
        if not lines:
            return
        
        # Add stock and ownership information for consumables
        if hasattr(item, 'use'):  # Consumable
            player_owned = 0
            if hasattr(self.game, 'inventory'):
                player_owned = self.game.inventory._total_available_count(item.key)
            
            available_stock = self.consumable_stock.get(item.key, 0)
            lines.append(f"You own: {player_owned}")
            lines.append(f"Available: {available_stock}")
        # Add purchase status information for equipment
        elif hasattr(item, 'modifiers'):  # Equipment
            player_owns_item = False
            if hasattr(self.game, 'inventory'):
                player_owns_item = item.key in self.game.inventory.armament_order
                
            if item.key in self.purchased_equipment:
                lines.append("Already purchased this visit")
            elif player_owns_item:
                lines.append("Already owned")
            else:
                # Add stat preview for equipment
                stats = self._get_player_stats_with_preview(item)
                if stats['attack'][1]:  # If attack would change
                    lines.append(f"Attack: {stats['attack'][0]} {stats['attack'][1]}")
                if stats['hp'][1]:  # If HP would change
                    lines.append(f"HP: {stats['hp'][0]} {stats['hp'][1]}")
                if stats['speed'][1]:  # If speed would change
                    lines.append(f"Speed: {stats['speed'][0]} {stats['speed'][1]}")
        
        font = get_font(16)
        icon_space = 34
        width = max(font.size(line)[0] for line in lines) + 20 + icon_space
        height = len(lines) * 22 + 12
        
        tooltip_rect = pygame.Rect(mouse_pos[0] + 18, mouse_pos[1] + 18, width, height)
        
        # Adjust position if tooltip goes off screen
        if tooltip_rect.right > WIDTH - 8:
            tooltip_rect.x = WIDTH - width - 8
        if tooltip_rect.bottom > HEIGHT - 8:
            tooltip_rect.y = HEIGHT - height - 8
        
        # Draw tooltip background
        pygame.draw.rect(screen, (28, 28, 38), tooltip_rect, border_radius=8)
        pygame.draw.rect(screen, (180, 170, 200), tooltip_rect, width=1, border_radius=8)
        
        # Draw icon
        icon_rect = pygame.Rect(tooltip_rect.x + 10, tooltip_rect.y + 10, 24, 24)
        icon_surf = None
        if hasattr(item, 'icon_path') and item.icon_path:
            surf = _safe_load_icon(item.icon_path, (24,24))
            if surf:
                icon_surf = surf
            else:
                try:
                    icon_surf = load_icon_masked(item.icon_path, (24,24), radius=6)
                except Exception:
                    icon_surf = None
        if icon_surf:
            screen.blit(icon_surf, icon_rect)
        else:
            pygame.draw.rect(screen, item.color, icon_rect, border_radius=6)
            if hasattr(item, 'icon_letter'):
                icon_font = get_font(14, bold=True)
                icon_surf2 = icon_font.render(item.icon_letter, True, (10, 10, 20))
                screen.blit(icon_surf2, icon_surf2.get_rect(center=icon_rect.center))
        
        # Draw text
        text_x = tooltip_rect.x + 10 + icon_space
        for i, line in enumerate(lines):
            color = (230, 230, 245)
            if "→" in line:  # Preview lines
                color = (100, 255, 100)  # Green for stat increases
            screen.blit(font.render(line, True, color),
                     (text_x, tooltip_rect.y + 6 + i * 22))
    
    def draw(self, screen):
        """Draw new 2x3 grid shop interface"""
        if not self.shop_open:
            return
        
        # Darken background
        overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 180))
        screen.blit(overlay, (0, 0))
        
        # Calculate panel dimensions
        margin = 40
        panel_width = WIDTH - (margin * 2)
        panel_height = HEIGHT - (margin * 2)
        panel_x = margin
        panel_y = margin
        
        panel_rect = pygame.Rect(panel_x, panel_y, panel_width, panel_height)
        pygame.draw.rect(screen, (30, 28, 40), panel_rect, border_radius=12)
        pygame.draw.rect(screen, (210, 200, 170), panel_rect, width=2, border_radius=12)
        
        # Clear regions for mouse interaction
        self.regions = []
        
        # Title
        title_font = get_font(28, bold=True)
        title_text = title_font.render("MYSTIC SHOP", True, (240, 220, 190))
        title_rect = title_text.get_rect(center=(panel_x + panel_width // 2, panel_y + 30))
        screen.blit(title_text, title_rect)
        
        # Calculate 2x3 grid layout - make cells larger
        grid_width = panel_width - 40  # Reduced margins for more space
        grid_height = panel_height - 120  # Reduced margins for more space
        cell_width = grid_width // 3  # 3 columns
        cell_height = grid_height // 2  # 2 rows
        
        # Grid positions
        grid_x = panel_x + 20  # Reduced margin
        grid_y = panel_y + 60  # Reduced margin
        
        # Cell 1: Shop Gear (top-left)
        shop_gear_rect = pygame.Rect(grid_x, grid_y, cell_width - 6, cell_height - 6)  # Less spacing
        self._draw_shop_gear_cell(screen, shop_gear_rect)
        
        # Cell 2: Shop Consumables (top-middle)
        shop_cons_rect = pygame.Rect(grid_x + cell_width, grid_y, cell_width - 6, cell_height - 6)  # Less spacing
        self._draw_shop_consumables_cell(screen, shop_cons_rect)
        
        # Cell 3: Player Status (top-right)
        player_status_rect = pygame.Rect(grid_x + cell_width * 2, grid_y, cell_width - 6, cell_height - 6)  # Less spacing
        self._draw_player_status_cell(screen, player_status_rect)
        
        # Cell 4: Player Gear Slots (bottom-left)
        player_gear_slots_rect = pygame.Rect(grid_x, grid_y + cell_height, cell_width - 6, cell_height - 6)  # Less spacing
        self._draw_player_gear_slots_cell(screen, player_gear_slots_rect)
        
        # Cell 5: Player Consumable Slots (bottom-middle)
        player_cons_slots_rect = pygame.Rect(grid_x + cell_width, grid_y + cell_height, cell_width - 6, cell_height - 6)  # Less spacing
        self._draw_player_consumable_slots_cell(screen, player_cons_slots_rect)
        
        # Cell 6: Dynamic Inventory Panel (bottom-right) - changes based on selection
        dynamic_rect = pygame.Rect(grid_x + cell_width * 2, grid_y + cell_height, cell_width - 6, cell_height - 6)  # Less spacing
        self._draw_dynamic_inventory_panel(screen, dynamic_rect)
        
        # Exit button at bottom center
        exit_button_width = 120
        exit_button_height = 40
        exit_button_x = panel_x + (panel_width - exit_button_width) // 2
        exit_button_y = panel_y + panel_height - 60
        exit_button_rect = pygame.Rect(exit_button_x, exit_button_y, exit_button_width, exit_button_height)
        
        mouse_pos = pygame.mouse.get_pos()
        is_exit_hovering = exit_button_rect.collidepoint(mouse_pos)
        
        exit_button_color = (200, 50, 50) if is_exit_hovering else (150, 150, 150)
        pygame.draw.rect(screen, exit_button_color, exit_button_rect, border_radius=6)
        pygame.draw.rect(screen, (200, 150, 150), exit_button_rect, width=2, border_radius=6)
        
        exit_text = get_font(16, bold=True).render("EXIT", True, (255, 255, 255))
        exit_text_rect = exit_text.get_rect(center=exit_button_rect.center)
        screen.blit(exit_text, exit_text_rect)
        
        # Register exit button region
        self.regions.append({'rect': exit_button_rect, 'action': 'exit'})
        
        # Instructions
        inst_font = get_font(12)
        instructions = [
            "WASD/Arrows: Navigate",
            "Space/Enter: Buy",
            "PageUp/Down: Scroll",
            "Mouse Wheel: Scroll",
            "ESC: Exit Shop"
        ]
        
        for i, instruction in enumerate(instructions):
            inst_text = inst_font.render(instruction, True, (180, 180, 200))
            screen.blit(inst_text, (panel_x + 20, panel_y + panel_height - 40 + i * 12))
        
        # Handle mouse hover for tooltips
        hover_item = self._get_item_at_pos(mouse_pos)
        if hover_item:
            self._draw_shop_tooltip(screen, hover_item, mouse_pos)
    
    def _draw_shop_gear_cell(self, screen, rect):
        """Draw shop gear items cell with a list view"""
        # Cell background
        pygame.draw.rect(screen, (25, 25, 35), rect, border_radius=10)
        pygame.draw.rect(screen, (100, 100, 120), rect, width=1, border_radius=10)
        
        # Title
        title_font = get_font(16, bold=True)
        title_text = title_font.render(f"Shop Gear ({len(self.selected_gear)})", True, (235, 210, 190))
        screen.blit(title_text, (rect.x + 10, rect.y + 10))
        
        # Draw list view with details and buy buttons
        list_height = rect.height - 40  # Reduced margin for more space
        list_rect = pygame.Rect(rect.x + 6, rect.y + 35, rect.width - 12, list_height)  # Better margins
        self._draw_gear_list(screen, list_rect, self.selected_gear)
    
    def _draw_shop_consumables_cell(self, screen, rect):
        """Draw shop consumables cell with a list view"""
        # Cell background
        pygame.draw.rect(screen, (25, 25, 35), rect, border_radius=10)
        pygame.draw.rect(screen, (100, 100, 120), rect, width=1, border_radius=10)
        
        # Title
        title_font = get_font(16, bold=True)
        title_text = title_font.render(f"Shop Consumables ({len(self.selected_consumables)})", True, (235, 210, 190))
        screen.blit(title_text, (rect.x + 10, rect.y + 10))
        
        # Draw list view with details and buy buttons
        list_height = rect.height - 40  # Reduced margin for more space
        list_rect = pygame.Rect(rect.x + 6, rect.y + 35, rect.width - 12, list_height)  # Better margins
        self._draw_consumable_list(screen, list_rect, self.selected_consumables)
    
    def _draw_player_status_cell(self, screen, rect):
        """Draw player status cell"""
        # Cell background
        pygame.draw.rect(screen, (25, 25, 35), rect, border_radius=10)
        pygame.draw.rect(screen, (100, 100, 120), rect, width=1, border_radius=10)
        
        # Title
        title_font = get_font(16, bold=True)
        title_text = title_font.render("Player Status", True, (235, 210, 190))
        screen.blit(title_text, (rect.x + 10, rect.y + 10))
        
        # Get current hover item for preview
        mouse_pos = pygame.mouse.get_pos()
        hover_item = self._get_item_at_pos(mouse_pos)
        
        # Get stats with preview
        stats = self._get_player_stats_with_preview(hover_item)
        
        # Draw stats
        stats_font = get_font(14)
        stats_y = rect.y + 40
        line_height = 20
        
        # Player class
        class_text = stats_font.render(f"Class: {self.game.player.cls}", True, (200, 200, 215))
        screen.blit(class_text, (rect.x + 10, stats_y))
        stats_y += line_height + 5
        
        # HP
        hp_text = stats_font.render(f"HP: {stats['hp'][0]}", True, (255, 150, 150))
        screen.blit(hp_text, (rect.x + 10, stats_y))
        if stats['hp'][1]:
            preview_text = stats_font.render(stats['hp'][1], True, (100, 255, 100))
            screen.blit(preview_text, (rect.x + 120, stats_y))
        stats_y += line_height
        
        # Attack
        attack_text = stats_font.render(f"Attack: {stats['attack'][0]}", True, (255, 200, 100))
        screen.blit(attack_text, (rect.x + 10, stats_y))
        if stats['attack'][1]:
            preview_text = stats_font.render(stats['attack'][1], True, (100, 255, 100))
            screen.blit(preview_text, (rect.x + 120, stats_y))
        stats_y += line_height
        
        # Mana
        mana_text = stats_font.render(f"Mana: {stats['mana'][0]}", True, (100, 150, 255))
        screen.blit(mana_text, (rect.x + 10, stats_y))
        if stats['mana'][1]:
            preview_text = stats_font.render(stats['mana'][1], True, (100, 255, 100))
            screen.blit(preview_text, (rect.x + 120, stats_y))
        stats_y += line_height
        
        # Stamina
        stamina_text = stats_font.render(f"Stamina: {stats['stamina'][0]}", True, (150, 255, 150))
        screen.blit(stamina_text, (rect.x + 10, stats_y))
        if stats['stamina'][1]:
            preview_text = stats_font.render(stats['stamina'][1], True, (100, 255, 100))
            screen.blit(preview_text, (rect.x + 120, stats_y))
        stats_y += line_height
        
        # Speed
        speed_text = stats_font.render(f"Speed: {stats['speed'][0]}", True, (200, 200, 255))
        screen.blit(speed_text, (rect.x + 10, stats_y))
        if stats['speed'][1]:
            preview_text = stats_font.render(stats['speed'][1], True, (100, 255, 100))
            screen.blit(preview_text, (rect.x + 120, stats_y))
        stats_y += line_height
        
        # Money
        money_text = stats_font.render(f"Coins: {self.game.player.money}", True, (255, 215, 0))
        screen.blit(money_text, (rect.x + 10, stats_y))
    
    def _draw_player_gear_slots_cell(self, screen, rect):
        """Draw player gear slots cell"""
        # Cell background
        pygame.draw.rect(screen, (25, 25, 35), rect, border_radius=10)
        pygame.draw.rect(screen, (100, 100, 120), rect, width=1, border_radius=10)
        
        # Title
        title_font = get_font(16, bold=True)
        title_text = title_font.render("Your Gear (3 slots)", True, (235, 210, 190))
        screen.blit(title_text, (rect.x + 10, rect.y + 10))
        
        if not hasattr(self.game, 'inventory'):
            # No inventory system
            no_inv_text = get_font(12).render("No inventory system", True, (180, 180, 200))
            screen.blit(no_inv_text, (rect.x + 10, rect.y + 50))
            return
        
        inventory = self.game.inventory
        
        # Draw 3 gear slots horizontally
        item_size = 60
        item_spacing = 15
        start_x = rect.x + 10
        start_y = rect.y + 40
        
        for i in range(3):  # 3 gear slots for player
            item_x = start_x + i * (item_size + item_spacing)
            item_y = start_y
            
            item_rect = pygame.Rect(item_x, item_y, item_size, item_size)
            
            # Draw slot background
            pygame.draw.rect(screen, (40, 40, 50), item_rect, border_radius=8)
            pygame.draw.rect(screen, (80, 80, 100), item_rect, width=1, border_radius=8)
            
            # Draw equipped item if any
            if i < len(inventory.gear_slots) and inventory.gear_slots[i]:
                item_key = inventory.gear_slots[i]
                item = inventory.armament_catalog.get(item_key)
                if item:
                    self._draw_equipped_item(screen, item, item_rect)
            
            # Slot number
            slot_text = get_font(12).render(str(i + 1), True, (120, 120, 140))
            screen.blit(slot_text, (item_rect.x + 3, item_rect.y + 3))
    
    def _draw_player_consumable_slots_cell(self, screen, rect):
        """Draw player consumable slots cell"""
        # Cell background
        pygame.draw.rect(screen, (25, 25, 35), rect, border_radius=10)
        pygame.draw.rect(screen, (100, 100, 120), rect, width=1, border_radius=10)
        
        # Title
        title_font = get_font(16, bold=True)
        title_text = title_font.render("Your Consumables", True, (235, 210, 190))
        screen.blit(title_text, (rect.x + 10, rect.y + 10))
        
        if not hasattr(self.game, 'inventory'):
            # No inventory system
            no_inv_text = get_font(12).render("No inventory system", True, (180, 180, 200))
            screen.blit(no_inv_text, (rect.x + 10, rect.y + 50))
            return
        
        inventory = self.game.inventory
        
        # Draw consumable slots horizontally
        item_size = 60
        item_spacing = 15
        start_x = rect.x + 10
        start_y = rect.y + 40
        
        for i, stack in enumerate(inventory.consumable_slots):
            if i >= 3:  # Only show first 3 slots
                break
                
            item_x = start_x + i * (item_size + item_spacing)
            item_y = start_y
            
            item_rect = pygame.Rect(item_x, item_y, item_size, item_size)
            
            # Draw slot background
            pygame.draw.rect(screen, (40, 40, 50), item_rect, border_radius=8)
            pygame.draw.rect(screen, (80, 80, 100), item_rect, width=1, border_radius=8)
            
            # Draw equipped consumable if any
            if stack:
                item = inventory.consumable_catalog.get(stack.key)
                if item:
                    self._draw_equipped_item(screen, item, item_rect)
                    
                    # Draw count
                    count_text = get_font(12, bold=True).render(str(stack.count), True, (255, 255, 255))
                    count_rect = count_text.get_rect(bottomright=(item_rect.right - 4, item_rect.bottom - 4))
                    screen.blit(count_text, count_rect)
            
            # Hotkey label
            hotkey = inventory._hotkey_label(i)
            hotkey_text = get_font(10).render(hotkey, True, (120, 120, 140))
            screen.blit(hotkey_text, (item_rect.x + 3, item_rect.y + 3))
    
    def _draw_dynamic_inventory_panel(self, screen, rect):
        """Draw dynamic inventory panel that changes based on selection"""
        # Cell background
        pygame.draw.rect(screen, (25, 25, 35), rect, border_radius=10)
        pygame.draw.rect(screen, (100, 100, 120), rect, width=1, border_radius=10)
        
        # Title
        title_font = get_font(16, bold=True)
        
        # Get current selection to determine what to show
        mouse_pos = pygame.mouse.get_pos()
        hover_item = self._get_item_at_pos(mouse_pos)
        
        if hover_item:
            if hasattr(hover_item, 'modifiers'):  # Gear item
                title_text = title_font.render("Gear Details", True, (235, 210, 190))
                screen.blit(title_text, (rect.x + 10, rect.y + 10))
                self._draw_gear_details(screen, hover_item, rect)
            elif hasattr(hover_item, 'use'):  # Consumable item
                title_text = title_font.render("Consumable Details", True, (235, 210, 190))
                screen.blit(title_text, (rect.x + 10, rect.y + 10))
                self._draw_consumable_details(screen, hover_item, rect)
        else:
            # Show equipment effects when no item is hovered
            title_text = title_font.render("Equipment Effects", True, (235, 210, 190))
            screen.blit(title_text, (rect.x + 10, rect.y + 10))
            self._draw_equipment_effects(screen, rect)
    
    def _draw_gear_details(self, screen, item, rect):
        """Draw detailed gear information"""
        if not hasattr(item, 'modifiers'):
            return
            
        # Draw modifiers
        details_font = get_font(12)
        details_y = rect.y + 40
        
        for stat, value in item.modifiers.items():
            if stat == 'max_hp':
                mod_text = f"HP +{value}"
                color = (255, 150, 150)
            elif stat == 'attack_damage':
                mod_text = f"Attack +{value}"
                color = (255, 200, 100)
            elif stat == 'max_mana':
                mod_text = f"Mana +{value}"
                color = (100, 150, 255)
            elif stat == 'max_stamina':
                mod_text = f"Stamina +{value}"
                color = (150, 255, 150)
            elif stat == 'player_speed':
                mod_text = f"Speed +{value:.1f}"
                color = (200, 200, 255)
            else:
                mod_text = f"{stat} +{value}"
                color = (200, 200, 200)
            
            mod_surface = details_font.render(mod_text, True, color)
            screen.blit(mod_surface, (rect.x + 15, details_y))
            details_y += 18
        
        # Draw price
        price = self._get_item_price(item)
        price_text = details_font.render(f"Price: {price} coins", True, (255, 215, 0))
        screen.blit(price_text, (rect.x + 15, details_y + 10))
    
    def _draw_consumable_details(self, screen, item, rect):
        """Draw detailed consumable information"""
        details_font = get_font(12)
        details_y = rect.y + 40
        
        # Draw effect text
        if hasattr(item, 'effect_text') and item.effect_text:
            effect_lines = item.effect_text.split('\n') if '\n' in item.effect_text else [item.effect_text]
            for line in effect_lines:
                effect_surface = details_font.render(line, True, (200, 200, 215))
                screen.blit(effect_surface, (rect.x + 15, details_y))
                details_y += 18
        
        # Draw stock and price
        stock = self.consumable_stock.get(item.key, 0)
        price = self._get_item_price(item)
        
        stock_text = details_font.render(f"Available: {stock}", True, (150, 255, 150))
        screen.blit(stock_text, (rect.x + 15, details_y + 10))
        
        price_text = details_font.render(f"Price: {price} coins", True, (255, 215, 0))
        screen.blit(price_text, (rect.x + 15, details_y + 30))
    
    def _draw_equipment_effects(self, screen, rect):
        """Draw current equipment effects"""
        if not hasattr(self.game, 'inventory') or not self.game.inventory.gear_slots:
            no_effects_text = get_font(12).render("No equipment equipped", True, (180, 180, 200))
            screen.blit(no_effects_text, (rect.x + 15, rect.y + 40))
            return
        
        details_font = get_font(11)
        details_y = rect.y + 40
        
        for i, key in enumerate(self.game.inventory.gear_slots):
            if key and key in self.game.inventory.armament_catalog:
                item = self.game.inventory.armament_catalog[key]
                
                # Item name
                item_name = details_font.render(f"• {item.name}", True, (200, 200, 215))
                screen.blit(item_name, (rect.x + 15, details_y))
                details_y += 15
                
                # Show modifiers
                for stat, value in item.modifiers.items():
                    if stat == 'max_hp':
                        mod_text = f"  HP +{value}"
                        color = (255, 150, 150)
                    elif stat == 'attack_damage':
                        mod_text = f"  Attack +{value}"
                        color = (255, 200, 100)
                    elif stat == 'max_mana':
                        mod_text = f"  Mana +{value}"
                        color = (100, 150, 255)
                    elif stat == 'max_stamina':
                        mod_text = f"  Stamina +{value}"
                        color = (150, 255, 150)
                    elif stat == 'player_speed':
                        mod_text = f"  Speed +{value:.1f}"
                        color = (200, 200, 255)
                    else:
                        mod_text = f"  {stat} +{value}"
                        color = (180, 180, 180)
                    
                    mod_surface = details_font.render(mod_text, True, color)
                    screen.blit(mod_surface, (rect.x + 20, details_y))
                    details_y += 12
                
                details_y += 8  # Extra spacing between items
    
    def _draw_equipped_item(self, screen, item, rect):
        """Draw an equipped item"""
        # Draw item background
        pygame.draw.rect(screen, item.color, rect.inflate(-8, -8), border_radius=6)
        
        # Draw rarity border
        border_color = rarity_border_color(item)
        pygame.draw.rect(screen, border_color, rect, width=2, border_radius=8)
        
        # Draw icon
        icon_rect = pygame.Rect(rect.x + 5, rect.y + 5, rect.width - 10, rect.height - 10)
        icon_surf = None
        if hasattr(item, 'icon_path') and item.icon_path:
            surf = _safe_load_icon(item.icon_path, (icon_rect.width, icon_rect.height))
            if surf:
                icon_surf = surf
            else:
                try:
                    icon_surf = load_icon_masked(item.icon_path, (icon_rect.width, icon_rect.height), radius=6)
                except Exception:
                    icon_surf = None
        if icon_surf:
            screen.blit(icon_surf, icon_rect)
        else:
            if hasattr(item, 'icon_letter'):
                icon_text = get_font(16, bold=True).render(item.icon_letter, True, (20, 20, 28))
                icon_text_rect = icon_text.get_rect(center=icon_rect.center)
                screen.blit(icon_text, icon_text_rect)
    
    def _draw_gear_list(self, screen, rect, gear_items):
        """Draw gear list with details and buy buttons"""
        # List items - make them much larger to match inventory icons
        item_height = 80  # Increased to accommodate 60x60 icons
        item_spacing = 6  # Increased spacing
        start_y = rect.y + 10
        
        # Calculate visible range with scrolling
        start_index = self.gear_scroll_offset
        end_index = min(start_index + self.max_visible_gear, len(gear_items))
        
        for i in range(start_index, end_index):
            item = gear_items[i]
            visible_index = i - start_index  # Index for positioning within visible area
                
            item_rect = pygame.Rect(rect.x + 10, start_y + visible_index * (item_height + item_spacing), rect.width - 20, item_height)
            
            if item_rect.bottom > rect.bottom:
                break
            
            # Highlight selected item
            if i == self.selection and self.selection_category == 'gear':
                pygame.draw.rect(screen, (60, 60, 80), item_rect, border_radius=4)
                pygame.draw.rect(screen, (255, 210, 120), item_rect, width=2, border_radius=4)
            else:
                pygame.draw.rect(screen, (40, 40, 50), item_rect, border_radius=4)
                border_color = rarity_border_color(item)
                pygame.draw.rect(screen, border_color, item_rect, width=1, border_radius=4)
            
            # Item icon
            icon_rect = pygame.Rect(item_rect.x + 8, item_rect.y + 8, 60, 60)  # Match inventory size (60x60)
            icon_surf = None
            if hasattr(item, 'icon_path') and item.icon_path:
                surf = _safe_load_icon(item.icon_path, (icon_rect.width, icon_rect.height))
                if surf:
                    icon_surf = surf
                else:
                    try:
                        icon_surf = load_icon_masked(item.icon_path, (icon_rect.width, icon_rect.height), radius=6)
                    except Exception:
                        icon_surf = None
            # Draw rarity border around icon
            border_color = rarity_border_color(item)
            pygame.draw.rect(screen, border_color, icon_rect.inflate(4, 4), width=2, border_radius=8)
            
            if icon_surf:
                screen.blit(icon_surf, icon_rect)
            else:
                pygame.draw.rect(screen, item.color, icon_rect, border_radius=6)
                if hasattr(item, 'icon_letter'):
                    icon_text = get_font(18, bold=True).render(item.icon_letter, True, (20, 20, 28))
                    icon_text_rect = icon_text.get_rect(center=icon_rect.center)
                    screen.blit(icon_text, icon_text_rect)
            
            # Item name
            name_font = get_font(14)  # Increased for better visibility
            name_text = name_font.render(item.name, True, (220, 220, 235))
            screen.blit(name_text, (item_rect.x + 75, item_rect.y + 8))
            
            # Price and buy button
            price = self._get_item_price(item)
            price_font = get_font(12, bold=True)  # Increased from 10
            button_font = get_font(11, bold=True)  # Increased from 9
            
            # Price
            price_color = GREEN if self.game.player.money >= price else (150, 150, 150)
            price_text = price_font.render(f"{price}c", True, price_color)
            screen.blit(price_text, (item_rect.x + 75, item_rect.y + 28))
            
            # Buy button
            button_rect = pygame.Rect(item_rect.right - 65, item_rect.y + 25, 60, 25)  # Even larger button
            
            # Check if sold out or owned
            is_sold_out = False
            button_text = "BUY"
            
            player_owns_item = False
            if hasattr(self.game, 'inventory'):
                player_owns_item = item.key in self.game.inventory.armament_order
                
            if item.key in self.purchased_equipment or player_owns_item:
                is_sold_out = True
                button_text = "SOLD"
            
            # Button color
            if is_sold_out:
                button_color = (60, 60, 60)
            elif self.game.player.money >= price:
                button_color = (0, 150, 0)
            else:
                button_color = (100, 80, 80)
            
            pygame.draw.rect(screen, button_color, button_rect, border_radius=2)
            pygame.draw.rect(screen, (150, 150, 170), button_rect, width=1, border_radius=2)
            
            button_text_color = (180, 180, 180) if is_sold_out else (255, 255, 255)
            button_surface = button_font.render(button_text, True, button_text_color)
            button_text_rect = button_surface.get_rect(center=button_rect.center)
            screen.blit(button_surface, button_text_rect)
            
            # Register regions
            self.regions.append({'rect': button_rect, 'item': item, 'action': 'buy'})
            self.regions.append({'rect': item_rect, 'item': item})
        
        # Draw scroll indicators for gear
        total_gear_items = len(gear_items)
        if total_gear_items > self.max_visible_gear:
            self._draw_scroll_indicators(screen, rect, total_gear_items, self.gear_scroll_offset, 'gear', self.max_visible_gear)
    
    def _draw_consumable_list(self, screen, rect, consumable_items):
        """Draw consumable list with details and buy buttons"""
        # List items - make them much larger to match inventory icons
        item_height = 80  # Increased to accommodate 60x60 icons
        item_spacing = 6  # Increased spacing
        start_y = rect.y + 10
        
        # Calculate visible range with scrolling
        start_index = self.consumable_scroll_offset
        end_index = min(start_index + self.max_visible_consumables, len(consumable_items))
        
        for i in range(start_index, end_index):
            item = consumable_items[i]
            visible_index = i - start_index  # Index for positioning within visible area
                
            item_rect = pygame.Rect(rect.x + 10, start_y + visible_index * (item_height + item_spacing), rect.width - 20, item_height)
            
            if item_rect.bottom > rect.bottom:
                break
            
            # Highlight selected item
            if i == self.selection and self.selection_category == 'consumable':
                pygame.draw.rect(screen, (60, 60, 80), item_rect, border_radius=4)
                pygame.draw.rect(screen, (255, 210, 120), item_rect, width=2, border_radius=4)
            else:
                pygame.draw.rect(screen, (40, 40, 50), item_rect, border_radius=4)
                border_color = rarity_border_color(item)
                pygame.draw.rect(screen, border_color, item_rect, width=1, border_radius=4)
            
            # Item icon - same size as gear (60x60)
            icon_rect = pygame.Rect(item_rect.x + 8, item_rect.y + 8, 60, 60)  # Match gear size
            icon_surf = None
            if hasattr(item, 'icon_path') and item.icon_path:
                surf = _safe_load_icon(item.icon_path, (icon_rect.width, icon_rect.height))
                if surf:
                    icon_surf = surf
                else:
                    try:
                        icon_surf = load_icon_masked(item.icon_path, (icon_rect.width, icon_rect.height), radius=6)
                    except Exception:
                        icon_surf = None
            
            # Draw rarity border around icon
            border_color = rarity_border_color(item)
            pygame.draw.rect(screen, border_color, icon_rect.inflate(4, 4), width=2, border_radius=8)
            
            if icon_surf:
                screen.blit(icon_surf, icon_rect)
            else:
                pygame.draw.rect(screen, item.color, icon_rect, border_radius=6)
                if hasattr(item, 'icon_letter'):
                    icon_text = get_font(18, bold=True).render(item.icon_letter, True, (20, 20, 28))
                    icon_text_rect = icon_text.get_rect(center=icon_rect.center)
                    screen.blit(icon_text, icon_text_rect)
            
            # Item name
            name_font = get_font(14)  # Increased for better visibility
            name_text = name_font.render(item.name, True, (220, 220, 235))
            screen.blit(name_text, (item_rect.x + 75, item_rect.y + 8))
            
            # Stock count
            stock = self.consumable_stock.get(item.key, 0)
            stock_font = get_font(12)  # Increased from 10
            stock_text = stock_font.render(f"Stock: {stock}", True, (150, 255, 150))
            screen.blit(stock_text, (item_rect.x + 75, item_rect.y + 28))
            
            # Price and buy button
            price = self._get_item_price(item)
            price_font = get_font(12, bold=True)  # Increased from 10
            button_font = get_font(11, bold=True)  # Increased from 9
            
            # Price
            price_color = GREEN if self.game.player.money >= price else (150, 150, 150)
            price_text = price_font.render(f"{price}c", True, price_color)
            screen.blit(price_text, (item_rect.x + 75, item_rect.y + 48))
            
            # Buy button
            button_rect = pygame.Rect(item_rect.right - 65, item_rect.y + 25, 60, 25)  # Even larger button
            
            # Check if sold out
            is_sold_out = stock <= 0
            button_text = "BUY" if not is_sold_out else "SOLD"
            
            # Button color
            if is_sold_out:
                button_color = (60, 60, 60)
            elif self.game.player.money >= price:
                button_color = (0, 150, 0)
            else:
                button_color = (100, 80, 80)
            
            pygame.draw.rect(screen, button_color, button_rect, border_radius=2)
            pygame.draw.rect(screen, (150, 150, 170), button_rect, width=1, border_radius=2)
            
            button_text_color = (180, 180, 180) if is_sold_out else (255, 255, 255)
            button_surface = button_font.render(button_text, True, button_text_color)
            button_text_rect = button_surface.get_rect(center=button_rect.center)
            screen.blit(button_surface, button_text_rect)
            
            # Register regions
            self.regions.append({'rect': button_rect, 'item': item, 'action': 'buy'})
            self.regions.append({'rect': item_rect, 'item': item})
        
        # Draw scroll indicators for consumables
        total_consumable_items = len(consumable_items)
        if total_consumable_items > self.max_visible_consumables:
            self._draw_scroll_indicators(screen, rect, total_consumable_items, self.consumable_scroll_offset, 'consumable', self.max_visible_consumables)
    
    
    def _draw_scroll_indicators(self, screen, rect, total_items, scroll_offset, list_type, max_visible):
        """Draw scroll indicators for lists"""
        if total_items <= max_visible:
            return  # No scrolling needed
        
        # Draw scroll up arrow
        if scroll_offset > 0:
            arrow_up_rect = pygame.Rect(rect.right - 25, rect.y + 5, 20, 15)
            pygame.draw.polygon(screen, (200, 200, 200), [
                (arrow_up_rect.centerx, arrow_up_rect.y + 3),
                (arrow_up_rect.x + 3, arrow_up_rect.bottom - 3),
                (arrow_up_rect.right - 3, arrow_up_rect.bottom - 3)
            ])
            self.regions.append({'rect': arrow_up_rect, 'action': f'scroll_up_{list_type}'})
        
        # Draw scroll down arrow
        if scroll_offset + max_visible < total_items:
            arrow_down_rect = pygame.Rect(rect.right - 25, rect.bottom - 20, 20, 15)
            pygame.draw.polygon(screen, (200, 200, 200), [
                (arrow_down_rect.centerx, arrow_down_rect.bottom - 3),
                (arrow_down_rect.x + 3, arrow_down_rect.y + 3),
                (arrow_down_rect.right - 3, arrow_down_rect.y + 3)
            ])
            self.regions.append({'rect': arrow_down_rect, 'action': f'scroll_down_{list_type}'})
        
        # Draw scroll position indicator
        if total_items > 0:
            scroll_progress = scroll_offset / (total_items - max_visible)
            indicator_height = max(20, int((max_visible / total_items) * (rect.height - 40)))
            indicator_y = rect.y + 20 + int(scroll_progress * (rect.height - 40 - indicator_height))
            indicator_rect = pygame.Rect(rect.right - 8, indicator_y, 4, indicator_height)
            pygame.draw.rect(screen, (150, 150, 150), indicator_rect, border_radius=2)
    
    def _scroll_up(self):
        """Scroll up in current list"""
        if self.selection_category == 'gear':
            if self.gear_scroll_offset > 0:
                self.gear_scroll_offset -= 1
                # Adjust selection if needed
                if self.selection < self.gear_scroll_offset:
                    self.selection = self.gear_scroll_offset
        else:  # consumable
            if self.consumable_scroll_offset > 0:
                self.consumable_scroll_offset -= 1
                # Adjust selection if needed
                if self.selection < self.consumable_scroll_offset:
                    self.selection = self.consumable_scroll_offset
    
    def _scroll_down(self):
        """Scroll down in current list"""
        if self.selection_category == 'gear':
            max_scroll = max(0, len(self.selected_gear) - self.max_visible_gear)
            if self.gear_scroll_offset < max_scroll:
                self.gear_scroll_offset += 1
                # Adjust selection if needed
                if self.selection >= self.gear_scroll_offset + self.max_visible_gear:
                    self.selection = self.gear_scroll_offset + self.max_visible_gear - 1
        else:  # consumable
            max_scroll = max(0, len(self.selected_consumables) - self.max_visible_consumables)
            if self.consumable_scroll_offset < max_scroll:
                self.consumable_scroll_offset += 1
                # Adjust selection if needed
                if self.selection >= self.consumable_scroll_offset + self.max_visible_consumables:
                    self.selection = self.consumable_scroll_offset + self.max_visible_consumables - 1
    
    def _scroll_to_top(self):
        """Scroll to top of current list"""
        if self.selection_category == 'gear':
            self.gear_scroll_offset = 0
            self.selection = 0
        else:  # consumable
            self.consumable_scroll_offset = 0
            self.selection = 0
    
    def _scroll_to_bottom(self):
        """Scroll to bottom of current list"""
        if self.selection_category == 'gear':
            self.gear_scroll_offset = max(0, len(self.selected_gear) - self.max_visible_gear)
            self.selection = len(self.selected_gear) - 1
        else:  # consumable
            self.consumable_scroll_offset = max(0, len(self.selected_consumables) - self.max_visible_consumables)
            self.selection = len(self.selected_consumables) - 1
    
    def handle_mouse_click(self, pos):
        """Handle mouse clicks in shop"""
        if not self.shop_open:
            return
        
        for info in self.regions:
            if info['rect'].collidepoint(pos):
                if info.get('action') == 'buy':
                    item = info.get('item')
                    if item:
                        self.purchase_item(item)
                elif info.get('action') == 'exit':
                    self.close_shop()
                elif info.get('action') == 'scroll_up_gear':
                    if self.gear_scroll_offset > 0:
                        self.gear_scroll_offset -= 1
                        if self.selection < self.gear_scroll_offset:
                            self.selection = self.gear_scroll_offset
                elif info.get('action') == 'scroll_down_gear':
                    max_scroll = max(0, len(self.selected_gear) - self.max_visible_gear)
                    if self.gear_scroll_offset < max_scroll:
                        self.gear_scroll_offset += 1
                        if self.selection >= self.gear_scroll_offset + self.max_visible_gear:
                            self.selection = self.gear_scroll_offset + self.max_visible_gear - 1
                elif info.get('action') == 'scroll_up_consumable':
                    if self.consumable_scroll_offset > 0:
                        self.consumable_scroll_offset -= 1
                        if self.selection < self.consumable_scroll_offset:
                            self.selection = self.consumable_scroll_offset
                elif info.get('action') == 'scroll_down_consumable':
                    max_scroll = max(0, len(self.selected_consumables) - self.max_visible_consumables)
                    if self.consumable_scroll_offset < max_scroll:
                        self.consumable_scroll_offset += 1
                        if self.selection >= self.consumable_scroll_offset + self.max_visible_consumables:
                            self.selection = self.consumable_scroll_offset + self.max_visible_consumables - 1
                elif info.get('item'):
                    # Click on item area - select it
                    item = info.get('item')
                    if item:
                        # Determine category and update selection
                        if hasattr(item, 'modifiers'):  # Gear
                            self.selection_category = 'gear'
                            try:
                                self.selection = self.selected_gear.index(item)
                            except ValueError:
                                pass
                        elif hasattr(item, 'use'):  # Consumable
                            self.selection_category = 'consumable'
                            try:
                                self.selection = self.selected_consumables.index(item)
                            except ValueError:
                                pass
                break
    
    def _get_item_price(self, item):
        """Calculate price for an item based on its properties"""
        if hasattr(item, 'amount'):  # Heal consumable
            base_price = 10 * item.amount
        elif hasattr(item, 'modifiers'):  # Equipment
            # Price based on total modifier values
            total_mods = sum(abs(v) for v in item.modifiers.values())
            base_price = int(50 * total_mods)
        else:  # Other consumables
            base_price = 30
        
        # Add some randomness but keep it consistent for this shop session
        if not hasattr(self, '_price_cache'):
            self._price_cache = {}
        
        if item.key not in self._price_cache:
            self._price_cache[item.key] = max(10, int(base_price * random.uniform(0.8, 1.2)))
        
        return self._price_cache[item.key]
