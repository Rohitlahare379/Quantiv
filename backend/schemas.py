from pydantic import BaseModel
from typing import Optional, Dict, Any
from datetime import datetime

class StrategyCreate(BaseModel):
    name: str
    code: str
    template_id: Optional[str] = "rsi"
    asset: Optional[str] = "BTCUSDT"
    timeframe: Optional[str] = "1h"
    parameters: Optional[Dict[str, Any]] = None

class StrategyResponse(StrategyCreate):
    id: int
    updated_at: datetime

    model_config = {"from_attributes": True}
