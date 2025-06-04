"""
Check Player Count Accuracy - Verify current player sessions and voice channel configuration
"""

import asyncio
import os
from motor.motor_asyncio import AsyncIOMotorClient

async def check_player_count_accuracy():
    """Check current player count and voice channel configuration"""
    try:
        mongo_uri = os.getenv('MONGO_URI')
        client = AsyncIOMotorClient(mongo_uri)
        db = client.emerald_killfeed
        
        guild_id = 1219706687980568769
        server_id = "7020"
        
        print("=== Player Session Analysis ===")
        
        # Check current player sessions
        sessions = await db.player_sessions.find({
            'guild_id': guild_id,
            'server_id': server_id
        }).to_list(length=None)
        
        print(f"Total player sessions: {len(sessions)}")
        
        # Count by state
        state_counts = {}
        for session in sessions:
            state = session.get('current_state', 'unknown')
            state_counts[state] = state_counts.get(state, 0) + 1
            
        print("Player states:")
        for state, count in state_counts.items():
            print(f"  {state}: {count}")
            
        # Show sample sessions
        print("\nSample sessions:")
        for i, session in enumerate(sessions[:5]):
            print(f"  {i+1}. EOS ID: {session.get('eos_id', 'None')[:20]}...")
            print(f"     State: {session.get('current_state', 'Unknown')}")
            print(f"     Player: {session.get('player_name', 'Unknown')}")
            print(f"     Last Update: {session.get('last_updated', 'Unknown')}")
            print()
            
        # Calculate expected voice channel count
        online_count = state_counts.get('online', 0)
        queued_count = state_counts.get('queued', 0)
        total_count = online_count + queued_count
        
        print(f"Expected voice channel count: {total_count} (Online: {online_count}, Queued: {queued_count})")
        
        # Check voice channel configuration
        print("\n=== Voice Channel Configuration ===")
        
        guild_config = await db.guild_configs.find_one({'guild_id': guild_id})
        if guild_config:
            server_channels = guild_config.get('server_channels', {})
            print(f"Available server channels: {list(server_channels.keys())}")
            
            for channel_set_name, channels in server_channels.items():
                voice_channel_id = channels.get('voice_channel')
                if voice_channel_id:
                    print(f"  {channel_set_name} voice channel: {voice_channel_id}")
                else:
                    print(f"  {channel_set_name}: No voice channel configured")
        else:
            print("No guild configuration found")
            
        # Check parser state
        print("\n=== Parser State ===")
        parser_state = await db.parser_states.find_one({
            'guild_id': guild_id,
            'server_id': server_id,
            'parser_type': 'unified'
        })
        
        if parser_state:
            print(f"Parser state exists:")
            print(f"  Last processed line: {parser_state.get('last_processed_line', 0)}")
            print(f"  Last update: {parser_state.get('last_updated')}")
            print(f"  Mode: {'HOT START' if parser_state.get('last_processed_line', 0) > 0 else 'COLD START'}")
        else:
            print("No parser state found - will trigger COLD START")
            
        await client.close()
        
    except Exception as e:
        print(f"Error checking player count: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(check_player_count_accuracy())