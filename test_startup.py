#!/usr/bin/env python3
"""
Test the remote server startup without actually running it
This validates the server can initialize without asyncio conflicts
"""

import os
import sys
import asyncio
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def test_server_init():
    """Test server initialization"""
    
    # Set up test environment
    os.environ['OWLET_USER'] = 'test@example.com'
    os.environ['OWLET_PASSWORD'] = 'testpassword'
    os.environ['PORT'] = '8000'
    os.environ['HOST'] = '0.0.0.0'
    
    try:
        # Import and create server
        from remote_mcp_server import create_server
        server = await create_server()
        
        logger.info("✅ Server created successfully")
        logger.info("✅ No asyncio conflicts detected")
        
        # Test that server has the required attributes
        assert hasattr(server, 'run'), "Server should have run method"
        logger.info("✅ Server has required methods")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Server initialization failed: {e}")
        return False

def main():
    """Main test function"""
    try:
        result = asyncio.run(test_server_init())
        if result:
            print("\n🎉 SERVER STARTUP TEST PASSED")
            print("Ready for deployment!")
        else:
            print("\n❌ SERVER STARTUP TEST FAILED")
        sys.exit(0 if result else 1)
    except Exception as e:
        logger.error(f"Test failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()