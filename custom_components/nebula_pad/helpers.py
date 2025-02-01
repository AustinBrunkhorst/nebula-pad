"""Helper functions for Creality Nebula Pad integration."""
import re
from typing import Optional

def parse_version_info(version_string: str) -> Optional[str]:
    """Parse software version from version string.
    
    Expected format: "printer hw ver:;printer sw ver:1.2.3;DWIN hw ver:NEBULA;DWIN sw ver:V1.1.0.27;"
    Returns the printer software version if found.
    """
    # Look for printer sw ver: followed by anything up to a semicolon
    match = re.search(r"printer sw ver:([^;]+)", version_string)
    if match and match.group(1).strip():
        return match.group(1).strip()
        
    # Fallback to DWIN sw ver if printer sw ver not found
    match = re.search(r"DWIN sw ver:([^;]+)", version_string)
    if match and match.group(1).strip():
        return match.group(1).strip()
        
    return None

def get_device_info(data: dict, host: str) -> dict:
    """Get device info from initial message.
    
    Args:
        data: Dictionary containing device information (hostname, model, modelVersion)
        host: IP address or hostname of the device
        
    Returns:
        Dictionary containing device information for Home Assistant device registry
    """
    model = data.get("model", "Unknown Model")
    hostname = data.get("hostname")
    
    # Use hostname from device if available, otherwise create default name
    if not hostname or hostname.strip() == "":
        hostname = f"Nebula Pad {host}"
    
    version = None
    if model_version := data.get("modelVersion"):
        version = parse_version_info(model_version)
    
    return {
        "name": hostname,
        "model": model,
        "sw_version": version,
        "manufacturer": "Creality",
        "connections": {("ip", host)},  # Add network connection information
    }