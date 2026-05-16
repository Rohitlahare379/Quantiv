from orchestrator.agents.base import BaseAgent
from orchestrator.context import SharedContext
import asyncio


class DeploymentAgent(BaseAgent):
    def __init__(self):
        super().__init__("DeploymentDecision")

    async def run(self, context: SharedContext) -> bool:
        self.log_event(context, "Synthesizing replay evidence, regime fit, and robustness for deployment decision...")

        if not context.regime_analysis or not context.robustness_results:
            self.log_event(context, "Error: Missing upstream agent data.")
            context.deployment_decision = "REJECT"
            context.decision_reasoning = "Insufficient regime or robustness data for deployment."
            return False

        await asyncio.sleep(0.2)

        replay = context.replay_metrics or {}
        missing = [
            key for key in [
                "live_return",
                "max_drawdown",
                "sharpe_ratio",
                "win_rate",
                "trade_count",
                "live_vs_ideal_gap",
            ]
            if key not in replay
        ]

        suitability = _number(context.regime_analysis.get("suitability_score"))
        robustness = _number(context.robustness_results.get("robustness_score"))
        live_return = _number(replay.get("live_return"))
        max_drawdown = _number(replay.get("max_drawdown"))
        sharpe_ratio = _number(replay.get("sharpe_ratio"))
        win_rate = _number(replay.get("win_rate"))
        trade_count = int(_number(replay.get("trade_count")))
        live_gap = _number(replay.get("live_vs_ideal_gap"))
        slippage_cost = _number(replay.get("slippage_cost"))
        latency_cost = _number(replay.get("latency_cost"))

        hard_blocks = []
        validation_flags = []

        if missing:
            validation_flags.append(f"missing replay fields: {', '.join(missing)}")
        if live_return < 0:
            hard_blocks.append(f"negative live return ({live_return:.2f}%)")
        if sharpe_ratio < 0:
            hard_blocks.append(f"negative Sharpe ({sharpe_ratio:.2f})")
        if max_drawdown > 40:
            hard_blocks.append(f"excessive drawdown ({max_drawdown:.2f}%)")
        if live_gap < -20:
            hard_blocks.append(f"severe live-vs-ideal degradation ({live_gap:.2f}%)")
        if trade_count < 3:
            validation_flags.append(f"insufficient trade sample ({trade_count} trades)")
        if max_drawdown > 25:
            validation_flags.append(f"elevated drawdown ({max_drawdown:.2f}%)")
        if sharpe_ratio < 0.5:
            validation_flags.append(f"weak Sharpe ({sharpe_ratio:.2f})")
        if win_rate < 40:
            validation_flags.append(f"low win rate ({win_rate:.2f}%)")
        if live_gap < -8:
            validation_flags.append(f"material friction drag ({live_gap:.2f}%)")
        if suitability < 50:
            validation_flags.append(f"low regime suitability ({suitability:.0f}/100)")
        if robustness < 60:
            validation_flags.append(f"low robustness ({robustness:.0f}/100)")

        if hard_blocks:
            context.deployment_decision = "REJECT"
            decision_basis = "Rejected because " + "; ".join(hard_blocks)
        elif validation_flags or suitability < 70 or robustness < 75:
            context.deployment_decision = "VALIDATION_REQUIRED"
            decision_basis = "Requires more validation because " + "; ".join(validation_flags or [
                f"regime suitability {suitability:.0f}/100 and robustness {robustness:.0f}/100 are below deploy thresholds"
            ])
        else:
            context.deployment_decision = "DEPLOY"
            decision_basis = (
                f"Deployment allowed: live return {live_return:.2f}%, drawdown {max_drawdown:.2f}%, "
                f"Sharpe {sharpe_ratio:.2f}, win rate {win_rate:.2f}%, {trade_count} trades, "
                f"regime suitability {suitability:.0f}/100, robustness {robustness:.0f}/100."
            )

        context.decision_reasoning = (
            f"{decision_basis} Replay evidence: live-vs-ideal gap {live_gap:.2f}%, "
            f"slippage impact {slippage_cost:.2f}%, latency degradation {latency_cost:.2f}%."
        )

        self.log_event(context, f"Decision: {context.deployment_decision}. {context.decision_reasoning}")
        return True


def _number(value, default=0.0):
    try:
        return float(value)
    except (TypeError, ValueError):
        return default
