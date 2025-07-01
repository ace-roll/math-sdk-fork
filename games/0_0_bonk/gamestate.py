"""Game logic and event emission for Bonk Boi multiplier game."""

from game_override import GameStateOverride


class GameState(GameStateOverride):
    """Handle basegame and freegame logic for Bonk Boi."""

    def run_spin(self, sim: int) -> None:
        """Run a single spin for Bonk Boi game."""
        self.reset_seed(sim)
        self.repeat = True
        while self.repeat:
            self.reset_book()
            
            # Draw board (spin the reels)
            self.draw_board(emit_event=True)
            
            # Calculate win based on symbols
            # Get symbol names from Symbol objects
            symbol1 = self.board[0][0].name if hasattr(self.board[0][0], 'name') else str(self.board[0][0])
            symbol2 = self.board[1][0].name if hasattr(self.board[1][0], 'name') else str(self.board[1][0])
            symbols = [symbol1, symbol2]
            win, bonus = self.calculate_spin_result(symbols)
            
            # Apply win
            if win > 0:
                self.win_manager.update_spinwin(win)
            
            # Update gametype wins
            self.win_manager.update_gametype_wins(self.gametype)
            
            # Update final win
            self.evaluate_finalwin()
            
            # Check repeat conditions
            self.check_repeat()
        
        self.imprint_wins()

    def run_freespin(self) -> None:
        """Run freespin for Bonk Boi game (not used in this simple game)."""
        self.reset_fs_spin()
        while self.fs < self.tot_fs:
            self.update_freespin()
            self.draw_board(emit_event=True)
            
            # Calculate win for freespin
            symbol1 = self.board[0][0].name if hasattr(self.board[0][0], 'name') else str(self.board[0][0])
            symbol2 = self.board[1][0].name if hasattr(self.board[1][0], 'name') else str(self.board[1][0])
            symbols = [symbol1, symbol2]
            win, bonus = self.calculate_spin_result(symbols)
            
            if win > 0:
                self.win_manager.update_spinwin(win)
            
            self.win_manager.update_gametype_wins(self.gametype)
        
        self.end_freespin()

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
