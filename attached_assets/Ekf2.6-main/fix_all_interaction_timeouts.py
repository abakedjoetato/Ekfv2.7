"""
Fix All Interaction Timeout Issues - Comprehensive solution for Discord command handlers
Prevents "Unknown interaction" errors across all command files
"""

import os
import re

def fix_all_interaction_timeouts():
    """Fix interaction timeout issues in all command files"""
    
    command_files = [
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
            
            # Fix 1: Ensure proper defer handling in all slash commands
            def fix_defer_pattern(match):
                full_match = match.group(0)
                
                # Replace problematic defer patterns
                if 'await asyncio.wait_for(ctx.defer()' in full_match:
                    return full_match.replace(
                        'await asyncio.wait_for(ctx.defer(), timeout=2.0)',
                        '''try:
            await ctx.defer()
        except discord.errors.NotFound:
            return
        except Exception as e:
            logger.error(f"Failed to defer: {e}")
            return'''
                    )
                
                return full_match
            
            # Pattern to find slash commands with defer issues
            defer_pattern = r'async def \w+\(.*?ctx.*?\):.*?defer.*?(?=async def|\Z)'
            content = re.sub(defer_pattern, fix_defer_pattern, content, flags=re.DOTALL)
            
            # Fix 2: Replace problematic followup patterns
            content = re.sub(
                r'await ctx\.followup\.send\(',
                '''try:
            await ctx.followup.send(''',
                content
            )
            
            # Add corresponding except blocks for followup calls
            content = re.sub(
                r'(try:\s*await ctx\.followup\.send\([^}]+?\))\s*\n',
                r'''\1
        except discord.errors.NotFound:
            pass  # Interaction expired
        except Exception as e:
            logger.error(f"Failed to send followup: {e}")
''',
                content,
                flags=re.MULTILINE
            )
            
            # Fix 3: Add interaction validity checks
            def add_interaction_check(match):
                line = match.group(0)
                if 'ctx.respond(' in line and 'try:' not in line:
                    return f'''        try:
            {line.strip()}
        except discord.errors.NotFound:
            pass  # Interaction expired'''
                return line
            
            # Pattern for ctx.respond calls
            respond_pattern = r'^\s*await ctx\.respond\([^)]+\)'
            content = re.sub(respond_pattern, add_interaction_check, content, flags=re.MULTILINE)
            
            # Save if changes were made
            if content != original_content:
                with open(file_path, 'w') as f:
                    f.write(content)
                fixes_applied += 1
                print(f"✅ Fixed interaction timeouts in {file_path}")
            
        except Exception as e:
            print(f"❌ Error fixing {file_path}: {e}")
    
    print(f"\n✅ Applied interaction timeout fixes to {fixes_applied} files")
    return fixes_applied

def fix_specific_command_patterns():
    """Fix specific patterns that cause interaction timeouts"""
    
    # Fix linking.py patterns
    if os.path.exists('bot/cogs/linking.py'):
        with open('bot/cogs/linking.py', 'r') as f:
            content = f.read()
        
        # Replace database operation patterns with timeout protection
        content = re.sub(
            r'await self\.bot\.db_manager\.',
            'await asyncio.wait_for(self.bot.db_manager.',
            content
        )
        
        # Add timeout parameter
        content = re.sub(
            r'await asyncio\.wait_for\(self\.bot\.db_manager\.([^,]+),',
            r'await asyncio.wait_for(self.bot.db_manager.\1, timeout=3.0,',
            content
        )
        
        with open('bot/cogs/linking.py', 'w') as f:
            f.write(content)
        print("✅ Fixed linking.py database timeout patterns")
    
    # Fix admin_channels.py patterns
    if os.path.exists('bot/cogs/admin_channels.py'):
        with open('bot/cogs/admin_channels.py', 'r') as f:
            content = f.read()
        
        # Ensure immediate defer in channel configuration commands
        if '@discord.slash_command' in content and 'await ctx.defer()' not in content:
            content = re.sub(
                r'(@discord\.slash_command[^)]*\)\s*async def \w+\([^)]+\):\s*"""[^"]*"""\s*)',
                r'''\1
        try:
            await ctx.defer()
        except discord.errors.NotFound:
            return
        ''',
                content
            )
        
        with open('bot/cogs/admin_channels.py', 'w') as f:
            f.write(content)
        print("✅ Fixed admin_channels.py defer patterns")

if __name__ == "__main__":
    fix_all_interaction_timeouts()
    fix_specific_command_patterns()