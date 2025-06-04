"""
Scalable Connection Pool Manager
Handles SSH connections for multi-server historical parsing with proper resource management
"""

import asyncio
import asyncssh
import logging
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timezone
from contextlib import asynccontextmanager
import weakref

logger = logging.getLogger(__name__)

class ServerConnectionPool:
    """Connection pool for a single server with health monitoring"""
    
    def __init__(self, server_config: Dict[str, Any], max_connections: int = 3):
        self.server_config = server_config
        self.max_connections = max_connections
        self.active_connections: List[asyncssh.SSHClientConnection] = []
        self.available_connections: asyncio.Queue = asyncio.Queue()
        self.connection_count = 0
        self.failed_attempts = 0
        self.last_failure_time: Optional[datetime] = None
        self.circuit_breaker_open = False
        self._lock = asyncio.Lock()
        
    async def get_connection(self) -> Optional[asyncssh.SSHClientConnection]:
        """Get an available connection from the pool"""
        async with self._lock:
            # Check circuit breaker
            if self.circuit_breaker_open:
                if self._should_retry():
                    self.circuit_breaker_open = False
                    logger.info(f"Circuit breaker reset for {self.server_config.get('host')}")
                else:
                    return None
            
            # Try to get existing connection
            try:
                if not self.available_connections.empty():
                    conn = await asyncio.wait_for(self.available_connections.get(), timeout=0.1)
                    if conn and not getattr(conn, 'is_closing', False):
                        return conn
            except asyncio.TimeoutError:
                pass
            
            # Create new connection if under limit
            if self.connection_count < self.max_connections:
                conn = await self._create_connection()
                if conn:
                    self.connection_count += 1
                    self.active_connections.append(conn)
                    return conn
            
            return None
    
    async def return_connection(self, conn: asyncssh.SSHClientConnection):
        """Return a connection to the pool"""
        if conn and not getattr(conn, 'is_closing', False):
            await self.available_connections.put(conn)
    
    async def _create_connection(self) -> Optional[asyncssh.SSHClientConnection]:
        """Create a new SSH connection with robust compatibility strategies"""
        
        # Define multiple connection strategies for maximum compatibility
        connection_strategies = [
            {
                'name': 'modern_secure',
                'kex_algs': [
                    'curve25519-sha256', 'curve25519-sha256@libssh.org',
                    'ecdh-sha2-nistp256', 'ecdh-sha2-nistp384', 'ecdh-sha2-nistp521',
                    'diffie-hellman-group16-sha512', 'diffie-hellman-group18-sha512',
                    'diffie-hellman-group14-sha256'
                ]
            },
            {
                'name': 'legacy_compatible',
                'kex_algs': [
                    'diffie-hellman-group14-sha1', 'diffie-hellman-group1-sha1',
                    'diffie-hellman-group-exchange-sha256', 'diffie-hellman-group-exchange-sha1'
                ]
            },
            {
                'name': 'ultra_legacy',
                'kex_algs': [
                    'diffie-hellman-group1-sha1'
                ]
            }
        ]
        
        for strategy in connection_strategies:
            try:
                logger.debug(f"Trying connection strategy: {strategy['name']} for {self.server_config.get('host')}")
                
                options = {
                    'username': self.server_config.get('username', ''),
                    'password': self.server_config.get('password', ''),
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
                    ],
                    'compression_algs': ['none'],
                    'server_host_key_algs': ['ssh-rsa', 'rsa-sha2-256', 'rsa-sha2-512', 'ssh-dss']
                }
                
                conn = await asyncio.wait_for(
                    asyncssh.connect(
                        self.server_config.get('host', 'localhost'),
                        port=self.server_config.get('port', 22),
                        **options
                    ),
                    timeout=30
                )
                
                logger.info(f"✅ SFTP connected using {strategy['name']} to {self.server_config.get('host')}")
                self.failed_attempts = 0
                return conn
                
            except asyncio.TimeoutError:
                logger.warning(f"Connection timeout with {strategy['name']}")
                continue
            except asyncssh.DisconnectError as e:
                if 'Invalid DH parameters' in str(e):
                    logger.warning(f"DH parameters rejected for {strategy['name']}")
                    continue
                else:
                    logger.warning(f"Server disconnected: {e}")
                    continue
            except Exception as e:
                if 'Invalid DH parameters' in str(e):
                    logger.warning(f"DH validation failed for {strategy['name']}")
                    continue
                elif 'auth' in str(e).lower():
                    logger.error(f"Authentication failed with provided credentials")
                    break  # No point trying other strategies with bad auth
                else:
                    logger.warning(f"Connection error with {strategy['name']}: {e}")
                    continue
        
        # All strategies failed
        self.failed_attempts += 1
        self.last_failure_time = datetime.now(timezone.utc)
        
        if self.failed_attempts >= 3:
            self.circuit_breaker_open = True
            logger.error(f"Circuit breaker opened for {self.server_config.get('host')} after {self.failed_attempts} failures")
        
        logger.error(f"All connection strategies failed for {self.server_config.get('host')}")
        return None
    
    def _should_retry(self) -> bool:
        """Check if circuit breaker should allow retry"""
        if not self.last_failure_time:
            return True
        
        time_since_failure = (datetime.now(timezone.utc) - self.last_failure_time).total_seconds()
        return time_since_failure > (30 * min(self.failed_attempts, 10))  # Exponential backoff up to 5 minutes
    
    async def close_all(self):
        """Close all connections in the pool"""
        async with self._lock:
            for conn in self.active_connections:
                if not getattr(conn, 'is_closing', False):
                    conn.close()
            
            self.active_connections.clear()
            self.connection_count = 0
            
            # Clear the queue
            while not self.available_connections.empty():
                try:
                    conn = self.available_connections.get_nowait()
                    if not conn.is_closing():
                        conn.close()
                except asyncio.QueueEmpty:
                    break

class GlobalConnectionManager:
    """Global connection pool manager for all servers across all guilds"""
    
    def __init__(self):
        self.guild_pools: Dict[int, Dict[str, ServerConnectionPool]] = {}
        self._cleanup_task: Optional[asyncio.Task] = None
        self._running = False
        
    async def start(self):
        """Start the connection manager"""
        if not self._running:
            self._running = True
            self._cleanup_task = asyncio.create_task(self._cleanup_routine())
            logger.info("Global connection manager started")
    
    async def stop(self):
        """Stop the connection manager and cleanup all connections"""
        self._running = False
        
        if self._cleanup_task:
            self._cleanup_task.cancel()
            try:
                await self._cleanup_task
            except asyncio.CancelledError:
                pass
        
        # Close all connection pools
        for guild_pools in self.guild_pools.values():
            for pool in guild_pools.values():
                await pool.close_all()
        
        self.guild_pools.clear()
        logger.info("Global connection manager stopped")
    
    @asynccontextmanager
    async def get_connection(self, guild_id: int, server_config: Dict[str, Any]):
        """Context manager for getting and returning connections"""
        server_key = f"{server_config.get('host')}:{server_config.get('port')}"
        
        # Ensure guild pool exists
        if guild_id not in self.guild_pools:
            self.guild_pools[guild_id] = {}
        
        # Ensure server pool exists
        if server_key not in self.guild_pools[guild_id]:
            self.guild_pools[guild_id][server_key] = ServerConnectionPool(server_config)
        
        pool = self.guild_pools[guild_id][server_key]
        conn = await pool.get_connection()
        
        if not conn:
            raise ConnectionError(f"Failed to get connection to {server_key}")
        
        try:
            yield conn
        finally:
            await pool.return_connection(conn)
    
    async def _cleanup_routine(self):
        """Periodic cleanup of stale connections"""
        while self._running:
            try:
                await asyncio.sleep(300)  # Check every 5 minutes
                
                for guild_id, guild_pools in list(self.guild_pools.items()):
                    for server_key, pool in list(guild_pools.items()):
                        # Clean up stale connections
                        async with pool._lock:
                            active_connections = []
                            for conn in pool.active_connections:
                                if not getattr(conn, 'is_closing', False):
                                    active_connections.append(conn)
                                else:
                                    pool.connection_count -= 1
                            
                            pool.active_connections = active_connections
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in connection cleanup routine: {e}")
    
    def get_pool_stats(self) -> Dict[str, Any]:
        """Get statistics about connection pools"""
        stats = {
            'total_guilds': len(self.guild_pools),
            'total_servers': sum(len(pools) for pools in self.guild_pools.values()),
            'guild_details': {}
        }
        
        for guild_id, guild_pools in self.guild_pools.items():
            guild_stats = {
                'servers': len(guild_pools),
                'total_connections': sum(pool.connection_count for pool in guild_pools.values()),
                'failed_servers': sum(1 for pool in guild_pools.values() if pool.circuit_breaker_open)
            }
            stats['guild_details'][str(guild_id)] = guild_stats
        
        return stats

# Global instance
connection_manager = GlobalConnectionManager()