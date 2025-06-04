#!/usr/bin/env python3
"""
Direct Killfeed CSV Test - Check actual CSV content and parser logic
"""

import asyncio
import logging
import os
from datetime import datetime, timezone

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def test_killfeed_csv():
    """Test killfeed CSV content directly"""
    try:
        # Import bot components
        from motor.motor_asyncio import AsyncIOMotorClient
        from bot.models.database import DatabaseManager
        from bot.utils.simple_killfeed_processor import SimpleKillfeedProcessor
        from bot.utils.connection_pool import connection_manager
        from bot.utils.shared_parser_state import initialize_shared_state_manager
        
        # Setup database
        mongo_client = AsyncIOMotorClient(os.getenv("MONGO_URI"))
        db_manager = DatabaseManager(mongo_client)
        initialize_shared_state_manager(db_manager)
        
        # Get guild config
        guild_id = 1219706687980568769
        guild_config = await db_manager.get_guild(guild_id)
        
        if not guild_config or not guild_config.get('servers'):
            logger.error("No guild configuration found")
            return
        
        server_config = guild_config['servers'][0]
        
        # Create mock bot for the processor
        class MockBot:
            def __init__(self, db_manager):
                self.db_manager = db_manager
            
            def get_channel(self, channel_id):
                logger.info(f"Mock: Getting channel {channel_id}")
                return MockChannel(channel_id)
        
        class MockChannel:
            def __init__(self, channel_id):
                self.id = channel_id
            
            async def send(self, embed=None, content=None):
                logger.info(f"Mock: Sending to channel {self.id}")
                if embed:
                    logger.info(f"  Embed title: {embed.title}")
                    logger.info(f"  Embed description: {embed.description}")
                    for field in embed.fields:
                        logger.info(f"  Field: {field.name} = {field.value}")
                if content:
                    logger.info(f"  Content: {content}")
        
        # Initialize connection manager and processor
        await connection_manager.start()
        mock_bot = MockBot(db_manager)
        processor = SimpleKillfeedProcessor(guild_id, server_config, mock_bot)
        
        logger.info("=== Testing Killfeed CSV Processing ===")
        
        # Process killfeed
        results = await processor.process_server_killfeed()
        
        logger.info(f"Results: {results}")
        
        if results.get('success'):
            events_processed = results.get('events_processed', 0)
            logger.info(f"✅ Successfully processed {events_processed} events")
            
            if events_processed == 0:
                logger.warning("⚠️ No events were processed - CSV file may be empty or no new data")
        else:
            logger.error(f"❌ Processing failed: {results.get('error', 'Unknown error')}")
        
        # Clean up
        await connection_manager.stop()
        await mongo_client.close()
        
    except Exception as e:
        logger.error(f"Test failed: {e}")
        import traceback
        logger.error(traceback.format_exc())

if __name__ == "__main__":
    asyncio.run(test_killfeed_csv())