"""
Check Available Discord Channels - Find actual channels in the server
"""

import asyncio
import logging
import os
import discord

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def check_available_channels():
    """Check what channels are actually available in the Discord server"""
    
    try:
        # Get Discord bot token
        bot_token = os.environ.get('BOT_TOKEN')
        if not bot_token:
            logger.error("BOT_TOKEN not found in environment variables")
            return []
        
        # Create Discord client
        intents = discord.Intents.default()
        intents.message_content = True
        client = discord.Client(intents=intents)
        
        available_channels = []
        
        @client.event
        async def on_ready():
            logger.info(f"Discord client connected as {client.user}")
            
            try:
                # Get guild
                guild_id = 1219706687980568769
                guild = client.get_guild(guild_id)
                
                if not guild:
                    logger.error(f"Guild {guild_id} not found")
                    await client.close()
                    return
                
                logger.info(f"Found guild: {guild.name}")
                logger.info(f"Guild has {len(guild.channels)} total channels")
                
                # List all text channels
                text_channels = [ch for ch in guild.channels if isinstance(ch, discord.TextChannel)]
                
                logger.info(f"Available text channels ({len(text_channels)}):")
                for channel in text_channels:
                    logger.info(f"  - {channel.name} (ID: {channel.id})")
                    available_channels.append({
                        'name': channel.name,
                        'id': channel.id,
                        'type': 'text'
                    })
                
                # List categories
                categories = [ch for ch in guild.channels if isinstance(ch, discord.CategoryChannel)]
                logger.info(f"Available categories ({len(categories)}):")
                for category in categories:
                    logger.info(f"  - {category.name} (ID: {category.id})")
                
                # Test sending a message to the first available text channel
                if text_channels:
                    test_channel = text_channels[0]
                    try:
                        test_embed = discord.Embed(
                            title="🤖 Bot Channel Test",
                            description="Testing Discord embed delivery capability",
                            color=0x00ff00
                        )
                        test_embed.add_field(
                            name="Status",
                            value="Successfully connected to Discord",
                            inline=False
                        )
                        
                        await test_channel.send(embed=test_embed)
                        logger.info(f"✅ Successfully sent test embed to #{test_channel.name}")
                        
                    except Exception as e:
                        logger.error(f"Failed to send test message: {e}")
                
            except Exception as e:
                logger.error(f"Error checking channels: {e}")
                import traceback
                traceback.print_exc()
            
            finally:
                await client.close()
        
        # Start Discord client
        await client.start(bot_token)
        return available_channels
        
    except Exception as e:
        logger.error(f"Failed to check Discord channels: {e}")
        return []

async def configure_real_channels():
    """Configure the bot to use real Discord channels"""
    
    try:
        from motor.motor_asyncio import AsyncIOMotorClient
        from bot.models.database import DatabaseManager
        
        # Get available channels
        channels = await check_available_channels()
        
        if not channels:
            logger.error("No channels found")
            return False
        
        # Connect to database
        mongo_uri = os.environ.get('MONGO_URI')
        client = AsyncIOMotorClient(mongo_uri)
        db_manager = DatabaseManager(client)
        
        guild_id = 1219706687980568769
        
        # Use the first available channel for all embed types initially
        primary_channel = channels[0]
        
        # Configure channel mapping
        channel_configs = [
            {
                'channel_id': primary_channel['id'],
                'embed_types': ['killfeed', 'events', 'missions', 'helicrash'],
                'name': primary_channel['name']
            }
        ]
        
        # Update guild configuration
        await db_manager.guild_configs.update_one(
            {'guild_id': guild_id},
            {
                '$set': {
                    'channels': channel_configs,
                    'last_updated': datetime.now(timezone.utc)
                }
            },
            upsert=True
        )
        
        logger.info(f"Configured bot to use channel #{primary_channel['name']} (ID: {primary_channel['id']})")
        logger.info("All embed types will be delivered to this channel")
        
        return True
        
    except Exception as e:
        logger.error(f"Failed to configure real channels: {e}")
        return False

async def main():
    """Run channel discovery and configuration"""
    
    logger.info("Checking available Discord channels...")
    
    # Check available channels
    channels = await check_available_channels()
    
    if channels:
        logger.info(f"Found {len(channels)} text channels")
        
        # Configure bot to use real channels
        configured = await configure_real_channels()
        
        if configured:
            logger.info("Bot successfully configured to use real Discord channels")
            logger.info("Ready to deliver embeds to your Discord server")
        else:
            logger.error("Failed to configure channels")
    else:
        logger.error("No Discord channels found")

if __name__ == "__main__":
    asyncio.run(main())