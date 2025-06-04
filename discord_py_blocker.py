
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
