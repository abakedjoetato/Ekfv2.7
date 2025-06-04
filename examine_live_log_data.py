#!/usr/bin/env python3
"""
Examine Live Log Data - Extract actual player connection patterns for accurate cold start implementation
"""

import asyncio
import asyncssh
import logging
import re
from datetime import datetime

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def examine_live_log_data():
    """Examine live log data to understand player connection patterns"""
    try:
        # Connect to server
        conn = await asyncssh.connect(
            '79.127.236.1',
            port=8822,
            username='baked',
            password='baked2024!',
            known_hosts=None,
            kex_algs=['diffie-hellman-group1-sha1', 'diffie-hellman-group14-sha1', 'diffie-hellman-group14-sha256', 'diffie-hellman-group16-sha512', 'ecdh-sha2-nistp256', 'ecdh-sha2-nistp384', 'ecdh-sha2-nistp521'],
            encryption_algs=['aes128-ctr', 'aes192-ctr', 'aes256-ctr', 'aes128-cbc', 'aes192-cbc', 'aes256-cbc'],
            mac_algs=['hmac-sha1', 'hmac-sha2-256', 'hmac-sha2-512'],
            compression_algs=['none'],
            server_host_key_algs=['ssh-rsa', 'rsa-sha2-256', 'rsa-sha2-512', 'ssh-dss']
        )
        
        sftp = await conn.start_sftp_client()
        log_path = "./79.127.236.1_emerald_eu/Logs/Deadside.log"
        
        logger.info("📊 Reading last 1000 lines of live log data...")
        
        async with sftp.open(log_path, 'rb') as file:
            # Get file size and read last portion
            file_stat = await sftp.stat(log_path)
            file_size = file_stat.size
            
            # Read last 100KB to get recent entries
            read_size = min(100000, file_size)
            await file.seek(file_size - read_size)
            content = await file.read()
            
            lines = content.decode('utf-8', errors='ignore').splitlines()
            logger.info(f"📋 Examining {len(lines)} recent lines")
            
            # Pattern matching for player connections
            connection_patterns = {
                'player_connected': re.compile(r'Player\s+(.+?)\s+Connected'),
                'player_disconnected': re.compile(r'Player\s+(.+?)\s+Disconnected'),
                'player_login': re.compile(r'Login:\s+(.+?)(?:\s|$)'),
                'player_logout': re.compile(r'Logout:\s+(.+?)(?:\s|$)'),
                'user_connected': re.compile(r'User\s+(.+?)\s+connected'),
                'user_disconnected': re.compile(r'User\s+(.+?)\s+disconnected'),
                'session_start': re.compile(r'Session.*?started.*?(\w+)'),
                'session_end': re.compile(r'Session.*?ended.*?(\w+)')
            }
            
            player_events = []
            current_players = set()
            
            for i, line in enumerate(lines[-500:]):  # Check last 500 lines
                timestamp_match = re.match(r'\[(\d{4}\.\d{2}\.\d{2}-\d{2}\.\d{2}\.\d{2}:\d{3})\]', line)
                if not timestamp_match:
                    continue
                    
                timestamp = timestamp_match.group(1)
                
                for pattern_name, pattern in connection_patterns.items():
                    match = pattern.search(line)
                    if match:
                        player_name = match.group(1).strip()
                        event_type = 'connect' if 'connect' in pattern_name or 'login' in pattern_name or 'start' in pattern_name else 'disconnect'
                        
                        player_events.append({
                            'timestamp': timestamp,
                            'player': player_name,
                            'event': event_type,
                            'pattern': pattern_name,
                            'line': line.strip()
                        })
                        
                        if event_type == 'connect':
                            current_players.add(player_name)
                        else:
                            current_players.discard(player_name)
                        
                        logger.info(f"🎮 {event_type.upper()}: {player_name} ({pattern_name})")
                        break
            
            logger.info(f"📊 Found {len(player_events)} player events")
            logger.info(f"👥 Current active players: {len(current_players)}")
            
            if current_players:
                logger.info("🟢 Active players:")
                for player in sorted(current_players):
                    logger.info(f"   - {player}")
            else:
                logger.info("🔴 No active players detected")
                
            # Show recent events
            logger.info("📋 Recent player events:")
            for event in player_events[-10:]:
                logger.info(f"   {event['timestamp']} - {event['event'].upper()}: {event['player']}")
        
        await conn.close()
        
    except Exception as e:
        logger.error(f"❌ Failed to examine live log data: {e}")

if __name__ == "__main__":
    asyncio.run(examine_live_log_data())