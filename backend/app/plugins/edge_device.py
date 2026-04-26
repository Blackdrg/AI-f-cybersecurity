from .base import PluginBase
from typing import Dict, Any, List
import asyncio
import aiohttp
from ..db.db_client import get_db


class EdgeDevicePlugin(PluginBase):
    """Plugin for edge device integration"""

    @property
    def name(self) -> str:
        return "edge_device"

    @property
    def version(self) -> str:
        return "1.0.0"

    async def initialize(self, config: Dict[str, Any]) -> bool:
        self.config = config
        self.devices = {}  # device_id: {'url': str, 'status': str}
        return True

    async def shutdown(self):
        pass

    async def get_devices(self) -> List[Dict[str, Any]]:
        db = await get_db()
        devices = await db.fetch("SELECT device_id, model_version, last_seen, status FROM edge_devices")
        return [dict(d) for d in devices]

    async def capture_from_device(self, device_id: str) -> bytes:
        if device_id not in self.devices:
            raise ValueError(f"Device {device_id} not registered")
        device_url = self.devices[device_id]['url']
        async with aiohttp.ClientSession() as session:
            async with session.get(f"{device_url}/capture") as resp:
                return await resp.read()

    async def process_data(self, data: bytes) -> Dict[str, Any]:
        # Process on-device recognition result
        # Assume data is JSON with recognition results
        import json
        result = json.loads(data.decode())
        return result

    async def register_device(self, device_id: str, url: str):
        self.devices[device_id] = {'url': url, 'status': 'active'}
        db = await get_db()
        await db.execute("""
            INSERT INTO edge_devices (device_id, status)
            VALUES ($1, $2)
            ON CONFLICT (device_id) DO UPDATE SET status = $2, last_seen = NOW()
        """, device_id, 'active')

    async def update_device_model(self, device_id: str, model_version: str):
        db = await get_db()
        await db.execute("""
            UPDATE edge_devices SET model_version = $1, last_seen = NOW()
            WHERE device_id = $2
        """, model_version, device_id)


Plugin = EdgeDevicePlugin
