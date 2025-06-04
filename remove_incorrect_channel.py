"""
Remove Incorrect Channel Configuration - Fix invalid Emerald EU killfeed channel
"""

import asyncio
import logging
import os
from datetime import datetime, timezone
from motor.motor_asyncio import AsyncIOMotorClient
from bot.models.database import DatabaseManager

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def remove_invalid_server_config():
    """Remove the invalid Emerald EU server configuration so it uses default channels"""
    
    try:
        # Connect to database
        mongo_uri = os.environ.get('MONGO_URI')
        client = AsyncIOMotorClient(mongo_uri)
        db_manager = DatabaseManager(client)
        
        guild_id = 1219706687980568769
        
        # Get current configuration
        guild_config = await db_manager.get_guild(guild_id)
        server_channels = guild_config.get('server_channels', {}) if guild_config else {}
        
        logger.info("Current server configurations:")
        for server_name in server_channels.keys():
            logger.info(f"  {server_name}")
        
        # Remove the problematic "Emerald EU" configuration
        if 'Emerald EU' in server_channels:
            logger.info("Removing invalid 'Emerald EU' server configuration...")
            del server_channels['Emerald EU']
            
            # Update database
            await db_manager.guild_configs.update_one(
                {'guild_id': guild_id},
                {
                    '$set': {
                        'server_channels': server_channels,
                        'last_updated': datetime.now(timezone.utc)
                    }
                },
                upsert=True
            )
            
            logger.info("✅ Removed invalid server configuration")
        else:
            logger.info("No 'Emerald EU' configuration found")
        
        # Verify the fix
        from bot.utils.channel_router import ChannelRouter
        
        class MockBot:
            def __init__(self, db_manager):
                self.db_manager = db_manager
        
        mock_bot = MockBot(db_manager)
        router = ChannelRouter(mock_bot)
        
        # Test routing for server 7020
        logger.info("\n=== TESTING ROUTING AFTER FIX ===")
        embed_types = ['killfeed', 'events', 'missions', 'helicrash', 'airdrop', 'trader']
        
        for embed_type in embed_types:
            channel_id = await router.get_channel_id(guild_id, '7020', embed_type)
            logger.info(f"{embed_type.upper()}: {channel_id}")
        
        logger.info("\n✅ Server 7020 will now use default channel configuration")
        
    except Exception as e:
        logger.error(f"Failed to remove invalid configuration: {e}")
        import traceback
        traceback.print_exc()

async def main():
    """Remove invalid server configuration"""
    await remove_invalid_server_config()

if __name__ == "__main__":
    asyncio.run(main())