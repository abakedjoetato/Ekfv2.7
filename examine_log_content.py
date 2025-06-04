"""
Examine actual log content to debug pattern matching issues
"""
import asyncio
import sys
import os
sys.path.append('.')

from bot.utils.connection_pool import connection_manager
import re

async def examine_log_content():
    """Examine actual log content to understand pattern matching issues"""
    
    # Server config for Emerald EU
    server_config = {
        'host': '79.127.236.1',
        'port': 8822,
        'username': 'baked',
        'password': 'YeeHAW!123',
        'server_id': 'emerald_eu'
    }
    
    guild_id = "1315008007830650941"
    
    try:
        async with connection_manager.get_connection(guild_id, server_config) as conn:
            if not conn:
                print("Failed to get connection")
                return
                
            sftp = await conn.start_sftp_client()
            log_path = f"./{server_config['host']}_{server_config['server_id']}/Logs/Deadside.log"
            
            print(f"Reading from: {log_path}")
            
            async with sftp.open(log_path, 'rb') as file:
                # Get last 100KB for analysis
                file_size = await file.stat()
                seek_pos = max(0, file_size.size - 100000)
                await file.seek(seek_pos)
                content = await file.read()
                lines = content.decode('utf-8', errors='ignore').splitlines()
                
                print(f"Analyzing {len(lines)} lines from position {seek_pos}")
                
                # Test patterns
                queue_pattern = r'LogNet: Join request: /Game/Maps/world_\d+/World_\d+\?.*?eosid=\|([a-f0-9]+).*?Name=([^&\?\s]+)'
                register_pattern = r'LogOnline: Warning: Player \|([a-f0-9]+) successfully registered!'
                disconnect_pattern = r'LogNet: UChannel::Close: Sending CloseBunch.*?UniqueId: EOS:\|([a-f0-9]+)'
                mission_respawn_pattern = r'LogSFPS: Mission (GA_[A-Za-z0-9_]+) will respawn in (\d+)'
                mission_state_pattern = r'LogSFPS: Mission (GA_[A-Za-z0-9_]+) switched to ([A-Z_]+)'
                
                # Count different event types
                events_found = {
                    'queue': 0,
                    'register': 0, 
                    'disconnect': 0,
                    'mission_respawn': 0,
                    'mission_state': 0,
                    'airdrop': 0,
                    'helicrash': 0,
                    'trader': 0,
                    'vehicle': 0
                }
                
                recent_lines = []
                
                for i, line in enumerate(lines[-50:], len(lines)-50):  # Last 50 lines with line numbers
                    line = line.strip()
                    if not line:
                        continue
                        
                    recent_lines.append(f"Line {i}: {line}")
                    
                    # Test each pattern
                    if re.search(queue_pattern, line, re.IGNORECASE):
                        events_found['queue'] += 1
                        print(f"QUEUE EVENT: {line}")
                    
                    if re.search(register_pattern, line, re.IGNORECASE):
                        events_found['register'] += 1
                        print(f"REGISTER EVENT: {line}")
                    
                    if re.search(disconnect_pattern, line, re.IGNORECASE):
                        events_found['disconnect'] += 1
                        print(f"DISCONNECT EVENT: {line}")
                    
                    if re.search(mission_respawn_pattern, line, re.IGNORECASE):
                        events_found['mission_respawn'] += 1
                        print(f"MISSION RESPAWN: {line}")
                    
                    if re.search(mission_state_pattern, line, re.IGNORECASE):
                        events_found['mission_state'] += 1
                        print(f"MISSION STATE: {line}")
                    
                    # Look for other event keywords
                    line_lower = line.lower()
                    if 'airdrop' in line_lower:
                        events_found['airdrop'] += 1
                        print(f"AIRDROP KEYWORD: {line}")
                    
                    if 'helicrash' in line_lower:
                        events_found['helicrash'] += 1
                        print(f"HELICRASH KEYWORD: {line}")
                    
                    if 'trader' in line_lower:
                        events_found['trader'] += 1
                        print(f"TRADER KEYWORD: {line}")
                    
                    if 'vehicle' in line_lower and ('spawn' in line_lower or 'del' in line_lower):
                        events_found['vehicle'] += 1
                        print(f"VEHICLE EVENT: {line}")
                
                print(f"\n=== EVENT SUMMARY ===")
                for event_type, count in events_found.items():
                    print(f"{event_type}: {count}")
                
                print(f"\n=== RECENT LOG LINES (Last 20) ===")
                for line in recent_lines[-20:]:
                    print(line)
    
    except Exception as e:
        print(f"Error examining log content: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(examine_log_content())