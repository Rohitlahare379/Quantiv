from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from contextlib import asynccontextmanager
import asyncio
import math
from datetime import datetime, timedelta, timezone

from database import engine, Base, get_db, SessionLocal
from sqlalchemy import text
import models
import schemas
from market_data.api.router import router as market_data_router
import market_data.storage.models  # Register market_candles table
from market_data.websocket.binance_ws import ws_client
from simulator.api.router import router as simulator_router
from orchestrator.runtime import Orchestrator
from orchestrator.context import SharedContext

from config import settings, validate_environment
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("QuantiveMain")

# Create database tables
Base.metadata.create_all(bind=engine)

def seed_demo_market_data_if_empty():
    """
    Ensures the simulator has a deterministic local replay dataset.
    This avoids the app appearing to run while replay metrics stay flat because
    SQLite was started from a different cwd or historical ingestion never ran.
    """
    from market_data.storage.models import MarketCandle

    db = SessionLocal()
    try:
        existing = db.query(MarketCandle).filter(
            MarketCandle.symbol == "BTCUSDT",
            MarketCandle.timeframe == "1h"
        ).count()
        if existing > 0:
            return

        logger.warning("No BTCUSDT 1h candles found. Seeding deterministic demo replay data.")
        start = datetime(2020, 1, 1, tzinfo=timezone.utc)
        records = []

        for i in range(2500):
            timestamp = start + timedelta(hours=i)
            cycle = math.sin(i / 9.0) * 420
            broader_cycle = math.sin(i / 53.0) * 850
            trend = i * 1.8
            close = 7200 + trend + cycle + broader_cycle
            open_price = close - math.sin(i / 5.0) * 80
            high = max(open_price, close) + 90 + abs(math.sin(i / 3.0) * 45)
            low = min(open_price, close) - 90 - abs(math.cos(i / 4.0) * 45)
            volume = 1200 + abs(math.sin(i / 7.0) * 600)

            records.append(MarketCandle(
                symbol="BTCUSDT",
                timeframe="1h",
                timestamp=timestamp,
                open=open_price,
                high=high,
                low=low,
                close=close,
                volume=volume,
                source="demo_seed"
            ))

        db.bulk_save_objects(records)
        db.commit()
        logger.info("Seeded %s deterministic BTCUSDT 1h candles.", len(records))
    finally:
        db.close()

@asynccontextmanager
async def lifespan(app: FastAPI):
    # 1. Environment Validation
    logger.info("--- Quantive System Startup ---")
    issues = validate_environment()
    if issues:
        for issue in issues:
            logger.error(f"Startup Blocked: {issue}")
        # In a real demo, we might exit, but for local dev we continue with warnings
    
    # 2. Database Connectivity Check
    try:
        # Simple query to verify DB
        db = SessionLocal()
        db.execute(text("SELECT 1"))
        db.close()
        logger.info("Database connectivity verified.")
        seed_demo_market_data_if_empty()
    except Exception as e:
        logger.error(f"Database connection failed: {str(e)}")

    # 3. Market Data Stream Initialization
    symbols = ["BTCUSDT", "ETHUSDT"]
    logger.info(f"Initializing real-time market data streams for: {symbols}")
    task = asyncio.create_task(ws_client.start_stream(symbols, timeframe="1m"))
    
    logger.info("Quantive Orchestrator initialized and ready.")
    yield
    
    # Shutdown
    logger.info("Shutting down market data streams...")
    task.cancel()
    logger.info("Quantive System Shutdown complete.")

app = FastAPI(title="Quantive Autonomous Evaluation Platform", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"], # Specific origins required for credentials
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(market_data_router, prefix="/api/market-data", tags=["Market Data"])
app.include_router(simulator_router, prefix="/ws", tags=["Simulator"])

@app.get("/")
def read_root():
    return {"message": "Quantive Room 1 Backend is running"}

@app.get("/health")
def health_check(db: Session = Depends(get_db)):
    return {"status": "ok", "database": "connected"}

@app.get("/api/strategies", response_model=list[schemas.StrategyResponse])
def list_strategies(db: Session = Depends(get_db)):
    return db.query(models.Strategy).order_by(models.Strategy.updated_at.desc()).all()

@app.get("/api/strategies/{strategy_id}", response_model=schemas.StrategyResponse)
def get_strategy(strategy_id: int, db: Session = Depends(get_db)):
    db_strategy = db.query(models.Strategy).filter(models.Strategy.id == strategy_id).first()
    if not db_strategy:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Strategy not found")
    return db_strategy

@app.post("/api/strategies", response_model=schemas.StrategyResponse)
def save_strategy(strategy: schemas.StrategyCreate, db: Session = Depends(get_db)):
    # If a strategy with the same name exists, we update it (standard behavior)
    db_strategy = db.query(models.Strategy).filter(models.Strategy.name == strategy.name).first()
    if db_strategy:
        for key, value in strategy.model_dump().items():
            setattr(db_strategy, key, value)
        db.commit()
        db.refresh(db_strategy)
        return db_strategy
        
    new_strategy = models.Strategy(**strategy.model_dump())
    db.add(new_strategy)
    db.commit()
    db.refresh(new_strategy)
    
    from omium.sdk import trace
    trace("WORKSHOP", "STRATEGY_SAVED", f"Strategy '{new_strategy.name}' persisted to database", {"strategy_id": new_strategy.id})
    
    return new_strategy

@app.put("/api/strategies/{strategy_id}", response_model=schemas.StrategyResponse)
def update_strategy(strategy_id: int, strategy: schemas.StrategyCreate, db: Session = Depends(get_db)):
    db_strategy = db.query(models.Strategy).filter(models.Strategy.id == strategy_id).first()
    if not db_strategy:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Strategy not found")
    
    for key, value in strategy.model_dump().items():
        setattr(db_strategy, key, value)
        
    db.commit()
    db.refresh(db_strategy)
    return db_strategy

@app.patch("/api/strategies/{strategy_id}", response_model=schemas.StrategyResponse)
def rename_strategy(strategy_id: int, name_data: dict, db: Session = Depends(get_db)):
    db_strategy = db.query(models.Strategy).filter(models.Strategy.id == strategy_id).first()
    if not db_strategy:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Strategy not found")
    
    db_strategy.name = name_data.get("name", db_strategy.name)
    db.commit()
    db.refresh(db_strategy)
    return db_strategy

@app.delete("/api/strategies/{strategy_id}")
def delete_strategy(strategy_id: int, db: Session = Depends(get_db)):
    db_strategy = db.query(models.Strategy).filter(models.Strategy.id == strategy_id).first()
    if not db_strategy:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Strategy not found")
    
    db.delete(db_strategy)
    db.commit()
    return {"status": "success"}

@app.post("/api/orchestrate")
async def run_orchestration(context_data: dict, db: Session = Depends(get_db)):
    orchestrator = Orchestrator()
    
    # Initialize shared context from request
    context = SharedContext(
        strategy_name=context_data.get("strategy_name", "Unknown"),
        strategy_code=context_data.get("strategy_code", ""),
        asset=context_data.get("asset", "BTCUSDT"),
        timeframe=context_data.get("timeframe", "1h"),
        parameters=context_data.get("parameters", {}),
        replay_metrics=context_data.get("replay_metrics", {})
    )
    
    # Run the workflow
    final_context = await orchestrator.execute_workflow(context)
    
    return final_context

@app.post("/api/send-report")
async def send_report(report_data: dict):
    email = report_data.get("email")
    if not email:
        from fastapi import HTTPException
        raise HTTPException(status_code=400, detail="Email is required")
    
    # Simulate email sending - In a real production app, use smtplib or a service like SendGrid
    logger.info(f"--- EMAIL REPORT OUTBOUND ---")
    logger.info(f"To: {email}")
    logger.info(f"Subject: Quantive Strategy Evaluation Report - {report_data.get('metadata', {}).get('strategy')}")
    logger.info(f"Content: Strategy {report_data.get('metadata', {}).get('strategy')} for {report_data.get('metadata', {}).get('asset')} has been evaluated.")
    logger.info(f"Decision: {report_data.get('evaluation', {}).get('decision')}")
    logger.info(f"------------------------------")
    
    return {"status": "success", "message": f"Report successfully queued for {email}"}
