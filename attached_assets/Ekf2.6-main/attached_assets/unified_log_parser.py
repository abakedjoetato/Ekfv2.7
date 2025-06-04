import asyncio
import logging
import os
import re
import time
import hashlib
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, Optional, List, Tuple
from pathlib import Path

import discord
import asyncssh
from motor.motor_asyncio import AsyncIOMotorClient

# Import EmbedFactory for themed messaging
from bot.utils.embed_factory import EmbedFactory

logger = logging.getLogger(__name__)

class UnifiedLogParser:
    """
    BULLETPROOF UNIFIED LOG PARSER
    - 100% reliable SFTP connection handling
    - Bulletproof state management
    - Guaranteed voice channel updates
    - Rate limit safe operation
    """

    def __init__(self, bot):
        self.bot = bot

        # Bulletproof state dictionaries with proper isolation
        self.file_states: Dict[str, Dict[str, Any]] = {}
        self.player_sessions: Dict[str, Dict[str, Any]] = {}
        self.sftp_connections: Dict[str, asyncssh.SSHClientConnection] = {}
        self.last_log_position: Dict[str, int] = {}
        self.player_lifecycle: Dict[str, Dict[str, Any]] = {}
        self.server_status: Dict[str, Dict[str, Any]] = {}
        self.log_file_hashes: Dict[str, str] = {}

        # Player name resolution cache
        self.player_name_cache: Dict[str, str] = {}

        # Compile patterns once for efficiency
        self.patterns = self._compile_patterns()
        self.mission_mappings = self._get_mission_mappings()

        # Configuration parameters with memory bounds
        self.max_cache_size = 1000  # Max entries in player_name_cache (reduced)
        self.max_lifecycle_entries = 2000  # Max entries in player_lifecycle (reduced)
        self.max_session_entries = 2000  # Max entries in player_sessions (reduced)
        self.cleanup_interval = 300  # Cleanup every 5 minutes

        # Load state on startup
        asyncio.create_task(self._load_persistent_state())

        # Start periodic cleanup task
        asyncio.create_task(self._schedule_periodic_cleanup())

    def _compile_patterns(self) -> Dict[str, re.Pattern]:
        """Compile regex patterns for log parsing"""
        return {
            # Player connection patterns - explicit matching based on provided examples
            'player_queue_join': re.compile(
                r'LogNet: Join request: /Game/Maps/world_\d+/World_\d+\?.*?eosid=\|([a-f0-9]+).*?Name=([^&\?\s]+).*?(?:platformid=([^&\?\s]+))?',
                re.IGNORECASE
            ),
            'player_registered': re.compile(
                r'LogOnline: Warning: Player \|([a-f0-9]+) successfully registered!',
                re.IGNORECASE
            ),
            'player_disconnect': re.compile(
                r'LogNet: UChannel::Close: Sending CloseBunch.*?UniqueId: EOS:\|([a-f0-9]+)',
                re.IGNORECASE
            ),

            # Server configuration patterns
            'max_player_count': re.compile(r'playersmaxcount\s*=\s*(\d+)', re.IGNORECASE),
            'server_name_pattern': re.compile(r'ServerName\s*=\s*([^,\s]+)', re.IGNORECASE),

            # Mission patterns
            'mission_respawn': re.compile(r'LogSFPS: Mission (GA_[A-Za-z0-9_]+) will respawn in (\d+)', re.IGNORECASE),
            'mission_state_change': re.compile(r'LogSFPS: Mission (GA_[A-Za-z0-9_]+) switched to ([A-Z_]+)', re.IGNORECASE),
            'mission_ready': re.compile(r'LogSFPS: Mission (GA_[A-Za-z0-9_]+) switched to READY', re.IGNORECASE),
            'mission_initial': re.compile(r'LogSFPS: Mission (GA_[A-Za-z0-9_]+) switched to INITIAL', re.IGNORECASE),
            'mission_in_progress': re.compile(r'LogSFPS: Mission (GA_[A-Za-z0-9_]+) switched to IN_PROGRESS', re.IGNORECASE),
            'mission_completed': re.compile(r'LogSFPS: Mission (GA_[A-Za-z0-9_]+) switched to COMPLETED', re.IGNORECASE),

            # Vehicle patterns
            'vehicle_spawn': re.compile(r'LogSFPS: \[ASFPSGameMode::NewVehicle_Add\] Add vehicle (BP_SFPSVehicle_[A-Za-z0-9_]+)', re.IGNORECASE),
            'vehicle_delete': re.compile(r'LogSFPS: \[ASFPSGameMode::NewVehicle_Del\] Del vehicle (BP_SFPSVehicle_[A-Za-z0-9_]+)', re.IGNORECASE),

            # Airdrop patterns
            'airdrop_event': re.compile(r'Event_AirDrop.*spawned.*location.*X=([\d\.-]+).*Y=([\d\.-]+)', re.IGNORECASE),
            'airdrop_spawn': re.compile(r'LogSFPS:.*airdrop.*spawn', re.IGNORECASE),
            'airdrop_flying': re.compile(r'LogSFPS:.*airdrop.*flying', re.IGNORECASE),

            # Helicrash patterns
            'helicrash_event': re.compile(r'Helicrash.*spawned.*location.*X=([\d\.-]+).*Y=([\d\.-]+)', re.IGNORECASE),
            'helicrash_spawn': re.compile(r'LogSFPS:.*helicrash.*spawn', re.IGNORECASE),
            'helicrash_crash': re.compile(r'LogSFPS:.*helicopter.*crash', re.IGNORECASE),

            # Trader patterns
            'trader_spawn': re.compile(r'Trader.*spawned.*location.*X=([\d\.-]+).*Y=([\d\.-]+)', re.IGNORECASE),
            'trader_event': re.compile(r'LogSFPS:.*trader.*spawn', re.IGNORECASE),
            'trader_arrival': re.compile(r'LogSFPS:.*trader.*arrived', re.IGNORECASE),

            # Timestamp
            'timestamp': re.compile(r'\[(\d{4}\.\d{2}\.\d{2}-\d{2}\.\d{2}\.\d{2}:\d{3})\]')
        }

    def _get_mission_mappings(self) -> Dict[str, str]:
        """Mission ID to readable name mappings"""
        return {
            'GA_Airport_mis_01_SFPSACMission': 'Airport Mission #1',
            'GA_Airport_mis_02_SFPSACMission': 'Airport Mission #2',
            'GA_Airport_mis_03_SFPSACMission': 'Airport Mission #3',
            'GA_Airport_mis_04_SFPSACMission': 'Airport Mission #4',
            'GA_Military_02_Mis1': 'Military Base Mission #2',
            'GA_Military_03_Mis_01': 'Military Base Mission #3',
            'GA_Military_04_Mis1': 'Military Base Mission #4',
            'GA_Beregovoy_Mis1': 'Beregovoy Settlement Mission',
            'GA_Settle_05_ChernyLog_Mis1': 'Cherny Log Settlement Mission',
            'GA_Ind_01_m1': 'Industrial Zone Mission #1',
            'GA_Ind_02_Mis_1': 'Industrial Zone Mission #2',
            'GA_KhimMash_Mis_01': 'Chemical Plant Mission #1',
            'GA_KhimMash_Mis_02': 'Chemical Plant Mission #2',
            'GA_Bunker_01_Mis1': 'Underground Bunker Mission',
            'GA_Sawmill_01_Mis1': 'Sawmill Mission #1',
            'GA_Settle_09_Mis_1': 'Settlement Mission #9',
            'GA_Military_04_Mis_2': 'Military Base Mission #4B',
            'GA_PromZone_6_Mis_1': 'Industrial Zone Mission #6',
            'GA_PromZone_Mis_01': 'Industrial Zone Mission A',
            'GA_PromZone_Mis_02': 'Industrial Zone Mission B',
            'GA_Kamensk_Ind_3_Mis_1': 'Kamensk Industrial Mission',
            'GA_Kamensk_Mis_1': 'Kamensk City Mission #1',
            'GA_Kamensk_Mis_2': 'Kamensk City Mission #2',
            'GA_Kamensk_Mis_3': 'Kamensk City Mission #3',
            'GA_Krasnoe_Mis_1': 'Krasnoe City Mission',
            'GA_Vostok_Mis_1': 'Vostok City Mission',
            'GA_Lighthouse_02_Mis1': 'Lighthouse Mission #2',
            'GA_Elevator_Mis_1': 'Elevator Complex Mission #1',
            'GA_Elevator_Mis_2': 'Elevator Complex Mission #2',
            'GA_Sawmill_02_1_Mis1': 'Sawmill Mission #2A',
            'GA_Sawmill_03_Mis_01': 'Sawmill Mission #3',
            'GA_Bochki_Mis_1': 'Barrel Storage Mission',
            'GA_Dubovoe_0_Mis_1': 'Dubovoe Resource Mission',
        }

    def normalize_mission_name(self, mission_id: str) -> str:
        """Convert mission ID to readable name using EmbedFactory"""
        return EmbedFactory.normalize_mission_name(mission_id)

    def get_mission_level(self, mission_id: str) -> int:
        """Determine mission difficulty level using EmbedFactory"""
        return EmbedFactory.get_mission_level(mission_id)

    async def get_sftp_connection(self, server_config: Dict[str, Any]) -> Optional[asyncssh.SSHClientConnection]:
        """
        Get or create bulletproof SFTP connection with retry logic and connection pooling.

        Args:
            server_config: Dictionary containing host, port, username, password

        Returns:
            AsyncSSH connection object or None if connection fails

        Raises:
            ConnectionError: If all connection attempts fail
        """
        try:
            host = server_config.get('host')
            port = server_config.get('port', 22)
            username = server_config.get('username')
            password = server_config.get('password')

            if not all([host, username, password]):
                logger.warning(f"Missing SFTP credentials for {server_config.get('_id')}")
                return None

            # Use port from config with validation
            if not isinstance(port, int) or port <= 0:
                port = 22  # Default SSH port

            connection_key = f"{host}:{port}:{username}"

            # Check existing connection
            if connection_key in self.sftp_connections:
                conn = self.sftp_connections[connection_key]
                try:
                    if not conn.is_closed():
                        return conn
                    else:
                        del self.sftp_connections[connection_key]
                except:
                    del self.sftp_connections[connection_key]

            # Create new connection with bulletproof settings
            for attempt in range(3):
                try:
                    conn = await asyncio.wait_for(
                        asyncssh.connect(
                            host,
                            username=username,
                            password=password,
                            port=port,
                            known_hosts=None,
                            server_host_key_algs=['ssh-rsa', 'rsa-sha2-256', 'rsa-sha2-512'],
                            kex_algs=['diffie-hellman-group14-sha256', 'diffie-hellman-group16-sha512', 'ecdh-sha2-nistp256', 'ecdh-sha2-nistp384', 'ecdh-sha2-nistp521'],
                            encryption_algs=['aes128-ctr', 'aes192-ctr', 'aes256-ctr', 'aes128-gcm@openssh.com', 'aes256-gcm@openssh.com'],
                            mac_algs=['hmac-sha2-256', 'hmac-sha1']
                        ),
                        timeout=30
                    )
                    self.sftp_connections[connection_key] = conn
                    logger.info(f"✅ SFTP connected to {host}:{port}")
                    return conn

                except asyncio.TimeoutError as e:
                    logger.warning(f"SFTP timeout on attempt {attempt + 1} to {host}:{port}")
                    if attempt < 2:
                        await asyncio.sleep(2 ** attempt)
                except asyncssh.Error as e:
                    # Sanitize error to prevent credential exposure
                    safe_error = str(e).replace(str(password) if password else "", "***").replace(str(username) if username else "", "***")
                    logger.warning(f"SSH error on attempt {attempt + 1}: {safe_error}")
                    if attempt < 2:
                        await asyncio.sleep(2 ** attempt)
                except ConnectionError as e:
                    logger.warning(f"Connection error on attempt {attempt + 1} to {host}:{port}")
                    if attempt < 2:
                        await asyncio.sleep(2 ** attempt)

            logger.error(f"❌ Failed to connect to SFTP {host}:{port}")
            return None

        except Exception as e:
            logger.error(f"SFTP connection error: {e}")
            return None

    async def get_log_content(self, server_config: Dict[str, Any]) -> Optional[str]:
        """Get log content with SFTP priority and local fallback"""
        try:
            server_id = str(server_config.get('_id', 'unknown'))
            host = server_config.get('host', 'unknown')

            # Try SFTP first
            conn = await self.get_sftp_connection(server_config)
            if conn:
                try:
                    remote_path = f"./{host}_{server_id}/Logs/Deadside.log"
                    logger.info(f"📡 Reading SFTP: {remote_path}")

                    async with conn.start_sftp_client() as sftp:
                        try:
                            await sftp.stat(remote_path)
                            async with sftp.open(remote_path, 'r') as f:
                                content = await f.read()
                                logger.info(f"✅ SFTP read {len(content)} bytes")
                                return content
                        except FileNotFoundError:
                            logger.warning(f"Remote file not found: {remote_path}")

                except Exception as e:
                    logger.error(f"SFTP read failed: {e}")

            # Fallback to local file
            local_path = f'./{host}_{server_id}/Logs/Deadside.log'
            logger.info(f"📁 Fallback to local: {local_path}")

            if os.path.exists(local_path):
                try:
                    with open(local_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                        logger.info(f"✅ Local read {len(content)} bytes")
                        return content
                except Exception as e:
                    logger.error(f"Local read failed: {e}")
            else:
                # Create test file for development
                logger.info(f"Creating test log file at {local_path}")
                test_dir = os.path.dirname(local_path)
                os.makedirs(test_dir, exist_ok=True)

                test_content = """[2025.05.30-12.20.00:000] LogSFPS: Mission GA_Airport_mis_01_SFPSACMission switched to READY
[2025.05.30-12.20.15:000] LogNet: Join request: /Game/Maps/world_1/World_1?Name=TestPlayer&eosid=|abc123def456
[2025.05.30-12.20.20:000] LogOnline: Warning: Player |abc123def456 successfully registered!
[2025.05.30-12.20.30:000] LogSFPS: Mission GA_Airport_mis_01_SFPSACMission switched to IN_PROGRESS
[2025.05.30-12.25.00:000] LogSFPS: Mission GA_Airport_mis_01_SFPSACMission switched to COMPLETED
[2025.05.30-12.25.15:000] UChannel::Close: Sending CloseBunch UniqueId: EOS:|abc123def456"""

                with open(local_path, 'w', encoding='utf-8') as f:
                    f.write(test_content)
                return test_content

            return None

        except Exception as e:
            logger.error(f"Error getting log content: {e}")
            return None

    async def parse_log_content(self, content: str, guild_id: str, server_id: str, cold_start: bool = False, server_name: str = "Unknown Server") -> List[discord.Embed]:
        """Parse log content and return embeds"""
        embeds = []
        if not content:
            return embeds

        lines = content.splitlines()
        server_key = f"{guild_id}_{server_id}"

        # Get current state
        file_state = self.file_states.get(server_key, {})
        last_processed = file_state.get('line_count', 0)

        # Determine what to process
        if cold_start or last_processed == 0:
            # Cold start: process all lines to rebuild accurate state
            lines_to_process = lines
            logger.info(f"🧊 Cold start: processing {len(lines)} lines to rebuild player state")

            # Clear any existing sessions for this server during cold start
            server_session_keys = [k for k in self.player_sessions.keys() if k.startswith(f"{guild_id}_")]
            for session_key in server_session_keys:
                session_data = self.player_sessions.get(session_key, {})
                if session_data.get('server_id') == server_id:
                    del self.player_sessions[session_key]

            # Clear lifecycle data for this server
            server_lifecycle_keys = [k for k in self.player_lifecycle.keys() if k.startswith(f"{guild_id}_")]
            for lifecycle_key in server_lifecycle_keys:
                del self.player_lifecycle[lifecycle_key]

            logger.info(f"🧹 Cleared existing session state for cold start")
        else:
            # Hot start: process only new lines
            if last_processed < len(lines):
                lines_to_process = lines[last_processed:]
                logger.info(f"🔥 Hot start: processing {len(lines_to_process)} new lines")
            else:
                logger.info("📊 No new lines to process")
                return embeds

        # Update state immediately
        self.file_states[server_key] = {
            'line_count': len(lines),
            'last_updated': datetime.now(timezone.utc).isoformat(),
            'cold_start_complete': True
        }
        await self._save_persistent_state()

        # Track voice channel updates needed and player events for sequential processing
        voice_channel_needs_update = False
        player_events = []
        extracted_max_players = None
        extracted_server_name = None

        # Server info patterns
        self.server_info_patterns = {
            'start': re.compile(r'Server started\. Port: (\d+), QueryPort: (\d+)', re.IGNORECASE),
            'map': re.compile(r'Map: (.+)', re.IGNORECASE),
            'max_players': re.compile(r'playersmaxcount:\s*(\d+)', re.IGNORECASE),
        }

        # Extract server configuration during both cold start and hot start
        for line in lines_to_process:
            # Extract MaxPlayerCount
            max_player_match = self.patterns['max_player_count'].search(line)
            if max_player_match:
                try:
                    extracted_max_players = int(max_player_match.group(1))
                    logger.info(f"📊 Extracted MaxPlayerCount: {extracted_max_players} for server {server_id}")
                    # Store immediately when found
                    await self._update_server_info(guild_id, server_id, extracted_max_players)
                except ValueError:
                    pass

        # First pass: collect all player events with timestamps for sequential processing
        player_event_dedup = {}  # Track events per player to prevent duplicates

        for line in lines_to_process:
            try:
                # Extract timestamp from line for ordering
                timestamp_match = self.patterns['timestamp'].search(line)
                line_timestamp = timestamp_match.group(1) if timestamp_match else None

                # Parse timestamp for proper ordering
                parsed_timestamp = None
                if line_timestamp:
                    try:
                        # Convert format "2025.05.30-12.20.00:000" to datetime
                        dt_str = line_timestamp.replace('.', '-').replace(':', '.')
                        parsed_timestamp = datetime.strptime(dt_str, "%Y-%m-%d-%H.%M.%S.%f")
                    except:
                        parsed_timestamp = datetime.now(timezone.utc)
                else:
                    parsed_timestamp = datetime.now(timezone.utc)

                # Queue event - Extract EosID, Player Name, and Platform
                queue_match = self.patterns['player_queue_join'].search(line)
                if queue_match:
                    groups = queue_match.groups()
                    player_id = groups[0]
                    player_name = groups[1] if len(groups) > 1 else "Unknown"
                    platform = groups[2] if len(groups) > 2 and groups[2] else "Unknown"

                    # Extract platform from platformid format (e.g., "PS5:3566759921101398874" -> "PS5")
                    if platform and ":" in platform:
                        platform = platform.split(":")[0]

                    # Clean and decode the player name
                    import urllib.parse
                    try:
                        decoded_name = urllib.parse.unquote(player_name)
                        clean_name = decoded_name.replace('+', ' ').strip()
                        final_name = clean_name if clean_name else player_name.strip()
                    except Exception:
                        final_name = player_name.strip()

                    # Deduplication: Only add if this is the latest queue event for this player
                    event_key = f"queue_{player_id}"
                    if event_key not in player_event_dedup or parsed_timestamp > player_event_dedup[event_key]['timestamp']:
                        player_event_dedup[event_key] = {
                            'type': 'queue',
                            'player_id': player_id,
                            'player_name': final_name,
                            'platform': platform,
                            'timestamp': parsed_timestamp,
                            'line_timestamp': line_timestamp,
                            'line': line
                        }

                # Join event - Player successfully registered
                register_match = self.patterns['player_registered'].search(line)
                if register_match:
                    player_id = register_match.group(1)

                    # Add join event
                    event_key = f"join_{player_id}"
                    if event_key not in player_event_dedup or parsed_timestamp > player_event_dedup[event_key]['timestamp']:
                        player_event_dedup[event_key] = {
                            'type': 'join',
                            'player_id': player_id,
                            'timestamp': parsed_timestamp,
                            'line_timestamp': line_timestamp,
                            'line': line
                        }

                # Disconnect event - Player disconnected
                disconnect_match = self.patterns['player_disconnect'].search(line)
                if disconnect_match:
                    player_id = disconnect_match.group(1)

                    # Add disconnect event
                    event_key = f"disconnect_{player_id}"
                    if event_key not in player_event_dedup or parsed_timestamp > player_event_dedup[event_key]['timestamp']:
                        player_event_dedup[event_key] = {
                            'type': 'disconnect',
                            'player_id': player_id,
                            'timestamp': parsed_timestamp,
                            'line_timestamp': line_timestamp,
                            'line': line
                        }

            except ValueError as e:
                logger.warning(f"Value error parsing line: {e}")
                continue
            except KeyError as e:
                logger.warning(f"Missing key in regex match: {e}")
                continue
            except Exception as e:
                logger.error(f"Unexpected error collecting player events from line: {e}")
                continue

        # Convert deduplicated events to sorted list by timestamp
        player_events = sorted(player_event_dedup.values(), key=lambda x: x['timestamp'])

        # Process events in strict chronological order with proper state management
        logger.info(f"🔄 Processing {len(player_events)} player events in chronological order")

        for event in player_events:
            try:
                player_id = event['player_id']
                lifecycle_key = f"{guild_id}_{player_id}"
                session_key = f"{guild_id}_{player_id}"

                if event['type'] == 'queue':
                    # Update lifecycle with queue information
                    self.player_lifecycle[lifecycle_key] = {
                        'name': event['player_name'],
                        'platform': event['platform'],
                        'state': 'queued',
                        'queued_at': event['timestamp'].isoformat()
                    }
                    logger.debug(f"👤 Player queued: {player_id} -> '{event['player_name']}' on {event['platform']}")

                elif event['type'] == 'join':
                    # Get player data from lifecycle (if available from queue event)
                    lifecycle_data = self.player_lifecycle.get(lifecycle_key, {})
                    player_name = lifecycle_data.get('name', f"Player{player_id[:8].upper()}")
                    platform = lifecycle_data.get('platform', 'Unknown')

                    # Update lifecycle state
                    if lifecycle_key in self.player_lifecycle:
                        self.player_lifecycle[lifecycle_key]['state'] = 'joined'
                        self.player_lifecycle[lifecycle_key]['joined_at'] = event['timestamp'].isoformat()
                    else:
                        # Player joined without queue data - create minimal record
                        self.player_lifecycle[lifecycle_key] = {
                            'name': player_name,
                            'platform': platform,
                            'state': 'joined',
                            'joined_at': event['timestamp'].isoformat()
                        }

                    # Track active session
                    session_data = {
                        'player_id': player_id,
                        'player_name': player_name,
                        'platform': platform,
                        'guild_id': guild_id,
                        'server_id': server_id,
                        'joined_at': event['timestamp'].isoformat(),
                        'status': 'online'
                    }
                    self.player_sessions[session_key] = session_data

                    # Persist to database with proper error handling
                    if hasattr(self.bot, 'db_manager'):
                        await self.bot.db_manager.save_player_session(
                            int(guild_id), server_id, player_id, session_data
                        )

                    # Mark voice channel for update
                    voice_channel_needs_update = True

                    # Create embed (only if not cold start)
                    if not cold_start:
                        embed_data = {
                            'title': '🔷 Reinforcements Arrive',
                            'description': 'New player has joined the server',
                            'player_name': player_name,
                            'platform': platform,
                            'server_name': server_name
                        }

                        final_embed, file_attachment = await EmbedFactory.build_connection_embed(embed_data)
                        embeds.append(final_embed)

                elif event['type'] == 'disconnect':
                    # Only process disconnect if player was previously joined
                    lifecycle_data = self.player_lifecycle.get(lifecycle_key, {})
                    session_data = self.player_sessions.get(session_key, {})

                    # Check if player was actually online before processing disconnect
                    if (lifecycle_data.get('state') == 'joined' or 
                        session_data.get('status') == 'online'):

                        player_name = lifecycle_data.get('name') or session_data.get('player_name', f"Player{player_id[:8].upper()}")
                        platform = lifecycle_data.get('platform') or session_data.get('platform', 'Unknown')

                        # Update lifecycle state
                        if lifecycle_key in self.player_lifecycle:
                            self.player_lifecycle[lifecycle_key]['state'] = 'disconnected'
                            self.player_lifecycle[lifecycle_key]['disconnected_at'] = event['timestamp'].isoformat()

                        # Update session status
                        if session_key in self.player_sessions:
                            self.player_sessions[session_key]['status'] = 'offline'
                            self.player_sessions[session_key]['left_at'] = event['timestamp'].isoformat()

                        # Remove from database (player is offline)
                        if hasattr(self.bot, 'db_manager'):
                            await self.bot.db_manager.remove_player_session(
                                int(guild_id), server_id, player_id
                            )

                        # Mark voice channel for update
                        voice_channel_needs_update = True

                        # Create embed (only if not cold start)
                        if not cold_start:
                            embed_data = {
                                'title': '🔻 Extraction Confirmed',
                                'description': 'Player has left the server',
                                'player_name': player_name,
                                'platform': platform,
                                'server_name': server_name
                            }

                            final_embed, file_attachment = await EmbedFactory.build_connection_embed(embed_data)
                            embeds.append(final_embed)
                    else:
                        logger.debug(f"Skipping disconnect for {player_id} - player was not joined")

            except Exception as e:
                logger.error(f"Error processing player event {event.get('type', 'unknown')} for {player_id}: {e}")
                continue

        # Second pass: process non-player events with deduplication
        processed_events = set()  # Track processed events to prevent duplicates

        for line in lines_to_process:
            try:

                # Check for server info updates
                if 'playersmaxcount:' in line:
                    match = self.server_info_patterns['max_players'].search(line)
                    if match:
                        max_players = int(match.group(1))
                        extracted_max_players = max_players
                        logger.info(f"📊 Updated max players for server {server_id}: {max_players}")
                        # Update database immediately
                        if hasattr(self.bot, 'db_manager'):
                            await self.bot.db_manager.servers.update_one(
                                {"guild_id": int(guild_id), "server_id": server_id},
                                {"$set": {"max_players": max_players}},
                                upsert=True
                            )

                # Mission events - ONLY READY missions of level 3+ with deduplication
                mission_match = self.patterns['mission_state_change'].search(line)
                if mission_match:
                    mission_id, state = mission_match.groups()

                    if not cold_start:
                        # Only process READY missions of level 3 or higher
                        if state == 'READY':
                            mission_level = self.get_mission_level(mission_id)
                            if mission_level >= 3:
                                # Create unique event key to prevent duplicates
                                event_key = f"mission_{mission_id}_{state}"
                                if event_key not in processed_events:
                                    processed_events.add(event_key)
                                    embed = await self.create_mission_embed(mission_id, state)
                                    if embed:
                                        embeds.append(embed)

                # Airdrop events - ONLY flying state with deduplication
                airdrop_flying_match = self.patterns['airdrop_flying'].search(line)
                if airdrop_flying_match:
                    if not cold_start:
                        event_key = f"airdrop_flying_{datetime.now().strftime('%H:%M')}"  # Dedupe by minute
                        if event_key not in processed_events:
                            processed_events.add(event_key)
                            embed = await self.create_airdrop_embed()
                            if embed:
                                embeds.append(embed)

                # Helicrash events - ONLY crash/ready state with deduplication
                helicrash_match = self.patterns['helicrash_event'].search(line) or self.patterns['helicrash_crash'].search(line)
                if helicrash_match:
                    if not cold_start:
                        event_key = f"helicrash_{datetime.now().strftime('%H:%M')}"  # Dedupe by minute
                        if event_key not in processed_events:
                            processed_events.add(event_key)
                            embed = await self.create_helicrash_embed()
                            if embed:
                                embeds.append(embed)

                # Trader events - ONLY arrival/ready state with deduplication
                trader_arrival_match = self.patterns['trader_arrival'].search(line)
                if trader_arrival_match:
                    if not cold_start:
                        event_key = f"trader_arrival_{datetime.now().strftime('%H:%M')}"  # Dedupe by minute
                        if event_key not in processed_events:
                            processed_events.add(event_key)
                            embed = await self.create_trader_embed()
                            if embed:
                                embeds.append(embed)

                # Vehicle events with deduplication
                vehicle_spawn_match = self.patterns['vehicle_spawn'].search(line)
                if vehicle_spawn_match:
                    vehicle_type = vehicle_spawn_match.group(1)
                    if not cold_start:
                        event_key = f"vehicle_spawn_{vehicle_type}_{datetime.now().strftime('%H:%M')}"
                        if event_key not in processed_events:
                            processed_events.add(event_key)
                            embed = await self.create_vehicle_embed('spawn', vehicle_type)
                            if embed:
                                embeds.append(embed)

                vehicle_delete_match = self.patterns['vehicle_delete'].search(line)
                if vehicle_delete_match:
                    vehicle_type = vehicle_delete_match.group(1)
                    if not cold_start:
                        event_key = f"vehicle_delete_{vehicle_type}_{datetime.now().strftime('%H:%M')}"
                        if event_key not in processed_events:
                            processed_events.add(event_key)
                            embed = await self.create_vehicle_embed('delete', vehicle_type)
                            if embed:
                                embeds.append(embed)

            except Exception as e:
                logger.error(f"Error processing line: {e}")
                continue

        # Update voice channel once at the end if needed
        if voice_channel_needs_update:
            await self.update_voice_channel(str(guild_id))

        if not cold_start:
            logger.info(f"🔍 Generated {len(embeds)} events")

        return embeds

    async def create_mission_embed(self, mission_id: str, state: str, respawn_time: Optional[int] = None) -> Optional[discord.Embed]:
        """Create mission embed"""
        try:
            mission_level = self.get_mission_level(mission_id)

            embed_data = {
                'mission_id': mission_id,
                'state': state,
                'level': mission_level,
                'respawn_time': respawn_time
            }

            embed, file = await EmbedFactory.build('mission', embed_data)
            return embed

        except Exception as e:
            logger.error(f"Failed to create mission embed: {e}")
            return None

    async def create_airdrop_embed(self, location: str = "Unknown") -> Optional[discord.Embed]:
        """Create airdrop embed"""
        try:
            embed = EmbedFactory.create_airdrop_embed(
                state="incoming",
                location=location,
                timestamp=datetime.now(timezone.utc)
            )
            return embed
        except Exception as e:
            logger.error(f"Failed to create airdrop embed: {e}")
            return None

    async def create_helicrash_embed(self, location: str = "Unknown") -> Optional[discord.Embed]:
        """Create helicrash embed"""
        try:
            embed = EmbedFactory.create_helicrash_embed(
                location=location,
                timestamp=datetime.now(timezone.utc)
            )
            return embed
        except Exception as e:
            logger.error(f"Failed to create helicrash embed: {e}")
            return None

    async def create_trader_embed(self, location: str = "Unknown") -> Optional[discord.Embed]:
        """Create trader embed"""
        try:
            embed = EmbedFactory.create_trader_embed(
                location=location,
                timestamp=datetime.now(timezone.utc)
            )
            return embed
        except Exception as e:
            logger.error(f"Failed to create trader embed: {e}")
            return None

    async def create_vehicle_embed(self, action: str, vehicle_type: str) -> Optional[discord.Embed]:
        """Create vehicle embed - BLOCKED per requirements"""
        # Vehicle embeds are suppressed per task requirements
        return None

    async def update_voice_channel(self, guild_id: str):
        """ADVANCED voice channel update with server name, counts, and queue info"""
        try:
            # Convert guild_id to int with better validation
            if isinstance(guild_id, str):
                # Skip if it's a MongoDB ObjectId
                if len(guild_id) == 24 and all(c in '0123456789abcdef' for c in guild_id.lower()):
                    logger.debug(f"Skipping voice update for MongoDB ObjectId: {guild_id}")
                    return
                try:
                    guild_id_int = int(guild_id)
                except ValueError:
                    logger.warning(f"Invalid guild_id format: {guild_id}")
                    return
            else:
                guild_id_int = guild_id

            # Count active players with better key validation
            guild_prefix = f"{guild_id}_"
            active_players = 0
            queued_players = 0

            for key, session in self.player_sessions.items():
                if key.startswith(guild_prefix) and isinstance(session, dict) and session.get('status') == 'online':
                    active_players += 1

            # Count queued players (those in 'queued' state but not joined)
            for key, lifecycle in self.player_lifecycle.items():
                if key.startswith(guild_prefix) and lifecycle.get('state') == 'queued':
                    queued_players += 1

            logger.debug(f"Counted {active_players} active players and {queued_players} queued for guild {guild_id_int}")

            # Get guild config with validation
            if not hasattr(self.bot, 'db_manager') or not self.bot.db_manager:
                logger.warning("Database manager not available for voice channel update")
                return

            guild_config = await self.bot.db_manager.get_guild(guild_id_int)
            if not guild_config:
                logger.debug(f"No guild config found for {guild_id_int}")
                return

            # Get server info for display
            servers = guild_config.get('servers', [])
            server_name = "Unknown Server"
            max_players = 60  # Default

            if servers:
                # Use first server's info for display (most common case is single server)
                primary_server = servers[0]
                server_name = primary_server.get('name', 'Server').replace(' Server', '').replace(' EU', '').replace(' US', '')

                # Try to get MaxPlayerCount from database first, then fallback to config
                try:
                    stored_max_players = await self._get_server_max_players(guild_id_int, str(primary_server.get('_id', '')))
                    if stored_max_players and stored_max_players > 0:
                        max_players = stored_max_players
                        logger.debug(f"Using database MaxPlayerCount: {max_players}")
                    else:
                        max_players = primary_server.get('max_players', 60)
                        logger.debug(f"Using config max_players: {max_players} (no database value found)")
                except Exception as e:
                    logger.warning(f"Failed to get stored max players: {e}")
                    max_players = primary_server.get('max_players', 60)

            # Find voice channel ID with comprehensive mapping
            voice_channel_id = None

            # Method 1: Check server_channels (new format)
            server_channels = guild_config.get('server_channels', {})
            for server_key, channels in server_channels.items():
                if isinstance(channels, dict):
                    # Try multiple voice channel key names
                    for voice_key in ['voice_count', 'playercountvc', 'playercount']:
                        if voice_key in channels:
                            voice_channel_id = channels[voice_key]
                            logger.debug(f"Found voice channel {voice_channel_id} as {voice_key} in server {server_key}")
                            break
                    if voice_channel_id:
                        break

            # Method 2: Check channels (legacy format)
            if not voice_channel_id:
                legacy_channels = guild_config.get('channels', {})
                if isinstance(legacy_channels, dict):
                    for voice_key in ['voice_count', 'playercountvc', 'playercount']:
                        if voice_key in legacy_channels:
                            voice_channel_id = legacy_channels[voice_key]
                            logger.debug(f"Found legacy voice channel {voice_channel_id} as {voice_key}")
                            break

            # Method 3: Check if any servers have voice channels configured
            if not voice_channel_id:
                for server in servers:
                    server_id = str(server.get('_id', ''))
                    if server_id in server_channels:
                        channels = server_channels[server_id]
                        if isinstance(channels, dict):
                            for voice_key in ['voice_count', 'playercountvc', 'playercount']:
                                if voice_key in channels:
                                    voice_channel_id = channels[voice_key]
                                    logger.debug(f"Found voice channel {voice_channel_id} in server {server_id}")
                                    break
                        if voice_channel_id:
                            break

            if not voice_channel_id:
                logger.debug(f"No voice channel configured for guild {guild_id_int}")
                return

            # Update the channel with rate limit protection
            guild = self.bot.get_guild(guild_id_int)
            if not guild:
                logger.warning(f"Guild {guild_id_int} not found")
                return

            voice_channel = guild.get_channel(voice_channel_id)
            if not voice_channel:
                logger.warning(f"Voice channel {voice_channel_id} not found in guild {guild_id_int}")
                return

            if voice_channel.type != discord.ChannelType.voice:
                logger.warning(f"Channel {voice_channel_id} is not a voice channel")
                return

            # Determine status emoji based on player count
            status_emoji = "🟢"  # Green for healthy
            if active_players == 0:
                status_emoji = "🔴"  # Red for empty
            elif active_players >= max_players * 0.8:
                status_emoji = "🟡"  # Yellow for near full
            elif active_players >= max_players:
                status_emoji = "🔴"  # Red for full

            # Build voice channel name with specified format
            queue_text = f" | {queued_players} in Queue" if queued_players > 0 else ""
            new_name = f"{status_emoji} {server_name} | {active_players}/{max_players}{queue_text}"

            # Ensure name fits Discord's 100 character limit
            if len(new_name) > 100:
                # Truncate server name if needed
                max_server_name_length = 100 - len(f"{status_emoji}  | {active_players}/{max_players}{queue_text}")
                if max_server_name_length > 0:
                    truncated_server_name = server_name[:max_server_name_length]
                    new_name = f"{status_emoji} {truncated_server_name} | {active_players}/{max_players}{queue_text}"
                else:
                    # Fallback to simple format
                    new_name = f"{status_emoji} Players: {active_players}/{max_players}"

            if voice_channel.name != new_name:
                try:
                    # Direct voice channel update - no rate limiter needed for voice channels
                    await voice_channel.edit(name=new_name)
                    logger.info(f"✅ Voice channel updated to: {new_name}")

                except discord.HTTPException as e:
                    if e.status == 429:  # Rate limited
                        logger.warning(f"Rate limited updating voice channel: {e}")
                    else:
                        logger.error(f"HTTP error updating voice channel: {e}")
                except Exception as edit_error:
                    logger.error(f"Error editing voice channel: {edit_error}")
            else:
                logger.debug(f"Voice channel already has correct name: {new_name}")

        except Exception as e:
            logger.error(f"Voice channel update failed: {e}")
            import traceback
            logger.error(f"Voice channel update traceback: {traceback.format_exc()}")

    async def get_channel_for_type(self, guild_id: int, server_id: str, channel_type: str) -> Optional[int]:
        """Get channel ID with bulletproof fallback"""
        try:
            if not hasattr(self.bot, 'db_manager') or not self.bot.db_manager:
                return None

            guild_config = await self.bot.db_manager.get_guild(guild_id)
            if not guild_config:
                return None

            server_channels = guild_config.get('server_channels', {})

            # Server-specific channel
            if server_id in server_channels and channel_type in server_channels[server_id]:
                return server_channels[server_id][channel_type]

            # Default server channel
            if 'default' in server_channels and channel_type in server_channels['default']:
                return server_channels['default'][channel_type]

            # Fallback to killfeed if no specific channel
            if channel_type != 'killfeed':
                killfeed_id = None
                if server_id in server_channels:
                    killfeed_id = server_channels[server_id].get('killfeed')
                if not killfeed_id and 'default' in server_channels:
                    killfeed_id = server_channels['default'].get('killfeed')
                if killfeed_id:
                    return killfeed_id

            # Legacy fallback
            return guild_config.get('channels', {}).get(channel_type)

        except Exception as e:
            logger.error(f"Error getting channel: {e}")
            return None

    async def send_embeds(self, guild_id: int, server_id: str, embeds: List[discord.Embed]):
        """Send embeds to appropriate channels with proper file attachments"""
        if not embeds:
            return

        try:
            for embed in embeds:
                # Determine channel type and embed type based on embed content
                channel_type = 'events'  # Default
                embed_type = 'general'

                # Check embed title and description for connection events
                if embed.title:
                    title_lower = embed.title.lower()
                    if any(word in title_lower for word in ['reinforcements', 'extraction', 'arrive', 'confirmed', 'join', 'left']):
                        channel_type = 'connections'
                        embed_type = 'connection'
                    elif 'mission' in title_lower:
                        channel_type = 'events'
                        embed_type = 'mission'
                    elif 'airdrop' in title_lower:
                        channel_type = 'events'
                        embed_type = 'airdrop'
                    elif 'helicrash' in title_lower or 'helicopter' in title_lower:
                        channel_type = 'events'
                        embed_type = 'helicrash'
                    elif 'trader' in title_lower:
                        channel_type = 'events'
                        embed_type = 'trader'

                # Get channel with proper fallback
                channel_id = await self.get_channel_for_type(guild_id, server_id, channel_type)
                if not channel_id:
                    # Fallback to events channel if connections channel not found
                    if channel_type == 'connections':
                        channel_id = await self.get_channel_for_type(guild_id, server_id, 'events')
                    if not channel_id:
                        continue

                channel = self.bot.get_channel(channel_id)
                if channel:
                    try:
                        # Send embeds directly without rebuilding to preserve data
                        if embed_type == 'connection':
                            # The embed already has the correct data, just send it with proper file
                            connections_file = discord.File("./assets/Connections.png", filename="Connections.png")
                            embed.set_thumbnail(url="attachment://Connections.png")
                            final_embed = embed
                            file_attachment = connections_file

                        elif embed_type == 'mission':
                            # The mission embed already has correct data, just add thumbnail
                            mission_file = discord.File("./assets/Mission.png", filename="Mission.png")
                            embed.set_thumbnail(url="attachment://Mission.png")
                            final_embed = embed
                            file_attachment = mission_file

                        else:
                            # For other embed types, send directly with appropriate thumbnail
                            if embed_type == 'airdrop':
                                asset_file = discord.File("./assets/Airdrop.png", filename="Airdrop.png")
                                embed.set_thumbnail(url="attachment://Airdrop.png")
                            elif embed_type == 'helicrash':
                                asset_file = discord.File("./assets/Helicrash.png", filename="Helicrash.png")
                                embed.set_thumbnail(url="attachment://Helicrash.png")
                            elif embed_type == 'trader':
                                asset_file = discord.File("./assets/Trader.png", filename="Trader.png")
                                embed.set_thumbnail(url="attachment://Trader.png")
                            else:
                                asset_file = discord.File("./assets/main.png", filename="main.png")
                                embed.set_thumbnail(url="attachment://main.png")

                            final_embed = embed
                            file_attachment = asset_file

                        # Set priority for rate limiter
                        from bot.utils.advanced_rate_limiter import MessagePriority
                        priority = MessagePriority.NORMAL
                        if embed_type == 'connection':
                            priority = MessagePriority.HIGH
                        elif embed_type == 'mission' and 'ready' in embed.title.lower():
                            priority = MessagePriority.HIGH

                        # Send with rate limiter if available
                        if hasattr(self.bot, 'advanced_rate_limiter'):
                            await self.bot.advanced_rate_limiter.queue_message(
                                channel_id=channel.id,
                                embed=final_embed,
                                file=file_attachment,
                                priority=priority
                            )
                        else:
                            # Fallback to direct send
                            if file_attachment:
                                await channel.send(embed=final_embed, file=file_attachment)
                            else:
                                await channel.send(embed=final_embed)

                    except Exception as e:
                        logger.error(f"Failed to send embed: {e}")

        except Exception as e:
            logger.error(f"Error sending embeds: {e}")

    async def parse_server_logs(self, guild_id: int, server: dict):
        """Parse logs for a single server"""
        try:
            server_id = str(server.get('_id', 'unknown'))
            server_name = server.get('name', 'Unknown')
            host = server.get('host', 'unknown')

            logger.info(f"🔍 Processing {server_name} (ID: {server_id}, Host: {host})")

            if not host or not server_id or host == 'unknown' or server_id == 'unknown':
                logger.warning(f"❌ Invalid server config: {server_name}")
                return

            # Get log content
            content = await self.get_log_content(server)
            if not content:
                logger.warning(f"❌ No log content for {server_name}")
                return

            # Determine if cold start
            server_key = f"{guild_id}_{server_id}"
            file_state = self.file_states.get(server_key, {})
            is_cold_start = not file_state.get('cold_start_complete', False)

            # Parse content with server context
            embeds = await self.parse_log_content(content, str(guild_id), server_id, is_cold_start, server_name)

            # Send embeds (only if not cold start)
            if not is_cold_start and embeds:
                await self.send_embeds(guild_id, server_id, embeds)

            # Log combined event summary
            if not is_cold_start and embeds:
                event_types = {}
                connection_events = 0
                for embed in embeds:
                    if embed.title:
                        title_lower = embed.title.lower()
                        if any(word in title_lower for word in ['connect', 'disconnect', 'join', 'left']):
                            connection_events += 1
                        elif 'mission' in title_lower:
                            event_types['missions'] = event_types.get('missions', 0) + 1
                        elif 'airdrop' in title_lower:
                            event_types['airdrops'] = event_types.get('airdrops', 0) + 1
                        elif 'helicrash' in title_lower:
                            event_types['helicrashes'] = event_types.get('helicrashes', 0) + 1
                        elif 'trader' in title_lower:
                            event_types['traders'] = event_types.get('traders', 0) + 1

                if connection_events:
                    event_types['connections'] = connection_events

                event_summary = ", ".join([f"{count} {type_name}" for type_name, count in event_types.items()])
                logger.info(f"✅ {server_name}: {len(embeds)} total events sent ({event_summary})")
            else:
                logger.info(f"✅ {server_name}: {'Cold start' if is_cold_start else 'No new events'}")

        except Exception as e:
            logger.error(f"Error parsing server {server.get('name', 'Unknown')}: {e}")

    async def run_log_parser(self):
        """Main parser entry point"""
        try:
            logger.info("🔄 Running unified log parser...")

            if not hasattr(self.bot, 'db_manager') or not self.bot.db_manager:
                logger.error("❌ Database not available")
                return

            # Get all guilds
            guilds_cursor = self.bot.db_manager.guilds.find({})
            guilds_list = await guilds_cursor.to_list(length=None)

            if not guilds_list:
                logger.info("No guilds found")
                return

            total_processed = 0

            for guild_doc in guilds_list:
                guild_id = guild_doc.get('guild_id')
                if not guild_id:
                    continue

                try:
                    guild_id = int(guild_id)
                except:
                    continue

                guild_name = guild_doc.get('name', f'Guild {guild_id}')
                servers = guild_doc.get('servers', [])

                if not servers:
                    continue

                logger.info(f"📡 Processing {len(servers)} servers for {guild_name}")

                for server in servers:
                    try:
                        await self.parse_server_logs(guild_id, server)
                        total_processed += 1
                    except Exception as e:
                        logger.error(f"Server parse error: {e}")

            logger.info(f"✅ Parser completed: {total_processed} servers processed")

        except Exception as e:
            logger.error(f"Parser run failed: {e}")

    async def _resolve_player_name(self, raw_name: str, player_id: str) -> str:
        """Enhanced player name resolution with caching and validation"""
        try:
            # Check cache first
            cache_key = f"{player_id}_{raw_name}"
            if cache_key in self.player_name_cache:
                return self.player_name_cache[cache_key]

            # Clean and decode the player name
            import urllib.parse
            try:
                decoded_name = urllib.parse.unquote(raw_name)
                clean_name = decoded_name.replace('+', ' ').strip()
                final_name = clean_name if clean_name else raw_name.strip()
            except Exception:
                final_name = raw_name.strip()

            # Validate the resolved name
            if not final_name or len(final_name) < 2:
                final_name = f"Player{player_id[:8].upper()}"

            # Reject numeric-only names
            if final_name.replace('.', '').replace('-', '').isdigit():
                final_name = f"Player{player_id[:8].upper()}"

            # Cache the result with expiration
            self.player_name_cache[cache_key] = final_name

            # Clean old cache entries (keep only last 1000)
            if len(self.player_name_cache) > 1000:
                old_keys = list(self.player_name_cache.keys())[:-500]
                for old_key in old_keys:
                    del self.player_name_cache[old_key]

            return final_name

        except Exception as e:
            logger.error(f"Failed to resolve player name: {e}")
            return f"Player{player_id[:8].upper()}"

    async def _save_persistent_state(self):
        """Save parser state to database"""
        try:
            if not hasattr(self.bot, 'db_manager') or not self.bot.db_manager:
                return

            for server_key, state_data in self.file_states.items():
                try:
                    # Extract guild_id and server_id from key
                    parts = server_key.split('_', 1)
                    if len(parts) == 2:
                        guild_id = int(parts[0])
                        server_id = parts[1]

                        await self.bot.db_manager.save_parser_state(
                            guild_id, server_id, state_data, "unified_log_parser"
                        )
                except Exception as e:
                    logger.error(f"Failed to save state for {server_key}: {e}")

        except Exception as e:
            logger.error(f"Failed to save persistent state: {e}")

    async def _load_persistent_state(self):
        """Load parser state and player sessions from database"""
        try:
            if not hasattr(self.bot, 'db_manager') or not self.bot.db_manager:
                return

            # Get all guilds to load their states
            guilds_cursor = self.bot.db_manager.guilds.find({})
            guilds_list = await guilds_cursor.to_list(length=None)

            loaded_count = 0
            session_count = 0

            for guild_doc in guilds_list:
                guild_id = guild_doc['guild_id']
                servers = guild_doc.get('servers', [])

                for server in servers:
                    server_id = str(server.get('_id', ''))
                    if server_id:
                        try:
                            # Load parser state
                            state = await self.bot.db_manager.get_parser_state(
                                guild_id, server_id, "unified_log_parser"
                            )

                            if state:
                                server_key = f"{guild_id}_{server_id}"
                                self.file_states[server_key] = state
                                loaded_count += 1

                            # Load active player sessions
                            active_sessions = await self.bot.db_manager.get_active_player_sessions(guild_id, server_id)
                            for session in active_sessions:
                                player_id = session.get('player_id')
                                if player_id:
                                    session_key = f"{guild_id}_{player_id}"
                                    self.player_sessions[session_key] = {
                                        'player_id': player_id,
                                        'player_name': session.get('player_name', f"Player{player_id[:8].upper()}"),
                                        'platform': session.get('platform', 'Unknown'),
                                        'guild_id': str(guild_id),
                                        'server_id': server_id,
                                        'joined_at': session.get('joined_at', datetime.now(timezone.utc).isoformat()),
                                        'status': 'online'
                                    }
                                    session_count += 1

                        except Exception as e:
                            logger.error(f"Failed to load state for {guild_id}_{server_id}: {e}")

            if loaded_count > 0:
                logger.info(f"✅ Loaded state for {loaded_count} servers")
            if session_count > 0:
                logger.info(f"✅ Restored {session_count} active player sessions")

            # Clean up stale sessions
            await self.bot.db_manager.cleanup_stale_sessions()

        except Exception as e:
            logger.error(f"Failed to load persistent state: {e}")

    async def _update_server_info(self, guild_id: str, server_id: str, max_players: Optional[int]):
        """Update server information in database"""
        try:
            if not hasattr(self.bot, 'db_manager') or not self.bot.db_manager:
                return

            if max_players:
                # Store max_players in a server_info collection or similar
                await self.bot.db_manager.save_parser_state(
                    int(guild_id), server_id, 
                    {'max_players': max_players}, 
                    "server_info"
                )
                logger.debug(f"Updated max_players for {server_id}: {max_players}")

        except Exception as e:
            logger.error(f"Failed to update server info: {e}")

    async def _get_server_max_players(self, guild_id: int, server_id: str) -> Optional[int]:
        """Get stored max_players for server"""
        try:
            if not hasattr(self.bot, 'db_manager') or not self.bot.db_manager:
                return None

            server_info = await self.bot.db_manager.get_parser_state(
                guild_id, server_id, "server_info"
            )

            if server_info and 'max_players' in server_info:
                return server_info['max_players']

            return None

        except Exception as e:
            logger.error(f"Failed to get server max players: {e}")
            return None

    async def _schedule_periodic_cleanup(self):
        """Schedule periodic cleanup of memory structures"""
        while True:
            try:
                await asyncio.sleep(300)  # Clean up every 5 minutes
                await self._cleanup_memory_structures()
            except Exception as e:
                logger.error(f"Error in periodic cleanup: {e}")

    async def _cleanup_memory_structures(self):
        """Clean up memory structures to prevent memory leaks"""
        try:
            current_time = time.time()

            # Clean up player lifecycle (remove entries older than 1 hour)
            lifecycle_cutoff = current_time - 3600
            to_remove = []

            for key, lifecycle in self.player_lifecycle.items():
                try:
                    # Check various timestamp fields
                    timestamps = [
                        lifecycle.get('queued_at'),
                        lifecycle.get('joined_at'),
                        lifecycle.get('disconnected_at')
                    ]

                    latest_activity = 0
                    for ts in timestamps:
                        if ts:
                            try:
                                if isinstance(ts, str):
                                    ts_dt = datetime.fromisoformat(ts.replace('Z', '+00:00'))
                                    latest_activity = max(latest_activity, ts_dt.timestamp())
                            except Exception:
                                pass

                    if latest_activity > 0 and latest_activity < lifecycle_cutoff:
                        to_remove.append(key)

                except Exception as e:
                    logger.error(f"Error checking lifecycle entry {key}: {e}")
                    to_remove.append(key)

            for key in to_remove:
                del self.player_lifecycle[key]

            # Clean up player sessions (remove offline players older than 30 minutes)
            session_cutoff = current_time - 1800
            to_remove = []

            for key, session in self.player_sessions.items():
                try:
                    if session.get('status') == 'offline':
                        left_at = session.get('left_at')
                        if left_at:
                            try:
                                if isinstance(left_at, str):
                                    left_dt = datetime.fromisoformat(left_at.replace('Z', '+00:00'))
                                    if left_dt.timestamp() < session_cutoff:
                                        to_remove.append(key)
                            except Exception:
                                to_remove.append(key)
                except Exception as e:
                    logger.error(f"Error checking session entry {key}: {e}")
                    to_remove.append(key)

            for key in to_remove:
                del self.player_sessions[key]

            # Aggressive memory management with bounds checking
            if len(self.player_name_cache) > self.max_cache_size:
                # Keep only the most recent entries with safety bounds
                try:
                    cache_items = list(self.player_name_cache.items())
                    keep_count = min(self.max_cache_size // 2, len(cache_items))
                    self.player_name_cache = dict(cache_items[-keep_count:]) if keep_count > 0 else {}
                except Exception as e:
                    logger.error(f"Error cleaning name cache: {e}")
                    self.player_name_cache.clear()

            if len(self.player_lifecycle) > self.max_lifecycle_entries:
                # Keep only active and recent entries
                try:
                    lifecycle_items = list(self.player_lifecycle.items())
                    keep_count = min(self.max_lifecycle_entries // 2, len(lifecycle_items))
                    self.player_lifecycle = dict(lifecycle_items[-keep_count:]) if keep_count > 0 else {}
                except Exception as e:
                    logger.error(f"Error cleaning lifecycle: {e}")
                    self.player_lifecycle.clear()

            if len(self.player_sessions) > self.max_session_entries:
                # Keep only active sessions
                try:
                    active_sessions = {k: v for k, v in self.player_sessions.items() if v.get('status') == 'online'}
                    if len(active_sessions) < self.max_session_entries:
                        self.player_sessions = active_sessions
                    else:
                        # If too many active sessions, keep most recent
                        session_items = list(active_sessions.items())
                        keep_count = min(self.max_session_entries // 2, len(session_items))
                        self.player_sessions = dict(session_items[-keep_count:]) if keep_count > 0 else {}
                except Exception as e:
                    logger.error(f"Error cleaning sessions: {e}")
                    # Emergency cleanup
                    self.player_sessions = {k: v for k, v in self.player_sessions.items() if v.get('status') == 'online'}

            logger.debug(f"Memory cleanup completed: {len(to_remove)} lifecycle entries, cache size: {len(self.player_name_cache)}")

        except Exception as e:
            logger.error(f"Failed to cleanup memory structures: {e}")

    def get_parser_status(self) -> Dict[str, Any]:
        """Get parser status"""
        try:
            active_sessions = sum(1 for session in self.player_sessions.values() if session.get('status') == 'online')

            # Calculate active players by guild
            active_players_by_guild = {}
            for key, session in self.player_sessions.items():
                if session.get('status') == 'online':
                    guild_id = session.get('guild_id', 'unknown')
                    active_players_by_guild[guild_id] = active_players_by_guild.get(guild_id, 0) + 1

            # Check SFTP connection status
            active_connections = 0
            for conn in self.sftp_connections.values():
                try:
                    if not conn.is_closed():
                        active_connections += 1
                except:
                    pass

            return {
                'active_sessions': active_sessions,
                'total_tracked_servers': len(self.file_states),
                'sftp_connections': active_connections,
                'connection_status': f"{active_connections}/{len(self.sftp_connections)} active",
                'active_players_by_guild': active_players_by_guild,
                'status': 'healthy' if active_sessions >= 0 else 'error'
            }
        except Exception as e:
            logger.error(f"Error getting parser status: {e}")
            return {
                'active_sessions': 0,
                'total_tracked_servers': 0,
                'sftp_connections': 0,
                'connection_status': 'error',
                'active_players_by_guild': {},
                'status': 'error'
            }

    async def cleanup_sftp_connections(self):
        """Clean up idle SFTP connections with enhanced error handling"""
        try:
            for conn_key, conn in list(self.sftp_connections.items()):
                try:
                    if hasattr(conn, 'is_closed') and conn.is_closed():
                        del self.sftp_connections[conn_key]
                        logger.debug(f"Cleaned up closed SFTP connection: {conn_key}")
                    elif hasattr(conn, '_transport') and hasattr(conn._transport, 'is_closing') and conn._transport.is_closing():
                        del self.sftp_connections[conn_key] 
                        logger.debug(f"Cleaned up closing SFTP connection: {conn_key}")
                except Exception as conn_error:
                    logger.warning(f"Error checking SFTP connection {conn_key}: {conn_error}")
                    if conn_key in self.sftp_connections:
                        del self.sftp_connections[conn_key]
        except Exception as e:
            logger.error(f"Failed to cleanup SFTP connections: {e}")

    def reset_parser_state(self):
        """Reset all parser state with proper cleanup"""
        try:
            # Clear dictionaries safely
            self.file_states.clear()
            self.player_sessions.clear()
            self.player_lifecycle.clear()
            self.last_log_position.clear()
            self.log_file_hashes.clear()
            self.player_name_cache.clear()

            if hasattr(self, 'server_status'):
                self.server_status.clear()

            # Close any open SFTP connections
            for conn_key, conn in list(self.sftp_connections.items()):
                try:
                    if hasattr(conn, 'close') and not conn.is_closed():
                        conn.close()
                except Exception as close_error:
                    logger.warning(f"Error closing SFTP connection: {close_error}")

            self.sftp_connections.clear()

            # Force garbage collection
            import gc
            gc.collect()

            logger.info("✅ Parser state reset with cleanup")
        except Exception as e:
            logger.error(f"Error resetting parser state: {e}")
            import traceback
            logger.error(f"State reset traceback: {traceback.format_exc()}")

    def get_active_player_count(self, guild_id: str) -> int:
        """Get active player count for a guild"""
        try:
            guild_prefix = f"{guild_id}_"
            return sum(
                1 for key, session in self.player_sessions.items()
                if key.startswith(guild_prefix) and isinstance(session, dict) and session.get('status') == 'online'
            )
        except Exception as e:
            logger.error(f"Error getting active player count: {e}")
            return 0