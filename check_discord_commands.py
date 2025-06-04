"""
Check Discord Commands - Verify current command status without triggering rate limits
"""

import asyncio
import os
import discord
from discord.ext import commands

async def check_discord_commands():
    """Check current Discord command status"""
    
    try:
        # Create minimal bot for checking
        intents = discord.Intents.default()
        intents.message_content = True
        bot = commands.Bot(command_prefix='!', intents=intents)
        
        bot_token = os.environ.get('BOT_TOKEN')
        if not bot_token:
            print("BOT_TOKEN not found")
            return
        
        @bot.event
        async def on_ready():
            print(f"Connected as {bot.user}")
            
            guild_id = 1219706687980568769
            guild = bot.get_guild(guild_id)
            
            if guild:
                print(f"Found guild: {guild.name}")
                
                # Check existing commands without syncing
                try:
                    existing_commands = await bot.tree.fetch_commands(guild=guild)
                    print(f"Existing commands in guild: {len(existing_commands)}")
                    
                    for cmd in existing_commands[:10]:
                        print(f"  - {cmd.name}")
                    
                    if len(existing_commands) > 10:
                        print(f"  ... and {len(existing_commands) - 10} more")
                        
                except Exception as e:
                    print(f"Could not fetch existing commands: {e}")
                
                # Check global commands
                try:
                    global_commands = await bot.tree.fetch_commands()
                    print(f"Global commands: {len(global_commands)}")
                    
                except Exception as e:
                    print(f"Could not fetch global commands: {e}")
            
            await bot.close()
        
        await bot.start(bot_token)
        
    except Exception as e:
        print(f"Check failed: {e}")

if __name__ == "__main__":
    asyncio.run(check_discord_commands())