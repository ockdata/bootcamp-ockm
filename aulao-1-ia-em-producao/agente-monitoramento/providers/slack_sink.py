"""Slack webhook alert sink."""

from __future__ import annotations

import httpx

from observability.logger import get_logger
from schemas.alerts import Alert

log = get_logger(__name__)


class SlackSink:
    """Sends alerts to Slack via incoming webhook. Implements AlertSink protocol."""

    def __init__(self, webhook_url: str) -> None:
        self.webhook_url = webhook_url

    async def send(self, alert: Alert) -> bool:
        recs = "\n".join(f"• {r}" for r in alert.recommendations) if alert.recommendations else "Nenhuma"

        blocks = [
            {
                "type": "header",
                "text": {
                    "type": "plain_text",
                    "text": f"🚨 {alert.title}",
                },
            },
            {
                "type": "section",
                "fields": [
                    {"type": "mrkdwn", "text": f"*Serviço:*\n{alert.service}"},
                    {"type": "mrkdwn", "text": f"*Severidade:*\n{alert.severity.upper()}"},
                    {"type": "mrkdwn", "text": f"*Risk Score:*\n{alert.risk_score}/100 ({alert.risk_level})"},
                    {"type": "mrkdwn", "text": f"*Event ID:*\n`{alert.event_id[:8]}...`"},
                ],
            },
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"*Resumo:*\n{alert.summary}",
                },
            },
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"*Causa Raiz:*\n{alert.root_cause}",
                },
            },
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"*Recomendações:*\n{recs}",
                },
            },
        ]

        payload = {"blocks": blocks}

        try:
            async with httpx.AsyncClient() as client:
                resp = await client.post(
                    self.webhook_url,
                    json=payload,
                    timeout=10.0,
                )
                resp.raise_for_status()
                log.info("slack.send.success", alert_id=alert.alert_id)
                return True
        except Exception as e:
            log.error("slack.send.failed", alert_id=alert.alert_id, error=str(e))
            return False
