"""
Emerald's Killfeed - Killfeed Parser (PHASE 2)
Parses CSV files for kill events and generates embeds
"""

import asyncio
import asyncssh
import csv
import logging
import os
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional, Tuple
from bot.utils.embed_factory import EmbedFactory

logger = logging.getLogger(__name__)

class KillfeedParser:
    """
    KILLFEED PARSER (FREE)
    - Runs every 300 seconds
    - SFTP path: ./{host}_{serverID}/actual1/deathlogs/*/*.csv
    - Loads most recent file only
    - Tracks and skips previously parsed lines
    - Suicides normalized (killer == victim, Suicide_by_relocation → Menu Suicide)
    - Emits killfeed embeds with distance, weapon, styled headers
    """

    def __init__(self, bot):
        self.bot = bot
        self.sftp_connections = {}
        self.connection_locks = {}
        self.last_processed_lines = {}
        self.last_csv_files = {}

    def parse_csv_line(self, line: str) -> Dict[str, Any]:
        """Parse a single CSV line into kill event data"""
        try:
            parts = line.strip().split(';')
            if len(parts) < 7:
                return {}
            timestamp_str = parts[0].strip()
            killer = parts[1].strip()
            killer_id = parts[2].strip()
            victim = parts[3].strip()
            victim_id = parts[4].strip()
            weapon = parts[5].strip()
            distance = parts[6].strip() if len(parts) > 6 else '0'

            killer = killer.strip()
            victim = victim.strip()

            # Parse timestamp - handle multiple formats
            try:
                timestamp = datetime.strptime(timestamp_str, '%Y.%m.%d-%H.%M.%S')
                timestamp = timestamp.replace(tzinfo=timezone.utc)
            except ValueError:
                try:
                    timestamp = datetime.strptime(timestamp_str, '%Y-%m-%d %H:%M:%S')
                    timestamp = timestamp.replace(tzinfo=timezone.utc)
                except ValueError:
                    timestamp = datetime.utcnow().replace(tzinfo=timezone.utc)

            # Normalize suicide events
            is_suicide = killer == victim or weapon.lower() == 'suicide_by_relocation'
            if is_suicide:
                if weapon.lower() == 'suicide_by_relocation':
                    weapon = 'Menu Suicide'
                elif weapon.lower() == 'falling':
                    weapon = 'Falling'
                    is_suicide = True
                else:
                    weapon = 'Suicide'

            # Parse distance
            try:
                if distance and distance != '':
                    distance_float = float(distance)
                else:
                    distance_float = 0.0
            except ValueError:
                distance_float = 0.0

            return {
                'timestamp': timestamp,
                'killer': killer,
                'victim': victim,
                'weapon': weapon,
                'distance': distance_float,
                'is_suicide': is_suicide
            }

        except Exception as e:
            logger.error(f"Error parsing CSV line: {e}")
            return {}
    def normalize_suicide_event(self, killer, victim, weapon):
        """Normalize suicide events"""
        is_suicide = killer == victim or weapon.lower() == 'suicide_by_relocation'
        if is_suicide:
            if weapon.lower() == 'suicide_by_relocation':
                weapon = 'Menu Suicide'
            elif weapon.lower() == 'falling':
                weapon = 'Falling'
            else:
                weapon = 'Suicide'
        return weapon, is_suicide

    async def get_sftp_connection(self, server_config: Dict[str, Any]) -> Optional[asyncssh.SSHClientConnection]:
        """Get or create SFTP connection with enhanced DH parameter compatibility"""
        server_key = f"{server_config['host']}:{server_config['port']}"
        
        # Check existing connection
        if server_key in self.sftp_connections:
            conn = self.sftp_connections[server_key]
            if conn and not conn.is_closed():
                return conn
            else:
                del self.sftp_connections[server_key]

        # Multiple connection strategies for maximum compatibility
        connection_strategies = [
            {
                'name': 'Standard DH Groups',
                'kex_algs': [
                    'diffie-hellman-group14-sha256',
                    'diffie-hellman-group16-sha512',
                    'diffie-hellman-group-exchange-sha256'
                ]
            },
            {
                'name': 'Legacy DH Groups',
                'kex_algs': [
                    'diffie-hellman-group14-sha1',
                    'diffie-hellman-group1-sha1',
                    'diffie-hellman-group-exchange-sha1'
                ]
            },
            {
                'name': 'All Available DH Groups',
                'kex_algs': [
                    'diffie-hellman-group18-sha512',
                    'diffie-hellman-group16-sha512', 
                    'diffie-hellman-group14-sha256',
                    'diffie-hellman-group14-sha1',
                    'diffie-hellman-group-exchange-sha256',
                    'diffie-hellman-group-exchange-sha1',
                    'diffie-hellman-group1-sha1'
                ]
            }
        ]

        for strategy in connection_strategies:
            logger.debug(f"Trying connection strategy: {strategy['name']}")
            
            try:
                options = {
                    'username': server_config['username'],
                    'password': server_config['password'],
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
                    ]
                }
                
                conn = await asyncio.wait_for(
                    asyncssh.connect(server_config['host'], port=server_config['port'], **options),
                    timeout=30
                )

                logger.info(f"✅ SFTP connected using {strategy['name']} to {server_config['host']}")
                self.sftp_connections[server_key] = conn
                return conn

            except asyncio.TimeoutError:
                logger.warning(f"⏱️ Connection timeout with {strategy['name']}")
                continue
            except asyncssh.DisconnectError as e:
                if 'Invalid DH parameters' in str(e):
                    logger.warning(f"🔒 DH parameters rejected for {strategy['name']}")
                    continue
                else:
                    logger.warning(f"🔌 Server disconnected: {e}")
                    continue
            except Exception as e:
                if 'Invalid DH parameters' in str(e):
                    logger.warning(f"🔒 DH validation failed for {strategy['name']}")
                    continue
                elif 'auth' in str(e).lower():
                    logger.error(f"🚫 Authentication failed with provided credentials")
                    return None
                else:
                    logger.warning(f"⚠️ Connection error with {strategy['name']}: {e}")
                    continue

        logger.error(f"❌ All connection strategies failed for {server_config['host']}")
        return None
    async def get_newest_csv_file(self, server_config: Dict[str, Any]) -> Optional[str]:
        """Get the newest CSV file from SFTP server"""
        try:
            conn = await self.get_sftp_connection(server_config)
            if not conn:
                return None

            async with conn.start_sftp_client() as sftp:
                base_path = f"./{server_config['host']}_{server_config['server_id']}/actual1/deathlogs"
                
                try:
                    dirs = await sftp.listdir(base_path)
                    newest_file = None
                    newest_time = None
                    
                    for dir_name in dirs:
                        dir_path = f"{base_path}/{dir_name}"
                        try:
                            files = await sftp.listdir(dir_path)
                            for file_name in files:
                                if file_name.endswith('.csv'):
                                    file_path = f"{dir_path}/{file_name}"
                                    
                                    # Extract timestamp from filename (YYYY.MM.DD-HH.MM.SS format)
                                    try:
                                        timestamp_str = file_name.replace('.csv', '')
                                        file_time = datetime.strptime(timestamp_str, '%Y.%m.%d-%H.%M.%S')
                                        
                                        if newest_time is None or file_time > newest_time:
                                            newest_time = file_time
                                            newest_file = file_path
                                    except ValueError:
                                        continue
                        except Exception:
                            continue
                    
                    return newest_file
                    
                except Exception:
                    return None

        except Exception as e:
            logger.error(f"Error getting newest CSV file: {e}")
            return None

    async def process_kill_event(self, guild_id: int, server_id: str, kill_data: Dict[str, Any]):
        """Process a kill event and update database"""
        try:
            # Update database with kill event
            await self.bot.db_manager.add_kill_event(guild_id, server_id, kill_data)

        except Exception as e:
            logger.error(f"Error processing kill event: {e}")

    async def send_killfeed_embed(self, guild_id: int, server_id: str, kill_data: Dict[str, Any]):
        """Send killfeed embed to designated channel"""
        try:
            # Use channel router for proper channel lookup
            channel = await self.bot.channel_router.get_channel(guild_id, server_id, 'killfeed')
            if not channel:
                logger.warning(f"No killfeed channel configured for guild {guild_id}, server {server_id}")
                return

            # Create killfeed embed
            embed, file = await EmbedFactory.build_killfeed_embed(kill_data)
            
            await channel.send(embed=embed, file=file)
            logger.info(f"✅ Sent killfeed embed to {channel.name} (ID: {channel.id})")

        except Exception as e:
            logger.error(f"Error sending killfeed embed: {e}")

    async def _process_final_lines(self, server_config: Dict[str, Any], file_path: str, server_key: str, guild_id: int):
        """Process remaining lines from old file before switching to new one"""
        try:
            conn = await self.get_sftp_connection(server_config)
            if not conn:
                return

            async with conn.start_sftp_client() as sftp:
                async with sftp.open(file_path, 'r') as f:
                    content = await f.read()
                    lines = content.strip().split('\n')
                    
                    last_line_count = self.last_processed_lines.get(server_key, 0)
                    remaining_lines = lines[last_line_count:]
                    
                    if remaining_lines:
                        logger.info(f"📋 Processing {len(remaining_lines)} final lines from old file")
                        for line in remaining_lines:
                            if line.strip():
                                kill_data = self.parse_csv_line(line)
                                if kill_data:
                                    await self.process_kill_event(guild_id, server_config['server_id'], kill_data)
        except Exception as e:
            logger.error(f"Error processing final lines: {e}")

    async def parse_server_killfeed(self, guild_id: int, server_config: Dict[str, Any]):
        """Parse killfeed for a single server"""
        try:
            server_id = server_config['server_id']
            newest_file = await self.get_newest_csv_file(server_config)
            
            if not newest_file:
                logger.info(f"⚠️ No CSV files found for server {server_id}")
                return
            
            logger.info(f"📁 Processing newest CSV file: {newest_file}")

            server_key = f"{guild_id}:{server_id}"
            
            # Check if we switched to a new file
            last_file = self.last_csv_files.get(server_key)
            file_changed = last_file != newest_file
            
            if file_changed and last_file:
                logger.info(f"📂 File changed from {last_file} to {newest_file}")
                # Process remaining lines from old file before switching
                await self._process_final_lines(server_config, last_file, server_key, guild_id)
                # Reset line count for new file
                self.last_processed_lines[server_key] = 0
            
            # Update current file tracking
            self.last_csv_files[server_key] = newest_file
            
            # Get last processed line count for current file
            last_line_count = self.last_processed_lines.get(server_key, 0)
            
            # Read and parse CSV file
            conn = await self.get_sftp_connection(server_config)
            if not conn:
                return

            async with conn.start_sftp_client() as sftp:
                try:
                    async with sftp.open(newest_file, 'r') as f:
                        content = await f.read()
                        lines = content.strip().split('\n')
                        
                        # Process only new lines (start from line after last processed)
                        new_lines = lines[last_line_count:]
                        logger.info(f"📊 Processing {len(new_lines)} new lines (total: {len(lines)}, last processed: {last_line_count})")
                        
                        kill_count = 0
                        for line in new_lines:
                            if line.strip():
                                kill_data = self.parse_csv_line(line)
                                if kill_data:
                                    kill_count += 1
                                    await self.process_kill_event(guild_id, server_id, kill_data)
                                    await self.send_killfeed_embed(guild_id, server_id, kill_data)
                        
                        logger.info(f"🎯 Processed {kill_count} kill events from {newest_file}")
                        
                        # Update last processed line count
                        self.last_processed_lines[server_key] = len(lines)
                        
                except Exception as e:
                    logger.error(f"Error reading CSV file {newest_file}: {e}")

        except Exception as e:
            logger.error(f"Error parsing server killfeed: {e}")

    async def run_killfeed_parser(self):
        """Run killfeed parser for all configured servers"""
        try:
            # Get all servers with killfeed enabled
            servers = await self.bot.db_manager.get_all_servers_with_killfeed()
            logger.info(f"🔍 Killfeed parser: Found {len(servers)} servers with killfeed enabled")
            
            for server in servers:
                try:
                    server_name = server.get('name', 'Unknown')
                    logger.info(f"🔍 Processing killfeed for {server_name}")
                    await self.parse_server_killfeed(server['guild_id'], server)
                except Exception as e:
                    logger.error(f"Error parsing killfeed for server {server.get('server_id')}: {e}")

        except Exception as e:
            logger.error(f"Error in killfeed parser: {e}")

    def schedule_killfeed_parser(self):
        """Schedule killfeed parser to run every 300 seconds"""
        try:
            if hasattr(self.bot, 'scheduler'):
                self.bot.scheduler.add_job(
                    self.run_killfeed_parser,
                    'interval',
                    seconds=300,
                    id='killfeed_parser',
                    replace_existing=True
                )
                logger.info("Killfeed parser scheduled")
        except Exception as e:
            logger.error(f"Error scheduling killfeed parser: {e}")

    async def cleanup_sftp_connections(self):
        """Clean up idle SFTP connections"""
        try:
            for server_key, conn in list(self.sftp_connections.items()):
                try:
                    if conn and hasattr(conn, 'is_closed') and conn.is_closed():
                        del self.sftp_connections[server_key]
                    elif conn and hasattr(conn, '_transport') and conn._transport:
                        if hasattr(conn._transport, '_transport') and not conn._transport._transport:
                            del self.sftp_connections[server_key]
                except Exception:
                    del self.sftp_connections[server_key]
        except Exception as e:
            logger.error(f"Error cleaning up SFTP connections: {e}")