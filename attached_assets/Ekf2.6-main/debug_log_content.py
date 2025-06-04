#!/usr/bin/env python3
"""
Debug log content to understand classification patterns
"""
import asyncio
import os
from motor.motor_asyncio import AsyncIOMotorClient

async def debug_log_content():
    """Debug actual log content to improve classification"""
    
    # Connect to MongoDB
    mongo_uri = os.getenv('MONGO_URI')
    if not mongo_uri:
        print("❌ MONGO_URI not found in environment")
        return
    
    client = AsyncIOMotorClient(mongo_uri)
    db = client.emerald_killfeed
    
    try:
        guild_id = 1219706687980568769
        
        # Import required modules
        from bot.utils.connection_pool import connection_manager
        await connection_manager.start()
        
        # Get server config
        guild_doc = await db.guilds.find_one({"guild_id": guild_id})
        if not guild_doc or not guild_doc.get('servers'):
            print("❌ No server configuration found")
            return
        
        server_config = guild_doc['servers'][0]
        server_name = server_config.get('name', 'Unknown')
        print(f"🔍 Examining log content for server: {server_name}")
        
        # Connect to SFTP and read recent log lines
        async with connection_manager.get_connection(guild_id, server_config) as conn:
            if not conn:
                print("❌ Failed to connect to server")
                return
            
            sftp = await conn.start_sftp_client()
            host = server_config.get('host', 'unknown')
            server_id = server_config.get('server_id', 'unknown')
            deadside_log_path = f"./{host}_{server_id}/Logs/Deadside.log"
            
            print(f"📄 Reading from: {deadside_log_path}")
            
            async with sftp.open(deadside_log_path, 'rb') as file:
                # Read last 50 lines for analysis
                await file.seek(-5000, 2)  # Seek to 5KB from end
                content = await file.read()
                lines = content.decode('utf-8', errors='ignore').splitlines()
                
                print(f"📊 Analyzing last {len(lines)} lines:")
                print("=" * 80)
                
                # Show sample log entries
                for i, line in enumerate(lines[-20:], 1):  # Last 20 lines
                    line = line.strip()
                    if line:
                        print(f"{i:2d}: {line}")
                
                print("=" * 80)
                
                # Look for player-related patterns
                player_patterns = [
                    'player',
                    'connect',
                    'disconnect', 
                    'join',
                    'leave',
                    'login',
                    'logout',
                    'kill',
                    'death',
                    'damage'
                ]
                
                pattern_counts = {}
                for line in lines[-100:]:  # Analyze last 100 lines
                    line_lower = line.lower()
                    for pattern in player_patterns:
                        if pattern in line_lower:
                            pattern_counts[pattern] = pattern_counts.get(pattern, 0) + 1
                
                print(f"🔍 Pattern analysis (last 100 lines):")
                for pattern, count in sorted(pattern_counts.items(), key=lambda x: x[1], reverse=True):
                    print(f"   {pattern}: {count} occurrences")
                
        await connection_manager.stop()
        
    except Exception as e:
        print(f"❌ Error debugging log content: {e}")
        import traceback
        traceback.print_exc()
    finally:
        client.close()

if __name__ == "__main__":
    asyncio.run(debug_log_content())