#!/usr/bin/env python3

"""
Configure Killfeed Channels
Set up proper channel configuration for killfeed event delivery
"""

import asyncio
import logging
import os
from motor.motor_asyncio import AsyncIOMotorClient

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def configure_killfeed_channels():
    """Configure killfeed channels for proper event delivery"""
    try:
        logger.info("=== Configuring Killfeed Channels ===")
        
        # Connect to database
        mongo_client = AsyncIOMotorClient(os.environ.get('MONGO_URI'))
        db = mongo_client.emerald_killfeed
        
        guild_id = 1219706687980568769
        
        # Get current guild configuration
        guild_config = await db.guild_configs.find_one({"guild_id": guild_id})
        logger.info(f"Current guild config: {guild_config}")
        
        if not guild_config:
            logger.info("Creating new guild configuration")
            guild_config = {
                "guild_id": guild_id,
                "server_channels": {},
                "channels": {}
            }
        
        # Configure killfeed channel for the server
        server_name = "Emerald EU"
        
        # Use a test channel ID (you'll need to replace this with actual channel)
        # For now, we'll set up the structure and show what needs to be configured
        test_channel_id = 1219706688815259700  # Replace with actual killfeed channel
        
        # Set up server-specific killfeed channel
        if "server_channels" not in guild_config:
            guild_config["server_channels"] = {}
        
        if server_name not in guild_config["server_channels"]:
            guild_config["server_channels"][server_name] = {}
        
        guild_config["server_channels"][server_name]["killfeed"] = test_channel_id
        
        # Also set up default killfeed channel
        if "default" not in guild_config["server_channels"]:
            guild_config["server_channels"]["default"] = {}
        
        guild_config["server_channels"]["default"]["killfeed"] = test_channel_id
        
        # Update database
        await db.guild_configs.update_one(
            {"guild_id": guild_id},
            {"$set": guild_config},
            upsert=True
        )
        
        logger.info(f"✅ Configured killfeed channel {test_channel_id} for server '{server_name}'")
        logger.info(f"Updated guild config: {guild_config}")
        
        # Verify configuration
        updated_config = await db.guild_configs.find_one({"guild_id": guild_id})
        logger.info(f"Verified configuration: {updated_config}")
        
        await mongo_client.close()
        
    except Exception as e:
        logger.error(f"Configuration failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(configure_killfeed_channels())