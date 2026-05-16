# Quantive: AI-Native Autonomous Quant Strategy Orchestrator

**Quantive** is an end-to-end autonomous pipeline for high-fidelity quantitative strategy evaluation. It bridges the gap between idealistic backtests and live market reality using a **Multi-Agent "Judge" Architecture** and **Storm Simulation** infrastructure.

Built for the **2026 Autonomous Quant Hackathon — Sponsored Track (Problem 03/04).**

---

## 🏗 Multi-Agent Autonomy
Quantive replaces human steering with a specialized multi-agent workflow. The system doesn't just calculate metrics; it applies **deep reasoning** to determine strategy suitability.

*   **Regime Classifier Agent**: Analyzes market conditions (Volatility, Trend) and historical dataset integrity via Binance APIs.
*   **Robustness Agent**: Stress-tests strategies by comparing "Ideal" returns against "Live" returns with simulated slippage and 1-candle latency.
*   **Deployment Agent**: Synthesizes agent findings into a final **DEPLOY / REJECT** verdict with a verifiable reasoning trace.

---

## 🛠 Features by "Room"

### Room 1: Strategy Engineering (Workshop)
*   **Deterministic Persistence**: Strategies are reliably saved and synchronized across the workspace.
*   **Dynamic Validation**: Real-time Python code loading and dry-run validation against live market data.
*   **Strategy Templates**: Jumpstart development with RSI, Momentum, and Mean Reversion patterns.

### Room 2: Storm Simulator (Replay)
*   **Custom Data Layers**: Select specific historical ranges (e.g., COVID Crash, FTX Collapse) or set custom dates.
*   **On-Demand Ingestion**: Automatically fetches missing historical data directly from **Binance** via async background workers.
*   **Friction Modeling**: Live streaming of "Storm Metrics" — accounting for exchange-grade slippage and execution latency.

### Room 3: Autonomous Evaluation (Orchestrator)
*   **Omium SDK Tracing**: Every meaningful action is instrumented with **verifiable causal traces** for judge auditability.
*   **Intelligent Reporting**: Generates exhaustive **Operational Intelligence Reports** (PDF/JSON).
*   **Async Side Effects**: Integrated Slack notifications, SMTP email delivery, and generic webhook dispatches.

---

## ⚡ Quick Start

### 1. Prerequisites
- Python 3.9+
- Node.js 18+
- Binance API Key (for on-demand historical data)

### 2. Installation

**Backend:**
```bash
cd backend
python3 -m pip install -r requirements.txt
python3 main.py # Initializes database and checks connectivity
```

**Frontend:**
```bash
cd frontend
npm install
npm run dev
```

### 3. Environment Configuration
Create `backend/.env`:
```env
DATABASE_URL=sqlite:///./quantive.db
BINANCE_API_KEY=your_key
BINANCE_API_SECRET=your_secret
SLACK_WEBHOOK_URL=your_slack_webhook
```

---

## 📈 Tech Stack
- **Backend**: FastAPI (Python), SQLAlchemy, Pydantic, WebSocket (Live Streaming).
- **Frontend**: React (Vite), Tailwind CSS, Lucide Icons, Recharts (Real-time Equity Curve).
- **Data**: Binance REST/WS API for historical and live data.
- **Observability**: **Omium SDK v1** for causal workflow tracing.

---

## 🛡 Verifiability & Omium Tracing
Quantive is fully instrumented for the **Bonus Trace Track**. Every execution produces a trace on the Omium dashboard (instrumented via `⚡ [OMIUM-v1]` logs). 
- **Causal Linking**: Each agent step is parented to the orchestrator start.
- **Complete Coverage**: Tracing includes validation, simulation, trade execution, and external side effects.

---
*Built with ❤️ for the future of Autonomous Finance.*
