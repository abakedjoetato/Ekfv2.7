"""
Check Server SSH Configuration - Examine what SSH credentials are actually stored
"""

import asyncio
import os
from motor.motor_asyncio import AsyncIOMotorClient

async def check_server_config():
    """Check the actual server configuration in database"""
    try:
        # Connect to database
        mongo_uri = os.getenv('MONGO_URI')
        if not mongo_uri:
            print("Missing MONGO_URI environment variable")
            return
        
        client = AsyncIOMotorClient(mongo_uri)
        db = client.EmeraldDB
        
        guild_id = 1219706687980568769  # Emerald Servers
        
        # Get guild configuration
        guild_config = await db.guilds.find_one({'guild_id': guild_id})
        if guild_config:
            print(f"Guild configuration found:")
            print(f"  Guild ID: {guild_config.get('guild_id')}")
            print(f"  Name: {guild_config.get('name', 'Unknown')}")
            
            # Check servers array
            servers = guild_config.get('servers', [])
            print(f"  Number of servers: {len(servers)}")
            
            for i, server in enumerate(servers):
                print(f"\n  Server {i+1}:")
                print(f"    Name: {server.get('name', 'Unknown')}")
                print(f"    Enabled: {server.get('enabled', False)}")
                print(f"    Host: {server.get('host', 'Not set')}")
                print(f"    SFTP Host: {server.get('sftp_host', 'Not set')}")
                print(f"    Username: {server.get('sftp_username', 'Not set')}")
                print(f"    Password: {'Set' if server.get('sftp_password') else 'Not set'}")
                print(f"    Port: {server.get('sftp_port', server.get('port', 'Not set'))}")
                print(f"    Log Path: {server.get('log_path', server.get('path', 'Not set'))}")
                print(f"    Server ID: {server.get('server_id', 'Not set')}")
                
        else:
            print(f"No guild configuration found for {guild_id}")
        
        await client.close()
        
    except Exception as e:
        print(f"Check failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(check_server_config())