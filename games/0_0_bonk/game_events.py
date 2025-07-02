"""Events specific to Bonk Boi game with bonus games."""

from copy import deepcopy
from src.events.events import json_ready_sym, EventConstants


class BonkBoiEvents:
    """Handle events for Bonk Boi multiplier game with bonus games."""

    def __init__(self, calculations):
        self.calculations = calculations
        self.bonus_mode = False
        self.super_bonus_mode = False
        # self.horny_jail_mode = False
        self.bonus_spins_left = 0
        self.sticky_multiplier = 1
        self.bonus_state = None
        self.last_spin_win = 0
        self.current_reel_set = "BR0"  # Default to BR0 for base game
        self.bonus_session_id = None
        self.bonus_spins_completed = 0
        self.total_bonus_win = 0

    def set_reel_set(self, reel_set):
        """Set the current reel set (BR0, BON1, or BON2)"""
        self.current_reel_set = reel_set

    def trigger_bonus(self, bonus_type):
        """Trigger bonus mode based on bonus type"""
        if bonus_type == "BONK_SPINS":
            self.bonus_mode = True
            self.bonus_spins_left = 10
            self.bonus_state = self.trigger_bonus_game("BONK_SPINS")
            # Switch to BON1 reels for first bonus game (Bat: 50, Golden Bat: 10)
            self.set_reel_set("BON1")
        elif bonus_type == "SUPER_BONK_SPINS":
            self.super_bonus_mode = True
            self.bonus_spins_left = 15
            self.sticky_multiplier = 2
            self.bonus_state = self.trigger_bonus_game("SUPER_BONK_SPINS")
            # Switch to BON2 reels for second bonus game (Bat: 0, Golden Bat: 10)
            self.set_reel_set("BON2")

    def trigger_bonus_game(self, bonus_type: str) -> dict:
        """Initialize bonus game state"""
        if bonus_type == "BONK_SPINS":
            return {
                "type": "BONK_SPINS",
                "spins_left": 10,
                "multiplier": 1,
                "total_win": 0,
                "symbols_collected": []
            }
        elif bonus_type == "SUPER_BONK_SPINS":
            return {
                "type": "SUPER_BONK_SPINS",
                "spins_left": 15,
                "multiplier": 2,
                "total_win": 0,
                "symbols_collected": []
            }
        else:
            return {
                "type": "UNKNOWN",
                "spins_left": 0,
                "multiplier": 1,
                "total_win": 0,
                "symbols_collected": []
            }

    def process_spin(self, reels):
        """Process a spin with given reel symbols"""
        if len(reels) != 2:
            return 0, None
        
        symbol1, symbol2 = reels
        
        # Check for bonus symbols first
        if symbol1 in ["Bat", "Golden Bat"] or symbol2 in ["Bat", "Golden Bat"]:
            # Determine bonus type based on symbols and current reel set
            if "Golden Bat" in [symbol1, symbol2]:
                bonus_type = "SUPER_BONK_SPINS"
            elif "Bat" in [symbol1, symbol2] and self.current_reel_set == "BR0":
                # Only trigger Bat bonus in base game (BR0)
                bonus_type = "BONK_SPINS"
            else:
                # No bonus trigger in bonus reels for Bat symbols
                return 0, None
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
        """Process a bonus spin with bonus game logic"""
        # If we're in bonus mode, use bonus game logic
        if self.bonus_mode or self.super_bonus_mode:
            if self.bonus_state:
                # Store previous total win
                previous_total = self.bonus_state["total_win"]
                
                # Process through bonus game
                self.bonus_state = self.process_bonus_spin_logic(self.bonus_state, reels)
                
                # Calculate this spin's win
                spin_win = self.bonus_state["total_win"] - previous_total
                self.last_spin_win = spin_win
                
                return spin_win, None
            else:
                # Fallback to old logic
                base_win, bonus = self.process_spin(reels)
                if self.bonus_mode or self.super_bonus_mode:
                    final_win = base_win * self.sticky_multiplier
                    return final_win, bonus
                return base_win, bonus
        else:
            # Regular spin processing
            base_win, bonus = self.process_spin(reels)
            if self.bonus_mode or self.super_bonus_mode:
                final_win = base_win * self.sticky_multiplier
                return final_win, bonus
            return base_win, bonus

    def process_bonus_spin_logic(self, bonus_state: dict, reel_symbols: list) -> dict:
        """Process a single bonus spin with bonus game logic"""
        if bonus_state["spins_left"] <= 0:
            return bonus_state
        
        bonus_type = bonus_state["type"]
        spin_multiplier = self.calculate_bonus_win(reel_symbols, bonus_type)
        final_multiplier = spin_multiplier * bonus_state["multiplier"]
        bonus_state["total_win"] += final_multiplier
        bonus_state["symbols_collected"].extend(reel_symbols)
        bonus_state["spins_left"] -= 1
        
        # Golden Bat gives extra spins and multiplier boost
        if "Golden Bat" in reel_symbols:
            bonus_state["spins_left"] += 5
            bonus_state["multiplier"] += 1
        
        return bonus_state

    def calculate_bonus_win(self, symbols: list, bonus_type: str) -> int:
        """Calculate win multiplier from bonus game symbols"""
        total_multiplier = 0
        
        # Define symbol values for different bonus types
        if bonus_type == "BONK_SPINS":
            # BON1: Bat=50, Golden Bat=10
            bonus_symbols = {
                "1": 1, "2": 2, "3": 3, "5": 5, "10": 10,
                "25": 25, "50": 50, "100": 100, "250": 250,
                "500": 500, "1000": 1000, "Bat": 50, "Golden Bat": 10
            }
        elif bonus_type == "SUPER_BONK_SPINS":
            # BON2: Bat=0, Golden Bat=10
            bonus_symbols = {
                "1": 1, "2": 2, "3": 3, "5": 5, "10": 10,
                "25": 25, "50": 50, "100": 100, "250": 250,
                "500": 500, "1000": 1000, "Bat": 0, "Golden Bat": 10
            }
        else:
            return 0
        
        for symbol in symbols:
            total_multiplier += bonus_symbols.get(symbol, 0)
        
        return total_multiplier

    def is_bonus_complete(self):
        """Check if current bonus game is complete"""
        if self.bonus_state:
            return self.bonus_state["spins_left"] <= 0
        return self.bonus_spins_left <= 0

    def get_bonus_summary(self):
        """Get summary of completed bonus game"""
        if self.bonus_state:
            return {
                "type": self.bonus_state["type"],
                "total_win": self.bonus_state["total_win"],
                "symbols_collected": self.bonus_state["symbols_collected"],
                "final_multiplier": self.bonus_state["multiplier"]
            }
        return None

    def reset_to_base_game(self):
        """Reset to base game mode with BR0 reels"""
        self.bonus_mode = False
        self.super_bonus_mode = False
        self.bonus_spins_left = 0
        self.sticky_multiplier = 1
        self.bonus_state = None
        self.last_spin_win = 0
        self.current_reel_set = "BR0"
        self.bonus_session_id = None
        self.bonus_spins_completed = 0
        self.total_bonus_win = 0


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
