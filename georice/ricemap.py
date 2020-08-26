import subprocess
from .utils import load_config
import os
import sys
import georice
from pathlib import Path

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
        script = Path(georice.__file__).parent.parent / 'bin' / 'ricemap.py'
        args = [sys.executable, str(script), scene_path, orbit_number, period[0], period[1], output_path]
        if direct:
            args.append('-d ')
            args.append(direct)
        if inter:
            args.append('-i')
        if lzw:
            args.append('-lzw')
        if mask:
            args.append('-m')
        if nr:
            args.append('-nr')
        args.append(part)

        try:
            p = subprocess.check_output(args=' '.join(args), shell=True)
            print(p.decode())
        except subprocess.CalledProcessError:
            print("Ricemap classificator wasn't executed successfully")
            quit()



