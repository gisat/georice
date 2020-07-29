from subprocess import Popen, DEVNULL
from .utils import load_config
import os
import psutil
import time
from osgeo import gdal
from datetime import datetime


class Filtering:
    """ This module runs multitemporal speckle filtering processor """

    def __init__(self):
        config = load_config()
        self.output = config['output']
        self.year_outcore_list = config['year_outcore_list']
        self.name = ''
        self.ram_per_process = int(config['ram_per_process']*psutil.cpu_count()/2)
        self.OTBThreads = int(config['OTBThreads']*psutil.cpu_count()/2)
        self.Window_radius = config['Window_radius']
        self.stdoutfile = DEVNULL
        self.stderrfile = open("S1ProcessorErr.log", 'a')

    def process(self, name, orbit_path):

        self.name = name

        filelist_str = " ".join((scene.path for scene in self.get_scenes if scene.name.endswith('.tif')))
        year_outcore_str = '-'.join([min(self.outcore_year), max(self.outcore_year)])

        self.compute_outcore(filelist_str, orbit_path, year_outcore_str)

        self.compute_filtered(filelist_str, orbit_path, year_outcore_str)

    def compute_outcore(self, filelist_str, orbit_path, year_outcore_str):

        pids = []

        command = f'export ITK_GLOBAL_DEFAULT_NUMBER_OF_THREADS={self.OTBThreads};' \
                  + "otbcli_MultitempFilteringOutcore -progress false -inl " \
                  + filelist_str + " -oc " \
                  + os.path.join(self.folder_path('scenes'), f'outcore{year_outcore_str}_S1{orbit_path}.tif') \
                  + f' -wr {self.Window_radius}' \
                  + f' -ram {str(self.ram_per_process)}'

        pids.append([Popen(command, stdout=self.stdoutfile, stderr=self.stderrfile, shell=True), command])

        try:
            os.makedirs(os.path.join(self.folder_path('scenes'), "filtered"))
        except os.error:
            pass

        title = "Compute outcore"
        nb_cmd = len(pids)
        print(title+"... 0%")
        while len(pids) > 0:

            for i, pid in enumerate(pids):
                status = pid[0].poll()
                if status is not None and status != 0:
                    print("Error in pid #"+str(i)+" id="+str(pid[0]))
                    print(pid[1])
                    del pids[i]
                    break

                if status == 0:
                    del pids[i]
                    print(title+"... "+str(int((nb_cmd-len(pids))*100./nb_cmd))+"%")
                    time.sleep(0.2)
                    break
            time.sleep(2)

    def compute_filtered(self, filelist_str, orbit_path, year_outcore_str):

        pids = []

        command = f'export ITK_GLOBAL_DEFAULT_NUMBER_OF_THREADS={self.OTBThreads};' \
                  + "otbcli_MultitempFilteringFilter -progress false -inl " \
                  + filelist_str + " -oc " \
                  + os.path.join(self.folder_path('scenes'), f'outcore{year_outcore_str}_S1{orbit_path}.tif') \
                  + f' -wr {self.Window_radius} -enl ' \
                  + os.path.join(self.folder_path('scenes'), 'filtered', f'enl_{year_outcore_str}_S1{orbit_path}.tif') \
                  + f' -ram {str(self.ram_per_process)}'

        pids.append([Popen(command, stdout=self.stdoutfile, stderr=self.stderrfile, shell=True), command])

        title = "Compute filtered images"
        nb_cmd = len(pids)
        print(title+"... 0%")
        while len(pids) > 0:

            for i, pid in enumerate(pids):
                status = pid[0].poll()
                if status is not None and status != 0:
                    print("Error in pid #"+str(i)+" id="+str(pid[0]))
                    print(pid[1])
                    del pids[i]
                    break

                if status == 0:
                    del pids[i]
                    print(title+"... "+str(int((nb_cmd-len(pids))*100./nb_cmd))+"%")
                    time.sleep(0.2)
                    break
            time.sleep(2)

        for f in os.listdir(self.folder_path(f'scenes{os.sep}filtered')):
            fullpath = os.path.join(self.folder_path(f'scenes{os.sep}filtered'), f)
            if os.path.isfile(fullpath) and f.startswith('s1') and f.endswith('filtered.tif'):
                dst = gdal.Open(fullpath, gdal.GA_Update)
                dst.SetMetadataItem('FILTERED', 'true')
                dst.SetMetadataItem('FILTERING_WINDOW_RADIUS', str(self.Window_radius))
                dst.SetMetadataItem('FILTERING_PROCESSINGDATE', str(datetime.now()))

    def folder_path(self, fld):
        return os.path.join(self.output, self.name, fld)

    @property
    def get_scenes(self):
        return os.scandir(self.folder_path('scenes'))

    @property
    def outcore_year(self):
        return (scene.name.split('_')[-2][0:4] for scene in self.get_scenes if scene.name.endswith('.tif'))


