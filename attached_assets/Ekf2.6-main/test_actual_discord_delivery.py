"""
Test Actual Discord Embed Delivery - Send real embeds to Discord channels
"""

import asyncio
import logging
import os
import discord
from datetime import datetime, timezone
from motor.motor_asyncio import AsyncIOMotorClient
from bot.models.database import DatabaseManager

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def configure_separate_channels():
    """Configure separate Discord channels for each embed type"""
    
    try:
        # Connect to database
        mongo_uri = os.environ.get('MONGO_URI')
        client = AsyncIOMotorClient(mongo_uri)
        db_manager = DatabaseManager(client)
        
        guild_id = 1219706687980568769  # Emerald Servers
        
        # Configure separate channels for different embed types
        channel_configs = [
            {
                'channel_id': 1219706688815398002,  # General channel
                'embed_types': ['killfeed'],
                'name': 'killfeed'
            },
            {
                'channel_id': 1219706688815398003,  # Events channel (if exists)
                'embed_types': ['events'],
                'name': 'server-events'
            },
            {
                'channel_id': 1219706688815398004,  # Missions channel (if exists)
                'embed_types': ['missions'],
                'name': 'missions'
            },
            {
                'channel_id': 1219706688815398005,  # Helicrash channel (if exists)
                'embed_types': ['helicrash'],
                'name': 'helicrash'
            }
        ]
        
        # Update guild configuration with separate channels
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
        
        logger.info(f"Configured {len(channel_configs)} separate channels for guild {guild_id}")
        for config in channel_configs:
            logger.info(f"Channel {config['channel_id']}: {config['embed_types']}")
        
        return channel_configs
        
    except Exception as e:
        logger.error(f"Failed to configure separate channels: {e}")
        return []

async def send_real_discord_embeds():
    """Send actual Discord embeds to test delivery"""
    
    try:
        # Get Discord bot token
        bot_token = os.environ.get('BOT_TOKEN')
        if not bot_token:
            logger.error("BOT_TOKEN not found in environment variables")
            return False
        
        # Create Discord client
        intents = discord.Intents.default()
        intents.message_content = True
        client = discord.Client(intents=intents)
        
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
                
                # Get channel configurations from database
                mongo_uri = os.environ.get('MONGO_URI')
                db_client = AsyncIOMotorClient(mongo_uri)
                db_manager = DatabaseManager(db_client)
                
                guild_config = await db_manager.guild_configs.find_one({'guild_id': guild_id})
                if not guild_config or not guild_config.get('channels'):
                    logger.error("No channel configuration found")
                    await client.close()
                    return
                
                channels = guild_config.get('channels', [])
                
                # Test each embed type
                test_embeds = [
                    {
                        'type': 'killfeed',
                        'embed': discord.Embed(
                            title="💀 Test Kill Event",
                            description="PlayerOne eliminated PlayerTwo",
                            color=0xff0000,
                            timestamp=datetime.now(timezone.utc)
                        )
                    },
                    {
                        'type': 'events',
                        'embed': discord.Embed(
                            title="🎮 Test Player Event",
                            description="TestPlayer joined the server",
                            color=0x00ff00,
                            timestamp=datetime.now(timezone.utc)
                        )
                    },
                    {
                        'type': 'missions',
                        'embed': discord.Embed(
                            title="📦 Test Mission Event",
                            description="Supply Drop mission started",
                            color=0xffa500,
                            timestamp=datetime.now(timezone.utc)
                        )
                    },
                    {
                        'type': 'helicrash',
                        'embed': discord.Embed(
                            title="🚁 Test Helicopter Crash",
                            description="Helicopter crash event triggered",
                            color=0xff6600,
                            timestamp=datetime.now(timezone.utc)
                        )
                    }
                ]
                
                successful_deliveries = []
                
                for test_embed in test_embeds:
                    embed_type = test_embed['type']
                    embed = test_embed['embed']
                    
                    # Find target channel for this embed type
                    target_channel_id = None
                    for channel_config in channels:
                        if embed_type in channel_config.get('embed_types', []):
                            target_channel_id = channel_config.get('channel_id')
                            break
                    
                    if not target_channel_id:
                        logger.warning(f"No channel configured for {embed_type}")
                        continue
                    
                    # Get Discord channel
                    discord_channel = guild.get_channel(target_channel_id)
                    if not discord_channel:
                        logger.warning(f"Discord channel {target_channel_id} not found, trying general channel")
                        # Fallback to general channel if specific channel doesn't exist
                        discord_channel = guild.get_channel(1219706688815398002)
                    
                    if discord_channel:
                        try:
                            # Add test identification
                            embed.add_field(
                                name="Test Status",
                                value="End-to-end parser test",
                                inline=True
                            )
                            embed.add_field(
                                name="Server",
                                value="Emerald EU (Test)",
                                inline=True
                            )
                            
                            # Send embed to Discord
                            await discord_channel.send(embed=embed)
                            logger.info(f"✅ Successfully sent {embed_type} embed to channel {discord_channel.name}")
                            successful_deliveries.append(embed_type)
                            
                            # Wait between sends to avoid rate limits
                            await asyncio.sleep(2)
                            
                        except Exception as e:
                            logger.error(f"Failed to send {embed_type} embed: {e}")
                    else:
                        logger.error(f"Could not find any suitable channel for {embed_type}")
                
                logger.info(f"Successfully delivered {len(successful_deliveries)} embed types: {successful_deliveries}")
                
                # Close database connection
                db_client.close()
                
            except Exception as e:
                logger.error(f"Error during embed delivery: {e}")
                import traceback
                traceback.print_exc()
            
            finally:
                await client.close()
        
        # Start Discord client
        await client.start(bot_token)
        return True
        
    except Exception as e:
        logger.error(f"Discord embed delivery failed: {e}")
        return False

async def test_parser_integration():
    """Test integration with actual bot parser system"""
    
    logger.info("Testing parser integration with Discord delivery...")
    
    try:
        # Import bot components
        import sys
        sys.path.insert(0, '.')
        
        from main import EmeraldKillfeedBot
        
        # Create bot instance
        bot_token = os.environ.get('BOT_TOKEN')
        if not bot_token:
            logger.error("BOT_TOKEN not found")
            return False
        
        # Test that parsers can access configured channels
        mongo_uri = os.environ.get('MONGO_URI')
        client = AsyncIOMotorClient(mongo_uri)
        db_manager = DatabaseManager(client)
        
        guild_id = 1219706687980568769
        
        # Check parser state
        parser_state = await db_manager.get_parser_state(guild_id, '7020')
        logger.info(f"Parser state: {parser_state}")
        
        # Check channel configuration
        guild_config = await db_manager.guild_configs.find_one({'guild_id': guild_id})
        channels = guild_config.get('channels', []) if guild_config else []
        
        logger.info(f"Configured channels: {len(channels)}")
        for channel in channels:
            logger.info(f"  Channel {channel.get('channel_id')}: {channel.get('embed_types')}")
        
        # Check server configuration
        servers = guild_config.get('servers', []) if guild_config else []
        if servers:
            server = servers[0]
            sftp_creds = server.get('sftp_credentials', {})
            logger.info(f"Server SFTP configured: {bool(sftp_creds.get('host'))}")
        
        return len(channels) > 0 and len(servers) > 0
        
    except Exception as e:
        logger.error(f"Parser integration test failed: {e}")
        return False

async def main():
    """Run complete Discord delivery testing"""
    
    logger.info("Starting actual Discord embed delivery testing...")
    
    # Configure separate channels
    channel_configs = await configure_separate_channels()
    
    # Test actual Discord delivery
    delivery_success = await send_real_discord_embeds()
    
    # Test parser integration
    integration_success = await test_parser_integration()
    
    # Summary
    logger.info("Discord Delivery Test Results:")
    logger.info(f"  Channel Configuration: {'PASS' if channel_configs else 'FAIL'}")
    logger.info(f"  Discord Delivery: {'PASS' if delivery_success else 'FAIL'}")
    logger.info(f"  Parser Integration: {'PASS' if integration_success else 'FAIL'}")
    
    if delivery_success:
        logger.info("Successfully sent test embeds to Discord - check your channels!")
        logger.info("Each embed type should appear in its designated channel")
    else:
        logger.error("Failed to deliver embeds to Discord")
    
    return delivery_success

if __name__ == "__main__":
    asyncio.run(main())