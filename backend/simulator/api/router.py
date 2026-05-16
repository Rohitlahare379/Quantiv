import asyncio
import json
from datetime import datetime, timezone
from fastapi import APIRouter, WebSocket, WebSocketDisconnect

import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../..')))

from simulator.loaders.strategy_loader import StrategyLoader
from simulator.models.replay import ReplayConfig, ReplayStatus
from simulator.replay.engine import ReplayEngine
from simulator.models.execution import ExecutionConfig
from simulator.execution.engine import ExecutionEngine
from simulator.portfolio.manager import PortfolioManager
from simulator.runtime.engine import StrategyRunner
from simulator.metrics.calculator import MetricsCalculator
from simulator.signals.enums import Signal
from omium.sdk import trace

import logging
logger = logging.getLogger("SimulatorAPI")

router = APIRouter()

from pydantic import BaseModel

class ValidationRequest(BaseModel):
    code: str

import traceback

@router.post("/validate/")
async def validate_strategy(request: ValidationRequest):
    trace("WORKSHOP", "VALIDATION_STARTED", "Starting strategy structure and dry-run validation")
    try:
        StrategyClass = StrategyLoader.load_from_string(request.code)
        if not StrategyClass:
            trace("WORKSHOP", "VALIDATION_FAILED", "Structure error: No valid Strategy subclass found")
            return {"status": "error", "message": "Structure error: No valid Strategy subclass found in the provided code."}
            
        # Instantiate to check __init__
        try:
            instance = StrategyClass()
        except Exception as e:
            return {
                "status": "error", 
                "message": f"Initialization error: {str(e)}",
                "traceback": traceback.format_exc()
            }
        
        # 2. Dry Run Phase
        try:
            from database import SessionLocal
            from market_data.storage.models import MarketCandle
            from simulator.runtime.engine import StrategyRunner
            
            db = SessionLocal()
            # Fetch a few candles for the standard asset (BTCUSDT) to test
            test_candles = db.query(MarketCandle).filter(MarketCandle.symbol == "BTCUSDT").limit(5).all()
            db.close()
            
            if test_candles:
                from market_data.normalizers.schemas import NormalizedCandle
                runner = StrategyRunner(instance, strategy_name="ValidationRunner")
                for candle in test_candles:
                    # Convert SQLAlchemy to Pydantic
                    pydantic_candle = NormalizedCandle(
                        symbol=candle.symbol,
                        timeframe=candle.timeframe,
                        timestamp=candle.timestamp,
                        open=candle.open,
                        high=candle.high,
                        low=candle.low,
                        close=candle.close,
                        volume=candle.volume,
                        source=candle.source
                    )
                    decision = runner.process_candle(pydantic_candle)
                    if "crashed" in decision.reasoning.lower():
                        return {
                            "status": "error",
                            "message": f"Runtime error during dry-run: {decision.reasoning}"
                        }
            
        except Exception as e:
            return {
                "status": "error",
                "message": f"Runtime error during dry-run: {str(e)}",
                "traceback": traceback.format_exc()
            }
            
        trace("WORKSHOP", "VALIDATION_COMPLETED", "Strategy passed dry-run and structure checks")
        return {"status": "success", "message": "Strategy validated successfully."}
    except Exception as e:
        logger.error(f"Validation error: {e}")
        return {
            "status": "error", 
            "message": str(e),
            "traceback": traceback.format_exc()
        }

@router.websocket("/replay")
@router.websocket("/simulate")
async def simulate_endpoint(websocket: WebSocket):
    await websocket.accept()
    
    # Simple state tracking for active sessions
    active_session = True
    replay_engine = None
    
    # Task to handle incoming commands (Pause, Play, Stop, Speed)
    async def listen_for_commands():
        nonlocal active_session
        try:
            while active_session:
                data = await websocket.receive_text()
                command = json.loads(data)
                
                action = command.get("action")
                if action == "pause" and replay_engine:
                    replay_engine.pause()
                    await websocket.send_json({"type": "status", "status": "PAUSED"})
                elif action == "play" and replay_engine:
                    replay_engine.start()
                    await websocket.send_json({"type": "status", "status": "REPLAYING"})
                elif action == "speed" and replay_engine:
                    new_speed = float(command.get("value", 20.0))
                    replay_engine.set_speed(new_speed)
                elif action == "stop":
                    logger.info("[Simulator] STOP command received.")
                    if replay_engine:
                        replay_engine.stop()
                    active_session = False
                    await websocket.send_json({"type": "status", "status": "STOPPED"})
                    
        except WebSocketDisconnect:
            active_session = False
            if replay_engine:
                replay_engine.stop()
        except Exception as e:
            logger.error(f"[Simulator] Command listener error: {e}")
            active_session = False

    try:
        # Wait for the initial configuration
        data = await websocket.receive_text()
        config_data = json.loads(data)
        
        # Validation Phase
        await websocket.send_json({"type": "status", "status": "LOADING"})
        
        command_task = asyncio.create_task(listen_for_commands())
        
        strategy_code = config_data.get("code", "")
        symbol = config_data.get("symbol", "BTCUSDT")
        regime_id = config_data.get("regime", "covid_2020")
        
        # 1. Configuration
        timeframe = config_data.get("timeframe", "1h")
        parameters = config_data.get("parameters", {})
        
        # Load Strategy
        StrategyClass = StrategyLoader.load_from_string(strategy_code)
        if not StrategyClass:
            await websocket.send_json({"type": "error", "message": "Failed to load strategy. Invalid code."})
            return
            
        strategy_instance = StrategyClass()
        
        # Apply parameters to strategy instance
        if parameters:
            for key, value in parameters.items():
                logger.info(f"[Simulator] Applying parameter: {key} = {value}")
                setattr(strategy_instance, key, value)
        
        # Regimes mapping and custom dataset support
        from simulator.regimes.manager import RegimeManager
        
        if regime_id == "custom":
            try:
                start_dt = datetime.fromisoformat(config_data.get("start_time")).replace(tzinfo=timezone.utc)
                end_dt = datetime.fromisoformat(config_data.get("end_time")).replace(tzinfo=timezone.utc)
            except (ValueError, TypeError):
                await websocket.send_json({"type": "error", "message": "Invalid custom date format."})
                return
        else:
            regime = RegimeManager.get_regime(regime_id)
            if not regime:
                regime = RegimeManager.get_regime("full_history")
            start_dt = regime["start"]
            end_dt = regime["end"]
        
        replay_config = ReplayConfig(
            symbols=[symbol],
            timeframe=timeframe,
            start_time=start_dt,
            end_time=end_dt,
            speed_multiplier=config_data.get("speed_multiplier", 20.0)
        )
        
        # 2. Instantiate and Validate
        replay_engine = ReplayEngine(replay_config)
        
        candle_count = await replay_engine.validate_dataset()
        
        # Dynamic Data Ingestion for Custom Ranges
        if candle_count == 0 and regime_id == "custom":
            logger.info(f"[Simulator] No local data for {symbol} ({timeframe}) in range {start_dt} to {end_dt}. Fetching from Binance...")
            await websocket.send_json({"type": "status", "status": "FETCHING_DATA", "message": f"Fetching missing data for {symbol}..."})
            
            from market_data.ingestion.fetch_binance import BinanceIngester
            from database import SessionLocal
            
            db = SessionLocal()
            try:
                ingester = BinanceIngester(db)
                # Run ingestion in a thread to avoid blocking the event loop
                await asyncio.to_thread(ingester.ingest_historical, symbol, timeframe, start_dt, end_dt)
                # Re-validate after ingestion
                candle_count = await replay_engine.validate_dataset()
            finally:
                db.close()

        if candle_count == 0:
            logger.error(f"[Simulator] No data found for {symbol} ({timeframe}) between {start_dt} and {end_dt}")
            await websocket.send_json({
                "type": "error", 
                "message": f"No historical data found for {symbol} at {timeframe} resolution for the selected dates."
            })
            return

        # 3. Validation Success
        await websocket.send_json({"type": "status", "status": "READY"})
        await asyncio.sleep(0.5) # UI transition breathing room
        
        runner = StrategyRunner(strategy_instance, strategy_name="WorkshopStrategy")
        
        # 3 Portfolios for Friction Breakdown
        # 1. Ideal: 0 slippage, 0 latency, 0 fees
        exec_ideal = ExecutionConfig(slippage_percent=0.0, fees_percent=0.0)
        portfolio_ideal = PortfolioManager(initial_balance=10000.0, execution_config=exec_ideal)
        
        # 2. Slippage: 0.5% slippage, 0.1% fees, 0 latency
        exec_slip = ExecutionConfig(slippage_percent=0.005, fees_percent=0.001)
        portfolio_slip = PortfolioManager(initial_balance=10000.0, execution_config=exec_slip)
        
        # 3. Live: Slippage + Fees + 1 Candle Latency
        exec_live = ExecutionConfig(slippage_percent=0.005, fees_percent=0.001)
        portfolio_live = PortfolioManager(initial_balance=10000.0, execution_config=exec_live)
        
        latency_queue = [] # Queue to hold signals for 1 candle latency
        
        # Send initial state
        trace("SIMULATOR", "REPLAY_STARTED", f"Starting market replay for {symbol} on {regime_id} regime", {"symbol": symbol, "regime": regime_id})
        await websocket.send_json({
            "type": "status",
            "status": "LOADING"
        })
        await asyncio.sleep(0.5) # Simulate loading phase

        await websocket.send_json({
            "type": "init",
            "balance": portfolio_live.state.current_balance
        })
        
        await websocket.send_json({
            "type": "status",
            "status": "REPLAYING"
        })
        
        # Track equity curves
        equity_ideal = [portfolio_ideal.state.current_balance]
        equity_slip = [portfolio_slip.state.current_balance]
        equity_live = [portfolio_live.state.current_balance]
        
        replay_engine.start()
        
        from simulator.models.runtime import StrategyDecision
        
        # Core Simulation Loop
        async for candle in replay_engine.stream_candles():
            if not active_session:
                break
                
            # 1. Strategy evaluates candle
            decision = runner.process_candle(candle)
            
            # 2. Portfolio handles execution (Ideal & Slippage happen instantly)
            portfolio_ideal.process_decision(decision, candle)
            portfolio_slip.process_decision(decision, candle)
            
            # 3. Latency execution
            latency_queue.append(decision)
            if len(latency_queue) > 1: # 1 candle latency
                delayed_decision = latency_queue.pop(0)
                exec_record = portfolio_live.process_decision(delayed_decision, candle)
            else:
                hold_decision = StrategyDecision(symbol=decision.symbol, signal=Signal.HOLD, timestamp=candle.timestamp, strategy_name=decision.strategy_name)
                exec_record = portfolio_live.process_decision(hold_decision, candle)
            
            # Update equity curves
            equity_ideal.append(portfolio_ideal.state.current_balance)
            equity_slip.append(portfolio_slip.state.current_balance)
            equity_live.append(portfolio_live.state.current_balance)
            
            # Calculate live metrics
            ret_ideal = ((portfolio_ideal.state.current_balance - 10000.0) / 10000.0) * 100
            ret_slip = ((portfolio_slip.state.current_balance - 10000.0) / 10000.0) * 100
            ret_live = ((portfolio_live.state.current_balance - 10000.0) / 10000.0) * 100
            
            slippage_cost = ret_slip - ret_ideal
            latency_cost = ret_live - ret_slip
            
            # 4. Stream incremental updates to frontend
            winning_trades = sum(1 for pnl in portfolio_live.realized_pnls if pnl > 0)
            live_win_rate = (winning_trades / len(portfolio_live.realized_pnls) * 100) if portfolio_live.realized_pnls else 0.0

            update = {
                "type": "update",
                "progress": {
                    "time": candle.timestamp.isoformat(),
                    "price": candle.close,
                    "candles_processed": replay_engine.state.candles_processed,
                    "total_candles": candle_count,
                    "percentage": (replay_engine.state.candles_processed / candle_count) * 100 if candle_count > 0 else 0,
                    "speed": replay_engine.config.speed_multiplier,
                    "regime": regime_id
                },
                "balance": portfolio_live.state.current_balance,
                "pnl": portfolio_live.state.current_balance - 10000.0,
                "trade_count": len(portfolio_live.realized_pnls),
                "win_rate": live_win_rate,
                "signal": decision.signal.name if decision.signal != Signal.HOLD else None,
                "metrics": {
                    "backtest_return": ret_ideal,
                    "live_return": ret_live,
                    "slippage_cost": slippage_cost,
                    "latency_cost": latency_cost,
                }
            }
            
            if decision.signal != Signal.HOLD:
                trace("SIMULATOR", "TRADE_EXECUTED", f"Strategy generated {decision.signal.name} signal", {"symbol": symbol, "signal": decision.signal.name, "price": candle.close})
            
            await websocket.send_json(update)

            if exec_record:
                await websocket.send_json({
                    "type": "execution",
                    "record": {
                        "timestamp": exec_record.timestamp.isoformat(),
                        "symbol": exec_record.symbol,
                        "signal": exec_record.signal.name,
                        "execution_price": exec_record.execution_price,
                        "quantity": exec_record.quantity,
                        "action": "OPEN" if portfolio_live.state.open_positions else "CLOSE",
                        "realized_pnl": portfolio_live.realized_pnls[-1] if (not portfolio_live.state.open_positions and portfolio_live.realized_pnls) else None
                    }
                })
            
        # Calculate final metrics using Live portfolio
        trace("SIMULATOR", "REPLAY_COMPLETED", "Market data stream exhausted. Calculating final performance metrics.")
        logger.info(f"[Simulator] Final Metrics Summary: Realized Trades: {len(portfolio_live.realized_pnls)}, Current Balance: {portfolio_live.state.current_balance:.2f}")
        
        metrics = MetricsCalculator.calculate(
            initial_balance=10000.0,
            final_balance=portfolio_live.state.current_balance,
            equity_curve=equity_live,
            trade_pnls=portfolio_live.realized_pnls
        )
        trace("SIMULATOR", "METRICS_GENERATED", "Performance verification complete.", {"win_rate": metrics.win_rate, "sharpe": metrics.sharpe_ratio})
        final_ret_ideal = ((portfolio_ideal.state.current_balance - 10000.0) / 10000.0) * 100
        final_ret_slip = ((portfolio_slip.state.current_balance - 10000.0) / 10000.0) * 100
        final_ret_live = ((portfolio_live.state.current_balance - 10000.0) / 10000.0) * 100
        final_slippage_cost = final_ret_slip - final_ret_ideal
        final_latency_cost = final_ret_live - final_ret_slip
        final_live_vs_ideal_gap = final_ret_live - final_ret_ideal

        evidence_metrics = {
            **metrics.model_dump(),
            "backtest_return": final_ret_ideal,
            "slippage_adjusted_return": final_ret_slip,
            "live_return": final_ret_live,
            "slippage_cost": final_slippage_cost,
            "latency_cost": final_latency_cost,
            "live_vs_ideal_gap": final_live_vs_ideal_gap,
            "friction_adjusted_pnl": portfolio_live.state.current_balance - 10000.0,
            "final_balance": portfolio_live.state.current_balance,
            "candles_processed": replay_engine.state.candles_processed,
            "total_candles": candle_count,
            "regime": regime_id
        }
        
        from fastapi.encoders import jsonable_encoder
        await websocket.send_json(jsonable_encoder({
            "type": "complete",
            "status": "COMPLETED",
            "metrics": evidence_metrics,
            "trades": [t.model_dump() for t in portfolio_live.trade_logs]
        }))

        
    except WebSocketDisconnect:
        logger.info("Simulator client disconnected.")
    except Exception as e:
        logger.error(f"[Simulator] Replay FAILED: {e}")
        try:
            await websocket.send_json({
                "type": "error", 
                "status": "FAILED",
                "message": str(e)
            })
        except:
            pass
    finally:
        active_session = False
        if not command_task.done():
            command_task.cancel()
        try:
            await websocket.close()
        except:
            pass
