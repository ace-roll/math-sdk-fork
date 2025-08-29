"""Game logic and event emission for Bonk Boi multiplier game with bonus games."""

from operator import rshift
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
        self.upgrade_trigger_symbols = None  # Store symbols that triggered the upgrade

    def run_spin(self, sim: int) -> None:
        """Run a single spin for Bonk Boi game."""
        self.reset_seed(sim)
        self.repeat = True
        while self.repeat:
            self.reset_book()
            
            # Check if this is Horny_Jail or Bonus_Hunt mode
            current_betmode = self.get_current_betmode()
            if current_betmode and current_betmode.get_name() == "Horny_Jail":
                self.events.current_reel_set = "Horny_Jail"
            elif current_betmode and current_betmode.get_name() == "bonus_hunt":
                self.events.current_reel_set = "Bonus_Hunt"
            
            # Create board without emitting standard reveal event
            self.create_board_reelstrips()
            
            # Get symbols from board
            reels = self.get_board_symbols()
            
            # Check if this is a buy bonus mode
            current_betmode = self.get_current_betmode()
            is_buy_bonus = current_betmode and current_betmode.get_buybonus()
            
            if is_buy_bonus:
                
                # Check which type of buy bonus mode
                betmode_name = current_betmode.get_name()
                is_super_bonk = betmode_name == "buy_super_bonk_spins"
                
                # First reveal event - custom board for buy bonus mode
                self.gametype = self.config.basegame_type
                
                # CRITICAL: Remove any existing reveal events from previous modes (like Horny_Jail)
                if hasattr(self, 'book') and self.book.events:
                    # Find and remove any existing reveal events
                    self.book.events = [event for event in self.book.events if event.get('type') != 'reveal']
                
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
                
                while (self.events.bonus_mode or self.events.super_bonus_mode) and not self.events.is_bonus_complete():
                    
                    # Use appropriate reels for buy bonus mode
                    # Set correct gametype based on bonus type to use proper reel set
                    if is_super_bonk:
                        self.gametype = self.config.freegame_type  # Use freegame_type for SUPER_BONK_SPINS
                    else:
                        self.gametype = self.config.freegame_type  # Use freegame_type for BONK_SPINS
                    
                    # Create new board for each bonus spin
                    self.create_board_reelstrips()
                    
                    # Change gametype to free for bonus spin events
                    self.gametype = self.config.freegame_type
                    
                    # Use custom reveal event for Bonk Boi
                    reveal_event_bonk_boi(self)
                    
                    # Get symbols from board
                    reels = self.get_board_symbols()
                    
                    # Process the bonus spin using base game logic (multiply two symbols)
                    if is_super_bonk:
                        # For SUPER_BONK_SPINS, use sticky logic from bonus_state
                        result = 0  # Will be calculated by process_super_bonk_spin
                    else:
                        # For BONK_SPINS, use regular calculation
                        result = self.events.calculate_bonus_spin_win(reels)
                    
                    # Handle bonus symbols for extra spins (ONLY for upgrade logic, not for adding spins)
                    for symbol in reels:
                        if symbol == "Golden Bat":
                            # Golden Bat in Bonk Spins upgrades to Super Bonk Spins
                            if self.events.bonus_mode and not self.events.super_bonus_mode:
                                # print(f"DEBUG: Upgrading from BONK_SPINS to SUPER_BONK_SPINS in gamestate!")
                                self.events.bonus_mode = False
                                self.events.super_bonus_mode = True
                                # Update bonus state - sync with process_bonk_spin
                                if self.events.bonus_state:
                                    self.events.bonus_state["type"] = "SUPER_BONK_SPINS"
                                    self.events.bonus_state["multiplier"] = 4  # SUPER_BONK_SPINS has 4x multiplier
                                    self.events.bonus_state["upgraded_from_bonk"] = True
                                
                                # CRITICAL: Mark that we need to create BONUS_TRIGGER event for upgrade
                                self.needs_upgrade_bonus_trigger = True
                                
                                # CRITICAL: Store the symbols that triggered the upgrade for BONUS_TRIGGER event
                                # Use actual symbols from current board (Golden Bat can be on either reel)
                                self.upgrade_trigger_symbols = list(reels)
                    
                    # Note: Extra spins are now handled ONLY in process_bonus_spin_logic to avoid duplication
                    
                    # Apply sticky multiplier for SUPER_BONK_SPINS
                    # if is_super_bonk:
                    #     # SUPER_BONK_SPINS uses sticky logic, result will be set by process_super_bonk_spin
                    #     print(f"DEBUG: SUPER_BONK_SPINS sticky mode - result will be calculated by sticky logic")
                    # else:
                    #     # Regular BONK_SPINS logic
                    #     pass
                    
                    self.bonus_game_active = True
                    self.bonus_spins_completed += 1
                    
                    # Update bonus state for buy bonus mode
                    if self.events.bonus_state:
                        # Update total_win in bonus_state before processing
                        self.events.bonus_state["total_win"] = self.total_bonus_win
                        
                        # Use process_bonus_spin_logic to handle bonus spin logic (including sticky for SUPER_BONK_SPINS)
                        bonus_type = self.events.bonus_state["type"]
                        self.events.bonus_state = self.events.process_bonus_spin_logic(self.events.bonus_state, reels, bonus_type)
                        
                        # Get current spin win from bonus_state for BOTH modes and accumulate once
                        current_spin_win = self.events.bonus_state.get("current_spin_win")
                        if current_spin_win is None:
                            prev_total = self.total_bonus_win
                            new_total = self.events.bonus_state.get("total_win", 0)
                            current_spin_win = max(0, new_total - prev_total)
                        result = current_spin_win
                        self.total_bonus_win += current_spin_win
                        
                        # CRITICAL: Always sync bonus_state["total_win"] with self.total_bonus_win
                        old_bonus_state_total_win = self.events.bonus_state["total_win"]
                        self.events.bonus_state["total_win"] = self.total_bonus_win
                        
                        # Check for maxwin limit (1,000,000) - stop bonus game if reached
                        if self.total_bonus_win >= 1000000:
                            self.events.bonus_state["maxwin_reached"] = True
                            self.events.bonus_state["spins_left"] = 0
                            # НЕ виходимо з циклу - дозволяємо завершити поточний спін
                            # щоб створити bonus spin event з maxWinReached: true
                        
                        # Check if bonus type was upgraded (only on the FIRST upgrade)
                        if (self.events.bonus_state["type"] == "SUPER_BONK_SPINS" and 
                            self.events.bonus_state.get("upgraded_from_bonk", False) and 
                            not self.upgrade_bonus_trigger_created):
                            
                            # Switch to BON2 reels for upgraded bonus
                            self.events.current_reel_set = "BON2"
                            
                            # CRITICAL: Update is_super_bonk to True after upgrade
                            is_super_bonk = True
                            
                            # CRITICAL: Sync total_bonus_win with bonus_state["total_win"] after upgrade
                            self.total_bonus_win = self.events.bonus_state["total_win"]
                            
                            # CRITICAL: Mark that we need to create BONUS_TRIGGER event after BONUS_SPIN
                            # We'll create the BONUS_TRIGGER event after add_bonus_spin_event
                            # self.needs_upgrade_bonus_trigger = True
                            
                            # Mark that we've already created the upgrade BONUS_TRIGGER
                            self.upgrade_bonus_trigger_created = True
                        
                        # Update total_win in bonus_state after processing
                        self.events.bonus_state["total_win"] = self.total_bonus_win
                    
                    # Add bonus spin event to book
                    self.add_bonus_spin_event(reels, result, bonus_type)
                    
                    # Check if we need to create BONUS_TRIGGER event for upgrade
                    if self.needs_upgrade_bonus_trigger:
                        # Create upgrade BONUS_TRIGGER event
                        self.events.create_bonus_trigger_event(
                            self,
                            "SUPER_BONK_SPINS",  # bonus_type for upgrade
                            self.upgrade_trigger_symbols,  # Use stored upgrade trigger symbols
                            0,  # trigger_win = 0 for upgrade
                            5   # spins_received = 5 for Golden Bat upgrade
                        )
                        # print(f"DEBUG: Created BONUS_TRIGGER event for upgrade")
                        # Reset the flag
                        self.needs_upgrade_bonus_trigger = False
                
                # End bonus game and add summary
                # Save the total bonus win before ending the game (since end_bonus_game resets it to 0)
                total_bonus_win = self.total_bonus_win
                self.end_bonus_game()
                print("here3")
                
                # Check if maxwin was reached in buy bonus mode
                if hasattr(self, 'final_win') and self.final_win > 0:
                    # Maxwin was reached - use final_win set in end_bonus_game
                    # final_win вже встановлено в end_bonus_game як maxwinAmount (без * 100)
                    final_win_amount = self.final_win
                    freegame_wins_amount = final_win_amount  # FIXED: Use actual final_win, not hardcoded 1000000
                else:
                    # Normal bonus completion - use total_bonus_win
                    final_win_amount = total_bonus_win
                    freegame_wins_amount = total_bonus_win
                
                # Встановлюємо final_win для системи (без додаткового множення на 100)
                self.final_win = final_win_amount
                
                # For buy bonus mode, payoutMultiplier should be the total bonus win amount
                # Not the multiplier ratio
                
                # Reset win manager for this spin
                self.win_manager.reset_spin_win()
                

                
                # Update win manager with final win amount
                self.win_manager.update_spinwin(final_win_amount)

                
                self.win_manager.update_gametype_wins(self.config.freegame_type)  # Bonus spins are free game

                
                # Set the final result for the spin - this should be the final win amount
                self.result = final_win_amount
                
                # Set gametype to free for buy bonus mode (since it's all bonus spins)
                self.gametype = self.config.freegame_type
                
                # Ensure win_manager has the correct values for final calculation
                self.win_manager.running_bet_win = final_win_amount

                
                # Update the win_manager to properly track base and free game wins
                # For buy bonus mode, all wins are considered free game wins
                self.win_manager.freegame_wins = freegame_wins_amount
                self.win_manager.basegame_wins = 0.0

                
                # CRITICAL: Ensure running_bet_win matches the sum of base and free game wins
                # This prevents the "Base + Free game payout mismatch!" error
                self.win_manager.running_bet_win = self.win_manager.basegame_wins + self.win_manager.freegame_wins

                
                # Also update the win_data to ensure proper final calculation
                self.win_data = {"totalWin": final_win_amount}
                
                # CRITICAL: Call evaluate_finalwin() for buy bonus mode to create finalWin event
                # This creates the finalWin event at the end of bonus spins
                self.evaluate_finalwin()
            elif current_betmode and current_betmode.get_name() == "Horny_Jail":
                # Horny_Jail mode - special handling, no bonus symbols, no additional board creation
                # Board already created by create_horny_jail_board() above
                # Just process the spin without additional logic
                reels = self.get_board_symbols()
                result = self.events.calculate_horny_jail_win(reels)
                self.result = result
                
                # Set gametype for Horny_Jail
                self.gametype = self.config.basegame_type
                
                # No bonus games for Horny_Jail
                bonus_type = None
                
                # Note: reveal event is already created in create_horny_jail_board()
                # so we don't need to call reveal_event_bonk_boi here
                
                # CRITICAL: Call evaluate_finalwin() to create finalWin event for Horny_Jail mode
                # This ensures payoutMultiplier is set before finalWin.amount is calculated
                self.evaluate_finalwin()
            elif current_betmode and current_betmode.get_name() == "bonus_hunt":
                # Bonus_Hunt mode - works exactly like base mode but uses Bonus_Hunt reel set
                # Board already created with Bonus_Hunt reel set above
                # Process spin using same logic as base game
                reels = self.get_board_symbols()
                print("here5")
                # CRITICAL: Calculate base game win for Bonus_Hunt mode from first spin symbols
                try:
                    if len(reels) >= 2:
                        symbol1 = reels[0]
                        symbol2 = reels[1]
                        
                        # Convert symbols to numbers (Bat and Golden Bat = 1)
                        def get_symbol_value(symbol):
                            if symbol in ["Bat", "Golden Bat"]:
                                return 1
                            elif symbol in ["1", "2", "3", "5", "10", "25", "50", "100", "250", "500", "1000"]:
                                return int(symbol)
                            else:
                                return 0
                        
                        mult1 = get_symbol_value(symbol1)
                        mult2 = get_symbol_value(symbol2)
                        
                        # Apply 1x1=0 rule
                        if mult1 == 1 and mult2 == 1:
                            base_game_win = 0
                        else:
                            base_game_win = mult1 * mult2
                        
                        # Store base game win for later use in update_final_win()
                        self.base_game_win_for_bonus_hunt = base_game_win
                    else:
                        self.base_game_win_for_bonus_hunt = 0
                except:
                    self.base_game_win_for_bonus_hunt = 0
                
                result, bonus_type = self.events.process_spin(reels)
                self.result = result
                
                # Set gametype for Bonus_Hunt
                self.gametype = self.config.basegame_type
                
                # Create reveal event for Bonus_Hunt mode
                reveal_event_bonk_boi(self)
                
                # Check for bonus symbols in Bonus_Hunt mode (Bat or Golden Bat)
                bonus_count = sum(1 for symbol in reels if symbol == "Bat")
                super_bonus_count = sum(1 for symbol in reels if symbol == "Golden Bat")
                
                # CRITICAL: For Bonus_Hunt mode, we need to handle base game wins differently
                # Update win_manager for base game wins using the calculated base_game_win_for_bonus_hunt
                self.win_manager.reset_spin_win()
                self.win_manager.update_spinwin(self.base_game_win_for_bonus_hunt)
                self.win_manager.update_gametype_wins(self.gametype)
                
                # Handle bonus if triggered by bonus symbols (same as base mode)
                if bonus_count > 0 or super_bonus_count > 0:
                    
                    if super_bonus_count > 0:
                        # Super Bonus symbols trigger SUPER_BONK_SPINS
                        spins_count = 13 if super_bonus_count == 2 else 10
                        bonus_type = "SUPER_BONK_SPINS"
                    else:
                        # Regular Bonus symbols trigger BONK_SPINS
                        spins_count = 15 if bonus_count == 2 else 10
                        bonus_type = "BONK_SPINS"
                    
                    # CRITICAL: Set correct reel set BEFORE triggering bonus
                    if bonus_type == "SUPER_BONK_SPINS":
                        self.events.current_reel_set = "BON2"
                    else:
                        self.events.current_reel_set = "BON1"
                    
                    # Trigger bonus (this will use the reel set we just set)
                    self.events.trigger_bonus(bonus_type, spins_count)
                    
                    # Add bonus event to book
                    self.add_bonus_event(bonus_type)
                    
                    # CRITICAL: Set bonus game active and run bonus spins for Bonus_Hunt mode
                    self.bonus_game_active = True
                    self.bonus_spins_completed = 0
                    self.total_bonus_win = 0
                    
                    # Initialize bonus state for Bonus_Hunt mode bonus
                    if bonus_type == "SUPER_BONK_SPINS":
                        self.events.bonus_state = {
                            "type": "SUPER_BONK_SPINS",
                            "spins_left": spins_count,
                            "total_win": 0,
                            "symbols_collected": [],
                            "multiplier": 4,
                            "sticky_value": None,
                            "sticky_reel": None,
                            "upgraded_from_bonk": False
                        }
                    else:
                        self.events.bonus_state = {
                            "type": "BONK_SPINS",
                            "spins_left": spins_count,
                            "total_win": 0,
                            "symbols_collected": [],
                            "multiplier": 2,
                            "upgraded_from_bonk": False
                        }
                    
                    # Run bonus spins for Bonus_Hunt mode bonus (same logic as base mode)
                    while self.bonus_game_active and self.events.bonus_state["spins_left"] > 0:
                        
                        # Set gametype for bonus spins
                        self.gametype = self.config.freegame_type
                        
                        # CRITICAL: Double-check that correct reel set is set for each bonus spin
                        if bonus_type == "SUPER_BONK_SPINS":
                            self.events.current_reel_set = "BON2"
                        else:
                            self.events.current_reel_set = "BON1"
                        
                        # Create new board for bonus spin (will use current_reel_set from events)
                        self.create_board_reelstrips()
                        
                        # Use custom reveal event for bonus spin
                        reveal_event_bonk_boi(self)
                        
                        # Get symbols from board
                        reels = self.get_board_symbols()
                        
                        # Process bonus spin logic
                        self.events.bonus_state = self.events.process_bonus_spin_logic(
                            self.events.bonus_state, reels, bonus_type
                        )
                        
                        # Get current spin win and accumulate
                        current_spin_win = self.events.bonus_state.get("current_spin_win", 0)
                        self.total_bonus_win += current_spin_win
                        
                        # Update bonus state
                        self.events.bonus_state["total_win"] = self.total_bonus_win
                        # NOTE: spins_left is decremented in process_bonus_spin_logic, don't decrement here
                        self.bonus_spins_completed += 1
                        
                        # Check for maxwin limit (1,000,000) - stop bonus game if reached
                        if self.total_bonus_win >= 1000000:
                            self.events.bonus_state["maxwin_reached"] = True
                            self.events.bonus_state["spins_left"] = 0
                            break  # Exit bonus loop
                        
                        # Add bonus spin event
                        self.add_bonus_spin_event(reels, current_spin_win, bonus_type)
                        
                        # Check for upgrade to SUPER_BONK_SPINS
                        if (bonus_type == "BONK_SPINS" and 
                            any(symbol == "Golden Bat" for symbol in reels)):
                            bonus_type = "SUPER_BONK_SPINS"
                            self.events.bonus_state["type"] = "SUPER_BONK_SPINS"
                            self.events.bonus_state["multiplier"] = 4
                            self.events.bonus_state["upgraded_from_bonk"] = True
                            self.events.bonus_state["spins_left"] += 5  # Add 5 more spins
                            
                            # CRITICAL: Switch to BON2 reels for remaining spins
                            self.events.current_reel_set = "BON2"
                            self.gametype = self.config.freegame_type
                            
                            # Force board recreation with new reel set
                            self.create_board_reelstrips()
                            
                            # CRITICAL: Create new Bonus_trigger event for the upgrade
                            self.add_bonus_event("SUPER_BONK_SPINS")
                    
                    # Preserve total bonus win BEFORE ending bonus (end_bonus_game resets totals)
                    final_total_bonus_win = self.total_bonus_win
                    
                    # CRITICAL: Check if bonus is already ended to prevent double end_bonus_game call
                    if self.events.bonus_state and not self.bonus_game_active:
                        # Bonus already ended, skip
                        pass
                    elif self.events.bonus_state:
                        # End bonus game and add summary
                        print("here2")
                        self.end_bonus_game()
                    
                    # CRITICAL: Reset reel set back to Bonus_Hunt after bonus ends
                    self.events.current_reel_set = "Bonus_Hunt"
                    
                    # Set result to preserved total bonus win for Bonus_Hunt mode
                    self.result = final_total_bonus_win
                    
                    # # CRITICAL: Skip win manager update here to prevent double counting
                    # # Win manager is already updated in end_bonus_game()
                    # self.win_manager.reset_spin_win()
                    # self.win_manager.update_spinwin(final_total_bonus_win)
                    # self.win_manager.update_gametype_wins(self.config.freegame_type)
                    
                    self.win_manager.reset_spin_win()
                    self.win_manager.update_spinwin(self.base_game_win_for_bonus_hunt)
                    self.win_manager.update_gametype_wins(self.config.freegame_type)
                    # Set gametype to free for bonus
                    self.gametype = self.config.freegame_type
                    
                    # Update final win to ensure freegame_wins is properly recorded
                    self.update_final_win()
                    
                    # CRITICAL: Call evaluate_finalwin() to create finalWin event for Bonus_Hunt mode
                    # This ensures payoutMultiplier is set before finalWin.amount is calculated
                    self.evaluate_finalwin()
                    
                    # Skip normal base game processing since we handled bonus
                    continue
                
                # Convert result to proper format (fraction, not cents) - same as base mode
                bet_amount = self.get_current_betmode().get_cost()
                result_multiplier = result / bet_amount if bet_amount > 0 else 0
                
                # Apply win cap for Bonus_Hunt mode
                if result_multiplier > self.config.wincap:
                    result_multiplier = self.config.wincap
                
                # Also update the win_data to ensure proper final calculation
                self.win_data = {"totalWin": result}
                
                # CRITICAL: Set final_win for Bonus_Hunt mode before calling evaluate_finalwin()
                # For bonus_hunt mode, final_win should be the total from win_manager
                self.final_win = self.base_game_win_for_bonus_hunt
                
                # CRITICAL: Call evaluate_finalwin() for Bonus_Hunt mode to set proper payoutMultiplier
                self.evaluate_finalwin()
            else:
                # Normal base game - check for bonus symbols first, then create board with correct reel set
                # Start with base game reels
                self.events.current_reel_set = "BR0"
                
                # Create initial board for base game
                self.create_board_reelstrips()
                
                # Use custom reveal event for Bonk Boi
                reveal_event_bonk_boi(self)
                
                # Get symbols from the board
                reels = self.get_board_symbols()
                
                # Process base game spin using original logic
                result, bonus_type = self.events.process_spin(reels)
                self.result = result
                
                # Check for bonus symbols in base game (Bat or Golden Bat)
                bonus_count = sum(1 for symbol in reels if symbol == "Bat")
                super_bonus_count = sum(1 for symbol in reels if symbol == "Golden Bat")
                
                # Handle bonus if triggered by bonus symbols
                if bonus_count > 0 or super_bonus_count > 0:
                    # First, attribute the base spin's win to baseGameWins as multiplier units
                    bet_amount = self.get_current_betmode().get_cost()
                    result_multiplier_for_base = result / bet_amount if bet_amount > 0 else 0
                    print(124, result_multiplier_for_base, result, bet_amount)
                    
                    self.win_manager.reset_spin_win()
                    self.win_manager.update_spinwin(result_multiplier_for_base)
                    self.win_manager.update_gametype_wins(self.config.basegame_type)
                    
                    if super_bonus_count > 0:
                        # Super Bonus symbols trigger SUPER_BONK_SPINS
                        spins_count = 13 if super_bonus_count == 2 else 10
                        bonus_type = "SUPER_BONK_SPINS"
                    else:
                        # Regular Bonus symbols trigger BONK_SPINS
                        spins_count = 15 if bonus_count == 2 else 10
                        bonus_type = "BONK_SPINS"
                    
                    # CRITICAL: Set correct reel set BEFORE triggering bonus
                    if bonus_type == "SUPER_BONK_SPINS":
                        self.events.current_reel_set = "BON2"
                    else:
                        self.events.current_reel_set = "BON1"
                    
                    # Trigger bonus (this will use the reel set we just set)
                    self.events.trigger_bonus(bonus_type, spins_count)
                    
                    # Add bonus event to book
                    self.add_bonus_event(bonus_type)
                    
                    # CRITICAL: Set bonus game active and run bonus spins for base game
                    self.bonus_game_active = True
                    self.bonus_spins_completed = 0
                    self.total_bonus_win = 0
                    
                    # Initialize bonus state for base game bonus
                    if bonus_type == "SUPER_BONK_SPINS":
                        self.events.bonus_state = {
                            "type": "SUPER_BONK_SPINS",
                            "spins_left": spins_count,
                            "total_win": 0,
                            "symbols_collected": [],
                            "multiplier": 4,
                            "sticky_value": None,
                            "sticky_reel": None,
                            "upgraded_from_bonk": False
                        }
                    else:
                        self.events.bonus_state = {
                            "type": "BONK_SPINS",
                            "spins_left": spins_count,
                            "total_win": 0,
                            "symbols_collected": [],
                            "multiplier": 2,
                            "upgraded_from_bonk": False
                        }
                    
                    # Run bonus spins for base game bonus
                    while self.bonus_game_active and self.events.bonus_state["spins_left"] > 0:
                        
                        # Set gametype for bonus spins
                        self.gametype = self.config.freegame_type
                        
                        # CRITICAL: Double-check that correct reel set is set for each bonus spin
                        if bonus_type == "SUPER_BONK_SPINS":
                            self.events.current_reel_set = "BON2"
                        else:
                            self.events.current_reel_set = "BON1"
                        
                        # Create new board for bonus spin (will use current_reel_set from events)
                        self.create_board_reelstrips()
                        
                        # Use custom reveal event for bonus spin
                        reveal_event_bonk_boi(self)
                        
                        # Get symbols from board
                        reels = self.get_board_symbols()
                        
                        # Process bonus spin logic
                        self.events.bonus_state = self.events.process_bonus_spin_logic(
                            self.events.bonus_state, reels, bonus_type
                        )
                        
                        # Get current spin win and accumulate
                        current_spin_win = self.events.bonus_state.get("current_spin_win", 0)
                        self.total_bonus_win += current_spin_win
                        
                        # Update bonus state
                        self.events.bonus_state["total_win"] = self.total_bonus_win
                        # NOTE: spins_left is decremented in process_bonus_spin_logic, don't decrement here
                        self.bonus_spins_completed += 1
                        
                        # Check for maxwin limit (1,000,000) - stop bonus game if reached
                        if self.total_bonus_win >= 1000000:
                            self.events.bonus_state["maxwin_reached"] = True
                            self.events.bonus_state["spins_left"] = 0
                            # НЕ виходимо з циклу - дозволяємо завершити поточний спін
                            # щоб створити bonus spin event з maxWinReached: true
                        
                        # Add bonus spin event
                        self.add_bonus_spin_event(reels, current_spin_win, bonus_type)
                        
                        # Check for upgrade to SUPER_BONK_SPINS
                        if (bonus_type == "BONK_SPINS" and 
                            any(symbol == "Golden Bat" for symbol in reels)):
                            bonus_type = "SUPER_BONK_SPINS"
                            self.events.bonus_state["type"] = "SUPER_BONK_SPINS"
                            self.events.bonus_state["multiplier"] = 4
                            self.events.bonus_state["upgraded_from_bonk"] = True
                            self.events.bonus_state["spins_left"] = 5  # Add 5 more spins
                            
                            # CRITICAL: Switch to BON2 reels for remaining spins
                            self.events.current_reel_set = "BON2"
                            self.gametype = self.config.freegame_type
                            
                            # Force board recreation with new reel set
                            self.create_board_reelstrips()
                            
                            # CRITICAL: Create new Bonus_trigger event for the upgrade
                            self.add_bonus_event("SUPER_BONK_SPINS")
                    
                    # Preserve total bonus win BEFORE ending bonus (end_bonus_game resets totals)
                    final_total_bonus_win = self.total_bonus_win
                    
                    # CRITICAL: Preserve base game win from win_manager before bonus ends
                    base_game_win = self.win_manager.basegame_wins
                    
                    # CRITICAL: Check if bonus is already ended to prevent double end_bonus_game call
                    if self.events.bonus_state and not self.bonus_game_active:
                        # Bonus already ended, skip
                        pass
                    elif self.events.bonus_state:
                        # End bonus game and add summary
                        print("here1")
                        self.end_bonus_game()
                    
                    # CRITICAL: Reset reel set back to base game after bonus ends
                    self.events.current_reel_set = "BR0"
                    
                    # CRITICAL: Set final_win to include BOTH base game win AND bonus win
                    # This ensures baseGameWins is properly recorded in the final result
                    self.final_win = base_game_win + final_total_bonus_win
                    
                    # Set result to total win (base + bonus)
                    self.result = self.final_win
                    
                    # Update win manager for free game wins
                    self.win_manager.reset_spin_win()
                    self.win_manager.update_spinwin(final_total_bonus_win)
                    self.win_manager.update_gametype_wins(self.config.freegame_type)
                    
                    # Set gametype to free for bonus
                    self.gametype = self.config.freegame_type
                    
                    # Update final win to ensure both basegame_wins and freegame_wins are properly recorded
                    self.update_final_win()
                    
                    # CRITICAL: Call evaluate_finalwin() to create finalWin event for base game with bonus
                    # This ensures payoutMultiplier is set before finalWin.amount is calculated
                    self.evaluate_finalwin()
                    
                    # Skip normal base game processing since we handled bonus
                    continue
                
                # Convert result to proper format (fraction, not cents)
                # Since our game uses multiplier values (1, 2, 3, etc.),
                # we need to convert to bet multiplier (result / bet_amount)
                bet_amount = self.get_current_betmode().get_cost()
                result_multiplier = result / bet_amount if bet_amount > 0 else 0
                
                # Apply win cap for base game
                if result_multiplier > self.config.wincap:
                    result_multiplier = self.config.wincap
                
                # Skip win manager updates for Horny_Jail and Bonus_Hunt modes since they're handled differently
                if not (current_betmode and current_betmode.get_name() in ["Horny_Jail", "bonus_hunt"]):
                    # This is crucial - it sets the payoutMultiplier in the book
                    
                    self.win_manager.update_spinwin(result_multiplier)
                    self.win_manager.update_gametype_wins(self.gametype)
                    
                    # Also update the win_data to ensure proper final calculation
                    self.win_data = {"totalWin": result_multiplier}
                elif current_betmode and current_betmode.get_name() == "Horny_Jail":
                    # For Horny_Jail mode, win_data should already be set in create_horny_jail_board
                    # But we need to set it to final_win for proper finalWin.amount display
                    if hasattr(self, 'final_win'):
                        self.win_data = {"totalWin": self.final_win}
                    elif not hasattr(self, 'win_data') or 'totalWin' not in self.win_data:
                        self.win_data = {"totalWin": 0}
                elif current_betmode and current_betmode.get_name() == "bonus_hunt":
                    # For Bonus_Hunt mode, win_data should already be set above
                    # But we need to set it to final_win for proper finalWin.amount display
                    if hasattr(self, 'final_win'):
                        self.win_data = {"totalWin": self.final_win}
                    elif not hasattr(self, 'win_data') or 'totalWin' not in self.win_data:
                        self.win_data = {"totalWin": 0}
            
            # This is crucial - it sets the payoutMultiplier in the book
            # Note: evaluate_finalwin() is now called inside buy bonus block
            # For Horny_Jail and Bonus_Hunt modes, call evaluate_finalwin() to create finalWin event
            if not (current_betmode and current_betmode.get_buybonus()):
                if current_betmode and current_betmode.get_name() == "Horny_Jail":
                    # For Horny_Jail mode, finalWin event is already created in create_horny_jail_board
                    # DO NOT call evaluate_finalwin() to avoid duplication
                    pass
                elif current_betmode and current_betmode.get_name() == "bonus_hunt":
                    # For Bonus_Hunt mode, payout_multiplier is already set
                    pass
                else:
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

        # Create bonus spin event using new method
        
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
        
        # If SUPER_BONK_SPINS sticky logic is active, attach the actual and sticky boards
        if bonus_spin_event and bonus_state["type"] == "SUPER_BONK_SPINS":
            sticky_value = bonus_state.get("sticky_value")
            sticky_reel = bonus_state.get("sticky_reel")
            # Only add sticky board if sticky logic is actually active (after first non-zero win)
            if sticky_value is not None and sticky_reel is not None:
                # Actual symbols that landed this spin
                actual_board_symbols = list(reels)
                # Symbols used for calculation with sticky applied
                if sticky_reel == 0:
                    sticky_board_symbols = [str(sticky_value), reels[1]]
                else:
                    sticky_board_symbols = [reels[0], str(sticky_value)]
                # Attach using expected keys
                bonus_spin_event["actualBoard"] = actual_board_symbols
                bonus_spin_event["stickyBoard"] = sticky_board_symbols
                
                # CRITICAL: Add stickReel property to show which reel is sticky
                bonus_spin_event["stickReel"] = sticky_reel
        
        # Check if maxwin was reached in this spin
        if bonus_state.get("maxwin_reached", False):
            bonus_spin_event["maxWinReached"] = True

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
            
            # Check if maxwin was reached
            if summary.get("maxwin_reached", False):
                # Create maxwin event instead of normal bonus complete
                self.create_maxwin_event(summary)
                
                # Set final_win and freegame_wins for maxwin case
                # final_win буде використано системою для створення finalWin event
                # НЕ множимо на 100 тут - система вже множить на 100 в final_win_event
                self.final_win = summary["maxwin_amount"]  # 1,000,000 (без * 100)
                
                # Встановлюємо win_manager значення для правильного finalWin event
                self.win_manager.freegame_wins = float(summary["maxwin_amount"])  # 1,000,000.0
                self.win_manager.basegame_wins = 0.0
                

                
                # CRITICAL: Ensure running_bet_win matches the sum of base and free game wins
                # This prevents the "Base + Free game payout mismatch!" error
                self.win_manager.running_bet_win = self.win_manager.basegame_wins + self.win_manager.freegame_wins

            else:
                # Create bonus complete event using new method
                self.events.create_bonus_complete_event(
                    self,
                    self.bonus_session_id,
                    summary["total_win"],
                    self.bonus_spins_completed,
                    summary["type"],
                    final_multiplier
                )
                
                # CRITICAL: Set final_win for normal bonus games (not maxwin)
                # This ensures baseGameWins and freeGameWins are calculated correctly
                self.final_win = summary["total_win"]
                
                # Встановлюємо win_manager значення для правильного finalWin event
                self.win_manager.freegame_wins = float(summary["total_win"])
                self.win_manager.basegame_wins = 0
                print(summary)
                
                # CRITICAL: Ensure running_bet_win matches the sum of base and free game wins
                # This prevents the "Base + Free game payout mismatch!" error
                self.win_manager.running_bet_win = self.win_manager.basegame_wins + self.win_manager.freegame_wins

        # Reset bonus state and return to base game
        self.bonus_game_active = False
        self.bonus_spins_completed = 0
        self.total_bonus_win = 0
        self.bonus_session_id = None
        self.events.reset_to_base_game()  # Reset to BR0 reels

        # Update bonus session ID in events
        self.events.bonus_session_id = None

    def create_maxwin_event(self, summary):
        """Create MAXWIN event when bonus game reaches 1,000,000 limit"""
        event = {
            "index": len(self.book.events),
            "type": "maxwin",  # Custom event type for maxwin
            "bonusSessionId": self.bonus_session_id,
            "totalBonusWin": summary["maxwin_amount"],  # 1,000,000
            "spinsCompleted": self.bonus_spins_completed,
            "bonusType": summary["type"],
            "reason": "maxwin_limit",
            "maxwinAmount": 1000000,
            "gameType": self.config.freegame_type
        }
        
        self.book.add_event(event)
        
        # НЕ створюємо finalWin event тут - система створить його автоматично
        # через evaluate_finalwin() → final_win_event()
        # Нам потрібно тільки правильно встановити final_win та freegame_wins

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
