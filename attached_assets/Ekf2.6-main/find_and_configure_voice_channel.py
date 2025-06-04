"""
Find and Configure Voice Channel - Discover actual voice channels and fix configuration
"""

import asyncio
import os
import discord
from motor.motor_asyncio import AsyncIOMotorClient

async def find_and_configure_voice_channel():
    """Find actual voice channels in Discord and configure properly"""
    try:
        bot_token = os.getenv('BOT_TOKEN')
        mongo_uri = os.getenv('MONGO_URI')
        
        if not bot_token:
            print("BOT_TOKEN not found")
            return
            
        # Create Discord client
        intents = discord.Intents.default()
        intents.message_content = True
        client = discord.Client(intents=intents)
        
        guild_id = 1219706687980568769
        found_channels = []
        
        @client.event
        async def on_ready():
            print(f"Connected as {client.user}")
            guild = client.get_guild(guild_id)
            
            if guild:
                print(f"\n=== Available Channels in {guild.name} ===")
                
                # Find voice channels
                voice_channels = [ch for ch in guild.channels if isinstance(ch, discord.VoiceChannel)]
                print(f"\nVoice Channels ({len(voice_channels)}):")
                for vc in voice_channels:
                    print(f"  {vc.name} (ID: {vc.id})")
                    found_channels.append({"name": vc.name, "id": vc.id, "type": "voice"})
                
                # Find text channels that could work for player count display
                text_channels = [ch for ch in guild.channels if isinstance(ch, discord.TextChannel)]
                print(f"\nText Channels ({len(text_channels)}):")
                for tc in text_channels[:10]:  # Show first 10
                    print(f"  {tc.name} (ID: {tc.id})")
                    
                # Find categories
                categories = [ch for ch in guild.channels if isinstance(ch, discord.CategoryChannel)]
                print(f"\nCategories ({len(categories)}):")
                for cat in categories:
                    print(f"  {cat.name} (ID: {cat.id})")
                    
                # Configure first available voice channel or suitable text channel
                target_channel = None
                if voice_channels:
                    target_channel = voice_channels[0]
                    print(f"\n✅ Will use voice channel: {target_channel.name} ({target_channel.id})")
                else:
                    # Use a text channel that can display count in name
                    suitable_channels = [ch for ch in text_channels if any(word in ch.name.lower() for word in ['player', 'count', 'online', 'status', 'info'])]
                    if suitable_channels:
                        target_channel = suitable_channels[0]
                        print(f"\n✅ Will use text channel for count display: {target_channel.name} ({target_channel.id})")
                    elif text_channels:
                        target_channel = text_channels[0]
                        print(f"\n✅ Will use first text channel: {target_channel.name} ({target_channel.id})")
                
                if target_channel:
                    # Update database configuration
                    mongo_client = AsyncIOMotorClient(mongo_uri)
                    db = mongo_client.emerald_killfeed
                    
                    await db.guild_configs.update_one(
                        {'guild_id': guild_id},
                        {
                            '$set': {
                                'server_channels.default.voice_channel': target_channel.id
                            }
                        },
                        upsert=True
                    )
                    
                    print(f"\n✅ Updated database with channel ID: {target_channel.id}")
                    await mongo_client.close()
                else:
                    print("\n❌ No suitable channels found")
                    
            else:
                print(f"Guild {guild_id} not found")
                
            await client.close()
        
        await client.start(bot_token)
        
    except Exception as e:
        print(f"Error finding channels: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(find_and_configure_voice_channel())