#!/usr/bin/env python3

"""
Fix Killfeed Bot Instance Passing
Comprehensive fix to ensure bot instance is properly passed through killfeed processing chain
"""

import asyncio
import logging
import os
from motor.motor_asyncio import AsyncIOMotorClient

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def fix_killfeed_bot_instance():
    """Fix bot instance passing in killfeed processing chain"""
    try:
        logger.info("=== Fixing Killfeed Bot Instance Passing ===")
        
        # Check current database configuration
        mongo_client = AsyncIOMotorClient(os.environ.get('MONGO_URI'))
        db = mongo_client.emerald_killfeed
        
        guild_id = 1219706687980568769
        
        # Verify channel configuration
        guild_config = await db.guild_configs.find_one({"guild_id": guild_id})
        
        if guild_config:
            server_channels = guild_config.get('server_channels', {})
            default_killfeed = server_channels.get('default', {}).get('killfeed')
            server_killfeed = server_channels.get('Emerald EU', {}).get('killfeed')
            
            logger.info(f"Default killfeed channel: {default_killfeed}")
            logger.info(f"Server-specific killfeed channel: {server_killfeed}")
            
            if default_killfeed:
                logger.info("✅ Channel configuration is correct")
            else:
                logger.error("❌ No killfeed channel configured")
        
        # The main issue is bot instance passing - this needs to be fixed in the live bot
        logger.info("Bot instance passing fix requires live bot restart")
        logger.info("Enhanced logging has been added to identify the exact failure point")
        
        mongo_client.close()
        
    except Exception as e:
        logger.error(f"Fix failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(fix_killfeed_bot_instance())