#!/usr/bin/env python3
"""
Debug Command Registration - Find why slash commands aren't being detected
"""
import asyncio
import discord
from discord.ext import commands
import os

async def debug_command_registration():
    """Debug command registration process"""
    
    print("Debug Command Registration Process")
    print("=" * 40)
    
    # Create bot instance like in main.py
    intents = discord.Intents.default()
    intents.message_content = True
    intents.guilds = True
    
    bot = commands.Bot(command_prefix='!', intents=intents)
    
    try:
        # Load a single cog to test
        print("Loading stats cog...")
        from bot.cogs.stats import Stats
        
        # Mock database manager for testing
        class MockDB:
            async def get_guild_servers(self, guild_id):
                return [{'server_name': 'Emerald EU', 'server_id': 'emerald_eu_1'}]
        
        bot.db_manager = MockDB()
        
        # Add the cog
        await bot.add_cog(Stats(bot))
        print(f"✅ Stats cog loaded")
        
        # Check different command attributes
        print("\nChecking command attributes:")
        
        if hasattr(bot, 'pending_application_commands'):
            pending = getattr(bot, 'pending_application_commands', [])
            print(f"pending_application_commands: {len(pending)} commands")
            for cmd in pending[:3]:  # Show first 3
                print(f"  - {getattr(cmd, 'name', 'Unknown')}: {type(cmd)}")
        
        if hasattr(bot, 'application_commands'):
            app_commands = getattr(bot, 'application_commands', [])
            print(f"application_commands: {len(app_commands)} commands")
            for cmd in app_commands[:3]:
                print(f"  - {getattr(cmd, 'name', 'Unknown')}: {type(cmd)}")
        
        # Check cog commands
        print(f"\nChecking cog commands:")
        for cog_name, cog in bot.cogs.items():
            print(f"Cog: {cog_name}")
            
            if hasattr(cog, '__cog_commands__'):
                cog_commands = getattr(cog, '__cog_commands__', [])
                print(f"  __cog_commands__: {len(cog_commands)} commands")
                for cmd in cog_commands[:3]:
                    print(f"    - {getattr(cmd, 'name', 'Unknown')}: {type(cmd)}")
            
            # Check for slash commands in cog
            if hasattr(cog, '__cog_app_commands__'):
                app_commands = getattr(cog, '__cog_app_commands__', [])
                print(f"  __cog_app_commands__: {len(app_commands)} commands")
                for cmd in app_commands[:3]:
                    print(f"    - {getattr(cmd, 'name', 'Unknown')}: {type(cmd)}")
            
            # Check all attributes for slash commands
            for attr_name in dir(cog):
                if attr_name.startswith('_'):
                    continue
                attr = getattr(cog, attr_name)
                if hasattr(attr, '__discord_app_commands_is_command__'):
                    print(f"    Found slash command: {attr_name}")
        
        print(f"\nTotal cogs loaded: {len(bot.cogs)}")
        
        # Test the specific online command
        stats_cog = bot.get_cog('Stats')
        if stats_cog and hasattr(stats_cog, 'online'):
            online_cmd = getattr(stats_cog, 'online')
            print(f"\nOnline command found: {type(online_cmd)}")
            print(f"Has discord app command marker: {hasattr(online_cmd, '__discord_app_commands_is_command__')}")
        
    except Exception as e:
        print(f"Error during debugging: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        await bot.close()

if __name__ == "__main__":
    asyncio.run(debug_command_registration())