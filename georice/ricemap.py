import subprocess
from .utils import load_config
import os


class Ricemap:

    def __init__(self):
        config = load_config()
        self.output = config['output']

    def ricemap_get_all(self, tile_name):
        """
        Generate rice maps for all combinations of orbit number, orbit direction
        and period found at scene directory for given tile name.

        """
        scene_path = os.path.join(self.output, tile_name, 'scenes')
        period, orb_num, orb_path = set(), set(), set()
        with os.scandir(scene_path) as files:
            for file in files:
                if file.is_file():
                    parsed = file.name.split('_')
                    period.add(parsed[5])
                    orb_num.add(parsed[4])
                    orb_path.add(parsed[3])
        for orbit in orb_path:
            for num in orb_num:
                command = ['ricemap.py', scene_path, num, min(period), max(period), self.output, '-d', orbit]
                subprocess.run(' '.join(command), shell=True)
                print(f'Ricemap for orbit path/orbit number/period: {orbit}/{num}/{min(period)}/{max(period)} '
                           f'saved at folder: {self.output}/{tile_name}')

    def ricemap_get(self, tile_name, orbit_number, period, direct, inter=False, lzw=False, mask=False, nr=False):
        """
        Set ricemap commands.
        NOTE: starting_date / ending_date => YYYYMMDD, inclusive
        """
        scene_path = os.path.join(self.output, tile_name, 'scenes')
        command = ['ricemap.py', scene_path, orbit_number, period[0], period[1], self.output]
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
        subprocess.run(' '.join(command), shell=True)
