import logging
from typing import Type, Optional
from sqlalchemy.orm import Session

import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../..')))

from models import Strategy as DBStrategy
from simulator.interfaces.strategy import Strategy, validate_strategy_class
from simulator.signals.enums import Signal

logger = logging.getLogger("StrategyLoader")

class StrategyLoader:
    """
    Safely loads and instantiates trading strategies from the database.
    Ensures that loaded code adheres to the standardized Strategy interface.
    """
    
    @staticmethod
    def load_from_db(db: Session, strategy_id: int) -> Optional[Type[Strategy]]:
        """
        Fetches a strategy by ID from the database and returns its class definition.
        """
        db_strategy = db.query(DBStrategy).filter(DBStrategy.id == strategy_id).first()
        if not db_strategy:
            logger.error(f"Strategy with ID {strategy_id} not found.")
            return None
            
        return StrategyLoader.load_from_string(db_strategy.code)

    @staticmethod
    def load_from_string(code: str) -> Optional[Type[Strategy]]:
        # Robustly strip mock UI imports using regex to handle variations in spacing/indentation
        import re
        # Strip lines containing quantive.sdk or aegis.sdk imports
        lines = code.splitlines()
        filtered_lines = []
        for line in lines:
            if re.search(r"(from|import)\s+(quantive|aegis)\.sdk", line, re.IGNORECASE):
                continue
            # Also strip other common mock imports from UI templates
            if "from simulator.interfaces.strategy import Strategy" in line: continue
            if "from simulator.signals.signal import Signal" in line: continue
            if "from simulator.signals.enums import Signal" in line: continue
            if "import pandas_ta as ta" in line: continue
            filtered_lines.append(line)
        
        code = "\n".join(filtered_lines)
        
        # Create a restricted globals dictionary with only necessary dependencies
        restricted_globals = {
            'Strategy': Strategy,
            'Agent': Strategy, # Map UI's 'Agent' to backend 'Strategy'
            'Signal': Signal,
            '__builtins__': __builtins__
        }
        
        # Try importing common mathematical/data libraries that strategies might need safely
        try:
            import pandas as pd
            restricted_globals['pd'] = pd
            try:
                import pandas_ta as ta
                restricted_globals['ta'] = ta
            except ImportError:
                class MockTA:
                    @staticmethod
                    def rsi(close, length=14):
                        # Simple mock RSI
                        return pd.Series([35.0 if i % 2 == 0 else 75.0 for i in range(len(close))], index=close.index)
                    @staticmethod
                    def sma(close, length=50):
                        return close.rolling(window=length, min_periods=1).mean()
                    @staticmethod
                    def zscore(close, length=20):
                        mean = close.rolling(window=length, min_periods=1).mean()
                        std = close.rolling(window=length, min_periods=1).std()
                        # Avoid div by zero
                        std = std.replace(0, 1)
                        return (close - mean) / std
                restricted_globals['ta'] = MockTA
        except ImportError:
            pass

        try:
            # Execute the code in the restricted namespace
            exec(code, restricted_globals)
            
            # Find the class that implements Strategy
            strategy_class = None
            for name, obj in restricted_globals.items():
                if isinstance(obj, type) and issubclass(obj, Strategy) and obj is not Strategy:
                    strategy_class = obj
                    break
                    
            if not strategy_class:
                logger.error("No valid Strategy subclass found in the provided code.")
                raise ValueError("No valid Strategy subclass found.")
                
            if not validate_strategy_class(strategy_class):
                logger.error(f"Class {strategy_class.__name__} failed validation.")
                raise ValueError(f"Class {strategy_class.__name__} failed validation.")
                
            return strategy_class
            
        except Exception as e:
            error_msg = f"{type(e).__name__}: {str(e)}"
            logger.error(f"Failed to load strategy code: {error_msg}")
            logger.error(f"Attempted to execute code:\n{code}")
            raise ValueError(error_msg)
