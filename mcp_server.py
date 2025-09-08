#!/usr/bin/env python3
"""
Owlet Baby Monitor MCP Server

A comprehensive Model Context Protocol server for monitoring Owlet baby devices.
Provides real-time vitals monitoring, alerts management, device status, and media access.
"""

import asyncio
import json
import logging
import os
import sys
from typing import Any, Dict, List, Optional
from datetime import datetime, timedelta

# Try to load environment variables from .env file
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    # dotenv not available, use environment variables directly
    pass

from mcp.server.fastmcp import FastMCP
from src.pyowletapi.api import OwletAPI
from src.pyowletapi.sock import Sock
from src.pyowletapi.exceptions import (
    OwletAuthenticationError,
    OwletConnectionError,
    OwletDevicesError,
    OwletError,
)

# Configure logging to stderr (important for MCP servers)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    stream=sys.stderr
)
logger = logging.getLogger(__name__)

# Initialize FastMCP server
mcp = FastMCP("owlet-monitor")

# Global variables for API and devices
api_client: Optional[OwletAPI] = None
devices: List[Sock] = []


async def get_authenticated_api() -> OwletAPI:
    """Get an authenticated API client."""
    global api_client
    
    if api_client is None:
        # Get credentials from environment variables
        region = os.getenv("OWLET_REGION", "world")
        user = os.getenv("OWLET_USER")
        password = os.getenv("OWLET_PASSWORD")
        
        if not user or not password:
            raise OwletAuthenticationError(
                "Authentication required. Please set OWLET_USER and OWLET_PASSWORD environment variables. "
                "You can create a .env file with your credentials. See README-MCP.md for setup instructions."
            )
        
        logger.info(f"Authenticating with Owlet API for region: {region}")
        api_client = OwletAPI(region=region, user=user, password=password)
        
        try:
            tokens = await api_client.authenticate()
            if tokens:
                logger.info("Successfully authenticated with Owlet API")
            else:
                logger.info("Using existing valid authentication")
        except OwletAuthenticationError as e:
            logger.error(f"Authentication failed: {e}")
            api_client = None
            raise OwletAuthenticationError(
                f"Failed to authenticate with Owlet API: {str(e)}. "
                "Please check your credentials in the environment variables."
            )
        except Exception as e:
            logger.error(f"Unexpected authentication error: {e}")
            api_client = None
            raise OwletAuthenticationError(
                f"Unexpected authentication error: {str(e)}"
            )
    
    return api_client


async def get_devices() -> List[Sock]:
    """Get list of available Owlet devices."""
    global devices
    
    if not devices:
        api = await get_authenticated_api()
        devices_response = await api.get_devices()
        
        devices = []
        for device_data in devices_response["response"]:
            sock = Sock(api, device_data["device"])
            devices.append(sock)
    
    return devices


def format_vitals_data(properties: Dict[str, Any]) -> str:
    """Format vital signs data into readable text."""
    vitals = []
    
    # Core vitals
    if "heart_rate" in properties:
        vitals.append(f"❤️ Heart Rate: {properties['heart_rate']} BPM")
    
    if "oxygen_saturation" in properties:
        vitals.append(f"🫁 Oxygen Saturation: {properties['oxygen_saturation']}%")
    
    if "skin_temperature" in properties:
        # Convert from integer (likely in tenths of degrees)
        temp_c = properties["skin_temperature"] / 10 if properties["skin_temperature"] > 100 else properties["skin_temperature"]
        temp_f = (temp_c * 9/5) + 32
        vitals.append(f"🌡️ Skin Temperature: {temp_c:.1f}°C ({temp_f:.1f}°F)")
    
    # Device status
    if "battery_percentage" in properties:
        vitals.append(f"🔋 Battery: {properties['battery_percentage']}%")
    
    if "signal_strength" in properties:
        vitals.append(f"📶 Signal Strength: {properties['signal_strength']} dBm")
    
    # Sleep and movement
    if "sleep_state" in properties:
        sleep_states = {0: "Awake", 1: "Light Sleep", 2: "Deep Sleep"}
        state = sleep_states.get(properties["sleep_state"], "Unknown")
        vitals.append(f"😴 Sleep State: {state}")
    
    if "movement" in properties:
        vitals.append(f"🏃 Movement Level: {properties['movement']}")
    
    # Charging status
    if "charging" in properties:
        charging_status = "Charging" if properties["charging"] else "Not Charging"
        vitals.append(f"⚡ Charging: {charging_status}")
    
    # Last updated
    if "last_updated" in properties:
        vitals.append(f"🕐 Last Updated: {properties['last_updated']}")
    
    return "\n".join(vitals) if vitals else "No vital signs data available"


def format_alerts_data(properties: Dict[str, Any]) -> str:
    """Format alerts data into readable text."""
    alerts = []
    
    # Critical alerts
    if properties.get("critical_oxygen_alert"):
        alerts.append("🚨 CRITICAL: Low Oxygen Alert")
    
    if properties.get("critical_battery_alert"):
        alerts.append("🚨 CRITICAL: Critical Battery Alert")
    
    # Standard alerts
    if properties.get("low_oxygen_alert"):
        alerts.append("⚠️ Low Oxygen Alert")
    
    if properties.get("high_oxygen_alert"):
        alerts.append("⚠️ High Oxygen Alert")
    
    if properties.get("low_heart_rate_alert"):
        alerts.append("⚠️ Low Heart Rate Alert")
    
    if properties.get("high_heart_rate_alert"):
        alerts.append("⚠️ High Heart Rate Alert")
    
    if properties.get("low_battery_alert"):
        alerts.append("🔋 Low Battery Alert")
    
    if properties.get("lost_power_alert"):
        alerts.append("⚡ Lost Power Alert")
    
    if properties.get("sock_disconnected"):
        alerts.append("📱 Sock Disconnected Alert")
    
    if properties.get("sock_off"):
        alerts.append("🧦 Sock Off Alert")
    
    # Wellness alerts
    if properties.get("wellness_alert"):
        alerts.append("💚 Wellness Alert")
    
    # Firmware updates
    if properties.get("firmware_update_available"):
        alerts.append("📱 Firmware Update Available")
    
    if not alerts:
        return "✅ No active alerts - Baby is being monitored normally"
    
    return "\n".join(alerts)


@mcp.tool()
async def get_device_list() -> str:
    """Get a list of all available Owlet devices.
    
    Returns:
        str: Formatted list of devices with their basic information
    """
    try:
        devices = await get_devices()
        
        if not devices:
            return "No Owlet devices found in your account."
        
        device_info = []
        for i, device in enumerate(devices, 1):
            info = [
                f"Device {i}: {device.name}",
                f"  Serial: {device.serial}",
                f"  Model: {device.model}",
                f"  Connection: {device.connection_status}",
                f"  SW Version: {device.sw_version}",
            ]
            if device.version:
                info.append(f"  Sock Version: {device.version}")
            device_info.append("\n".join(info))
        
        return "\n\n".join(device_info)
    
    except Exception as e:
        logger.error(f"Error getting device list: {e}")
        return f"Error retrieving device list: {str(e)}"


@mcp.tool()
async def get_current_vitals(device_serial: str = "") -> str:
    """Get current vital signs for a baby monitor device.
    
    Args:
        device_serial: Serial number of the device (optional, uses first device if not specified)
    
    Returns:
        str: Current vital signs including heart rate, oxygen saturation, temperature, etc.
    """
    try:
        devices = await get_devices()
        
        if not devices:
            return "No devices found. Please check your Owlet account."
        
        # Select device
        target_device = None
        if device_serial:
            target_device = next((d for d in devices if d.serial == device_serial), None)
            if not target_device:
                return f"Device with serial {device_serial} not found."
        else:
            target_device = devices[0]  # Use first device
        
        # Get current properties
        properties_data = await target_device.update_properties()
        properties = properties_data["properties"]
        
        result = [
            f"📱 Current Vitals for {target_device.name} ({target_device.serial})",
            "=" * 50,
            format_vitals_data(properties)
        ]
        
        return "\n".join(result)
    
    except Exception as e:
        logger.error(f"Error getting vitals: {e}")
        return f"Error retrieving vitals: {str(e)}"


@mcp.tool()
async def get_active_alerts(device_serial: str = "") -> str:
    """Get active alerts for a baby monitor device.
    
    Args:
        device_serial: Serial number of the device (optional, uses first device if not specified)
    
    Returns:
        str: List of active alerts and their status
    """
    try:
        devices = await get_devices()
        
        if not devices:
            return "No devices found. Please check your Owlet account."
        
        # Select device
        target_device = None
        if device_serial:
            target_device = next((d for d in devices if d.serial == device_serial), None)
            if not target_device:
                return f"Device with serial {device_serial} not found."
        else:
            target_device = devices[0]  # Use first device
        
        # Get current properties
        properties_data = await target_device.update_properties()
        properties = properties_data["properties"]
        
        result = [
            f"🚨 Active Alerts for {target_device.name} ({target_device.serial})",
            "=" * 50,
            format_alerts_data(properties)
        ]
        
        # Add alert pause status
        if properties.get("alert_paused_status"):
            result.append("\n⏸️ Note: Alerts are currently paused")
        
        return "\n".join(result)
    
    except Exception as e:
        logger.error(f"Error getting alerts: {e}")
        return f"Error retrieving alerts: {str(e)}"


@mcp.tool()
async def get_device_status(device_serial: str = "") -> str:
    """Get comprehensive device status including connection, battery, and base station.
    
    Args:
        device_serial: Serial number of the device (optional, uses first device if not specified)
    
    Returns:
        str: Detailed device status information
    """
    try:
        devices = await get_devices()
        
        if not devices:
            return "No devices found. Please check your Owlet account."
        
        # Select device
        target_device = None
        if device_serial:
            target_device = next((d for d in devices if d.serial == device_serial), None)
            if not target_device:
                return f"Device with serial {device_serial} not found."
        else:
            target_device = devices[0]  # Use first device
        
        # Get current properties
        properties_data = await target_device.update_properties()
        properties = properties_data["properties"]
        
        status_info = [
            f"📱 Device Status for {target_device.name}",
            "=" * 50,
            f"Serial Number: {target_device.serial}",
            f"Model: {target_device.model} ({target_device.oem_model})",
            f"Software Version: {target_device.sw_version}",
            f"Hardware Version: {properties.get('hardware_version', 'Unknown')}",
            f"MAC Address: {target_device.mac}",
            f"LAN IP: {target_device.lan_ip}",
            "",
            "Connection Status:",
        ]
        
        # Connection details
        connection_status = "✅ Connected" if target_device.connection_status == "Online" else f"❌ {target_device.connection_status}"
        status_info.append(f"  Device: {connection_status}")
        
        if "sock_connection" in properties:
            sock_status = "✅ Connected" if properties["sock_connection"] else "❌ Disconnected"
            status_info.append(f"  Sock: {sock_status}")
        
        if "base_station_on" in properties:
            base_status = "✅ On" if properties["base_station_on"] else "❌ Off"
            status_info.append(f"  Base Station: {base_status}")
        
        # Battery information
        status_info.append("\nBattery Information:")
        if "battery_percentage" in properties:
            battery_level = properties["battery_percentage"]
            battery_emoji = "🔋" if battery_level > 20 else "🪫"
            status_info.append(f"  Sock Battery: {battery_emoji} {battery_level}%")
        
        if "battery_minutes" in properties:
            minutes = properties["battery_minutes"]
            hours = minutes // 60
            mins = minutes % 60
            status_info.append(f"  Remaining Time: {hours}h {mins}m")
        
        if "base_battery_status" in properties:
            base_battery = "✅ Good" if properties["base_battery_status"] else "⚠️ Low"
            status_info.append(f"  Base Station Battery: {base_battery}")
        
        # Monitoring status
        status_info.append("\nMonitoring Status:")
        if "monitoring_start_time" in properties:
            start_time = datetime.fromtimestamp(properties["monitoring_start_time"])
            status_info.append(f"  Started: {start_time.strftime('%Y-%m-%d %H:%M:%S')}")
        
        if "readings_flag" in properties:
            reading_status = "✅ Active" if properties["readings_flag"] else "❌ Inactive"
            status_info.append(f"  Readings: {reading_status}")
        
        return "\n".join(status_info)
    
    except Exception as e:
        logger.error(f"Error getting device status: {e}")
        return f"Error retrieving device status: {str(e)}"


@mcp.tool()
async def control_base_station(action: str, device_serial: str = "") -> str:
    """Turn the base station on or off.
    
    Args:
        action: Either "on" or "off" to control the base station
        device_serial: Serial number of the device (optional, uses first device if not specified)
    
    Returns:
        str: Result of the base station control operation
    """
    try:
        if action.lower() not in ["on", "off"]:
            return "Invalid action. Please use 'on' or 'off'."
        
        devices = await get_devices()
        
        if not devices:
            return "No devices found. Please check your Owlet account."
        
        # Select device
        target_device = None
        if device_serial:
            target_device = next((d for d in devices if d.serial == device_serial), None)
            if not target_device:
                return f"Device with serial {device_serial} not found."
        else:
            target_device = devices[0]  # Use first device
        
        # Control base station
        turn_on = action.lower() == "on"
        success = await target_device.control_base_station(turn_on)
        
        if success:
            status = "turned on" if turn_on else "turned off"
            return f"✅ Base station {status} successfully for device {target_device.name} ({target_device.serial})"
        else:
            return "❌ Failed to control base station. Please try again."
    
    except Exception as e:
        logger.error(f"Error controlling base station: {e}")
        return f"Error controlling base station: {str(e)}"


@mcp.tool()
async def get_live_feed_info(device_serial: str = "") -> str:
    """Get information about accessing live feed and camera features.
    
    Args:
        device_serial: Serial number of the device (optional, uses first device if not specified)
    
    Returns:
        str: Information about live feed access and camera capabilities
    """
    try:
        devices = await get_devices()
        
        if not devices:
            return "No devices found. Please check your Owlet account."
        
        # Select device
        target_device = None
        if device_serial:
            target_device = next((d for d in devices if d.serial == device_serial), None)
            if not target_device:
                return f"Device with serial {device_serial} not found."
        else:
            target_device = devices[0]  # Use first device
        
        # Get device properties to check for camera capabilities
        properties_data = await target_device.update_properties()
        
        info = [
            f"📹 Live Feed Information for {target_device.name}",
            "=" * 50,
            f"Device: {target_device.serial}",
            f"Model: {target_device.model}",
            "",
            "Live Feed Access:",
        ]
        
        # Check if this is a camera-enabled device
        if target_device.version == 3:
            info.extend([
                "✅ This device supports live monitoring features",
                "",
                "📱 Owlet App Live Feed:",
                "  • Open the Owlet Care app on your mobile device",
                "  • Navigate to your baby's monitoring dashboard",
                "  • Look for the 'Live' or 'Camera' tab",
                "  • The live feed will be available when the sock is active",
                "",
                "🌐 Web Dashboard Access:",
                f"  • Visit: https://app.owletdata.com",
                "  • Log in with your Owlet account credentials",
                "  • Select your baby's profile",
                "  • Access live data and historical trends",
                "",
                "📊 Available Live Data:",
                "  • Real-time heart rate monitoring",
                "  • Oxygen saturation levels",
                "  • Skin temperature readings",
                "  • Sleep state tracking",
                "  • Movement detection",
                "  • Base station status",
            ])
        else:
            info.extend([
                "ℹ️ This device (Sock v2) has limited live feed capabilities",
                "",
                "📱 Available Features:",
                "  • Real-time vital signs in the Owlet app",
                "  • Push notifications for alerts",
                "  • Historical data tracking",
                "",
                "📊 Live Data Access:",
                "  • Heart rate monitoring",
                "  • Oxygen level tracking", 
                "  • Movement detection",
                "  • Charging status",
            ])
        
        # Add current monitoring status
        properties = properties_data["properties"]
        info.extend([
            "",
            "Current Status:",
            f"  • Monitoring Active: {'✅ Yes' if properties.get('readings_flag', 0) else '❌ No'}",
            f"  • Base Station: {'✅ On' if properties.get('base_station_on', 0) else '❌ Off'}",
            f"  • Sock Connected: {'✅ Yes' if properties.get('sock_connection', 0) else '❌ No'}",
        ])
        
        if properties.get('last_updated'):
            info.append(f"  • Last Update: {properties['last_updated']}")
        
        # Add helpful tips
        info.extend([
            "",
            "💡 Tips for Best Live Feed Experience:",
            "  • Ensure strong WiFi connection for the base station",
            "  • Keep the sock charged and properly positioned",
            "  • Use the official Owlet Care app for best performance",
            "  • Enable notifications to get real-time alerts",
        ])
        
        return "\n".join(info)
    
    except Exception as e:
        logger.error(f"Error getting live feed info: {e}")
        return f"Error retrieving live feed information: {str(e)}"


@mcp.tool()
async def get_historical_data_info(device_serial: str = "") -> str:
    """Get information about accessing historical monitoring data and trends.
    
    Args:
        device_serial: Serial number of the device (optional, uses first device if not specified)
    
    Returns:
        str: Information about historical data access and available trends
    """
    try:
        devices = await get_devices()
        
        if not devices:
            return "No devices found. Please check your Owlet account."
        
        # Select device
        target_device = None
        if device_serial:
            target_device = next((d for d in devices if d.serial == device_serial), None)
            if not target_device:
                return f"Device with serial {device_serial} not found."
        else:
            target_device = devices[0]  # Use first device
        
        # Get current properties for context
        properties_data = await target_device.update_properties()
        properties = properties_data["properties"]
        
        info = [
            f"📊 Historical Data Information for {target_device.name}",
            "=" * 50,
            f"Device: {target_device.serial}",
            f"Sock Version: {target_device.version}",
            "",
            "Historical Data Access:",
        ]
        
        # Monitoring start time if available
        if properties.get("monitoring_start_time"):
            start_time = datetime.fromtimestamp(properties["monitoring_start_time"])
            info.append(f"  • Current Session Started: {start_time.strftime('%Y-%m-%d %H:%M:%S')}")
            
            # Calculate session duration
            duration = datetime.now() - start_time
            hours = duration.total_seconds() // 3600
            minutes = (duration.total_seconds() % 3600) // 60
            info.append(f"  • Session Duration: {int(hours)}h {int(minutes)}m")
        
        info.extend([
            "",
            "🌐 Owlet Web Dashboard:",
            "  • URL: https://app.owletdata.com",
            "  • Login with your Owlet account credentials",
            "  • Access historical trends and analytics",
            "",
            "📱 Owlet Mobile App:",
            "  • Open the Owlet Care app",
            "  • Navigate to 'History' or 'Trends' section",
            "  • View daily, weekly, and monthly summaries",
            "",
            "📈 Available Historical Metrics:",
        ])
        
        if target_device.version == 3:
            info.extend([
                "  • Heart rate trends and patterns",
                "  • Oxygen saturation levels over time",
                "  • Skin temperature variations",
                "  • Sleep state analysis (Awake/Light Sleep/Deep Sleep)",
                "  • Movement activity patterns",
                "  • Sleep duration and quality metrics",
                "  • Alert frequency and types",
                "  • Base station connectivity history",
            ])
        else:
            info.extend([
                "  • Heart rate monitoring history",
                "  • Oxygen level tracking",
                "  • Movement pattern analysis",
                "  • Charging session history",
                "  • Connection status logs",
                "  • Alert and notification history",
            ])
        
        info.extend([
            "",
            "📅 Data Retention:",
            "  • Real-time data: Available while monitoring",
            "  • Daily summaries: Typically 30+ days",
            "  • Weekly trends: Several months",
            "  • Monthly reports: Extended historical period",
            "",
            "📊 Export Options:",
            "  • PDF reports available through the web dashboard",
            "  • Email summaries can be enabled",
            "  • Share reports with healthcare providers",
            "",
            "💡 Data Analysis Tips:",
            "  • Look for patterns in sleep and vital signs",
            "  • Monitor trends over multiple nights",
            "  • Note correlations with feeding, room temperature, etc.",
            "  • Share unusual patterns with your pediatrician",
        ])
        
        # Add current data snapshot
        info.extend([
            "",
            "Current Data Snapshot:",
            f"  • Last Updated: {properties.get('last_updated', 'Unknown')}",
        ])
        
        if "heart_rate" in properties:
            info.append(f"  • Current Heart Rate: {properties['heart_rate']} BPM")
        
        if "oxygen_saturation" in properties:
            info.append(f"  • Current Oxygen Saturation: {properties['oxygen_saturation']}%")
        
        if "sleep_state" in properties:
            sleep_states = {0: "Awake", 1: "Light Sleep", 2: "Deep Sleep"}
            state = sleep_states.get(properties["sleep_state"], "Unknown")
            info.append(f"  • Current Sleep State: {state}")
        
        return "\n".join(info)
    
    except Exception as e:
        logger.error(f"Error getting historical data info: {e}")
        return f"Error retrieving historical data information: {str(e)}"


@mcp.tool()
async def get_baby_wellness_summary(device_serial: str = "") -> str:
    """Get a comprehensive wellness summary for the baby including all vitals, alerts, and recommendations.
    
    Args:
        device_serial: Serial number of the device (optional, uses first device if not specified)
    
    Returns:
        str: Complete wellness summary with vitals, alerts, and guidance
    """
    try:
        devices = await get_devices()
        
        if not devices:
            return "No devices found. Please check your Owlet account."
        
        # Select device
        target_device = None
        if device_serial:
            target_device = next((d for d in devices if d.serial == device_serial), None)
            if not target_device:
                return f"Device with serial {device_serial} not found."
        else:
            target_device = devices[0]  # Use first device
        
        # Get current properties
        properties_data = await target_device.update_properties()
        properties = properties_data["properties"]
        
        # Create comprehensive summary
        summary = [
            f"👶 Baby Wellness Summary",
            f"Device: {target_device.name} ({target_device.serial})",
            f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            "=" * 60,
            "",
            "🫀 VITAL SIGNS:",
            format_vitals_data(properties),
            "",
            "🚨 ALERT STATUS:",
            format_alerts_data(properties),
            "",
        ]
        
        # Device and monitoring status
        summary.extend([
            "📱 MONITORING STATUS:",
            f"  • Device Connection: {'✅ Online' if target_device.connection_status == 'Online' else '❌ ' + target_device.connection_status}",
            f"  • Sock Connection: {'✅ Connected' if properties.get('sock_connection', 0) else '❌ Disconnected'}",
            f"  • Base Station: {'✅ On' if properties.get('base_station_on', 0) else '❌ Off'}",
            f"  • Readings Active: {'✅ Yes' if properties.get('readings_flag', 0) else '❌ No'}",
        ])
        
        if properties.get("monitoring_start_time"):
            start_time = datetime.fromtimestamp(properties["monitoring_start_time"])
            duration = datetime.now() - start_time
            hours = duration.total_seconds() // 3600
            minutes = (duration.total_seconds() % 3600) // 60
            summary.append(f"  • Monitoring Duration: {int(hours)}h {int(minutes)}m")
        
        summary.append("")
        
        # Wellness assessment
        summary.extend([
            "💚 WELLNESS ASSESSMENT:",
        ])
        
        # Check for any critical issues
        critical_alerts = any([
            properties.get("critical_oxygen_alert"),
            properties.get("critical_battery_alert"),
            properties.get("sock_disconnected"),
            properties.get("sock_off")
        ])
        
        if critical_alerts:
            summary.append("  🚨 ATTENTION NEEDED: Critical alerts detected - check immediately")
        else:
            # Normal wellness assessment
            hr_normal = 60 <= properties.get("heart_rate", 100) <= 160 if properties.get("heart_rate") else True
            ox_normal = properties.get("oxygen_saturation", 95) >= 95 if properties.get("oxygen_saturation") else True
            battery_ok = properties.get("battery_percentage", 50) > 20 if properties.get("battery_percentage") else True
            
            if hr_normal and ox_normal and battery_ok:
                summary.append("  ✅ Baby appears to be doing well - all vitals in normal range")
            else:
                if not hr_normal:
                    summary.append("  ⚠️ Heart rate may need attention")
                if not ox_normal:
                    summary.append("  ⚠️ Oxygen saturation may need attention")
                if not battery_ok:
                    summary.append("  🔋 Device battery needs charging soon")
        
        # Sleep assessment
        if "sleep_state" in properties:
            sleep_states = {0: "Awake", 1: "Light Sleep", 2: "Deep Sleep"}
            state = sleep_states.get(properties["sleep_state"], "Unknown")
            if state == "Deep Sleep":
                summary.append("  😴 Baby is in deep sleep - optimal rest state")
            elif state == "Light Sleep":
                summary.append("  😊 Baby is in light sleep - resting comfortably")
            else:
                summary.append("  👀 Baby is awake - normal activity period")
        
        # Recommendations
        summary.extend([
            "",
            "📋 RECOMMENDATIONS:",
        ])
        
        if properties.get("battery_percentage", 100) < 30:
            summary.append("  • Charge the sock soon to ensure continuous monitoring")
        
        if not properties.get("base_station_on", 1):
            summary.append("  • Turn on the base station to resume monitoring")
        
        if not properties.get("sock_connection", 1):
            summary.append("  • Check sock placement and connection")
        
        if properties.get("low_oxygen_alert") or properties.get("low_heart_rate_alert"):
            summary.append("  • Monitor baby closely and consult healthcare provider if concerns persist")
        
        if not any([properties.get("low_oxygen_alert"), properties.get("low_heart_rate_alert"), 
                   properties.get("critical_oxygen_alert"), properties.get("critical_battery_alert")]):
            summary.append("  • Continue normal monitoring routine")
            summary.append("  • Ensure sock is properly positioned on baby's foot")
            summary.append("  • Keep base station within range and powered")
        
        # Emergency guidance
        summary.extend([
            "",
            "🆘 EMERGENCY GUIDANCE:",
            "  • If baby appears unresponsive or in distress, contact emergency services immediately",
            "  • Owlet monitors are not medical devices and should not replace attentive care",
            "  • Always trust your parental instincts over device readings",
            "  • Consult your pediatrician for any health concerns",
        ])
        
        return "\n".join(summary)
    
    except Exception as e:
        logger.error(f"Error generating wellness summary: {e}")
        return f"Error generating wellness summary: {str(e)}"


async def cleanup():
    """Cleanup function to close the API connection."""
    global api_client
    if api_client:
        await api_client.close()


if __name__ == "__main__":
    try:
        # Run the FastMCP server
        mcp.run(transport='stdio')
    except KeyboardInterrupt:
        logger.info("Server shutting down...")
    finally:
        # Cleanup
        if api_client:
            import asyncio
            asyncio.run(cleanup())