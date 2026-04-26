from fastapi import APIRouter, Depends, HTTPException
from typing import List, Dict, Any
from ..plugins.loader import plugin_loader
from ..security import require_auth, require_admin

router = APIRouter(prefix="/plugins", tags=["plugins"])

@router.get("/")
async def list_plugins(user: dict = Depends(require_auth)):
    """List all available plugins."""
    return {
        "success": True,
        "data": plugin_loader.list_plugins(),
        "error": None
    }

@router.get("/{plugin_name}")
async def get_plugin_details(plugin_name: str, user: dict = Depends(require_auth)):
    """Get plugin details."""
    plugin = plugin_loader.get_plugin(plugin_name)
    if not plugin:
        raise HTTPException(status_code=404, detail="Plugin not found or not enabled")
    return {
        "success": True,
        "data": {
            "name": plugin.name,
            "version": plugin.version,
            "enabled": True
        },
        "error": None
    }

@router.post("/{plugin_name}/enable")
async def enable_plugin(
    plugin_name: str,
    config: Dict[str, Any] = {},
    user: dict = Depends(require_admin)
):
    """Enable a plugin."""
    success = await plugin_loader.enable_plugin(plugin_name, config)
    if not success:
        raise HTTPException(status_code=400, detail="Failed to enable plugin")
    return {"success": True, "data": {"enabled": True}, "error": None}

@router.delete("/{plugin_name}/disable")
async def disable_plugin(plugin_name: str, user: dict = Depends(require_admin)):
    """Disable a plugin."""
    await plugin_loader.disable_plugin(plugin_name)
    return {"success": True, "data": {"enabled": False}, "error": None}

@router.get("/{plugin_name}/devices")
async def list_plugin_devices(plugin_name: str, user: dict = Depends(require_auth)):
    """List devices available from a plugin."""
    plugin = plugin_loader.get_plugin(plugin_name)
    if not plugin:
        raise HTTPException(status_code=404, detail="Plugin not found or not enabled")
    devices = await plugin.get_devices()
    return {
        "success": True,
        "data": devices,
        "error": None
    }
