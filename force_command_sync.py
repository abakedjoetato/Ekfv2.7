"""
Force Command Sync - Properly sync commands to Discord without rate limiting protection
"""

import asyncio
import os
import sys
from datetime import datetime

# Add project root to path
sys.path.insert(0, '.')

async def force_command_sync():
    """Force sync commands to Discord by bypassing protection"""
    
    # Import Discord modules
    import discord
    from discord.ext import commands
    import motor.motor_asyncio
    from bot.models.database import DatabaseManager
    
    # Get environment variables
    bot_token = os.environ.get('BOT_TOKEN')
    mongo_uri = os.environ.get('MONGO_URI')
    
    if not bot_token:
        print("BOT_TOKEN not found in environment")
        return
    
    if not mongo_uri:
        print("MONGO_URI not found in environment")
        return
    
    # Create bot instance
    intents = discord.Intents.default()
    intents.message_content = True
    intents.members = True
    bot = commands.Bot(intents=intents)
    
    # Connect to database
    mongo_client = motor.motor_asyncio.AsyncIOMotorClient(mongo_uri)
    await mongo_client.admin.command('ping')
    db_manager = DatabaseManager(mongo_client)
    bot.db_manager = db_manager
    
    @bot.event
    async def on_ready():
        print(f"Bot logged in as {bot.user}")
        
        # Load commands from cogs
        cog_modules = [
            'bot.cogs.info',
            'bot.cogs.stats', 
            'bot.cogs.linking',
            'bot.cogs.admin_channels',
            'bot.cogs.economy',
            'bot.cogs.factions',
            'bot.cogs.bounties',
            'bot.cogs.premium',
            'bot.cogs.parsers'
        ]
        
        for module_name in cog_modules:
            try:
                bot.load_extension(module_name)
                print(f"Loaded cog: {module_name}")
            except Exception as e:
                print(f"Failed to load {module_name}: {e}")
        
        # Get guild
        guild_id = 1219706687980568769
        guild = bot.get_guild(guild_id)
        
        if not guild:
            print(f"Guild {guild_id} not found")
            await bot.close()
            return
        
        # Check current commands
        try:
            existing_commands = await guild.fetch_commands()
            print(f"Existing commands on Discord: {len(existing_commands)}")
            
            # Get bot's pending commands
            pending_commands = bot.pending_application_commands
            print(f"Bot has {len(pending_commands)} commands to sync")
            
            if len(existing_commands) >= len(pending_commands):
                print("Commands already synced, no action needed")
                await bot.close()
                return
            
            # Force sync
            print("Syncing commands to Discord...")
            synced = await bot.sync_commands(guild_id=guild_id)
            print(f"Successfully synced {len(synced)} commands")
            
            # Verify sync
            updated_commands = await guild.fetch_commands()
            print(f"Commands now on Discord: {len(updated_commands)}")
            
        except discord.HTTPException as e:
            if e.status == 429:
                print(f"Rate limited: {e}")
                print("Commands cannot be synced due to rate limiting")
            else:
                print(f"HTTP error: {e}")
        except Exception as e:
            print(f"Error syncing commands: {e}")
        
        await bot.close()
    
    # Start bot
    try:
        await bot.start(bot_token)
    except Exception as e:
        print(f"Error starting bot: {e}")
    finally:
        await mongo_client.close()

if __name__ == "__main__":
    asyncio.run(force_command_sync())