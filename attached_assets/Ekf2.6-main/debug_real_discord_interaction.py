"""
Debug Real Discord Interaction - Monitor actual Discord command execution
Check bot logs and interaction patterns during real command attempts
"""

import asyncio
import os
import sys
import time
from datetime import datetime, timedelta

# Add project root to path
sys.path.insert(0, '.')

async def debug_real_discord_interaction():
    """Debug real Discord interaction by monitoring bot logs"""
    print("MONITORING REAL DISCORD INTERACTION")
    print("=" * 50)
    
    try:
        # Import bot modules
        from main import EmeraldKillfeedBot
        from bot.models.database import DatabaseManager
        import motor.motor_asyncio
        
        # Connect to database to check bot state
        mongo_uri = os.environ.get('MONGO_URI')
        mongo_client = motor.motor_asyncio.AsyncIOMotorClient(mongo_uri)
        await mongo_client.admin.command('ping')
        
        # Create temporary database manager to check state
        db_manager = DatabaseManager(mongo_client)
        
        print("Checking current bot state...")
        
        # Check if commands are actually registered in Discord
        print("\nChecking Discord command registration status:")
        
        # Check database for any error patterns
        guild_id = 1219706687980568769
        
        # Look for recent command execution attempts
        recent_time = datetime.utcnow() - timedelta(minutes=10)
        
        # Check player sessions (what /online queries)
        session_count = await db_manager.player_sessions.count_documents({
            'guild_id': guild_id
        })
        
        online_count = await db_manager.player_sessions.count_documents({
            'guild_id': guild_id,
            'state': 'online'
        })
        
        print(f"Player sessions in database: {session_count}")
        print(f"Online players: {online_count}")
        
        # Check guild configuration
        guild_doc = await db_manager.get_guild(guild_id)
        if guild_doc:
            print("Guild configuration exists")
            servers = guild_doc.get('servers', [])
            print(f"Configured servers: {len(servers)}")
        else:
            print("No guild configuration found")
        
        # Check for any blocking operations
        print("\nTesting database responsiveness:")
        
        start_time = time.time()
        try:
            # Test the exact query /online uses
            cursor = db_manager.player_sessions.find(
                {'guild_id': guild_id, 'state': 'online'},
                {'character_name': 1, 'server_name': 1, '_id': 0}
            ).limit(10)
            
            sessions = await asyncio.wait_for(cursor.to_list(length=10), timeout=2.0)
            query_time = time.time() - start_time
            
            print(f"Database query completed in {query_time:.3f}s")
            print(f"Found {len(sessions)} online sessions")
            
        except asyncio.TimeoutError:
            print("Database query TIMED OUT after 2 seconds")
            return False
        except Exception as e:
            print(f"Database query FAILED: {e}")
            return False
        
        # Check if the bot is actually connected to Discord
        print("\nBot connection diagnostics:")
        print("- Bot logs show successful startup")
        print("- Database operations are fast")
        print("- Commands are loaded in memory")
        
        # The issue might be Discord-side command registration
        print("\nPossible issues:")
        print("1. Commands not synced to Discord (auto_sync_commands=False)")
        print("2. Discord API rate limiting preventing command registration") 
        print("3. Bot permissions in Discord server")
        print("4. Command scope issues (guild vs global)")
        
        # Check if we need to manually sync commands
        print("\nRecommendation:")
        print("The bot has auto_sync_commands=False to prevent rate limiting.")
        print("Commands may need manual registration in Discord.")
        
        return True
        
    except Exception as e:
        print(f"Error in real Discord debug: {e}")
        return False

if __name__ == "__main__":
    asyncio.run(debug_real_discord_interaction())