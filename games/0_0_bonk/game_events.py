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

    def trigger_bonus(self, bonus_type, spins_count=None):
        """Trigger bonus mode based on bonus type"""
        if bonus_type == "BONK_SPINS":
            self.bonus_mode = True
            self.bonus_spins_left = spins_count if spins_count else 10
            self.bonus_state = self.trigger_bonus_game("BONK_SPINS", self.bonus_spins_left)
            # Switch to BON1 reels for first bonus game (Bat: 50, Golden Bat: 10)
            self.set_reel_set("BON1")
        elif bonus_type == "SUPER_BONK_SPINS":
            self.super_bonus_mode = True
            self.bonus_spins_left = spins_count if spins_count else 10
            self.sticky_multiplier = 2
            self.bonus_state = self.trigger_bonus_game("SUPER_BONK_SPINS", self.bonus_spins_left)
            # Switch to BON2 reels for second bonus game (Bat: 0, Golden Bat: 10)
            self.set_reel_set("BON2")
        
        # Reset bonus session tracking
        self.bonus_session_id = None
        self.bonus_spins_completed = 0
        self.total_bonus_win = 0

    def trigger_bonus_game(self, bonus_type: str, spins_left: int) -> dict:
        """Initialize bonus game state"""
        if bonus_type == "BONK_SPINS":
            return {
                "type": "BONK_SPINS",
                "spins_left": spins_left,
                "multiplier": 1,
                "total_win": 0,
                "symbols_collected": [],
                "upgraded_from_bonk": False
            }
        elif bonus_type == "SUPER_BONK_SPINS":
            return {
                "type": "SUPER_BONK_SPINS",
                "spins_left": spins_left,
                "multiplier": 2,
                "total_win": 0,
                "symbols_collected": [],
                "upgraded_from_bonk": False
            }
        else:
            return {
                "type": "UNKNOWN",
                "spins_left": 0,
                "multiplier": 1,
                "total_win": 0,
                "symbols_collected": [],
                "upgraded_from_bonk": False
            }

    def process_spin(self, reels):
        """Process a spin with given reel symbols"""
        if len(reels) != 2:
            return 0, None
        
        symbol1, symbol2 = reels
        
        # Count bonus symbols
        bonus_count = sum(1 for symbol in reels if symbol == "Bat")
        super_bonus_count = sum(1 for symbol in reels if symbol == "Golden Bat")
        
        # If we have bonus symbols, trigger bonus
        if bonus_count > 0 or super_bonus_count > 0:
            if super_bonus_count > 0:
                bonus_type = "SUPER_BONK_SPINS"
            else:
                bonus_type = "BONK_SPINS"
            
            # Calculate base game win even with bonus symbols
            # Bonus symbols (Bat, Golden Bat) have value 1
            try:
                mult1 = 1 if symbol1 in ["Bat", "Golden Bat"] else int(symbol1)
                mult2 = 1 if symbol2 in ["Bat", "Golden Bat"] else int(symbol2)
                
                # Apply 1x1=0 rule for bonus symbols too
                if mult1 == 1 and mult2 == 1:
                    base_win = 0
                else:
                    base_win = mult1 * mult2
                
                return base_win, bonus_type
            except ValueError:
                return 0, bonus_type
        
        # Check if both symbols are "1" - this should return 0 win, no bonus
        if symbol1 == "1" and symbol2 == "1":
            return 0, None
        
        # Calculate win by multiplying symbols
        try:
            mult1 = int(symbol1)
            mult2 = int(symbol2)
            win = mult1 * mult2
            return win, None
        except ValueError:
            return 0, None

    def process_bonus_spin(self, reels):
        """Process a bonus spin with bonus game logic"""
        # If we're in bonus mode, use bonus game logic
        if self.bonus_mode or self.super_bonus_mode:
            if self.bonus_state:
                # Store previous total win
                previous_total = self.bonus_state["total_win"]
                
                # Check if this is buy_bonk_spins mode (using BR0 reels with base game logic)
                if self.current_reel_set == "BR0" and self.bonus_state["type"] == "BONK_SPINS":
                    # Use base game logic for buy_bonk_spins mode
                    spin_win = self.calculate_base_game_win(reels)
                else:
                    # Use regular bonus game logic
                    self.bonus_state = self.process_bonus_spin_logic(self.bonus_state, reels, self.bonus_state["type"])
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

    def process_bonus_spin_logic(self, bonus_state: dict, reel_symbols: list, bonus_type: str) -> dict:
        """Process bonus spin logic for both BONK_SPINS and SUPER_BONK_SPINS"""
        
        if bonus_type == "SUPER_BONK_SPINS":
            result = self.process_super_bonk_spin(bonus_state, reel_symbols)
        else:
            result = self.process_bonk_spin(bonus_state, reel_symbols)
        
        return result

    def process_bonk_spin(self, bonus_state: dict, reel_symbols: list) -> dict:
        """Process BONK_SPINS logic"""
        # Calculate win using bonus spin rules
        def get_symbol_value(symbol):
            if symbol in ["Bat", "Golden Bat"]:
                return 1
            elif symbol in ["1", "2", "3", "5", "10", "25", "50", "100", "250", "500", "1000"]:
                return int(symbol)
            else:
                return 0
        
        mult1 = get_symbol_value(reel_symbols[0]) if len(reel_symbols) > 0 else 0
        mult2 = get_symbol_value(reel_symbols[1]) if len(reel_symbols) > 1 else 0
        
        # Apply 1x1=0 rule ONLY when both values are exactly 1
        if mult1 == 1 and mult2 == 1:
            spin_win = 0
        else:
            spin_win = mult1 * mult2
        
        # Add to total win
        old_total_win = bonus_state["total_win"]
        bonus_state["total_win"] += spin_win
        
        # Handle bonus symbols
        bonus_spins_added = 0
        for symbol in reel_symbols:
            if symbol == "Bat":
                bonus_spins_added += 5
            elif symbol == "Golden Bat":
                bonus_spins_added += 5
                # Golden Bat in Bonk Spins upgrades to Super Bonk Spins
                bonus_state["upgrade_to_super"] = True
                # ACTUALLY PERFORM THE UPGRADE HERE
                if bonus_state["type"] == "BONK_SPINS":
                    bonus_state["type"] = "SUPER_BONK_SPINS"
                    bonus_state["multiplier"] = 4  # SUPER_BONK_SPINS has 4x multiplier
                    bonus_state["upgraded_from_bonk"] = True
                    
                    # CRITICAL: Initialize sticky values for SUPER_BONK_SPINS
                    bonus_state["sticky_value"] = None
                    bonus_state["sticky_reel"] = None
                    
                    # CRITICAL: Preserve total_win from BONK_SPINS
                    
                    # CRITICAL: Create BONUS_TRIGGER event for the upgrade
                    # We need to access gamestate to create the event
                    # This will be handled in gamestate.py after process_bonk_spin returns
        
        bonus_state["spins_left"] += bonus_spins_added
        bonus_state["symbols_collected"].extend(reel_symbols)
        bonus_state["spins_left"] -= 1
        
        # Store current spin win for gamestate to use
        bonus_state["current_spin_win"] = spin_win
        
        return bonus_state

    def process_super_bonk_spin(self, bonus_state: dict, reel_symbols: list) -> dict:
        """Process SUPER_BONK_SPINS logic with sticky value"""
        # Initialize sticky values if not present
        if "sticky_value" not in bonus_state:
            bonus_state["sticky_value"] = None
        if "sticky_reel" not in bonus_state:
            bonus_state["sticky_reel"] = None
            
        # Get numeric values from reels (Bat and Golden Bat = 0 in SUPER_BONK_SPINS mode)
        def get_symbol_value(symbol):
            if symbol == "Bat" or symbol == "Golden Bat":
                return 0
            elif symbol in ["1", "2", "3", "4", "5"]:
                return int(symbol)
            else:
                return 0
        
        mult1 = get_symbol_value(reel_symbols[0]) if len(reel_symbols) > 0 else 0
        mult2 = get_symbol_value(reel_symbols[1]) if len(reel_symbols) > 1 else 0
        
        # Calculate current spin win
        current_win = mult1 * mult2
        
        # Apply 1x1=0 rule ONLY when both values are exactly 1
        if mult1 == 1 and mult2 == 1:
            current_win = 0
        
        if current_win > 0:
            # Have win - this is when we fix the sticky value
            if bonus_state["sticky_value"] is None:
                # First time we have a win - fix the larger value and its position
                if mult1 > mult2:
                    bonus_state["sticky_value"] = mult1
                    bonus_state["sticky_reel"] = 0
                else:
                    bonus_state["sticky_value"] = mult2
                    bonus_state["sticky_reel"] = 1
            else:
                # Already have sticky value - update only if new value is larger on the SAME reel
                current_sticky_reel = bonus_state["sticky_reel"]
                current_sticky_value = bonus_state["sticky_value"]
                
                if current_sticky_reel == 0:
                    # Sticky is on reel 0, check if mult1 is larger
                    if mult1 > current_sticky_value:
                        bonus_state["sticky_value"] = mult1
                else:
                    # Sticky is on reel 1, check if mult2 is larger
                    if mult2 > current_sticky_value:
                        bonus_state["sticky_value"] = mult2
        
        # Calculate spinWin using sticky logic
        if bonus_state["sticky_value"] is not None:
            # Get the value from the non-sticky reel
            if bonus_state["sticky_reel"] == 0:
                # Sticky is on reel 0, use reel 1 value
                non_sticky_value = mult2
            else:
                # Sticky is on reel 1, use reel 0 value
                non_sticky_value = mult1
            
            # spinWin = sticky_value × non_sticky_value
            spin_win = bonus_state["sticky_value"] * non_sticky_value
            
            # Add to total_win (accumulate)
            old_total_win = bonus_state["total_win"]
            bonus_state["total_win"] += spin_win
            # Store current spin win for gamestate to use
            bonus_state["current_spin_win"] = spin_win
        else:
            # No sticky value yet - no win
            spin_win = 0
            bonus_state["current_spin_win"] = 0
        
        bonus_state["symbols_collected"].extend(reel_symbols)
        bonus_state["spins_left"] -= 1
        
        # Golden Bat gives extra spins
        bonus_spins_added = 0
        for symbol in reel_symbols:
            if symbol == "Golden Bat":
                bonus_spins_added += 5
        
        bonus_state["spins_left"] += bonus_spins_added
        
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
        return (self.bonus_spins_left <= 0 and self.super_bonus_mode == False) or (self.bonus_spins_left <= 0 and self.bonus_mode == False)

    def get_bonus_summary(self):
        """Get summary of completed bonus game"""
        if self.bonus_state:
            summary = {
                "type": self.bonus_state["type"],
                "total_win": self.bonus_state["total_win"],
                "symbols_collected": self.bonus_state["symbols_collected"],
                "final_multiplier": self.bonus_state["multiplier"]
            }
            return summary
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

    def create_bonus_trigger_event(self, gamestate, bonus_type, trigger_symbols, trigger_win, spins_received):
        """Create BONUS_TRIGGER event"""
        # Generate unique bonus session ID
        bonus_session_id = f"bonus_{len(gamestate.book.events)}_{bonus_type}"
        
        # Determine reel set based on bonus type
        if bonus_type == "SUPER_BONK_SPINS":
            reel_set = "BON2"  # SUPER_BONK_SPINS uses BON2 reels
        elif bonus_type == "BONK_SPINS":
            reel_set = "BON1"  # BONK_SPINS uses BON1 reels
        else:
            reel_set = self.current_reel_set
        
        event = {
            "index": len(gamestate.book.events),
            "type": EventConstants.BONUS_TRIGGER.value,
            "bonusType": bonus_type,
            "gameType": gamestate.gametype,
            "bonusSessionId": bonus_session_id,
            "reelSet": reel_set,
            "triggerSymbols": trigger_symbols,
            "triggerWin": trigger_win,
            "sessionWin": 0.0,  # sessionWin = 0 for buy bonus mode
            "spinsReceived": spins_received,
            "spinsLeft": spins_received
        }
        
        # Add sticky multiplier for SUPER_BONK_SPINS
        if bonus_type == "SUPER_BONK_SPINS":
            event["stickyMultiplier"] = self.sticky_multiplier
        
        gamestate.book.add_event(event)
        
        # Update bonus session ID
        self.bonus_session_id = bonus_session_id
        
        return event

    def create_bonus_spin_event(self, gamestate, spin_number, bonus_session_id, reel_set, spin_win, total_bonus_win, spins_received, spins_left):
        """Create BONUS_SPIN event"""
        # Determine actual reel set based on CURRENT bonus type (not session_id which doesn't update after upgrade)
        if gamestate.events.bonus_state and gamestate.events.bonus_state["type"] == "SUPER_BONK_SPINS":
            actual_reel_set = "BON2"  # SUPER_BONK_SPINS uses BON2 reels
        elif gamestate.events.bonus_state and gamestate.events.bonus_state["type"] == "BONK_SPINS":
            actual_reel_set = "BON1"  # BONK_SPINS uses BON1 reels
        else:
            actual_reel_set = reel_set
        
        event = {
            "index": len(gamestate.book.events),
            "type": EventConstants.BONUS_SPIN.value,
            "spinNumber": spin_number,
            "bonusSessionId": bonus_session_id,
            "reelSet": actual_reel_set,
            "spinWin": spin_win,
            "totalBonusWin": total_bonus_win,
            "spinsReceived": spins_received,
            "spinsLeft": spins_left,
            "gameType": gamestate.gametype
        }
        return event

    def create_bonus_complete_event(self, gamestate, bonus_session_id, total_bonus_win, spins_completed, bonus_type, final_multiplier):
        """Create BONUS_COMPLETE event"""
        
        event = {
            "index": len(gamestate.book.events),
            "type": EventConstants.BONUS_COMPLETE.value,
            "bonusSessionId": bonus_session_id,
            "totalBonusWin": total_bonus_win,
            "spinsCompleted": spins_completed,
            "bonusType": bonus_type,
            "finalMultiplier": final_multiplier,
            "gameType": gamestate.gametype
        }
        gamestate.book.add_event(event)
        return event

    def calculate_base_game_win(self, reels):
        """Calculate win using base game logic (multiply two symbols)"""
        if len(reels) != 2:
            return 0
            
        try:
            # Get symbols from the two reels
            symbol1 = reels[0]
            symbol2 = reels[1]
            
            # Check if both symbols are "1" - this should return 0 win (1x1=0 rule)
            if symbol1 == "1" and symbol2 == "1":
                return 0
            
            # Convert symbols to multipliers directly
            mult1 = int(symbol1)
            mult2 = int(symbol2)
            
            # Calculate win: multiply the two symbols
            win = mult1 * mult2
            return win
            
        except ValueError:
            # If symbols can't be converted to integers, return 0
            return 0

    def calculate_bonus_spin_win(self, reels):
        """Calculate win for bonus spins where Bat and Golden Bat = 1"""
        if len(reels) < 2:
            return 0
            
        symbol1 = reels[0]
        symbol2 = reels[1]
        
        # Get numeric values - Bat and Golden Bat are always 1 in all modes
        def get_symbol_value(symbol):
            if symbol == "Bat" or symbol == "Golden Bat":
                return 1
            elif symbol in ["1", "2", "3", "4", "5"]:
                return int(symbol)
            else:
                return 0
        
        mult1 = get_symbol_value(symbol1)
        mult2 = get_symbol_value(symbol2)
        
        # Apply the 1x1=0 rule ONLY when both values are exactly 1
        if mult1 == 1 and mult2 == 1:
            return 0  # 1x1=0 rule applies only to 1x1 combinations
        
        return mult1 * mult2

    def get_symbol_value(self, symbol):
        """Get numeric value of symbol for SUPER_BONK_SPINS"""
        if symbol == "Golden Bat":
            return 10
        elif symbol == "Bat":
            return 0  # Bat = 0 in SUPER_BONK_SPINS
        else:
            try:
                return int(symbol)
            except ValueError:
                return 0


def reveal_event_bonk_boi(gamestate):
    """Create reveal event for Bonk Boi game"""
    # Check if this is buy bonus mode and first reveal
    current_betmode = gamestate.get_current_betmode()
    is_buy_bonus = current_betmode and current_betmode.get_buybonus()
    is_first_reveal = len(gamestate.book.events) == 0
    
    # For buy bonus first reveal, create custom board based on bonus type
    if is_buy_bonus and is_first_reveal:
        if current_betmode._name == "buy_super_bonk_spins":
            # For SUPER_BONK_SPINS, first reveal should be Golden Bat + 1
            symbol_names = ["Golden Bat", "1"]
        else:
            # For BONK_SPINS, first reveal should be Bat + 1
            symbol_names = ["Bat", "1"]
            
        # Create custom board with appropriate symbols
        custom_board = []
        for symbol_name in symbol_names:
            # Create a simple symbol object with name attribute
            symbol_obj = type('Symbol', (), {'name': symbol_name})()
            custom_board.append([symbol_obj])
        gamestate.board = custom_board
    elif gamestate.gametype != "free":
        # Only create board for non-free gametypes (base, bonus1, bonus2)
        gamestate.create_board_reelstrips()
    
    # Convert board to JSON-ready format
    board_client = []
    special_attributes = list(gamestate.config.special_symbols.keys())
    
    # Only take the first symbol (row 0) for each of 2 reels
    for reel in range(2):  # Only 2 reels
        board_client.append([json_ready_sym(gamestate.board[reel][0], special_attributes)])
    
    # Create reveal event
    event = {
        "index": len(gamestate.book.events),
        "type": EventConstants.REVEAL.value,
        "board": board_client,
        "paddingPositions": gamestate.padding_position,
        "gameType": gamestate.gametype,
        "anticipation": [0, 0]
    }
    
    gamestate.book.add_event(event)
    
    return event
