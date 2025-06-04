#!/usr/bin/env python3

"""
Test Semicolon Delimiter Fix
Force a killfeed parser run to test the corrected semicolon delimiter parsing
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

async def test_semicolon_fix():
    """Test the semicolon delimiter fix by forcing a killfeed parser run"""
    try:
        logger.info("=== Testing Semicolon Delimiter Fix ===")
        
        # Initialize killfeed parser with mock bot
        bot = MockBot()
        killfeed_parser = ScalableKillfeedParser(bot)
        
        # Force a killfeed processing run
        logger.info("Forcing killfeed parser run...")
        
        await killfeed_parser.run_killfeed_parser()
        
        logger.info("✅ Killfeed parser run completed - check logs for results")
        
    except Exception as e:
        logger.error(f"Test failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_semicolon_fix())