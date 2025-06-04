"""
Cache Management Commands - Administrative Cache Control
Provides commands for cache monitoring and management
"""

import discord
import discord
from discord.ext import commands
from discord import SlashCommandGroup
import asyncio
import logging
from datetime import datetime
from typing import Dict, Any

logger = logging.getLogger(__name__)

class CacheManagement(discord.Cog):
    """Administrative commands for cache system management"""
    
    def __init__(self, bot):
        self.bot = bot
    
    async def check_premium_access(self, guild_id: int) -> bool:
        """Check if guild has premium access - unified validation"""
        try:

            pass
            if hasattr(self.bot, 'premium_manager_v2'):
                return await self.bot.premium_manager_v2.has_premium_access(guild_id)
            else:
                return False
        except Exception as e:
            logger.error(f"Premium access check failed: {e}")
            return False
    
    cache_group = SlashCommandGroup(
        name="cache",
        description="Cache management commands (Admin only)"
    )
    
    @cache_group.command(
        name="stats",
        description="View cache performance statistics"
    )
    async def cache_stats(self, ctx: discord.ApplicationContext):
        """Display comprehensive cache performance metrics"""
        if not await self._check_admin_permissions(ctx):
            return
        
        try:

        
            pass
            # Get cache statistics
            if hasattr(self.bot.db_manager, 'get_cache_stats'):
                stats = await self.bot.db_manager.get_cache_stats()
            else:
                await ctx.respond("❌ Cache system not available", ephemeral=True)
                return
            
            # Create statistics embed
            embed = discord.Embed(
                title="🚀 Cache Performance Statistics",
                color=0x00ff88,
                timestamp=datetime.utcnow()
            )
            
            # Overall performance
            embed.add_field(
                name="📊 Overall Performance",
                value=f"**Hit Rate:** {stats['hit_rate']}%\n"
                      f"**Total Hits:** {stats['hits']:,}\n"
                      f"**Total Misses:** {stats['misses']:,}\n"
                      f"**Total Entries:** {stats['total_entries']:,}",
                inline=False
            )
            
            # Cache operations
            embed.add_field(
                name="🔄 Cache Operations",
                value=f"**Evictions:** {stats['evictions']:,}\n"
                      f"**Invalidations:** {stats['invalidations']:,}",
                inline=True
            )
            
            # Cache breakdown by type
            cache_breakdown = ""
            for cache_type, details in stats['cache_details'].items():
                cache_breakdown += f"**{cache_type}:** {details['entries']} entries\n"
            
            if cache_breakdown:
                embed.add_field(
                    name="📋 Cache Breakdown",
                    value=cache_breakdown,
                    inline=True
                )
            
            # Performance recommendation
            if stats['hit_rate'] >= 90:
                performance_status = "🟢 Excellent"
            elif stats['hit_rate'] >= 80:
                performance_status = "🟡 Good"
            else:
                performance_status = "🔴 Needs Optimization"
            
            embed.add_field(
                name="⚡ Performance Status",
                value=performance_status,
                inline=False
            )
            
            embed.set_footer(text=f"Guild: {ctx.guild.name if ctx.guild else 'Unknown Guild'}")
            
            await ctx.respond(embed=embed, ephemeral=True)
            
        except Exception as e:
            logger.error(f"Error getting cache stats: {e}")
            await ctx.respond("❌ Error retrieving cache statistics", ephemeral=True)
    
    @cache_group.command(
        name="clear",
        description="Clear cache for this guild (Admin only)"
    )
    async def cache_clear(self, ctx: discord.ApplicationContext):
        """Clear all cached data for the current guild"""
        if not await self._check_admin_permissions(ctx):
            return
        
        try:

        
            pass
            guild_id = ctx.guild.id if ctx.guild else 0
            
            # Confirm action
            embed = discord.Embed(
                title="⚠️ Clear Guild Cache",
                description=f"This will clear all cached data for **{ctx.guild.name if ctx.guild else 'Unknown Guild'}**.\n"
                           f"Data will be automatically refreshed from database as needed.\n\n"
                           f"**This action cannot be undone.**",
                color=0xffaa00
            )
            
            view = ClearCacheView()
            await ctx.respond(embed=embed, view=view, ephemeral=True)
            
            # Wait for user response
            await view.wait()
            
            if view.confirmed:
                # Clear guild cache
                if hasattr(self.bot.db_manager, 'invalidate_all_cache'):
                    await self.bot.db_manager.invalidate_all_cache(guild_id)
                
                success_embed = discord.Embed(
                    title="✅ Cache Cleared",
                    description=f"All cached data for **{ctx.guild.name if ctx.guild else 'Unknown Guild'}** has been cleared.",
                    color=0x00ff88
                )
                await ctx.edit(embed=success_embed, view=None)
                
                logger.info(f"Cache cleared for guild {guild_id} by {ctx.author.id}")
            
        except Exception as e:
            logger.error(f"Error clearing cache: {e}")
            await ctx.respond("❌ Error clearing cache", ephemeral=True)
    
    @cache_group.command(
        name="cleanup",
        description="Clean up expired cache entries (Admin only)"
    )
    async def cache_cleanup(self, ctx: discord.ApplicationContext):
        """Manually trigger cleanup of expired cache entries"""
        if not await self._check_admin_permissions(ctx):
            return
        
        try:

        
            pass
            # Perform cleanup
            if hasattr(self.bot.db_manager, 'cleanup_cache'):
                cleaned_count = await self.bot.db_manager.cleanup_cache()
            else:
                await ctx.respond("❌ Cache system not available", ephemeral=True)
                return
            
            embed = discord.Embed(
                title="🧹 Cache Cleanup Complete",
                description=f"Cleaned up **{cleaned_count}** expired cache entries.",
                color=0x00ff88,
                timestamp=datetime.utcnow()
            )
            
            await ctx.respond(embed=embed, ephemeral=True)
            logger.info(f"Manual cache cleanup performed by {ctx.author.id}, cleaned {cleaned_count} entries")
            
        except Exception as e:
            logger.error(f"Error during cache cleanup: {e}")
            await ctx.respond("❌ Error during cache cleanup", ephemeral=True)
    
    @cache_group.command(
        name="refresh",
        description="Refresh premium cache for this guild (Admin only)"
    )
    async def cache_refresh_premium(self, ctx: discord.ApplicationContext):
        """Manually refresh premium cache for the current guild"""
        if not await self._check_admin_permissions(ctx):
            return
        
        try:

        
            pass
            guild_id = ctx.guild.id if ctx.guild else 0
            
            # Refresh premium cache
            if hasattr(self.bot.db_manager, 'invalidate_premium_cache'):
                await self.bot.db_manager.invalidate_premium_cache(guild_id)
            
            embed = discord.Embed(
                title="🔄 Premium Cache Refreshed",
                description=f"Premium status cache for **{ctx.guild.name if ctx.guild else 'Unknown Guild'}** has been refreshed.\n"
                           f"Next premium check will use fresh data from database.",
                color=0x00ff88,
                timestamp=datetime.utcnow()
            )
            
            await ctx.respond(embed=embed, ephemeral=True)
            logger.info(f"Premium cache refreshed for guild {guild_id} by {ctx.author.id}")
            
        except Exception as e:
            logger.error(f"Error refreshing premium cache: {e}")
            await ctx.respond("❌ Error refreshing premium cache", ephemeral=True)
    
    async def _check_admin_permissions(self, ctx: discord.ApplicationContext) -> bool:
        """Check if user has administrator permissions"""
        if not ctx.guild or not ctx.author.guild_permissions or not ctx.author.guild_permissions.administrator:
            embed = discord.Embed(
                title="❌ Access Denied",
                description="You need **Administrator** permissions to use cache management commands.",
                color=0xff0000
            )
            await ctx.respond(embed=embed, ephemeral=True)
            return False
        return True


class ClearCacheView(discord.ui.View):
    """Confirmation view for cache clearing"""
    
    def __init__(self):
        super().__init__(timeout=30)
        self.confirmed = False
    
    @discord.ui.button(
        label="Clear Cache",
        style=discord.ButtonStyle.danger,
        emoji="🗑️"
    )
    async def confirm_clear(self, button: discord.ui.Button, interaction: discord.Interaction):
        self.confirmed = True
        self.stop()
    
    @discord.ui.button(
        label="Cancel",
        style=discord.ButtonStyle.secondary,
        emoji="❌"
    )
    async def cancel_clear(self, button: discord.ui.Button, interaction: discord.Interaction):
        self.confirmed = False
        self.stop()
        
        embed = discord.Embed(
            title="❌ Cache Clear Cancelled",
            description="No changes were made.",
            color=0x888888
        )
        await interaction.response.edit_message(embed=embed, view=None)


def setup(bot):
    bot.add_cog(CacheManagement(bot))