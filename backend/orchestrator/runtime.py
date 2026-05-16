import asyncio
import logging
from typing import List, Optional
from datetime import datetime
from orchestrator.context import SharedContext, TraceEvent
from orchestrator.agents.base import BaseAgent
from orchestrator.agents.regime_agent import RegimeClassifierAgent
from orchestrator.agents.robustness_agent import RobustnessAgent
from orchestrator.agents.deployment_agent import DeploymentAgent

from orchestrator.notifiers import WorkflowNotifier
import os
from omium.sdk import trace

logger = logging.getLogger("Orchestrator")

class Orchestrator:
    """
    Core runtime for coordinating autonomous agent workflows in Room 3.
    Manages state, execution order, and shared context.
    """
    def __init__(self):
        self.agents: List[BaseAgent] = [
            RegimeClassifierAgent(),
            RobustnessAgent(),
            DeploymentAgent()
        ]
        self.state = "IDLE"
        # In production, these would come from env vars
        self.notifier = WorkflowNotifier(
            slack_url=os.getenv("SLACK_WEBHOOK_URL"),
            webhook_url=os.getenv("GENERIC_WEBHOOK_URL")
        )

    async def execute_workflow(self, context: SharedContext) -> SharedContext:
        """
        Executes the full multi-agent pipeline.
        """
        start_time = datetime.utcnow()
        self.state = "RUNNING"
        context.current_phase = "ORCHESTRATION_START"
        context.traces.append(TraceEvent(
            agent_id="Orchestrator",
            event_type="START",
            stage="Workflow Initiation",
            message="Autonomous evaluation pipeline started.",
            data={"strategy": context.strategy_name}
        ))
        trace("ORCHESTRATOR", "STARTED", f"Autonomous evaluation pipeline initiated for {context.strategy_name}")
        logger.info(f"Starting workflow for strategy: {context.strategy_name}")
        asyncio.create_task(self.notifier.notify_workflow_event("WORKFLOW_START", context))

        for agent in self.agents:
            agent_start = datetime.utcnow()
            context.traces.append(TraceEvent(
                agent_id=agent.agent_id,
                event_type="AGENT_START",
                stage=agent.agent_id,
                message=f"Agent {agent.agent_id} began execution."
            ))
            trace("ORCHESTRATOR", "AGENT_STARTED", f"Agent {agent.agent_id} beginning specialized analysis phase")
            
            success = await self._run_agent_with_retries(agent, context)
            
            duration = (datetime.utcnow() - agent_start).total_seconds() * 1000
            if not success:
                context.traces.append(TraceEvent(
                    agent_id=agent.agent_id,
                    event_type="ERROR",
                    stage=agent.agent_id,
                    message=f"Agent {agent.agent_id} failed after retries.",
                    duration_ms=duration
                ))
                asyncio.create_task(self.notifier.notify_workflow_event("WORKFLOW_FAILED", context))
                logger.error(f"Workflow failed at agent: {agent.agent_id}")
                self.state = "FAILED"
                context.current_phase = f"FAILED_{agent.agent_id.upper()}"
                return context
            
            context.traces.append(TraceEvent(
                agent_id=agent.agent_id,
                event_type="COMPLETE",
                stage=agent.agent_id,
                message=f"Agent {agent.agent_id} completed successfully.",
                duration_ms=duration
            ))
            trace("ORCHESTRATOR", "AGENT_COMPLETED", f"Agent {agent.agent_id} finalized findings.", {"duration_ms": duration})
            asyncio.create_task(self.notifier.notify_workflow_event(f"AGENT_COMPLETE_{agent.agent_id.upper()}", context))

        self.state = "COMPLETED"
        context.current_phase = "COMPLETED"
        total_duration = (datetime.utcnow() - start_time).total_seconds() * 1000
        context.traces.append(TraceEvent(
            agent_id="Orchestrator",
            event_type="FINISH",
            stage="Workflow Completion",
            message=f"Autonomous evaluation finalized. Decision: {context.deployment_decision}",
            duration_ms=total_duration,
            data={"decision": context.deployment_decision}
        ))
        trace("ORCHESTRATOR", "DECISION_GENERATED", f"Autonomous evaluation complete. Final Decision: {context.deployment_decision}", {"decision": context.deployment_decision, "total_duration_ms": total_duration})
        asyncio.create_task(self.notifier.notify_workflow_event("DECISION_GENERATED", context))
        logger.info(f"Workflow completed successfully for {context.strategy_name}. Decision: {context.deployment_decision}")
        return context

    async def _run_agent_with_retries(self, agent: BaseAgent, context: SharedContext, max_retries: int = 2) -> bool:
        """
        Runs a single agent with basic retry logic.
        """
        retries = 0
        while retries <= max_retries:
            try:
                context.current_phase = agent.agent_id.upper()
                logger.info(f"Executing Agent: {agent.agent_id} (Attempt {retries + 1})")
                
                success = await agent.run(context)
                if success:
                    return True
                
                logger.warning(f"Agent {agent.agent_id} reported failure.")
            except Exception as e:
                logger.error(f"Exception in agent {agent.agent_id}: {str(e)}", exc_info=True)
            
            retries += 1
            if retries <= max_retries:
                wait_time = 2 ** retries
                logger.info(f"Retrying agent {agent.agent_id} in {wait_time}s...")
                await asyncio.sleep(wait_time)

        return False
