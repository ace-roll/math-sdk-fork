"""Game override functions for Bonk Boi multiplier game with bonus games."""

import re
from game_executables import GameExecutables
from src.calculations.statistics import get_random_outcome


class GameStateOverride(GameExecutables):
    """Override functions for Bonk Boi game."""

    def reset_book(self):
        """Reset book and game state for new simulation."""
        super().reset_book()
        # Reset bonus game state
        self.bonus_game_active = False
        self.bonus_spins_completed = 0
        self.total_bonus_win = 0
        self.bonus_session_id = None
        # Reset Horny_Jail processing flag
        self._horny_jail_processed = False
        
        # Reset win_manager for new simulation
        if hasattr(self, 'win_manager'):
            self.win_manager.reset_end_round_wins()

    def create_board_reelstrips(self):
        """Create board using appropriate reel strips based on current game state."""
        # Determine which reel set to use based on current_reel_set from events
        if hasattr(self, 'events') and hasattr(self.events, 'current_reel_set') and self.events.current_reel_set:
            reel_set = self.events.current_reel_set
        else:
            reel_set = "BR0"  # Default to base game reels
        
        # Set the reel set for this spin
        self.set_reel_set(reel_set)
        
        # Special logic for Horny_Jail mode: first reel always shows "1000"
        if reel_set == "Horny_Jail":
            self.create_horny_jail_board()
        elif reel_set == "Bonus_Hunt":
            # Create board manually using current_reel_strips instead of parent method
            self.create_board_from_reel_strips()
        else:
            # Create board manually using current_reel_strips instead of parent method
            self.create_board_from_reel_strips()

    def create_board_from_reel_strips(self):
        """Create board manually using current_reel_strips to ensure correct symbols are used."""
        if not hasattr(self, 'current_reel_strips') or not self.current_reel_strips:
            # Fallback to parent method if current_reel_strips not set
            super().create_board_reelstrips()
            return
        
        # Check if we're in SUPER_BONK_SPINS mode and need to use sticky reels
        if (hasattr(self, 'events') and 
            hasattr(self.events, 'bonus_state') and 
            self.events.bonus_state and 
            self.events.bonus_state.get('type') == 'SUPER_BONK_SPINS' and
            self.events.bonus_state.get('sticky_reel') is not None):
            
            # Use sticky reel logic for SUPER_BONK_SPINS
            sticky_reel = self.events.bonus_state.get('sticky_reel')
            self.board = self.create_sticky_board_from_reel_strips(sticky_reel)
            # Set padding positions for events
            import random
            self.padding_position = [random.randint(0, 50000), random.randint(0, 50000)]
        else:
            # Use regular reel logic
            self.create_regular_board_from_reel_strips()

    def create_regular_board_from_reel_strips(self):
        """Create board using regular reel strips (BON2.csv for SUPER_BONK_SPINS)."""
        # Create board manually using current_reel_strips
        self.board = []
        
        # Get symbols from current reel strips
        reel1_symbols = self.current_reel_strips[0]  # First reel
        reel2_symbols = self.current_reel_strips[1]  # Second reel
        
        # Select random symbols from each reel
        import random
        
        # First reel
        symbol1_name = random.choice(reel1_symbols)
        symbol1_obj = type('Symbol', (), {'name': str(symbol1_name)})()
        self.board.append([symbol1_obj])
        
        # Second reel
        symbol2_name = random.choice(reel2_symbols)
        symbol2_obj = type('Symbol', (), {'name': str(symbol2_name)})()
        self.board.append([symbol2_obj])

        # Set padding positions for events
        self.padding_position = [random.randint(0, 50000), random.randint(0, 50000)]

    def create_sticky_board_from_reel_strips(self, sticky_reel):
        """
        Create a board with one sticky reel (BON2_stick) and one non-sticky reel (BON2_run)
        """
        import random
        
        # Get sticky reel symbols (BON2_stick.csv - only numeric)
        all_sticky_reel_strips = self.config.reels.get("BON2_stick", [])
        if not all_sticky_reel_strips:
            # Fallback to regular BON2 if BON2_stick not available
            sticky_reel_symbols = self.current_reel_strips[sticky_reel]
        else:
            sticky_reel_symbols = all_sticky_reel_strips[sticky_reel]
        
        # Get non-sticky reel symbols (BON2_run.csv - can have Golden Bat)
        non_sticky_reel = 1 if sticky_reel == 0 else 0
        all_non_sticky_reel_strips = self.config.reels.get("BON2_run", [])
        if not all_non_sticky_reel_strips:
            # Fallback to regular BON2 if BON2_run not available
            non_sticky_reel_symbols = self.current_reel_strips[non_sticky_reel]
        else:
            non_sticky_reel_symbols = all_non_sticky_reel_strips[non_sticky_reel]
        
        # Create board with sticky and non-sticky reels
        if sticky_reel == 0:
            # Sticky reel is first reel (index 0)
            symbol1_name = random.choice(sticky_reel_symbols)
            symbol2_name = random.choice(non_sticky_reel_symbols)
            
            symbol1_obj = type('Symbol', (), {'name': str(symbol1_name)})()
            symbol2_obj = type('Symbol', (), {'name': str(symbol2_name)})()
            
            board = [
                [symbol1_obj],  # Sticky reel (numeric only)
                [symbol2_obj]   # Non-sticky reel (can have Golden Bat)
            ]
        else:
            # Sticky reel is second reel (index 1)
            symbol1_name = random.choice(non_sticky_reel_symbols)
            symbol2_name = random.choice(sticky_reel_symbols)
            
            symbol1_obj = type('Symbol', (), {'name': str(symbol1_name)})()
            symbol2_obj = type('Symbol', (), {'name': str(symbol2_name)})()
            
            board = [
                [symbol1_obj],  # Non-sticky reel (can have Golden Bat)
                [symbol2_obj]   # Sticky reel (numeric only)
            ]
        
        return board

    def set_reel_set(self, reel_set):
        """Set the current reel set and update game state."""
        # Update the reel strips in the game state
        if reel_set in self.config.reels:
            # Set the current reel strips for this spin
            self.current_reel_strips = self.config.reels[reel_set]
        else:
            # Fallback to base reels if specified reel set doesn't exist
            self.current_reel_strips = self.config.reels["BR0"]

    def assign_special_sym_function(self):
        self.special_symbol_functions = {
            "M": [self.assign_mult_property],
            "W": [self.assign_mult_property],
        }

    def assign_mult_property(self, symbol):
        multiplier_value = get_random_outcome(
            self.get_current_distribution_conditions()["mult_values"][self.gametype]
        )
        symbol.multiplier = multiplier_value

    def check_game_repeat(self):
        if self.repeat == False:
            win_criteria = self.get_current_betmode_distributions().get_win_criteria()
            if win_criteria is not None and self.final_win != win_criteria:
                self.repeat = True

    def create_horny_jail_board(self):
        """Create board for Horny_Jail mode: first reel frozen on '1000', second reel spins normally."""
        
        # Create simple board structure: list of lists
        self.board = []
        
        # First reel: always frozen on "1000"
        symbol_1000 = type('Symbol', (), {'name': '1000'})()
        self.board.append([symbol_1000])
        
        # Second reel: spin normally from Horny_Jail reel set
        horny_jail_symbols = self.config.reels["Horny_Jail"][1]  # Use second reel symbols
        import random
        random_symbol = random.choice(horny_jail_symbols)
        symbol_obj = type('Symbol', (), {'name': str(random_symbol)})()
        self.board.append([symbol_obj])
        
        # Calculate win: 1000 × symbol from second reel
        second_reel_value = int(random_symbol)
        # CRITICAL: final_win should be the absolute win amount for proper calculation
        self.final_win = 1000 * second_reel_value
        
        # Set win components for proper RTP calculation
        # base_game_win should be the absolute win amount for proper RTP calculation
        self.base_game_win = 1000 * second_reel_value
        self.free_game_win = 0.0
        
        # Set random padding positions for events (like other modes)
        import random
        self.padding_position = [random.randint(0, 500), random.randint(0, 500)]
        
        # Set board in game state
        self.current_board = self.board
        
        # For Horny_Jail mode, set payoutMultiplier to absolute win amount
        # This ensures payoutMultiplier shows as 1000×X instead of multiplier units
        self.payout_multiplier = 1000 * second_reel_value
        
        # Set book fields so writer uses desired values
        if hasattr(self, 'book'):
            # CRITICAL: payoutMultiplier should be the actual win amount (e.g., 1000 × 100 = 100000)
            self.book.payout_multiplier = 1000 * second_reel_value
            # baseGameWins should reflect the base game win (e.g., 1000 × 5 = 5000)
            # base_game_win is now in multiplier units, so convert back to absolute win for display
            # CRITICAL: baseGameWins must be float type
            self.book.basegame_wins = float(1000 * second_reel_value)
            self.book.freegame_wins = 0.0
        
        # Create reveal event for Horny_Jail mode
        if hasattr(self, 'book'):
            from src.events.events import json_ready_sym, EventConstants
            
            # Convert board to JSON-ready format
            board_client = []
            special_attributes = list(self.config.special_symbols.keys())
            
            # Only take the first symbol (row 0) for each of 2 reels
            for reel in range(2):  # Only 2 reels
                board_client.append([json_ready_sym(self.board[reel][0], special_attributes)])
            
            # Create reveal event with proper structure
            reveal_event = {
                "index": len(self.book.events),
                "type": EventConstants.REVEAL.value,
                "board": board_client,
                "paddingPositions": self.padding_position,
                "gameType": self.config.basegame_type,
                "anticipation": [0, 0]
            }
            
            # Add the reveal event to the book
            self.book.add_event(reveal_event)
        
        # Update win manager for proper RTP calculation
        # Only update if we haven't already processed this spin to avoid double counting
        if hasattr(self, 'win_manager') and not getattr(self, '_horny_jail_processed', False):
            # Convert final_win to multiplier units (divide by cost)
            bet_amount = self.get_current_betmode().get_cost()
            result_multiplier = self.final_win / bet_amount if bet_amount > 0 else 0
            
            # Reset spin_win to avoid double counting
            self.win_manager.reset_spin_win()
            
            # Update win manager with the result multiplier
            self.win_manager.update_spinwin(result_multiplier)
            
            # Ensure gametype is set to basegame_type for Horny_Jail mode
            self.gametype = self.config.basegame_type
            
            # Update gametype wins
            self.win_manager.update_gametype_wins(self.config.basegame_type)
            
            # Set win_data for proper final calculation
            # finalWin.amount should show the actual win amount (1000 × 3 = 3000), not the multiplier
            self.win_data = {"totalWin": 1000 * second_reel_value}
            
            # Mark as processed to prevent double updates
            self._horny_jail_processed = True
        
        # CRITICAL: DO NOT create finalWin event here - it will be created by evaluate_finalwin()
        # This prevents finalWin events from being carried over to other modes
        
        # Do not imprint or add events here; normal flow will add FINALWIN in order
        
        # Return early to avoid overwriting the win calculation
        return
