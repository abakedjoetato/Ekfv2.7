#!/usr/bin/env python3

"""
Verify Killfeed Working - Test complete killfeed pipeline end-to-end
"""

import asyncio
import logging
import os
from motor.motor_asyncio import AsyncIOMotorClient

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def verify_killfeed():
    """Verify the killfeed system is working correctly"""
    try:
        logger.info("=== Verifying Killfeed System ===")
        
        # Connect to database to check parser state
        mongo_client = AsyncIOMotorClient(os.environ.get('MONGO_URI'))
        db = mongo_client.emerald_killfeed
        
        guild_id = 1219706687980568769
        
        # Check parser state for killfeed
        parser_state = await db.parser_states.find_one({
            "guild_id": guild_id,
            "server_id": "7020",
            "parser_type": "killfeed"
        })
        
        logger.info(f"Current killfeed parser state: {parser_state}")
        
        # Check guild configuration
        guild_config = await db.guild_configs.find_one({"guild_id": guild_id})
        server_channels = guild_config.get("server_channels", {}) if guild_config else {}
        
        # Check if killfeed channel is configured
        killfeed_channel = None
        if "Emerald EU" in server_channels:
            killfeed_channel = server_channels["Emerald EU"].get("killfeed")
        elif "default" in server_channels:
            killfeed_channel = server_channels["default"].get("killfeed")
        
        logger.info(f"Killfeed channel configured: {killfeed_channel}")
        
        # Force a killfeed parser run
        logger.info("Forcing killfeed parser run...")
        
        from bot.parsers.scalable_killfeed_parser import ScalableKillfeedParser
        from bot.models.database import DatabaseManager
        
        class MockBot:
            def __init__(self):
                self.mongo_client = mongo_client
                self.db_manager = DatabaseManager(mongo_client)
                
            def get_channel(self, channel_id):
                logger.info(f"Channel {channel_id} requested for killfeed delivery")
                return MockChannel(channel_id)
        
        class MockChannel:
            def __init__(self, channel_id):
                self.id = channel_id
                
            async def send(self, content=None, embed=None, file=None):
                if embed:
                    logger.info(f"✅ KILLFEED EVENT DELIVERED to channel {self.id}: {embed.title}")
                return MockMessage()
        
        class MockMessage:
            def __init__(self):
                self.id = 12345
        
        bot = MockBot()
        killfeed_parser = ScalableKillfeedParser(bot)
        
        # Run killfeed parser
        await killfeed_parser.run_killfeed_parser()
        
        # Check updated parser state
        updated_state = await db.parser_states.find_one({
            "guild_id": guild_id,
            "server_id": "7020",
            "parser_type": "killfeed"
        })
        
        logger.info(f"Updated killfeed parser state: {updated_state}")
        
        mongo_client.close()
        
        logger.info("✅ Killfeed verification completed")
        
    except Exception as e:
        logger.error(f"Verification failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(verify_killfeed())