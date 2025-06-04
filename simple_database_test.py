#!/usr/bin/env python3
"""
Simple Database Test - Check if player sessions exist and /online command works
"""
import asyncio
import os
import motor.motor_asyncio

async def test_database():
    """Simple test of database state"""
    try:
        mongo_uri = os.environ.get('MONGO_URI')
        client = motor.motor_asyncio.AsyncIOMotorClient(mongo_uri)
        db = client.EmeraldDB
        
        guild_id = 1219706687980568769
        
        print("=== SIMPLE DATABASE TEST ===")
        
        # Count documents
        total = await db.player_sessions.count_documents({'guild_id': guild_id})
        online = await db.player_sessions.count_documents({'guild_id': guild_id, 'state': 'online'})
        emerald_online = await db.player_sessions.count_documents({
            'guild_id': guild_id, 
            'server_name': 'Emerald EU', 
            'state': 'online'
        })
        
        print(f"Total sessions: {total}")
        print(f"Online sessions: {online}")
        print(f"Emerald EU online: {emerald_online}")
        
        # List first few online players
        if emerald_online > 0:
            print("\nOnline players:")
            async for session in db.player_sessions.find({
                'guild_id': guild_id, 
                'server_name': 'Emerald EU', 
                'state': 'online'
            }).limit(5):
                player_id = session.get('player_id', 'unknown')
                player_name = session.get('player_name', 'unknown')
                print(f"  {player_id[:8]}... ({player_name})")
        
        client.close()
        
        if emerald_online > 0:
            print(f"\n✅ /online command should work with {emerald_online} players")
        else:
            print(f"\n❌ /online command will show empty")
            
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    asyncio.run(test_database())