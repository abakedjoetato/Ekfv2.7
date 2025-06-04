"""
Check Actual Killfeed Channel Configuration - Verify the correct killfeed channel
"""

import asyncio
import logging
import os
from motor.motor_asyncio import AsyncIOMotorClient
from bot.models.database import DatabaseManager

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def check_actual_killfeed_configuration():
    """Check the actual killfeed channel configuration in database"""
    
    try:
        # Connect to database
        mongo_uri = os.environ.get('MONGO_URI')
        client = AsyncIOMotorClient(mongo_uri)
        db_manager = DatabaseManager(client)
        
        guild_id = 1219706687980568769
        
        # Get current guild configuration
        guild_config = await db_manager.get_guild(guild_id)
        
        if not guild_config:
            logger.error("No guild configuration found")
            return None
        
        logger.info("=== Current Database Configuration ===")
        
        # Check server_channels structure
        server_channels = guild_config.get('server_channels', {})
        logger.info(f"Server channels configured: {list(server_channels.keys())}")
        
        # Check default server killfeed channel
        if 'default' in server_channels:
            default_channels = server_channels['default']
            default_killfeed = default_channels.get('killfeed')
            logger.info(f"Default server killfeed channel: {default_killfeed}")
        
        # Check server-specific killfeed channels
        for server_name, channels in server_channels.items():
            if server_name != 'default':
                killfeed_channel = channels.get('killfeed')
                if killfeed_channel:
                    logger.info(f"Server '{server_name}' killfeed channel: {killfeed_channel}")
        
        # Check legacy channel configuration
        legacy_channels = guild_config.get('channels', {})
        if legacy_channels:
            legacy_killfeed = legacy_channels.get('killfeed')
            if legacy_killfeed:
                logger.info(f"Legacy killfeed channel: {legacy_killfeed}")
        
        # Check channel_configs collection (old structure)
        channel_config = await db_manager.channel_configs.find_one({'guild_id': guild_id})
        if channel_config:
            old_killfeed = channel_config.get('killfeed_channel_id')
            if old_killfeed:
                logger.info(f"Old channel_configs killfeed: {old_killfeed}")
        
        # Test channel router resolution
        from bot.utils.channel_router import ChannelRouter
        
        class MockBot:
            def __init__(self, db_manager):
                self.db_manager = db_manager
        
        mock_bot = MockBot(db_manager)
        router = ChannelRouter(mock_bot)
        
        resolved_killfeed = await router.get_channel_id(guild_id, '7020', 'killfeed')
        logger.info(f"Channel router resolves killfeed to: {resolved_killfeed}")
        
        return resolved_killfeed
        
    except Exception as e:
        logger.error(f"Failed to check killfeed configuration: {e}")
        import traceback
        traceback.print_exc()
        return None

async def check_discord_channels():
    """Check what killfeed channels actually exist in Discord"""
    
    try:
        import discord
        
        # Get Discord bot token
        bot_token = os.environ.get('BOT_TOKEN')
        if not bot_token:
            logger.error("BOT_TOKEN not found")
            return []
        
        # Create Discord client
        intents = discord.Intents.default()
        client = discord.Client(intents=intents)
        
        killfeed_channels = []
        
        @client.event
        async def on_ready():
            try:
                guild_id = 1219706687980568769
                guild = client.get_guild(guild_id)
                
                if not guild:
                    logger.error(f"Guild {guild_id} not found")
                    await client.close()
                    return
                
                logger.info("=== Discord Killfeed Channels ===")
                
                # Find channels with 'killfeed' in the name
                text_channels = [ch for ch in guild.channels if isinstance(ch, discord.TextChannel)]
                
                for channel in text_channels:
                    if 'killfeed' in channel.name.lower():
                        logger.info(f"Found killfeed channel: {channel.name} (ID: {channel.id})")
                        killfeed_channels.append({
                            'name': channel.name,
                            'id': channel.id
                        })
                
                if not killfeed_channels:
                    logger.info("No channels with 'killfeed' in name found")
                    
                    # Show some general channels that might be used
                    logger.info("Available text channels:")
                    for channel in text_channels[:10]:  # Show first 10 channels
                        logger.info(f"  {channel.name} (ID: {channel.id})")
                
            except Exception as e:
                logger.error(f"Error checking Discord channels: {e}")
            
            finally:
                await client.close()
        
        # Start Discord client
        await client.start(bot_token)
        return killfeed_channels
        
    except Exception as e:
        logger.error(f"Failed to check Discord channels: {e}")
        return []

async def main():
    """Check actual killfeed channel configuration"""
    
    logger.info("Checking actual killfeed channel configuration...")
    
    # Check database configuration
    db_killfeed = await check_actual_killfeed_configuration()
    
    # Check Discord channels
    discord_channels = await check_discord_channels()
    
    # Summary
    logger.info("=== Summary ===")
    logger.info(f"Database resolves killfeed to: {db_killfeed}")
    
    if discord_channels:
        logger.info("Discord killfeed channels found:")
        for channel in discord_channels:
            logger.info(f"  {channel['name']}: {channel['id']}")
    else:
        logger.info("No Discord channels with 'killfeed' in name found")
    
    # Check if database channel exists in Discord
    if db_killfeed and discord_channels:
        db_channel_exists = any(ch['id'] == db_killfeed for ch in discord_channels)
        if not db_channel_exists:
            logger.warning(f"Database killfeed channel {db_killfeed} not found in Discord killfeed channels")

if __name__ == "__main__":
    asyncio.run(main())