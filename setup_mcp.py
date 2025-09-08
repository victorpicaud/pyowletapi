#!/usr/bin/env python3
"""
Owlet MCP Server Setup Script

This script helps set up the Owlet MCP server by:
1. Checking dependencies
2. Validating credentials
3. Testing the connection
4. Generating Claude Desktop configuration
"""

import asyncio
import os
import sys
import json
from pathlib import Path

def check_dependencies():
    """Check if all required dependencies are installed."""
    print("🔍 Checking dependencies...")
    
    missing_deps = []
    
    try:
        import aiohttp
        print("  ✅ aiohttp")
    except ImportError:
        missing_deps.append("aiohttp")
        print("  ❌ aiohttp")
    
    try:
        from mcp.server.fastmcp import FastMCP
        print("  ✅ mcp")
    except ImportError:
        missing_deps.append("mcp[cli]")
        print("  ❌ mcp")
    
    try:
        from dotenv import load_dotenv
        print("  ✅ python-dotenv")
    except ImportError:
        print("  ⚠️ python-dotenv (optional)")
    
    if missing_deps:
        print(f"\n❌ Missing dependencies: {', '.join(missing_deps)}")
        print("Please install them with:")
        print(f"pip install {' '.join(missing_deps)}")
        return False
    
    print("✅ All required dependencies found")
    return True


def load_credentials():
    """Load and validate Owlet credentials."""
    print("\n🔐 Checking credentials...")
    
    # Try to load from .env file
    env_file = Path(".env")
    if env_file.exists():
        try:
            from dotenv import load_dotenv
            load_dotenv()
            print("  ✅ Loaded .env file")
        except ImportError:
            print("  ⚠️ .env file found but python-dotenv not installed")
    
    user = os.getenv("OWLET_USER")
    password = os.getenv("OWLET_PASSWORD")
    region = os.getenv("OWLET_REGION", "world")
    
    if not user:
        print("  ❌ OWLET_USER not set")
        user = input("Enter your Owlet email: ").strip()
    else:
        print(f"  ✅ OWLET_USER: {user}")
    
    if not password:
        print("  ❌ OWLET_PASSWORD not set")
        import getpass
        password = getpass.getpass("Enter your Owlet password: ").strip()
    else:
        print("  ✅ OWLET_PASSWORD: [hidden]")
    
    print(f"  ✅ OWLET_REGION: {region}")
    
    return user, password, region


async def test_connection(user, password, region):
    """Test connection to Owlet API."""
    print("\n🌐 Testing Owlet API connection...")
    
    try:
        # Import here to avoid dependency issues
        sys.path.insert(0, str(Path(__file__).parent))
        from src.pyowletapi.api import OwletAPI
        
        api = OwletAPI(region=region, user=user, password=password)
        
        print("  🔑 Authenticating...")
        await api.authenticate()
        print("  ✅ Authentication successful")
        
        print("  📱 Fetching devices...")
        devices_response = await api.get_devices()
        devices = devices_response["response"]
        
        print(f"  ✅ Found {len(devices)} device(s)")
        for i, device_data in enumerate(devices, 1):
            device = device_data["device"]
            print(f"    {i}. {device.get('product_name', 'Unknown')} ({device.get('dsn', 'Unknown')})")
        
        await api.close()
        return True
        
    except Exception as e:
        print(f"  ❌ Connection failed: {str(e)}")
        return False


def generate_claude_config(user, password, region):
    """Generate Claude Desktop configuration."""
    print("\n📝 Generating Claude Desktop configuration...")
    
    script_path = Path(__file__).parent / "mcp_server.py"
    absolute_path = str(script_path.resolve())
    
    config = {
        "mcpServers": {
            "owlet-monitor": {
                "command": "python",
                "args": [absolute_path],
                "env": {
                    "OWLET_USER": user,
                    "OWLET_PASSWORD": password,
                    "OWLET_REGION": region
                }
            }
        }
    }
    
    # Determine Claude Desktop config path
    if sys.platform == "win32":
        config_dir = Path(os.getenv("APPDATA")) / "Claude"
    elif sys.platform == "darwin":
        config_dir = Path.home() / "Library" / "Application Support" / "Claude"
    else:
        config_dir = Path.home() / ".config" / "claude"
    
    config_file = config_dir / "claude_desktop_config.json"
    
    print(f"  📍 Config file location: {config_file}")
    
    # Check if config file exists and merge
    if config_file.exists():
        try:
            with open(config_file, 'r') as f:
                existing_config = json.load(f)
            
            if "mcpServers" not in existing_config:
                existing_config["mcpServers"] = {}
            
            existing_config["mcpServers"]["owlet-monitor"] = config["mcpServers"]["owlet-monitor"]
            config = existing_config
            print("  ✅ Merged with existing configuration")
            
        except Exception as e:
            print(f"  ⚠️ Could not read existing config: {e}")
            print("  📝 Creating new configuration")
    
    # Create config directory if it doesn't exist
    config_dir.mkdir(parents=True, exist_ok=True)
    
    # Write configuration
    try:
        with open(config_file, 'w') as f:
            json.dump(config, f, indent=2)
        print("  ✅ Configuration written successfully")
        print(f"  📁 Path: {config_file}")
        
        return True
        
    except Exception as e:
        print(f"  ❌ Failed to write configuration: {e}")
        print("\n📝 Manual configuration:")
        print(json.dumps(config, indent=2))
        return False


def create_env_file(user, password, region):
    """Create .env file with credentials."""
    env_file = Path(".env")
    
    if env_file.exists():
        response = input("\n.env file already exists. Overwrite? (y/N): ").strip().lower()
        if response != 'y':
            return
    
    try:
        with open(env_file, 'w') as f:
            f.write(f"# Owlet MCP Server Configuration\n")
            f.write(f"OWLET_USER={user}\n")
            f.write(f"OWLET_PASSWORD={password}\n")
            f.write(f"OWLET_REGION={region}\n")
            f.write(f"LOG_LEVEL=INFO\n")
        
        print(f"✅ Created .env file: {env_file.absolute()}")
        
    except Exception as e:
        print(f"❌ Failed to create .env file: {e}")


async def main():
    """Main setup function."""
    print("🍼 Owlet MCP Server Setup")
    print("=" * 40)
    
    # Check dependencies
    if not check_dependencies():
        return False
    
    # Load credentials
    user, password, region = load_credentials()
    
    if not user or not password:
        print("❌ Missing credentials")
        return False
    
    # Test connection
    if not await test_connection(user, password, region):
        print("\n❌ Setup failed - could not connect to Owlet API")
        print("Please check your credentials and try again")
        return False
    
    # Create .env file
    create_env_file(user, password, region)
    
    # Generate Claude config
    if generate_claude_config(user, password, region):
        print("\n✅ Setup completed successfully!")
        print("\nNext steps:")
        print("1. Restart Claude for Desktop")
        print("2. Look for the MCP tools icon in Claude")
        print("3. Try asking: 'What are my baby's current vital signs?'")
        print("\nFor troubleshooting, see README-MCP.md")
    else:
        print("\n⚠️ Setup partially completed")
        print("You may need to manually configure Claude Desktop")
    
    return True


if __name__ == "__main__":
    try:
        success = asyncio.run(main())
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\n❌ Setup cancelled")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Setup failed: {e}")
        sys.exit(1)