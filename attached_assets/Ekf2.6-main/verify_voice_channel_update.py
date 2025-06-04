"""
Verify Voice Channel Update - Check if Discord voice channel shows correct player count
"""

import asyncio
import os
import discord
from motor.motor_asyncio import AsyncIOMotorClient

async def verify_voice_channel_update():
    """Verify the voice channel is showing the correct player count"""
    try:
        # Create Discord client
        intents = discord.Intents.default()
        intents.message_content = True
        client = discord.Client(intents=intents)
        
        @client.event
        async def on_ready():
            print(f"✅ Connected as {client.user}")
            
            # Find the guild
            guild = client.get_guild(1219706687980568769)  # Emerald Servers
            if not guild:
                print("❌ Could not find Emerald Servers guild")
                await client.close()
                return
            
            print(f"📡 Connected to guild: {guild.name}")
            
            # Connect to database to check player count
            mongo_client = AsyncIOMotorClient(os.environ['MONGO_URI'])
            db = mongo_client.emerald_killfeed
            
            # Get current player sessions
            online_count = await db.player_sessions.count_documents({
                'guild_id': 1219706687980568769,
                'state': 'online'
            })
            
            print(f"📊 Database shows {online_count} online players")
            
            # Find voice channel with player count
            voice_channels = [ch for ch in guild.channels if isinstance(ch, discord.VoiceChannel)]
            
            print(f"🔍 Found {len(voice_channels)} voice channels:")
            for vc in voice_channels:
                print(f"  - {vc.name} (ID: {vc.id})")
                if "Emerald EU" in vc.name or "2/" in vc.name:
                    print(f"    ⭐ This appears to be the player count channel")
            
            # Check database configuration
            config = await db.guild_configs.find_one({'guild_id': 1219706687980568769})
            if config:
                voice_config = config.get('voice_channel_config', {})
                print(f"🔧 Voice channel config: {voice_config}")
            
            mongo_client.close()
            await client.close()
        
        # Connect to Discord
        await client.start(os.environ['BOT_TOKEN'])
        
    except Exception as e:
        print(f"❌ Error verifying voice channel: {e}")

if __name__ == "__main__":
    asyncio.run(verify_voice_channel_update())