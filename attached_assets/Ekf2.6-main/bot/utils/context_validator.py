"""
Context Validation Utility - Production Safety Layer
Provides comprehensive null safety and validation for Discord contexts
"""

import discord
from typing import Optional, Tuple
import logging

logger = logging.getLogger(__name__)

class ContextValidator:
    """Production-grade context validation with comprehensive error handling"""
    
    @staticmethod
    def validate_guild_context(ctx: discord.ApplicationContext) -> Tuple[bool, Optional[int], Optional[str]]:
        """
        Validate guild context and return (is_valid, guild_id, error_message)
        
        Returns:
            Tuple[bool, Optional[int], Optional[str]]: (success, guild_id, error_message)
        """
        try:
            if not ctx.guild:
                return False, None, "❌ This command must be used in a server"
            
            if not (ctx.guild.id if ctx.guild else None):
                return False, None, "❌ Unable to identify server"
                
            return True, (ctx.guild.id if ctx.guild else None), None
            
        except Exception as e:
            logger.error(f"Context validation error: {e}")
            return False, None, "❌ Context validation failed"
    
    @staticmethod
    def validate_user_context(ctx: discord.ApplicationContext) -> Tuple[bool, Optional[int], Optional[str]]:
        """
        Validate user context and return (is_valid, user_id, error_message)
        
        Returns:
            Tuple[bool, Optional[int], Optional[str]]: (success, user_id, error_message)
        """
        try:
            if not ctx.user:
                return False, None, "❌ Unable to identify user"
            
            if not ctx.user.id:
                return False, None, "❌ Invalid user ID"
                
            return True, ctx.user.id, None
            
        except Exception as e:
            logger.error(f"User context validation error: {e}")
            return False, None, "❌ User validation failed"
    
    @staticmethod
    async def validate_and_respond(ctx: discord.ApplicationContext, require_guild: bool = True, require_user: bool = True) -> Tuple[bool, Optional[int], Optional[int]]:
        """
        Comprehensive context validation with automatic error responses
        
        Args:
            ctx: Discord application context
            require_guild: Whether guild context is required
            require_user: Whether user context is required
            
        Returns:
            Tuple[bool, Optional[int], Optional[int]]: (success, guild_id, user_id)
        """
        guild_id = None
        user_id = None
        
        try:
            # Validate guild if required
            if require_guild:
                is_valid, guild_id, error_msg = ContextValidator.validate_guild_context(ctx)
                if not is_valid:
                    await ctx.respond(error_msg, ephemeral=True)
                    return False, None, None
            
            # Validate user if required
            if require_user:
                is_valid, user_id, error_msg = ContextValidator.validate_user_context(ctx)
                if not is_valid:
                    await ctx.respond(error_msg, ephemeral=True)
                    return False, None, None
            
            return True, guild_id, user_id
            
        except Exception as e:
            logger.error(f"Context validation and response error: {e}")
            try:
                await ctx.respond("❌ System validation error occurred", ephemeral=True)
            except:
                pass  # Prevent cascading failures
            return False, None, None

def guild_required(func):
    """Decorator to ensure guild context is available"""
    async def wrapper(self, ctx: discord.ApplicationContext, *args, **kwargs):
        is_valid, guild_id, user_id = await ContextValidator.validate_and_respond(ctx, require_guild=True, require_user=True)
        if not is_valid:
            return
        
        return await func(self, ctx, *args, **kwargs)
    return wrapper

def premium_required(func):
    """Decorator to ensure premium access before command execution"""
    async def wrapper(self, ctx: discord.ApplicationContext, *args, **kwargs):
        is_valid, guild_id, user_id = await ContextValidator.validate_and_respond(ctx, require_guild=True, require_user=True)
        if not is_valid:
            return
        
        # Check premium access if method exists
        if hasattr(self, 'check_premium_server'):
            try:
                has_premium = await self.check_premium_server(guild_id)
                if not has_premium:
                    embed = discord.Embed(
                        title="🔒 Premium Feature",
                        description="This feature requires a premium server subscription.",
                        color=discord.Color.red()
                    )
                    embed.add_field(
                        name="How to Get Premium",
                        value="Contact server administrators to upgrade this server to premium.",
                        inline=False
                    )
                    await ctx.respond(embed=embed, ephemeral=True)
                    return
            except Exception as e:
                logger.error(f"Premium check error: {e}")
                await ctx.respond("❌ Premium verification failed", ephemeral=True)
                return
        
        # Inject validated IDs
        ctx._validated_guild_id = guild_id
        ctx._validated_user_id = user_id
        
        return await func(self, ctx, *args, **kwargs)
    return wrapper