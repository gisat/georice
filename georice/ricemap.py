import subprocess
from .utils import load_config
import os
import sys

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
        command = [sys.executable, f'bin{os.sep}ricemap.py', scene_path, orbit_number, period[0], period[1], output_path]
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

        returncode = subprocess.run(' '.join(command), shell=False, check=True, capture_output=True)
        if returncode.returncode !=0:
            print("Ricemap classificator wasn't executed successfully")
        else:
            print(returncode.stdout.decode(encoding='UTF-8'))

