#!/usr/bin/env python3
"""
Simple validation script for the remote Owlet MCP server

This script performs basic validation checks to ensure the server can:
- Import successfully without errors
- Create server instance
- Basic security feature validation
"""

import asyncio
import logging
import os
import sys

# Set up test environment
sys.path.append('.')
os.environ.setdefault('OWLET_USER', 'test@example.com')
os.environ.setdefault('OWLET_PASSWORD', 'testpassword')

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

async def validate_server():
    """Validate server can be imported and created"""
    logger.info("🔍 Validating remote MCP server...")
    
    try:
        # Test 1: Import validation
        logger.info("1. Testing imports...")
        from remote_mcp_server import create_server
        logger.info("   ✓ Server module imported successfully")
        
        # Test 2: Server creation
        logger.info("2. Testing server creation...")
        server = await create_server()
        assert server is not None
        logger.info("   ✓ Server instance created successfully")
        
        # Test 3: Security features
        logger.info("3. Testing security features...")
        from remote_mcp_server import validate_query, sanitize_output
        
        # Test input validation
        assert not validate_query(""), "Empty query should be invalid"
        assert validate_query("valid query"), "Valid query should be accepted"
        logger.info("   ✓ Input validation working")
        
        # Test output sanitization
        test_data = {"heart_rate": 120, "password": "secret", "token": "abc123"}
        sanitized = sanitize_output(test_data)
        assert "password" not in sanitized, "Password should be removed"
        assert "heart_rate" in sanitized, "Valid data should be preserved"
        logger.info("   ✓ Output sanitization working")
        
        # Test 4: Server configuration
        logger.info("4. Testing server configuration...")
        assert hasattr(server, 'name') or hasattr(server, '_name'), "Server should have name attribute"
        logger.info("   ✓ Server properly configured")
        
        logger.info("\n🎉 All validation checks passed!")
        logger.info("✅ Remote MCP server is ready for deployment")
        return True
        
    except Exception as e:
        logger.error(f"\n❌ Validation failed: {e}")
        return False

def main():
    """Main validation runner"""
    try:
        result = asyncio.run(validate_server())
        if result:
            print("\n" + "="*50)
            print("🚀 DEPLOYMENT READY")
            print("="*50)
            print("Your Owlet MCP server is validated and ready!")
            print("\nNext steps:")
            print("1. Deploy to your chosen platform (Render, Railway, Heroku)")
            print("2. Set environment variables (OWLET_USER, OWLET_PASSWORD)")
            print("3. Test with OpenAI ChatGPT integration")
            print("4. Configure your MCP client connection")
        else:
            print("\n" + "="*50)
            print("❌ VALIDATION FAILED")
            print("="*50)
            print("Please fix the issues before deployment.")
        
        sys.exit(0 if result else 1)
        
    except KeyboardInterrupt:
        logger.info("Validation interrupted by user")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Validation runner failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()