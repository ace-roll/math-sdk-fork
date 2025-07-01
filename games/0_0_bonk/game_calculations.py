"""Calculations specific to Bonk Boi game."""

from src.executables.executables import Executables


class GameCalculations(Executables):
    """Handle calculations for Bonk Boi multiplier game."""

    def __init__(self, config):
        super().__init__(config)

    def calculate_spin_result(self, reels):
        """Calculate the result of a spin based on reel symbols"""
        if len(reels) != 2:
            return 0, None
        
        symbol1, symbol2 = reels
        
        # Check for bonus symbols
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

    def assign_special_sym_function(self, *args, **kwargs):
        """Assign special symbol functions."""
        pass

    def run_freespin(self, *args, **kwargs):
        pass

    def run_spin(self, *args, **kwargs):
        pass
