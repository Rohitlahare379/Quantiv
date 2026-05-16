import asyncio
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
sys.path.insert(0, str(BACKEND))

from orchestrator.agents.deployment_agent import DeploymentAgent
from orchestrator.agents.robustness_agent import RobustnessAgent
from orchestrator.context import SharedContext


BASE_CONTEXT = {
    "strategy_name": "Evidence Verification RSI",
    "strategy_code": "class RSIAgent: pass # rsi",
    "asset": "BTCUSDT",
    "timeframe": "1h",
    "parameters": {"period": 14, "oversold": 30, "overbought": 70},
    "regime_analysis": {"regime": "CALM", "suitability_score": 85},
}


CASES = [
    {
        "name": "excellent replay should deploy",
        "expected": "DEPLOY",
        "replay_metrics": {
            "live_return": 40.0,
            "backtest_return": 45.0,
            "slippage_cost": -2.0,
            "latency_cost": -3.0,
            "live_vs_ideal_gap": -5.0,
            "trade_count": 50,
            "max_drawdown": 4.0,
            "sharpe_ratio": 2.4,
            "win_rate": 68.0,
        },
    },
    {
        "name": "catastrophic replay should reject",
        "expected": "REJECT",
        "replay_metrics": {
            "live_return": -80.0,
            "backtest_return": 20.0,
            "slippage_cost": -40.0,
            "latency_cost": -60.0,
            "live_vs_ideal_gap": -100.0,
            "trade_count": 2,
            "max_drawdown": 75.0,
            "sharpe_ratio": -3.0,
            "win_rate": 0.0,
        },
    },
    {
        "name": "missing replay should require validation",
        "expected": "VALIDATION_REQUIRED",
        "replay_metrics": {},
    },
]


async def run_case(case: dict) -> bool:
    context = SharedContext(**BASE_CONTEXT, replay_metrics=case["replay_metrics"])

    await RobustnessAgent().run(context)
    await DeploymentAgent().run(context)

    passed = context.deployment_decision == case["expected"]
    status = "PASS" if passed else "FAIL"
    print(f"[{status}] {case['name']}")
    print(f"       expected={case['expected']} actual={context.deployment_decision}")
    print(f"       robustness={context.robustness_results.get('robustness_score') if context.robustness_results else None}")
    print(f"       reasoning={context.decision_reasoning}")
    return passed


async def main() -> int:
    results = [await run_case(case) for case in CASES]
    if not all(results):
        return 1

    print("[PASS] Room 2 -> Room 3 evidence decision gates are sensitive to replay metrics")
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
