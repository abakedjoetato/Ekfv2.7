#!/usr/bin/env python3
"""
Direct Database Verification - Check actual database state using bot's connection method
"""
import asyncio
import os
import motor.motor_asyncio
from datetime import datetime, timezone

async def verify_database_state():
    """Verify database state using the same connection method as the bot"""
    mongo_uri = os.environ.get('MONGO_URI')
    print(f"Connecting to: {mongo_uri[:20]}...")
    
    client = motor.motor_asyncio.AsyncIOMotorClient(mongo_uri)
    db = client.EmeraldDB
    
    guild_id = 1219706687980568769
    
    print("=== DIRECT DATABASE VERIFICATION ===")
    
    # 1. Check all collections
    print("\n1. Available Collections:")
    collections = await db.list_collection_names()
    for collection in collections:
        count = await db[collection].count_documents({})
        print(f"  {collection}: {count} documents")
    
    # 2. Check player_sessions specifically
    print("\n2. Player Sessions Collection Analysis:")
    
    # Total count
    total_count = await db.player_sessions.count_documents({})
    print(f"  Total documents: {total_count}")
    
    # Guild-specific count
    guild_count = await db.player_sessions.count_documents({'guild_id': guild_id})
    print(f"  Guild {guild_id} documents: {guild_count}")
    
    # State breakdown
    states = {}
    async for doc in db.player_sessions.find({'guild_id': guild_id}):
        state = doc.get('state', 'unknown')
        states[state] = states.get(state, 0) + 1
    
    print(f"  State breakdown: {states}")
    
    # 3. Recent documents
    print("\n3. Recent Player Sessions (last 5):")
    async for doc in db.player_sessions.find({'guild_id': guild_id}).sort('last_updated', -1).limit(5):
        player_id = doc.get('player_id', 'unknown')
        state = doc.get('state', 'unknown')
        server = doc.get('server_name', 'unknown')
        updated = doc.get('last_updated', 'unknown')
        print(f"  {player_id[:8]}... -> {state} on {server} (updated: {updated})")
    
    # 4. Test /online command queries directly
    print("\n4. /online Command Query Simulation:")
    
    # All servers query
    all_online = await db.player_sessions.count_documents({
        'guild_id': guild_id,
        'state': 'online'
    })
    print(f"  /online (all servers): {all_online} players")
    
    # Specific server query
    emerald_online = await db.player_sessions.count_documents({
        'guild_id': guild_id,
        'server_name': 'Emerald EU',
        'state': 'online'
    })
    print(f"  /online Emerald EU: {emerald_online} players")
    
    # 5. Sample online players
    if emerald_online > 0:
        print("\n5. Sample Online Players:")
        async for session in db.player_sessions.find({
            'guild_id': guild_id,
            'server_name': 'Emerald EU',
            'state': 'online'
        }).limit(5):
            player_name = session.get('player_name', session.get('character_name', 'Unknown'))
            player_id = session.get('player_id', '')
            joined_at = session.get('joined_at', 'Unknown')
            platform = session.get('platform', 'Unknown')
            
            print(f"    {player_name}")
            print(f"      ID: {player_id[:8]}...")
            print(f"      Joined: {joined_at}")
            print(f"      Platform: {platform}")
    
    # 6. Database connection verification
    print("\n6. Database Connection Verification:")
    try:
        server_info = await client.server_info()
        print(f"  MongoDB version: {server_info.get('version', 'unknown')}")
        print(f"  Connection: Active")
    except Exception as e:
        print(f"  Connection error: {e}")
    
    client.close()
    
    print(f"\n=== VERIFICATION COMPLETE ===")
    if emerald_online > 0:
        print(f"✅ SUCCESS: Database contains {emerald_online} online players")
        print(f"   /online command should work correctly")
    else:
        print(f"❌ ISSUE: No online players found in database")
        print(f"   Cold start batch commit may have failed")

if __name__ == "__main__":
    asyncio.run(verify_database_state())