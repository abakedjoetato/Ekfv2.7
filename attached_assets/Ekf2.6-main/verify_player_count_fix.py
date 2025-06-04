#!/usr/bin/env python3
"""
Verify Player Count Fix - Comprehensive verification of player state accuracy
"""
import asyncio
import os
import motor.motor_asyncio
from datetime import datetime, timezone

async def verify_player_count_fix():
    """Verify the player count accuracy fix is working correctly"""
    mongo_uri = os.environ.get('MONGO_URI')
    client = motor.motor_asyncio.AsyncIOMotorClient(mongo_uri)
    db = client.EmeraldDB
    
    guild_id = 1219706687980568769
    
    print("=== PLAYER COUNT ACCURACY VERIFICATION ===")
    
    # 1. Check current database state after cold start
    print("\n1. Post-Cold Start Database State:")
    total_sessions = await db.player_sessions.count_documents({'guild_id': guild_id})
    online_sessions = await db.player_sessions.count_documents({'guild_id': guild_id, 'state': 'online'})
    offline_sessions = await db.player_sessions.count_documents({'guild_id': guild_id, 'state': 'offline'})
    
    print(f"  Total sessions: {total_sessions}")
    print(f"  Online sessions: {online_sessions}")
    print(f"  Offline sessions: {offline_sessions}")
    
    # 2. Test /online command queries directly
    print("\n2. Direct /online Command Query Test:")
    
    # Query exactly as /online command does
    query_results = {}
    
    # All servers query
    all_query = {'guild_id': guild_id, 'state': 'online'}
    all_count = await db.player_sessions.count_documents(all_query)
    query_results['all_servers'] = all_count
    print(f"  All servers (/online): {all_count} players")
    
    # Specific server query  
    server_query = {'guild_id': guild_id, 'server_name': 'Emerald EU', 'state': 'online'}
    server_count = await db.player_sessions.count_documents(server_query)
    query_results['emerald_eu'] = server_count
    print(f"  Emerald EU (/online Emerald EU): {server_count} players")
    
    # 3. Check if any sessions exist but with wrong states
    print("\n3. Session State Analysis:")
    
    # Count sessions by state
    state_counts = {}
    async for doc in db.player_sessions.aggregate([
        {'$match': {'guild_id': guild_id}},
        {'$group': {'_id': '$state', 'count': {'$sum': 1}}}
    ]):
        state_counts[doc['_id']] = doc['count']
    
    print(f"  Session states: {state_counts}")
    
    # 4. Show recent activity
    print("\n4. Recent Player Activity:")
    if total_sessions > 0:
        recent_limit = min(10, total_sessions)
        async for session in db.player_sessions.find({'guild_id': guild_id}).sort('last_updated', -1).limit(recent_limit):
            player_name = session.get('player_name', 'Unknown')
            player_id = session.get('player_id', 'Unknown')[:8] + '...'
            state = session.get('state', 'unknown')
            server = session.get('server_name', 'Unknown')
            last_updated = session.get('last_updated', 'Unknown')
            print(f"  {player_name} ({player_id}) - {state} on {server} at {last_updated}")
    else:
        print("  No sessions found")
    
    # 5. Create test session to verify /online would show it
    print("\n5. Testing /online Display Logic:")
    
    test_player_id = "test_online_display_001"
    test_session = {
        "guild_id": guild_id,
        "player_id": test_player_id,
        "player_name": "TestOnlinePlayer",
        "state": "online",
        "server_name": "Emerald EU",
        "last_updated": datetime.now(timezone.utc),
        "joined_at": datetime.now(timezone.utc).isoformat()
    }
    
    try:
        # Insert test session
        await db.player_sessions.insert_one(test_session)
        print(f"  ✓ Created test online session")
        
        # Test queries with test session
        test_all_count = await db.player_sessions.count_documents(all_query)
        test_server_count = await db.player_sessions.count_documents(server_query)
        
        print(f"  All servers with test player: {test_all_count}")
        print(f"  Emerald EU with test player: {test_server_count}")
        
        # Query the actual data as /online would
        print("\n  Test /online results:")
        async for session in db.player_sessions.find(server_query):
            player_name = session.get('player_name', session.get('character_name', 'Unknown'))
            joined_at = session.get('joined_at')
            platform = session.get('platform', 'Unknown')
            player_id_display = session.get('player_id', '')
            
            print(f"    Player: {player_name}")
            print(f"    Platform: {platform}")
            print(f"    Joined: {joined_at}")
            print(f"    ID: {player_id_display}")
        
        # Clean up test session
        await db.player_sessions.delete_one({"player_id": test_player_id})
        print(f"  ✓ Cleaned up test session")
        
    except Exception as e:
        print(f"  ✗ Test session creation failed: {e}")
    
    # 6. Voice channel comparison
    print("\n6. Voice Channel vs Database Comparison:")
    
    # Check guild config for voice channel settings
    guild_config = await db.guild_configs.find_one({'guild_id': guild_id})
    if guild_config:
        vc_config = guild_config.get('server_channels', {}).get('default', {})
        vc_id = vc_config.get('playercountvc')
        print(f"  Voice channel ID: {vc_id}")
        
        # Voice channel should reflect database online count
        print(f"  Database online count: {online_sessions}")
        print(f"  Voice channel should show: {online_sessions} players")
    
    # 7. Check parser state
    print("\n7. Parser State Check:")
    parser_state = await db.parser_states.find_one({
        'guild_id': guild_id,
        'server_name': 'Emerald EU',
        'parser_type': 'unified'
    })
    
    if parser_state:
        last_processed = parser_state.get('last_processed', 'Unknown')
        last_position = parser_state.get('last_byte_position', 0)
        print(f"  Last processed: {last_processed}")
        print(f"  Last position: {last_position}")
    else:
        print(f"  No parser state found")
    
    client.close()
    
    # 8. Final assessment
    print("\n=== VERIFICATION RESULTS ===")
    
    if total_sessions == 0:
        print("❌ ISSUE: No player sessions in database")
        print("   Cold start processing detected players but sessions didn't persist")
        print("   The /online command will show empty until this is resolved")
    elif online_sessions == 0:
        print("⚠️  PARTIAL: Sessions exist but none are online")
        print("   Players may have disconnected or states weren't updated correctly")
        print("   The /online command will show empty state")
    else:
        print("✅ SUCCESS: Player sessions found in database")
        print(f"   {online_sessions} players online, {total_sessions} total sessions")
        print("   The /online command should work correctly")
    
    print(f"\nQuery results for /online command:")
    print(f"  /online (all servers): {query_results.get('all_servers', 0)} players")
    print(f"  /online Emerald EU: {query_results.get('emerald_eu', 0)} players")

if __name__ == "__main__":
    asyncio.run(verify_player_count_fix())