"""
Update Server SSH Credentials - Add missing SSH credentials to server configuration
"""

import asyncio
import os
from motor.motor_asyncio import AsyncIOMotorClient

async def update_server_ssh_credentials():
    """Update server SSH credentials from environment variables"""
    try:
        # Initialize database connection
        mongo_uri = os.getenv('MONGO_URI')
        client = AsyncIOMotorClient(mongo_uri)
        db = client.emerald_killfeed
        servers_collection = db.servers
        
        # Get SSH credentials from environment
        ssh_host = os.getenv('SSH_HOST')
        ssh_username = os.getenv('SSH_USERNAME') 
        ssh_password = os.getenv('SSH_PASSWORD')
        ssh_port = int(os.getenv('SSH_PORT', 22))
        
        print(f"Updating server with SSH credentials:")
        print(f"  Host: {ssh_host}")
        print(f"  Username: {ssh_username}")
        print(f"  Port: {ssh_port}")
        
        # Update the Emerald EU server with SSH credentials
        result = await servers_collection.update_one(
            {
                'guild_id': 1219706687980568769,
                'server_id': '7020'
            },
            {
                '$set': {
                    'ssh_host': ssh_host,
                    'ssh_username': ssh_username,
                    'ssh_password': ssh_password,
                    'ssh_port': ssh_port,
                    'log_path': '/home/deadside/79.127.236.1_7020/actual1/Deadside/Saved/Logs/Deadside.log'
                }
            }
        )
        
        if result.modified_count > 0:
            print("✅ Server SSH credentials updated successfully")
        else:
            print("❌ Failed to update server SSH credentials")
            
        # Verify the update
        server = await servers_collection.find_one({
            'guild_id': 1219706687980568769,
            'server_id': '7020'
        })
        
        if server:
            print(f"\nVerification - Server: {server.get('server_name', 'Unknown')}")
            print(f"  SSH Host: {server.get('ssh_host', 'NOT SET')}")
            print(f"  SSH Username: {server.get('ssh_username', 'NOT SET')}")
            print(f"  SSH Port: {server.get('ssh_port', 'NOT SET')}")
            print(f"  SSH Password: {'SET' if server.get('ssh_password') else 'NOT SET'}")
            print(f"  Log Path: {server.get('log_path', 'NOT SET')}")
            
    except Exception as e:
        print(f"Error updating server SSH credentials: {e}")

if __name__ == "__main__":
    asyncio.run(update_server_ssh_credentials())