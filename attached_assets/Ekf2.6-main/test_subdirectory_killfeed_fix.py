#!/usr/bin/env python3
"""
Test Subdirectory Killfeed Fix
Test the corrected killfeed path that searches all subdirectories under deathlogs
"""

import asyncio
import logging
from bot.utils.simple_killfeed_processor import SimpleKillfeedProcessor

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def test_subdirectory_killfeed():
    """Test killfeed discovery with subdirectory searching"""
    
    # Test server config
    server_config = {
        'host': '79.127.236.1',
        'server_id': '24242',
        'name': 'Emerald EU',
        'port': 8822,
        'username': 'baked',
        'auth_method': 'modern_secure'
    }
    
    guild_id = 1219706687980568769
    
    logger.info("=== Testing Subdirectory Killfeed Discovery ===")
    
    try:
        # Create processor
        processor = SimpleKillfeedProcessor(guild_id, server_config)
        
        logger.info(f"Killfeed path: {processor._get_killfeed_path()}")
        
        # Test CSV file discovery
        logger.info("Testing CSV file discovery...")
        newest_file = await processor._discover_newest_csv_file()
        
        if newest_file:
            logger.info(f"✅ Found newest killfeed file: {newest_file}")
            if processor._current_subdir:
                logger.info(f"✅ Found in subdirectory: {processor._current_subdir}")
            else:
                logger.info("✅ Found in root deathlogs directory")
        else:
            logger.error("❌ No killfeed files found")
            return
        
        # Test processing
        logger.info("Testing killfeed processing...")
        
        def progress_callback(message):
            logger.info(f"Progress: {message}")
        
        results = await processor.process_server_killfeed(progress_callback)
        
        logger.info(f"Processing results: {results}")
        
        if results.get('events_processed', 0) > 0:
            logger.info(f"✅ Successfully processed {results['events_processed']} killfeed events")
        else:
            logger.warning("⚠️ No killfeed events processed")
            
    except Exception as e:
        logger.error(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_subdirectory_killfeed())