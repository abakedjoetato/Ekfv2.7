#!/usr/bin/env python3

"""
Debug Channel Configuration - Check current channel setup and routing logic
"""

import asyncio
import logging
import os
from motor.motor_asyncio import AsyncIOMotorClient

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def debug_channel_config():
    """Debug current channel configuration"""
    try:
        logger.info("=== Debugging Channel Configuration ===")
        
        # Connect to database
        mongo_client = AsyncIOMotorClient(os.environ.get('MONGO_URI'))
        db = mongo_client.emerald_killfeed
        
        guild_id = 1219706687980568769
        server_name = "Emerald EU"
        
        # Get current guild configuration
        guild_config = await db.guild_configs.find_one({"guild_id": guild_id})
        
        if guild_config:
            logger.info(f"=== Guild Configuration for {guild_id} ===")
            
            # Check server_channels structure
            server_channels = guild_config.get('server_channels', {})
            logger.info(f"Server channels structure: {list(server_channels.keys())}")
            
            # Check default channels
            if 'default' in server_channels:
                default_channels = server_channels['default']
                logger.info(f"Default channels: {list(default_channels.keys())}")
                killfeed_channel = default_channels.get('killfeed')
                logger.info(f"Default killfeed channel: {killfeed_channel}")
            
            # Check server-specific channels
            if server_name in server_channels:
                server_specific = server_channels[server_name]
                logger.info(f"'{server_name}' specific channels: {list(server_specific.keys())}")
                killfeed_channel = server_specific.get('killfeed')
                logger.info(f"'{server_name}' killfeed channel: {killfeed_channel}")
            else:
                logger.info(f"No server-specific channels for '{server_name}'")
            
            # Check legacy channels
            legacy_channels = guild_config.get('channels', {})
            if legacy_channels:
                logger.info(f"Legacy channels: {list(legacy_channels.keys())}")
                legacy_killfeed = legacy_channels.get('killfeed')
                logger.info(f"Legacy killfeed channel: {legacy_killfeed}")
            
            # Test channel resolution logic
            logger.info("=== Testing Channel Resolution Logic ===")
            
            # Priority 1: Server-specific
            channel_id = None
            if server_name in server_channels:
                channel_id = server_channels[server_name].get('killfeed')
                if channel_id:
                    logger.info(f"✅ FOUND: Server-specific killfeed channel {channel_id}")
            
            # Priority 2: Default server
            if not channel_id and 'default' in server_channels:
                channel_id = server_channels['default'].get('killfeed')
                if channel_id:
                    logger.info(f"✅ FOUND: Default killfeed channel {channel_id}")
            
            # Priority 3: Legacy
            if not channel_id:
                channel_id = legacy_channels.get('killfeed')
                if channel_id:
                    logger.info(f"✅ FOUND: Legacy killfeed channel {channel_id}")
            
            if not channel_id:
                logger.warning("❌ NO killfeed channel found anywhere")
            
            logger.info(f"Final resolved channel ID: {channel_id}")
        
        else:
            logger.error("No guild configuration found!")
        
        mongo_client.close()
        
    except Exception as e:
        logger.error(f"Debug failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(debug_channel_config())