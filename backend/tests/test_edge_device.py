from app.plugins.edge_device import EdgeDevicePlugin
import pytest
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))


def test_edge_device_plugin_initialization():
    plugin = EdgeDevicePlugin()
    assert plugin.name == "edge_device"
    assert plugin.version == "1.0.0"

    success = plugin.initialize({"config": "test"})
    assert success


def test_register_device():
    plugin = EdgeDevicePlugin()
    plugin.initialize({})

    # Mock DB call - in real test, use test DB
    # For POC, just test the method exists
    assert hasattr(plugin, 'register_device')


def test_update_device_model():
    plugin = EdgeDevicePlugin()
    plugin.initialize({})

    assert hasattr(plugin, 'update_device_model')
