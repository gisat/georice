import subprocess
from georice.utils import load_config
import os


class Ricemap:

    def __init__(self):
        config = load_config()
        self.rice_output = config['rice_output']
        self.scn_output = config['scn_output']

    def ricemap_get_all(self, delete=False):
        """
        Generate rice maps for all combinations of orbit number, orbit direction
        and period found at scene directory. Rice maps """
        period, orb_num, orb_path = set(), set(), set()
        with os.scandir(self.scn_output) as files:
            for file in files:
                if file.is_file():
                    parsed = file.name.split('_')
                    period.add(parsed[5])
                    orb_num.add(parsed[4])
                    orb_path.add(parsed[3])
        for orbit in orb_path:
            for num in orb_num:
                command = ['ricemap.py', self.scn_output, num, min(period), max(period), self.rice_output, '-d', orbit]
                subprocess.run(' '.join(command), shell=True)
                print(f'Ricemap for orbit path/orbit number/period: {orbit}/{num}/{min(period)}/{max(period)} '
                           f'saved at folder: {self.rice_output}')

    def ricemap_get(self, orbit_number, period, direct, inter=False, lzw=False, mask=False, nr=False,
                delete=False):
        """
        Set ricemap commands.
        NOTE: starting_date / ending_date => YYYYMMDD, inclusive
        """
        config_rice = load_config()
        command = ['ricemap.py', config_rice['scn_output'], orbit_number, period[0], period[1],
                   config_rice['rice_output']]
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
        print(f'Ricemap saved into folder: {config_rice["rice_output"]}')

    def _delete_scene(self):
        pass
