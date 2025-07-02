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

    def create_board_reelstrips(self):
        """Create board using appropriate reel strips based on current game state."""
        # Determine which reel set to use based on game type
        if self.gametype == "bonus1":
            reel_set = "BON1"
        elif self.gametype == "bonus2":
            reel_set = "BON2"
        else:
            reel_set = "BR0"  # Default to base game reels
        
        # Set the reel set for this spin
        self.set_reel_set(reel_set)
        
        # Create board using parent method
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
