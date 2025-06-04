#!/usr/bin/env python3
"""
Direct Killfeed Parser Test
Test the killfeed parser directly to verify it's working with the corrected path structure
"""

import asyncio
import logging
import sys
import os
from datetime import datetime
from bot.models.database import DatabaseManager
from motor.motor_asyncio import AsyncIOMotorClient

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class MockBot:
    def __init__(self, mongo_client):
        self.mongo_client = mongo_client
        self.db_manager = DatabaseManager(mongo_client)
        
    def get_channel(self, channel_id):
        return MockChannel(channel_id)

class MockChannel:
    def __init__(self, channel_id):
        self.id = channel_id
        
    async def send(self, content=None, embed=None, file=None):
        if embed:
            logger.info(f"KILLFEED EVENT: {embed.title} delivered to channel {self.id}")
        return MockMessage()

class MockMessage:
    def __init__(self):
        self.id = 12345

async def test_killfeed_parser_direct():
    """Test killfeed parser directly"""
    
    logger.info("=== Testing Killfeed Parser Directly ===")
    
    try:
        # Connect to database
        mongo_uri = os.getenv('MONGO_URI')
        if not mongo_uri:
            logger.error("MONGO_URI not found in environment")
            return False
            
        mongo_client = AsyncIOMotorClient(mongo_uri)
        
        # Create mock bot
        bot = MockBot(mongo_client)
        
        # Import and create killfeed parser
        from bot.parsers.scalable_killfeed_parser import ScalableKillfeedParser
        killfeed_parser = ScalableKillfeedParser(bot)
        
        logger.info("Killfeed parser created successfully")
        
        # Run killfeed parser
        logger.info("Running killfeed parser...")
        await killfeed_parser.run_killfeed_parser()
        
        logger.info("✅ Killfeed parser test completed successfully")
        
        mongo_client.close()
        return True
        
    except Exception as e:
        logger.error(f"❌ Killfeed parser test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = asyncio.run(test_killfeed_parser_direct())
    if success:
        print("\n🎉 KILLFEED PARSER TEST PASSED")
    else:
        print("\n❌ KILLFEED PARSER TEST FAILED")
        sys.exit(1)