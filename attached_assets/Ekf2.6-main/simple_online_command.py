"""
Simple replacement for the /online command in stats.py
"""

SIMPLE_ONLINE_COMMAND = '''
    @discord.slash_command(name="online", description="Show currently online players")
    async def online(self, ctx: discord.ApplicationContext):
        """Show currently online players"""
        try:
            guild_id = ctx.guild.id
            
            # Get online players from database
            sessions = await self.bot.db_manager.player_sessions.find({
                'guild_id': guild_id,
                'state': 'online'
            }).to_list(length=50)
            
            # Create embed
            embed = discord.Embed(
                title="🌐 Online Players",
                description=f"**{len(sessions)}** players currently online",
                color=0x32CD32
            )
            
            if sessions:
                player_lines = []
                for i, session in enumerate(sessions[:20], 1):
                    player_id = session.get('player_id', 'Unknown')
                    player_name = player_id[:8] + '...' if len(player_id) > 8 else player_id
                    server_name = session.get('server_name', 'Unknown')
                    player_lines.append(f"`{i:2d}.` **{player_name}** ({server_name})")
                
                embed.add_field(
                    name="📋 Players Online",
                    value="\\n".join(player_lines),
                    inline=False
                )
            else:
                embed.add_field(
                    name="📭 No Players Online",
                    value="No players are currently online.",
                    inline=False
                )
            
            await ctx.respond(embed=embed)
            
        except Exception as e:
            await ctx.respond("Failed to fetch online players.", ephemeral=True)
'''