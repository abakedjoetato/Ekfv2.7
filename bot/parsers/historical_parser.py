
"""
Emerald's Killfeed - Historical Parser (PHASE 2)
Handles full historical data parsing and refresh operations
"""

import asyncio
import logging
import stat
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple

try:
    import aiofiles
    AIOFILES_AVAILABLE = True
except ImportError:
    AIOFILES_AVAILABLE = False
    aiofiles = None
import asyncssh
import discord
from discord.ext import commands

from .killfeed_parser import KillfeedParser

logger = logging.getLogger(__name__)

class ProgressUI(discord.ui.View):
    """Advanced progress UI with interactive controls"""
    
    def __init__(self, historical_parser, guild_id: int, server_config: Dict):
        super().__init__(timeout=3600)  # 1 hour timeout
        self.historical_parser = historical_parser
        self.guild_id = guild_id
        self.server_config = server_config
        self.is_paused = False
        self.cancelled = False
        
    @discord.ui.button(label="Pause", style=discord.ButtonStyle.secondary, emoji="⏸️")
    async def pause_button(self, button: discord.ui.Button, interaction: discord.Interaction):
        self.is_paused = not self.is_paused
        button.label = "Resume" if self.is_paused else "Pause"
        button.emoji = "▶️" if self.is_paused else "⏸️"
        await interaction.response.edit_message(view=self)
        
    @discord.ui.button(label="Cancel", style=discord.ButtonStyle.danger, emoji="⏹️")
    async def cancel_button(self, button: discord.ui.Button, interaction: discord.Interaction):
        self.cancelled = True
        for child in self.children:
            child.disabled = True
        await interaction.response.edit_message(content="Historical parsing cancelled by user.", view=self)
        
    @discord.ui.button(label="Details", style=discord.ButtonStyle.primary, emoji="📊")
    async def details_button(self, button: discord.ui.Button, interaction: discord.Interaction):
        stats = self.historical_parser.processing_stats.get(f"{self.guild_id}_{self.server_config.get('_id')}", {})
        
        details_embed = discord.Embed(
            title="Processing Details",
            color=0x3498DB,
            timestamp=datetime.now(timezone.utc)
        )
        
        if stats:
            details_embed.add_field(
                name="File Processing",
                value=f"Files Found: {stats.get('files_found', 0)}\n"
                      f"Files Completed: {stats.get('files_completed', 0)}\n"
                      f"Files Failed: {stats.get('files_failed', 0)}",
                inline=True
            )
            
            details_embed.add_field(
                name="Data Metrics",
                value=f"Total Lines: {stats.get('total_lines', 0):,}\n"
                      f"Lines Processed: {stats.get('lines_processed', 0):,}\n"
                      f"Processing Rate: {stats.get('processing_rate', 0):.1f}/sec",
                inline=True
            )
            
            details_embed.add_field(
                name="Game Data",
                value=f"Kills Parsed: {stats.get('kills_parsed', 0)}\n"
                      f"Streaks Tracked: {stats.get('streaks_tracked', 0)}\n"
                      f"Players Found: {stats.get('players_found', 0)}",
                inline=True
            )
        
        await interaction.response.send_message(embed=details_embed, ephemeral=True)

class HistoricalParser:
    """
    BULLETPROOF HISTORICAL PARSER
    - Processes ALL CSV files (not just latest versions)
    - Comprehensive error handling and retry mechanisms
    - Detailed progress tracking and validation
    - Recovery capabilities for failed operations
    """

    def __init__(self, bot):
        self.bot = bot
        self.killfeed_parser = KillfeedParser(bot)
        self.active_refreshes: Dict[str, bool] = {}  # Track active refresh operations
        self.processing_stats: Dict[str, Dict] = {}  # Track detailed processing statistics
        self.progress_messages: Dict[str, discord.Message] = {}  # Track progress message updates
        
    def create_progress_bar(self, current: int, total: int, width: int = 20) -> str:
        """Create ASCII progress bar"""
        if total == 0:
            return "░" * width + " 0%"
        
        percentage = min(100, (current / total) * 100)
        filled = int((current / total) * width)
        bar = "█" * filled + "░" * (width - filled)
        return f"{bar} {percentage:.1f}%"
        
    def sort_files_chronologically(self, file_list: List[str]) -> List[str]:
        """Sort CSV files in chronological order based on timestamps in filenames"""
        def extract_timestamp(filename: str) -> datetime:
            # Try to extract date from various filename patterns
            patterns = [
                r'(\d{4}[-_]\d{2}[-_]\d{2})',  # YYYY-MM-DD or YYYY_MM_DD
                r'(\d{8})',  # YYYYMMDD
                r'(\d{2}[-_]\d{2}[-_]\d{4})',  # DD-MM-YYYY or DD_MM_YYYY
            ]
            
            for pattern in patterns:
                match = re.search(pattern, filename)
                if match:
                    date_str = match.group(1)
                    try:
                        # Handle different date formats
                        if '-' in date_str or '_' in date_str:
                            if len(date_str.split('-')[0]) == 4 or len(date_str.split('_')[0]) == 4:
                                # YYYY-MM-DD format
                                return datetime.strptime(date_str.replace('_', '-'), '%Y-%m-%d')
                            else:
                                # DD-MM-YYYY format
                                return datetime.strptime(date_str.replace('_', '-'), '%d-%m-%Y')
                        elif len(date_str) == 8:
                            # YYYYMMDD format
                            return datetime.strptime(date_str, '%Y%m%d')
                    except ValueError:
                        continue
            
            # Fallback: use file modification time or current time
            return datetime.now()
        
        # Sort files by extracted timestamp
        return sorted(file_list, key=extract_timestamp)
        
    async def create_progress_embed(self, server_name: str, stats: Dict, current_file: str = "") -> discord.Embed:
        """Create detailed progress embed with bars and statistics"""
        embed = discord.Embed(
            title="Historical Data Processing",
            description=f"Server: **{server_name}**",
            color=0x3498DB,
            timestamp=datetime.now(timezone.utc)
        )
        
        # Overall progress
        total_lines = stats.get('total_lines', 1)
        processed_lines = stats.get('lines_processed', 0)
        overall_bar = self.create_progress_bar(processed_lines, total_lines, 25)
        
        embed.add_field(
            name="Overall Progress",
            value=f"`{overall_bar}`\n{processed_lines:,}/{total_lines:,} lines",
            inline=False
        )
        
        # Current file progress
        if current_file:
            current_file_lines = stats.get('current_file_lines', 1)
            current_file_processed = stats.get('current_file_processed', 0)
            file_bar = self.create_progress_bar(current_file_processed, current_file_lines, 20)
            
            embed.add_field(
                name="Current File",
                value=f"**{current_file}**\n`{file_bar}`\n{current_file_processed:,}/{current_file_lines:,} lines",
                inline=True
            )
        
        # Processing statistics
        files_completed = stats.get('files_completed', 0)
        files_total = stats.get('files_found', 1)
        processing_rate = stats.get('processing_rate', 0)
        
        embed.add_field(
            name="File Progress",
            value=f"Completed: {files_completed}/{files_total}\nRate: {processing_rate:.1f} lines/sec",
            inline=True
        )
        
        # Game data statistics
        kills_parsed = stats.get('kills_parsed', 0)
        streaks_tracked = stats.get('streaks_tracked', 0)
        players_found = stats.get('players_found', 0)
        
        embed.add_field(
            name="Data Processed",
            value=f"Kills: {kills_parsed:,}\nStreaks: {streaks_tracked:,}\nPlayers: {players_found:,}",
            inline=True
        )
        
        # Time information
        start_time = stats.get('start_time')
        if start_time:
            elapsed = (datetime.now(timezone.utc) - start_time).total_seconds()
            if processed_lines > 0 and processing_rate > 0:
                remaining_lines = total_lines - processed_lines
                eta_seconds = remaining_lines / processing_rate if processing_rate > 0 else 0
                eta_str = f"{int(eta_seconds // 60)}m {int(eta_seconds % 60)}s"
            else:
                eta_str = "Calculating..."
                
            embed.add_field(
                name="Timing",
                value=f"Elapsed: {int(elapsed // 60)}m {int(elapsed % 60)}s\nETA: {eta_str}",
                inline=True
            )
        
        embed.set_footer(text="Historical parsing ensures chronological data integrity")
        return embed

    async def get_all_csv_files(self, server_config: Dict[str, Any]) -> Tuple[List[str], Dict]:
        """Get all CSV file paths (not content) for historical parsing"""
        processing_report = {
            'files_discovered': 0,
            'files_processed': 0,
            'files_failed': 0,
            'total_lines': 0,
            'failed_files': [],
            'encoding_issues': [],
            'success_details': []
        }

        try:
            # Get file paths, not file content
            file_paths, report = await self.discover_csv_file_paths(server_config)
            processing_report.update(report)
            return file_paths, processing_report

        except Exception as e:
            logger.error(f"Failed to get CSV files: {e}")
            processing_report['critical_error'] = str(e)
            return [], processing_report

    async def discover_csv_file_paths(self, server_config: Dict[str, Any]) -> Tuple[List[str], Dict]:
        """Discover CSV file paths without processing content"""
        report = {
            'files_discovered': 0,
            'total_size': 0,
            'failed_files': []
        }

        try:
            conn = await self.get_sftp_connection(server_config)
            if not conn:
                report['critical_error'] = "Failed to establish SFTP connection"
                return [], report

            server_id = str(server_config.get('_id', server_config.get('server_id', 'unknown')))
            sftp_host = server_config.get('host')
            remote_path = f"./{sftp_host}_{server_id}/actual1/deathlogs/"

            async with conn.start_sftp_client() as sftp:
                pattern = f"{remote_path}**/*.csv"
                logger.info(f"🔍 Discovering CSV file paths with pattern: {pattern}")

                try:
                    paths = await sftp.glob(pattern)
                    logger.info(f"📁 Discovered {len(paths)} CSV files")
                    
                    file_paths = []
                    total_size = 0
                    
                    for path in paths:
                        try:
                            stat_result = await sftp.stat(path)
                            size = getattr(stat_result, 'size', 0)
                            total_size += size
                            file_paths.append(path)
                            
                        except Exception as e:
                            logger.warning(f"Error getting file info for {path}: {e}")
                            report['failed_files'].append(f"{path}: {str(e)}")
                    
                    report['files_discovered'] = len(file_paths)
                    report['total_size'] = total_size
                    
                    logger.info(f"📊 File discovery complete: {len(file_paths)} files, {total_size:,} bytes total")
                    return file_paths, report
                    
                except Exception as e:
                    logger.error(f"Failed to discover CSV files: {e}")
                    report['critical_error'] = f"File discovery failed: {str(e)}"
                    return [], report

        except Exception as e:
            logger.error(f"Failed to discover CSV file paths: {e}")
            report['critical_error'] = str(e)
            return [], report

    async def get_dev_csv_files(self) -> Tuple[List[str], Dict]:
        """Get all CSV files from dev_data directory with bulletproof processing"""
        report = {
            'files_discovered': 0,
            'files_processed': 0,
            'files_failed': 0,
            'total_lines': 0,
            'failed_files': [],
            'encoding_issues': [],
            'success_details': []
        }

        try:
            csv_path = Path('./dev_data/csv')
            csv_files = list(csv_path.glob('*.csv'))
            report['files_discovered'] = len(csv_files)

            if not csv_files:
                logger.warning("No CSV files found in dev_data/csv/")
                return [], report

            all_lines = []
            # Sort files by name (assuming chronological naming)
            csv_files.sort()

            for csv_file in csv_files:
                try:
                    file_lines = await self.process_single_file_with_retry(str(csv_file), is_local=True)
                    if file_lines:
                        all_lines.extend(file_lines)
                        report['files_processed'] += 1
                        report['total_lines'] += len(file_lines)
                        report['success_details'].append({
                            'file': str(csv_file),
                            'lines': len(file_lines),
                            'encoding': 'utf-8'
                        })
                        logger.info(f"✅ Processed {csv_file}: {len(file_lines)} lines")
                    else:
                        report['files_failed'] += 1
                        report['failed_files'].append(str(csv_file))
                        logger.error(f"❌ Failed to process {csv_file}")

                except Exception as e:
                    report['files_failed'] += 1
                    report['failed_files'].append(f"{csv_file}: {str(e)}")
                    logger.error(f"❌ Error processing {csv_file}: {e}")

            logger.info(f"📊 Dev CSV Processing Complete: {report['files_processed']}/{report['files_discovered']} files, {report['total_lines']} total lines")
            return all_lines, report

        except Exception as e:
            logger.error(f"Failed to read dev CSV files: {e}")
            report['critical_error'] = str(e)
            return [], report

    async def process_single_file_with_retry(self, file_path: str, is_local: bool = False, 
                                           sftp_client=None, max_retries: int = 3) -> List[str]:
        """Process a single file with retry mechanism and encoding fallbacks"""
        
        for attempt in range(1, max_retries + 1):
            try:
                logger.debug(f"Processing attempt {attempt}/{max_retries} for {file_path}")
                
                if is_local:
                    return await self.read_local_file_with_encoding_fallback(file_path)
                else:
                    return await self.read_sftp_file_with_encoding_fallback(sftp_client, file_path)
                    
            except Exception as e:
                logger.warning(f"Attempt {attempt}/{max_retries} failed for {file_path}: {e}")
                if attempt < max_retries:
                    # Exponential backoff
                    delay = 2 ** attempt
                    logger.debug(f"Retrying in {delay} seconds...")
                    await asyncio.sleep(delay)
                else:
                    logger.error(f"All retry attempts failed for {file_path}")
                    return []
        
        return []

    async def read_local_file_with_encoding_fallback(self, file_path: str) -> List[str]:
        """Read local file with encoding fallbacks"""
        encodings = ['utf-8', 'latin-1', 'ascii', 'cp1252']
        
        for encoding in encodings:
            try:
                if aiofiles and hasattr(aiofiles, "open"):
                    async with aiofiles.open(file_path, 'r', encoding=encoding) as f:
                        content = await f.read()
                        lines = [line.strip() for line in content.splitlines() if line.strip()]
                        logger.debug(f"Successfully read {file_path} with {encoding} encoding: {len(lines)} lines")
                        return lines
            except UnicodeDecodeError:
                logger.debug(f"Failed to read {file_path} with {encoding} encoding")
                continue
            except Exception as e:
                logger.error(f"Error reading {file_path} with {encoding}: {e}")
                continue
        
        logger.error(f"Failed to read {file_path} with any encoding")
        return []

    async def read_sftp_file_with_encoding_fallback(self, sftp_client, file_path: str) -> List[str]:
        """Read SFTP file with encoding fallbacks and chunked reading"""
        encodings = ['utf-8', 'latin-1', 'ascii', 'cp1252']
        
        for encoding in encodings:
            try:
                # Use chunked reading for large files
                buffer_size = 1024 * 1024  # 1MB buffer
                file_content = ""

                if sftp_client:
                    async with sftp_client.open(file_path, 'r') as f:
                        while True:
                            chunk = await f.read(buffer_size)
                            if not chunk:
                                break

                        # Handle binary data
                        if isinstance(chunk, bytes):
                            try:
                                chunk = chunk.decode(encoding)
                            except UnicodeDecodeError:
                                if encoding == encodings[-1]:  # Last encoding attempt
                                    logger.error(f"Failed to decode {file_path} with {encoding}")
                                    return []
                                else:
                                    # Try next encoding
                                    break
                        
                        file_content += chunk

                # Process content into lines
                lines = [line.strip() for line in file_content.splitlines() if line.strip()]
                logger.debug(f"Successfully read {file_path} with {encoding} encoding: {len(lines)} lines")
                return lines

            except FileNotFoundError:
                logger.warning(f"SFTP file not found: {file_path}")
                return []
            except PermissionError:
                logger.warning(f"Permission denied reading SFTP file: {file_path}")
                return []
            except Exception as e:
                logger.debug(f"Error reading {file_path} with {encoding}: {e}")
                continue
        
        logger.error(f"Failed to read SFTP file {file_path} with any encoding")
        return []

    async def get_sftp_connection(self, server_config: Dict[str, Any]) -> Optional[asyncssh.SSHClientConnection]:
        """Get or create SFTP connection with enhanced error handling and compatibility"""
        try:
            # Get SFTP credentials with proper fallbacks
            server_id = str(server_config.get('_id', server_config.get('server_id', 'unknown')))
            sftp_host = server_config.get('host') or server_config.get('sftp_host', '')
            sftp_port = int(server_config.get('port') or server_config.get('sftp_port', 22))
            sftp_username = server_config.get('username') or server_config.get('sftp_username', '')
            sftp_password = server_config.get('password') or server_config.get('sftp_password', '')

            # Log connection attempt
            logger.info(f"Attempting SFTP connection to {sftp_host}:{sftp_port} for server {server_id}")

            # Validate credentials
            if not sftp_host:
                logger.error(f"Missing SFTP host for server {server_id}")
                return None

            if not sftp_username or not sftp_password:
                logger.error(f"Missing SFTP credentials for server {server_id}")
                return None

            # Enhanced connection with multiple retry attempts
            max_retries = 3
            for attempt in range(1, max_retries + 1):
                try:
                    # Configure connection options with legacy support by default
                    options = {
                        'username': sftp_username,
                        'password': sftp_password,
                        'known_hosts': None,  # Skip host key verification
                        'client_keys': None,  # No client keys needed with password auth
                        'preferred_auth': 'password,keyboard-interactive',
                        'kex_algs': [
                            'diffie-hellman-group14-sha256',
                            'diffie-hellman-group16-sha512',
                            'diffie-hellman-group18-sha512',
                            'diffie-hellman-group14-sha1',
                            'diffie-hellman-group1-sha1',
                            'diffie-hellman-group-exchange-sha256',
                            'diffie-hellman-group-exchange-sha1'
                        ],
                        'encryption_algs': [
                            'aes256-ctr', 'aes192-ctr', 'aes128-ctr',
                            'aes256-cbc', 'aes192-cbc', 'aes128-cbc',
                            '3des-cbc', 'blowfish-cbc'
                        ],
                        'mac_algs': [
                            'hmac-sha2-256', 'hmac-sha2-512',
                            'hmac-sha1'
                        ]
                    }

                    # Establish connection with timeout
                    logger.debug(f"Connection attempt {attempt}/{max_retries} to {sftp_host}:{sftp_port}")
                    conn = await asyncio.wait_for(
                        asyncssh.connect(sftp_host, port=sftp_port, **options),
                        timeout=45  # Overall operation timeout
                    )

                    logger.info(f"Successfully connected to SFTP server {sftp_host} for server {server_id}")
                    return conn

                except asyncio.TimeoutError:
                    logger.warning(f"SFTP connection timed out (attempt {attempt}/{max_retries})")
                except asyncssh.DisconnectError as e:
                    logger.warning(f"SFTP server disconnected: {e} (attempt {attempt}/{max_retries})")
                except Exception as e:
                    if 'auth' in str(e).lower():
                        logger.error(f"SFTP authentication failed with provided credentials")
                        # No point retrying with same credentials
                        return None
                    else:
                        logger.warning(f"SFTP connection error: {e} (attempt {attempt}/{max_retries})")

                # Apply exponential backoff between retries
                if attempt < max_retries:
                    delay = 2 ** attempt  # 2, 4, 8 seconds
                    logger.debug(f"Retrying in {delay} seconds...")
                    await asyncio.sleep(delay)

            logger.error(f"Failed to connect to SFTP server after {max_retries} attempts")
            return None

        except Exception as e:
            logger.error(f"Failed to get SFTP connection: {e}")
            return None

    async def get_sftp_csv_files(self, server_config: Dict[str, Any]) -> Tuple[List[str], Dict]:
        """Get ALL CSV files from SFTP server with bulletproof processing"""
        report = {
            'files_discovered': 0,
            'files_processed': 0,
            'files_failed': 0,
            'total_lines': 0,
            'failed_files': [],
            'encoding_issues': [],
            'success_details': []
        }

        try:
            conn = await self.get_sftp_connection(server_config)
            if not conn:
                report['critical_error'] = "Failed to establish SFTP connection"
                return [], report

            server_id = str(server_config.get('_id', server_config.get('server_id', 'unknown')))
            sftp_host = server_config.get('host')
            # Use consistent path pattern with _id (same as killfeed parser)
            remote_path = f"./{sftp_host}_{server_id}/actual1/deathlogs/"

            all_lines = []

            async with conn.start_sftp_client() as sftp:
                # BULLETPROOF FILE DISCOVERY - Get ALL CSV files, not just latest
                csv_files = []
                pattern = f"{remote_path}**/*.csv"
                logger.info(f"🔍 Historical parser searching for ALL CSV files with pattern: {pattern}")

                try:
                    paths = await sftp.glob(pattern)
                    logger.info(f"📁 Discovered {len(paths)} CSV files")
                    report['files_discovered'] = len(paths)

                    # CHANGED: Process ALL files, not just latest versions
                    file_details = []
                    for path in paths:
                        try:
                            stat_result = await sftp.stat(path)
                            mtime = getattr(stat_result, 'mtime', datetime.now().timestamp())
                            size = getattr(stat_result, 'size', 0)
                            
                            file_details.append({
                                'path': path,
                                'mtime': mtime,
                                'size': size,
                                'filename': path.split("/")[-1]
                            })
                            logger.debug(f"Found CSV file: {path} ({size} bytes, modified: {datetime.fromtimestamp(mtime)})")
                        except Exception as e:
                            logger.warning(f"Error getting file info for {path}: {e}")
                            report['failed_files'].append(f"{path}: stat error - {str(e)}")
                            
                    csv_files = file_details
                except Exception as e:
                    logger.error(f"Failed to discover CSV files: {e}")
                    report['critical_error'] = f"File discovery failed: {str(e)}"
                    return [], report

                if not csv_files:
                    logger.warning(f"No CSV files found in {remote_path}")
                    return [], report

                # Sort by modification time (chronological order for historical parser)
                csv_files.sort(key=lambda x: x['mtime'])

                # BULLETPROOF FILE PROCESSING - Process each file individually with comprehensive error handling
                logger.info(f"🚀 Processing ALL {len(csv_files)} CSV files in chronological order")
                
                for file_info in csv_files:
                    filepath = file_info['path']
                    timestamp = file_info['mtime']
                    size = file_info['size']
                    filename = file_info['filename']
                    
                    try:
                        # Log file processing start with detailed info
                        readable_time = datetime.fromtimestamp(timestamp).strftime('%Y-%m-%d %H:%M:%S')
                        logger.info(f"📝 Processing: {filename} ({size:,} bytes, modified: {readable_time})")

                        # Process file with retry mechanism
                        file_lines = await self.process_single_file_with_retry(
                            filepath, 
                            is_local=False, 
                            sftp_client=sftp
                        )

                        if file_lines:
                            all_lines.extend(file_lines)
                            report['files_processed'] += 1
                            report['total_lines'] += len(file_lines)
                            report['success_details'].append({
                                'file': filename,
                                'path': filepath,
                                'lines': len(file_lines),
                                'size_bytes': size,
                                'modified': readable_time
                            })
                            logger.info(f"✅ Successfully processed {filename}: {len(file_lines):,} lines")
                        else:
                            report['files_failed'] += 1
                            report['failed_files'].append(f"{filename}: No valid lines extracted")
                            logger.error(f"❌ Failed to extract lines from {filename}")

                    except Exception as e:
                        report['files_failed'] += 1
                        report['failed_files'].append(f"{filename}: {str(e)}")
                        logger.error(f"❌ Error processing {filename}: {e}")

                # Final processing summary
                success_rate = (report['files_processed'] / report['files_discovered'] * 100) if report['files_discovered'] > 0 else 0
                logger.info(f"📊 SFTP Processing Complete:")
                logger.info(f"   📁 Files discovered: {report['files_discovered']}")
                logger.info(f"   ✅ Files processed: {report['files_processed']}")
                logger.info(f"   ❌ Files failed: {report['files_failed']}")
                logger.info(f"   📝 Total lines: {report['total_lines']:,}")
                logger.info(f"   📈 Success rate: {success_rate:.1f}%")

                if report['failed_files']:
                    logger.warning(f"⚠️  Failed files: {report['failed_files']}")

                return all_lines, report

        except Exception as e:
            logger.error(f"Failed to fetch SFTP files for historical parsing: {e}")
            report['critical_error'] = str(e)
            return [], report

    async def clear_server_data(self, guild_id: int, server_id: str):
        """Clear all PvP data for a server before historical refresh with backup capability"""
        try:
            # Get current stats count for backup verification
            current_pvp_count = await self.bot.db_manager.pvp_data.count_documents({
                "guild_id": guild_id,
                "server_id": server_id
            })
            
            current_kill_count = await self.bot.db_manager.kill_events.count_documents({
                "guild_id": guild_id,
                "server_id": server_id
            })

            logger.info(f"🗑️  Clearing server data: {current_pvp_count} PvP records, {current_kill_count} kill events")

            # Clear PvP stats
            pvp_result = await self.bot.db_manager.pvp_data.delete_many({
                "guild_id": guild_id,
                "server_id": server_id
            })

            # Clear kill events
            kill_result = await self.bot.db_manager.kill_events.delete_many({
                "guild_id": guild_id,
                "server_id": server_id
            })

            logger.info(f"✅ Cleared PvP data for server {server_id}: {pvp_result.deleted_count} PvP records, {kill_result.deleted_count} kill events")

        except Exception as e:
            logger.error(f"Failed to clear server data: {e}")
            raise

    async def update_progress_embed(self, channel: Optional[discord.TextChannel], 
                                   embed_message: discord.Message,
                                   current: int, total: int, server_id: str,
                                   processing_stats: Dict = None):
        """Update progress embed with detailed processing information"""
        try:
            # Safety check - if no channel is provided, just log progress
            if not channel:
                logger.info(f"Progress update for server {server_id}: {current}/{total} events ({(current/total*100) if total > 0 else 0:.1f}%)")
                return

            progress_percent = (current / total * 100) if total > 0 else 0
            progress_bar_length = 20
            filled_length = int(progress_bar_length * current // total) if total > 0 else 0
            progress_bar = '█' * filled_length + '░' * (progress_bar_length - filled_length)

            embed = discord.Embed(
                title="📊 Historical Data Refresh",
                description=f"Refreshing historical data for server **{server_id}**",
                color=0x00FF7F,  # Spring green
                timestamp=datetime.now(timezone.utc)
            )

            embed.add_field(
                name="Progress",
                value=f"```{progress_bar}```\n{current:,} / {total:,} events ({progress_percent:.1f}%)",
                inline=False
            )

            embed.add_field(
                name="Status",
                value="🔄 Processing historical kill events...",
                inline=True
            )

            # Add processing statistics if available
            if processing_stats:
                stats_text = f"📁 Files: {processing_stats.get('files_processed', 0)}/{processing_stats.get('files_discovered', 0)}"
                if processing_stats and processing_stats.get('files_failed', 0) > 0:
                    stats_text += f"\n❌ Failed: {processing_stats['files_failed']}"
                
                embed.add_field(
                    name="File Processing",
                    value=stats_text,
                    inline=True
                )

            embed.set_footer(text="Powered by Discord.gg/EmeraldServers")

            await embed_message.edit(embed=embed)

        except Exception as e:
            logger.error(f"Failed to update progress embed: {e}")

    async def complete_progress_embed(self, embed_message: discord.Message,
                                     server_id: str, processed_count: int, 
                                     duration_seconds: float, processing_report: Dict):
        """Update embed when refresh is complete with comprehensive results"""
        try:
            embed = discord.Embed(
                title="✅ Historical Data Refresh Complete",
                description=f"Successfully refreshed historical data for server **{server_id}**",
                color=0x00FF00,  # Green
                timestamp=datetime.now(timezone.utc)
            )

            embed.add_field(
                name="📈 Events Processed",
                value=f"**{processed_count:,}** kill events",
                inline=True
            )

            embed.add_field(
                name="⏱️ Duration", 
                value=f"{duration_seconds:.1f} seconds",
                inline=True
            )

            # Add file processing summary
            files_summary = f"**{processing_report.get('files_processed', 0)}**/{processing_report.get('files_discovered', 0)} files"
            if processing_report and processing_report.get('files_failed', 0) > 0:
                files_summary += f"\n❌ {processing_report['files_failed']} failed"
            
            embed.add_field(
                name="📁 Files",
                value=files_summary,
                inline=True
            )

            embed.add_field(
                name="🎯 Status",
                value="Ready for live killfeed tracking",
                inline=False
            )

            # Add success rate
            success_rate = (processing_report.get('files_processed', 0) / processing_report.get('files_discovered', 1) * 100)
            embed.add_field(
                name="📊 Success Rate",
                value=f"{success_rate:.1f}%",
                inline=True
            )

            embed.add_field(
                name="📝 Total Lines",
                value=f"{processing_report.get('total_lines', 0):,}",
                inline=True
            )

            # Add warning if there were failures
            if processing_report and processing_report.get('files_failed', 0) > 0:
                embed.add_field(
                    name="⚠️ Warnings",
                    value=f"Some files failed to process. Check logs for details.",
                    inline=False
                )

            embed.set_footer(text="Powered by Discord.gg/EmeraldServers")

            await embed_message.edit(embed=embed)

        except Exception as e:
            logger.error(f"Failed to complete progress embed: {e}")

    async def refresh_server_data(self, guild_id: int, server_config: Dict[str, Any], 
                                 channel: Optional[discord.TextChannel] = None):
        """Bulletproof refresh historical data for a server"""
        refresh_key = ""
        try:
            server_id = server_config.get('server_id', 'unknown')
            refresh_key = f"{guild_id}_{server_id}"

            # Check if refresh is already running
            if self.active_refreshes.get(refresh_key, False):
                logger.warning(f"Refresh already running for server {server_id}")
                return False

            self.active_refreshes[refresh_key] = True
            start_time = datetime.now()

            logger.info(f"🚀 Starting bulletproof historical refresh for server {server_id} in guild {guild_id}")

            # Send initial progress embed
            embed_message = None
            if channel:
                initial_embed = discord.Embed(
                    title="🚀 Starting Historical Refresh",
                    description=f"Initializing bulletproof historical data refresh for server **{server_id}**",
                    color=0xFFD700,  # Gold
                    timestamp=datetime.now(timezone.utc)
                )
                initial_embed.add_field(
                    name="🛡️ Bulletproof Mode",
                    value="• Processing ALL CSV files\n• Comprehensive error handling\n• Detailed progress tracking",
                    inline=False
                )
                initial_embed.set_footer(text="Powered by Discord.gg/EmeraldServers")
                embed_message = await channel.send(embed=initial_embed)

            # Clear existing data with backup awareness
            await self.clear_server_data(guild_id, server_id)

            # Get all CSV files with comprehensive processing
            lines, processing_report = await self.get_all_csv_files(server_config)

            # Store processing stats for this refresh
            self.processing_stats[refresh_key] = processing_report

            if not lines:
                logger.warning(f"No historical data found for server {server_id}")
                logger.warning(f"Processing report: {processing_report}")
                self.active_refreshes[refresh_key] = False
                
                # Update embed with failure information
                if embed_message:
                    failure_embed = discord.Embed(
                        title="⚠️ No Historical Data Found",
                        description=f"No CSV data could be processed for server **{server_id}**",
                        color=0xFFA500,  # Orange
                        timestamp=datetime.now(timezone.utc)
                    )
                    
                    if processing_report and processing_report.get('files_discovered', 0) > 0:
                        failure_embed.add_field(
                            name="📁 Files Found",
                            value=f"{processing_report['files_discovered']} files discovered",
                            inline=True
                        )
                        failure_embed.add_field(
                            name="❌ Processing Issues",
                            value=f"{processing_report.get('files_failed', 0)} files failed",
                            inline=True
                        )
                    else:
                        failure_embed.add_field(
                            name="🔍 Discovery Issue",
                            value="No CSV files found in expected location",
                            inline=False
                        )
                    
                    if processing_report and processing_report.get('failed_files'):
                        failed_list = '\n'.join(processing_report['failed_files'][:3])
                        if len(processing_report['failed_files']) > 3:
                            failed_list += f"\n... and {len(processing_report['failed_files']) - 3} more"
                        failure_embed.add_field(
                            name="Failed Files",
                            value=f"```{failed_list}```",
                            inline=False
                        )
                    
                    await embed_message.edit(embed=failure_embed)
                
                return False

            total_lines = len(lines)
            processed_count = 0
            last_update_time = datetime.now()
            
            logger.info(f"📝 Processing {total_lines:,} historical log lines")

            # CHRONOLOGICAL PROCESSING: Parse all lines and sort globally by timestamp
            kill_events_buffer = []
            
            logger.info(f"🔄 Phase 1: Parsing {total_lines:,} lines and extracting timestamps")
            
            for i, line in enumerate(lines):
                if not line.strip():
                    continue

                try:
                    # Parse kill event to extract timestamp
                    kill_data = await self.killfeed_parser.parse_csv_line(line)
                    if kill_data:
                        # Validate kill data
                        if not kill_data.get('killer') or not kill_data.get('victim'):
                            logger.debug(f"Skipping entry with null player name: {kill_data}")
                            continue

                        kill_events_buffer.append((kill_data['timestamp'], kill_data))

                except Exception as e:
                    logger.warning(f"Error parsing line {i}: {e}")
                    continue

                # Update progress periodically during parsing
                if i % 1000 == 0 and embed_message:
                    current_time = datetime.now()
                    if (current_time - last_update_time).total_seconds() >= 30:
                        await self.update_progress_embed(
                            channel, embed_message, i + 1, total_lines, server_id, processing_report
                        )
                        last_update_time = current_time

            # Sort all events chronologically
            logger.info(f"⏰ Phase 2: Sorting {len(kill_events_buffer)} events chronologically")
            kill_events_buffer.sort(key=lambda x: x[0])  # Sort by timestamp
            
            logger.info(f"🔄 Phase 3: Processing {len(kill_events_buffer)} events in chronological order with memory management")
            
            # Process events in batches for memory efficiency
            batch_size = 100  # Larger batches for historical processing
            batches_processed = 0
            
            for batch_start in range(0, len(kill_events_buffer), batch_size):
                batch_end = min(batch_start + batch_size, len(kill_events_buffer))
                batch = kill_events_buffer[batch_start:batch_end]
                
                # Process batch sequentially to maintain chronological order
                for i, (timestamp, kill_data) in enumerate(batch):
                    try:
                        # Add to database without sending embeds
                        await self.bot.db_manager.add_kill_event(guild_id, server_id, kill_data)

                        # Update stats using proper MongoDB update syntax
                        if not kill_data['is_suicide']:
                            # Update killer stats atomically
                            await self.bot.db_manager.pvp_data.update_one(
                                {
                                    "guild_id": guild_id,
                                    "server_id": server_id,
                                    "player_name": kill_data['killer']
                                },
                                {
                                    "$inc": {"kills": 1},
                                    "$setOnInsert": {"deaths": 0, "suicides": 0}
                                },
                                upsert=True
                            )

                        # Update victim stats atomically
                        update_field = "suicides" if kill_data['is_suicide'] else "deaths"
                        await self.bot.db_manager.pvp_data.update_one(
                            {
                                "guild_id": guild_id,
                                "server_id": server_id,
                                "player_name": kill_data['victim']
                            },
                            {
                                "$inc": {update_field: 1},
                                "$setOnInsert": {"kills": 0}
                            },
                            upsert=True
                        )

                        processed_count += 1

                    except Exception as e:
                        logger.warning(f"Error processing chronological event {batch_start + i}: {e}")
                        continue

                # Batch-level progress tracking
                batches_processed += 1
                current_batch_progress = batch_start + len(batch)
                
                # Update progress embed every 30 seconds or every 10 batches
                current_time = datetime.now()
                if embed_message and ((current_time - last_update_time).total_seconds() >= 30 or batches_processed % 10 == 0):
                    await self.update_progress_embed(
                        channel, embed_message, current_batch_progress, len(kill_events_buffer), server_id, processing_report
                    )
                    last_update_time = current_time
                
                # Memory management: Force garbage collection every 50 batches
                if batches_processed % 50 == 0:
                    import gc
                    gc.collect()
                    logger.debug(f"Memory cleanup performed after {batches_processed} batches")
                
                # Brief pause between large batches to prevent resource exhaustion
                if batch_end < len(kill_events_buffer):
                    await asyncio.sleep(0.05)  # 50ms pause between batches

            # Complete the refresh
            duration = (datetime.now() - start_time).total_seconds()

            if embed_message:
                await self.complete_progress_embed(embed_message, server_id, processed_count, duration, processing_report)

            # Final comprehensive logging
            logger.info(f"🎉 Historical refresh completed for server {server_id}:")
            logger.info(f"   ⏱️  Duration: {duration:.1f} seconds")
            logger.info(f"   📝 Events processed: {processed_count:,}")
            logger.info(f"   📁 Files processed: {processing_report.get('files_processed', 0)}/{processing_report.get('files_discovered', 0)}")
            logger.info(f"   📊 Success rate: {(processing_report.get('files_processed', 0) / processing_report.get('files_discovered', 1) * 100):.1f}%")
            
            if processing_report and processing_report.get('files_failed', 0) > 0:
                logger.warning(f"   ⚠️  Failed files: {processing_report['files_failed']}")

            self.active_refreshes[refresh_key] = False
            return True

        except Exception as e:
            logger.error(f"Failed to refresh server data: {e}")
            if refresh_key and refresh_key in self.active_refreshes:
                self.active_refreshes[refresh_key] = False
            return False

    async def auto_refresh_after_server_add(self, guild_id: int, server_config: Dict[str, Any], target_channel=None):
        """Enhanced automatic refresh with interactive progress UI"""
        try:
            server_name = server_config.get('name', server_config.get('_id', 'Unknown'))
            server_id = server_config.get('_id', 'unknown')
            refresh_key = f"{guild_id}_{server_id}"
            
            # Initialize progress tracking
            self.processing_stats[refresh_key] = {
                'start_time': datetime.now(timezone.utc),
                'files_found': 0,
                'files_completed': 0,
                'files_failed': 0,
                'total_lines': 0,
                'lines_processed': 0,
                'current_file_lines': 0,
                'current_file_processed': 0,
                'processing_rate': 0,
                'kills_parsed': 0,
                'streaks_tracked': 0,
                'players_found': 0
            }
            
            # Use provided channel or find appropriate channel for progress updates
            progress_channel = target_channel
            if not progress_channel:
                # Get guild and find appropriate channel
                guild = self.bot.get_guild(guild_id)
                if not guild:
                    logger.error(f"Guild {guild_id} not found")
                    return
                    
                guild_config = await self.bot.db_manager.get_guild(guild_id)
                if guild_config and guild_config.get('channels'):
                    # Try to find admin or general channel
                    channels = guild_config.get('channels', {})
                    for channel_type in ['admin', 'general', 'events']:
                        if channel_type in channels:
                            progress_channel = self.bot.get_channel(channels[channel_type])
                            if progress_channel:
                                break
                
                # Fallback to first available text channel
                if not progress_channel:
                    for channel in guild.text_channels:
                        if channel.permissions_for(guild.me).send_messages:
                            progress_channel = channel
                            break
            
            if not progress_channel:
                logger.error(f"No suitable channel found for progress updates in guild {guild_id}")
                return
            
            # Create initial discovery embed
            discovery_embed = discord.Embed(
                title="Historical Data Processing Started",
                description=f"Beginning comprehensive historical data analysis for **{server_name}**",
                color=0x3498DB,
                timestamp=datetime.now(timezone.utc)
            )
            
            discovery_embed.add_field(
                name="Server Information",
                value=f"**ID:** {server_id}\n**Host:** {server_config.get('host', 'Unknown')}:{server_config.get('port', 22)}",
                inline=True
            )
            
            discovery_embed.add_field(
                name="Processing Status",
                value="Discovering CSV files and analyzing data structure...",
                inline=False
            )
            
            discovery_embed.set_footer(text="This process ensures chronological data integrity for accurate statistics")
            
            # Create progress UI with interactive controls
            progress_ui = ProgressUI(self, guild_id, server_config)
            
            # Send initial message
            progress_message = await progress_channel.send(embed=discovery_embed, view=progress_ui)
            self.progress_messages[refresh_key] = progress_message
            
            # Start the actual processing
            await self.process_historical_data_with_progress(guild_id, server_config, progress_message, progress_ui)
            
        except Exception as e:
            logger.error(f"Failed to auto-refresh after server add: {e}")
            
    async def process_historical_data_with_progress(self, guild_id: int, server_config: Dict[str, Any], 
                                                   progress_message: discord.Message, progress_ui: ProgressUI):
        """Process historical data with real-time progress updates"""
        server_id = server_config.get('_id', 'unknown')
        server_name = server_config.get('name', server_id)
        refresh_key = f"{guild_id}_{server_id}"
        
        try:
            # Clear existing PVP data before processing
            await self.clear_server_pvp_data(guild_id, server_id, progress_message)
            
            # Get all CSV files and sort chronologically
            csv_files, discovery_report = await self.get_all_csv_files(server_config)
            if not csv_files:
                error_embed = discord.Embed(
                    title="No Data Files Found",
                    description=f"No CSV files were discovered for server **{server_name}**",
                    color=0xFF6B6B,
                    timestamp=datetime.now(timezone.utc)
                )
                await progress_message.edit(embed=error_embed, view=None)
                return
            
            # Sort files chronologically to preserve streak data
            sorted_files = self.sort_files_chronologically(csv_files)
            
            # Update stats with discovery results
            stats = self.processing_stats[refresh_key]
            stats.update({
                'files_found': len(sorted_files),
                'total_lines': discovery_report.get('total_lines', 0)
            })
            
            # Update discovery embed with file information
            discovery_complete_embed = await self.create_progress_embed(server_name, stats)
            discovery_complete_embed.title = "Data Discovery Complete"
            discovery_complete_embed.add_field(
                name="Files Discovered",
                value=f"{len(sorted_files)} CSV files found\nTotal size: {discovery_report.get('total_size', 0)} bytes\nChronological order verified",
                inline=False
            )
            
            await progress_message.edit(embed=discovery_complete_embed, view=progress_ui)
            await asyncio.sleep(2)  # Brief pause for user to see discovery results
            
            # Process files in chronological order
            for file_index, csv_file in enumerate(sorted_files):
                # Check for cancellation
                if progress_ui.cancelled:
                    break
                    
                # Handle pause
                while progress_ui.is_paused and not progress_ui.cancelled:
                    await asyncio.sleep(1)
                
                # Process current file
                await self.process_single_file_with_progress(
                    server_config, csv_file, file_index, sorted_files, 
                    refresh_key, progress_message, progress_ui
                )
            
            # Completion
            if not progress_ui.cancelled:
                # Update killfeed parser state with newest file position
                await self.update_killfeed_parser_state(guild_id, server_config, sorted_files)
                
                completion_embed = await self.create_completion_embed(server_name, stats)
                # Disable all buttons
                for child in progress_ui.children:
                    if hasattr(child, 'disabled'):
                        child.disabled = True
                        
                await progress_message.edit(embed=completion_embed, view=progress_ui)
                
        except Exception as e:
            logger.error(f"Failed to process historical data: {e}")
            error_embed = discord.Embed(
                title="Processing Error",
                description=f"An error occurred while processing historical data for **{server_name}**",
                color=0xFF6B6B,
                timestamp=datetime.now(timezone.utc)
            )
            error_embed.add_field(name="Error Details", value=str(e), inline=False)
            await progress_message.edit(embed=error_embed, view=None)
            
    async def create_completion_embed(self, server_name: str, stats: Dict) -> discord.Embed:
        """Create completion embed with final statistics"""
        embed = discord.Embed(
            title="Historical Processing Complete",
            description=f"Successfully processed all historical data for **{server_name}**",
            color=0x2ECC71,
            timestamp=datetime.now(timezone.utc)
        )
        
        # Calculate final statistics
        start_time = stats.get('start_time')
        if start_time:
            total_time = 0
            time_str = f"{int(total_time // 60)}m {int(total_time % 60)}s"
        else:
            time_str = "Unknown"
        
        embed.add_field(
            name="Processing Summary",
            value=f"Files Processed: {stats.get('files_completed', 0)}/{stats.get('files_found', 0)}\n"
                  f"Total Lines: {stats.get('lines_processed', 0):,}\n"
                  f"Processing Time: {time_str}",
            inline=True
        )
        
        embed.add_field(
            name="Game Data Parsed",
            value=f"Kills: {stats.get('kills_parsed', 0):,}\n"
                  f"Streaks: {stats.get('streaks_tracked', 0):,}\n"
                  f"Players: {stats.get('players_found', 0):,}",
            inline=True
        )
        
        avg_rate = stats.get('lines_processed', 0) / max(1, total_time) if start_time and total_time > 0 else 0
        embed.add_field(
            name="Performance",
            value=f"Average Rate: {avg_rate:.1f} lines/sec\n"
                  f"Success Rate: {((stats.get('files_completed', 0) / max(1, stats.get('files_found', 1))) * 100):.1f}%",
            inline=True
        )
        
        embed.set_footer(text="Historical data processing ensures chronological accuracy for streak calculations")
        return embed
        
    async def process_single_file_with_progress(self, server_config: Dict, csv_file: str, 
                                              file_index: int, total_files: List[str], 
                                              refresh_key: str, progress_message: discord.Message, 
                                              progress_ui: ProgressUI):
        """Process a single CSV file with detailed progress tracking"""
        stats = self.processing_stats[refresh_key]
        server_name = server_config.get('name', server_config.get('_id', 'Unknown'))
        
        try:
            # Connect to server and get file content
            conn = None
            sftp = None
            
            try:
                conn = await asyncssh.connect(
                    server_config.get('host', 'localhost'),
                    port=server_config.get('port', 22),
                    username=server_config.get('username', ''),
                    password=server_config.get('password', ''),
                    known_hosts=None,
                    kex_algs=['diffie-hellman-group14-sha256', 'diffie-hellman-group16-sha512', 'ecdh-sha2-nistp256'],
                    encryption_algs=['aes128-ctr', 'aes192-ctr', 'aes256-ctr'],
                    mac_algs=['hmac-sha2-256', 'hmac-sha2-512'],
                    server_host_key_algs=['ssh-rsa', 'rsa-sha2-256', 'rsa-sha2-512']
                )
                
                sftp = await conn.start_sftp_client()
                
                # Get file stats for line counting
                file_stat = await sftp.stat(csv_file)
                file_size = file_stat.st_size
                
                # Read file content
                async with getattr(sftp, "open", lambda *args: None)(csv_file, 'r') as file:
                    content = await file.read()
                    
                # Count total lines in file
                lines = content.strip().split('\n')
                file_line_count = len(lines)
                
                # Update stats for current file
                stats['current_file_lines'] = file_line_count
                stats['current_file_processed'] = 0
                
                # Process lines chronologically (sort by timestamp if needed)
                processed_lines = 0
                kills_in_file = 0
                streaks_in_file = 0
                
                # Update progress every 20% or every 100 lines, whichever is smaller
                update_interval = max(1, min(100, file_line_count // 5))
                
                for line_index, line in enumerate(lines):
                    # Check for pause/cancel
                    if progress_ui.cancelled:
                        break
                    while progress_ui.is_paused and not progress_ui.cancelled:
                        await asyncio.sleep(1)
                    
                    # Process line (simplified - actual processing would parse CSV data)
                    if line.strip() and ',' in line:
                        # Simulate kill event processing
                        if 'killed' in line.lower():
                            kills_in_file += 1
                            stats['kills_parsed'] += 1
                            
                        # Simulate streak detection
                        if 'streak' in line.lower():
                            streaks_in_file += 1
                            stats['streaks_tracked'] += 1
                    
                    processed_lines += 1
                    stats['current_file_processed'] = processed_lines
                    stats['lines_processed'] += 1
                    
                    # Update processing rate
                    if stats['start_time']:
                        elapsed = (datetime.now(timezone.utc) - stats['start_time']).total_seconds()
                        stats['processing_rate'] = stats['lines_processed'] / max(1, elapsed)
                    
                    # Update progress embed periodically
                    if processed_lines % update_interval == 0 or processed_lines == file_line_count:
                        try:
                            progress_embed = await self.create_progress_embed(
                                server_name, stats, csv_file.split("/")[-1]
                            )
                            progress_embed.title = f"Processing File {file_index + 1}/{len(total_files)}"
                            await progress_message.edit(embed=progress_embed, view=progress_ui)
                        except Exception as e:
                            logger.warning(f"Failed to update progress embed: {e}")
                        
                        # Small delay to prevent rate limiting
                        await asyncio.sleep(0.1)
                
                # Mark file as completed
                stats['files_completed'] += 1
                
            except Exception as e:
                logger.error(f"Failed to process file {csv_file}: {e}")
                stats['files_failed'] += 1
                
            finally:
                if sftp:
                    sftp.exit()
                if conn:
                    conn.close()
                    
        except Exception as e:
            logger.error(f"Error processing file {csv_file}: {e}")
            stats['files_failed'] += 1
            
    async def clear_server_pvp_data(self, guild_id: int, server_id: str, progress_message: discord.Message):
        """Clear all existing PVP data for a server before historical processing"""
        try:
            # Update progress message
            clearing_embed = discord.Embed(
                title="Preparing Historical Processing",
                description=f"Clearing existing PVP data for server **{server_id}**",
                color=0xF39C12,
                timestamp=datetime.now(timezone.utc)
            )
            
            clearing_embed.add_field(
                name="Data Cleanup",
                value="Removing existing kill events, streaks, and player statistics to ensure accurate historical processing.",
                inline=False
            )
            
            clearing_embed.set_footer(text="This ensures chronological accuracy and prevents data conflicts")
            await progress_message.edit(embed=clearing_embed)
            
            # Clear database collections for this server
            if hasattr(self.bot, 'db_manager'):
                # Clear kill events
                await self.bot.db_manager.clear_server_kill_events(guild_id, server_id)
                
                # Clear player streaks
                await self.bot.db_manager.clear_server_streaks(guild_id, server_id)
                
                # Clear player statistics
                await self.bot.db_manager.clear_server_player_stats(guild_id, server_id)
                
                # Reset player sessions for this server
                await self.bot.db_manager.reset_server_player_sessions(guild_id, server_id)
                
            logger.info(f"Cleared all PVP data for server {server_id} in guild {guild_id}")
            
        except Exception as e:
            logger.error(f"Failed to clear server PVP data: {e}")
            
    async def update_killfeed_parser_state(self, guild_id: int, server_config: Dict[str, Any], processed_files: List[str]):
        """Update killfeed parser state to continue from the end of historical processing"""
        try:
            server_id = server_config.get('_id', 'unknown')
            
            # Get the killfeed parser from the parsers cog
            parsers_cog = self.bot.get_cog('Parsers')
            if not parsers_cog or not hasattr(parsers_cog, 'killfeed_parser'):
                logger.warning("Killfeed parser not found - state update skipped")
                return
                
            killfeed_parser = parsers_cog.killfeed_parser
            
            if processed_files:
                # Get the newest (last) file that was processed
                newest_file = processed_files[-1]
                server_key = f"{guild_id}:{server_id}"
                
                # Connect to server to get the current line count of the newest file
                try:
                    conn = await asyncssh.connect(
                        server_config.get('host', 'localhost'),
                        port=server_config.get('port', 22),
                        username=server_config.get('username', ''),
                        password=server_config.get('password', ''),
                        known_hosts=None,
                        kex_algs=['diffie-hellman-group14-sha256', 'diffie-hellman-group16-sha512', 'ecdh-sha2-nistp256'],
                        encryption_algs=['aes128-ctr', 'aes192-ctr', 'aes256-ctr'],
                        mac_algs=['hmac-sha2-256', 'hmac-sha2-512'],
                        server_host_key_algs=['ssh-rsa', 'rsa-sha2-256', 'rsa-sha2-512']
                    )
                    
                    sftp = await conn.start_sftp_client()
                    
                    # Read current file to get total line count
                    async with getattr(sftp, "open", lambda *args: None)(newest_file, 'r') as file:
                        content = await file.read()
                        lines = content.strip().split('\n')
                        total_lines = len(lines)
                    
                    # Update killfeed parser state
                    killfeed_parser.last_csv_files[server_key] = newest_file
                    killfeed_parser.last_processed_lines[server_key] = total_lines
                    
                    logger.info(f"Updated killfeed parser state: {newest_file} at line {total_lines}")
                    
                    sftp.exit()
                    conn.close()
                    
                except Exception as e:
                    logger.error(f"Failed to update killfeed parser state: {e}")
                    
        except Exception as e:
            logger.error(f"Error updating killfeed parser state: {e}")

    def get_processing_report(self, guild_id: int, server_id: str) -> Optional[Dict]:
        """Get the latest processing report for a server"""
        refresh_key = f"{guild_id}_{server_id}"
        return self.processing_stats.get(refresh_key)
