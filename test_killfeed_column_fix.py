#!/usr/bin/env python3

"""
Test Killfeed Column Fix
Force a killfeed parser run to test the corrected 9+ column CSV parsing
"""

import asyncio
import logging
import os
from motor.motor_asyncio import AsyncIOMotorClient
from bot.parsers.scalable_killfeed_parser import ScalableKillfeedParser

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class MockBot:
    def __init__(self):
        self.mongo_client = AsyncIOMotorClient(os.environ.get('MONGO_URI'))
        from bot.models.database import DatabaseManager
        self.db_manager = DatabaseManager(self.mongo_client)

async def test_column_fix():
    """Test the killfeed column count fix by forcing a parser run"""
    try:
        logger.info("=== Testing Killfeed Column Count Fix ===")
        
        # Initialize killfeed parser
        bot = MockBot()
        killfeed_parser = ScalableKillfeedParser(bot)
        
        # Force a killfeed processing run
        logger.info("Forcing killfeed parser run with column fix...")
        
        await killfeed_parser.run_killfeed_parser()
        
        logger.info("Killfeed parser run completed - check logs for successful event detection")
        
    except Exception as e:
        logger.error(f"Test failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_column_fix())