"""paths.py of the release's mods/generator: on a player's PC the generator sits in <game folder>/mods/generator, and the game folder is two levels up.
(release.py copies this file as mods/generator/paths.py; in this project paths.py at _tools/ answers the same two names.)"""
import os

TOOLS = os.path.dirname(os.path.abspath(__file__))     # <game folder>/mods/generator
ROOT = os.path.dirname(os.path.dirname(TOOLS))          # <game folder>
