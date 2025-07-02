"""Game logic and event emission for Bonk Boi multiplier game with bonus games."""

from game_override import GameStateOverride
from game_calculations import GameCalculations
from game_events import BonkBoiEvents, reveal_event_bonk_boi


class GameState(GameStateOverride):
    """Handle basegame and bonus game logic for Bonk Boi."""

    def __init__(self, config):
        super().__init__(config)
        self.calculations = GameCalculations(config)
        self.events = BonkBoiEvents(self.calculations)
        self.bonus_game_active = False
        self.bonus_spins_completed = 0
        self.total_bonus_win = 0
        self.bonus_session_id = None

    def run_spin(self, sim: int) -> None:
        """Run a single spin for Bonk Boi game."""
        self.reset_seed(sim)
        self.repeat = True
        while self.repeat:
            self.reset_book()
            
            # Create board without emitting standard reveal event
            self.create_board_reelstrips()
            
            # Use custom reveal event for Bonk Boi
            reveal_event_bonk_boi(self)
            
            # Get symbols from board
            reels = self.get_board_symbols()
            
            # Process the spin through events
            if self.events.bonus_mode or self.events.super_bonus_mode:
                result, bonus = self.events.process_bonus_spin(reels)
                self.bonus_game_active = True
                self.bonus_spins_completed += 1
                self.total_bonus_win += result
                # Бонусна гра = freegame
                self.gametype = self.config.freegame_type
                
                # Add bonus spin event to book
                self.add_bonus_spin_event(reels, result, bonus)
            else:
                result, bonus = self.events.process_spin(reels)
                # Base game
                self.gametype = self.config.basegame_type
            
            # Apply win cap - обмежуємо виграш до максимального значення
            if result > self.config.wincap:
                result = self.config.wincap
            
            # Convert result to proper format (fraction, not cents)
            # Since our game uses multiplier values (1, 2, 3, etc.), 
            # we need to convert to bet multiplier (result / bet_amount)
            bet_amount = self.get_current_betmode().get_cost()
            result_multiplier = result / bet_amount if bet_amount > 0 else 0
            
            # Update win data with proper format
            self.win_data = {"totalWin": result_multiplier}
            self.win_manager.update_spinwin(result_multiplier)
            self.win_manager.update_gametype_wins(self.gametype)
            
            # Handle bonus if triggered
            if bonus:
                self.events.trigger_bonus(bonus)
                # Add bonus event to book
                self.add_bonus_event(bonus)
            
            # Check if bonus game is complete
            if self.bonus_game_active and self.events.is_bonus_complete():
                self.end_bonus_game()
            
            # This is crucial - it sets the payoutMultiplier in the book
            self.evaluate_finalwin()
            
            self.repeat = False
        
        self.check_repeat()
        self.imprint_wins()

    def get_board_symbols(self):
        """Get symbols from the drawn board (robust for both object and string)"""
        reels = []
        for reel_idx in range(self.config.num_reels):
            symbol_obj = self.board[reel_idx][0]
            symbol = symbol_obj.name if hasattr(symbol_obj, 'name') else symbol_obj
            reels.append(symbol)
        return reels

    def add_bonus_event(self, bonus_type):
        """Add bonus trigger event to the book"""
        # Generate unique bonus session ID
        if not self.bonus_session_id:
            self.bonus_session_id = f"bonus_{len(self.book.events)}_{self.events.current_reel_set}"
        
        event = {
            "index": len(self.book.events),
            "type": "BONUS_TRIGGER",
            "bonusType": bonus_type,
            "gameType": self.gametype,
            "bonusSessionId": self.bonus_session_id,
            "reelSet": self.events.current_reel_set,
            "triggerSymbols": self.get_board_symbols()
        }
        self.book.add_event(event)

    def add_bonus_spin_event(self, reels, win, bonus):
        """Add individual bonus spin event to the book"""
        if not self.bonus_session_id:
            return
        
        event = {
            "index": len(self.book.events),
            "type": "BONUS_SPIN",
            "bonusSessionId": self.bonus_session_id,
            "spinNumber": self.bonus_spins_completed,
            "reels": reels,
            "win": win,
            "bonusTriggered": bonus,
            "gameType": self.gametype,
            "reelSet": self.events.current_reel_set,
            "bonusState": {
                "type": self.events.bonus_state.get("type") if self.events.bonus_state else None,
                "spinsLeft": self.events.bonus_state.get("spins_left") if self.events.bonus_state else 0,
                "multiplier": self.events.bonus_state.get("multiplier") if self.events.bonus_state else 1,
                "totalWin": self.events.bonus_state.get("total_win") if self.events.bonus_state else 0,
                "symbolsCollected": len(self.events.bonus_state.get("symbols_collected", [])) if self.events.bonus_state else 0
            }
        }
        self.book.add_event(event)

    def end_bonus_game(self):
        """End bonus game and add summary event. Виграш бонусу також множник."""
        if self.events.bonus_state:
            summary = self.events.get_bonus_summary()
            bet_amount = self.get_current_betmode().get_cost()
            bonus_win_multiplier = summary["total_win"] / bet_amount if bet_amount > 0 else 0
            
            event = {
                "index": len(self.book.events),
                "type": "BONUS_COMPLETE",
                "bonusType": summary["type"],
                "bonusSessionId": self.bonus_session_id,
                "totalWin": bonus_win_multiplier,
                "finalMultiplier": summary["final_multiplier"],
                "symbolsCollected": len(summary["symbols_collected"]),
                "spinsPlayed": self.bonus_spins_completed,
                "gameType": self.gametype,
                "reelSet": self.events.current_reel_set,
                "bonusDetails": {
                    "totalSymbolsCollected": len(summary["symbols_collected"]),
                    "batSymbols": summary["symbols_collected"].count("Bat"),
                    "goldenBatSymbols": summary["symbols_collected"].count("Golden Bat"),
                    "regularSymbols": len([s for s in summary["symbols_collected"] if s not in ["Bat", "Golden Bat"]]),
                    "averageWinPerSpin": bonus_win_multiplier / self.bonus_spins_completed if self.bonus_spins_completed > 0 else 0
                }
            }
            self.book.add_event(event)
        
        # Reset bonus state and return to base game
        self.bonus_game_active = False
        self.bonus_spins_completed = 0
        self.total_bonus_win = 0
        self.bonus_session_id = None
        self.events.reset_to_base_game()  # Reset to BR0 reels

    def draw_board(self, emit_event: bool = True) -> None:
        """Override draw_board to use custom reveal event for Bonk Boi."""
        # Use parent method to create the board without emitting event
        super().draw_board(emit_event=False)
        
        # Use custom reveal event for Bonk Boi
        if emit_event:
            reveal_event_bonk_boi(self)

    def run_freespin(self):
        """Run freespin for Bonk Boi game (not used in this game with bonus games)."""
        self.reset_fs_spin()
        while self.fs < self.tot_fs:
            self.update_freespin()
            pass
        self.end_freespin()

    def get_bonus_statistics(self):
        """Get bonus game statistics for analysis"""
        return {
            "bonus_games_triggered": self.events.bonus_mode or self.events.super_bonus_mode,
            "bonus_spins_completed": self.bonus_spins_completed,
            "total_bonus_win": self.total_bonus_win,
            "bonus_state": self.events.bonus_state,
            "current_reel_set": self.events.current_reel_set,
            "bonus_session_id": self.bonus_session_id
        }
