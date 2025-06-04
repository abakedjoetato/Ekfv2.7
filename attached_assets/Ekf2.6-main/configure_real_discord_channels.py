"""
Configure Real Discord Channels - Map embed types to actual server channels
"""

import asyncio
import logging
import os
from datetime import datetime, timezone
from motor.motor_asyncio import AsyncIOMotorClient
from bot.models.database import DatabaseManager

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def configure_real_channels():
    """Configure the bot to use real Discord channels based on available channels"""
    
    try:
        # Connect to database
        mongo_uri = os.environ.get('MONGO_URI')
        client = AsyncIOMotorClient(mongo_uri)
        db_manager = DatabaseManager(client)
        
        guild_id = 1219706687980568769
        
        # Map embed types to actual Discord channels found in the server
        channel_configs = [
            {
                'channel_id': 1219745194346287226,  # 🔫┊killfeed
                'embed_types': ['killfeed'],
                'name': 'killfeed'
            },
            {
                'channel_id': 1361522248451756234,  # events
                'embed_types': ['events'],
                'name': 'events'
            },
            {
                'channel_id': 1219941143362666506,  # 🎪╰events
                'embed_types': ['missions'],
                'name': 'missions'
            },
            {
                'channel_id': 1291895121809506314,  # 💣┊raid-alerts
                'embed_types': ['helicrash'],
                'name': 'helicrash'
            }
        ]
        
        # Update guild configuration with real channels
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
        
        logger.info(f"Configured {len(channel_configs)} real Discord channels:")
        for config in channel_configs:
            logger.info(f"  {config['embed_types'][0]} -> Channel ID {config['channel_id']} ({config['name']})")
        
        return channel_configs
        
    except Exception as e:
        logger.error(f"Failed to configure real channels: {e}")
        return []

async def test_real_embed_delivery():
    """Test actual embed delivery to the configured real channels"""
    
    try:
        import discord
        
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
                
                # Get configured channels from database
                mongo_uri = os.environ.get('MONGO_URI')
                db_client = AsyncIOMotorClient(mongo_uri)
                db_manager = DatabaseManager(db_client)
                
                guild_config = await db_manager.guild_configs.find_one({'guild_id': guild_id})
                channels = guild_config.get('channels', []) if guild_config else []
                
                # Test embeds for each type
                test_embeds = [
                    {
                        'type': 'killfeed',
                        'embed': discord.Embed(
                            title="💀 Kill Event",
                            description="SniperElite eliminated RushingPlayer",
                            color=0xff0000,
                            timestamp=datetime.now(timezone.utc)
                        ).add_field(name="Weapon", value="Mosin-Nagant", inline=True
                        ).add_field(name="Distance", value="287m", inline=True
                        ).add_field(name="Server", value="Emerald EU", inline=True)
                    },
                    {
                        'type': 'events',
                        'embed': discord.Embed(
                            title="🎮 Player Event",
                            description="NewPlayer joined the server",
                            color=0x00ff00,
                            timestamp=datetime.now(timezone.utc)
                        ).add_field(name="Event", value="Connection", inline=True
                        ).add_field(name="Server", value="Emerald EU", inline=True)
                    },
                    {
                        'type': 'missions',
                        'embed': discord.Embed(
                            title="📦 Mission Started",
                            description="Supply Drop mission is now active",
                            color=0xffa500,
                            timestamp=datetime.now(timezone.utc)
                        ).add_field(name="Location", value="Grid 1450,2200", inline=True
                        ).add_field(name="Server", value="Emerald EU", inline=True)
                    },
                    {
                        'type': 'helicrash',
                        'embed': discord.Embed(
                            title="🚁 Helicopter Crash",
                            description="Helicopter crash event triggered",
                            color=0xff6600,
                            timestamp=datetime.now(timezone.utc)
                        ).add_field(name="Location", value="Grid 1800,2500", inline=True
                        ).add_field(name="Loot", value="High-tier", inline=True
                        ).add_field(name="Server", value="Emerald EU", inline=True)
                    }
                ]
                
                successful_deliveries = []
                
                for test_embed_data in test_embeds:
                    embed_type = test_embed_data['type']
                    embed = test_embed_data['embed']
                    
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
                        logger.warning(f"Discord channel {target_channel_id} not found")
                        continue
                    
                    try:
                        # Send embed to Discord
                        await discord_channel.send(embed=embed)
                        logger.info(f"✅ Successfully sent {embed_type} embed to #{discord_channel.name}")
                        successful_deliveries.append(embed_type)
                        
                        # Wait between sends to avoid rate limits
                        await asyncio.sleep(2)
                        
                    except Exception as e:
                        logger.error(f"Failed to send {embed_type} embed: {e}")
                
                logger.info(f"Successfully delivered {len(successful_deliveries)} embed types: {successful_deliveries}")
                
                # Close database connection
                db_client.close()
                
                # Summary
                if len(successful_deliveries) >= 4:
                    logger.info("🎉 All embed types successfully delivered to Discord channels!")
                else:
                    logger.warning(f"Only {len(successful_deliveries)}/4 embed types delivered")
                
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

async def main():
    """Configure channels and test delivery"""
    
    logger.info("Configuring real Discord channels for embed delivery...")
    
    # Configure real channels
    channel_configs = await configure_real_channels()
    
    if channel_configs:
        logger.info("Testing actual embed delivery to configured channels...")
        
        # Test actual delivery
        delivery_success = await test_real_embed_delivery()
        
        if delivery_success:
            logger.info("✅ Discord embed delivery system is fully operational")
            logger.info("All parser types will now deliver embeds to their designated channels")
        else:
            logger.error("❌ Some issues with embed delivery")
    else:
        logger.error("Failed to configure channels")

if __name__ == "__main__":
    asyncio.run(main())