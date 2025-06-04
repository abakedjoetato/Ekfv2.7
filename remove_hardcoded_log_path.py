"""
Remove Hardcoded Log Path - Clear the hardcoded log_path so dynamic pattern is used
"""

import asyncio
import os
from motor.motor_asyncio import AsyncIOMotorClient

async def remove_hardcoded_path():
    """Remove the hardcoded log_path from server configuration"""
    try:
        # Connect to database
        mongo_uri = os.getenv('MONGO_URI')
        if not mongo_uri:
            print("Missing MONGO_URI environment variable")
            return
        
        client = AsyncIOMotorClient(mongo_uri)
        db = client.EmeraldDB
        
        guild_id = 1219706687980568769  # Emerald Servers
        
        # Get current guild configuration
        guild_config = await db.guilds.find_one({'guild_id': guild_id})
        if not guild_config or not guild_config.get('servers'):
            print("No guild configuration found")
            return
        
        # Remove log_path from all servers in the configuration
        servers = guild_config.get('servers', [])
        updated_servers = []
        
        for server in servers:
            # Remove problematic hardcoded paths
            if 'log_path' in server:
                del server['log_path']
                print(f"Removed log_path from server {server.get('name', 'Unknown')}")
            if 'base_path' in server:
                del server['base_path']
                print(f"Removed base_path from server {server.get('name', 'Unknown')}")
            
            updated_servers.append(server)
        
        # Update the guild configuration
        result = await db.guilds.update_one(
            {'guild_id': guild_id},
            {'$set': {'servers': updated_servers}}
        )
        
        if result.modified_count > 0:
            print("✅ Successfully removed hardcoded paths")
            print("   Dynamic pattern will now be used: ./79.127.236.1_7020/Logs/Deadside.log")
        else:
            print("❌ No changes made to configuration")
        
        # Verify the configuration
        updated_config = await db.guilds.find_one({'guild_id': guild_id})
        if updated_config and updated_config.get('servers'):
            server = updated_config['servers'][0]
            print(f"\n📊 Updated server configuration:")
            print(f"   Name: {server.get('name')}")
            print(f"   Server ID: {server.get('server_id')}")
            print(f"   Host: {server.get('host')}")
            print(f"   Log path: {'Dynamic pattern' if not server.get('log_path') else server.get('log_path')}")
        
        client.close()
        
    except Exception as e:
        print(f"Failed to remove hardcoded paths: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(remove_hardcoded_path())