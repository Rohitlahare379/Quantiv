# Quantive Room 2: Simulator Architecture

## Overview
The Simulator (Room 2) is designed to backtest user-defined strategies against historical market data. To ensure determinism, safety, and maintainability, the simulation architecture is heavily decoupled into isolated responsibilities.

## Directory Structure & Responsibilities

- **`interfaces/`**: Defines strict contracts (e.g., the `Strategy` abstract base class) that all user-submitted code must adhere to. This prevents arbitrary execution and ensures uniform `on_candle` behavior.
- **`signals/`**: Contains deterministic enums like `Signal.BUY`, `Signal.SELL`, and `Signal.HOLD`. Strategies are only allowed to communicate via these standard signals, replacing arbitrary string returns.
- **`models/`**: Clean Pydantic data models for state management. This includes `PortfolioState`, `OpenPosition`, `TradeRecord`, and the overarching `SimulationState`. By isolating state here, we prevent shared mutable chaos during a replay.
- **`loaders/`**: The `StrategyLoader` safely pulls Python code strings from PostgreSQL, constructs a restricted execution namespace (limiting `exec()`), and injects standard dependencies before returning a valid `Strategy` class instance.
- **`replay/`**: (To be implemented) The engine responsible for fetching historical `NormalizedCandle` data from the Market Data Layer and iteratively feeding it to the strategy to simulate the passage of time.
- **`execution/`**: (To be implemented) Simulates order fills, slippage, and fee calculations when a strategy emits a trading signal.
- **`portfolio/`**: (To be implemented) Manages the ledger, translating execution engine fills into updated balances and open positions inside the `PortfolioState`.
- **`metrics/`**: (To be implemented) Post-processes `TradeRecord` lists to calculate performance indicators (Sharpe ratio, max drawdown, win rate).

## Separation of Concerns

1. **Market Data Layer Independence:** 
   The simulator does not fetch raw Binance data. It strictly consumes `NormalizedCandle` objects. This decouples the simulation logic from any specific crypto exchange API.
   
2. **Strategy Loading vs. Strategy Logic:**
   The `loaders/` module is solely responsible for getting the strategy ready to run. It does not execute the strategy's core logic. The user's code acts as a pure function mapping a `NormalizedCandle` to a `Signal`.

3. **Execution vs. State:**
   The Strategy does not hold its own balance or position details. It emits a Signal. The `execution` and `portfolio` modules determine if the user has enough balance to actually execute that Signal.

## The Strategy Lifecycle

1. **Load:** The user requests a backtest for `Strategy ID 5`. The `StrategyLoader` fetches the code, verifies it implements `Strategy`, and instantiates it.
2. **Setup:** A fresh `SimulationState` and `PortfolioState` are initialized.
3. **Replay Loop:** The `replay` engine iterates through historical `NormalizedCandle` data chronologically.
4. **Tick:** For each candle, `strategy.on_candle(candle)` is called.
5. **Signal Evaluation:** If a `BUY` or `SELL` signal is returned, it is passed to the `execution` engine.
6. **State Update:** The `execution` engine verifies funds and modifies the `PortfolioState`, logging a `TradeRecord` if a position is opened or closed.
7. **Finalization:** Once all candles are processed, `metrics` calculates the performance, and the final state is returned to the frontend.
