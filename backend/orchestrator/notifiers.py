import json
import logging
import httpx
import asyncio
from typing import Dict, Any, Optional
from datetime import datetime
from omium.sdk import trace

logger = logging.getLogger("WorkflowNotifier")

class WorkflowNotifier:
    """
    Handles external side effects for the Quantive Orchestrator.
    Supports Slack and generic Webhooks with basic retry logic.
    """
    def __init__(self, slack_url: Optional[str] = None, webhook_url: Optional[str] = None):
        self.slack_url = slack_url
        self.webhook_url = webhook_url

    async def notify_workflow_event(self, event_type: str, context: Any):
        """
        Dispatches notifications based on the event type.
        """
        tasks = []
        
        # Prepare payload
        payload = self._prepare_payload(event_type, context)
        
        if self.slack_url:
            tasks.append(self._send_slack_with_retry(payload))
            
        if self.webhook_url:
            tasks.append(self._send_webhook_with_retry(payload))
            
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)

    def _prepare_payload(self, event_type: str, context: Any) -> Dict[str, Any]:
        return {
            "event_type": event_type,
            "timestamp": datetime.utcnow().isoformat(),
            "strategy": {
                "name": context.strategy_name,
                "asset": context.asset,
                "timeframe": context.timeframe
            },
            "status": context.current_phase,
            "results": {
                "robustness_score": context.robustness_results.get("robustness_score") if context.robustness_results else None,
                "deployment_decision": context.deployment_decision,
                "reasoning": context.decision_reasoning
            }
        }

    async def _send_slack_with_retry(self, payload: Dict[str, Any], max_retries: int = 3):
        if not self.slack_url: return
        
        # Format Slack block message
        color = "#36a64f" if payload["results"]["deployment_decision"] == "DEPLOY" else "#ff0000"
        slack_payload = {
            "attachments": [
                {
                    "color": color,
                    "title": f"Quantive Workflow: {payload['event_type']}",
                    "text": f"*Strategy:* {payload['strategy']['name']}\n*Asset:* {payload['strategy']['asset']}\n*Decision:* {payload['results']['deployment_decision'] or 'PENDING'}\n*Reasoning:* {payload['results']['reasoning'] or 'N/A'}",
                    "footer": "Quantive Autonomous System"
                }
            ]
        }

        await self._do_post_with_retry("Slack", self.slack_url, slack_payload, max_retries)
        trace("SIDE_EFFECTS", "SLACK_NOTIFICATION_SENT", "Workflow event dispatched to Slack workspace")

    async def _send_webhook_with_retry(self, payload: Dict[str, Any], max_retries: int = 3):
        if not self.webhook_url: return
        await self._do_post_with_retry("Generic Webhook", self.webhook_url, payload, max_retries)
        trace("SIDE_EFFECTS", "WEBHOOK_FIRED", "Operational data transmitted via generic webhook")

    async def _do_post_with_retry(self, name: str, url: str, payload: Dict[str, Any], max_retries: int):
        retries = 0
        while retries < max_retries:
            try:
                async with httpx.AsyncClient(timeout=5.0) as client:
                    logger.info(f"Dispatching {name} notification (Attempt {retries + 1})...")
                    res = await client.post(url, json=payload)
                    if res.status_code < 300:
                        logger.info(f"{name} notification sent successfully.")
                        return True
                    else:
                        logger.warning(f"{name} failed with status {res.status_code}.")
            except Exception as e:
                logger.error(f"Error sending {name} notification: {str(e)}")
            
            retries += 1
            if retries < max_retries:
                await asyncio.sleep(2 ** retries)
        
        logger.error(f"All {max_retries} attempts to send {name} notification failed.")
        return False
