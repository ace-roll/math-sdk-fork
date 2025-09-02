"""Game calculations for Bonk Boi multiplier game with bonus games."""

from game_executables import GameExecutables


class GameCalculations(GameExecutables):
    """Handle game-specific calculations for Bonk Boi."""

    def __init__(self, config):
        super().__init__(config)

    def calculate_spin_result(self, symbols):
        """Calculate the result of a spin based on reel symbols."""
        if len(symbols) != 2:
            return 0, None
        
        symbol1, symbol2 = symbols
        
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

    def calculate_bonus_win(self, symbols, bonus_type):
        """Calculate win for bonus game based on bonus type."""
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

    def assign_special_sym_function(self, *args, **kwargs):
        """Assign special symbol functions."""
        pass

    def run_freespin(self, *args, **kwargs):
        pass

    def run_spin(self, *args, **kwargs):
        pass
