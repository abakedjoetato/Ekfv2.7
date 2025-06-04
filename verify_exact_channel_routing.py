"""
Verify Exact Channel Routing - Show exactly where each embed type will be delivered
"""

import asyncio
import logging
import os
import discord
from motor.motor_asyncio import AsyncIOMotorClient
from bot.models.database import DatabaseManager
from bot.utils.channel_router import ChannelRouter

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def verify_exact_routing():
    """Verify exactly where each embed type will route with actual Discord channel names"""
    
    try:
        # Connect to database
        mongo_uri = os.environ.get('MONGO_URI')
        client = AsyncIOMotorClient(mongo_uri)
        db_manager = DatabaseManager(client)
        
        # Get Discord bot token
        bot_token = os.environ.get('BOT_TOKEN')
        if not bot_token:
            logger.error("BOT_TOKEN not found")
            return
        
        # Create Discord client to get actual channel names
        intents = discord.Intents.default()
        discord_client = discord.Client(intents=intents)
        
        routing_results = {}
        
        @discord_client.event
        async def on_ready():
            try:
                guild_id = 1219706687980568769
                server_id = '7020'
                
                guild = discord_client.get_guild(guild_id)
                if not guild:
                    logger.error(f"Guild {guild_id} not found")
                    await discord_client.close()
                    return
                
                # Create mock bot for channel router
                class MockBot:
                    def __init__(self, db_manager):
                        self.db_manager = db_manager
                
                mock_bot = MockBot(db_manager)
                router = ChannelRouter(mock_bot)
                
                # Test all embed types
                embed_types = ['killfeed', 'events', 'missions', 'helicrash', 'airdrop', 'trader']
                
                logger.info("=== EXACT CHANNEL ROUTING FOR CURRENT SERVER ===")
                logger.info(f"Server: {server_id} (Emerald EU)")
                logger.info("")
                
                for embed_type in embed_types:
                    # Get channel ID from router
                    channel_id = await router.get_channel_id(guild_id, server_id, embed_type)
                    
                    if channel_id:
                        # Get actual Discord channel
                        discord_channel = guild.get_channel(channel_id)
                        
                        if discord_channel:
                            channel_name = discord_channel.name
                            logger.info(f"{embed_type.upper()} embeds → #{channel_name}")
                            routing_results[embed_type] = {
                                'channel_id': channel_id,
                                'channel_name': channel_name
                            }
                        else:
                            logger.error(f"{embed_type.upper()} embeds → CHANNEL NOT FOUND (ID: {channel_id})")
                            routing_results[embed_type] = {
                                'channel_id': channel_id,
                                'channel_name': 'CHANNEL NOT FOUND'
                            }
                    else:
                        logger.error(f"{embed_type.upper()} embeds → NO CHANNEL CONFIGURED")
                        routing_results[embed_type] = {
                            'channel_id': None,
                            'channel_name': 'NO CHANNEL CONFIGURED'
                        }
                
                logger.info("")
                logger.info("=== SUMMARY ===")
                
                # Group by channel
                channel_groups = {}
                for embed_type, info in routing_results.items():
                    channel_name = info['channel_name']
                    if channel_name not in channel_groups:
                        channel_groups[channel_name] = []
                    channel_groups[channel_name].append(embed_type)
                
                for channel_name, embed_types in channel_groups.items():
                    embed_list = ', '.join(embed_types)
                    logger.info(f"#{channel_name} will receive: {embed_list}")
                
            except Exception as e:
                logger.error(f"Error verifying routing: {e}")
                import traceback
                traceback.print_exc()
            
            finally:
                await discord_client.close()
        
        # Start Discord client
        await discord_client.start(bot_token)
        
    except Exception as e:
        logger.error(f"Failed to verify routing: {e}")

async def main():
    """Verify exact channel routing"""
    await verify_exact_routing()

if __name__ == "__main__":
    asyncio.run(main())