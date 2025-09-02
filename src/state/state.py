from copy import copy
from abc import ABC, abstractmethod
from warnings import warn
import random

# from src.config.config import BetMode
from src.wins.win_manager import WinManager
from src.calculations.symbol import SymbolStorage
from src.config.output_filenames import OutputFiles
from src.state.books import Book
from src.write_data.write_data import (
    print_recorded_wins,
    make_lookup_tables,
    write_json,
    make_lookup_pay_split,
    write_library_events,
)


class GeneralGameState(ABC):
    """Master gamestate which other classes inherit from."""

    def __init__(self, config):
        self.config = config
        self.output_files = OutputFiles(self.config)
        self.win_manager = WinManager(self.config.basegame_type, self.config.freegame_type)
        self.library = {}
        self.recorded_events = {}
        self.special_symbol_functions = {}
        self.temp_wins = []
        self.create_symbol_map()
        self.assign_special_sym_function()
        self.sim = 0
        self.criteria = ""
        self.book = Book(self.sim, self.criteria)
        self.repeat = True
        self.repeat_count = 0
        self.win_data = {
            "totalWin": 0,
            "wins": [],
        }
        self.reset_seed()
        self.reset_book()
        self.reset_fs_spin()

    def create_symbol_map(self) -> None:
        """Construct all valid symbols from config file (from pay-table and special symbols)."""
        all_symbols_list = set()
        for key, _ in self.config.paytable.items():
            all_symbols_list.add(key[1])

        for key in self.config.special_symbols:
            for sym in self.config.special_symbols[key]:
                all_symbols_list.add(sym)

        all_symbols_list = list(all_symbols_list)
        self.symbol_storage = SymbolStorage(self.config, all_symbols_list)

    @abstractmethod
    def assign_special_sym_function(self):
        """ "Define custom symbol functions in game_override."""
        warn("No special symbol functions are defined")

    def reset_book(self) -> None:
        """Reset global simulation variables."""
        self.temp_wins = []
        self.board = [[[] for _ in range(self.config.num_rows[x])] for x in range(self.config.num_reels)]
        self.top_symbols = None
        self.bottom_symbols = None
        self.book_id = self.sim + 1
        self.book = Book(self.book_id, self.criteria)
        self.win_data = {
            "totalWin": 0,
            "wins": [],
        }
        self.win_manager.reset_end_round_wins()
        self.global_multiplier = 1
        self.final_win = 0
        self.tot_fs = 0
        self.fs = 0
        self.wincap_triggered = False
        self.triggered_freegame = False
        self.gametype = self.config.basegame_type
        self.repeat = False
        self.anticipation = [0] * self.config.num_reels
        
        # Нові змінні для відстеження статистики спінів
        self.total_spins_count = 0  # Загальна кількість спінів (базові + фрі)
        self.freespins_count = 0    # Кількість фріспінів
        self.base_spins_count = 0   # Кількість базових спінів

    def reset_seed(self, sim: int = 0) -> None:
        """Reset rng seed to simulation number for reproducibility."""
        # random.seed(sim + 1)
        self.sim = sim
        self.repeat_count = 0

    def reset_fs_spin(self) -> None:
        """Use if using repeat during freespin games."""
        self.triggered_freegame = True
        self.fs = 0
        self.gametype = self.config.freegame_type
        self.win_manager.reset_spin_win()
    
    def increment_spin_count(self, spin_type: str = "base") -> None:
        """Збільшує лічильник спінів залежно від типу."""
        self.total_spins_count += 1
        if spin_type.lower() == "free" or spin_type.lower() == "freespin":
            self.freespins_count += 1
        else:
            self.base_spins_count += 1
    
    def get_spin_statistics(self) -> dict:
        """Повертає статистику спінів."""
        return {
            "total_spins": self.total_spins_count,
            "base_spins": self.base_spins_count,
            "freespins": self.freespins_count,
            "freespin_percentage": round((self.freespins_count / max(self.total_spins_count, 1)) * 100, 2)
        }

    def get_betmode(self, mode_name) -> object:
        """Return all current betmode information."""
        for betmode in self.config.bet_modes:
            if betmode.get_name() == mode_name:
                return betmode
        print("\nWarning: betmode couldn't be retrieved\n")

    def get_current_betmode(self) -> object:
        """Get current betmode information."""
        for betmode in self.config.bet_modes:
            if betmode.get_name() == self.betmode:
                return betmode

    def get_current_betmode_distributions(self) -> object:
        """Return current betmode criteria information."""
        dist = self.get_current_betmode().get_distributions()
        for c in dist:
            if c._criteria == self.criteria:
                return c
        raise RuntimeError("Could not locate criteria distribution.")

    def get_current_distribution_conditions(self) -> dict:
        """Return requirements for criteria setup/acceptance."""
        for d in self.get_betmode(self.betmode).get_distributions():
            if d._criteria == self.criteria:
                return d._conditions
        return RuntimeError("Could not locate betmode conditions")

    def check_current_repeat_count(self, warn_after_count: int = 1000):
        """Alert user to high repeat count."""
        if self.repeat_count >= warn_after_count and (self.repeat_count % warn_after_count) == 0:
            warn(
                f"\nHigh repeat count:\n Current Count: {self.repeat_count} \n Criteria: {self.criteria} \n Simulation: {self.sim}"
            )

    def record(self, description: dict) -> None:
        """
        Record functions must be used for distribution conditions.
        Freespin triggers are most commonly used, i.e {"kind": X, "symbol": "S", "gametype": "basegame"}
        It is recommended to otherwise record rare events with several keys in order to reduce the overall file-size containing many duplicate ids
        """
        dstr = {}
        for k, v in description.items():
            dstr[str(k)] = str(v)
        self.temp_wins.append(dstr)
        self.temp_wins.append(self.book_id)

    def check_force_keys(self, description) -> None:
        """Check and append unique force-key parameters."""
        current_mode_force_keys = self.get_current_betmode().get_force_keys()  # type:ignore
        for keyValue in description:
            if keyValue[0] not in current_mode_force_keys:
                self.get_current_betmode().add_force_key(keyValue[0])  # type:ignore

    def combine(self, modes, betmode_name) -> None:
        """Retrieve unique force record keys."""
        for modeConfig in modes:
            for betmode in modeConfig:
                if betmode.get_name() == betmode_name:
                    break
            force_keys = betmode.get_force_keys()  # type:ignore
            for key in force_keys:
                if key not in self.get_betmode(betmode_name).get_force_keys():  # type:ignore
                    self.get_betmode(betmode_name).add_force_key(key)  # type:ignore

    def imprint_wins(self) -> None:
        """Record all events to library if criteria conditions are satisfied."""
        for temp_win_index in range(int(len(self.temp_wins) / 2)):
            description = tuple(sorted(self.temp_wins[2 * temp_win_index].items()))
            book_id = self.temp_wins[2 * temp_win_index + 1]
            if description in self.recorded_events and (
                book_id not in self.recorded_events[description]["bookIds"]
            ):
                self.recorded_events[description]["timesTriggered"] += 1
                self.recorded_events[description]["bookIds"] += [book_id]
            elif description not in self.recorded_events:
                self.check_force_keys(description)
                self.recorded_events[description] = {
                    "timesTriggered": 1,
                    "bookIds": [book_id],
                }
        self.temp_wins = []
        self.library[self.sim + 1] = copy(self.book.to_json())
        
        self.win_manager.update_end_round_wins()

    def update_final_win(self) -> None:
        """Separate base and freegame wins, verify the sum of there are equal to the final simulation payout."""
        # CRITICAL: For Horny_Jail mode, preserve the custom final_win set in create_horny_jail_board
        # CRITICAL: For bonus games (base and bonus_hunt with bonuses), preserve final_win set in end_bonus_game
        current_betmode = self.get_current_betmode()
        
        if current_betmode and current_betmode.get_name() == "Horny_Jail":
            # Horny_Jail mode: preserve custom final_win, don't overwrite with win_manager values
            final = self.final_win  # Use existing final_win
            # CRITICAL: For Horny_Jail, basegame_wins and freegame_wins must match payout_multiplier
            # Since Horny_Jail has no free games, all wins are base game wins
            basewin = final  # basegame_wins = final_win (absolute amount)
            freewin = 0.0    # freegame_wins = 0 (no free games)
        elif hasattr(self, 'final_win') and self.final_win > 0:
            # Bonus games mode: preserve final_win set in end_bonus_game
            # BUT: For bonus_hunt mode, we need special handling
            current_betmode = self.get_current_betmode()
            if current_betmode and current_betmode.get_name() == "bonus_hunt":
                # Bonus_hunt mode: use win_manager values directly
                # because final_win might only contain base game win, not total
                basewin = round(min(self.win_manager.basegame_wins, self.config.wincap), 2)
                freewin = round(min(self.win_manager.freegame_wins, self.config.wincap), 2)
                # final = basewin + freewin  # Total from win_manager
                final = round(min(self.win_manager.running_bet_win, self.config.wincap), 2)
                # print(54321, final)
            else:
                # Other bonus games: use final_win as is
                final = self.final_win
                
                # For bonus games, check if we have base game wins from win_manager
                # This handles cases where base game had wins before bonus triggered
                if self.win_manager.basegame_wins > 0:
                    # We have base game wins - use them directly
                    basewin = round(min(self.win_manager.basegame_wins, self.config.wincap), 2)
                    # Free game wins should be the remaining amount
                    freewin = round(min(self.win_manager.freegame_wins, self.config.wincap), 2)
                    
                else:
                    # No base game wins, all wins are free game wins
                    basewin = 0.0
                    freewin = final
        else:
            # Other modes: use normal win_manager calculation
            final = round(min(self.win_manager.running_bet_win, self.config.wincap), 2)
            basewin = round(min(self.win_manager.basegame_wins, self.config.wincap), 2)
            freewin = round(min(self.win_manager.freegame_wins, self.config.wincap), 2)
        
        self.final_win = final
        self.book.payout_multiplier = self.final_win
        self.book.basegame_wins = float(basewin)
        self.book.freegame_wins = float(freewin)
        
        assert min(
            round(self.win_manager.basegame_wins + self.win_manager.freegame_wins, 2),
            self.config.wincap,
        ) == round(
            min(self.win_manager.running_bet_win, self.config.wincap), 2
        ), "Base + Free game payout mismatch!"
        assert min(
            round(self.book.basegame_wins + self.book.freegame_wins, 2),
            self.config.wincap,
        ) == min(
            round(self.book.payout_multiplier, 2), round(self.config.wincap, 2)
        ), "Base + Free game payout mismatch!"

    def check_repeat(self) -> None:
        """Checks if the spin failed a criteria constraint at any point."""
        if self.repeat is False:
            win_criteria = self.get_current_betmode_distributions().get_win_criteria()
            if win_criteria is not None and self.final_win != win_criteria:
                self.repeat = True

            if self.get_current_distribution_conditions()["force_freegame"] and not (self.triggered_freegame):
                self.repeat = True

        self.repeat_count += 1
        self.check_current_repeat_count()

    @abstractmethod
    def run_spin(self, sim):
        """run_spin should be defined in gamestate."""
        print("Base Game is not implemented in this game. Currently passing when calling runSpin.")

    @abstractmethod
    def run_freespin(self):
        """run_freespin trigger function should be defined in gamestate."""
        print("gamestate requires def run_freespin(), currently passing when calling runFreeSpin")

    def run_sims(
        self,
        betmode_copy_list,
        betmode,
        sim_to_criteria,
        total_threads,
        total_repeats,
        num_sims,
        thread_index,
        repeat_count,
        compress=True,
        write_event_list=True,
    ) -> None:
        """Assigns criteria and runs individual simulations. Results are stored in temporary file to be combined when all threads are finished."""
        self.win_manager = WinManager(self.config.basegame_type, self.config.freegame_type)
        self.library = {}
        self.betmode = betmode
        self.num_sims = num_sims
        for sim in range(
            thread_index * num_sims + (total_threads * num_sims) * repeat_count,
            (thread_index + 1) * num_sims + (total_threads * num_sims) * repeat_count,
        ):
            self.criteria = sim_to_criteria[sim]
            self.run_spin(sim)
        
        mode_cost = self.get_current_betmode().get_cost()
        betmode_name = self.get_current_betmode().get_name()

        # Avoid division by zero
        if mode_cost <= 0:
            print(f"Warning: mode_cost is {mode_cost}, cannot calculate RTP")
            rtp = 0.0
            base_rtp = 0.0
            free_rtp = 0.0
        else:
            # Різні формули RTP для різних режимів
            if betmode_name == "Horny_Jail":
                # Для Horny_Jail: total_cumulative_wins вже в multiplier units, тому ділимо тільки на num_sims
                rtp = round(self.win_manager.total_cumulative_wins / num_sims, 3)
                base_rtp = round(self.win_manager.cumulative_base_wins / num_sims, 3)
                free_rtp = round(self.win_manager.cumulative_free_wins / num_sims, 3)

            elif betmode_name == "bonus_hunt":
                # Для Bonus_Hunt: total_cumulative_wins вже в multiplier units, тому ділимо тільки на num_sims
                rtp = round((self.win_manager.total_cumulative_wins) / (num_sims * mode_cost), 3)
                base_rtp = round((self.win_manager.cumulative_base_wins) / (num_sims * mode_cost), 3)
                free_rtp = round((self.win_manager.cumulative_free_wins) / (num_sims * mode_cost), 3)
            elif betmode_name == "buy_bonk_spins":
                # Для режимів buy bonus: total_cumulative_wins - це сума всіх виграшів за всі симуляції
                # cost - це вартість за весь пакет (10 bonus spins)
                # RTP = (сума всіх виграшів) / (mode_cost × num_sims)
                rtp = round(self.win_manager.total_cumulative_wins / (num_sims * mode_cost), 3)
                base_rtp = round((self.win_manager.cumulative_base_wins) / (num_sims * mode_cost), 3)
                free_rtp = round((self.win_manager.cumulative_free_wins) / (num_sims * mode_cost), 3)
                
            elif betmode_name == "buy_super_bonk_spins":
                # Для режимів buy bonus: total_cumulative_wins - це сума всіх виграшів за всі симуляції
                # cost - це вартість за весь пакет (10 bonus spins)
                # RTP = (сума всіх виграшів) / (mode_cost × num_sims)
                rtp = round((self.win_manager.total_cumulative_wins) / (num_sims * mode_cost), 3)
                base_rtp = round((self.win_manager.cumulative_base_wins) / (num_sims * mode_cost), 3)
                free_rtp = round((self.win_manager.cumulative_free_wins) / (num_sims * mode_cost), 3)
            else:
                # Для всіх інших режимів: загальний виграш / (кількість симуляцій × cost)
                rtp = round(self.win_manager.total_cumulative_wins / num_sims, 3)
                base_rtp = round(self.win_manager.cumulative_base_wins / (num_sims * mode_cost), 3)
                free_rtp = round(self.win_manager.cumulative_free_wins / (num_sims * mode_cost), 3)
                if free_rtp > 0:
                    print(self.win_manager.cumulative_base_wins)
                    print(self.win_manager.cumulative_free_wins)
                    print(num_sims)
                    print(mode_cost)
                 

        # Показуємо, яка формула RTP використовувалася
        if betmode_name == "Horny_Jail" or betmode_name == "bonus_hunt" or betmode_name == "base":
            rtp_formula = "multiplier_units/num_sims"
        elif betmode_name in ["buy_bonk_spins", "buy_super_bonk_spins"]:
            rtp_formula = f"total_wins/({num_sims}×{mode_cost})"
        else:
            rtp_formula = f"total_wins/({num_sims}×{mode_cost})"
        
        # Отримуємо статистику спінів
        spin_stats = self.get_spin_statistics()
        
        print(
            "Thread " + str(thread_index),
            f"finished with {rtp} RTP for {betmode_name} mode",
            f"[baseGame: {base_rtp}, freeGame: {free_rtp}]",
            f"Formula: {rtp_formula}",
            f"Spins: {spin_stats['total_spins']} (Base: {spin_stats['base_spins']}, Free: {spin_stats['freespins']}, {spin_stats['freespin_percentage']}%)",
            flush=True,
        )

        write_json(
            self,
            self.output_files.get_temp_multi_thread_name(
                betmode, thread_index, repeat_count, (compress) * True + (not compress) * False
            ),
        )
        print_recorded_wins(self, self.output_files.get_temp_force_name(betmode, thread_index, repeat_count))
        make_lookup_tables(self, self.output_files.get_temp_lookup_name(betmode, thread_index, repeat_count))
        make_lookup_pay_split(self, self.output_files.get_temp_segmented_name(betmode, thread_index, repeat_count))

        if write_event_list:
            write_library_events(self, list(self.library.values()), betmode)
        betmode_copy_list.append(self.config.bet_modes)
