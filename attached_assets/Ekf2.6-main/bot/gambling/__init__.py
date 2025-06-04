"""
Gambling System Module
Modular gambling system with specialized game implementations
"""

from .core import GamblingCore
from .slots import SlotsGame
from .blackjack import BlackjackGame
from .roulette import RouletteGame

__all__ = ['GamblingCore', 'SlotsGame', 'BlackjackGame', 'RouletteGame']