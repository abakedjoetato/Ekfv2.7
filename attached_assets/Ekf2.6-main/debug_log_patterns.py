"""
Debug script to examine actual log content and understand why events aren't being detected
"""
import asyncio
import asyncssh
import re
from datetime import datetime, timezone

async def debug_log_patterns():
    """Debug the actual log content to see what patterns we're missing"""
    try:
        # Connect to server and get recent log content
        conn = await asyncssh.connect(
            '79.127.236.1',
            port=8822,
            username='baked',
            password='YeeHAW!123',
            known_hosts=None
        )
        
        sftp = await conn.start_sftp_client()
        log_path = "./79.127.236.1_emerald_eu/Logs/Deadside.log"
        
        async with sftp.open(log_path, 'rb') as file:
            # Get last 50KB of log
            await file.seek(-50000, 2)  # Seek from end
            content = await file.read()
            lines = content.decode('utf-8', errors='ignore').splitlines()[-200:]  # Last 200 lines
            
            print(f"Examining last {len(lines)} log lines for pattern analysis...")
            
            # Analyze each line
            player_patterns = []
            mission_patterns = []
            event_patterns = []
            other_patterns = []
            
            for i, line in enumerate(lines):
                line = line.strip()
                if not line or not line.startswith('['):
                    continue
                
                line_lower = line.lower()
                
                # Look for player-related patterns
                if any(keyword in line_lower for keyword in ['join', 'player', 'register', 'connect', 'disconnect', 'eosid']):
                    player_patterns.append(f"Line {i}: {line}")
                
                # Look for mission patterns
                elif any(keyword in line_lower for keyword in ['mission', 'ga_']):
                    mission_patterns.append(f"Line {i}: {line}")
                
                # Look for event patterns
                elif any(keyword in line_lower for keyword in ['airdrop', 'helicrash', 'trader', 'event']):
                    event_patterns.append(f"Line {i}: {line}")
                
                # Other interesting patterns
                elif any(keyword in line_lower for keyword in ['vehicle', 'spawn', 'del']):
                    other_patterns.append(f"Line {i}: {line}")
            
            print(f"\n=== PLAYER PATTERNS ({len(player_patterns)}) ===")
            for pattern in player_patterns[-10:]:  # Last 10
                print(pattern)
            
            print(f"\n=== MISSION PATTERNS ({len(mission_patterns)}) ===")
            for pattern in mission_patterns[-10:]:  # Last 10
                print(pattern)
            
            print(f"\n=== EVENT PATTERNS ({len(event_patterns)}) ===")
            for pattern in event_patterns:
                print(pattern)
            
            print(f"\n=== OTHER PATTERNS ({len(other_patterns)}) ===")
            for pattern in other_patterns[-10:]:  # Last 10
                print(pattern)
            
            # Test our existing regex patterns
            print(f"\n=== TESTING EXISTING PATTERNS ===")
            
            queue_pattern = r'LogNet: Join request: /Game/Maps/world_\d+/World_\d+\?.*?eosid=\|([a-f0-9]+).*?Name=([^&\?\s]+).*?(?:platformid=([^&\?\s]+))?'
            register_pattern = r'LogOnline: Warning: Player \|([a-f0-9]+) successfully registered!'
            disconnect_pattern = r'LogNet: UChannel::Close: Sending CloseBunch.*?UniqueId: EOS:\|([a-f0-9]+)'
            airdrop_pattern = r'Event_AirDrop.*spawned.*location.*X=([\d\.-]+).*Y=([\d\.-]+)'
            helicrash_pattern = r'Helicrash.*spawned.*location.*X=([\d\.-]+).*Y=([\d\.-]+)'
            
            for line in lines:
                if re.search(queue_pattern, line, re.IGNORECASE):
                    print(f"QUEUE MATCH: {line}")
                if re.search(register_pattern, line, re.IGNORECASE):
                    print(f"REGISTER MATCH: {line}")
                if re.search(disconnect_pattern, line, re.IGNORECASE):
                    print(f"DISCONNECT MATCH: {line}")
                if re.search(airdrop_pattern, line, re.IGNORECASE):
                    print(f"AIRDROP MATCH: {line}")
                if re.search(helicrash_pattern, line, re.IGNORECASE):
                    print(f"HELICRASH MATCH: {line}")
        
        await conn.close()
        
    except Exception as e:
        print(f"Error debugging log patterns: {e}")

if __name__ == "__main__":
    asyncio.run(debug_log_patterns())