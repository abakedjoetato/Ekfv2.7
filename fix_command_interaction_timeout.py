"""
Fix Command Interaction Timeout - Comprehensive solution for "Unknown interaction" errors
Addresses Discord interaction timeout issues across all command handlers
"""

import os
import re
import asyncio

def fix_command_interaction_timeout():
    """Fix all command interaction timeout issues"""
    
    # Files that need fixing
    command_files = [
        'bot/cogs/stats.py',
        'bot/cogs/linking.py',
        'bot/cogs/admin_channels.py',
        'bot/cogs/core.py',
        'bot/cogs/premium.py',
        'bot/cogs/bounty.py',
        'bot/cogs/leaderboard.py'
    ]
    
    fixes_applied = 0
    
    for file_path in command_files:
        if not os.path.exists(file_path):
            continue
            
        try:
            with open(file_path, 'r') as f:
                content = f.read()
            
            original_content = content
            
            # Fix 1: Replace problematic defer with immediate response pattern
            if 'await asyncio.wait_for(ctx.defer(), timeout=' in content:
                content = re.sub(
                    r'await asyncio\.wait_for\(ctx\.defer\(\), timeout=[\d.]+\)',
                    'await ctx.defer()',
                    content
                )
                print(f"Fixed defer timeout pattern in {file_path}")
            
            # Fix 2: Add try-except around defer calls to handle expired interactions
            def add_defer_protection(match):
                full_match = match.group(0)
                indent = match.group(1) if match.groups() else '        '
                
                # Replace with protected defer
                protected_defer = f"""{indent}try:
{indent}    await ctx.defer()
{indent}except discord.errors.NotFound:
{indent}    # Interaction already expired, respond immediately
{indent}    await ctx.respond("Processing...", ephemeral=True)
{indent}except Exception as e:
{indent}    logger.error(f"Failed to defer interaction: {{e}}")
{indent}    await ctx.respond("Processing...", ephemeral=True)"""
                
                return protected_defer
            
            # Pattern to match defer calls
            defer_pattern = r'(\s*)await ctx\.defer\(\)'
            content = re.sub(defer_pattern, add_defer_protection, content)
            
            # Fix 3: Add interaction validity checks before followup
            def add_interaction_check(match):
                full_match = match.group(0)
                indent = match.group(1) if match.groups() else '        '
                
                # Add check before followup
                protected_followup = f"""{indent}try:
{indent}    if hasattr(ctx, 'response') and not ctx.response.is_done():
{indent}        await ctx.respond({match.group(2)})
{indent}    else:
{indent}        await ctx.followup.send({match.group(2)})
{indent}except discord.errors.NotFound:
{indent}    logger.warning("Interaction expired, cannot send response")
{indent}except Exception as e:
{indent}    logger.error(f"Failed to send response: {{e}}")"""
                
                return protected_followup
            
            # Pattern to match followup calls
            followup_pattern = r'(\s*)await ctx\.followup\.send\(([^)]+)\)'
            content = re.sub(followup_pattern, add_interaction_check, content)
            
            # Fix 4: Add timeout protection to database operations
            content = re.sub(
                r'await cursor\.to_list\(length=\d+\)',
                'await asyncio.wait_for(cursor.to_list(length=10), timeout=2.0)',
                content
            )
            
            # Fix 5: Add early response for slow operations
            if 'sessions = await asyncio.wait_for(' in content:
                content = re.sub(
                    r'sessions = await asyncio\.wait_for\([^)]+\)',
                    '''sessions = []
                try:
                    sessions = await asyncio.wait_for(cursor.to_list(length=10), timeout=1.0)
                except asyncio.TimeoutError:
                    # Respond immediately with loading message, then update
                    loading_embed = discord.Embed(
                        title="🔄 Loading...",
                        description="Fetching player data...",
                        color=0x3498db
                    )
                    await ctx.edit_original_response(embed=loading_embed)
                    
                    # Try longer timeout
                    try:
                        sessions = await asyncio.wait_for(cursor.to_list(length=10), timeout=5.0)
                    except asyncio.TimeoutError:
                        error_embed = discord.Embed(
                            title="⚠️ Database Timeout",
                            description="Database is currently slow. Please try again.",
                            color=0xe74c3c
                        )
                        await ctx.edit_original_response(embed=error_embed)
                        return''',
                    content
                )
            
            # Save the fixed file
            if content != original_content:
                with open(file_path, 'w') as f:
                    f.write(content)
                fixes_applied += 1
                print(f"✅ Fixed interaction timeouts in {file_path}")
            
        except Exception as e:
            print(f"❌ Error fixing {file_path}: {e}")
    
    print(f"\n✅ Applied fixes to {fixes_applied} files")
    return fixes_applied

if __name__ == "__main__":
    fix_command_interaction_timeout()