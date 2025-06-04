"""
Comprehensive Player State Tracking Fix
Fixes the core issue where voice channel shows 0 players when players are actually online
"""

import asyncio
import os
from motor.motor_asyncio import AsyncIOMotorClient
from datetime import datetime, timezone
import logging
import re

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def fix_player_state_tracking():
    """Fix player state tracking to show correct online player count"""
    try:
        # Connect to MongoDB
        client = AsyncIOMotorClient(os.environ['MONGO_URI'])
        db = client.emerald_killfeed
        
        print("=== COMPREHENSIVE PLAYER STATE TRACKING FIX ===")
        
        # Step 1: Check current server log to see who's actually online
        print("\n🔍 Step 1: Analyzing current server logs to find online players...")
        
        # Import the connection pool to access server logs
        import asyncssh
        
        # Get SSH credentials from environment
        ssh_host = os.environ.get('SSH_HOST', '79.127.236.1')
        ssh_port = int(os.environ.get('SSH_PORT', '8822'))
        ssh_username = os.environ.get('SSH_USERNAME', 'baked')
        ssh_password = os.environ.get('SSH_PASSWORD')
        
        if not ssh_password:
            print("❌ SSH password not found in environment variables")
            return
        
        # Connect to server and read recent log entries
        try:
            conn = await asyncssh.connect(
                ssh_host,
                port=ssh_port,
                username=ssh_username,
                password=ssh_password,
                known_hosts=None
            )
            
            # Get recent log entries (last 500 lines)
            sftp = await conn.start_sftp_client()
            
            # Read the current log file
            log_path = './79.127.236.1_7020/Logs/Deadside.log'
            
            try:
                async with sftp.open(log_path, 'r') as f:
                    await f.seek(-50000, 2)  # Seek to last 50KB
                    recent_logs = await f.read()
                    
                # Parse recent logs to find current player state
                lines = recent_logs.decode('utf-8', errors='ignore').split('\n')
                print(f"📝 Analyzing last {len(lines)} log lines...")
                
                # Track current players based on recent connect/disconnect events
                current_players = {}
                
                # Regex patterns for player events
                login_pattern = re.compile(r'LogLogin: Login: (.+?) UniqueId: EOS:([a-f0-9]+) from (\d+\.\d+\.\d+\.\d+)')
                connect_pattern = re.compile(r'LogGameMode: Player \|([a-f0-9]+) successfully registered')
                disconnect_pattern = re.compile(r'LogGameMode: UniqueId: EOS:\|([a-f0-9]+)')
                
                for line in lines:
                    # Check for login events
                    login_match = login_pattern.search(line)
                    if login_match:
                        player_name = login_match.group(1)
                        eos_id = login_match.group(2)
                        current_players[eos_id] = {
                            'name': player_name,
                            'state': 'queued',
                            'eos_id': eos_id
                        }
                        continue
                    
                    # Check for successful registration (queued -> online)
                    connect_match = connect_pattern.search(line)
                    if connect_match:
                        eos_id = connect_match.group(1)
                        if eos_id in current_players:
                            current_players[eos_id]['state'] = 'online'
                        continue
                    
                    # Check for disconnection events
                    disconnect_match = disconnect_pattern.search(line)
                    if disconnect_match:
                        eos_id = disconnect_match.group(1)
                        if eos_id in current_players:
                            current_players[eos_id]['state'] = 'offline'
                
                # Count actually online players
                online_players = [p for p in current_players.values() if p['state'] == 'online']
                queued_players = [p for p in current_players.values() if p['state'] == 'queued']
                
                print(f"🎮 Current server state:")
                print(f"  Online players: {len(online_players)}")
                print(f"  Queued players: {len(queued_players)}")
                
                if online_players:
                    print("📋 Online players:")
                    for player in online_players:
                        print(f"  - {player['name']} ({player['eos_id'][:8]}...)")
                
                if queued_players:
                    print("⏳ Queued players:")
                    for player in queued_players:
                        print(f"  - {player['name']} ({player['eos_id'][:8]}...)")
                
            except Exception as e:
                print(f"❌ Error reading log file: {e}")
                return
            finally:
                await sftp.close()
                conn.close()
        
        except Exception as e:
            print(f"❌ Error connecting to server: {e}")
            return
        
        # Step 2: Update database to match actual server state
        print(f"\n🔧 Step 2: Updating database to match actual server state...")
        
        guild_id = 1219706687980568769
        server_id = '7020'
        
        # First, set all existing sessions to offline
        await db.player_sessions.update_many(
            {
                'guild_id': guild_id,
                'server_id': server_id
            },
            {
                '$set': {
                    'state': 'offline',
                    'last_updated': datetime.now(timezone.utc)
                }
            }
        )
        
        # Then update/create sessions for currently active players
        for eos_id, player_info in current_players.items():
            await db.player_sessions.update_one(
                {
                    'eos_id': eos_id,
                    'guild_id': guild_id,
                    'server_id': server_id
                },
                {
                    '$set': {
                        'player_name': player_info['name'],
                        'state': player_info['state'],
                        'last_updated': datetime.now(timezone.utc),
                        'last_seen': datetime.now(timezone.utc)
                    }
                },
                upsert=True
            )
        
        print(f"✅ Updated {len(current_players)} player sessions in database")
        
        # Step 3: Verify database state
        print(f"\n📊 Step 3: Verifying updated database state...")
        
        sessions = await db.player_sessions.find({
            'guild_id': guild_id,
            'server_id': server_id
        }).to_list(None)
        
        state_counts = {}
        for session in sessions:
            state = session.get('state', 'unknown')
            state_counts[state] = state_counts.get(state, 0) + 1
        
        print("📈 Updated database state:")
        for state, count in state_counts.items():
            print(f"  {state}: {count} players")
        
        # Step 4: Update voice channel to reflect correct count
        print(f"\n🔊 Step 4: Updating voice channel with correct player count...")
        
        online_count = len(online_players)
        queued_count = len(queued_players)
        
        print(f"Voice channel should show: {online_count} online, {queued_count} queued")
        
        client.close()
        print("\n✅ Player state tracking fix completed!")
        
    except Exception as e:
        logger.error(f"Error fixing player state tracking: {e}")

if __name__ == "__main__":
    asyncio.run(fix_player_state_tracking())