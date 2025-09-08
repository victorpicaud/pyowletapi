#!/usr/bin/env python3
"""
Basic test script for the Owlet MCP Server
"""

import sys
import os
from pathlib import Path

def test_imports():
    """Test if we can import required modules."""
    print("🧪 Testing imports...")
    
    try:
        import asyncio
        print("  ✅ asyncio")
    except ImportError as e:
        print(f"  ❌ asyncio: {e}")
        return False
    
    try:
        from mcp.server.fastmcp import FastMCP
        print("  ✅ mcp.server.fastmcp")
    except ImportError as e:
        print(f"  ❌ mcp.server.fastmcp: {e}")
        print("     Run: pip install mcp[cli]")
        return False
    
    try:
        from src.pyowletapi.api import OwletAPI
        print("  ✅ src.pyowletapi.api")
    except ImportError as e:
        print(f"  ❌ src.pyowletapi.api: {e}")
        return False
    
    try:
        from src.pyowletapi.sock import Sock
        print("  ✅ src.pyowletapi.sock")
    except ImportError as e:
        print(f"  ❌ src.pyowletapi.sock: {e}")
        return False
    
    return True


def test_mcp_server():
    """Test if the MCP server can be imported."""
    print("\n🧪 Testing MCP server import...")
    
    try:
        # Add current directory to path
        sys.path.insert(0, str(Path(__file__).parent))
        
        # Import the server module
        import mcp_server
        print("  ✅ mcp_server module imported")
        
        # Test if FastMCP instance exists
        if hasattr(mcp_server, 'mcp'):
            print("  ✅ FastMCP instance found")
        else:
            print("  ❌ FastMCP instance not found")
            return False
        
        return True
        
    except Exception as e:
        print(f"  ❌ Failed to import mcp_server: {e}")
        return False


def test_environment():
    """Test environment setup."""
    print("\n🧪 Testing environment...")
    
    # Check for .env file
    env_file = Path(".env")
    if env_file.exists():
        print("  ✅ .env file exists")
    else:
        print("  ⚠️ .env file not found (will use environment variables)")
    
    # Check for credentials in environment
    user = os.getenv("OWLET_USER")
    password = os.getenv("OWLET_PASSWORD")
    region = os.getenv("OWLET_REGION", "world")
    
    if user:
        print(f"  ✅ OWLET_USER: {user}")
    else:
        print("  ⚠️ OWLET_USER not set")
    
    if password:
        print("  ✅ OWLET_PASSWORD: [hidden]")
    else:
        print("  ⚠️ OWLET_PASSWORD not set")
    
    print(f"  ✅ OWLET_REGION: {region}")
    
    return True


def main():
    """Run all tests."""
    print("🍼 Owlet MCP Server Test Suite")
    print("=" * 40)
    
    all_passed = True
    
    # Test imports
    if not test_imports():
        all_passed = False
    
    # Test MCP server
    if not test_mcp_server():
        all_passed = False
    
    # Test environment
    if not test_environment():
        all_passed = False
    
    print("\n" + "=" * 40)
    
    if all_passed:
        print("✅ All basic tests passed!")
        print("\nNext steps:")
        print("1. Set up your credentials (run setup_mcp.py)")
        print("2. Configure Claude Desktop")
        print("3. Test with Claude")
    else:
        print("❌ Some tests failed!")
        print("\nPlease fix the issues above before proceeding.")
    
    return all_passed


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)