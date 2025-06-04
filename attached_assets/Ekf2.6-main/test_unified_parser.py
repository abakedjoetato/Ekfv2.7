#!/usr/bin/env python3
"""
Test unified parser processing to debug why data isn't being collected
"""
import asyncio
import os
from motor.motor_asyncio import AsyncIOMotorClient
from datetime import datetime, timezone

async def test_unified_parser():
    """Test the unified parser directly"""
    
    # Connect to MongoDB
    mongo_uri = os.getenv('MONGO_URI')
    if not mongo_uri:
        print("❌ MONGO_URI not found in environment")
        return
    
    client = AsyncIOMotorClient(mongo_uri)
    db = client.emerald_killfeed
    
    try:
        guild_id = 1219706687980568769
        
        # Import the unified parser
        from bot.parsers.scalable_unified_parser import ScalableUnifiedParser
        
        # Create mock bot instance
        mock_bot = type('MockBot', (), {
            'db_manager': type('MockDBManager', (), {
                'guilds': db.guilds,
                'kills': db.kills,
                'player_sessions': db.player_sessions,
                'parser_states': db.parser_states
            })()
        })()
        
        # Create parser instance with mock bot
        parser = ScalableUnifiedParser(mock_bot)
        
        print(f"🔍 Testing unified parser for guild {guild_id}")
        
        # Trigger manual processing
        result = await parser.process_guild_manual(guild_id)
        
        print(f"📊 Parser result: {result}")
        
        if result.get('success'):
            print(f"✅ Processing successful!")
            print(f"   Processed servers: {result.get('processed_servers', 0)}")
            print(f"   Entries processed: {result.get('entries_processed', 0)}")
            print(f"   Rotated servers: {result.get('rotated_servers', 0)}")
        else:
            print(f"❌ Processing failed: {result.get('error', 'Unknown error')}")
        
        # Check if any new data was created
        print(f"\n🔍 Checking database for new data...")
        
        kills_count = await db.kills.count_documents({"guild_id": guild_id})
        print(f"📊 Total kills in database: {kills_count}")
        
        # Check latest parser state
        parser_state = await db.parser_states.find_one(
            {"guild_id": guild_id, "server_id": "7020"},
            sort=[("last_run", -1)]
        )
        
        if parser_state:
            print(f"📊 Parser state:")
            print(f"   Last position: {parser_state.get('last_position', 0)}")
            print(f"   Last run: {parser_state.get('last_run')}")
            print(f"   Last line: {parser_state.get('last_line', 0)}")
        else:
            print(f"❌ No parser state found")
            
    except Exception as e:
        print(f"❌ Error testing unified parser: {e}")
        import traceback
        traceback.print_exc()
    finally:
        client.close()

if __name__ == "__main__":
    asyncio.run(test_unified_parser())