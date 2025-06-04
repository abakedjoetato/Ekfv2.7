"""
Manual Command Registration - Direct Discord API approach for py-cord 2.6.1
"""

import asyncio
import os
import sys
import discord
from discord.ext import commands

async def register_commands():
    """Register commands directly to Discord"""
    
    bot_token = os.environ.get('BOT_TOKEN')
    if not bot_token:
        print("BOT_TOKEN not found")
        return
    
    # Create minimal bot for command registration
    intents = discord.Intents.default()
    bot = commands.Bot(intents=intents)
    
    @bot.event
    async def on_ready():
        print(f"Connected as {bot.user}")
        
        guild_id = 1219706687980568769
        guild = bot.get_guild(guild_id)
        
        if not guild:
            print(f"Guild {guild_id} not found")
            await bot.close()
            return
        
        print(f"Found guild: {guild.name}")
        
        # Load essential cogs for command registration
        try:
            bot.load_extension('bot.cogs.stats')
            bot.load_extension('bot.cogs.admin_channels')
            print("Loaded core cogs")
        except Exception as e:
            print(f"Error loading cogs: {e}")
        
        # Get pending commands
        commands_to_sync = bot.pending_application_commands
        print(f"Commands to sync: {len(commands_to_sync)}")
        
        if not commands_to_sync:
            print("No commands to sync")
            await bot.close()
            return
        
        # Attempt sync using py-cord 2.6.1 method
        try:
            # Method 1: Direct guild sync
            synced = await bot.sync_commands(guild=guild)
            print(f"Successfully synced {len(synced)} commands to {guild.name}")
            
        except Exception as sync_error:
            print(f"Sync method 1 failed: {sync_error}")
            
            try:
                # Method 2: Global sync (slower but more reliable)
                synced = await bot.sync_commands()
                print(f"Successfully synced {len(synced)} commands globally")
                
            except Exception as global_sync_error:
                print(f"Global sync also failed: {global_sync_error}")
                
                # Method 3: HTTP direct approach
                try:
                    commands_data = [cmd.to_dict() for cmd in commands_to_sync]
                    synced = await bot.http.bulk_upsert_guild_commands(
                        bot.user.id, guild_id, commands_data
                    )
                    print(f"HTTP sync successful: {len(synced)} commands")
                    
                except Exception as http_error:
                    print(f"All sync methods failed. HTTP error: {http_error}")
        
        await bot.close()
    
    try:
        await bot.start(bot_token)
    except Exception as e:
        print(f"Bot start error: {e}")

if __name__ == "__main__":
    # Add project root to path
    sys.path.insert(0, '.')
    asyncio.run(register_commands())