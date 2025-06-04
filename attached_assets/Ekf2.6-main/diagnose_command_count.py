"""
Diagnose Command Count - Find why we're dropping from 32 to 29 commands
"""

import os
import sys
import traceback

# Add the project root to the path
sys.path.insert(0, os.getcwd())

def check_cog_files():
    """Check which cog files exist and can be imported"""
    
    expected_cogs = [
        'bot.cogs.core',
        'bot.cogs.admin_channels', 
        'bot.cogs.admin_batch',
        'bot.cogs.linking',
        'bot.cogs.stats',
        'bot.cogs.leaderboards_fixed',
        'bot.cogs.automated_leaderboard',
        'bot.cogs.economy',
        'bot.cogs.professional_casino',
        'bot.cogs.bounties',
        'bot.cogs.factions',
        'bot.cogs.subscription_management',
        'bot.cogs.premium',
        'bot.cogs.parsers',
        'bot.cogs.cache_management'
    ]
    
    missing_cogs = []
    import_failed_cogs = []
    successful_cogs = []
    
    for cog_module in expected_cogs:
        file_path = cog_module.replace('.', '/') + '.py'
        
        if not os.path.exists(file_path):
            missing_cogs.append(cog_module)
            continue
            
        try:
            # Try to import the module
            __import__(cog_module)
            successful_cogs.append(cog_module)
        except Exception as e:
            import_failed_cogs.append((cog_module, str(e)))
    
    print("📊 Cog Status Report:")
    print(f"✅ Successful imports: {len(successful_cogs)}")
    print(f"❌ Missing files: {len(missing_cogs)}")
    print(f"💥 Import failures: {len(import_failed_cogs)}")
    
    if missing_cogs:
        print("\n📂 Missing cog files:")
        for cog in missing_cogs:
            print(f"  - {cog}")
    
    if import_failed_cogs:
        print("\n💥 Import failures:")
        for cog, error in import_failed_cogs:
            print(f"  - {cog}: {error}")
    
    return len(successful_cogs), missing_cogs, import_failed_cogs

def count_commands_per_cog():
    """Count how many commands each cog should have"""
    
    cog_command_counts = {}
    
    # Check each existing cog file for slash commands
    cog_files = [
        ('bot/cogs/core.py', 'Core'),
        ('bot/cogs/admin_channels.py', 'AdminChannels'),
        ('bot/cogs/linking.py', 'Linking'),
        ('bot/cogs/stats.py', 'Stats'),
        ('bot/cogs/premium.py', 'Premium')
    ]
    
    total_expected = 0
    
    for file_path, cog_name in cog_files:
        if os.path.exists(file_path):
            with open(file_path, 'r') as f:
                content = f.read()
            
            # Count @discord.slash_command decorators
            command_count = content.count('@discord.slash_command')
            cog_command_counts[cog_name] = command_count
            total_expected += command_count
            
            print(f"📋 {cog_name}: {command_count} commands")
    
    print(f"\n📊 Total expected commands from existing cogs: {total_expected}")
    
    return total_expected, cog_command_counts

def check_bot_logs():
    """Check recent bot logs for cog loading failures"""
    
    if os.path.exists('bot.log'):
        print("\n📜 Recent bot log entries:")
        with open('bot.log', 'r') as f:
            lines = f.readlines()
        
        # Get last 50 lines
        recent_lines = lines[-50:]
        
        for line in recent_lines:
            if any(keyword in line for keyword in ['Failed to load cog', 'ERROR', 'commands synced']):
                print(f"  {line.strip()}")

def main():
    """Main diagnostic function"""
    print("🔍 Diagnosing command count discrepancy...")
    
    # Check cog files
    successful_count, missing, failed = check_cog_files()
    
    # Count expected commands
    expected_commands, command_breakdown = count_commands_per_cog()
    
    # Check logs
    check_bot_logs()
    
    print(f"\n🎯 Summary:")
    print(f"  - Expected cogs: 15")
    print(f"  - Successfully imported: {successful_count}")
    print(f"  - Expected commands from existing cogs: {expected_commands}")
    print(f"  - Actual synced commands: 29")
    print(f"  - Command deficit: {expected_commands - 29 if expected_commands > 29 else 0}")
    
    if missing or failed:
        print(f"\n⚠️ Issues found:")
        print(f"  - Missing cog files: {len(missing)}")
        print(f"  - Import failures: {len(failed)}")
        print(f"  - This explains the command count discrepancy")

if __name__ == "__main__":
    main()