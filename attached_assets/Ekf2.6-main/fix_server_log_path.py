#!/usr/bin/env python3
"""
Fix existing server log path to use dynamic format
"""
import asyncio
import os
from motor.motor_asyncio import AsyncIOMotorClient
from datetime import datetime, timezone

async def fix_server_log_path():
    """Update existing server to use correct dynamic log path format"""
    
    # Connect to MongoDB
    mongo_uri = os.getenv('MONGO_URI')
    if not mongo_uri:
        print("❌ MONGO_URI not found in environment")
        return
    
    client = AsyncIOMotorClient(mongo_uri)
    db = client.emerald_killfeed
    
    try:
        guild_id = 1219706687980568769
        
        # Get current guild configuration
        guild_doc = await db.guilds.find_one({"guild_id": guild_id})
        if not guild_doc:
            print(f"❌ Guild {guild_id} not found")
            return
        
        servers = guild_doc.get('servers', [])
        if not servers:
            print(f"❌ No servers found for guild {guild_id}")
            return
        
        print(f"📊 Found {len(servers)} servers for guild {guild_id}")
        
        # Update each server with correct log path format
        for i, server in enumerate(servers):
            server_id = server.get('_id') or server.get('server_id')
            host = server.get('host') or server.get('hostname')
            current_log_path = server.get('log_path', 'Not Set')
            enabled = server.get('enabled', 'Not Set')
            
            print(f"\n🔍 Server {i+1}: {server.get('name', 'Unknown')}")
            print(f"   ID: {server_id}")
            print(f"   Host: {host}")
            print(f"   Current log_path: {current_log_path}")
            print(f"   Enabled: {enabled}")
            
            if host and server_id:
                # Create correct dynamic log path
                new_log_path = f"./{host}_{server_id}/Logs/Deadside.log"
                
                # Update server configuration
                update_result = await db.guilds.update_one(
                    {"guild_id": guild_id},
                    {
                        "$set": {
                            f"servers.{i}.log_path": new_log_path,
                            f"servers.{i}.enabled": True,  # Ensure it's enabled
                            f"servers.{i}.updated_at": datetime.now(timezone.utc)
                        }
                    }
                )
                
                if update_result.modified_count > 0:
                    print(f"   ✅ Updated log_path to: {new_log_path}")
                    print(f"   ✅ Enabled: True")
                else:
                    print(f"   ⚠️ No changes made")
            else:
                print(f"   ❌ Missing host or server_id")
        
        print(f"\n🎉 Server log path update completed!")
        
    except Exception as e:
        print(f"❌ Error updating server configuration: {e}")
    finally:
        client.close()

if __name__ == "__main__":
    asyncio.run(fix_server_log_path())