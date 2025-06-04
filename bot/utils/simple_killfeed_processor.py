"""
Simple Killfeed Processor
Based on historical parser's proven CSV discovery and processing approach
Maintains state instead of clearing it like historical parser does
Shares state system with historical parser (separate from unified parser)
"""

import asyncio
import logging
import re
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass

from bot.utils.connection_pool import GlobalConnectionManager, connection_manager
from bot.utils.killfeed_state_manager import killfeed_state_manager, KillfeedState

logger = logging.getLogger(__name__)

@dataclass
class KillfeedEvent:
    """Represents a single killfeed event"""
    timestamp: datetime
    killer: str
    victim: str
    weapon: str
    distance: int
    killer_platform: str
    victim_platform: str
    raw_line: str
    line_number: int
    filename: str

class SimpleKillfeedProcessor:
    """Simple killfeed processor without shared state dependencies"""
    
    def __init__(self, guild_id: int, server_config: Dict[str, Any], bot=None):
        self.guild_id = guild_id
        self.server_config = server_config
        self.server_name = server_config.get('name', 'Unknown')
        self.state_manager = killfeed_state_manager
        self.bot = bot
        self.cancelled = False
        self._current_subdir = None  # Track current subdirectory
        
        # Initialize channel router for proper channel resolution
        from bot.utils.channel_router import ChannelRouter
        self.channel_router = ChannelRouter(bot) if bot else None
        
    def _get_killfeed_path(self) -> str:
        """Get the killfeed path for this server"""
        host = self.server_config.get('host', 'unknown')
        server_id = self.server_config.get('_id', self.server_config.get('server_id', 'unknown'))
        return f"./{host}_{server_id}/actual1/deathlogs/"
    
    async def process_server_killfeed(self, progress_callback=None) -> Dict[str, Any]:
        """Main entry point for killfeed processing"""
        results = {
            'success': False,
            'events_processed': 0,
            'errors': []
        }
        
        try:
            # Register session with killfeed state manager
            if self.state_manager:
                await self.state_manager.register_session(self.guild_id, self.server_name)
            
            # Get current killfeed-specific state
            current_state = None
            if self.state_manager:
                current_state = await self.state_manager.get_killfeed_state(self.guild_id, self.server_name)
                if current_state:
                    logger.info(f"Found existing killfeed state: {current_state.last_file} at line {current_state.last_line}")
            
            events = []
            
            # Discover newest CSV file
            newest_file = await self._discover_newest_csv_file()
            if newest_file:
                logger.info(f"Processing killfeed file: {newest_file}")
                
                # Always process the newest file - check if it's a new file or continuing existing
                if current_state and current_state.last_file == newest_file:
                    # Continue from last known position in same file
                    logger.info(f"Continuing from position {current_state.last_byte_position} in {newest_file}")
                    new_events = await self._process_csv_file(newest_file, current_state)
                else:
                    # New file or first run - start from beginning
                    logger.info(f"Starting fresh processing of {newest_file}")
                    new_events = await self._process_csv_file(newest_file, None)
                
                events.extend(new_events)
            else:
                logger.warning("No killfeed CSV files found")
            
            if events:
                # Deliver events to Discord
                await self._deliver_killfeed_events(events)
                results['events_processed'] = len(events)
                logger.info(f"✅ Processed {len(events)} killfeed events for {self.server_name}")
            else:
                logger.info(f"No new killfeed events found for {self.server_name}")
            
            results['success'] = True
            
        except Exception as e:
            logger.error(f"Killfeed processing failed for {self.server_name}: {e}")
            results['error'] = str(e)
        
        finally:
            # Unregister session
            if self.state_manager:
                await self.state_manager.unregister_session(self.guild_id, self.server_name)
        
        return results
    
    async def _finish_previous_file(self, current_state: KillfeedState) -> List[KillfeedEvent]:
        """Finish processing the previous file from last known position"""
        events = []
        
        try:
            # Construct path to previous file
            killfeed_path = self._get_killfeed_path()
            
            # Use the subdirectory if we have one from discovery
            if self._current_subdir:
                previous_file_path = f"{killfeed_path}{self._current_subdir}/{current_state.last_file}"
            else:
                previous_file_path = f"{killfeed_path}{current_state.last_file}"
            
            logger.info(f"Finishing previous file: {current_state.last_file} from line {current_state.last_line}")
            
            async with connection_manager.get_connection(self.guild_id, self.server_config) as conn:
                if not conn:
                    return events
                
                sftp = await conn.start_sftp_client()
                
                # Check if previous file still exists
                try:
                    await sftp.stat(previous_file_path)
                except:
                    logger.warning(f"Previous file {current_state.last_file} no longer exists")
                    return events
                
                # Read from last known position to end of file
                async with sftp.open(previous_file_path, 'rb') as file:
                    await file.seek(current_state.last_byte_position)
                    remaining_content = await file.read()
                    
                    if remaining_content:
                        lines = remaining_content.decode('utf-8', errors='ignore').splitlines()
                        
                        # Process remaining lines
                        for i, line in enumerate(lines):
                            if self.cancelled:
                                break
                            
                            line = line.strip()
                            if not line:
                                continue
                            
                            event = self._parse_killfeed_line(line, current_state.last_line + i, current_state.last_file)
                            if event:
                                events.append(event)
                        
                        # Update state to reflect completion of previous file
                        if self.state_manager and lines:
                            final_line = current_state.last_line + len(lines)
                            final_byte = current_state.last_byte_position + len(remaining_content)
                            
                            await self.state_manager.update_killfeed_state(
                                self.guild_id, self.server_name,
                                current_state.last_file, final_line, final_byte,
                                current_state.file_timestamp
                            )
                            
        except Exception as e:
            logger.error(f"Failed to finish previous file: {e}")
        
        return events

    async def _discover_newest_csv_file(self) -> Optional[str]:
        """Discover newest CSV file by searching all subdirectories under deathlogs"""
        try:
            async with connection_manager.get_connection(self.guild_id, self.server_config) as conn:
                if not conn:
                    return None
                
                sftp = await conn.start_sftp_client()
                killfeed_path = self._get_killfeed_path()
                
                all_csv_files = []
                
                # Search all subdirectories under deathlogs
                try:
                    entries = await sftp.listdir(killfeed_path)
                    
                    for entry in entries:
                        entry_path = f"{killfeed_path}{entry}/"
                        
                        try:
                            # Check if it's a directory
                            stat_info = await sftp.stat(entry_path)
                            if stat_info.permissions and (stat_info.permissions & 0o040000):  # Directory check
                                # Search for CSV files in this subdirectory
                                subdir_files = await sftp.listdir(entry_path)
                                for file in subdir_files:
                                    if file.endswith('.csv'):
                                        all_csv_files.append((file, entry))  # Store filename and subdirectory
                        except:
                            # Skip if can't access or not a directory
                            continue
                    
                    if not all_csv_files:
                        return None
                    
                    # Get newest file (max by filename which includes timestamp)
                    newest_file, subdir = max(all_csv_files, key=lambda x: x[0])
                    self._current_subdir = subdir  # Store for later use
                    logger.info(f"Found newest killfeed file: {newest_file} in {subdir}")
                    return newest_file
                    
                except Exception as e:
                    logger.warning(f"Failed to search killfeed directories under {killfeed_path}: {e}")
                    return None
                    
        except Exception as e:
            logger.error(f"Failed to discover killfeed files: {e}")
            return None
    
    async def _process_csv_file(self, filename: str, current_state: Optional[KillfeedState] = None) -> List[KillfeedEvent]:
        """Process CSV file from last known position"""
        events = []
        
        try:
            async with connection_manager.get_connection(self.guild_id, self.server_config) as conn:
                if not conn:
                    logger.error("No connection available for CSV processing")
                    return events
                
                sftp = await conn.start_sftp_client()
                killfeed_path = self._get_killfeed_path()
                
                # Use the subdirectory if we have one from discovery
                if self._current_subdir:
                    file_path = f"{killfeed_path}{self._current_subdir}/{filename}"
                else:
                    file_path = f"{killfeed_path}{filename}"
                
                logger.info(f"Reading CSV file: {file_path}")
                
                # Determine starting position
                start_line = 0
                start_byte = 0
                
                if current_state and current_state.last_file == filename:
                    start_line = current_state.last_line
                    start_byte = current_state.last_byte_position
                    logger.info(f"Resuming from line {start_line}, byte {start_byte}")
                else:
                    logger.info(f"Starting fresh processing from beginning")
                
                # Get file size for debugging
                try:
                    stat_info = await sftp.stat(file_path)
                    file_size = stat_info.size
                    logger.info(f"CSV file size: {file_size} bytes")
                except Exception as e:
                    logger.warning(f"Could not get file size: {e}")
                    file_size = 0
                
                # Read file content from starting position
                async with sftp.open(file_path, 'rb') as file:
                    await file.seek(start_byte)
                    content = await file.read()
                    
                logger.info(f"Read {len(content)} bytes from position {start_byte}")
                
                if not content:
                    logger.warning(f"No content read from CSV file (at position {start_byte})")
                    return events
                
                # Process lines
                lines = content.decode('utf-8', errors='ignore').splitlines()
                logger.info(f"Decoded {len(lines)} lines from content")
                
                # Show first few lines for debugging
                if lines:
                    logger.info("First 3 lines of CSV content:")
                    for i, line in enumerate(lines[:3]):
                        logger.info(f"  Line {i+1}: '{line}'")
                
                # Extract timestamp from filename for state management
                file_timestamp = self._extract_timestamp_from_filename(filename)
                
                valid_events_count = 0
                for i, line in enumerate(lines):
                    if self.cancelled:
                        break
                    
                    line = line.strip()
                    if not line:
                        continue
                    
                    event = self._parse_killfeed_line(line, start_line + i + 1, filename)
                    if event:
                        events.append(event)
                        valid_events_count += 1
                
                logger.info(f"Parsed {valid_events_count} valid events from {len(lines)} lines")
                
                # Update state after processing
                if self.state_manager and lines:
                    final_line = start_line + len(lines)
                    final_byte = start_byte + len(content)
                    
                    logger.info(f"Updating state: line {start_line} -> {final_line}, byte {start_byte} -> {final_byte}")
                    
                    await self.state_manager.update_killfeed_state(
                        self.guild_id, self.server_name,
                        filename, final_line, final_byte,
                        file_timestamp
                    )
                
        except Exception as e:
            logger.error(f"Failed to process CSV file {filename}: {e}")
            import traceback
            logger.error(traceback.format_exc())
        
        return events
    
    def _parse_killfeed_line(self, line: str, line_number: int, filename: str) -> Optional[KillfeedEvent]:
        """Parse a single killfeed CSV line using historical parser's exact logic"""
        try:
            # Historical parser uses semicolon delimiter with 9+ columns
            parts = line.split(';')
            
            if len(parts) < 9:
                return None
            
            # Extract fields (0-indexed) - CSV format: timestamp;killer;killer_id;victim;victim_id;weapon;distance;killer_platform;victim_platform;
            timestamp_str = parts[0].strip()
            killer = parts[1].strip()
            killer_id = parts[2].strip()
            victim = parts[3].strip() 
            victim_id = parts[4].strip()
            weapon = parts[5].strip()
            distance_str = parts[6].strip()
            killer_platform = parts[7].strip() if len(parts) > 7 else "Unknown"
            victim_platform = parts[8].strip() if len(parts) > 8 else "Unknown"
            
            # Parse timestamp
            event_timestamp = self._parse_timestamp(timestamp_str)
            if not event_timestamp:
                return None
                
            # Only skip events with blank killer names
            if not killer or not killer.strip():
                return None
            
            # Parse distance
            try:
                distance = int(float(distance_str))
            except (ValueError, TypeError):
                distance = 0
            
            # Create event for all deaths (PvP kills, suicides, falling deaths, etc.)
            return KillfeedEvent(
                timestamp=event_timestamp,
                killer=killer,
                victim=victim,
                weapon=weapon,
                distance=distance,
                killer_platform=killer_platform,
                victim_platform=victim_platform,
                raw_line=line,
                line_number=line_number,
                filename=filename
            )
            
        except Exception as e:
            logger.debug(f"Failed to parse killfeed line: {line} - {e}")
            return None
    
    def _parse_timestamp(self, timestamp_str: str) -> Optional[datetime]:
        """Parse timestamp from killfeed data"""
        try:
            # Try multiple timestamp formats
            formats = [
                '%Y.%m.%d-%H.%M.%S',  # CSV format: 2025.06.03-01.45.48
                '%Y-%m-%d %H:%M:%S',
                '%Y/%m/%d %H:%M:%S',
                '%d/%m/%Y %H:%M:%S',
                '%Y-%m-%d_%H-%M-%S'
            ]
            
            for fmt in formats:
                try:
                    return datetime.strptime(timestamp_str, fmt).replace(tzinfo=timezone.utc)
                except ValueError:
                    continue
            
            return None
            
        except Exception as e:
            logger.debug(f"Failed to parse timestamp {timestamp_str}: {e}")
            return None
    
    def _extract_timestamp_from_filename(self, filename: str) -> Optional[str]:
        """Extract timestamp from killfeed filename"""
        try:
            # Historical parser extracts timestamp from filename pattern
            # Example: killfeed_2024-06-03_22-15-30.csv
            import re
            
            timestamp_match = re.search(r'(\d{4}-\d{2}-\d{2}_\d{2}-\d{2}-\d{2})', filename)
            if timestamp_match:
                return timestamp_match.group(1)
            
            # Alternative pattern: killfeed_20240603_221530.csv  
            timestamp_match = re.search(r'(\d{8}_\d{6})', filename)
            if timestamp_match:
                return timestamp_match.group(1)
                
            return None
            
        except Exception as e:
            logger.debug(f"Failed to extract timestamp from filename {filename}: {e}")
            return None
    
    async def _deliver_killfeed_events(self, events: List[KillfeedEvent]):
        """Deliver killfeed events to Discord channels"""
        try:
            logger.info(f"Starting delivery of {len(events)} killfeed events")
            
            if not self.bot:
                logger.error("CRITICAL: No bot instance available for killfeed delivery")
                return
                
            # Use channel router for consistent channel resolution
            if self.channel_router:
                channel_id = await self.channel_router.get_channel_id(self.guild_id, self.server_name, 'killfeed')
            else:
                # Fallback to direct database lookup if no channel router
                guild_config = await self.bot.db_manager.get_guild(self.guild_id)
                if not guild_config:
                    logger.warning(f"No guild config found for guild {self.guild_id}")
                    return

                server_channels = guild_config.get('server_channels', {})
                channel_id = None
                
                # Try server-specific channel first
                if self.server_name in server_channels:
                    channel_id = server_channels[self.server_name].get('killfeed')
                
                # Fall back to default server channel
                if not channel_id and 'default' in server_channels:
                    channel_id = server_channels['default'].get('killfeed')
                
                # Legacy fallback
                if not channel_id:
                    legacy_channels = guild_config.get('channels', {})
                    channel_id = legacy_channels.get('killfeed')
            
            if not channel_id:
                logger.warning(f"No killfeed channel configured for guild {self.guild_id}")
                return
            
            # Get Discord channel
            channel = self.bot.get_channel(channel_id)
            if not channel:
                logger.warning(f"Killfeed channel {channel_id} not found")
                return
            
            # Send events to channel
            for event in events:
                try:
                    # Create killfeed embed with factory
                    embed, file = await self._create_killfeed_embed(event)
                    
                    # Send with embed and file attachment
                    await channel.send(embed=embed, file=file)
                    logger.info(f"✅ Delivered killfeed event: {event.killer} killed {event.victim} with {event.weapon}")
                    
                except Exception as e:
                    logger.error(f"Failed to deliver killfeed event: {e}")
                    
        except Exception as e:
            logger.error(f"Killfeed delivery failed: {e}")
    
    async def _create_killfeed_embed(self, event: KillfeedEvent):
        """Create Discord embed for killfeed event using EmbedFactory for consistent branding"""
        from bot.utils.embed_factory import EmbedFactory
        
        # Determine if this is a suicide event
        is_suicide = event.killer == event.victim
        
        # Prepare embed data for factory
        embed_data = {
            'killer': event.killer,
            'victim': event.victim,
            'weapon': event.weapon,
            'distance': event.distance,
            'killer_platform': event.killer_platform,
            'victim_platform': event.victim_platform,
            'server_name': self.server_name,
            'timestamp': event.timestamp,
            'is_suicide': is_suicide,
            'guild_id': self.guild_id
        }
        
        # Use factory to create branded embed with thumbnail
        embed, file = await EmbedFactory.build('killfeed', embed_data)
        
        return embed, file
    
    def cancel(self):
        """Cancel the processing"""
        self.cancelled = True

class MultiServerSimpleKillfeedProcessor:
    """Process killfeed for multiple servers using simple approach"""
    
    def __init__(self, guild_id: int, bot=None):
        self.guild_id = guild_id
        self.bot = bot
        self.active_processors = {}
    
    async def process_available_servers(self, server_configs: List[Dict[str, Any]], 
                                      progress_callback=None) -> Dict[str, Any]:
        """Process all available servers for killfeed updates"""
        results = {
            'processed_servers': 0,
            'skipped_servers': 0,
            'total_events': 0
        }
        
        for server_config in server_configs:
            server_name = server_config.get('name', 'Unknown')
            
            try:
                # Create processor for this server
                processor = SimpleKillfeedProcessor(self.guild_id, server_config, self.bot)
                self.active_processors[server_name] = processor
                
                # Process killfeed
                server_results = await processor.process_server_killfeed(progress_callback)
                
                if server_results.get('success'):
                    results['processed_servers'] += 1
                    results['total_events'] += server_results.get('events_processed', 0)
                else:
                    results['skipped_servers'] += 1
                
            except Exception as e:
                logger.error(f"Failed to process killfeed for {server_name}: {e}")
                results['skipped_servers'] += 1
            finally:
                # Cleanup
                if server_name in self.active_processors:
                    del self.active_processors[server_name]
        
        return results