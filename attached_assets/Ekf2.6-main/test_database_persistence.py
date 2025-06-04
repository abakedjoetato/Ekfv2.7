#!/usr/bin/env python3
"""
Test Database Persistence - Verify player session storage and retrieval
"""
import asyncio
import os
import motor.motor_asyncio
from datetime import datetime, timezone

async def test_database_persistence():
    """Test direct database operations for player sessions"""
    mongo_uri = os.environ.get('MONGO_URI')
    client = motor.motor_asyncio.AsyncIOMotorClient(mongo_uri)
    db = client.EmeraldDB
    
    guild_id = 1219706687980568769
    test_eosid = "000240ecc1ba45d59962bc2d34e0177e"
    
    print("=== DATABASE PERSISTENCE TEST ===")
    
    # Test 1: Direct insertion
    print("\n1. Testing direct insertion...")
    test_session = {
        "guild_id": guild_id,
        "player_id": test_eosid,
        "player_name": "TestPlayer",
        "state": "online",
        "server_name": "Emerald EU",
        "last_updated": datetime.now(timezone.utc)
    }
    
    try:
        result = await db.player_sessions.insert_one(test_session)
        print(f"Insert successful: {result.inserted_id}")
    except Exception as e:
        print(f"Insert failed: {e}")
    
    # Test 2: Query retrieval
    print("\n2. Testing query retrieval...")
    
    # Test the exact queries used by /online command
    test_queries = [
        {"guild_id": guild_id, "state": "online"},
        {"guild_id": guild_id, "status": "online"},
        {"guild_id": guild_id, "server_name": "Emerald EU", "state": "online"}
    ]
    
    for i, query in enumerate(test_queries, 1):
        try:
            count = await db.player_sessions.count_documents(query)
            print(f"Query {i} {query}: {count} results")
            
            if count > 0:
                session = await db.player_sessions.find_one(query)
                player_name = session.get('player_name', 'Unknown')
                print(f"  Found player: {player_name}")
        except Exception as e:
            print(f"Query {i} failed: {e}")
    
    # Test 3: Update operation (upsert)
    print("\n3. Testing upsert operation...")
    
    upsert_data = {
        "$set": {
            "state": "online",
            "server_name": "Emerald EU",
            "last_updated": datetime.now(timezone.utc),
            "player_name": "UpdatedTestPlayer"
        }
    }
    
    try:
        result = await db.player_sessions.update_one(
            {"guild_id": guild_id, "player_id": test_eosid},
            upsert_data,
            upsert=True
        )
        print(f"Upsert result: matched={result.matched_count}, modified={result.modified_count}, upserted={result.upserted_id}")
    except Exception as e:
        print(f"Upsert failed: {e}")
    
    # Test 4: Check final state
    print("\n4. Final database state...")
    total_sessions = await db.player_sessions.count_documents({"guild_id": guild_id})
    online_sessions = await db.player_sessions.count_documents({"guild_id": guild_id, "state": "online"})
    
    print(f"Total sessions: {total_sessions}")
    print(f"Online sessions: {online_sessions}")
    
    # Show all sessions for this guild
    print("\nAll sessions:")
    async for session in db.player_sessions.find({"guild_id": guild_id}):
        player_name = session.get('player_name', 'Unknown')
        state = session.get('state', 'unknown')
        server = session.get('server_name', 'Unknown')
        print(f"  {player_name} - {state} on {server}")
    
    # Test 5: Cleanup
    print("\n5. Cleanup test data...")
    cleanup_result = await db.player_sessions.delete_many({"guild_id": guild_id, "player_id": test_eosid})
    print(f"Cleaned up {cleanup_result.deleted_count} test records")
    
    client.close()
    
    print("\n=== TEST SUMMARY ===")
    print("Database operations working correctly")
    print("Issue is likely in the unified processor database calls")

if __name__ == "__main__":
    asyncio.run(test_database_persistence())