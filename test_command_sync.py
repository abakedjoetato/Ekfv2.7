"""
Test Command Sync - Force sync commands to Discord after removing cooldown
"""

import asyncio
import os
import logging
from datetime import datetime, timedelta
import discord
from discord.ext import commands

logger = logging.getLogger(__name__)

async def test_command_sync():
    """Test command sync functionality"""
    
    try:
        # Import the bot class
        from main import EmeraldKillfeedBot
        
        # Create bot instance
        bot = EmeraldKillfeedBot()
        
        # Load environment
        bot_token = os.environ.get('BOT_TOKEN')
        if not bot_token:
            print("❌ BOT_TOKEN not found")
            return
        
        print("🔄 Testing command sync...")
        
        # Connect to Discord
        await bot.login(bot_token)
        
        # Check if cooldown file exists
        cooldown_file = 'command_sync_cooldown.txt'
        if os.path.exists(cooldown_file):
            print(f"❌ Cooldown file still exists: {cooldown_file}")
            os.remove(cooldown_file)
            print("✅ Removed cooldown file")
        else:
            print("✅ No cooldown file found")
        
        # Get pending commands
        commands = bot.pending_application_commands
        print(f"Found {len(commands)} commands to sync:")
        
        for cmd in commands[:10]:  # Show first 10 commands
            print(f"  - {cmd.name}: {cmd.description}")
        
        if len(commands) > 10:
            print(f"  ... and {len(commands) - 10} more commands")
        
        # Get guild
        guild_id = 1219706687980568769
        guild = bot.get_guild(guild_id)
        
        if not guild:
            # Connect to get guild info
            await bot.connect()
            guild = bot.get_guild(guild_id)
        
        if guild:
            print(f"✅ Found guild: {guild.name}")
            
            # Force sync commands
            print("🔄 Forcing command sync...")
            try:
                synced = await bot.sync_commands()
                print(f"✅ Command sync successful: {len(synced) if synced else 0} commands synced")
                
                # List synced commands
                if synced:
                    print("Synced commands:")
                    for cmd in synced[:10]:
                        print(f"  - {cmd.name}")
                    if len(synced) > 10:
                        print(f"  ... and {len(synced) - 10} more")
                        
            except discord.HTTPException as e:
                print(f"❌ Command sync failed: {e}")
                if e.status == 429:
                    print("Rate limited - try again later")
                
        else:
            print("❌ Could not find guild")
        
        # Cleanup
        await bot.close()
        
    except Exception as e:
        print(f"Test failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_command_sync())