#!/usr/bin/env python3
"""
Owlet Baby Monitor Remote MCP Server

A remote Model Context Protocol server for monitoring Owlet baby devices.
Compatible with OpenAI ChatGPT connectors and deep research.

This server implements the required 'search' and 'fetch' tools for OpenAI integration
while providing comprehensive baby monitoring capabilities.
"""

import asyncio
import json
import logging
import os
import sys
from typing import Any, Dict, List, Optional
from datetime import datetime, timedelta
import uuid
import time
from functools import wraps

# Try to load environment variables from .env file
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    # dotenv not available, use environment variables directly
    pass

from fastmcp import FastMCP
from src.pyowletapi.api import OwletAPI
from src.pyowletapi.sock import Sock
from src.pyowletapi.exceptions import (
    OwletAuthenticationError,
    OwletConnectionError,
    OwletDevicesError,
    OwletError,
)

# Configure logging to stderr (important for remote MCP servers)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    stream=sys.stderr
)
logger = logging.getLogger(__name__)

# Security and rate limiting
request_counts = {}
REQUEST_LIMIT = 100  # requests per minute
TIME_WINDOW = 60  # seconds

def rate_limit(func):
    """Rate limiting decorator"""
    @wraps(func)
    async def wrapper(*args, **kwargs):
        client_id = kwargs.get('client_id', 'unknown')
        current_time = time.time()
        
        # Clean old entries
        cutoff_time = current_time - TIME_WINDOW
        request_counts[client_id] = [
            req_time for req_time in request_counts.get(client_id, [])
            if req_time > cutoff_time
        ]
        
        # Check rate limit
        if len(request_counts.get(client_id, [])) >= REQUEST_LIMIT:
            raise Exception(f"Rate limit exceeded: {REQUEST_LIMIT} requests per minute")
        
        # Add current request
        if client_id not in request_counts:
            request_counts[client_id] = []
        request_counts[client_id].append(current_time)
        
        return await func(*args, **kwargs)
    return wrapper

def validate_query(query: str) -> bool:
    """Validate search query for security"""
    if not query or len(query.strip()) == 0:
        return False
    if len(query) > 500:  # Limit query length
        return False
    # Add more validation as needed
    return True

def sanitize_output(data: Any) -> Any:
    """Sanitize output data"""
    if isinstance(data, dict):
        # Remove sensitive fields
        sensitive_fields = ['password', 'token', 'key', 'secret']
        return {
            k: sanitize_output(v) for k, v in data.items()
            if k.lower() not in sensitive_fields
        }
    elif isinstance(data, list):
        return [sanitize_output(item) for item in data]
    return data

# Global variables for API and devices
api_client: Optional[OwletAPI] = None
devices: List[Sock] = []
search_cache: Dict[str, Any] = {}

# Server instructions for OpenAI integration
server_instructions = """
This MCP server provides baby monitoring capabilities for Owlet Smart Sock devices.
Use the search tool to find specific monitoring data, alerts, or device information.
Use the fetch tool to retrieve detailed vitals, historical data, or comprehensive reports.

Available search queries:
- "current vitals" - Get real-time heart rate, oxygen, temperature
- "active alerts" - Check for any monitoring alerts
- "device status" - Get device connectivity and battery status
- "wellness summary" - Get comprehensive baby health overview
- "historical data" - Access trends and historical monitoring
- "live feed" - Get live monitoring access information

The server connects to official Owlet APIs to provide real-time baby monitoring data.
"""


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
                "Authentication required. Please set OWLET_USER and OWLET_PASSWORD environment variables."
            )
        
        logger.info(f"Authenticating with Owlet API for region: {region}")
        api_client = OwletAPI(region=region, user=user, password=password)
        
        try:
            tokens = await api_client.authenticate()
            logger.info("Successfully authenticated with Owlet API")
        except Exception as e:
            logger.error(f"Authentication failed: {e}")
            api_client = None
            raise OwletAuthenticationError(f"Failed to authenticate: {str(e)}")
    
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
        
        logger.info(f"Found {len(devices)} Owlet devices")
    
    return devices


def format_vitals_for_search(properties: Dict[str, Any], device_name: str, device_serial: str) -> Dict[str, Any]:
    """Format vitals data for search results."""
    
    # Create a summary
    summary_parts = []
    if "heart_rate" in properties:
        summary_parts.append(f"HR: {properties['heart_rate']} BPM")
    if "oxygen_saturation" in properties:
        summary_parts.append(f"O2: {properties['oxygen_saturation']}%")
    if "skin_temperature" in properties:
        temp_c = properties["skin_temperature"] / 10 if properties["skin_temperature"] > 100 else properties["skin_temperature"]
        summary_parts.append(f"Temp: {temp_c:.1f}°C")
    
    summary = ", ".join(summary_parts) if summary_parts else "Monitoring data available"
    
    return {
        "id": f"vitals_{device_serial}",
        "title": f"Current Vitals - {device_name}",
        "text": summary,
        "url": f"https://app.owletdata.com/device/{device_serial}"
    }


def format_alerts_for_search(properties: Dict[str, Any], device_name: str, device_serial: str) -> Dict[str, Any]:
    """Format alerts data for search results."""
    
    # Count alerts
    alert_count = 0
    critical_alerts = 0
    
    alert_keys = [
        "critical_oxygen_alert", "critical_battery_alert", "low_oxygen_alert",
        "high_oxygen_alert", "low_heart_rate_alert", "high_heart_rate_alert",
        "low_battery_alert", "lost_power_alert", "sock_disconnected", "sock_off"
    ]
    
    for key in alert_keys:
        if properties.get(key):
            alert_count += 1
            if "critical" in key:
                critical_alerts += 1
    
    if alert_count == 0:
        summary = "No active alerts - monitoring normally"
    elif critical_alerts > 0:
        summary = f"{critical_alerts} critical alerts, {alert_count} total alerts"
    else:
        summary = f"{alert_count} active alerts"
    
    return {
        "id": f"alerts_{device_serial}",
        "title": f"Alert Status - {device_name}",
        "text": summary,
        "url": f"https://app.owletdata.com/device/{device_serial}/alerts"
    }


async def create_server():
    """Create and configure the remote MCP server."""
    
    mcp = FastMCP(name="Owlet Baby Monitor", instructions=server_instructions)
    
    @mcp.tool()
    @rate_limit
    async def search(query: str) -> Dict[str, List[Dict[str, Any]]]:
        """
        Search for baby monitoring data from Owlet devices.
        
        This tool searches through available monitoring data to find relevant information
        about your baby's health, device status, alerts, and historical trends.
        
        Args:
            query: Search query string. Examples:
                   - "current vitals" or "heart rate oxygen"
                   - "alerts" or "warnings"
                   - "device status" or "battery connection"
                   - "wellness summary" or "health overview"
                   - "historical data" or "trends"
                   - "live feed" or "monitoring access"
        
        Returns:
            Dictionary with 'results' key containing list of matching monitoring data.
            Each result includes id, title, summary text, and URL for citation.
        """
        if not query or not query.strip():
            return {"results": []}
        
        # Security validation
        if not validate_query(query):
            return {"results": [{
                "id": "error_invalid_query",
                "title": "Invalid Query",
                "text": "Query validation failed. Please provide a valid search query.",
                "url": "https://app.owletdata.com"
            }]}
        
        query_lower = query.lower()
        results = []
        
        try:
            devices = await get_devices()
            
            if not devices:
                return {"results": [{
                    "id": "no_devices",
                    "title": "No Owlet Devices Found",
                    "text": "No Owlet devices are currently available in your account.",
                    "url": "https://app.owletdata.com"
                }]}
            
            for device in devices:
                try:
                    # Get current properties for the device
                    properties_data = await device.update_properties()
                    properties = properties_data["properties"]
                    
                    # Search for vitals-related queries
                    if any(term in query_lower for term in ["vitals", "heart", "oxygen", "temperature", "current", "now"]):
                        result = format_vitals_for_search(properties, device.name, device.serial)
                        results.append(result)
                    
                    # Search for alert-related queries
                    if any(term in query_lower for term in ["alert", "warning", "critical", "alarm", "problem"]):
                        result = format_alerts_for_search(properties, device.name, device.serial)
                        results.append(result)
                    
                    # Search for device status queries
                    if any(term in query_lower for term in ["device", "status", "battery", "connection", "base station"]):
                        battery_level = properties.get("battery_percentage", 0)
                        connection_status = "Connected" if device.connection_status == "Online" else device.connection_status
                        
                        results.append({
                            "id": f"status_{device.serial}",
                            "title": f"Device Status - {device.name}",
                            "text": f"Connection: {connection_status}, Battery: {battery_level}%",
                            "url": f"https://app.owletdata.com/device/{device.serial}/status"
                        })
                    
                    # Search for wellness/summary queries
                    if any(term in query_lower for term in ["wellness", "summary", "overview", "health", "report"]):
                        # Create a comprehensive summary
                        hr = properties.get("heart_rate", "N/A")
                        ox = properties.get("oxygen_saturation", "N/A")
                        alerts = "No alerts" if not any(properties.get(k) for k in ["critical_oxygen_alert", "critical_battery_alert"]) else "Active alerts"
                        
                        results.append({
                            "id": f"wellness_{device.serial}",
                            "title": f"Wellness Summary - {device.name}",
                            "text": f"HR: {hr}, O2: {ox}%, Status: {alerts}",
                            "url": f"https://app.owletdata.com/device/{device.serial}/wellness"
                        })
                    
                    # Search for historical data queries
                    if any(term in query_lower for term in ["history", "historical", "trends", "past", "data"]):
                        start_time = properties.get("monitoring_start_time")
                        duration_text = "Session active"
                        if start_time:
                            duration = datetime.now() - datetime.fromtimestamp(start_time)
                            hours = duration.total_seconds() // 3600
                            duration_text = f"Monitoring for {int(hours)}h"
                        
                        results.append({
                            "id": f"history_{device.serial}",
                            "title": f"Historical Data - {device.name}",
                            "text": f"{duration_text}, trends and patterns available",
                            "url": f"https://app.owletdata.com/device/{device.serial}/history"
                        })
                    
                    # Search for live feed queries
                    if any(term in query_lower for term in ["live", "feed", "camera", "video", "streaming", "real-time"]):
                        sock_version = device.version or "Unknown"
                        capability = "Full live monitoring" if sock_version == 3 else "Real-time vitals"
                        
                        results.append({
                            "id": f"live_{device.serial}",
                            "title": f"Live Feed Access - {device.name}",
                            "text": f"Sock v{sock_version}: {capability} available",
                            "url": f"https://app.owletdata.com/device/{device.serial}/live"
                        })
                
                except Exception as e:
                    logger.error(f"Error processing device {device.serial}: {e}")
                    continue
            
            # If no specific matches, provide general device info
            if not results:
                for device in devices:
                    results.append({
                        "id": f"device_{device.serial}",
                        "title": f"Owlet Device - {device.name}",
                        "text": f"Model: {device.model}, Status: {device.connection_status}",
                        "url": f"https://app.owletdata.com/device/{device.serial}"
                    })
            
            logger.info(f"Search for '{query}' returned {len(results)} results")
            sanitized_results = sanitize_output(results)
            return {"results": sanitized_results}
        
        except Exception as e:
            logger.error(f"Search error: {e}")
            return {"results": [{
                "id": "error",
                "title": "Search Error",
                "text": f"Unable to search monitoring data: {str(e)}",
                "url": "https://app.owletdata.com"
            }]}
    
    @mcp.tool()
    @rate_limit
    async def fetch(id: str) -> Dict[str, Any]:
        """
        Retrieve complete monitoring data by ID for detailed analysis.
        
        This tool fetches comprehensive information about baby monitoring data,
        device status, alerts, or wellness reports. Use this after finding
        relevant items with the search tool to get complete information.
        
        Args:
            id: Document ID from search results (e.g., "vitals_DEVICE123", "alerts_DEVICE123")
        
        Returns:
            Complete document with id, title, full monitoring data,
            URL for citation, and metadata about the monitoring session.
        """
        if not id:
            raise ValueError("Document ID is required")
        
        try:
            # Parse the ID to determine what data to fetch
            parts = id.split("_", 1)
            if len(parts) != 2:
                raise ValueError(f"Invalid document ID format: {id}")
            
            data_type, device_serial = parts
            
            devices = await get_devices()
            target_device = next((d for d in devices if d.serial == device_serial), None)
            
            if not target_device:
                raise ValueError(f"Device {device_serial} not found")
            
            # Get current properties
            properties_data = await target_device.update_properties()
            properties = properties_data["properties"]
            
            # Generate content based on data type
            if data_type == "vitals":
                content = await _generate_vitals_content(target_device, properties)
            elif data_type == "alerts":
                content = await _generate_alerts_content(target_device, properties)
            elif data_type == "status":
                content = await _generate_status_content(target_device, properties)
            elif data_type == "wellness":
                content = await _generate_wellness_content(target_device, properties)
            elif data_type == "history":
                content = await _generate_history_content(target_device, properties)
            elif data_type == "live":
                content = await _generate_live_content(target_device, properties)
            elif data_type == "device":
                content = await _generate_device_content(target_device, properties)
            else:
                raise ValueError(f"Unknown data type: {data_type}")
            
            logger.info(f"Fetched content for: {id}")
            sanitized_content = sanitize_output(content)
            return sanitized_content
        
        except Exception as e:
            logger.error(f"Fetch error for ID {id}: {e}")
            raise ValueError(f"Unable to fetch document {id}: {str(e)}")
    
    return mcp


async def _generate_vitals_content(device: Sock, properties: Dict[str, Any]) -> Dict[str, Any]:
    """Generate comprehensive vitals content."""
    
    vitals_data = {
        "timestamp": datetime.now().isoformat(),
        "device": {
            "name": device.name,
            "serial": device.serial,
            "model": device.model,
            "version": device.version
        },
        "vitals": {},
        "status": {}
    }
    
    # Core vitals
    if "heart_rate" in properties:
        vitals_data["vitals"]["heart_rate"] = {
            "value": properties["heart_rate"],
            "unit": "BPM",
            "status": "normal" if 60 <= properties["heart_rate"] <= 160 else "attention_needed"
        }
    
    if "oxygen_saturation" in properties:
        vitals_data["vitals"]["oxygen_saturation"] = {
            "value": properties["oxygen_saturation"],
            "unit": "%",
            "status": "normal" if properties["oxygen_saturation"] >= 95 else "attention_needed"
        }
    
    if "skin_temperature" in properties:
        temp_c = properties["skin_temperature"] / 10 if properties["skin_temperature"] > 100 else properties["skin_temperature"]
        temp_f = (temp_c * 9/5) + 32
        vitals_data["vitals"]["skin_temperature"] = {
            "celsius": temp_c,
            "fahrenheit": temp_f,
            "unit": "°C",
            "status": "normal"
        }
    
    # Sleep and movement
    if "sleep_state" in properties:
        sleep_states = {0: "Awake", 1: "Light Sleep", 2: "Deep Sleep"}
        vitals_data["vitals"]["sleep_state"] = {
            "value": sleep_states.get(properties["sleep_state"], "Unknown"),
            "numeric_value": properties["sleep_state"]
        }
    
    if "movement" in properties:
        vitals_data["vitals"]["movement"] = {
            "level": properties["movement"],
            "status": "active" if properties["movement"] > 5 else "calm"
        }
    
    # Device status
    vitals_data["status"] = {
        "battery_percentage": properties.get("battery_percentage"),
        "signal_strength": properties.get("signal_strength"),
        "charging": properties.get("charging", False),
        "base_station_on": properties.get("base_station_on", False),
        "sock_connection": properties.get("sock_connection", False),
        "last_updated": properties.get("last_updated")
    }
    
    formatted_content = json.dumps(vitals_data, indent=2)
    
    return {
        "id": f"vitals_{device.serial}",
        "title": f"Current Vital Signs - {device.name}",
        "text": formatted_content,
        "url": f"https://app.owletdata.com/device/{device.serial}",
        "metadata": {
            "source": "owlet_api",
            "device_serial": device.serial,
            "data_type": "vitals",
            "timestamp": datetime.now().isoformat()
        }
    }


async def _generate_alerts_content(device: Sock, properties: Dict[str, Any]) -> Dict[str, Any]:
    """Generate comprehensive alerts content."""
    
    alerts_data = {
        "timestamp": datetime.now().isoformat(),
        "device": {
            "name": device.name,
            "serial": device.serial
        },
        "critical_alerts": {},
        "standard_alerts": {},
        "wellness_alerts": {},
        "alert_summary": {
            "total_count": 0,
            "critical_count": 0,
            "alert_paused": properties.get("alert_paused_status", False)
        }
    }
    
    # Critical alerts
    critical_alerts = {
        "critical_oxygen_alert": "Critical Low Oxygen",
        "critical_battery_alert": "Critical Battery Level"
    }
    
    for key, description in critical_alerts.items():
        if properties.get(key):
            alerts_data["critical_alerts"][key] = {
                "active": True,
                "description": description,
                "severity": "critical"
            }
            alerts_data["alert_summary"]["critical_count"] += 1
            alerts_data["alert_summary"]["total_count"] += 1
    
    # Standard alerts
    standard_alerts = {
        "low_oxygen_alert": "Low Oxygen Level",
        "high_oxygen_alert": "High Oxygen Level",
        "low_heart_rate_alert": "Low Heart Rate",
        "high_heart_rate_alert": "High Heart Rate",
        "low_battery_alert": "Low Battery",
        "lost_power_alert": "Lost Power",
        "sock_disconnected": "Sock Disconnected",
        "sock_off": "Sock Removed"
    }
    
    for key, description in standard_alerts.items():
        if properties.get(key):
            alerts_data["standard_alerts"][key] = {
                "active": True,
                "description": description,
                "severity": "warning"
            }
            alerts_data["alert_summary"]["total_count"] += 1
    
    # Wellness alerts
    if properties.get("wellness_alert"):
        alerts_data["wellness_alerts"]["wellness_alert"] = {
            "active": True,
            "description": "Wellness Notification",
            "severity": "info"
        }
    
    formatted_content = json.dumps(alerts_data, indent=2)
    
    return {
        "id": f"alerts_{device.serial}",
        "title": f"Alert Status - {device.name}",
        "text": formatted_content,
        "url": f"https://app.owletdata.com/device/{device.serial}/alerts",
        "metadata": {
            "source": "owlet_api",
            "device_serial": device.serial,
            "data_type": "alerts",
            "timestamp": datetime.now().isoformat()
        }
    }


async def _generate_status_content(device: Sock, properties: Dict[str, Any]) -> Dict[str, Any]:
    """Generate device status content."""
    
    status_data = {
        "timestamp": datetime.now().isoformat(),
        "device_info": {
            "name": device.name,
            "serial": device.serial,
            "model": device.model,
            "oem_model": device.oem_model,
            "software_version": device.sw_version,
            "hardware_version": properties.get("hardware_version"),
            "mac_address": device.mac,
            "lan_ip": device.lan_ip,
            "sock_version": device.version
        },
        "connectivity": {
            "device_status": device.connection_status,
            "sock_connected": properties.get("sock_connection", False),
            "base_station_on": properties.get("base_station_on", False),
            "signal_strength": properties.get("signal_strength"),
            "readings_active": properties.get("readings_flag", False)
        },
        "power": {
            "battery_percentage": properties.get("battery_percentage"),
            "battery_minutes_remaining": properties.get("battery_minutes"),
            "charging": properties.get("charging", False),
            "base_battery_status": properties.get("base_battery_status")
        },
        "monitoring": {
            "monitoring_start_time": properties.get("monitoring_start_time"),
            "last_updated": properties.get("last_updated"),
            "update_status": properties.get("update_status"),
            "firmware_update_available": properties.get("firmware_update_available", False)
        }
    }
    
    formatted_content = json.dumps(status_data, indent=2)
    
    return {
        "id": f"status_{device.serial}",
        "title": f"Device Status - {device.name}",
        "text": formatted_content,
        "url": f"https://app.owletdata.com/device/{device.serial}/status",
        "metadata": {
            "source": "owlet_api",
            "device_serial": device.serial,
            "data_type": "status",
            "timestamp": datetime.now().isoformat()
        }
    }


async def _generate_wellness_content(device: Sock, properties: Dict[str, Any]) -> Dict[str, Any]:
    """Generate comprehensive wellness summary content."""
    
    wellness_data = {
        "timestamp": datetime.now().isoformat(),
        "device": {
            "name": device.name,
            "serial": device.serial
        },
        "wellness_assessment": {
            "overall_status": "monitoring",
            "recommendations": [],
            "concerns": []
        },
        "current_vitals": {},
        "monitoring_session": {},
        "emergency_guidance": {
            "important_note": "Owlet monitors are not medical devices. Always trust parental instincts and contact healthcare providers for medical concerns.",
            "emergency_contact": "Contact emergency services immediately if baby appears unresponsive or in distress."
        }
    }
    
    # Assess vitals
    hr_normal = True
    ox_normal = True
    
    if "heart_rate" in properties:
        hr = properties["heart_rate"]
        hr_normal = 60 <= hr <= 160
        wellness_data["current_vitals"]["heart_rate"] = {
            "value": hr,
            "status": "normal" if hr_normal else "attention_needed"
        }
    
    if "oxygen_saturation" in properties:
        ox = properties["oxygen_saturation"]
        ox_normal = ox >= 95
        wellness_data["current_vitals"]["oxygen_saturation"] = {
            "value": ox,
            "status": "normal" if ox_normal else "attention_needed"
        }
    
    # Check for critical issues
    critical_alerts = any([
        properties.get("critical_oxygen_alert"),
        properties.get("critical_battery_alert"),
        properties.get("sock_disconnected"),
        properties.get("sock_off")
    ])
    
    if critical_alerts:
        wellness_data["wellness_assessment"]["overall_status"] = "attention_needed"
        wellness_data["wellness_assessment"]["concerns"].append("Critical alerts detected - check immediately")
    elif hr_normal and ox_normal:
        wellness_data["wellness_assessment"]["overall_status"] = "good"
        wellness_data["wellness_assessment"]["recommendations"].append("Baby appears to be doing well - continue normal monitoring")
    
    # Add monitoring session info
    if properties.get("monitoring_start_time"):
        start_time = datetime.fromtimestamp(properties["monitoring_start_time"])
        duration = datetime.now() - start_time
        wellness_data["monitoring_session"] = {
            "started": start_time.isoformat(),
            "duration_hours": duration.total_seconds() / 3600,
            "last_updated": properties.get("last_updated")
        }
    
    # Add sleep state if available
    if "sleep_state" in properties:
        sleep_states = {0: "Awake", 1: "Light Sleep", 2: "Deep Sleep"}
        state = sleep_states.get(properties["sleep_state"], "Unknown")
        wellness_data["current_vitals"]["sleep_state"] = state
        
        if state == "Deep Sleep":
            wellness_data["wellness_assessment"]["recommendations"].append("Baby is in deep sleep - optimal rest state")
    
    formatted_content = json.dumps(wellness_data, indent=2)
    
    return {
        "id": f"wellness_{device.serial}",
        "title": f"Wellness Summary - {device.name}",
        "text": formatted_content,
        "url": f"https://app.owletdata.com/device/{device.serial}/wellness",
        "metadata": {
            "source": "owlet_api",
            "device_serial": device.serial,
            "data_type": "wellness",
            "timestamp": datetime.now().isoformat()
        }
    }


async def _generate_history_content(device: Sock, properties: Dict[str, Any]) -> Dict[str, Any]:
    """Generate historical data access information."""
    
    history_info = {
        "timestamp": datetime.now().isoformat(),
        "device": {
            "name": device.name,
            "serial": device.serial,
            "version": device.version
        },
        "current_session": {},
        "data_access": {
            "web_dashboard": "https://app.owletdata.com",
            "mobile_app": "Owlet Care app available on iOS and Android",
            "available_metrics": []
        },
        "data_retention": {
            "real_time": "Available while monitoring",
            "daily_summaries": "30+ days",
            "weekly_trends": "Several months",
            "monthly_reports": "Extended historical period"
        }
    }
    
    # Current session info
    if properties.get("monitoring_start_time"):
        start_time = datetime.fromtimestamp(properties["monitoring_start_time"])
        duration = datetime.now() - start_time
        history_info["current_session"] = {
            "started": start_time.isoformat(),
            "duration_hours": round(duration.total_seconds() / 3600, 1),
            "last_updated": properties.get("last_updated")
        }
    
    # Available metrics based on device version
    if device.version == 3:
        history_info["data_access"]["available_metrics"] = [
            "Heart rate trends and patterns",
            "Oxygen saturation levels over time",
            "Skin temperature variations",
            "Sleep state analysis (Awake/Light Sleep/Deep Sleep)",
            "Movement activity patterns",
            "Sleep duration and quality metrics",
            "Alert frequency and types",
            "Base station connectivity history"
        ]
    else:
        history_info["data_access"]["available_metrics"] = [
            "Heart rate monitoring history",
            "Oxygen level tracking",
            "Movement pattern analysis",
            "Charging session history",
            "Connection status logs",
            "Alert and notification history"
        ]
    
    formatted_content = json.dumps(history_info, indent=2)
    
    return {
        "id": f"history_{device.serial}",
        "title": f"Historical Data Access - {device.name}",
        "text": formatted_content,
        "url": f"https://app.owletdata.com/device/{device.serial}/history",
        "metadata": {
            "source": "owlet_api",
            "device_serial": device.serial,
            "data_type": "history",
            "timestamp": datetime.now().isoformat()
        }
    }


async def _generate_live_content(device: Sock, properties: Dict[str, Any]) -> Dict[str, Any]:
    """Generate live feed access information."""
    
    live_info = {
        "timestamp": datetime.now().isoformat(),
        "device": {
            "name": device.name,
            "serial": device.serial,
            "version": device.version
        },
        "live_capabilities": {},
        "access_methods": {
            "mobile_app": {
                "name": "Owlet Care app",
                "platforms": ["iOS", "Android"],
                "features": []
            },
            "web_dashboard": {
                "url": "https://app.owletdata.com",
                "features": []
            }
        },
        "current_status": {
            "monitoring_active": properties.get("readings_flag", False),
            "base_station_on": properties.get("base_station_on", False),
            "sock_connected": properties.get("sock_connection", False),
            "last_update": properties.get("last_updated")
        }
    }
    
    # Capabilities based on device version
    if device.version == 3:
        live_info["live_capabilities"] = {
            "real_time_vitals": True,
            "live_notifications": True,
            "streaming_data": True,
            "advanced_analytics": True
        }
        live_info["access_methods"]["mobile_app"]["features"] = [
            "Real-time heart rate monitoring",
            "Oxygen saturation levels",
            "Skin temperature readings",
            "Sleep state tracking",
            "Movement detection",
            "Push notifications for alerts",
            "Live data streaming"
        ]
    else:
        live_info["live_capabilities"] = {
            "real_time_vitals": True,
            "live_notifications": True,
            "streaming_data": False,
            "advanced_analytics": False
        }
        live_info["access_methods"]["mobile_app"]["features"] = [
            "Real-time vital signs",
            "Push notifications for alerts",
            "Heart rate monitoring",
            "Oxygen level tracking",
            "Movement detection"
        ]
    
    live_info["access_methods"]["web_dashboard"]["features"] = [
        "Live data dashboard",
        "Historical trends",
        "Alert management",
        "Device settings",
        "Export capabilities"
    ]
    
    formatted_content = json.dumps(live_info, indent=2)
    
    return {
        "id": f"live_{device.serial}",
        "title": f"Live Feed Access - {device.name}",
        "text": formatted_content,
        "url": f"https://app.owletdata.com/device/{device.serial}/live",
        "metadata": {
            "source": "owlet_api",
            "device_serial": device.serial,
            "data_type": "live_feed",
            "timestamp": datetime.now().isoformat()
        }
    }


async def _generate_device_content(device: Sock, properties: Dict[str, Any]) -> Dict[str, Any]:
    """Generate general device information content."""
    
    device_info = {
        "timestamp": datetime.now().isoformat(),
        "device_details": {
            "name": device.name,
            "serial": device.serial,
            "model": device.model,
            "oem_model": device.oem_model,
            "software_version": device.sw_version,
            "hardware_version": properties.get("hardware_version"),
            "sock_version": device.version,
            "mac_address": device.mac,
            "device_type": device.device_type
        },
        "current_status": {
            "connection": device.connection_status,
            "battery_level": properties.get("battery_percentage"),
            "monitoring_active": properties.get("readings_flag", False),
            "last_updated": properties.get("last_updated")
        },
        "capabilities": [],
        "support_info": {
            "manufacturer": "Owlet Baby Care",
            "support_url": "https://support.owletcare.com",
            "app_download": "Search 'Owlet Care' in app stores"
        }
    }
    
    # Add capabilities based on device version
    if device.version == 3:
        device_info["capabilities"] = [
            "Real-time heart rate monitoring",
            "Oxygen saturation tracking",
            "Skin temperature sensing",
            "Sleep state detection",
            "Movement tracking",
            "Advanced analytics",
            "Push notifications",
            "Historical data storage"
        ]
    elif device.version == 2:
        device_info["capabilities"] = [
            "Heart rate monitoring",
            "Oxygen level tracking",
            "Movement detection",
            "Basic analytics",
            "Push notifications",
            "Historical data storage"
        ]
    else:
        device_info["capabilities"] = [
            "Basic monitoring features",
            "Alert notifications"
        ]
    
    formatted_content = json.dumps(device_info, indent=2)
    
    return {
        "id": f"device_{device.serial}",
        "title": f"Device Information - {device.name}",
        "text": formatted_content,
        "url": f"https://app.owletdata.com/device/{device.serial}",
        "metadata": {
            "source": "owlet_api",
            "device_serial": device.serial,
            "data_type": "device_info",
            "timestamp": datetime.now().isoformat()
        }
    }


async def cleanup():
    """Cleanup function to close the API connection."""
    global api_client
    if api_client:
        await api_client.close()


async def initialize_and_run():
    """Initialize and run the remote MCP server."""
    
    # Verify required environment variables
    if not os.getenv("OWLET_USER") or not os.getenv("OWLET_PASSWORD"):
        logger.error("Missing required environment variables: OWLET_USER and OWLET_PASSWORD")
        sys.exit(1)
    
    logger.info("Starting Owlet Baby Monitor MCP Server")
    logger.info(f"Region: {os.getenv('OWLET_REGION', 'world')}")
    
    # Create the MCP server
    server = await create_server()
    
    # Get port from environment or default to 8000
    port = int(os.getenv("PORT", 8000))
    host = os.getenv("HOST", "0.0.0.0")
    
    logger.info(f"Starting server on {host}:{port}")
    logger.info("Server will be accessible via SSE transport")
    
    try:
        # Use FastMCP's built-in run method with SSE transport for OpenAI compatibility
        await server.run(transport="sse", host=host, port=port)
    except KeyboardInterrupt:
        logger.info("Server stopped by user")
    except Exception as e:
        logger.error(f"Server error: {e}")
        raise
    finally:
        # Cleanup
        await cleanup()


async def main():
    """Main server entry point"""
    await initialize_and_run()


if __name__ == "__main__":
    asyncio.run(main())