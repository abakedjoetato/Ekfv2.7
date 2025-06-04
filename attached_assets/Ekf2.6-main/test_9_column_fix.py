#!/usr/bin/env python3

"""
Test 9-Column CSV Format Fix
Directly test the simple killfeed processor with the corrected 9-column format
"""

import asyncio
import logging
import os
from motor.motor_asyncio import AsyncIOMotorClient
from bot.utils.simple_killfeed_processor import SimpleKillfeedProcessor, MultiServerSimpleKillfeedProcessor
from bot.models.database import DatabaseManager

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def test_9_column_csv_fix():
    """Test the 9-column CSV format fix directly"""
    try:
        logger.info("=== Testing 9-Column CSV Format Fix ===")
        
        # Test server configuration directly
        guild_id = 1219706687980568769
        test_server = {
            'name': 'Emerald EU',
            'host': '79.127.236.1',
            'port': 8822,
            'username': 'baked',
            'ssh_password': os.environ.get('SSH_PASSWORD'),
            'log_path': './79.127.236.1_7020/actual1/Deadside.log',
            'killfeed_path': './79.127.236.1_7020/actual1/deathlogs/'
        }
        servers = [test_server]
        
        logger.info(f"Found {len(servers)} servers for guild {guild_id}")
        
        if not servers:
            logger.error("No servers found for testing")
            return
        
        # Test the multi-server processor
        processor = MultiServerSimpleKillfeedProcessor(guild_id)
        
        def progress_callback(message):
            logger.info(f"Progress: {message}")
        
        results = await processor.process_available_servers(servers, progress_callback)
        
        logger.info("=== RESULTS ===")
        logger.info(f"Processing results: {results}")
        
        # Check for actual killfeed events
        total_events = 0
        for server_name, result in results.items():
            if isinstance(result, dict) and 'events_found' in result:
                events = result['events_found']
                total_events += events
                logger.info(f"Server {server_name}: {events} killfeed events found")
        
        if total_events > 0:
            logger.info(f"✅ SUCCESS: Found {total_events} total killfeed events with 9-column format")
        else:
            logger.warning("❌ ISSUE: Still finding 0 events - format may need further adjustment")
            
    except Exception as e:
        logger.error(f"Test failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_9_column_csv_fix())