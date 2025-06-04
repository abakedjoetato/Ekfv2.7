#!/usr/bin/env python3
"""
Test Simple Killfeed Processor
Verify the simplified processor works correctly with file discovery and state management
"""

import asyncio
import logging
import sys
sys.path.insert(0, '/home/runner/workspace')

from bot.utils.simple_killfeed_processor import SimpleKillfeedProcessor
from bot.models.database import DatabaseManager
from bot.utils.connection_pool import GlobalConnectionManager

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def test_simple_killfeed_processor():
    """Test the simple killfeed processor"""
    try:
        # Initialize database
        db_manager = DatabaseManager()
        await db_manager.initialize()
        
        # Initialize connection manager
        connection_manager = GlobalConnectionManager()
        
        # Get server configuration
        guild_configs = await db_manager.get_all_guild_configs()
        if not guild_configs:
            logger.error("No guild configurations found")
            return
        
        guild_config = guild_configs[0]
        guild_id = guild_config.get('guild_id')
        servers = guild_config.get('servers', [])
        
        if not servers:
            logger.error("No servers configured")
            return
        
        server_config = servers[0]
        logger.info(f"Testing simple killfeed processor for {server_config.get('name')}")
        
        # Create processor
        processor = SimpleKillfeedProcessor(guild_id, server_config)
        
        # Test killfeed processing
        results = await processor.process_server_killfeed()
        
        # Log results
        logger.info(f"Processing results: {results}")
        
        if results['success']:
            logger.info(f"SUCCESS: Found {results['events_found']} killfeed events")
            logger.info(f"Newest file: {results['newest_file']}")
            if results['file_transition']:
                logger.info("File transition was handled correctly")
        else:
            logger.error(f"FAILED: {results.get('error', 'Unknown error')}")
        
    except Exception as e:
        logger.error(f"Test failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_simple_killfeed_processor())