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
        self.bonus_spins_left = 0  # Add missing attribute
        self.needs_upgrade_bonus_trigger = False  # Track if we need to create upgrade BONUS_TRIGGER
        self.upgrade_bonus_trigger_created = False  # Track if upgrade BONUS_TRIGGER was already created

    def run_spin(self, sim: int) -> None:
        """Run a single spin for Bonk Boi game."""
        self.reset_seed(sim)
        self.repeat = True
        while self.repeat:
            self.reset_book()
            
            # Create board without emitting standard reveal event
            self.create_board_reelstrips()
            
            # Get symbols from board
            reels = self.get_board_symbols()
            
            # Check if this is a buy bonus mode
            current_betmode = self.get_current_betmode()
            is_buy_bonus = current_betmode and current_betmode.get_buybonus()
            
            # Debug logging
            print(f"DEBUG: gamestate.py - self.betmode: {self.betmode}")
            print(f"DEBUG: gamestate.py - current_betmode: {current_betmode}")
            if current_betmode:
                print(f"DEBUG: Bet mode: {current_betmode.get_name()}, is_buybonus: {current_betmode.get_buybonus()}")
            else:
                print(f"DEBUG: current_betmode is None!")
            
            if is_buy_bonus:
                print(f"DEBUG: Running in buy bonus mode")
                
                # Check which type of buy bonus mode
                betmode_name = current_betmode.get_name()
                is_super_bonk = betmode_name == "buy_super_bonk_spins"
                
                # First reveal event - base game with Bat symbols
                self.gametype = self.config.basegame_type
                self.create_board_reelstrips()
                
                # Force the first reveal to show ["Bat", "1"] for buy bonus mode
                # Create a custom board with Bat and 1 symbols using simple dict format
                custom_board = []
                for symbol_name in ["Bat", "1"]:
                    # Create a simple symbol object with name attribute
                    symbol_obj = type('Symbol', (), {'name': symbol_name})()
                    custom_board.append([symbol_obj])
                self.board = custom_board
                
                reveal_event_bonk_boi(self)
                
                # Buy bonus mode - automatically trigger appropriate bonus type
                if is_super_bonk:
                    bonus_type = "SUPER_BONK_SPINS"
                    spins_count = 10  # SUPER_BONK_SPINS має 10 спінів
                    reel_set = "BON2"
                else:
                    bonus_type = "BONK_SPINS"
                    spins_count = 10
                    reel_set = "BON1"
                
                self.events.trigger_bonus(bonus_type, spins_count)
                self.add_bonus_event(bonus_type)
                
                # For buy bonus mode, use appropriate reels
                self.events.current_reel_set = reel_set
                
                # Initialize bonus state for the new bonus round
                if self.events.super_bonus_mode:
                    self.events.bonus_state = {
                        "type": "SUPER_BONK_SPINS",
                        "spins_left": spins_count,  # Use spins_count instead of bonus_spins_left
                        "total_win": 0,
                        "symbols_collected": [],
                        "multiplier": 2,
                        "sticky_value": None,
                        "sticky_reel": None
                    }
                else:
                    self.events.bonus_state = {
                        "type": "BONK_SPINS",
                        "spins_left": spins_count,  # Use spins_count instead of bonus_spins_left
                        "total_win": 0,
                        "symbols_collected": [],
                        "multiplier": 1,
                        "upgrade_to_super": False
                    }
                
                # Run all bonus spins until completion
                print(f"DEBUG: Before bonus loop - bonus_mode: {self.events.bonus_mode}, super_bonus_mode: {self.events.super_bonus_mode}, is_bonus_complete: {self.events.is_bonus_complete()}")
                print(f"DEBUG: Bonus state: {self.events.bonus_state}")
                
                while (self.events.bonus_mode or self.events.super_bonus_mode) and not self.events.is_bonus_complete():
                    print(f"DEBUG: Inside bonus loop - spin {self.bonus_spins_completed + 1}")
                    
                    # Use appropriate reels for buy bonus mode
                    # Temporarily set gametype to base to create board, then change to free for events
                    self.gametype = self.config.basegame_type
                    
                    # Create new board for each bonus spin
                    self.create_board_reelstrips()
                    
                    # Change gametype to free for bonus spin events
                    self.gametype = self.config.freegame_type
                    
                    # Use custom reveal event for Bonk Boi
                    reveal_event_bonk_boi(self)
                    
                    # Get symbols from board
                    reels = self.get_board_symbols()
                    print(f"DEBUG: Board symbols: {reels}")
                    
                    # Process the bonus spin using base game logic (multiply two symbols)
                    if is_super_bonk:
                        # For SUPER_BONK_SPINS, use sticky logic from bonus_state
                        result = 0  # Will be calculated by process_super_bonk_spin
                    else:
                        # For BONK_SPINS, use regular calculation
                        result = self.events.calculate_bonus_spin_win(reels)
                    print(f"DEBUG: Spin result: {result}")
                    
                    # Handle bonus symbols for extra spins (ONLY for upgrade logic, not for adding spins)
                    for symbol in reels:
                        if symbol == "Golden Bat":
                            # Golden Bat in Bonk Spins upgrades to Super Bonk Spins
                            if self.events.bonus_mode and not self.events.super_bonus_mode:
                                print(f"DEBUG: Upgrading from BONK_SPINS to SUPER_BONK_SPINS in gamestate!")
                                self.events.bonus_mode = False
                                self.events.super_bonus_mode = True
                                # Update bonus state - sync with process_bonk_spin
                                if self.events.bonus_state:
                                    self.events.bonus_state["type"] = "SUPER_BONK_SPINS"
                                    self.events.bonus_state["multiplier"] = 4  # SUPER_BONK_SPINS has 4x multiplier
                                    self.events.bonus_state["upgraded_from_bonk"] = True
                    
                    # Note: Extra spins are now handled ONLY in process_bonus_spin_logic to avoid duplication
                    
                    # Apply sticky multiplier for SUPER_BONK_SPINS
                    if is_super_bonk:
                        # SUPER_BONK_SPINS uses sticky logic, result will be set by process_super_bonk_spin
                        print(f"DEBUG: SUPER_BONK_SPINS sticky mode - result will be calculated by sticky logic")
                    else:
                        # Regular BONK_SPINS logic
                        pass
                    
                    self.bonus_game_active = True
                    self.bonus_spins_completed += 1
                    print(f"DEBUG: After spin - completed: {self.bonus_spins_completed}, total_win (pre-update): {self.total_bonus_win}")
                    
                    # Update bonus state for buy bonus mode
                    if self.events.bonus_state:
                        # Update total_win in bonus_state before processing
                        self.events.bonus_state["total_win"] = self.total_bonus_win
                        
                        # Use process_bonus_spin_logic to handle bonus spin logic (including sticky for SUPER_BONK_SPINS)
                        bonus_type = self.events.bonus_state["type"]
                        print(f"DEBUG: gamestate.py - BEFORE process_bonus_spin_logic - bonus_type: {bonus_type}, total_win: {self.events.bonus_state['total_win']}")
                        
                        self.events.bonus_state = self.events.process_bonus_spin_logic(self.events.bonus_state, reels, bonus_type)
                        
                        print(f"DEBUG: gamestate.py - AFTER process_bonus_spin_logic - bonus_type: {self.events.bonus_state['type']}, total_win: {self.events.bonus_state['total_win']}")
                        
                        # Get current spin win from bonus_state for BOTH modes and accumulate once
                        current_spin_win = self.events.bonus_state.get("current_spin_win")
                        if current_spin_win is None:
                            prev_total = self.total_bonus_win
                            new_total = self.events.bonus_state.get("total_win", 0)
                            current_spin_win = max(0, new_total - prev_total)
                        result = current_spin_win
                        self.total_bonus_win += current_spin_win
                        print(f"DEBUG: current_spin_win: {current_spin_win}, accumulated total_bonus_win: {self.total_bonus_win}")
                        
                        # CRITICAL: Always sync bonus_state["total_win"] with self.total_bonus_win
                        old_bonus_state_total_win = self.events.bonus_state["total_win"]
                        self.events.bonus_state["total_win"] = self.total_bonus_win
                        print(f"DEBUG: Synced bonus_state[\"total_win\"]: {old_bonus_state_total_win} -> {self.total_bonus_win}")
                        
                        # Check if bonus type was upgraded (only on the FIRST upgrade)
                        if (self.events.bonus_state["type"] == "SUPER_BONK_SPINS" and 
                            self.events.bonus_state.get("upgraded_from_bonk", False) and 
                            not self.upgrade_bonus_trigger_created):
                            
                            # Switch to BON2 reels for upgraded bonus
                            self.events.current_reel_set = "BON2"
                            print(f"DEBUG: Switched to BON2 reels after upgrade to SUPER_BONK_SPINS")
                            
                            # CRITICAL: Update is_super_bonk to True after upgrade
                            is_super_bonk = True
                            print(f"DEBUG: Updated is_super_bonk to True after upgrade!")
                            
                            # CRITICAL: Sync total_bonus_win with bonus_state["total_win"] after upgrade
                            self.total_bonus_win = self.events.bonus_state["total_win"]
                            print(f"DEBUG: Synced total_bonus_win with bonus_state after upgrade: {self.total_bonus_win}")
                            
                            # CRITICAL: Mark that we need to create BONUS_TRIGGER event after BONUS_SPIN
                            print(f"DEBUG: Marked for BONUS_TRIGGER event creation after BONUS_SPIN")
                            # We'll create the BONUS_TRIGGER event after add_bonus_spin_event
                            self.needs_upgrade_bonus_trigger = True
                            
                            # Mark that we've already created the upgrade BONUS_TRIGGER
                            self.upgrade_bonus_trigger_created = True
                        
                        # Update total_win in bonus_state after processing
                        self.events.bonus_state["total_win"] = self.total_bonus_win
                        
                        print(f"DEBUG: Updated bonus state - total_win: {self.events.bonus_state['total_win']}, spins_left: {self.events.bonus_state['spins_left']}")
                    
                    # Add bonus spin event to book
                    print(f"DEBUG: gamestate.py - About to call add_bonus_spin_event with result: {result}, bonus_type: {bonus_type}")
                    self.add_bonus_spin_event(reels, result, bonus_type)
                    
                    # Check if we need to create BONUS_TRIGGER event for upgrade
                    if self.needs_upgrade_bonus_trigger:
                        print(f"DEBUG: Creating BONUS_TRIGGER event for upgrade after BONUS_SPIN")
                        # Create upgrade BONUS_TRIGGER event
                        self.events.create_bonus_trigger_event(
                            self,
                            "SUPER_BONK_SPINS",  # bonus_type for upgrade
                            reels,  # Use current board symbols as trigger symbols
                            0,  # trigger_win = 0 for upgrade
                            5   # spins_received = 5 for Golden Bat upgrade
                        )
                        print(f"DEBUG: Created BONUS_TRIGGER event for upgrade")
                        # Reset the flag
                        self.needs_upgrade_bonus_trigger = False
                
                # End bonus game and add summary
                # Save the total bonus win before ending the game (since end_bonus_game resets it to 0)
                total_bonus_win = self.total_bonus_win
                self.end_bonus_game()
                
                # For buy bonus mode, payoutMultiplier should be the total bonus win amount
                # Not the multiplier ratio
                print(f"DEBUG: Total bonus win: {total_bonus_win}")
                
                # Reset win manager for this spin
                self.win_manager.reset_spin_win()
                
                # Update win manager with total bonus win
                self.win_manager.update_spinwin(total_bonus_win)
                self.win_manager.update_gametype_wins(self.config.freegame_type)  # Bonus spins are free game
                
                print(f"DEBUG: After update - running_bet_win: {self.win_manager.running_bet_win}, basegame_wins: {self.win_manager.basegame_wins}, freegame_wins: {self.win_manager.freegame_wins}")
                
                # Set the final result for the spin - this should be the total win amount
                self.result = total_bonus_win
                
                # Set gametype to free for buy bonus mode (since it's all bonus spins)
                self.gametype = self.config.freegame_type
                
                # Ensure win_manager has the correct values for final calculation
                self.win_manager.running_bet_win = total_bonus_win
                
                # Also update the win_data to ensure proper final calculation
                self.win_data = {"totalWin": total_bonus_win}
                
                print(f"DEBUG: Final values - running_bet_win: {self.win_manager.running_bet_win}, totalWin: {self.win_data['totalWin']}")
                
                # Evaluate final win immediately for buy bonus mode to set payoutMultiplier
                self.evaluate_finalwin()
            else:
                # Normal base game - use custom reveal event for Bonk Boi
                reveal_event_bonk_boi(self)
                
                # Get symbols from the NEW board (after reveal_event_bonk_boi)
                reels = self.get_board_symbols()
                
                # Process base game spin using original logic
                print(f"DEBUG: gamestate.py - About to call process_spin with reels: {reels}")
                result, bonus_type = self.events.process_spin(reels)
                print(f"DEBUG: gamestate.py - process_spin returned: result={result}, bonus_type={bonus_type}")
                self.result = result
                
                # Check for bonus symbols in base game (Bat or Golden Bat)
                bonus_count = sum(1 for symbol in reels if symbol == "Bat")
                super_bonus_count = sum(1 for symbol in reels if symbol == "Golden Bat")
                
                # Handle bonus if triggered by bonus symbols
                if bonus_count > 0 or super_bonus_count > 0:
                    if super_bonus_count > 0:
                        # Super Bonus symbols trigger SUPER_BONK_SPINS
                        spins_count = 13 if super_bonus_count == 2 else 10
                        bonus_type = "SUPER_BONK_SPINS"
                    else:
                        # Regular Bonus symbols trigger BONK_SPINS
                        spins_count = 15 if bonus_count == 2 else 10
                        bonus_type = "BONK_SPINS"
                    
                    # Trigger bonus
                    self.events.trigger_bonus(bonus_type, spins_count)
                    # Add bonus event to book
                    self.add_bonus_event(bonus_type)
                
                # Convert result to proper format (fraction, not cents)
                # Since our game uses multiplier values (1, 2, 3, etc.),
                # we need to convert to bet multiplier (result / bet_amount)
                bet_amount = self.get_current_betmode().get_cost()
                result_multiplier = result / bet_amount if bet_amount > 0 else 0
                
                print(f"DEBUG: gamestate.py - result: {result}, bet_amount: {bet_amount}, result_multiplier: {result_multiplier}")
                print(f"DEBUG: gamestate.py - BEFORE update_spinwin - running_bet_win: {self.win_manager.running_bet_win}")
                
                # Apply win cap for base game
                if result_multiplier > self.config.wincap:
                    result_multiplier = self.config.wincap
                
                # This is crucial - it sets the payoutMultiplier in the book
                self.win_manager.update_spinwin(result_multiplier)
                self.win_manager.update_gametype_wins(self.gametype)
                
                print(f"DEBUG: gamestate.py - AFTER update_spinwin - running_bet_win: {self.win_manager.running_bet_win}")
                
                # Also update the win_data to ensure proper final calculation
                self.win_data = {"totalWin": result_multiplier}
            
            # This is crucial - it sets the payoutMultiplier in the book
            # Note: evaluate_finalwin() is now called inside buy bonus block
            if not (current_betmode and current_betmode.get_buybonus()):
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
            self.bonus_session_id = f"bonus_{len(self.book.events)}_{bonus_type}"

        # Get trigger symbols from current board
        trigger_symbols = self.get_board_symbols()

        # For buy bonus mode, use appropriate trigger symbols based on bonus type
        current_betmode = self.get_current_betmode()
        if current_betmode and current_betmode.get_buybonus():
            if bonus_type == "SUPER_BONK_SPINS":
                # For SUPER_BONK_SPINS, use Golden Bat + 1
                trigger_symbols = ["Golden Bat", "1"]
            else:
                # For BONK_SPINS, use Bat + 1
                trigger_symbols = ["Bat", "1"]

        # Determine number of spins based on bonus type
        if bonus_type == "SUPER_BONK_SPINS":
            # Check if this is an upgrade from BONK_SPINS
            if self.events.bonus_state and self.events.bonus_state["type"] == "BONK_SPINS":
                spins_received = self.events.bonus_state["spins_left"] + 5  # Upgrade with +5
            else:
                # Check trigger symbols for number of Super Bonus symbols
                super_bonus_count = sum(1 for symbol in trigger_symbols if symbol == "Golden Bat")
                if super_bonus_count == 2:
                    spins_received = 13  # 2 Super Bonus symbols = 13 spins
                else:
                    spins_received = 10  # 1 Super Bonus symbol = 10 spins
        else:  # BONK_SPINS
            # Check trigger symbols for number of Bonus symbols
            bonus_count = sum(1 for symbol in trigger_symbols if symbol == "Bat")
            if bonus_count == 2:
                spins_received = 15  # 2 Bonus symbols = 15 spins
            else:
                spins_received = 10  # 1 Bonus symbol = 10 spins

        # Create bonus trigger event using new method
        self.events.create_bonus_trigger_event(
            self,
            bonus_type,
            trigger_symbols,
            0,  # trigger_win = 0 for buy bonus
            spins_received
        )

        # Update bonus session ID in events
        self.events.bonus_session_id = self.bonus_session_id

    def add_bonus_spin_event(self, reels, win, bonus_type):
        """Add individual bonus spin event to book"""
        if not self.bonus_session_id or not self.events.bonus_state:
            return

        # Get current bonus state
        bonus_state = self.events.bonus_state
        bonus_type = bonus_state["type"]
        
        # Determine spins_received for THIS specific spin (ONLY extra spins from Bat/Golden Bat in THIS spin)
        spins_received = 0  # Default: no extra spins in this spin
        
        # Check if THIS spin has Bat or Golden Bat symbols
        for symbol in reels:
            if bonus_type == "SUPER_BONK_SPINS" and symbol == "Golden Bat":
                spins_received += 5  # Golden Bat gives 5 extra spins
            elif bonus_type == "BONK_SPINS" and symbol == "Bat":
                spins_received += 5  # Bat gives 5 extra spins
            
        spins_left = bonus_state["spins_left"]
        # Use self.total_bonus_win instead of bonus_state["total_win"] for proper updates
        total_bonus_win = self.total_bonus_win
        print(f"DEBUG: add_bonus_spin_event - bonus_state[\"total_win\"]: {bonus_state['total_win']}, self.total_bonus_win: {self.total_bonus_win}")

        # Create bonus spin event using new method
        print(f"DEBUG: add_bonus_spin_event - creating event with spin_win: {win}, total_bonus_win: {total_bonus_win}, spins_received: {spins_received}")
        
        bonus_spin_event = self.events.create_bonus_spin_event(
            self,
            self.bonus_spins_completed,
            self.bonus_session_id,
            self.events.current_reel_set,
            win,
            total_bonus_win,
            spins_received,  # Pass actual spins received for this spin
            spins_left
        )
        
        # Add the bonus spin event to the book
        if bonus_spin_event:
            self.book.add_event(bonus_spin_event)

        # Update bonus session ID in events
        self.events.bonus_session_id = self.bonus_session_id

    def end_bonus_game(self):
        """End bonus game and add summary event. Виграш бонусу також множник."""
        if self.events.bonus_state:
            summary = self.events.get_bonus_summary()
            
            # Determine final multiplier based on bonus type
            bonus_type = summary["type"]
            if bonus_type == "SUPER_BONK_SPINS":
                final_multiplier = 4  # SUPER_BONK_SPINS має множник x4
            else:  # BONK_SPINS
                final_multiplier = 2  # Звичайний BONK_SPINS має множник x2
            
            print(f"DEBUG: end_bonus_game - bonus_type: {bonus_type}, final_multiplier: {final_multiplier}, summary[\"total_win\"]: {summary['total_win']}")

            # Create bonus complete event using new method
            self.events.create_bonus_complete_event(
                self,
                self.bonus_session_id,
                summary["total_win"],
                self.bonus_spins_completed,
                summary["type"],
                final_multiplier
            )

        # Reset bonus state and return to base game
        self.bonus_game_active = False
        self.bonus_spins_completed = 0
        self.total_bonus_win = 0
        self.bonus_session_id = None
        self.events.reset_to_base_game()  # Reset to BR0 reels

        # Update bonus session ID in events
        self.events.bonus_session_id = None

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
