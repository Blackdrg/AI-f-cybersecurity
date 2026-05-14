import importlib
import pkgutil
import sys
from pathlib import Path
from typing import Dict, Any, List
from .base import PluginBase
import logging

logger = logging.getLogger(__name__)


class PluginLoader:
    def __init__(self):
        self.plugins: Dict[str, PluginBase] = {}
        self.enabled_plugins: Dict[str, PluginBase] = {}
        self._plugins_path = Path(__file__).parent

    def discover_plugins(self):
        """Discover plugins in the plugins directory"""
        plugin_files = list(self._plugins_path.glob("*.py"))
        for plugin_file in plugin_files:
            modname = plugin_file.stem
            if modname != 'base' and modname != 'loader' and modname != '__init__':
                try:
                    module = importlib.import_module(
                        f"app.plugins.{modname}")
                    if hasattr(module, 'Plugin'):
                        plugin_class = getattr(module, 'Plugin')
                        if issubclass(plugin_class, PluginBase):
                            plugin_instance = plugin_class()
                            self.plugins[plugin_instance.name] = plugin_instance
                            logger.info(
                                f"Discovered plugin: {plugin_instance.name}")
                except Exception as e:
                    logger.error(f"Failed to load plugin {modname}: {str(e)}")

    async def enable_plugin(self, plugin_name: str, config: Dict[str, Any]) -> bool:
        if plugin_name not in self.plugins:
            return False

        plugin = self.plugins[plugin_name]
        if await plugin.initialize(config):
            self.enabled_plugins[plugin_name] = plugin
            logger.info(f"Enabled plugin: {plugin_name}")
            return True
        return False

    async def disable_plugin(self, plugin_name: str):
        if plugin_name in self.enabled_plugins:
            await self.enabled_plugins[plugin_name].shutdown()
            del self.enabled_plugins[plugin_name]
            logger.info(f"Disabled plugin: {plugin_name}")

    def get_plugin(self, plugin_name: str) -> PluginBase:
        return self.enabled_plugins.get(plugin_name)

    def list_plugins(self) -> List[Dict[str, Any]]:
        return [
            {
                "name": name,
                "version": plugin.version,
                "enabled": name in self.enabled_plugins
            }
            for name, plugin in self.plugins.items()
        ]


# Global instance
plugin_loader = PluginLoader()
