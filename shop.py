import pygame
import random
from config import WIDTH, HEIGHT, WHITE, GREEN, CYAN
from utils import draw_text, get_font
from shop_items import build_shop_consumables, build_shop_equipment
from entities import floating, DamageNumber


class Shop:
    def __init__(self, game):
        self.game = game
        self.shop_open = False
        self.selection = 0
        self.shop_consumables = build_shop_consumables()
        self.shop_equipment = build_shop_equipment()
        
        # Create random shop inventory (3 consumables, 3 equipment)
        self.refresh_inventory()
        
        # UI regions for interaction
        self.regions = []
        
    def refresh_inventory(self):
        """Create random selection of 3 consumables and 3 equipment"""
        # Randomly select 3 consumables
        consumable_keys = list(self.shop_consumables.keys())
        random.shuffle(consumable_keys)
        self.selected_consumables = [
            self.shop_consumables[key] for key in consumable_keys[:3]
        ]
        
        # Randomly select 3 equipment
        equipment_keys = list(self.shop_equipment.keys())
        random.shuffle(equipment_keys)
        self.selected_equipment = [
            self.shop_equipment[key] for key in equipment_keys[:3]
        ]
        
        # Combine for easier iteration
        self.shop_items = self.selected_consumables + self.selected_equipment
    
    def open_shop(self):
        """Open the shop interface"""
        self.shop_open = True
        self.selection = 0
        self.refresh_inventory()
        
    def close_shop(self):
        """Close the shop interface"""
        self.shop_open = False
        self.selection = 0
        self.regions = []
    
    def can_afford(self, item):
        """Check if player can afford an item"""
        return self.game.player.money >= item.price
    
    def purchase_item(self, item):
        """Attempt to purchase an item"""
        if not self.can_afford(item):
            floating.append(DamageNumber(
                self.game.player.rect.centerx,
                self.game.player.rect.top - 12,
                "Not enough coins!",
                (255, 100, 100)
            ))
            return False
        
        # Deduct money
        self.game.player.money -= item.price
        
        # Handle different item types
        if hasattr(item, 'use'):  # Consumable
            success = item.use(self.game)
            if success:
                floating.append(DamageNumber(
                    self.game.player.rect.centerx,
                    self.game.player.rect.top - 12,
                    f"Purchased {item.name}",
                    GREEN
                ))
            else:
                # Refund if item couldn't be used
                self.game.player.money += item.price
                return False
        else:  # Equipment
            self._equip_shop_item(item)
            floating.append(DamageNumber(
                self.game.player.rect.centerx,
                self.game.player.rect.top - 12,
                f"Equipped {item.name}",
                GREEN
            ))
        
        return True
    
    def _equip_shop_item(self, equipment):
        """Handle equipment purchase and equipping"""
        # Add to inventory system
        if hasattr(self.game, 'inventory'):
            # Find empty gear slot or replace existing
            for i in range(len(self.game.inventory.gear_slots)):
                if self.game.inventory.gear_slots[i] is None:
                    self.game.inventory.gear_slots[i] = equipment.key
                    self.game.inventory.recalculate_player_stats()
                    return
                elif self.game.inventory.gear_slots[i] == equipment.key:
                    # Already equipped, just refund
                    self.game.player.money += equipment.price
                    floating.append(DamageNumber(
                        self.game.player.rect.centerx,
                        self.game.player.rect.top - 12,
                        "Already equipped!",
                        (255, 200, 100)
                    ))
                    return
            
            # All slots full, replace first slot
            self.game.inventory.gear_slots[0] = equipment.key
            self.game.inventory.recalculate_player_stats()
        else:
            # Fallback: apply modifiers directly to player
            player = self.game.player
            for stat, value in equipment.modifiers.items():
                if hasattr(player, stat):
                    setattr(player, stat, getattr(player, stat) + value)
    
    def handle_input(self):
        """Handle shop input"""
        keys = pygame.key.get_pressed()
        
        # Navigation
        if keys[pygame.K_UP]:
            self.selection = (self.selection - 1) % len(self.shop_items)
            pygame.time.wait(150)  # Prevent rapid selection
        elif keys[pygame.K_DOWN]:
            self.selection = (self.selection + 1) % len(self.shop_items)
            pygame.time.wait(150)
        
        # Purchase
        if keys[pygame.K_RETURN] or keys[pygame.K_SPACE]:
            item = self.shop_items[self.selection]
            self.purchase_item(item)
            pygame.time.wait(200)
        
        # Close shop
        if keys[pygame.K_ESCAPE] or keys[pygame.K_i]:
            self.close_shop()
            pygame.time.wait(150)
    
    def draw(self, screen):
        """Draw the shop interface"""
        if not self.shop_open:
            return
        
        # Darken background
        overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 180))
        screen.blit(overlay, (0, 0))
        
        # Shop panel
        panel_width = 600
        panel_height = 500
        panel_x = (WIDTH - panel_width) // 2
        panel_y = (HEIGHT - panel_height) // 2
        
        panel_rect = pygame.Rect(panel_x, panel_y, panel_width, panel_height)
        pygame.draw.rect(screen, (30, 28, 40), panel_rect, border_radius=12)
        pygame.draw.rect(screen, (210, 200, 170), panel_rect, width=2, border_radius=12)
        
        # Title
        title_font = get_font(28, bold=True)
        title_text = title_font.render("MYSTIC SHOP", True, (240, 220, 190))
        title_rect = title_text.get_rect(center=(panel_x + panel_width // 2, panel_y + 30))
        screen.blit(title_text, title_rect)
        
        # Player money
        money_font = get_font(20, bold=True)
        money_text = money_font.render(f"Coins: {self.game.player.money}", True, (255, 215, 0))
        money_rect = money_text.get_rect(center=(panel_x + panel_width // 2, panel_y + 60))
        screen.blit(money_text, money_rect)
        
        # Item grid
        item_font = get_font(16)
        price_font = get_font(14)
        
        # Draw items in 2 columns
        for i, item in enumerate(self.shop_items):
            row = i // 2
            col = i % 2
            
            item_x = panel_x + 50 + col * 280
            item_y = panel_y + 120 + row * 120
            
            # Item background
            item_rect = pygame.Rect(item_x, item_y, 250, 100)
            
            # Highlight selected item
            if i == self.selection:
                pygame.draw.rect(screen, (60, 60, 80), item_rect, border_radius=8)
                pygame.draw.rect(screen, (255, 210, 120), item_rect, width=2, border_radius=8)
            else:
                pygame.draw.rect(screen, (40, 40, 50), item_rect, border_radius=8)
                pygame.draw.rect(screen, (100, 100, 120), item_rect, width=1, border_radius=8)
            
            # Item icon
            icon_rect = pygame.Rect(item_x + 10, item_y + 10, 30, 30)
            pygame.draw.rect(screen, item.color, icon_rect, border_radius=6)
            
            # Item icon letter
            if hasattr(item, 'icon_letter'):
                icon_text = get_font(18, bold=True).render(item.icon_letter, True, (20, 20, 28))
                icon_text_rect = icon_text.get_rect(center=icon_rect.center)
                screen.blit(icon_text, icon_text_rect)
            
            # Item name and price
            name_color = GREEN if self.can_afford(item) else (150, 150, 150)
            name_text = item_font.render(item.name, True, name_color)
            screen.blit(name_text, (item_x + 50, item_y + 10))
            
            price_text = price_font.render(f"{item.price} coins", True, name_color)
            screen.blit(price_text, (item_x + 50, item_y + 35))
            
            # Item description (shortened)
            desc_lines = item.description.split('.')
            if desc_lines:
                short_desc = desc_lines[0][:40] + ("..." if len(desc_lines[0]) > 40 else "")
                desc_text = price_font.render(short_desc, True, (180, 180, 200))
                screen.blit(desc_text, (item_x + 50, item_y + 60))
        
        # Instructions
        inst_font = get_font(14)
        instructions = [
            "↑/↓: Navigate",
            "Enter/Space: Purchase",
            "ESC/I: Close Shop"
        ]
        
        for i, instruction in enumerate(instructions):
            inst_text = inst_font.render(instruction, True, (180, 180, 200))
            screen.blit(inst_text, (panel_x + 20, panel_y + panel_height - 80 + i * 20))