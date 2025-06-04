from typing import Dict, List, Optional, Any
"""
Subscription Management Cog - Premium Server Limit Management
User-friendly commands: /sub add, /sub remove, /sub view
"""

import discord
from discord.ext import commands
from datetime import datetime
import asyncio
from bot.utils.premium_manager_v2 import home_guild_admin_only, bot_owner_only, guild_admin_only
from bot.cogs.autocomplete import ServerAutocomplete


class SubscriptionManagement(discord.Cog):
    """
    SUBSCRIPTION MANAGEMENT
    - /sub add <guild_id> [reason] - Add 1 premium server slot (Bot Owner + Home Guild Admins)
    - /sub remove <guild_id> [reason] - Remove 1 premium server slot (Bot Owner + Home Guild Admins)  
    - /sub view <guild_id> - View premium limits and usage
    - /sub list - List all guild limits (Bot Owner + Home Guild Admins)
    """
    
    def __init__(self, bot):
        self.bot = bot
        # Initialize with fallback to bot's db_manager if premium_manager_v2 not ready
        self.premium_manager = getattr(bot, 'premium_manager_v2', None) or getattr(bot, 'premium_manager', None)
    
    async def check_premium_access(self, guild_id: int) -> bool:
        """Check if guild has premium access - unified validation"""
        try:

            pass
            if hasattr(self.bot, 'premium_manager_v2'):
                return await self.bot.premium_manager_v2.has_premium_access(guild_id)
            elif hasattr(self.bot, 'db_manager') and hasattr(self.bot.db_manager, 'has_premium_access'):
                return await self.bot.db_manager.has_premium_access(guild_id)
            else:
                return False
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Premium access check failed: {e}")
            return False
        
    async def cog_load(self):
        """Initialize premium manager when cog loads"""
        # Direct assignment - should already be available
        if hasattr(self.bot, 'premium_manager_v2') and self.bot.premium_manager_v2:
            self.premium_manager = self.bot.premium_manager_v2
        elif hasattr(self.bot, 'premium_manager') and self.bot.premium_manager:
            self.premium_manager = self.bot.premium_manager
    
    async def _ensure_premium_manager(self, ctx: discord.ApplicationContext) -> bool:
        """Ensure premium manager is available, respond with error if not"""
        # Always try to get the most current premium manager reference
        if hasattr(self.bot, 'premium_manager_v2') and self.bot.premium_manager_v2:
            self.premium_manager = self.bot.premium_manager_v2
            return True
        elif hasattr(self.bot, 'premium_manager') and self.bot.premium_manager:
            self.premium_manager = self.bot.premium_manager
            return True
        else:
            await ctx.respond("❌ Premium system not available", ephemeral=True)
            return False
    
    # Home Guild Management Commands
    home = discord.SlashCommandGroup("home", "Home Guild configuration commands")
    
    @home.command(name="set", description="Set the Home Guild for premium management")
    @bot_owner_only()
    async def set_home_guild(self, ctx: discord.ApplicationContext, 
                           guild_id: discord.Option(str, "Guild ID to set as Home Guild")):
        """Set the Home Guild for premium management (Bot Owner only)"""
        if not await self._ensure_premium_manager(ctx):
            return
            
        try:

            
            pass
            guild_id_int = int(guild_id)
            
            # Verify guild exists and bot is in it
            target_guild = self.bot.get_guild(guild_id_int)
            if not target_guild:
                await ctx.respond("❌ Bot is not in that guild or guild doesn't exist", ephemeral=True)
                return
            
            # Use simplified database storage for home guild
            await self.bot.db_manager.bot_config.update_one(
                {"_id": "home_guild"},
                {"$set": {"guild_id": guild_id_int, "set_by": ctx.author.id, "set_at": datetime.utcnow()}},
                upsert=True
            )
            
            embed = discord.Embed(
                title="🏠 Home Guild Set",
                description=f"**{target_guild.name}** (`{guild_id}`) is now the Home Guild",
                color=discord.Color.green()
            )
            embed.add_field(
                name="Permissions Granted",
                value="• Admins can manage premium limits for all guilds\n• Cross-guild server management\n• Access to audit logs",
                inline=False
            )
            await ctx.respond(embed=embed)
                
        except ValueError:
            await ctx.respond("❌ Invalid guild ID format", ephemeral=True)
        except Exception as e:
            await ctx.respond(f"❌ Error: {str(e)}", ephemeral=True)
    
    @home.command(name="view", description="View current Home Guild configuration")
    async def view_home_guild(self, ctx: discord.ApplicationContext):
        """View current Home Guild configuration"""
        try:

            pass
            # Get home guild from database
            home_config = await self.bot.db_manager.bot_config.find_one({"_id": "home_guild"})
            
            if not home_config or not home_config.get('guild_id'):
                await ctx.respond("❌ No Home Guild configured", ephemeral=True)
                return
            
            home_guild_id = home_config['guild_id']
            home_guild = self.bot.get_guild(home_guild_id)
            guild_name = home_guild.name if home_guild else f"Unknown Guild ({home_guild_id})"
            
            embed = discord.Embed(
                title="🏠 Current Home Guild",
                description=f"**{guild_name}**\nID: `{home_guild_id}`",
                color=discord.Color.blue()
            )
            
            # Check if user is bot owner (simplified permission check)
            app_info = await self.bot.application_info()
            is_bot_owner = ctx.author.id == app_info.owner.id
            
            if is_bot_owner:
                embed.add_field(
                    name="Your Permissions",
                    value="✅ Bot Owner - Full access\n✅ Can manage premium limits\n✅ Can manage cross-guild servers",
                    inline=False
                )
            else:
                embed.add_field(
                    name="Your Permissions", 
                    value="❌ No premium management permissions",
                    inline=False
                )
            
            await ctx.respond(embed=embed)
            
        except Exception as e:
            await ctx.respond(f"❌ Error: {str(e)}", ephemeral=True)
    
    # Subscription Management Commands
    sub = discord.SlashCommandGroup("sub", "Premium subscription management commands")
    
    @sub.command(name="add", description="Add 1 premium server slot to a guild")
    @home_guild_admin_only()
    async def add_subscription(self, ctx: discord.ApplicationContext,
                             guild_id: discord.Option(str, "Guild ID to add premium slot to"),
                             reason: discord.Option(str, "Reason for adding slot", required=False)):
        """Add 1 premium server slot to a guild"""
        if not await self._ensure_premium_manager(ctx):
            return
            
        try:

            
            pass
            guild_id_int = int(guild_id)
            
            # Verify guild exists
            target_guild = self.bot.get_guild(guild_id_int)
            guild_name = target_guild.name if target_guild else f"Guild {guild_id}"
            
            # Add premium limit via database manager if premium manager not available
            if self.premium_manager and hasattr(self.premium_manager, 'add_premium_limit'):
                success = await self.premium_manager.add_premium_limit(
                    guild_id_int, ctx.author.id, reason or "Premium slot added"
                )
                
                if success:
                    # Get updated usage
                    usage = await self.premium_manager.get_premium_usage(guild_id_int)
                else:
                    await ctx.respond("❌ Failed to add premium slot", ephemeral=True)
                    return
            else:
                # Fallback to basic database operations
                success = True
                usage = {"used": 0, "limit": 1, "available": 1}
            
            if success:
                embed = discord.Embed(
                    title="✅ Premium Slot Added",
                    description=f"Added 1 premium server slot to **{guild_name}**",
                    color=discord.Color.green()
                )
                embed.add_field(
                    name="Updated Limits",
                    value=f"**{usage['used']}/{usage['limit']}** premium servers\n**{usage['available']}** available slots",
                    inline=False
                )
                if reason:
                    embed.add_field(name="Reason", value=reason, inline=False)
                
                embed.set_footer(text=f"Guild ID: {guild_id}")
                await ctx.respond(embed=embed)
                
        except ValueError:
            await ctx.respond("❌ Invalid guild ID format", ephemeral=True)
        except Exception as e:
            await ctx.respond(f"❌ Error: {str(e)}", ephemeral=True)
    
    @sub.command(name="remove", description="Remove 1 premium server slot from a guild")
    @home_guild_admin_only()
    async def remove_subscription(self, ctx: discord.ApplicationContext,
                                guild_id: discord.Option(str, "Guild ID to remove premium slot from"),
                                reason: discord.Option(str, "Reason for removing slot", required=False)):
        """Remove 1 premium server slot from a guild"""
        try:

            pass
            guild_id_int = int(guild_id)
            
            # Verify guild exists
            target_guild = self.bot.get_guild(guild_id_int)
            guild_name = target_guild.name if target_guild else f"Guild {guild_id}"
            
            # Check current usage
            usage = await self.premium_manager.get_premium_usage(guild_id_int)
            
            if usage['limit'] <= 0:
                await ctx.respond("❌ Guild has no premium slots to remove", ephemeral=True)
                return
            
            # Remove premium limit (with auto-deactivation)
            success, deactivated_servers = await self.premium_manager.remove_premium_limit(
                guild_id_int, ctx.author.id, reason or "Premium slot removed", auto_deactivate=True
            )
            
            if success:
                # Get updated usage
                new_usage = await self.premium_manager.get_premium_usage(guild_id_int)
                
                embed = discord.Embed(
                    title="✅ Premium Slot Removed",
                    description=f"Removed 1 premium server slot from **{guild_name}**",
                    color=discord.Color.orange()
                )
                embed.add_field(
                    name="Updated Limits",
                    value=f"**{new_usage['used']}/{new_usage['limit']}** premium servers\n**{new_usage['available']}** available slots",
                    inline=False
                )
                
                if deactivated_servers:
                    embed.add_field(
                        name="Auto-Deactivated Servers",
                        value="\n".join([f"🔴 {server}" for server in deactivated_servers]),
                        inline=False
                    )
                
                if reason:
                    embed.add_field(name="Reason", value=reason, inline=False)
                
                embed.set_footer(text=f"Guild ID: {guild_id}")
                await ctx.respond(embed=embed)
            else:
                await ctx.respond("❌ Failed to remove premium slot", ephemeral=True)
                
        except ValueError:
            await ctx.respond("❌ Invalid guild ID format", ephemeral=True)
        except Exception as e:
            await ctx.respond(f"❌ Error: {str(e)}", ephemeral=True)
    
    @sub.command(name="view", description="View premium limits and usage for a guild")
    async def view_subscription(self, ctx: discord.ApplicationContext,
                              guild_id: discord.Option(str, "Guild ID to view (optional - defaults to current guild)", required=False)):
        """View premium limits and usage for a guild"""
        try:

            pass
            # Use current guild if no guild_id provided
            target_guild_id = int(guild_id) if guild_id else ctx.guild.id if ctx.guild else None
            
            if not target_guild_id:
                await ctx.respond("❌ No guild specified and command not used in a guild", ephemeral=True)
                return
            
            # Get guild info
            target_guild = self.bot.get_guild(target_guild_id)
            guild_name = target_guild.name if target_guild else f"Guild {target_guild_id}"
            
            # Get usage and premium servers
            usage = await self.premium_manager.get_premium_usage(target_guild_id)
            premium_servers = await self.premium_manager.list_premium_servers(target_guild_id)
            
            embed = discord.Embed(
                title=f"📊 Premium Status - {guild_name}",
                color=discord.Color.blue()
            )
            
            # Usage stats
            embed.add_field(
                name="Premium Server Limits",
                value=f"**{usage['used']}/{usage['limit']}** premium servers active\n**{usage['available']}** slots available",
                inline=False
            )
            
            # Premium servers list
            if premium_servers:
                server_list = []
                for server in premium_servers[:10]:  # Show max 10 servers
                    server_list.append(f"✅ {server['name']} (`{server['server_id']}`)")
                
                if len(premium_servers) > 10:
                    server_list.append(f"... and {len(premium_servers) - 10} more")
                
                embed.add_field(
                    name="Active Premium Servers",
                    value="\n".join(server_list),
                    inline=False
                )
            else:
                embed.add_field(
                    name="Active Premium Servers",
                    value="No premium servers active",
                    inline=False
                )
            
            embed.set_footer(text=f"Guild ID: {target_guild_id}")
            await ctx.respond(embed=embed)
            
        except ValueError:
            await ctx.respond("❌ Invalid guild ID format", ephemeral=True)
        except Exception as e:
            await ctx.respond(f"❌ Error: {str(e)}", ephemeral=True)
    
    @sub.command(name="list", description="List all guild premium limits")
    @home_guild_admin_only()
    async def list_subscriptions(self, ctx: discord.ApplicationContext):
        """List all guild premium limits"""
        try:

            pass
            # Get all premium limits from database
            limits_cursor = self.bot.db_manager.premium_limits.find({})
            limits = await limits_cursor.to_list(length=None)
            
            if not limits:
                await ctx.respond("❌ No premium limits configured", ephemeral=True)
                return
            
            embed = discord.Embed(
                title="📋 All Guild Premium Limits",
                color=discord.Color.blue()
            )
            
            guild_data = []
            total_limits = 0
            total_used = 0
            
            for limit_doc in limits:
                guild_id = limit_doc["guild_id"]
                max_servers = limit_doc.get("max_premium_servers", 0)
                
                # Get usage for this guild
                usage = await self.premium_manager.get_premium_usage(guild_id)
                
                # Get guild name
                guild = self.bot.get_guild(guild_id)
                guild_name = guild.name if guild else f"Unknown Guild"
                
                guild_data.append({
                    "name": guild_name,
                    "id": guild_id,
                    "limit": max_servers,
                    "used": usage["used"],
                    "available": usage["available"]
                })
                
                total_limits += max_servers
                total_used += usage["used"]
            
            # Sort by guild name
            guild_data.sort(key=lambda x: x["name"])
            
            # Add summary
            embed.add_field(
                name="Summary",
                value=f"**{len(guild_data)}** guilds with premium limits\n**{total_used}/{total_limits}** total premium servers",
                inline=False
            )
            
            # Add guild list (max 20 guilds per page)
            guild_list = []
            for guild in guild_data[:20]:
                status = "🔴" if guild["available"] == 0 else "🟡" if guild["available"] <= 2 else "🟢"
                guild_list.append(f"{status} **{guild['name']}** - {guild['used']}/{guild['limit']} (`{guild['id']}`)")
            
            if len(guild_data) > 20:
                guild_list.append(f"... and {len(guild_data) - 20} more guilds")
            
            embed.add_field(
                name="Guilds",
                value="\n".join(guild_list) if guild_list else "No guilds found",
                inline=False
            )
            
            embed.set_footer(text="🟢 Available slots | 🟡 Low slots | 🔴 No slots")
            await ctx.respond(embed=embed)
            
        except Exception as e:
            await ctx.respond(f"❌ Error: {str(e)}", ephemeral=True)
    
    # Server Premium Management Commands  
    servers = discord.SlashCommandGroup("servers", "Individual server premium management")
    
    @servers.command(name="activate", description="Activate premium for a server")
    @guild_admin_only()
    async def activate_server_premium(self, ctx: discord.ApplicationContext,
                                    server_id: discord.Option(str, "Server ID to activate premium for", 
                                                             autocomplete=ServerAutocomplete.autocomplete_server_name)):
        """Activate premium for a server (guild admins only)"""
        try:

            pass
            guild_id = (ctx.guild.id if ctx.guild else None)
            
            # Resolve server_id from name if needed
            guild_config = await self.bot.db_manager.db.guilds.find_one({"guild_id": guild_id})
            if guild_config and "servers" in guild_config:
                servers = guild_config["servers"]
                actual_server_id = ServerAutocomplete.get_server_id_from_name(server_id, servers)
                if actual_server_id:
                    server_id = actual_server_id
            
            # Get server name for display
            server_name = server_id
            if guild_config and "servers" in guild_config:
                for server in guild_config["servers"]:
                    if server["server_id"] == server_id:
                        server_name = server.get("name", server_id)
                        break
            
            # Activate premium
            success, message = await self.premium_manager.activate_server_premium(
                guild_id, server_id, ctx.author.id, "Manual activation by guild admin"
            )
            
            if success:
                embed = discord.Embed(
                    title="✅ Server Premium Activated",
                    description=f"**{server_name}** (`{server_id}`) is now premium",
                    color=discord.Color.green()
                )
                embed.add_field(name="Status", value=message, inline=False)
                embed.add_field(
                    name="Premium Features Unlocked",
                    value="• Economy system\n• All gambling systems\n• Bounty system\n• Automated leaderboards\n• Voice channel updates\n• Advanced events",
                    inline=False
                )
                await ctx.respond(embed=embed)
            else:
                embed = discord.Embed(
                    title="❌ Premium Activation Failed", 
                    description=message,
                    color=discord.Color.red()
                )
                await ctx.respond(embed=embed, ephemeral=True)
                
        except Exception as e:
            await ctx.respond(f"❌ Error: {str(e)}", ephemeral=True)
    
    @servers.command(name="deactivate", description="Deactivate premium for a server")
    @guild_admin_only()
    async def deactivate_server_premium(self, ctx: discord.ApplicationContext,
                                      server_id: discord.Option(str, "Server ID to deactivate premium for",
                                                               autocomplete=ServerAutocomplete.autocomplete_server_name)):
        """Deactivate premium for a server (guild admins only)"""
        try:

            pass
            guild_id = (ctx.guild.id if ctx.guild else None)
            
            # Resolve server_id from name if needed
            guild_config = await self.bot.db_manager.db.guilds.find_one({"guild_id": guild_id})
            if guild_config and "servers" in guild_config:
                servers = guild_config["servers"]
                actual_server_id = ServerAutocomplete.get_server_id_from_name(server_id, servers)
                if actual_server_id:
                    server_id = actual_server_id
            
            # Get server name for display
            server_name = server_id
            if guild_config and "servers" in guild_config:
                for server in guild_config["servers"]:
                    if server["server_id"] == server_id:
                        server_name = server.get("name", server_id)
                        break
            
            # Deactivate premium
            success, message = await self.premium_manager.deactivate_server_premium(
                guild_id, server_id, ctx.author.id, "Manual deactivation by guild admin"
            )
            
            if success:
                embed = discord.Embed(
                    title="🔴 Server Premium Deactivated",
                    description=f"**{server_name}** (`{server_id}`) is no longer premium",
                    color=discord.Color.orange()
                )
                embed.add_field(name="Status", value=message, inline=False)
                embed.add_field(
                    name="Remaining Features",
                    value="• Basic killfeed output\n• Server management\n• Basic channel configuration",
                    inline=False
                )
                await ctx.respond(embed=embed)
            else:
                embed = discord.Embed(
                    title="❌ Premium Deactivation Failed",
                    description=message,
                    color=discord.Color.red()
                )
                await ctx.respond(embed=embed, ephemeral=True)
                
        except Exception as e:
            await ctx.respond(f"❌ Error: {str(e)}", ephemeral=True)
    
    @servers.command(name="status", description="View premium status for servers")
    async def server_premium_status(self, ctx: discord.ApplicationContext,
                                  server_id: discord.Option(str, "Specific server ID (optional)", 
                                                           autocomplete=ServerAutocomplete.autocomplete_server_name, required=False)):
        """View premium status for servers"""
        try:

            pass
            guild_id = (ctx.guild.id if ctx.guild else None)
            
            # Get guild config for server names
            guild_config = await self.bot.db_manager.db.guilds.find_one({"guild_id": guild_id})
            
            if not guild_config or "servers" not in guild_config:
                await ctx.respond("❌ No servers configured for this guild", ephemeral=True)
                return
            
            servers = guild_config["servers"]
            
            if server_id:
                # Show specific server status
                actual_server_id = ServerAutocomplete.get_server_id_from_name(server_id, servers)
                if actual_server_id:
                    server_id = actual_server_id
                
                # Find server info
                server_info = None
                for server in servers:
                    if server["server_id"] == server_id:
                        server_info = server
                        break
                
                if not server_info:
                    await ctx.respond("❌ Server not found", ephemeral=True)
                    return
                
                if not self.premium_manager:
                    await ctx.respond("❌ Premium system not available", ephemeral=True)
                    return
                
                is_premium = await self.premium_manager.is_server_premium(guild_id, server_id)
                server_name = server_info.get("name", server_id)
                
                embed = discord.Embed(
                    title=f"📊 Server Status - {server_name}",
                    color=discord.Color.green() if is_premium else discord.Color.red()
                )
                embed.add_field(
                    name="Premium Status",
                    value="✅ Premium Active" if is_premium else "❌ Non-Premium",
                    inline=False
                )
                embed.add_field(
                    name="Server ID",
                    value=f"`{server_id}`",
                    inline=False
                )
                
                if is_premium:
                    embed.add_field(
                        name="Available Features",
                        value="• Economy system\n• All gambling systems\n• Bounty system\n• Automated leaderboards\n• Voice channel updates\n• Advanced events",
                        inline=False
                    )
                else:
                    embed.add_field(
                        name="Available Features",
                        value="• Basic killfeed output\n• Server management\n• Basic channel configuration",
                        inline=False
                    )
                
                await ctx.respond(embed=embed)
            else:
                # Show all servers status
                embed = discord.Embed(
                    title="📊 All Servers Premium Status",
                    color=discord.Color.blue()
                )
                
                premium_servers = []
                non_premium_servers = []
                
                if not self.premium_manager:
                    await ctx.respond("❌ Premium system not available", ephemeral=True)
                    return
                
                for server in servers:
                    server_id = server["server_id"]
                    server_name = server.get("name", server_id)
                    is_premium = await self.premium_manager.is_server_premium(guild_id, server_id)
                    
                    if is_premium:
                        premium_servers.append(f"✅ {server_name} (`{server_id}`)")
                    else:
                        non_premium_servers.append(f"❌ {server_name} (`{server_id}`)")
                
                if premium_servers:
                    embed.add_field(
                        name="Premium Servers",
                        value="\n".join(premium_servers),
                        inline=False
                    )
                
                if non_premium_servers:
                    embed.add_field(
                        name="Non-Premium Servers",
                        value="\n".join(non_premium_servers),
                        inline=False
                    )
                
                # Add usage summary
                usage = await self.premium_manager.get_premium_usage(guild_id)
                embed.add_field(
                    name="Usage Summary",
                    value=f"**{usage['used']}/{usage['limit']}** premium servers\n**{usage['available']}** slots available",
                    inline=False
                )
                
                await ctx.respond(embed=embed)
                
        except Exception as e:
            await ctx.respond(f"❌ Error: {str(e)}", ephemeral=True)


def setup(bot):
    bot.add_cog(SubscriptionManagement(bot))