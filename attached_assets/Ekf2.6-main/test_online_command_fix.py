"""
Test /online Command Fix - Verify real player data processing
"""

import asyncio
import os
from motor.motor_asyncio import AsyncIOMotorClient

async def test_online_command():
    """Test the /online command with real server data"""
    try:
        # Connect to database
        mongo_uri = os.getenv('MONGO_URI')
        if not mongo_uri:
            print("Missing MONGO_URI environment variable")
            return
        
        client = AsyncIOMotorClient(mongo_uri)
        db = client.EmeraldDB
        
        guild_id = 1219706687980568769  # Emerald Servers
        
        print("🔍 Testing /online command data sources...")
        
        # Check player sessions (what /online command queries)
        sessions = await db.player_sessions.find(
            {'guild_id': guild_id, 'state': 'online'}
        ).to_list(length=50)
        
        print(f"✅ Online player sessions: {len(sessions)}")
        
        if sessions:
            print("   Current online players:")
            for session in sessions[:5]:  # Show first 5
                player = session.get('character_name') or session.get('player_name', 'Unknown')
                server = session.get('server_name', 'Unknown')
                print(f"   - {player} on {server}")
        else:
            print("   No online sessions found")
            
            # Check all sessions regardless of state
            all_sessions = await db.player_sessions.find(
                {'guild_id': guild_id}
            ).to_list(length=10)
            print(f"   Total sessions in database: {len(all_sessions)}")
            
            if all_sessions:
                print("   Recent session states:")
                for session in all_sessions[:3]:
                    player = session.get('character_name') or session.get('player_name', 'Unknown')
                    state = session.get('state', 'unknown')
                    print(f"   - {player}: {state}")
        
        # Check voice channel data (fallback for /online command)
        voice_data = await db.guilds.find_one(
            {'guild_id': guild_id},
            {'voice_channel_count': 1, 'servers': 1}
        )
        
        if voice_data:
            vc_count = voice_data.get('voice_channel_count', 0)
            servers = voice_data.get('servers', [])
            print(f"✅ Voice channel player count: {vc_count}")
            print(f"✅ Configured servers: {len(servers)}")
            
            if servers:
                for server in servers:
                    name = server.get('name', 'Unknown')
                    enabled = server.get('enabled', False)
                    print(f"   - {name}: {'Enabled' if enabled else 'Disabled'}")
        
        client.close()
        
        # Summary
        print(f"\n📊 /online Command Status:")
        if sessions:
            print(f"   Will show {len(sessions)} online players from real server data")
        elif all_sessions:
            print(f"   Has {len(all_sessions)} total sessions but none currently online")
        else:
            print(f"   No player session data - will show voice channel count ({vc_count if voice_data else 0})")
        
    except Exception as e:
        print(f"Test failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_online_command())