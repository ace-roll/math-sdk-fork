"""Game executables for Bonk Boi multiplier game with bonus games."""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))
from src.executables.executables import Executables


class GameExecutables(Executables):
    """Handle game-specific executable functions for Bonk Boi."""

    def __init__(self, config):
        super().__init__(config)

    def assign_special_sym_function(self, *args, **kwargs):
        """Assign special symbol functions."""
        pass
