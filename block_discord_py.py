
#!/usr/bin/env python3
"""
Block discord.py installation and ensure py-cord 2.6.1 exclusivity
"""

import subprocess
import sys
import os

def block_discord_py():
    """Block discord.py and ensure only py-cord is available"""
    
    print("🚫 Blocking discord.py installation...")
    
    try:
        # Uninstall discord.py if present
        result = subprocess.run([sys.executable, '-m', 'pip', 'uninstall', 'discord.py', '-y'], 
                              capture_output=True, text=True)
        if result.returncode == 0:
            print("✅ Removed discord.py")
        else:
            print("ℹ️ discord.py not installed")
        
        # Uninstall discord if present (older versions)
        result = subprocess.run([sys.executable, '-m', 'pip', 'uninstall', 'discord', '-y'], 
                              capture_output=True, text=True)
        if result.returncode == 0:
            print("✅ Removed discord")
        
        # Ensure py-cord 2.6.1 is installed
        result = subprocess.run([sys.executable, '-m', 'pip', 'install', 'py-cord==2.6.1'], 
                              capture_output=True, text=True)
        if result.returncode == 0:
            print("✅ py-cord 2.6.1 installed/verified")
        else:
            print(f"❌ Failed to install py-cord: {result.stderr}")
        
        # Create a permanent block
        create_import_block()
        
    except Exception as e:
        print(f"❌ Error during blocking: {e}")

def create_import_block():
    """Create import hook to block discord.py"""
    
    block_code = '''
# Block discord.py imports to prevent conflicts with py-cord
import sys
import importlib.util

class DiscordPyBlocker:
    """Block discord.py imports to ensure py-cord exclusivity"""
    
    def find_spec(self, fullname, path, target=None):
        if fullname == 'discord' and 'py-cord' not in str(path or []):
            # Allow py-cord discord module
            return None
        elif fullname.startswith('discord.') and not self._is_pycord_import(fullname):
            raise ImportError(
                f"discord.py import '{fullname}' blocked. "
                f"Use py-cord 2.6.1 instead: pip install py-cord==2.6.1"
            )
        return None
    
    def _is_pycord_import(self, fullname):
        """Check if import is from py-cord"""
        try:
            import discord
            # If discord is already imported and it's py-cord, allow the import
            return hasattr(discord, '__version__') and 'py-cord' in str(discord.__file__ or '')
        except:
            return False

# Install the blocker
if 'discord_py_blocker' not in [meta.name for meta in sys.meta_path if hasattr(meta, 'name')]:
    blocker = DiscordPyBlocker()
    blocker.name = 'discord_py_blocker'
    sys.meta_path.insert(0, blocker)
'''
    
    try:
        # Create the blocker file
        with open('discord_py_blocker.py', 'w') as f:
            f.write(block_code)
        print("✅ Created discord.py import blocker")
        
        # Add to main.py if not already present
        with open('main.py', 'r') as f:
            content = f.read()
        
        if 'discord_py_blocker' not in content:
            # Add import at the top
            import_line = "import discord_py_blocker  # Block discord.py imports\n"
            
            # Find where to insert (after the module cleanup but before discord import)
            lines = content.split('\n')
            insert_index = 0
            
            for i, line in enumerate(lines):
                if 'del sys.modules[module_name]' in line:
                    insert_index = i + 1
                    break
            
            if insert_index > 0:
                lines.insert(insert_index, import_line)
                
                with open('main.py', 'w') as f:
                    f.write('\n'.join(lines))
                print("✅ Added blocker import to main.py")
        
    except Exception as e:
        print(f"❌ Error creating blocker: {e}")

if __name__ == "__main__":
    block_discord_py()
