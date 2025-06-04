"""
Configure Server Credentials - Update database with environment variable references
"""

import asyncio
import os
from motor.motor_asyncio import AsyncIOMotorClient

async def configure_server_credentials():
    """Configure server with SFTP credentials from environment variables"""
    try:
        # Connect to database
        mongo_uri = os.getenv('MONGO_URI')
        if not mongo_uri:
            print("Missing MONGO_URI environment variable")
            return
        
        client = AsyncIOMotorClient(mongo_uri)
        db = client.EmeraldDB
        
        guild_id = 1219706687980568769  # Emerald Servers
        
        # Get SSH credentials from environment
        ssh_host = os.getenv('SSH_HOST')
        ssh_username = os.getenv('SSH_USERNAME') 
        ssh_password = os.getenv('SSH_PASSWORD')
        ssh_port = os.getenv('SSH_PORT', '22')
        
        if not all([ssh_host, ssh_username, ssh_password]):
            print("Missing SSH credentials in environment variables:")
            print(f"  SSH_HOST: {'✓' if ssh_host else '✗'}")
            print(f"  SSH_USERNAME: {'✓' if ssh_username else '✗'}")
            print(f"  SSH_PASSWORD: {'✓' if ssh_password else '✗'}")
            print(f"  SSH_PORT: {ssh_port}")
            return
        
        # Create server configuration with correct server_id for dynamic path
        server_config = {
            "name": "Emerald EU",
            "server_id": "7020",
            "_id": "7020",
            "enabled": True,
            "host": ssh_host,
            "sftp_host": ssh_host,
            "sftp_username": ssh_username,
            "sftp_password": ssh_password,
            "sftp_port": int(ssh_port),
            "port": int(ssh_port),
            "log_file": "Deadside.log",
            "path": "/root/servers/79.127.236.1_7020/actual1",
            "killfeed_path": "/root/servers/79.127.236.1_7020/actual1/killfeed.csv"
        }
        
        # Update guild configuration with server
        result = await db.guilds.update_one(
            {'guild_id': guild_id},
            {
                '$set': {
                    'servers': [server_config],
                    'name': 'Emerald Servers'
                }
            },
            upsert=True
        )
        
        if result.modified_count > 0 or result.upserted_id:
            print("✅ Server configuration updated successfully")
            print(f"   Host: {ssh_host}")
            print(f"   Username: {ssh_username}")
            print(f"   Port: {ssh_port}")
            print(f"   Log path: {server_config['log_path']}")
        else:
            print("❌ Failed to update server configuration")
        
        client.close()
        
    except Exception as e:
        print(f"Configuration failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(configure_server_credentials())