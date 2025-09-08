# Owlet Baby Monitor Remote MCP Server

🍼 **A comprehensive remote MCP server for OpenAI ChatGPT integration**

This remote Model Context Protocol (MCP) server provides real-time access to Owlet baby monitoring data through OpenAI ChatGPT, deep research, and API integrations. Built specifically for OpenAI's MCP requirements with `search` and `fetch` tools.

## 🌟 Features

- **Real-time Baby Monitoring**: Heart rate, oxygen saturation, temperature tracking
- **Smart Alerts**: Critical and standard alert monitoring with intelligent assessments  
- **Device Management**: Battery status, connectivity, base station control
- **Wellness Analytics**: Comprehensive health summaries and recommendations
- **Historical Data**: Session tracking and trend analysis
- **Live Feed Integration**: Access to real-time monitoring streams
- **OpenAI Compatible**: Works with ChatGPT connectors and deep research
- **Secure API**: Environment-based authentication with rate limiting

## 🚀 Quick Deploy

### Deploy to Render (Recommended)
[![Deploy to Render](https://render.com/images/deploy-to-render-button.svg)](https://render.com/deploy?repo=https://github.com/victorpicaud/pyowletapi)

### Deploy to Railway
[![Deploy on Railway](https://railway.app/button.svg)](https://railway.app/template/example)

### Deploy to Heroku
[![Deploy to Heroku](https://www.herokucdn.com/deploy/button.svg)](https://heroku.com/deploy?template=https://github.com/victorpicaud/pyowletapi)

## 📋 Prerequisites

- Valid Owlet account with registered Smart Sock devices
- OpenAI account for ChatGPT integration
- Hosting platform account (Render, Railway, Heroku, etc.)

## 🔧 Environment Variables

Set these environment variables in your hosting platform:

```env
OWLET_USER=your_email@example.com
OWLET_PASSWORD=your_password
OWLET_REGION=world  # or "europe" for EU accounts
PORT=8000  # Usually set automatically by hosting platform
HOST=0.0.0.0  # Usually set automatically
```

## 🔌 OpenAI Integration

### ChatGPT Connectors

1. **In ChatGPT Settings**:
   - Navigate to "Connectors" 
   - Click "Add Connector"
   - Enter your deployed server URL with `/sse/` suffix
   - Example: `https://your-app.render.com/sse/`

2. **Configure Tools**:
   - Enable "search" and "fetch" tools
   - Set approval to "never" for deep research

### API Integration

Use with OpenAI's Responses API:

```bash
curl https://api.openai.com/v1/responses \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $OPENAI_API_KEY" \
  -d '{
  "model": "o4-mini-deep-research",
  "input": [
    {
      "role": "user",
      "content": [
        {
          "type": "input_text", 
          "text": "How is my baby doing? Check current vitals and any alerts."
        }
      ]
    }
  ],
  "tools": [
    {
      "type": "mcp",
      "server_url": "https://your-app.render.com/sse/",
      "allowed_tools": ["search", "fetch"],
      "require_approval": "never"
    }
  ]
}'
```

## 🔍 Available Search Queries

The server supports natural language searches:

- **"current vitals"** - Real-time heart rate, oxygen, temperature
- **"active alerts"** - Check for monitoring alerts  
- **"device status"** - Battery, connectivity, base station
- **"wellness summary"** - Comprehensive health overview
- **"historical data"** - Trends and session history
- **"live feed"** - Access to real-time monitoring

## 📊 Example Usage

### In ChatGPT:
```
"How is my baby doing right now? Check vitals and any alerts."

"Show me a wellness summary for the past monitoring session."

"Is the Owlet device working properly? Check battery and connection."
```

### Search Results Format:
```json
{
  "results": [
    {
      "id": "vitals_DEVICE123",
      "title": "Current Vitals - Baby Monitor",
      "text": "HR: 120 BPM, O2: 98%, Temp: 36.5°C",
      "url": "https://app.owletdata.com/device/DEVICE123"
    }
  ]
}
```

### Fetch Results Format:
```json
{
  "id": "vitals_DEVICE123",
  "title": "Current Vital Signs - Baby Monitor", 
  "text": "{detailed JSON data with all vitals, timestamps, status}",
  "url": "https://app.owletdata.com/device/DEVICE123",
  "metadata": {
    "source": "owlet_api",
    "device_serial": "DEVICE123",
    "data_type": "vitals",
    "timestamp": "2025-09-08T10:30:00Z"
  }
}
```

## 🛠️ Local Development

1. **Clone and setup**:
   ```bash
   git clone https://github.com/victorpicaud/pyowletapi.git
   cd pyowletapi
   pip install -r requirements-remote.txt
   ```

2. **Configure environment**:
   ```bash
   cp .env.example .env
   # Edit .env with your Owlet credentials
   ```

3. **Run server**:
   ```bash
   python remote_mcp_server.py
   ```

4. **Test endpoints**:
   ```bash
   # Server will be available at http://localhost:8000/sse/
   curl http://localhost:8000/sse/
   ```

## 🔒 Security Features

- **Environment Variables**: Credentials stored securely
- **HTTPS Required**: All production deployments use HTTPS
- **Rate Limiting**: Built-in API call throttling  
- **Input Validation**: Comprehensive request validation
- **Error Handling**: Secure error messages without data leakage
- **Audit Logging**: All API calls logged for monitoring

## 🏗️ Deployment Platforms

### Render (Recommended)
- Free tier available
- Automatic HTTPS
- Easy environment variable management
- Git-based deployments

### Railway
- Simple setup with railway.toml
- Automatic scaling
- Built-in monitoring

### Heroku  
- Established platform
- Add-on ecosystem
- Procfile-based deployment

### Docker
- Use provided Dockerfile
- Deploy to any container platform
- Kubernetes compatible

## 📱 Supported Devices

- **Owlet Smart Sock 3**: Full feature support
- **Owlet Smart Sock 2**: Core monitoring features  
- **Base Station**: Remote control and status

## ⚠️ Important Disclaimers

**Medical Disclaimer**: This MCP server is a third-party tool for accessing Owlet data. It is NOT a medical device and should not replace:
- Professional medical advice
- Continuous medical monitoring  
- Emergency medical services
- Attentive parental care

**Security**: 
- Only connect to trusted MCP servers
- This server connects directly to official Owlet APIs
- No data is stored or transmitted to third parties
- Review hosting platform security policies

**Data Privacy**:
- Server uses your existing Owlet account permissions
- Data is only cached temporarily for performance
- All communications use HTTPS encryption

## 🐛 Troubleshooting

### Common Issues

1. **Authentication Errors**:
   - Verify Owlet credentials in environment variables
   - Check if you can log into the Owlet app
   - Ensure correct region setting

2. **No Devices Found**:
   - Confirm devices are set up in Owlet app
   - Check device connectivity and battery

3. **Server Not Responding**:
   - Check hosting platform logs
   - Verify environment variables are set
   - Ensure server URL ends with `/sse/`

### Logs and Monitoring

Check your hosting platform's logs for debugging:
- Render: Dashboard → Service → Logs
- Railway: Dashboard → Project → Deployments  
- Heroku: Dashboard → App → More → View logs

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Add improvements or fixes
4. Test with your Owlet devices
5. Submit a pull request

## 📄 License

This project extends the pyowletapi library. See LICENSE file for details.

## 🆘 Support

- **Owlet Device Issues**: Contact Owlet customer support
- **Server Issues**: Open an issue in this repository  
- **OpenAI Integration**: Contact OpenAI support
- **Hosting Issues**: Contact your hosting platform support

---

**Made with ❤️ for parents who want smart baby monitoring integrated with AI assistants.**