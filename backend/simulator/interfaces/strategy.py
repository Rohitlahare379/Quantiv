from abc import ABC, abstractmethod
from typing import Any, Dict

import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../..')))

from market_data.normalizers.schemas import NormalizedCandle
from simulator.signals.enums import Signal

class Strategy(ABC):
    """
    Standardized base class for all Quantive trading strategies.
    Any custom strategy loaded from PostgreSQL must inherit from this
    and implement the on_candle method.
    """
    @abstractmethod
    def on_candle(self, candle: NormalizedCandle, history: Dict[str, Any] = None) -> Signal:
        """
        Process a new candle and return a trading signal.
        
        :param candle: The latest normalized market candle.
        :param history: Historical context or indicators (optional).
        :return: Signal.BUY, Signal.SELL, or Signal.HOLD
        """
        pass

def validate_strategy_class(cls: type) -> bool:
    """
    Validates that a given class definition correctly implements the Strategy interface.
    """
    if not isinstance(cls, type):
        return False
        
    if not issubclass(cls, Strategy):
        return False
        
    # Check that it actually overrides on_candle
    if not hasattr(cls, 'on_candle'):
        return False
        
    return True
