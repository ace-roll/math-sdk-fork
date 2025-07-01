"""Configuration for Bonk Boi game."""

from src.config.config import Config
from src.config.betmode import BetMode
from src.config.distributions import Distribution
import os


class GameConfig(Config):
    """Configuration for Bonk Boi multiplier slot game."""

    def __init__(self):
        super().__init__()
        
        # Game ID must be in format: provider_gameNumber_rtp
        self.game_id = "0_0_bonk"  # 96% RTP target
        
        # Game type
        self.basegame_type = "base"
        self.freegame_type = "free"
        
        # Board configuration
        self.num_reels = 2
        self.num_rows = [1, 1]  # 1 row per reel
        
        # Win cap - максимальний виграш 5000x
        self.wincap = 5000.0
        
        # Paytable - multiplier values (правильні мультиплікатори)
        self.paytable = {
            (1, "1"): 1,
            (1, "2"): 2,
            (1, "3"): 3,
            (1, "5"): 5,
            (1, "10"): 10,
            (1, "25"): 25,
            (1, "50"): 50,
            (1, "100"): 100,
            (1, "250"): 250,
            (1, "500"): 500,
            (1, "1000"): 1000,
        }
        
        # Special symbols
        self.special_symbols = {
            "bonus": ["Bat", "Golden Bat"],
            "scatter": []  # No scatter symbols in this game, but needed to prevent KeyError
        }
        
        # Reel strips
        self.reel_strips = {
            "base": {
                "reels": ["games/0_0_bonk/reels/BR0.csv", "games/0_0_bonk/reels/BR0.csv"]
            }
        }
        
        # Bet modes
        self.bet_modes = [
            BetMode(
                name="base",
                cost=1.0,
                rtp=0.96,
                max_win=5000.0,  # Максимальний виграш 5000x
                auto_close_disabled=False,
                is_feature=False,
                is_buybonus=False,
                distributions=[
                    Distribution(
                        criteria="0",
                        quota=1,
                        win_criteria=None,
                        conditions={
                            "reel_weights": {self.basegame_type: {"BR0": 1}},
                            "force_wincap": False,
                            "force_freegame": False,
                        }
                    )
                ]
            )
        ]
        
        # Optimization parameters (not needed for this simple game)
        self.optimization_params = None
        
        # Event list writing
        self.write_event_list = True

        self.provider_numer = 0
        self.working_name = "Bonk Boi"
        self.win_type = "multiplier"
        self.rtp = 0.96  # RTP 96%
        
        self.construct_paths()

        # Game Dimensions

        # Board and Symbol Properties

        self.include_padding = True
        self.freespin_triggers = {self.basegame_type: {999: 0}, self.freegame_type: {999: 0}}  # Dummy high value to never trigger
        self.anticipation_triggers = {self.basegame_type: 0, self.freegame_type: 0}

        # Load reel strips using custom method for single-column format
        self.reels = {}
        
        # Load the base reel data - BR0.csv has one symbol per line
        base_reel_path = os.path.join(os.path.dirname(__file__), "reels", "BR0.csv")
        base_reel_symbols = self.read_single_column_csv(base_reel_path)
        
        # Create proper reels structure for 2-reel game
        # BR0 should be a list where each element is a list of symbols for one reel
        self.reels["BR0"] = [base_reel_symbols, base_reel_symbols]  # 2 reels, both using same symbols

        # Set up padding reels for standard system - use proper format
        self.padding_reels = {}
        self.padding_reels[self.basegame_type] = [base_reel_symbols, base_reel_symbols]  # 2 reels
        self.padding_reels[self.freegame_type] = [base_reel_symbols, base_reel_symbols]  # 2 reels

    def read_single_column_csv(self, file_path):
        """Read single column CSV file (one symbol per line)"""
        symbols = []
        with open(file_path, 'r', encoding='UTF-8') as file:
            for line in file:
                symbol = line.strip()
                if symbol:  # Skip empty lines
                    symbols.append(symbol)
        return symbols
