from orchestrator.agents.base import BaseAgent
from orchestrator.context import SharedContext
import asyncio


class RobustnessAgent(BaseAgent):
    def __init__(self):
        super().__init__("RobustnessTester")

    async def run(self, context: SharedContext) -> bool:
        self.log_event(context, "Evaluating robustness from replay evidence...")
        await asyncio.sleep(0.2)

        replay = context.replay_metrics or {}
        required = [
            "live_return",
            "max_drawdown",
            "sharpe_ratio",
            "win_rate",
            "trade_count",
            "live_vs_ideal_gap",
        ]
        missing = [key for key in required if key not in replay]

        if missing:
            context.robustness_results = {
                "robustness_score": 0,
                "sharpe_stability": "Unknown",
                "max_drawdown_consistency": "Unknown",
                "overfitting_risk": "Unknown",
                "friction_sensitivity": "Unknown",
                "evidence_quality": "Insufficient",
                "missing_replay_fields": missing,
                "reasoning": f"Replay evidence is incomplete. Missing: {', '.join(missing)}."
            }
            self.log_event(context, f"Replay evidence incomplete: {', '.join(missing)}")
            return True

        live_return = _number(replay.get("live_return"))
        max_drawdown = _number(replay.get("max_drawdown"))
        sharpe_ratio = _number(replay.get("sharpe_ratio"))
        win_rate = _number(replay.get("win_rate"))
        trade_count = int(_number(replay.get("trade_count")))
        live_gap = _number(replay.get("live_vs_ideal_gap"))

        score = 100
        score -= _penalty(live_return < 0, 30)
        score -= _penalty(sharpe_ratio < 0, 25)
        score -= _penalty(sharpe_ratio < 0.5, 12)
        score -= _penalty(max_drawdown > 35, 25)
        score -= _penalty(max_drawdown > 20, 10)
        score -= _penalty(win_rate < 40, 10)
        score -= _penalty(trade_count < 5, 15)
        score -= _penalty(live_gap < -15, 20)
        score -= _penalty(live_gap < -5, 8)
        score = max(0, min(100, score))

        robustness_data = {
            "sharpe_stability": _grade_sharpe(sharpe_ratio),
            "max_drawdown_consistency": _grade_drawdown(max_drawdown),
            "overfitting_risk": _grade_overfit(trade_count, win_rate, sharpe_ratio),
            "friction_sensitivity": _grade_friction(live_gap),
            "robustness_score": score,
            "evidence_quality": "Replay-backed",
            "replay_evidence": {
                "live_return": live_return,
                "max_drawdown": max_drawdown,
                "sharpe_ratio": sharpe_ratio,
                "win_rate": win_rate,
                "trade_count": trade_count,
                "live_vs_ideal_gap": live_gap,
                "slippage_cost": _number(replay.get("slippage_cost")),
                "latency_cost": _number(replay.get("latency_cost")),
            },
            "reasoning": (
                f"Replay-backed robustness score {score}/100 from live return {live_return:.2f}%, "
                f"drawdown {max_drawdown:.2f}%, Sharpe {sharpe_ratio:.2f}, "
                f"win rate {win_rate:.2f}%, {trade_count} trades, and live-vs-ideal gap {live_gap:.2f}%."
            )
        }

        context.robustness_results = robustness_data
        self.log_event(context, robustness_data["reasoning"])
        return True


def _number(value, default=0.0):
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _penalty(condition: bool, points: int) -> int:
    return points if condition else 0


def _grade_sharpe(sharpe: float) -> str:
    if sharpe >= 1.5:
        return "Strong"
    if sharpe >= 0.5:
        return "Acceptable"
    if sharpe >= 0:
        return "Weak"
    return "Negative"


def _grade_drawdown(drawdown: float) -> str:
    if drawdown <= 10:
        return "Stable"
    if drawdown <= 25:
        return "Moderate"
    return "Unstable"


def _grade_overfit(trade_count: int, win_rate: float, sharpe: float) -> str:
    if trade_count < 5:
        return "High"
    if win_rate > 80 and trade_count < 20:
        return "Elevated"
    if sharpe < 0:
        return "High"
    return "Low"


def _grade_friction(live_gap: float) -> str:
    if live_gap <= -15:
        return "Severe"
    if live_gap <= -5:
        return "Moderate"
    return "Low"
