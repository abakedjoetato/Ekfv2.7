"""
Configure SSH Credentials - Add SSH credentials to guild configuration
"""

import asyncio
import os
from motor.motor_asyncio import AsyncIOMotorClient

async def configure_ssh_credentials():
    """Add SSH credentials to the guild configuration"""
    try:
        # Initialize database connection
        mongo_uri = os.getenv('MONGO_URI')
        client = AsyncIOMotorClient(mongo_uri)
        db = client.emerald_killfeed
        
        # Update the guild configuration with SSH credentials
        result = await db.guild_configs.update_one(
            {
                'guild_id': 1219706687980568769,
                'servers.server_id': '7020'
            },
            {
                '$set': {
                    'servers.$.ssh_host': '79.127.236.1',
                    'servers.$.ssh_username': 'deadside',
                    'servers.$.ssh_password': 'deadsidepass',
                    'servers.$.ssh_port': 22,
                    'servers.$.log_path': '/home/deadside/79.127.236.1_7020/actual1/Deadside/Saved/Logs/Deadside.log'
                }
            }
        )
        
        if result.modified_count > 0:
            print("✅ SSH credentials added to guild configuration")
        else:
            print("❌ Failed to update guild configuration")
            
        # Verify the update
        config = await db.guild_configs.find_one({'guild_id': 1219706687980568769})
        
        if config:
            servers = config.get('servers', [])
            for server in servers:
                if server.get('server_id') == '7020':
                    print(f"\nVerification - Server: {server.get('server_name', 'Unknown')}")
                    print(f"  SSH Host: {server.get('ssh_host', 'NOT SET')}")
                    print(f"  SSH Username: {server.get('ssh_username', 'NOT SET')}")
                    print(f"  SSH Port: {server.get('ssh_port', 'NOT SET')}")
                    print(f"  SSH Password: {'SET' if server.get('ssh_password') else 'NOT SET'}")
                    print(f"  Log Path: {server.get('log_path', 'NOT SET')}")
                    break
            
    except Exception as e:
        print(f"Error configuring SSH credentials: {e}")

if __name__ == "__main__":
    asyncio.run(configure_ssh_credentials())