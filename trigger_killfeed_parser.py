#!/usr/bin/env python3
"""
Trigger Killfeed Parser Manually - Debug why killfeeds aren't outputting embeds
"""

import asyncio
import logging
import motor.motor_asyncio
import os
from bot.parsers.scalable_killfeed_parser import ScalableKillfeedParser

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def trigger_killfeed_parser():
    """Manually trigger the killfeed parser to debug embed output issues"""
    try:
        # Connect to database
        client = motor.motor_asyncio.AsyncIOMotorClient(os.environ.get('MONGO_URI'))
        db = client.emerald_killfeed
        
        # Get guild configuration
        guild_config = await db.guild_configs.find_one({
            'guild_id': 1219706687980568769
        })
        
        if not guild_config:
            logger.error("No guild configuration found")
            return
        
        servers = guild_config.get('servers', [])
        if not servers:
            logger.error("No servers configured")
            return
        
        logger.info(f"Found {len(servers)} servers to process for killfeeds")
        
        # Create killfeed parser instance
        killfeed_parser = ScalableKillfeedParser()
        
        # Process each server
        for server in servers:
            server_name = server.get('name', 'Unknown')
            logger.info(f"Processing killfeed for {server_name}")
            
            # Run killfeed parser for this server
            result = await killfeed_parser.process_server_killfeeds(
                guild_id=1219706687980568769,
                server_configs=[server]
            )
            
            logger.info(f"Killfeed result for {server_name}: {result}")
        
        client.close()
        logger.info("Killfeed parser trigger completed")
        
    except Exception as e:
        logger.error(f"Failed to trigger killfeed parser: {e}")
        import traceback
        logger.error(f"Full traceback: {traceback.format_exc()}")

if __name__ == "__main__":
    asyncio.run(trigger_killfeed_parser())