# Owlet Baby Monitor MCP Server

A comprehensive Model Context Protocol (MCP) server for monitoring Owlet baby devices. This server provides real-time access to vital signs, alerts, device status, and wellness monitoring through a secure API interface.

## Features

🫀 **Real-time Vital Signs Monitoring**
- Heart rate tracking
- Oxygen saturation levels  
- Skin temperature monitoring
- Sleep state detection
- Movement tracking

🚨 **Alert Management**
- Critical alerts (low oxygen, critical battery)
- Standard alerts (heart rate, battery, connectivity)
- Wellness notifications
- Alert pause status

📱 **Device Management**
- Device discovery and status
- Base station control
- Battery monitoring
- Connection status
- Firmware update notifications

📊 **Historical Data Access**
- Monitoring session tracking
- Historical trends and patterns
- Data export information
- Wellness analysis

🌐 **Live Feed Integration**
- Live monitoring access information
- Mobile app integration guidance
- Web dashboard links
- Real-time data streaming

## Installation

### Prerequisites

- Python 3.10 or higher
- Valid Owlet account with registered devices
- Claude for Desktop (for testing)

### Setup

1. **Clone and navigate to the repository**:
   ```bash
   cd pyowletapi
   ```

2. **Install MCP server dependencies**:
   ```bash
   pip install -r requirements-mcp.txt
   ```

3. **Create environment configuration**:
   ```bash
   cp .env.example .env
   ```

4. **Edit `.env` file with your Owlet credentials**:
   ```env
   OWLET_USER=your_email@example.com
   OWLET_PASSWORD=your_password
   OWLET_REGION=world  # or "europe" for EU accounts
   ```

### Configure Claude for Desktop

Add the following to your Claude Desktop configuration file:

**Windows**: `%APPDATA%\Claude\claude_desktop_config.json`
**macOS**: `~/Library/Application Support/Claude/claude_desktop_config.json`

```json
{
  "mcpServers": {
    "owlet-monitor": {
      "command": "python",
      "args": ["C:\\ABSOLUTE\\PATH\\TO\\pyowletapi\\mcp_server.py"],
      "env": {
        "OWLET_USER": "your_email@example.com",
        "OWLET_PASSWORD": "your_password",
        "OWLET_REGION": "world"
      }
    }
  }
}
```

**Important**: Replace `C:\\ABSOLUTE\\PATH\\TO\\pyowletapi\\` with the actual absolute path to your project directory.

## Available Tools

### 👶 Baby Monitoring Tools

#### `get_device_list`
Get a list of all available Owlet devices in your account.

#### `get_current_vitals`
Get current vital signs for a baby monitor device.
- **Parameters**: `device_serial` (optional)
- **Returns**: Heart rate, oxygen saturation, temperature, sleep state, movement

#### `get_active_alerts`
Get active alerts for a baby monitor device.
- **Parameters**: `device_serial` (optional)  
- **Returns**: Critical alerts, standard alerts, wellness notifications

#### `get_device_status`
Get comprehensive device status including connection, battery, and base station.
- **Parameters**: `device_serial` (optional)
- **Returns**: Connection status, battery levels, hardware info, monitoring status

#### `control_base_station`
Turn the base station on or off.
- **Parameters**: `action` (required: "on" or "off"), `device_serial` (optional)
- **Returns**: Success/failure status

### 📊 Data and Analysis Tools

#### `get_baby_wellness_summary`
Get a comprehensive wellness summary including all vitals, alerts, and recommendations.
- **Parameters**: `device_serial` (optional)
- **Returns**: Complete wellness assessment with guidance

#### `get_historical_data_info`
Get information about accessing historical monitoring data and trends.
- **Parameters**: `device_serial` (optional)
- **Returns**: Data access methods, retention policies, export options

#### `get_live_feed_info`
Get information about accessing live feed and camera features.
- **Parameters**: `device_serial` (optional)
- **Returns**: Live feed access instructions, app links, current monitoring status

## Usage Examples

### Basic Monitoring

**Get current vitals:**
```
What are my baby's current vital signs?
```

**Check for alerts:**
```
Are there any active alerts for my baby monitor?
```

**Get device status:**
```
What's the status of my Owlet device?
```

### Device Control

**Control base station:**
```
Turn on the base station for my Owlet monitor
```

### Comprehensive Analysis

**Get wellness summary:**
```
Give me a complete wellness summary for my baby
```

**Access historical data:**
```
How can I access my baby's historical monitoring data?
```

**Live feed information:**
```
How do I access the live feed from my Owlet monitor?
```

## Security Features

- 🔐 **Secure Authentication**: Uses official Owlet API authentication
- 🔒 **Environment Variables**: Credentials stored securely in environment variables
- 🛡️ **Error Handling**: Comprehensive error handling and logging
- 📝 **Audit Logging**: All API calls logged to stderr for debugging

## Supported Devices

- **Owlet Smart Sock 3**: Full feature support including real-time vitals
- **Owlet Smart Sock 2**: Basic monitoring features
- **Base Station**: Remote control and status monitoring

## Data Privacy

This MCP server:
- ✅ Connects directly to Owlet's official API
- ✅ Does not store or transmit your data to third parties
- ✅ Uses your existing Owlet account permissions
- ✅ Logs only to local stderr for debugging

## Troubleshooting

### Authentication Issues

1. **Invalid Credentials Error**:
   - Verify your email and password in the `.env` file
   - Ensure you can log into the Owlet app with the same credentials

2. **Region Error**:
   - Set `OWLET_REGION=europe` if you have a European Owlet account
   - Use `OWLET_REGION=world` for US/Canada/other regions

### Connection Issues

1. **No Devices Found**:
   - Ensure your devices are set up in the Owlet app
   - Check that devices are online and connected

2. **API Timeout**:
   - Check your internet connection
   - Ensure Owlet services are operational

### Claude Desktop Integration

1. **Server Not Showing Up**:
   - Restart Claude for Desktop completely
   - Check the JSON syntax in `claude_desktop_config.json`
   - Verify the absolute path to `mcp_server.py`

2. **Tool Calls Failing**:
   - Check Claude's logs: `~/Library/Logs/Claude/` (macOS) or `%APPDATA%\Claude\Logs\` (Windows)
   - Verify environment variables are correctly set

## Development

### Running the Server Manually

```bash
python mcp_server.py
```

### Testing Tools

You can test individual tools by running the server and sending JSON-RPC requests, or by using it through Claude Desktop.

### Contributing

1. Fork the repository
2. Create a feature branch
3. Add your improvements
4. Test with Claude Desktop
5. Submit a pull request

## Disclaimer

⚠️ **Important Medical Disclaimer**:

This MCP server is a third-party tool for accessing Owlet monitoring data. It is NOT a medical device and should not be used as a substitute for:

- Professional medical advice
- Continuous medical monitoring
- Emergency medical services
- Attentive parental care

Always:
- Trust your parental instincts over device readings
- Consult healthcare providers for medical concerns
- Contact emergency services immediately if your baby appears in distress
- Use this tool as a supplement to, not replacement for, responsible childcare

## License

This project extends the existing pyowletapi library. Please refer to the original license terms.

## Support

For issues related to:
- **Owlet devices**: Contact Owlet customer support
- **This MCP server**: Open an issue in this repository
- **Claude Desktop**: Contact Anthropic support