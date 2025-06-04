"""
Debug Channel Structure - Examine actual database channel configuration
"""
import asyncio
import logging
from bot.models.database import DatabaseManager
import pymongo

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def debug_channel_structure():
    """Debug actual channel configuration in database"""
    try:
        # Create database connection like the bot does
        mongo_client = AsyncIOMotorClient(os.getenv('MONGO_URI'))
        db_manager = DatabaseManager(mongo_client)
        await db_manager.initialize_database()
        
        guild_id = 1219706687980568769
        
        # Get guild configuration
        guild_config = await db_manager.get_guild(guild_id)
        
        if guild_config:
            logger.info(f"=== Guild {guild_id} Configuration ===")
            
            # Examine server_channels structure
            server_channels = guild_config.get('server_channels', {})
            logger.info(f"Server channels keys: {list(server_channels.keys())}")
            
            for server_name, channels in server_channels.items():
                logger.info(f"\n--- {server_name} ---")
                if isinstance(channels, dict):
                    for channel_type, channel_id in channels.items():
                        logger.info(f"  {channel_type}: {channel_id}")
                else:
                    logger.info(f"  Invalid structure: {type(channels)}")
            
            # Check legacy channels
            legacy_channels = guild_config.get('channels', {})
            if legacy_channels:
                logger.info(f"\n--- Legacy Channels ---")
                for channel_type, channel_id in legacy_channels.items():
                    logger.info(f"  {channel_type}: {channel_id}")
            
            # Test channel router logic
            logger.info(f"\n=== Channel Resolution Test ===")
            
            # Test for killfeed channel
            channel_id = None
            server_name = "Emerald EU"
            
            # Priority 1: Server-specific
            if server_name in server_channels:
                channel_id = server_channels[server_name].get('killfeed')
                if channel_id:
                    logger.info(f"✅ Server-specific killfeed: {channel_id}")
                else:
                    logger.info(f"❌ No server-specific killfeed for {server_name}")
            
            # Priority 2: Default
            if not channel_id and 'default' in server_channels:
                channel_id = server_channels['default'].get('killfeed')
                if channel_id:
                    logger.info(f"✅ Default killfeed: {channel_id}")
                else:
                    logger.info(f"❌ No default killfeed channel")
            
            # Priority 3: Legacy
            if not channel_id:
                channel_id = legacy_channels.get('killfeed')
                if channel_id:
                    logger.info(f"✅ Legacy killfeed: {channel_id}")
                else:
                    logger.info(f"❌ No legacy killfeed channel")
            
            logger.info(f"\nFinal resolved channel ID: {channel_id}")
            
        else:
            logger.error("No guild configuration found")
            
    except Exception as e:
        logger.error(f"Failed to debug channel structure: {e}")
        import traceback
        logger.error(traceback.format_exc())

if __name__ == "__main__":
    asyncio.run(debug_channel_structure())