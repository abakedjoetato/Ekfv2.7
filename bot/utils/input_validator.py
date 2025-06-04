"""
Input Validation Framework
Comprehensive validation for all user inputs
"""

import discord
from functools import wraps
import re
from typing import Any, Optional

class InputValidator:
    """Comprehensive input validation"""
    
    @staticmethod
    def validate_guild_id(guild_id: Any) -> Optional[int]:
        """Validate guild ID"""
        try:
            return int(guild_id)
        except (ValueError, TypeError):
            return None
            
    @staticmethod
    def validate_server_id(server_id: Any) -> Optional[str]:
        """Validate server ID"""
        if isinstance(server_id, str) and server_id.isdigit():
            return server_id
        return None
        
    @staticmethod
    def validate_player_name(name: Any) -> Optional[str]:
        """Validate player name"""
        if not isinstance(name, str):
            return None
            
        # Remove dangerous characters
        clean_name = re.sub(r'[<>@#&]', '', name)
        
        if len(clean_name) < 2 or len(clean_name) > 32:
            return None
            
        return clean_name
        
    @staticmethod
    def validate_amount(amount: Any, min_val: int = 1, max_val: int = 1000000) -> Optional[int]:
        """Validate numeric amounts"""
        try:
            val = int(amount)
            if min_val <= val <= max_val:
                return val
        except (ValueError, TypeError):
            pass
        return None

def validate_input(**validation_rules):
    """Decorator for input validation"""
    def decorator(func):
        @wraps(func)
        async def wrapper(self, ctx: discord.ApplicationContext, *args, **kwargs):
            # Validate each parameter according to rules
            for param_name, rule in validation_rules.items():
                if param_name in kwargs:
                    value = kwargs[param_name]
                    
                    if rule == 'guild_id':
                        validated = InputValidator.validate_guild_id(value)
                    elif rule == 'server_id':
                        validated = InputValidator.validate_server_id(value)
                    elif rule == 'player_name':
                        validated = InputValidator.validate_player_name(value)
                    elif rule.startswith('amount'):
                        parts = rule.split(':')
                        min_val = int(parts[1]) if len(parts) > 1 else 1
                        max_val = int(parts[2]) if len(parts) > 2 else 1000000
                        validated = InputValidator.validate_amount(value, min_val, max_val)
                    else:
                        validated = value
                        
                    if validated is None:
                        embed = discord.Embed(
                            title="Invalid Input",
                            description=f"Invalid {param_name}: {value}",
                            color=0xff0000
                        )
                        await ctx.respond(embed=embed, ephemeral=True)
                        return
                        
                    kwargs[param_name] = validated
                    
            return await func(self, ctx, *args, **kwargs)
        return wrapper
    return decorator
