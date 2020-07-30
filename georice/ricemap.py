import subprocess
from .utils import load_config
import os


class Ricemap:

    def __init__(self):
        config = load_config()
        self.output = config['output']

    def ricemap_get(self, tile_name, orbit_number, period, direct, inter=False, lzw=False, mask=False, nr=False,
                    part='', folder='scenes'):
        """
        Set ricemap commands.
        NOTE: starting_date / ending_date => YYYYMMDD, inclusive
        """
        scene_path = os.path.join(self.output, tile_name, folder)
        output_path = os.path.join(self.output, tile_name)
        command = ['ricemap.py', scene_path, orbit_number, period[0], period[1], output_path]
        if direct:
            command.append('-d ' + direct)
        if inter:
            command.append('-i')
        if lzw:
            command.append('-lzw')
        if mask:
            command.append('-m')
        if nr:
            command.append('-nr')
        command.append(part)
        subprocess.run(' '.join(command), shell=True)
