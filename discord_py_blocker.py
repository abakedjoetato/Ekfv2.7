

# Block discord.py imports to prevent conflicts with py-cord
import sys
import importlib.util

class DiscordPyBlocker:
    """Block discord.py imports to ensure py-cord exclusivity"""
    
    def find_spec(self, fullname, path, target=None):
        # Always allow py-cord imports - check if discord is already imported as py-cord
        if fullname == 'discord' or fullname.startswith('discord.'):
            try:
                # If discord is already imported, check if it's py-cord
                if 'discord' in sys.modules:
                    discord_module = sys.modules['discord']
                    module_file = getattr(discord_module, '__file__', '')
                    # py-cord typically has 'py_cord' or 'py-cord' in its path
                    if 'py_cord' in str(module_file) or 'py-cord' in str(module_file):
                        return None  # Allow py-cord imports
                
                # For initial imports, check if py-cord is installed
                import subprocess
                result = subprocess.run([sys.executable, '-m', 'pip', 'show', 'py-cord'], 
                                      capture_output=True, text=True)
                if result.returncode == 0 and '2.6.1' in result.stdout:
                    return None  # Allow py-cord 2.6.1 imports
                
                # Block if it's discord.py
                if fullname.startswith('discord.'):
                    raise ImportError(
                        f"discord.py import '{fullname}' blocked. "
                        f"Use py-cord 2.6.1 instead: pip install py-cord==2.6.1"
                    )
                    
            except ImportError as e:
                if 'blocked' in str(e):
                    raise e
            except:
                pass
        
        return None

# Install the blocker
if 'discord_py_blocker' not in [getattr(meta, 'name', '') for meta in sys.meta_path]:
    blocker = DiscordPyBlocker()
    blocker.name = 'discord_py_blocker'
    sys.meta_path.insert(0, blocker)

