"""Events specific to Bonk Boi game."""

from copy import deepcopy
from src.events.events import json_ready_sym, EventConstants


class BonkBoiEvents:
    """Handle events for Bonk Boi multiplier game."""

    def __init__(self, calculations):
        self.calculations = calculations
        self.bonus_mode = False
        self.super_bonus_mode = False
        self.horny_jail_mode = False
        self.bonus_spins_left = 0
        self.sticky_multiplier = 1

    def trigger_bonus(self, bonus_type):
        """Trigger bonus mode based on bonus type"""
        if bonus_type == "BONK_SPINS":
            self.bonus_mode = True
            self.bonus_spins_left = 10
        elif bonus_type == "SUPER_BONK_SPINS":
            self.super_bonus_mode = True
            self.bonus_spins_left = 15
            self.sticky_multiplier = 1
        elif bonus_type == "HORNY_JAIL":
            self.horny_jail_mode = True
            self.bonus_spins_left = 5
            self.sticky_multiplier = 1000

    def process_spin(self, reels):
        """Process a spin with given reel symbols"""
        if len(reels) != 2:
            return 0, None
        
        symbol1, symbol2 = reels
        
        # Check for bonus symbols first
        if symbol1 in ["Bat", "Golden Bat"] or symbol2 in ["Bat", "Golden Bat"]:
            # Determine bonus type based on symbols
            if "Golden Bat" in [symbol1, symbol2]:
                bonus_type = "SUPER_BONK_SPINS"
            else:
                bonus_type = "BONK_SPINS"
            return 0, bonus_type
        
        # Regular multiplier calculation
        try:
            mult1 = int(symbol1)
            mult2 = int(symbol2)
            
            # Rule: if both symbols are "1", result is 0 (1x1=0)
            if mult1 == 1 and mult2 == 1:
                return 0, None
            
            # Calculate win: multiply the two symbols
            win = mult1 * mult2
            return win, None
            
        except ValueError:
            # If symbols can't be converted to integers, return 0
            return 0, None

    def process_bonus_spin(self, reels):
        """Process a bonus spin with sticky multiplier"""
        base_win, bonus = self.process_spin(reels)
        
        # Apply sticky multiplier if in bonus mode
        if self.bonus_mode or self.super_bonus_mode or self.horny_jail_mode:
            final_win = base_win * self.sticky_multiplier
            return final_win, bonus
        
        return base_win, bonus


def reveal_event_bonk_boi(gamestate):
    """Custom reveal event for Bonk Boi game - only shows 2 reels, 1 row each."""
    board_client = []
    special_attributes = list(gamestate.config.special_symbols.keys())
    
    # Only take the first symbol (row 0) for each of 2 reels
    for reel in range(2):  # Only 2 reels
        board_client.append([json_ready_sym(gamestate.board[reel][0], special_attributes)])

    if gamestate.config.include_padding:
        for reel in range(2):  # Only 2 reels
            board_client[reel] = [json_ready_sym(gamestate.top_symbols[reel], special_attributes)] + board_client[reel]
            board_client[reel].append(json_ready_sym(gamestate.bottom_symbols[reel], special_attributes))

    event = {
        "index": len(gamestate.book.events),
        "type": EventConstants.REVEAL.value,
        "board": board_client,
        "paddingPositions": gamestate.reel_positions[:2],  # Only first 2 positions
        "gameType": gamestate.gametype,
        "anticipation": gamestate.anticipation[:2],  # Only first 2 anticipation values
    }
    gamestate.book.add_event(event)
