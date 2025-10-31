import aiohttp
import json
import asyncio
from typing import Dict, Any, List
from .db.db_client import get_db
import logging

logger = logging.getLogger(__name__)


class WebhookManager:
    def __init__(self):
        self.session = None

    async def init(self):
        self.session = aiohttp.ClientSession()

    async def close(self):
        if self.session:
            await self.session.close()

    async def trigger_webhook(self, webhook_url: str, event: str, data: Dict[str, Any]):
        if not self.session:
            await self.init()

        payload = {
            "event": event,
            "timestamp": asyncio.get_event_loop().time(),
            "data": data
        }

        try:
            async with self.session.post(webhook_url, json=payload, timeout=5) as resp:
                if resp.status == 200:
                    logger.info(
                        f"Webhook triggered successfully: {webhook_url}")
                else:
                    logger.error(
                        f"Webhook failed: {webhook_url}, status: {resp.status}")
        except Exception as e:
            logger.error(f"Webhook error: {webhook_url}, error: {str(e)}")

    async def trigger_event(self, event: str, data: Dict[str, Any]):
        db = await get_db()
        # Fetch webhooks from DB (placeholder)
        webhooks = []  # await db.get_webhooks_for_event(event)

        tasks = [self.trigger_webhook(wh['url'], event, data)
                 for wh in webhooks]
        await asyncio.gather(*tasks, return_exceptions=True)


# Global instance
webhook_manager = WebhookManager()


async def init_webhooks():
    await webhook_manager.init()


async def close_webhooks():
    await webhook_manager.close()


async def trigger_webhook_event(event: str, data: Dict[str, Any]):
    await webhook_manager.trigger_event(event, data)
