#!/usr/bin/env python3
"""
Debug parser processing to understand why no data is being collected
"""
import asyncio
import os
from motor.motor_asyncio import AsyncIOMotorClient
from datetime import datetime, timezone
import asyncssh

async def debug_parser_processing():
    """Debug why the parser isn't collecting data"""
    
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
        
        # Check each server configuration
        for i, server in enumerate(servers):
            server_id = server.get('_id') or server.get('server_id')
            host = server.get('host') or server.get('hostname')
            port = server.get('port', 22)
            username = server.get('username')
            password = server.get('password')
            log_path = server.get('log_path')
            enabled = server.get('enabled', False)
            
            print(f"\n🔍 Server {i+1}: {server.get('name', 'Unknown')}")
            print(f"   ID: {server_id}")
            print(f"   Host: {host}:{port}")
            print(f"   Username: {username}")
            print(f"   Password: {'***' if password else 'Not Set'}")
            print(f"   Log Path: {log_path}")
            print(f"   Enabled: {enabled}")
            
            if not enabled:
                print(f"   ⚠️ Server is disabled - skipping")
                continue
            
            if not all([host, username, password, log_path]):
                print(f"   ❌ Missing required SFTP credentials")
                continue
            
            # Test SFTP connection and file access
            print(f"   🔗 Testing SFTP connection...")
            
            # Define multiple connection strategies for maximum compatibility
            connection_strategies = [
                {
                    'name': 'modern_secure',
                    'kex_algs': [
                        'curve25519-sha256', 'curve25519-sha256@libssh.org',
                        'ecdh-sha2-nistp256', 'ecdh-sha2-nistp384', 'ecdh-sha2-nistp521',
                        'diffie-hellman-group16-sha512', 'diffie-hellman-group18-sha512',
                        'diffie-hellman-group14-sha256'
                    ]
                },
                {
                    'name': 'legacy_compatible',
                    'kex_algs': [
                        'diffie-hellman-group14-sha1', 'diffie-hellman-group1-sha1',
                        'diffie-hellman-group-exchange-sha256', 'diffie-hellman-group-exchange-sha1'
                    ]
                },
                {
                    'name': 'ultra_legacy',
                    'kex_algs': [
                        'diffie-hellman-group1-sha1'
                    ]
                }
            ]
            
            conn = None
            for strategy in connection_strategies:
                try:
                    print(f"      Trying {strategy['name']} strategy...")
                    
                    options = {
                        'username': username,
                        'password': password,
                        'known_hosts': None,
                        'client_keys': None,
                        'preferred_auth': 'password,keyboard-interactive',
                        'kex_algs': strategy['kex_algs'],
                        'encryption_algs': [
                            'aes256-ctr', 'aes192-ctr', 'aes128-ctr',
                            'aes256-cbc', 'aes192-cbc', 'aes128-cbc',
                            '3des-cbc', 'blowfish-cbc'
                        ],
                        'mac_algs': [
                            'hmac-sha2-256', 'hmac-sha2-512',
                            'hmac-sha1', 'hmac-md5'
                        ],
                        'compression_algs': ['none'],
                        'server_host_key_algs': ['ssh-rsa', 'rsa-sha2-256', 'rsa-sha2-512', 'ssh-dss']
                    }
                    
                    conn = await asyncio.wait_for(
                        asyncssh.connect(host, port=port, **options),
                        timeout=30
                    )
                    
                    print(f"   ✅ Connected using {strategy['name']} strategy")
                    break
                    
                except Exception as e:
                    if 'Invalid DH parameters' in str(e):
                        print(f"      DH parameters rejected for {strategy['name']}")
                        continue
                    elif 'auth' in str(e).lower():
                        print(f"      Authentication failed")
                        break
                    else:
                        print(f"      Failed with {strategy['name']}: {e}")
                        continue
            
            if conn:
                try:
                    async with conn:
                        print(f"   ✅ SFTP connection successful")
                        
                        # Test file access
                        async with conn.start_sftp_client() as sftp:
                            print(f"   📁 Testing file access: {log_path}")
                            
                            try:
                                # Check if file exists
                                stat = await sftp.stat(log_path)
                                file_size = stat.size if stat.size is not None else 0
                                modified_time = datetime.fromtimestamp(float(stat.mtime), tz=timezone.utc) if stat.mtime else datetime.now(timezone.utc)
                                
                                print(f"   ✅ Log file found!")
                                print(f"   📏 File size: {file_size:,} bytes")
                                print(f"   🕒 Last modified: {modified_time}")
                                
                                # Read last few lines to check for recent activity
                                if file_size > 0:
                                    # Read last 1000 bytes to get recent entries
                                    read_size = min(1000, file_size)
                                    async with sftp.open(log_path, 'rb') as f:
                                        await f.seek(max(0, file_size - read_size))
                                        content = await f.read()
                                        
                                    try:
                                        text_content = content.decode('utf-8', errors='ignore')
                                        lines = text_content.strip().split('\n')
                                        
                                        print(f"   📝 Last few log entries:")
                                        for line in lines[-3:]:
                                            if line.strip():
                                                print(f"      {line.strip()}")
                                        
                                        # Check for recent timestamps
                                        recent_entries = 0
                                        
                                        for line in lines:
                                            if '[' in line and ']' in line:
                                                try:
                                                    # Extract timestamp from log line
                                                    timestamp_str = line.split('[')[1].split(']')[0]
                                                    # This is a rough check - actual parsing would be more complex
                                                    recent_entries += 1
                                                except:
                                                    pass
                                        
                                        print(f"   📊 Recent log entries found: {recent_entries}")
                                        
                                    except Exception as e:
                                        print(f"   ⚠️ Could not decode file content: {e}")
                                else:
                                    print(f"   ⚠️ Log file is empty")
                                
                            except FileNotFoundError:
                                print(f"   ❌ Log file not found at: {log_path}")
                            except Exception as e:
                                print(f"   ❌ Error accessing log file: {e}")
                                
                except Exception as e:
                    print(f"   ❌ SFTP operations failed: {e}")
            else:
                print(f"   ❌ All connection strategies failed")
        
        # Check parser state
        print(f"\n🔍 Checking parser state...")
        parser_states = []
        async for state in db.parser_states.find({"guild_id": guild_id}):
            parser_states.append(state)
        
        print(f"📊 Found {len(parser_states)} parser states")
        for state in parser_states:
            server_id = state.get('server_id')
            parser_type = state.get('parser_type')
            last_position = state.get('last_position', 0)
            last_run = state.get('last_run')
            
            print(f"   Server {server_id} ({parser_type}): position {last_position}, last run {last_run}")
        
        # Check recent kills/data
        print(f"\n🔍 Checking recent data...")
        
        # Check kills
        kills_count = await db.kills.count_documents({"guild_id": guild_id})
        print(f"📊 Total kills in database: {kills_count}")
        
        if kills_count > 0:
            latest_kill = await db.kills.find_one(
                {"guild_id": guild_id},
                sort=[("timestamp", -1)]
            )
            if latest_kill:
                print(f"🕒 Latest kill timestamp: {latest_kill.get('timestamp')}")
        
        # Check player sessions
        sessions_count = await db.player_sessions.count_documents({"guild_id": guild_id})
        print(f"📊 Total player sessions: {sessions_count}")
        
        if sessions_count > 0:
            latest_session = await db.player_sessions.find_one(
                {"guild_id": guild_id},
                sort=[("last_seen", -1)]
            )
            if latest_session:
                print(f"🕒 Latest session update: {latest_session.get('last_seen')}")
        
    except Exception as e:
        print(f"❌ Error debugging parser: {e}")
    finally:
        client.close()

if __name__ == "__main__":
    asyncio.run(debug_parser_processing())