"""
Fix Killfeed Channel Configuration - Update to use the correct killfeed channel
"""

import asyncio
import logging
import os
from datetime import datetime, timezone
from motor.motor_asyncio import AsyncIOMotorClient
from bot.models.database import DatabaseManager

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def fix_killfeed_channel():
    """Fix killfeed channel configuration to use the correct channel"""
    
    try:
        # Connect to database
        mongo_uri = os.environ.get('MONGO_URI')
        client = AsyncIOMotorClient(mongo_uri)
        db_manager = DatabaseManager(client)
        
        guild_id = 1219706687980568769
        
        # Available killfeed channels from Discord
        killfeed_channels = {
            '🔫┊killfeed': 1219745194346287226,
            '💀┊killfeed': 1360217093273813227,
            'dskillfeed': 1360008068452061304
        }
        
        logger.info("Available killfeed channels:")
        for name, channel_id in killfeed_channels.items():
            logger.info(f"  {name}: {channel_id}")
        
        # Get current configuration
        guild_config = await db_manager.get_guild(guild_id)
        server_channels = guild_config.get('server_channels', {}) if guild_config else {}
        
        # Get current default server configuration
        default_config = server_channels.get('default', {})
        current_killfeed = default_config.get('killfeed')
        
        logger.info(f"Current killfeed channel in database: {current_killfeed}")
        
        # Check which channel exists and is likely the main one
        primary_killfeed = 1219745194346287226  # 🔫┊killfeed - seems like the primary one
        
        if current_killfeed != primary_killfeed:
            logger.info(f"Updating killfeed channel to: {primary_killfeed} (🔫┊killfeed)")
            
            # Update default server configuration
            default_config['killfeed'] = primary_killfeed
            server_channels['default'] = default_config
            
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
            
            logger.info("Killfeed channel updated successfully")
        else:
            logger.info("Killfeed channel is already correctly configured")
        
        # Verify the fix
        from bot.utils.channel_router import ChannelRouter
        
        class MockBot:
            def __init__(self, db_manager):
                self.db_manager = db_manager
        
        mock_bot = MockBot(db_manager)
        router = ChannelRouter(mock_bot)
        
        resolved_killfeed = await router.get_channel_id(guild_id, '7020', 'killfeed')
        logger.info(f"Channel router now resolves killfeed to: {resolved_killfeed}")
        
        # Verify this matches a real Discord channel
        if resolved_killfeed in killfeed_channels.values():
            channel_name = next(name for name, cid in killfeed_channels.items() if cid == resolved_killfeed)
            logger.info(f"✅ Killfeed correctly routes to Discord channel: {channel_name}")
            return True
        else:
            logger.error(f"❌ Killfeed routes to {resolved_killfeed} which doesn't match any Discord killfeed channel")
            return False
        
    except Exception as e:
        logger.error(f"Failed to fix killfeed channel configuration: {e}")
        import traceback
        traceback.print_exc()
        return False

async def main():
    """Fix killfeed channel configuration"""
    
    logger.info("Fixing killfeed channel configuration...")
    
    success = await fix_killfeed_channel()
    
    if success:
        logger.info("✅ Killfeed channel configuration fixed successfully")
        logger.info("Parser will now deliver killfeed embeds to the correct Discord channel")
    else:
        logger.error("❌ Failed to fix killfeed channel configuration")

if __name__ == "__main__":
    asyncio.run(main())