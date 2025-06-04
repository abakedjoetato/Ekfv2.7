"""
Direct Voice Channel Count Fix
Analyzes actual server logs to determine current online players and updates voice channel accordingly
"""

import asyncio
import os
from motor.motor_asyncio import AsyncIOMotorClient
from datetime import datetime, timezone
import logging
import re
import asyncssh

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def analyze_current_players():
    """Analyze server logs to find currently online players"""
    try:
        # SSH connection to server
        conn = await asyncssh.connect(
            os.environ['SSH_HOST'],
            port=int(os.environ['SSH_PORT']),
            username=os.environ['SSH_USERNAME'], 
            password=os.environ['SSH_PASSWORD'],
            known_hosts=None
        )
        
        sftp = await conn.start_sftp_client()
        log_path = './79.127.236.1_7020/Logs/Deadside.log'
        
        # Read last 100KB of log file
        async with sftp.open(log_path, 'r') as f:
            await f.seek(-100000, 2)
            recent_logs = await f.read()
        
        await sftp.close()
        conn.close()
        
        # Parse logs to track player states
        lines = recent_logs.decode('utf-8', errors='ignore').split('\n')
        
        # Track player states based on chronological events
        player_states = {}
        
        # Regex patterns
        login_pattern = re.compile(r'LogLogin: Login: (.+?) UniqueId: EOS:([a-f0-9]+)')
        connect_pattern = re.compile(r'LogGameMode: Player \|([a-f0-9]+) successfully registered')
        disconnect_pattern = re.compile(r'LogGameMode: UniqueId: EOS:\|([a-f0-9]+)')
        
        print(f"Analyzing {len(lines)} log lines...")
        
        for line in lines:
            if not line.strip():
                continue
                
            # Player login (queued state)
            login_match = login_pattern.search(line)
            if login_match:
                player_name = login_match.group(1)
                eos_id = login_match.group(2)
                player_states[eos_id] = {
                    'name': player_name,
                    'state': 'queued',
                    'eos_id': eos_id
                }
                continue
            
            # Player connected (online state)
            connect_match = connect_pattern.search(line)
            if connect_match:
                eos_id = connect_match.group(1)
                if eos_id in player_states:
                    player_states[eos_id]['state'] = 'online'
                continue
            
            # Player disconnected
            disconnect_match = disconnect_pattern.search(line)
            if disconnect_match:
                eos_id = disconnect_match.group(1)
                if eos_id in player_states:
                    player_states[eos_id]['state'] = 'offline'
        
        # Count current states
        online_count = sum(1 for p in player_states.values() if p['state'] == 'online')
        queued_count = sum(1 for p in player_states.values() if p['state'] == 'queued')
        
        print(f"Current server state:")
        print(f"  Online: {online_count} players")
        print(f"  Queued: {queued_count} players")
        
        # Show online players
        online_players = [p for p in player_states.values() if p['state'] == 'online']
        if online_players:
            print("Online players:")
            for player in online_players:
                print(f"  - {player['name']}")
        
        return online_count, queued_count, player_states
        
    except Exception as e:
        print(f"Error analyzing players: {e}")
        return 0, 0, {}

async def update_database_and_voice_channel():
    """Update database with correct player states and fix voice channel"""
    try:
        online_count, queued_count, player_states = await analyze_current_players()
        
        # Connect to database
        client = AsyncIOMotorClient(os.environ['MONGO_URI'])
        db = client.emerald_killfeed
        
        guild_id = 1219706687980568769
        server_id = '7020'
        
        # Clear all existing sessions
        await db.player_sessions.delete_many({
            'guild_id': guild_id,
            'server_id': server_id
        })
        
        # Insert current player states
        if player_states:
            session_docs = []
            for eos_id, player_data in player_states.items():
                if player_data['state'] != 'offline':  # Only store active players
                    session_docs.append({
                        'eos_id': eos_id,
                        'player_name': player_data['name'],
                        'state': player_data['state'],
                        'guild_id': guild_id,
                        'server_id': server_id,
                        'last_updated': datetime.now(timezone.utc),
                        'last_seen': datetime.now(timezone.utc)
                    })
            
            if session_docs:
                await db.player_sessions.insert_many(session_docs)
                print(f"Inserted {len(session_docs)} active player sessions")
        
        # Verify database state
        sessions = await db.player_sessions.find({
            'guild_id': guild_id,
            'server_id': server_id
        }).to_list(None)
        
        db_online = sum(1 for s in sessions if s.get('state') == 'online')
        db_queued = sum(1 for s in sessions if s.get('state') == 'queued')
        
        print(f"Database verification:")
        print(f"  Online in DB: {db_online}")
        print(f"  Queued in DB: {db_queued}")
        
        client.close()
        
        print(f"Voice channel should now show: {online_count} online, {queued_count} queued")
        return True
        
    except Exception as e:
        print(f"Error updating database: {e}")
        return False

if __name__ == "__main__":
    asyncio.run(update_database_and_voice_channel())