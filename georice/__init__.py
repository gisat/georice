#!/usr/bin/env python

from .imagery import GetSentinel, Geometry
from .ricemap import Ricemap
from .filtering import Filtering
from .utils import load_config, show_config, save_config, set_sh, Dir, mosaic
import os

class Georice:

    def __init__(self):
        self.config = load_config()
        self._path_check()
        self._imagery = GetSentinel()
        self._ricemap = Ricemap()
        self._filtering = Filtering()

        self._get_tile_attr()

    def _path_check(self):
        if self.config['output'] == 'default':
            home = os.getcwd()
            self.set_config(output=os.path.join(home, 'output'))
            self.config = load_config()

    def _get_tile_attr(self):
        try:
            output = os.scandir(self.config['output'])
        except FileNotFoundError:
            os.makedirs(self.config['output'], mode=0o777)
            output = os.scandir(self.config['output'])

        for file in output:
            if file.is_dir():
                setattr(self, file.name, Dir(file.path))

    def tiles(self):
        """Return list of tiles"""
        return [file.name for file in os.scandir(self.config['output']) if file.is_dir()]

    def set_credentials(self, **kwargs):
        """
        Save sentinel hub credentials into SHConfig. Credentials are:
        sh_client_id
        sh_client_secret
        instance_id
        More information about Sentinel-Hub credential at https://www.sentinel-hub.com/
        Usage: Georice.set_credentials(**{'instance_id': 'your instance id'})
        """
        for key in kwargs.keys():
            if key in ['sh_client_id', 'sh_client_secret', 'instance_id']:
                set_sh(key, kwargs[key])
            else:
                raise Exception(f'Key: {key} was not in expected keys  (sh_client_id, sh_client_secret, instance_id)')
        self._imagery = GetSentinel()

    def set_config(self, **kwargs: dict):
        """Save setting of config file

        Parameters:
        polar - polarization,  used for searching the archive; type: list; values VV, VH; default = ['VV','VH'];
        orbit_path - orbit path, - used for filtering and searching of scenes; type: list;
        values ASC - ascending, DES - descending; type: list; default =['ASC','DES];
        output - output folder, if not set, current working directory is used, type: string;
        wsf_version - type: str; default = '1.0.0';
        img_height - height of img in pixels; type: int; default = 1000;
        img_width - width of img in pixels; type: int; default = 1000;
        resx - resolution in x axis; type: int; default = 10;
        resy - resolution in y axis; type: int; default = 10;
        max_area - if the area of  AOI in m2 is greater, AOI is break down into smaller tiles that area process
        individually; type int; default = 1E9;
        year_outcore_list - parameter of SAR MultiTempFilter, define year for outcore; type: list;
        default = ["2019","2018"];
         year_filter_list - parameter of SAR MultiTempFilter, define year for filter; type: list;
        default = ["2019","2018"];
        ram_per_process - parameter of SAR MultiTempFilter, define RAM used for a processing; type: int; default = 4096;
        OTBThreads - parameter of SAR MultiTempFilter, number of threads; type: int; default = 4;
        Window_radius - parameter of SAR MultiTempFilter; type: int; default = 2;
        """
        save_config(kwargs)
        self.config = load_config()

    @staticmethod
    def show_config():
        """Save setting of config file

        Parameters:
        polar - polarization,  used for searching the archive; type: list; values VV, VH; default = ['VV','VH'];
        orbit_path - orbit path, - used for filtering and searching of scenes; type: list;
        output - output folder, if not set, current working directory is used, type: string;
        values ASC - ascending, DES - descending; type: list; default =['ASC','DES];
        wsf_version - type: str; default = '1.0.0';
        img_height - height of img in pixels; type: int; default = 1000;
        img_width - width of img in pixels; type: int; default = 1000;
        resx - resolution in x axis; type: int; default = 10;
        resy - resolution in y axis; type: int; default = 10;
        max_area - if the area of  AOI in m2 is greater, AOI is break down into smaller tiles that area process
        individually; type int; default = 1E9;
        year_outcore_list - parameter of SAR MultiTempFilter, define year for outcore; type: list;
        default = ["2019","2018"];
         year_filter_list - parameter of SAR MultiTempFilter, define year for filter; type: list;
        default = ["2019","2018"];
        ram_per_process - parameter of SAR MultiTempFilter, define RAM used for a processing; type: int; default = 4096;
        OTBThreads - parameter of SAR MultiTempFilter, number of threads; type: int; default = 4;
        Window_radius - parameter of SAR MultiTempFilter; type: int; default = 2;
        """
        show_config()

    def find_scenes(self, bbox=None, epsg=None, period=None, info=True):
        """
        Find Sentinel 1 scenes from Sentinel Hub and return their list
        :param bbox: list of coordinates representing bbox
        :param epsg: int or str
        :param period: tuple (str, str). date format YYYYMMDD
        :param info: bool, turn off/on writing down list of found scenes
        """
        self._imagery.search(bbox, epsg, period)
        if info:
            self.scenes()

    def scenes(self):
        """Show found scenes"""
        self._imagery.scenes()

    def filter(self, inplace=False, **kwargs):
        """
        Provide filtering of found scenes according to given keyword arguments. Return the result of filtering, if
        inplace (default: False) is True, fond scenes are overwrite by filter result
        :param inplace: bool, default False, Overwrite scenes by filter result
        :param kwargs: keyword filtering arguments
        :return:
        """
        return self._imagery.filter(inplace, **kwargs)

    def get_scenes(self, name):
        """
        Download selected scenes into output folder ie. 'output folder'/'tile name'/scenes.
        :param name: Name of the tile
        :return:
        """
        self._imagery.download(name)
        print(f'Scenes were downloaded into {self.config["output"]}/{name}/scenes')
        self._get_tile_attr()

    def get_ricemap(self, name, period, orbit_path=None, orbit_number=None, inter=False, lzw=False, mask=False, nr=False,
                    filtering=True):
        """
         Georice - generation of classified rice map
        "no_data":0, "rice":1, "urban_tree":2, "water":3, "other":4

        Generete rice maps for given parameters of orbit number, orbit path and period and save them
        into rice_output path defined.
        orbit_number - orbit number; type: str; - three digits string representation i.e. '018'
        period - starting_date / ending_date => YYYYMMDD, type: tuple('str','str')
        orbit_path - orbit direction; type: str; values ASC - ascending, DES - descending; default = 'DES'
        inter - save intermediate products (min/max/mean/max_increase); type: bool; default = False
        lzv - use LZW compression; type: bool; default = False i.e. DEFLATE
        mask - generate and write rice, trees, water, other and nodata masks; type: bool; default = False
        nr - diable automatic reprojection to EPSG:4326, type: bool; default = True
        filtering - Use SAR multi-temporal speckle filter; default = True
        """
        self.filter(inplace=True, rel_orbit_num=orbit_number, orbit_path=orbit_path)
        if hasattr(self, name) and hasattr(self.__getattribute__(name), 'scenes'):
            self.__getattribute__(name).scenes.delete()

        if self._imagery.aoi.geometry.area >= load_config().get('max_area'):
            geom = Geometry(self._imagery.aoi.geometry, self._imagery.aoi.crs, grid_leght=(10000, 10000))
            copy = self._imagery.__copy__()

            print(f'Area is larger than {self.config["max_area"]/1e6} km2. AOI will be processed in parts.')
            n_parts = sum(1 for dummy in iter(geom))

            for id, sub_aoi in enumerate(iter(geom)):
                print(f'Starting to process part {id+1}/{n_parts}')
                part = f'part{id}-'
                grid = Geometry(sub_aoi[0], self._imagery.aoi.crs)
                copy.aoi = grid
                copy.download(tile_name=name, part=part)
                if filtering:
                    self._filtering.process(name, orbit_path)
                    self._ricemap.ricemap_get(name, orbit_number, period, orbit_path, inter, lzw, mask, nr, part=part,
                                              folder=f'scenes{os.sep}filtered')
                else:
                    self._ricemap.ricemap_get(name, orbit_number, period, orbit_path, inter, lzw, mask, nr, part=part)
                self._get_tile_attr()
                self.__getattribute__(name).scenes.delete()
            print(f'')
            mosaic(self.__getattribute__(name).ricemaps.file_paths())
        else:
            print('Downloading scenes')
            self._imagery.download(tile_name=name)
            print('Downloading finished')
            if filtering:
                self._filtering.process(name, orbit_path)
                self._ricemap.ricemap_get(name, orbit_number, period, orbit_path, inter, lzw, mask, nr,
                                          folder=f'scenes{os.sep}filtered')
            else:
                self._ricemap.ricemap_get(name, orbit_number, period, orbit_path, inter, lzw, mask, nr)
            self._get_tile_attr()
            self.__getattribute__(name).scenes.delete()

        print(f'Rice map was downloaded into {self.config["output"]}{os.sep}{name}{os.sep}ricemaps')



















