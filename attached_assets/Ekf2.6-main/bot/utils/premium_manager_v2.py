"""
Premium Manager V2 - Mixed Server Model
Handles per-server premium status with incremental limit management
"""

import asyncio
from datetime import datetime
from typing import Dict, List, Optional, Tuple
import discord
import discord
from discord.ext import commands


class PremiumManagerV2:
    """
    Premium Manager V2 - Mixed Server Model
    
    Features:
    - Per-server premium status (guilds can have both premium and non-premium servers)
    - Incremental limit management (/sub add, /sub remove)
    - Cross-guild administrative control via Home Guild
    - Automatic server deactivation when limits are reduced
    """
    
    def __init__(self, database):
        self.db = database
        self._locks = {}
        
        # Initialize cache integration if available
        try:
            from .unified_cache import get_cache
            self.cache = get_cache()
        except ImportError:
            self.cache = None
    
    def get_guild_lock(self, guild_id: int) -> asyncio.Lock:
        """Get or create a lock for guild operations to prevent race conditions"""
        if guild_id not in self._locks:
            self._locks[guild_id] = asyncio.Lock()
        return self._locks[guild_id]
    
    # =====================
    # HOME GUILD MANAGEMENT
    # =====================
    
    async def set_home_guild(self, guild_id: int, set_by: int) -> bool:
        """Set the Home Guild for premium management (Bot Owner only)"""
        try:
            await self.db.bot_config.update_one(
                {"config_type": "home_guild"},
                {
                    "$set": {
                        "guild_id": guild_id,
                        "set_by": set_by,
                        "set_at": datetime.utcnow()
                    }
                },
                upsert=True
            )
            return True
        except Exception as e:
            print(f"Error setting home guild: {e}")
            return False
    
    async def get_home_guild(self) -> Optional[int]:
        """Get the current Home Guild ID"""
        try:
            config = await self.db.bot_config.find_one({"config_type": "home_guild"})
            return config.get("guild_id") if config else None
        except Exception:
            return None
    
    # =======================
    # PREMIUM LIMIT MANAGEMENT
    # =======================
    
    async def add_premium_limit(self, guild_id: int, added_by: int, reason: str = None) -> bool:
        """Add 1 to the premium server limit for a guild"""
        async with self.get_guild_lock(guild_id):
            try:
                # Get current limit
                current_limit = await self.get_premium_limit(guild_id)
                new_limit = current_limit + 1
                
                # Update limit
                await self.db.premium_limits.update_one(
                    {"guild_id": guild_id},
                    {
                        "$set": {
                            "guild_id": guild_id,
                            "max_premium_servers": new_limit,
                            "last_modified_by": added_by,
                            "last_modified_at": datetime.utcnow()
                        },
                        "$push": {
                            "limit_history": {
                                "action": "increased",
                                "from_limit": current_limit,
                                "to_limit": new_limit,
                                "by": added_by,
                                "at": datetime.utcnow(),
                                "reason": reason or "Premium limit increased"
                            }
                        }
                    },
                    upsert=True
                )
                return True
            except Exception as e:
                print(f"Error adding premium limit: {e}")
                return False
    
    async def remove_premium_limit(self, guild_id: int, removed_by: int, reason: str = None, auto_deactivate: bool = True) -> Tuple[bool, List[str]]:
        """
        Remove 1 from the premium server limit for a guild
        Returns (success, list_of_deactivated_servers)
        """
        async with self.get_guild_lock(guild_id):
            try:
                # Get current status
                current_limit = await self.get_premium_limit(guild_id)
                current_count = await self.count_premium_servers(guild_id)
                
                if current_limit <= 0:
                    return False, []
                
                new_limit = current_limit - 1
                deactivated_servers = []
                
                # Check if we need to deactivate servers
                if current_count > new_limit:
                    servers_to_deactivate = current_count - new_limit
                    
                    if auto_deactivate:
                        # Auto-deactivate oldest servers
                        deactivated_servers = await self._auto_deactivate_servers(
                            guild_id, servers_to_deactivate, removed_by, 
                            f"Auto-deactivated due to limit reduction: {reason or 'Limit decreased'}"
                        )
                    else:
                        # Cannot remove without deactivation
                        return False, []
                
                # Update limit
                await self.db.premium_limits.update_one(
                    {"guild_id": guild_id},
                    {
                        "$set": {
                            "max_premium_servers": new_limit,
                            "last_modified_by": removed_by,
                            "last_modified_at": datetime.utcnow()
                        },
                        "$push": {
                            "limit_history": {
                                "action": "decreased",
                                "from_limit": current_limit,
                                "to_limit": new_limit,
                                "by": removed_by,
                                "at": datetime.utcnow(),
                                "reason": reason or "Premium limit decreased",
                                "auto_deactivated_servers": deactivated_servers
                            }
                        }
                    }
                )
                return True, deactivated_servers
                
            except Exception as e:
                print(f"Error removing premium limit: {e}")
                return False, []
    
    async def set_premium_limit(self, guild_id: int, limit: int, set_by: int, reason: str = None) -> bool:
        """Direct set premium limit (admin override)"""
        async with self.get_guild_lock(guild_id):
            try:
                current_limit = await self.get_premium_limit(guild_id)
                
                await self.db.premium_limits.update_one(
                    {"guild_id": guild_id},
                    {
                        "$set": {
                            "guild_id": guild_id,
                            "max_premium_servers": limit,
                            "last_modified_by": set_by,
                            "last_modified_at": datetime.utcnow()
                        },
                        "$push": {
                            "limit_history": {
                                "action": "set",
                                "from_limit": current_limit,
                                "to_limit": limit,
                                "by": set_by,
                                "at": datetime.utcnow(),
                                "reason": reason or f"Direct set to {limit}"
                            }
                        }
                    },
                    upsert=True
                )
                return True
            except Exception as e:
                print(f"Error setting premium limit: {e}")
                return False
    
    async def get_premium_limit(self, guild_id: int) -> int:
        """Get current premium server limit for guild"""
        try:
            limit_doc = await self.db.premium_limits.find_one({"guild_id": guild_id})
            if limit_doc:
                # Use max_premium_servers as the primary field name
                return limit_doc.get("max_premium_servers", 0)
            return 0
        except Exception:
            return 0
    
    async def get_premium_usage(self, guild_id: int) -> Dict[str, int]:
        """Get premium usage statistics for guild"""
        try:
            limit = await self.get_premium_limit(guild_id)
            used = await self.count_premium_servers(guild_id)
            available = max(0, limit - used)
            
            return {
                "limit": limit,
                "used": used,
                "available": available
            }
        except Exception:
            return {"limit": 0, "used": 0, "available": 0}
    
    # ==========================
    # SERVER PREMIUM MANAGEMENT
    # ==========================
    
    async def is_server_premium(self, guild_id: int, server_id: str) -> bool:
        """Check if a specific server is premium"""
        try:
            status = await self.db.server_premium_status.find_one({
                "guild_id": guild_id,
                "server_id": server_id,
                "is_active": True
            })
            return status is not None
        except Exception:
            return False
    
    async def activate_server_premium(self, guild_id: int, server_id: str, activated_by: int, reason: str = None) -> Tuple[bool, str]:
        """
        Activate premium for a server
        Returns (success, message)
        """
        async with self.get_guild_lock(guild_id):
            try:
                # Check if already premium
                if await self.is_server_premium(guild_id, server_id):
                    return False, "Server is already premium"
                
                # Check capacity
                usage = await self.get_premium_usage(guild_id)
                if usage["available"] <= 0:
                    active_servers = await self.list_premium_servers(guild_id)
                    server_list = ", ".join([f"{s['name']} ({s['server_id']})" for s in active_servers])
                    return False, f"Premium server limit reached ({usage['used']}/{usage['limit']}). Active servers: {server_list}"
                
                # Activate premium
                await self.db.server_premium_status.update_one(
                    {"guild_id": guild_id, "server_id": server_id},
                    {
                        "$set": {
                            "guild_id": guild_id,
                            "server_id": server_id,
                            "is_active": True,
                            "activated_by": activated_by,
                            "activated_at": datetime.utcnow()
                        },
                        "$push": {
                            "premium_history": {
                                "action": "activated",
                                "by": activated_by,
                                "at": datetime.utcnow(),
                                "reason": reason or "Manual activation"
                            }
                        }
                    },
                    upsert=True
                )
                
                return True, f"Server {server_id} activated as premium ({usage['used'] + 1}/{usage['limit']})"
                
            except Exception as e:
                print(f"Error activating server premium: {e}")
                return False, "Database error occurred"
    
    async def deactivate_server_premium(self, guild_id: int, server_id: str, deactivated_by: int, reason: str = None) -> Tuple[bool, str]:
        """
        Deactivate premium for a server
        Returns (success, message)
        """
        async with self.get_guild_lock(guild_id):
            try:
                # Check if premium
                if not await self.is_server_premium(guild_id, server_id):
                    return False, "Server is not premium"
                
                # Deactivate premium
                await self.db.server_premium_status.update_one(
                    {"guild_id": guild_id, "server_id": server_id},
                    {
                        "$set": {
                            "is_active": False,
                            "deactivated_by": deactivated_by,
                            "deactivated_at": datetime.utcnow()
                        },
                        "$push": {
                            "premium_history": {
                                "action": "deactivated",
                                "by": deactivated_by,
                                "at": datetime.utcnow(),
                                "reason": reason or "Manual deactivation"
                            }
                        }
                    }
                )
                
                usage = await self.get_premium_usage(guild_id)
                return True, f"Server {server_id} deactivated ({usage['used']}/{usage['limit']})"
                
            except Exception as e:
                print(f"Error deactivating server premium: {e}")
                return False, "Database error occurred"
    
    async def count_premium_servers(self, guild_id: int) -> int:
        """Count active premium servers for guild"""
        try:
            count = await self.db.server_premium_status.count_documents({
                "guild_id": guild_id,
                "is_active": True
            })
            return count
        except Exception:
            return 0
    
    async def has_premium_access(self, guild_id: int, server_id: str = None) -> bool:
        """
        Check if guild has premium access
        
        For server-specific features: checks if specific server is premium
        For guild-wide features (economy, gambling): checks if ANY server in guild is premium
        """
        try:
            if server_id:
                # Server-specific premium check
                return await self.is_server_premium(guild_id, server_id)
            else:
                # Guild-wide premium check - need at least 1 premium server
                premium_count = await self.count_premium_servers(guild_id)
                return premium_count > 0
        except Exception:
            return False
    
    async def check_premium_access(self, guild_id: int, server_id: str = None) -> bool:
        """
        Legacy compatibility method - same as has_premium_access
        """
        return await self.has_premium_access(guild_id, server_id)
    
    async def list_premium_servers(self, guild_id: int) -> List[Dict[str, str]]:
        """List all premium servers for guild with names"""
        try:
            premium_servers = []
            
            # Get premium server IDs
            premium_docs = await self.db.server_premium_status.find({
                "guild_id": guild_id,
                "is_premium": True
            }).to_list(length=None)
            
            # Get server names from guild config
            guild_config = await self.db.guilds.find_one({"guild_id": guild_id})
            server_names = {}
            
            if guild_config and "servers" in guild_config:
                for server in guild_config["servers"]:
                    server_names[server["server_id"]] = server.get("name", f"Server {server['server_id']}")
            
            # Build result list
            for doc in premium_docs:
                server_id = doc["server_id"]
                premium_servers.append({
                    "server_id": server_id,
                    "name": server_names.get(server_id, f"Server {server_id}"),
                    "activated_at": doc.get("activated_at"),
                    "activated_by": doc.get("activated_by")
                })
            
            # Sort by activation date (oldest first for deactivation priority)
            premium_servers.sort(key=lambda x: x.get("activated_at") or datetime.min)
            
            return premium_servers
            
        except Exception as e:
            print(f"Error listing premium servers: {e}")
            return []
    
    async def _auto_deactivate_servers(self, guild_id: int, count: int, deactivated_by: int, reason: str) -> List[str]:
        """Auto-deactivate oldest premium servers"""
        try:
            premium_servers = await self.list_premium_servers(guild_id)
            deactivated = []
            
            for i in range(min(count, len(premium_servers))):
                server = premium_servers[i]
                success, _ = await self.deactivate_server_premium(
                    guild_id, server["server_id"], deactivated_by, reason
                )
                if success:
                    deactivated.append(f"{server['name']} ({server['server_id']})")
            
            return deactivated
            
        except Exception as e:
            print(f"Error auto-deactivating servers: {e}")
            return []
    
    # ===================
    # PERMISSION CHECKING
    # ===================
    
    async def is_bot_owner(self, user_id: int, bot) -> bool:
        """Check if user is bot owner"""
        try:
            app_info = await bot.application_info()
            return user_id == app_info.owner.id
        except Exception:
            return False
    
    async def is_home_guild_admin(self, user_id: int, bot) -> bool:
        """Check if user is admin in Home Guild"""
        try:
            home_guild_id = await self.get_home_guild()
            if not home_guild_id:
                return False
            
            home_guild = bot.get_guild(home_guild_id)
            if not home_guild:
                return False
            
            member = home_guild.get_member(user_id)
            if not member:
                return False
            
            return member.guild_permissions.administrator
            
        except Exception:
            return False
    
    async def can_manage_premium_limits(self, user_id: int, bot) -> bool:
        """Check if user can manage premium limits (bot owner or home guild admin)"""
        return await self.is_bot_owner(user_id, bot) or await self.is_home_guild_admin(user_id, bot)
    
    async def is_guild_admin(self, user_id: int, guild_id: int, bot) -> bool:
        """Check if user is admin in specific guild"""
        try:
            guild = bot.get_guild(guild_id)
            if not guild:
                return False
            
            member = guild.get_member(user_id)
            if not member:
                return False
            
            return member.guild_permissions.administrator
            
        except Exception:
            return False


# Permission decorators for commands
def bot_owner_only():
    """Decorator to restrict commands to bot owner only"""
    async def predicate(ctx):
        premium_manager = ctx.bot.premium_manager_v2
        return await premium_manager.is_bot_owner(ctx.author.id, ctx.bot)
    
    return commands.check(predicate)


def home_guild_admin_only():
    """Decorator to restrict commands to bot owner or home guild admins"""
    async def predicate(ctx):
        premium_manager = ctx.bot.premium_manager_v2
        return await premium_manager.can_manage_premium_limits(ctx.author.id, ctx.bot)
    
    return commands.check(predicate)


def guild_admin_only():
    """Decorator to restrict commands to guild administrators"""
    async def predicate(ctx):
        if not ctx.guild:
            return False
        return ctx.author.guild_permissions.administrator
    
    return commands.check(predicate)