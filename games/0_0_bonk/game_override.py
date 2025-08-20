"""Game override functions for Bonk Boi multiplier game with bonus games."""

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
        else:
            # Create board using parent method for normal modes
            super().create_board_reelstrips()

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
        self.final_win = 1000 * second_reel_value
        
        # Set win components for proper RTP calculation
        # base_game_win should be X (second reel value), not 1000×X
        self.base_game_win = second_reel_value
        self.free_game_win = 0.0
        
        # Set random padding positions for events (like other modes)
        import random
        self.padding_position = [random.randint(0, 500), random.randint(0, 500)]
        
        # Set board in game state
        self.current_board = self.board
        
        # For Horny_Jail mode, set payoutMultiplier directly without dividing by cost
        # This ensures payoutMultiplier shows as 1000×X instead of (1000×X)/20000
        self.payout_multiplier = self.final_win
        
        # Set book fields so writer uses desired values
        if hasattr(self, 'book'):
            self.book.payout_multiplier = self.final_win
            # baseGameWins should reflect 1000×X
            self.book.basegame_wins = float(self.final_win)
            self.book.freegame_wins = 0.0
        
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
            self.win_data = {"totalWin": result_multiplier}
            
            # Mark as processed to prevent double updates
            self._horny_jail_processed = True
        
        # Do not imprint or add events here; normal flow will add REVEAL and FINALWIN in order
        
        # Return early to avoid overwriting the win calculation
        return
