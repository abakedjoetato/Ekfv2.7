"""
Fix /online Command - Replace problematic implementation with optimized version
"""

def create_fixed_online_command():
    """Create fixed /online command implementation"""
    return '''            # Create simple embed
            if not sessions:
                embed = discord.Embed(
                    title="🌐 No Players Online",
                    description="No players are currently online on any server.",
                    color=0xFFAA00,
                    timestamp=datetime.now(timezone.utc)
                )
            else:
                # Group by server
                servers = {}
                for session in sessions:
                    server_name = session.get('server_name', 'Unknown')
                    player_name = session.get('character_name') or session.get('player_name', 'Unknown')
                    if server_name not in servers:
                        servers[server_name] = []
                    servers[server_name].append(player_name)
                
                total_players = len(sessions)
                embed = discord.Embed(
                    title=f"🌐 Online Players ({total_players})",
                    color=0x00FF00,
                    timestamp=datetime.now(timezone.utc)
                )
                
                for server_name, players in servers.items():
                    player_list = []
                    for i, player in enumerate(players[:15], 1):
                        player_list.append(f"`{i:2d}.` **{player}**")
                    
                    embed.add_field(
                        name=f"🌐 {server_name} ({len(players)} online)",
                        value="\\n".join(player_list) if player_list else "No players",
                        inline=False
                    )
            
            embed.set_footer(text="Updated every 3 minutes")
            
            # Send response
            try:
                await ctx.followup.send(embed=embed)
            except discord.errors.NotFound:
                logger.warning("Interaction expired, cannot send online response")
            except Exception as e:
                logger.error(f"Failed to send online response: {e}")
            
        except Exception as e:
            logger.error(f"Error in /online command: {e}")
            try:
                await ctx.followup.send("An error occurred while retrieving online players.", ephemeral=True)
            except:
                pass'''

if __name__ == "__main__":
    print("Fixed online command implementation created")