"""
Scalable Killfeed Processor
Real-time incremental processing with state coordination and connection pooling
"""

import asyncio
import logging
import re
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any, Tuple
from bot.utils.connection_pool import connection_manager
from bot.utils.shared_parser_state import get_shared_state_manager, ParserState
from dataclasses import dataclass

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

class ScalableKillfeedProcessor:
    """Manages incremental killfeed processing for a single server with state coordination"""
    
    def __init__(self, guild_id: int, server_config: Dict[str, Any]):
        self.guild_id = guild_id
        self.server_config = server_config
        self.server_name = server_config.get('name', server_config.get('server_name', 'default'))
        self.cancelled = False
        self.state_manager = get_shared_state_manager()
    
    def _get_killfeed_path(self) -> str:
        """Get the killfeed path for this server"""
        if 'killfeed_path' in self.server_config:
            return self.server_config['killfeed_path']
        
        # Build dynamic path based on server configuration
        host = self.server_config.get('host', 'unknown')
        server_id = self.server_config.get('_id', self.server_config.get('server_id', 'unknown'))
        return f"./{host}_{server_id}/actual1/deathlogs/"
        
    async def process_server_killfeed(self, progress_callback=None) -> Dict[str, Any]:
        """Main entry point for incremental killfeed processing"""
        results = {
            'success': False,
            'server_name': self.server_name,
            'events_processed': 0,
            'new_file_detected': False,
            'state_updated': False,
            'error': None
        }
        
        try:
            # Register session to prevent conflicts
            if self.state_manager and not await self.state_manager.register_session(self.guild_id, self.server_name, 'killfeed'):
                results['error'] = 'Server currently under historical processing'
                return results
            
            # Get current parser state
            current_state = None
            if self.state_manager:
                current_state = await self.state_manager.get_parser_state(self.guild_id, self.server_name)
            
            # Discover current newest file
            newest_file = await self._discover_newest_file()
            if not newest_file:
                results['error'] = 'No killfeed files found'
                return results
            
            file_timestamp = self._extract_timestamp_from_filename(newest_file)
            
            # Determine processing strategy
            if current_state and current_state.last_file:
                if newest_file != current_state.last_file:
                    # New file detected - process gap then switch
                    results['new_file_detected'] = True
                    await self._process_file_transition(current_state, newest_file, progress_callback)
                else:
                    # Continue with same file
                    await self._process_incremental_update(current_state, newest_file, progress_callback)
            else:
                # Fresh start - process from beginning
                await self._process_fresh_start(newest_file, file_timestamp or "", progress_callback)
            
            results['success'] = True
            results['state_updated'] = True
            
        except Exception as e:
            logger.error(f"Killfeed processing failed for {self.server_name}: {e}")
            results['error'] = str(e)
        
        finally:
            # Unregister session
            if self.state_manager:
                await self.state_manager.unregister_session(self.guild_id, self.server_name, 'killfeed')
        
        return results
    
    async def _discover_newest_file(self) -> Optional[str]:
        """Find the newest timestamped killfeed file"""
        try:
            async with connection_manager.get_connection(self.guild_id, self.server_config) as conn:
                if not conn:
                    logger.warning(f"No connection available for killfeed discovery on {self.server_name}")
                    return None
                
                sftp = await conn.start_sftp_client()
                killfeed_path = self._get_killfeed_path()
                logger.info(f"Killfeed discovery: Looking for CSV files in {killfeed_path}")
                
                # Use glob pattern matching like historical parser for recursive discovery
                try:
                    # Use recursive glob pattern to find CSV files in subdirectories
                    pattern = f"{killfeed_path}**/*.csv"
                    logger.info(f"Killfeed discovery using glob pattern: {pattern}")
                    
                    paths = []
                    file_list = []
                    
                    try:
                        # Use glob for recursive file discovery (same as historical parser)
                        paths = await sftp.glob(pattern)
                        logger.info(f"Glob discovery: Found {len(paths)} CSV files")
                        
                        for path in paths:
                            # Extract just the filename portion for compatibility
                            import os
                            filename = os.path.basename(str(path))
                            file_list.append(filename)
                            logger.info(f"Found CSV file: {filename} (full path: {path})")
                            
                    except Exception as e:
                        logger.warning(f"Glob pattern failed, falling back to directory listing: {e}")
                        paths = []  # Clear paths since glob failed
                        
                        # Fallback to directory listing if glob fails
                        try:
                            all_files = await sftp.listdir(killfeed_path)
                            file_list = [f for f in all_files if f.endswith('.csv')]
                            logger.info(f"Fallback directory listing: Found {len(file_list)} CSV files in {killfeed_path}: {file_list}")
                            
                            # If no CSV files found, check for other file types that might contain killfeed data
                            if not file_list:
                                other_files = [f for f in all_files if not f.startswith('.')]
                                logger.warning(f"No CSV files found. Other files present: {other_files}")
                                
                        except Exception as e2:
                            logger.error(f"Both glob and directory listing failed: {e2}")
                            file_list = []
                except Exception as e:
                    logger.warning(f"Could not list killfeed directory {killfeed_path}: {e}")
                    return None
                file_attrs = []
                
                # If using glob results, we have full paths already
                if paths:
                    for full_path in paths:
                        try:
                            attrs = await sftp.stat(full_path)
                            import os
                            filename = os.path.basename(str(full_path))
                            file_info = type('FileInfo', (), {
                                'filename': filename,
                                'full_path': str(full_path),  # Store full path for later use
                                'size': getattr(attrs, 'size', 0),
                                'mtime': getattr(attrs, 'mtime', 0)
                            })()
                            file_attrs.append(file_info)
                        except Exception as e:
                            logger.warning(f"Failed to get stats for {full_path}: {e}")
                else:
                    # If using directory listing, construct paths manually
                    for filename in file_list:
                        if filename.endswith('.csv'):
                            try:
                                file_path = f"{killfeed_path.rstrip('/')}/{filename}"
                                attrs = await sftp.stat(file_path)
                                file_info = type('FileInfo', (), {
                                    'filename': filename,
                                    'size': getattr(attrs, 'size', 0),
                                    'mtime': getattr(attrs, 'mtime', 0)
                                })()
                                file_attrs.append(file_info)
                            except Exception as e:
                                logger.warning(f"Failed to get stats for {filename}: {e}")
                csv_files = []
                
                for attr in file_attrs:
                    if attr.filename.endswith('.csv'):
                        # Extract timestamp from filename
                        timestamp = self._extract_timestamp_from_filename(attr.filename)
                        if timestamp and timestamp.strip():
                            # Store both filename and full path for later use
                            full_path = getattr(attr, 'full_path', None)
                            csv_files.append((attr.filename, timestamp, full_path))
                
                if csv_files:
                    # Sort by timestamp and return newest filename and full path
                    csv_files.sort(key=lambda x: x[1], reverse=True)
                    newest_file, _, newest_full_path = csv_files[0]
                    
                    # Store the full path for later use in processing
                    self._newest_file_full_path = newest_full_path
                    return newest_file
                
                return None
                
        except Exception as e:
            logger.error(f"Failed to discover newest file for {self.server_name}: {e}")
            return None
    
    def _extract_timestamp_from_filename(self, filename: str) -> Optional[str]:
        """Extract timestamp from killfeed filename"""
        # Match patterns like: 2025.06.03-00.00.00.csv (current format)
        current_pattern = r'(\d{4}\.\d{2}\.\d{2}-\d{2}\.\d{2}\.\d{2})'
        match = re.search(current_pattern, filename)
        if match:
            return match.group(1)
        
        # Fallback to legacy pattern: killfeed_2024-06-02_21-45-30.csv
        legacy_pattern = r'(\d{4}-\d{2}-\d{2}_\d{2}-\d{2}-\d{2})'
        match = re.search(legacy_pattern, filename)
        return match.group(1) if match else None
    
    async def _process_file_transition(self, current_state: ParserState, newest_file: str, progress_callback=None):
        """Process transition from old file to new file"""
        # First, check previous file for any missed lines
        if current_state.last_file and current_state.last_file != newest_file:
            await self._process_gap_from_previous_file(current_state, progress_callback)
        
        # Then start processing new file from beginning
        file_timestamp = self._extract_timestamp_from_filename(newest_file)
        if file_timestamp is None:
            file_timestamp = "unknown"
        await self._process_fresh_start(newest_file, file_timestamp, progress_callback)
    
    async def _process_gap_from_previous_file(self, current_state: ParserState, progress_callback=None):
        """Check previous file for any lines missed since last processing"""
        try:
            async with connection_manager.get_connection(self.guild_id, self.server_config) as conn:
                if not conn:
                    return
                
                sftp = await conn.start_sftp_client()
                
                # For gap processing, construct the path properly for the last known file
                killfeed_path = self._get_killfeed_path()
                file_path = f"{killfeed_path.rstrip('/')}/world_0/{current_state.last_file}"
                
                # Read from last known position to end of file
                async with sftp.open(file_path, 'rb') as file:
                    await file.seek(current_state.last_byte_position)
                    remaining_content = await file.read()
                    
                    if remaining_content:
                        lines = remaining_content.decode('utf-8', errors='ignore').splitlines()
                        await self._process_killfeed_lines(lines, current_state.last_line, current_state.last_file)
                        
                        # Update state with final position of previous file
                        final_position = current_state.last_byte_position + len(remaining_content)
                        final_line = current_state.last_line + len(lines)
                        
                        if self.state_manager:
                            await self.state_manager.update_parser_state(
                                self.guild_id, self.server_name,
                                current_state.last_file, final_line, final_position,
                                'killfeed', current_state.file_timestamp
                            )
                
        except Exception as e:
            logger.error(f"Failed to process gap from previous file: {e}")
    
    async def _process_incremental_update(self, current_state: ParserState, current_file: str, progress_callback=None):
        """Process incremental updates from current file"""
        try:
            async with connection_manager.get_connection(self.guild_id, self.server_config) as conn:
                if not conn:
                    return
                
                sftp = await conn.start_sftp_client()
                killfeed_path = self._get_killfeed_path()
                file_path = f"{killfeed_path.rstrip('/')}/{current_file}"
                
                # Get current file size
                file_attrs = await sftp.stat(file_path)
                current_size = file_attrs.size
                
                if current_size and current_size > current_state.last_byte_position:
                    # File has grown - read new content
                    async with sftp.open(file_path, 'rb') as file:
                        await file.seek(current_state.last_byte_position)
                        new_content = await file.read()
                        
                        if new_content:
                            lines = new_content.decode('utf-8', errors='ignore').splitlines()
                            await self._process_killfeed_lines(lines, current_state.last_line, current_file)
                            
                            # Update state
                            new_position = current_state.last_byte_position + len(new_content)
                            new_line = current_state.last_line + len(lines)
                            
                            if self.state_manager:
                                await self.state_manager.update_parser_state(
                                    self.guild_id, self.server_name,
                                    current_file, new_line, new_position,
                                    'killfeed', current_state.file_timestamp
                                )
                
        except Exception as e:
            logger.error(f"Failed to process incremental update: {e}")
    
    async def _process_fresh_start(self, newest_file: str, file_timestamp: str, progress_callback=None):
        """Process new file from the beginning"""
        try:
            async with connection_manager.get_connection(self.guild_id, self.server_config) as conn:
                if not conn:
                    return
                
                sftp = await conn.start_sftp_client()
                
                # Use stored full path if available, otherwise construct path
                if hasattr(self, '_newest_file_full_path') and self._newest_file_full_path:
                    file_path = self._newest_file_full_path
                else:
                    killfeed_path = self._get_killfeed_path()
                    file_path = f"{killfeed_path.rstrip('/')}/{newest_file}"
                
                # Read entire file content
                async with sftp.open(file_path, 'rb') as file:
                    content = await file.read()
                    
                    if content:
                        lines = content.decode('utf-8', errors='ignore').splitlines()
                        await self._process_killfeed_lines(lines, 0, newest_file)
                        
                        # Update state
                        if self.state_manager:
                            await self.state_manager.update_parser_state(
                                self.guild_id, self.server_name,
                                newest_file, len(lines), len(content),
                                'killfeed', file_timestamp
                            )
                
        except Exception as e:
            logger.error(f"Failed to process fresh start: {e}")
    
    async def _process_killfeed_lines(self, lines: List[str], start_line_number: int, filename: str):
        """Process killfeed lines and extract events"""
        events = []
        
        for i, line in enumerate(lines):
            if self.cancelled:
                break
                
            line = line.strip()
            if not line:
                continue
                
            # Parse killfeed line (no header - starts with kill data immediately)
            event = self._parse_killfeed_line(line, start_line_number + i, filename)
            if event:
                events.append(event)
        
        # Process events if any found
        if events:
            await self._deliver_killfeed_events(events)
    
    def _parse_killfeed_line(self, line: str, line_number: int, filename: str) -> Optional[KillfeedEvent]:
        """Parse a single killfeed CSV line"""
        try:
            # CSV format: timestamp,killer,victim,weapon,distance,killer_platform,victim_platform
            parts = [part.strip().strip('"') for part in line.split(',')]
            
            if len(parts) >= 7:
                timestamp_str = parts[0]
                timestamp = self._parse_timestamp(timestamp_str)
                
                if timestamp:
                    return KillfeedEvent(
                        timestamp=timestamp,
                        killer=parts[1],
                        victim=parts[2],
                        weapon=parts[3],
                        distance=int(parts[4]) if parts[4].isdigit() else 0,
                        killer_platform=parts[5],
                        victim_platform=parts[6],
                        raw_line=line,
                        line_number=line_number
                    )
            
        except Exception as e:
            logger.debug(f"Failed to parse killfeed line {line_number}: {e}")
        
        return None
    
    def _parse_timestamp(self, timestamp_str: str) -> Optional[datetime]:
        """Parse timestamp from killfeed data"""
        formats = [
            '%Y-%m-%d %H:%M:%S',
            '%Y-%m-%d_%H-%M-%S',
            '%m/%d/%Y %H:%M:%S',
            '%d/%m/%Y %H:%M:%S'
        ]
        
        for fmt in formats:
            try:
                return datetime.strptime(timestamp_str, fmt).replace(tzinfo=timezone.utc)
            except ValueError:
                continue
        
        return None
    
    async def _deliver_killfeed_events(self, events: List[KillfeedEvent]):
        """Deliver killfeed events to Discord channels with proper routing"""
        try:
            if not events:
                return
                
            logger.info(f"Delivering {len(events)} killfeed events for {self.server_name}")
            
            # Get bot instance from the first processor in the hierarchy
            bot = None
            if hasattr(self, 'bot') and self.bot:
                bot = self.bot
            elif self.state_manager and hasattr(self.state_manager, 'bot') and self.state_manager.bot:
                bot = self.state_manager.bot
            
            if not bot or not hasattr(bot, 'embed_factory') or not hasattr(bot, 'channel_router'):
                logger.warning(f"Bot components not available for killfeed delivery")
                return
            
            # Process each kill event
            for event in events[:10]:  # Limit to prevent spam
                try:
                    # Determine if this is a suicide
                    is_suicide = event.killer.lower() == event.victim.lower()
                    
                    # Normalize suicide weapons
                    weapon = event.weapon
                    if is_suicide and weapon.lower() in ['suicide_by_relocation', 'relocation']:
                        weapon = 'Menu Suicide'
                    
                    # Create killfeed embed data
                    embed_data = {
                        'guild_id': self.guild_id,
                        'killer': event.killer,
                        'victim': event.victim,
                        'weapon': weapon,
                        'distance': event.distance,
                        'timestamp': event.timestamp,
                        'is_suicide': is_suicide,
                        'killer_platform': getattr(event, 'killer_platform', 'PC'),
                        'victim_platform': getattr(event, 'victim_platform', 'PC')
                    }
                    
                    # Build embed using EmbedFactory
                    embed, file_attachment = await bot.embed_factory.build('killfeed', embed_data)
                    
                    if embed:
                        # Send to killfeed channel with server-specific routing
                        success = await bot.channel_router.send_embed_to_channel(
                            guild_id=self.guild_id,
                            server_id=self.server_name,
                            channel_type='killfeed',
                            embed=embed,
                            file=file_attachment
                        )
                        
                        if success:
                            logger.debug(f"Sent killfeed embed: {event.killer} -> {event.victim}")
                        else:
                            logger.warning(f"Failed to send killfeed embed to channel")
                    
                    # Record kill in database for stats
                    if hasattr(bot, 'db_manager') and bot.db_manager:
                        await bot.db_manager.record_kill(
                            guild_id=self.guild_id,
                            killer_name=event.killer,
                            victim_name=event.victim,
                            weapon=weapon,
                            server_name=self.server_name,
                            timestamp=event.timestamp,
                            distance=event.distance
                        )
                
                except Exception as event_error:
                    logger.error(f"Failed to process individual kill event: {event_error}")
            
        except Exception as e:
            logger.error(f"Failed to deliver killfeed events: {e}")
    
    def cancel(self):
        """Cancel the processing"""
        self.cancelled = True

class MultiServerKillfeedProcessor:
    """Manages parallel killfeed processing across multiple servers with conflict avoidance"""
    
    def __init__(self, guild_id: int):
        self.guild_id = guild_id
        self.processors: Dict[str, ScalableKillfeedProcessor] = {}
        self.state_manager = get_shared_state_manager()
    
    async def process_available_servers(self, server_configs: List[Dict[str, Any]], 
                                      progress_callback=None) -> Dict[str, Any]:
        """Process all available servers for killfeed updates"""
        # Filter out servers under historical processing
        available_servers = await self.state_manager.get_available_servers_for_killfeed(server_configs)
        
        if not available_servers:
            return {
                'success': True,
                'total_servers': len(server_configs),
                'available_servers': 0,
                'processed_servers': 0,
                'skipped_servers': len(server_configs)
            }
        
        # Process available servers in parallel
        tasks = []
        for server_config in available_servers:
            processor = ScalableKillfeedProcessor(self.guild_id, server_config)
            self.processors[server_config.get('name', 'default')] = processor
            tasks.append(processor.process_server_killfeed(progress_callback))
        
        # Execute all tasks
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Compile summary
        successful = sum(1 for result in results if isinstance(result, dict) and result.get('success'))
        
        return {
            'success': True,
            'total_servers': len(server_configs),
            'available_servers': len(available_servers),
            'processed_servers': successful,
            'skipped_servers': len(server_configs) - len(available_servers),
            'results': results
        }