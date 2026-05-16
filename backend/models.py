from sqlalchemy import Column, Integer, String, Text, DateTime, JSON
from sqlalchemy.sql import func
from database import Base

class Strategy(Base):
    __tablename__ = "strategies"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)
    code = Column(Text)
    template_id = Column(String, default="rsi")
    asset = Column(String, default="BTCUSDT")
    timeframe = Column(String, default="1h")
    parameters = Column(JSON, nullable=True)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now(), default=func.now())
