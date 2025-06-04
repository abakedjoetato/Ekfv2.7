#!/usr/bin/env python3

"""
Test Complete Killfeed Delivery Pipeline
Comprehensive test to identify where killfeed events fail to reach Discord
"""

import asyncio
import logging
import os
from motor.motor_asyncio import AsyncIOMotorClient
from bot.parsers.scalable_killfeed_parser import ScalableKillfeedParser

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class MockBot:
    def __init__(self):
        self.mongo_client = AsyncIOMotorClient(os.environ.get('MONGO_URI'))
        from bot.models.database import DatabaseManager
        self.db_manager = DatabaseManager(self.mongo_client)
        
    def get_channel(self, channel_id):
        """Mock channel retrieval with detailed logging"""
        logger.info(f"🔍 Bot.get_channel called for channel ID: {channel_id}")
        return MockChannel(channel_id)

class MockChannel:
    def __init__(self, channel_id):
        self.id = channel_id
        logger.info(f"📄 MockChannel created for ID: {channel_id}")
        
    async def send(self, content=None, embed=None, file=None):
        """Mock sending with detailed tracking"""
        if embed:
            logger.info(f"✅ SUCCESSFUL DELIVERY to channel {self.id}")
            logger.info(f"   Embed title: {embed.title}")
            logger.info(f"   Embed description: {embed.description[:100]}...")
        else:
            logger.info(f"✅ SUCCESSFUL MESSAGE to channel {self.id}: {content}")
        return MockMessage()

class MockMessage:
    def __init__(self):
        self.id = 12345

async def test_delivery_pipeline():
    """Test complete killfeed delivery pipeline with detailed tracking"""
    try:
        logger.info("=== Testing Complete Killfeed Delivery Pipeline ===")
        
        # Initialize bot with proper instance
        bot = MockBot()
        killfeed_parser = ScalableKillfeedParser(bot)
        
        logger.info("Bot instance created successfully")
        logger.info(f"Bot has db_manager: {hasattr(bot, 'db_manager')}")
        logger.info(f"Parser has bot: {hasattr(killfeed_parser, 'bot')}")
        
        # Force complete killfeed processing
        logger.info("Starting killfeed parser run...")
        
        await killfeed_parser.run_killfeed_parser()
        
        logger.info("Killfeed parser completed - check logs for delivery results")
        
    except Exception as e:
        logger.error(f"Pipeline test failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_delivery_pipeline())