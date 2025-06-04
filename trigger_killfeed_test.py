#!/usr/bin/env python3
"""
Trigger Killfeed Test - Manual execution to verify subdirectory path fix
"""

import asyncio
import logging
from bot.parsers.scalable_killfeed_parser import ScalableKillfeedParser
from bot.models.database import db

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def trigger_killfeed_test():
    """Manually trigger killfeed parser to test subdirectory path fix"""
    
    logger.info("=== Manual Killfeed Parser Test ===")
    
    try:
        # Initialize database
        await db.init()
        logger.info("Database initialized")
        
        # Create killfeed parser
        parser = ScalableKillfeedParser()
        logger.info("Killfeed parser created")
        
        # Run killfeed parser
        logger.info("Running killfeed parser...")
        await parser.run_killfeed_parser()
        
        logger.info("✅ Killfeed parser test completed")
        
    except Exception as e:
        logger.error(f"❌ Killfeed parser test failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(trigger_killfeed_test())