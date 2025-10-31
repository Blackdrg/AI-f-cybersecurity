from abc import ABC, abstractmethod
from typing import Dict, Any, List
import asyncio


class PluginBase(ABC):
    """Base class for all plugins"""

    @property
    @abstractmethod
    def name(self) -> str:
        pass

    @property
    @abstractmethod
    def version(self) -> str:
        pass

    @abstractmethod
    async def initialize(self, config: Dict[str, Any]) -> bool:
        """Initialize the plugin with configuration"""
        pass

    @abstractmethod
    async def shutdown(self):
        """Shutdown the plugin"""
        pass

    @abstractmethod
    async def get_devices(self) -> List[Dict[str, Any]]:
        """Get list of available devices"""
        pass

    @abstractmethod
    async def capture_from_device(self, device_id: str) -> bytes:
        """Capture data from a specific device"""
        pass

    @abstractmethod
    async def process_data(self, data: bytes) -> Dict[str, Any]:
        """Process captured data"""
        pass
