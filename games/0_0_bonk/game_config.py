"""Configuration for Bonk Boi game with bonus games."""

from src.config.config import Config
from src.config.betmode import BetMode
from src.config.distributions import Distribution
import os


class GameConfig(Config):
    """Configuration for Bonk Boi multiplier slot game with bonus games."""

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
        
        # Win cap - максимальний виграш 10,000,000x (абсолютний максимум)
        self.wincap = 10000000.0
        
        # Bet limits - обмеження для ставок
        self.min_denomination = 0.1  # Мінімальна ставка 0.1
        self.max_denomination = 10.0  # Максимальна ставка 10.0
        
        # Bet ranges для кожного режиму (множники від базової ставки)
        self.bet_ranges = {
            "base": {"min_multiplier": 1, "max_multiplier": 100},  # 0.1 - 10.0
            "bonus_hunt": {"min_multiplier": 1, "max_multiplier": 100},  # 0.1 - 5.0
            "Horny_Jail": {"min_multiplier": 1, "max_multiplier": 100},  # 0.1 - 1.0
            "buy_bonk_spins": {"min_multiplier": 1, "max_multiplier": 100},  # 0.1 - 2.0
            "buy_super_bonk_spins": {"min_multiplier": 1, "max_multiplier": 100},  # 0.1 - 1.0
        }
        
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
        
        # Note: reel_strips is deprecated, using self.reels instead
        # All reel configurations are now in self.reels
        
        # Bet modes
        self.bet_modes = [
            BetMode(
                name="base",
                cost=1.0,
                rtp=0.96,
                max_win=1000000.0,  # Максимальний виграш 5000x (обмежує BR0 барабани)
                auto_close_disabled=False,
                is_feature=False,
                is_buybonus=False,
                distributions=[
                    Distribution(
                        criteria="0",
                        quota=1,
                        win_criteria=None,
                        conditions={
                            "reel_weights": {self.basegame_type: {"BR0": 1}, self.freegame_type: {"BR0": 1}},
                            "force_wincap": False,
                            "force_freegame": False,
                        }
                    )
                ]
            ),
            BetMode(
                name="bonus_hunt",
                cost=3.0,
                rtp=0.96,
                max_win=1000000.0,  # Максимальний виграш 1,000,000x (обмежує Bonus_Hunt барабани)
                auto_close_disabled=False,
                is_feature=False,
                is_buybonus=False,
                distributions=[
                    Distribution(
                        criteria="0",
                        quota=1,
                        win_criteria=None,
                        conditions={
                            "reel_weights": {self.basegame_type: {"Bonus_Hunt": 1}},
                            "force_wincap": False,
                            "force_freegame": False,  # НЕ запускати фрігейми
                        }
                    )
                ]
            ),
            BetMode(
                name="Horny_Jail",
                cost=20000.0,  # Вартість 20000
                rtp=0.96,
                max_win=1000000.0,  # Максимальний виграш 1,000,000x (1000 × 1000)
                auto_close_disabled=False,
                is_feature=False,
                is_buybonus=False,
                distributions=[
                    Distribution(
                        criteria="0",
                        quota=1,
                        win_criteria=None,
                        conditions={
                            "reel_weights": {self.basegame_type: {"Horny_Jail": 1}},
                            "force_wincap": False,
                            "force_freegame": False,
                        }
                    )
                ]
            ),


            BetMode(
                name="buy_bonk_spins",
                cost=40.0,
                rtp=0.96,
                max_win=1000000.0,  # Максимальний виграш 1,000,000x (обмежує BON1 барабани)
                auto_close_disabled=False,
                is_feature=True,
                is_buybonus=True,  # Це режим покупки бонусу
                distributions=[
                    Distribution(
                        criteria="buy_bonk_spins",
                        quota=1,
                        win_criteria=None,
                        conditions={
                            "reel_weights": {self.basegame_type: {"BON1": 1}, self.freegame_type: {"BON1": 1}},
                            "force_wincap": False,
                            "force_freegame": True,  # Примусово запускає бонусну гру
                        }
                    )
                ]
            ),
            BetMode(
                name="buy_super_bonk_spins",
                cost=200.0,  # Вища вартість для супер-бонусу
                rtp=0.96,
                max_win=1000000.0,  # Максимальний виграш 1,000,000x (обмежує BON2 барабани)
                auto_close_disabled=False,
                is_feature=True,
                is_buybonus=True,  # Режим покупки бонусу
                distributions=[
                    Distribution(
                        criteria="buy_super_bonk_spins",
                        quota=1,
                        win_criteria=None,
                        conditions={
                            "reel_weights": {self.basegame_type: {"BON2": 1}, self.freegame_type: {"BON2": 1}},
                            "force_wincap": False,
                            "force_freegame": True,  # Примусово запускає бонусну гру
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
        
        # Load all reel data files
        base_reel_path = os.path.join(os.path.dirname(__file__), "reels", "BR0.csv")
        bon1_reel_path = os.path.join(os.path.dirname(__file__), "reels", "BON1.csv")
        bon2_reel_path = os.path.join(os.path.dirname(__file__), "reels", "BON2.csv")
        bon2_run_reel_path = os.path.join(os.path.dirname(__file__), "reels", "BON2_run.csv")
        bon2_stick_reel_path = os.path.join(os.path.dirname(__file__), "reels", "BON2_stick.csv")
        bonus_hunt_reel_path = os.path.join(os.path.dirname(__file__), "reels", "Bonus_Hunt.csv")
        horny_jail_reel_path = os.path.join(os.path.dirname(__file__), "reels", "Horny_Jail.csv")
        
        base_reel_symbols = self.read_single_column_csv(base_reel_path)
        bon1_reel_symbols = self.read_single_column_csv(bon1_reel_path)
        bon2_reel_symbols = self.read_single_column_csv(bon2_reel_path)
        bon2_run_reel_symbols = self.read_single_column_csv(bon2_run_reel_path)
        bon2_stick_reel_symbols = self.read_single_column_csv(bon2_stick_reel_path)
        bonus_hunt_reel_symbols = self.read_single_column_csv(bonus_hunt_reel_path)
        horny_jail_reel_symbols = self.read_single_column_csv(horny_jail_reel_path)
        
        # Create proper reels structure for 2-reel game
        # BR0 for base game (with Bat bonuses)
        self.reels["BR0"] = [base_reel_symbols, base_reel_symbols]  # 2 reels, both using same symbols
        
        # BON1 for first bonus game (used by buy_bonk_spins)
        self.reels["BON1"] = [bon1_reel_symbols, bon1_reel_symbols]  # 2 reels, both using same symbols
        
        # BON2 for second bonus game (used by buy_super_bonk_spins)
        self.reels["BON2"] = [bon2_reel_symbols, bon2_reel_symbols]  # 2 reels, both using same symbols
        
        # BON2_run for non-sticky reels in SUPER_BONK_SPINS (can have Golden Bat)
        self.reels["BON2_run"] = [bon2_run_reel_symbols, bon2_run_reel_symbols]  # 2 reels, both using same symbols
        
        # BON2_stick for sticky reels in SUPER_BONK_SPINS (only numeric symbols, no Golden Bat)
        self.reels["BON2_stick"] = [bon2_stick_reel_symbols, bon2_stick_reel_symbols]  # 2 reels, both using same symbols
        
        # Bonus_Hunt: custom base-like reel set with different distribution
        self.reels["Bonus_Hunt"] = [bonus_hunt_reel_symbols, bonus_hunt_reel_symbols]
        
        # Horny_Jail: special mode — first reel fixed to "1000", second reel spins normally
        self.reels["Horny_Jail"] = [["1000"], horny_jail_reel_symbols]
        
        # Note: free game reels are dynamically selected based on bonus type:
        # - BONK_SPINS uses BON1 reels
        # - SUPER_BONK_SPINS uses BON2 reels
        # - When a reel becomes sticky in SUPER_BONK_SPINS:
        #   * Sticky reel uses BON2_stick (numeric only)
        #   * Non-sticky reel uses BON2_run (can have Golden Bat)
        # This is handled in game_events.py and game_override.py

        # Set up padding reels for standard system - use proper format
        self.padding_reels = {}
        self.padding_reels[self.basegame_type] = [base_reel_symbols, base_reel_symbols]  # 2 reels with BR0
        # Note: freegame_type padding reels are dynamically selected based on bonus type
        
        # Add Horny_Jail padding reels (first reel fixed)
        self.padding_reels["Horny_Jail"] = [["1000"], horny_jail_reel_symbols]

    def validate_bet(self, bet_amount: float, mode_name: str = "base") -> dict:
        """
        Валідує ставку для конкретного режиму гри
        
        Args:
            bet_amount: Розмір ставки
            mode_name: Назва режиму гри
            
        Returns:
            dict: Результат валідації з деталями
        """
        result = {
            "is_valid": False,
            "error_message": "",
            "min_allowed": 0.0,
            "max_allowed": 0.0,
            "suggested_bet": 0.0
        }
        
        # Перевіряємо чи існує режим
        if mode_name not in self.bet_ranges:
            result["error_message"] = f"Невідомий режим гри: {mode_name}"
            return result
        
        # Отримуємо діапазон ставок для режиму
        bet_range = self.bet_ranges[mode_name]
        min_multiplier = bet_range["min_multiplier"]
        max_multiplier = bet_range["max_multiplier"]
        
        # Розраховуємо дозволені ставки
        min_allowed = self.min_denomination * min_multiplier
        max_allowed = self.min_denomination * max_multiplier
        
        result["min_allowed"] = min_allowed
        result["max_allowed"] = max_allowed
        
        # Перевіряємо мінімальну ставку
        if bet_amount < min_allowed:
            result["error_message"] = f"Ставка {bet_amount} занадто мала. Мінімум: {min_allowed}"
            result["suggested_bet"] = min_allowed
            return result
        
        # Перевіряємо максимальну ставку
        if bet_amount > max_allowed:
            result["error_message"] = f"Ставка {bet_amount} занадто велика. Максимум: {max_allowed}"
            result["suggested_bet"] = max_allowed
            return result
        
        # Перевіряємо глобальні обмеження
        if bet_amount < self.min_denomination:
            result["error_message"] = f"Ставка {bet_amount} менша за глобальний мінімум: {self.min_denomination}"
            result["suggested_bet"] = self.min_denomination
            return result
        
        if bet_amount > self.max_denomination:
            result["error_message"] = f"Ставка {bet_amount} більша за глобальний максимум: {self.max_denomination}"
            result["suggested_bet"] = self.max_denomination
            return result
        
        # Ставка валідна
        result["is_valid"] = True
        return result
    
    def get_bet_range(self, mode_name: str = "base") -> dict:
        """
        Повертає діапазон ставок для конкретного режиму
        
        Args:
            mode_name: Назва режиму гри
            
        Returns:
            dict: Діапазон ставок
        """
        if mode_name not in self.bet_ranges:
            return {"min": 0.0, "max": 0.0, "error": f"Невідомий режим: {mode_name}"}
        
        bet_range = self.bet_ranges[mode_name]
        return {
            "min": self.min_denomination * bet_range["min_multiplier"],
            "max": self.min_denomination * bet_range["max_multiplier"],
            "min_multiplier": bet_range["min_multiplier"],
            "max_multiplier": bet_range["max_multiplier"]
        }
    
    def get_all_bet_ranges(self) -> dict:
        """
        Повертає всі діапазони ставок для всіх режимів
        
        Returns:
            dict: Всі діапазони ставок
        """
        all_ranges = {}
        for mode_name in self.bet_ranges:
            all_ranges[mode_name] = self.get_bet_range(mode_name)
        return all_ranges

    def read_single_column_csv(self, file_path):
        """Read single column CSV file (one symbol per line)"""
        symbols = []
        with open(file_path, 'r', encoding='UTF-8') as file:
            for line in file:
                symbol = line.strip()
                if symbol:  # Skip empty lines
                    symbols.append(symbol)
        return symbols
