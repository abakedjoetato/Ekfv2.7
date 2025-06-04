"""
Comprehensive fix for /online command "Unknown interaction" error
"""

import os
import re

def fix_online_command():
    """Fix the /online command with proper interaction handling"""
    
    # Read the current stats.py file
    with open('bot/cogs/stats.py', 'r') as f:
        content = f.read()
    
    # Find the online command and replace it entirely
    online_command_pattern = r'@discord\.slash_command\(description="View currently online players"\)\s*async def online\(self, ctx: discord\.ApplicationContext\):.*?(?=@discord\.slash_command|\Z)'
    
    # New online command implementation
    new_online_command = '''@discord.slash_command(description="View currently online players")
    async def online(self, ctx: discord.ApplicationContext):
        """Show currently online players"""
        import asyncio
        logger.info(f"Starting /online command for guild {ctx.guild.id if ctx.guild else 'None'}")
        
        # Immediate defer to prevent Discord timeout
        try:
            await ctx.defer()
            logger.info("Context deferred successfully")
        except discord.errors.NotFound:
            logger.error("Interaction already expired before defer")
            return
        except Exception as e:
            logger.error(f"Failed to defer interaction: {e}")
            return
        
        try:
            if not ctx.guild:
                await ctx.followup.send("This command can only be used in a server!", ephemeral=True)
                return
                
            guild_id = ctx.guild.id
            logger.info(f"Processing /online for guild {guild_id}")
            
            # Fast database query with timeout protection
            sessions = []
            try:
                logger.info("Attempting database query")
                cursor = self.bot.db_manager.player_sessions.find(
                    {'guild_id': guild_id, 'state': 'online'},
                    {'character_name': 1, 'server_name': 1, '_id': 0}
                ).limit(10)
                
                sessions = await asyncio.wait_for(cursor.to_list(length=10), timeout=2.0)
                logger.info(f"Query successful: {len(sessions)} sessions found")
                
            except asyncio.TimeoutError:
                logger.warning("Database query timed out")
                embed = discord.Embed(
                    title="🌐 Online Players",
                    description="Database is currently slow. Please try again in a moment.",
                    color=0xFFAA00
                )
                await ctx.followup.send(embed=embed, ephemeral=True)
                return
                
            except Exception as e:
                logger.error(f"Database query failed: {e}")
                embed = discord.Embed(
                    title="❌ Error",
                    description="Unable to fetch player data. Please try again.",
                    color=0xFF0000
                )
                await ctx.followup.send(embed=embed, ephemeral=True)
                return
            
            # Create response embed
            if not sessions:
                embed = discord.Embed(
                    title="🌐 Online Players",
                    description="No players are currently online.",
                    color=0x808080
                )
            else:
                # Group by server
                servers = {}
                for session in sessions:
                    server_name = session.get('server_name', 'Unknown Server')
                    character_name = session.get('character_name', 'Unknown Player')
                    
                    if server_name not in servers:
                        servers[server_name] = []
                    servers[server_name].append(character_name)
                
                embed = discord.Embed(
                    title="🌐 Online Players",
                    description=f"Found {len(sessions)} players online",
                    color=0x00FF00
                )
                
                for server_name, players in servers.items():
                    player_list = "\\n".join([f"• {player}" for player in players[:10]])
                    embed.add_field(
                        name=f"🎮 {server_name}",
                        value=player_list,
                        inline=False
                    )
            
            embed.set_footer(text="Real-time player data")
            
            # Send response
            try:
                await ctx.followup.send(embed=embed)
                logger.info("Response sent successfully")
            except discord.errors.NotFound:
                logger.warning("Interaction expired, cannot send response")
            except Exception as e:
                logger.error(f"Failed to send response: {e}")
                
        except Exception as e:
            logger.error(f"Error in /online command: {e}")
            try:
                error_embed = discord.Embed(
                    title="❌ Command Error",
                    description="An unexpected error occurred. Please try again.",
                    color=0xFF0000
                )
                await ctx.followup.send(embed=error_embed, ephemeral=True)
            except:
                pass  # Interaction may have expired

'''
    
    # Replace the command
    content = re.sub(online_command_pattern, new_online_command, content, flags=re.DOTALL)
    
    # Write the fixed file
    with open('bot/cogs/stats.py', 'w') as f:
        f.write(content)
    
    print("✅ Fixed /online command with proper interaction handling")

if __name__ == "__main__":
    fix_online_command()