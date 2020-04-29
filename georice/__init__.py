#!/usr/bin/env python

from .imagery import GetSentinel
from .ricemap import Ricemap
from .utils import load_config, show_config, save_config, set_sh, show_sh
import os


class Georice:

    def __init__(self):
        self.config = load_config()
        self._imagery = GetSentinel()
        self._ricemap = Ricemap()

    @staticmethod
    def set_credentials(**kwargs):
        """
        Save sentinel hub credentials into SHConfig. Credentials are:
        sh_client_id
        sh_client_secret
        instance_id
        More information about Sentinel-Hub credential at https://www.sentinel-hub.com/
        """
        for key in kwargs.keys():
            if key in ['sh_client_id', 'sh_client_secret', 'instance_id']:
                set_sh(key, kwargs[key])
            else:
                raise Exception(f'Key: {key} was not in expected keys  (sh_client_id, sh_client_secret, instance_id)')

    @staticmethod
    def show_credentials():
        """Show actual settingo of Sentinel Hub Credentials"""
        show_sh()

    @staticmethod
    def set_config(**kwargs):
        """Save setting of config file

        Parameters:
        polar - polarization; type: list; values VV, VH; default = ['VV','VH']; - used for filtering scenes
        orbit_path - orbit path; type: list; values ASC - ascending, DES - descending; default =['ASC','DES]; - used for filtering scenes
        scn_output - path to folder were scenes will be downloaded; type: str; required;
        rice_output - path to folder were will be saved generated rice maps; type: str; required;
        nodata - no data value; type: int; default = -999;
        timerange - used for filtering a merging S1B scenes which were acquired withing the time range; type: inf; default = 3600 s
        wsf_verison - type: str; default = '1.0.0'
        img_height - height of img in pixels; type: int; defualt = 1000;
        img_width - width of img in pixels; type: int; defualt = 1000;
        resx - resolution in x axis; type: int; default = 10;
        resy - resolution in y axis; type: int; default = 10;
        """
        save_config(kwargs)


    @staticmethod
    def show_config(**kwargs):
        """Save setting of config file

        Parameters:
        polar - polarization; type: list; values VV, VH; default = ['VV','VH']; - used for filtering scenes
        orbit_path - orbit path; type: list; values ASC - ascending, DES - descending; default =['ASC','DES]; - used for filtering scenes
        scn_output - path to folder were scenes will be downloaded; type: str; required;
        rice_output - path to folder were will be saved generated rice maps; type: str; required;
        nodata - no data value; type: int; default = -999;
        timerange - used for filtering a merging S1B scenes which were acquired withing the time range; type: inf; default = 3600 s
        wsf_verison - type: str; default = '1.0.0'
        img_height - height of img in pixels; type: int; defualt = 1000;
        img_width - width of img in pixels; type: int; defualt = 1000;
        resx - resolution in x axis; type: int; default = 10;
        resy - resolution in y axis; type: int; default = 10;
        """
        show_config()

    def find_scenes(self, bbox=None, epsg=None, period=None, tile_name='Tile'):
        """
        Find Sentinel 1 scenes from Sentinel Hub
        :param bbox: list of coordinates representing bbox or object with __geo_interface__ and bbox attribute
        :param epsg: int
        :param period: tuple (str, str). date format YYYYMMDD
        :param tile_name: str
        :param kwargs: additional parameters

        """
        self._imagery.search(bbox, epsg, period, tile_name)

    @property
    def scenes(self):
        """Return list of founded scenes"""
        if len(self._imagery._scenes) > 0:
            return self._imagery.scenes
        else:
            print(f'For given input parameters 0 scenes were found')

    def get_scenes(self):
        self._imagery.dump()
        print(f'Scenes were downoladed into {self.config["output"]}')

    def ricemap_get_all(self, tile_name):
        """
        Georice - generation of classified rice map
        "no_data":0, "rice":1, "urban_tree":2, "water":3, "other":4

        Generete rice maps for all combination of orbit number, orbit path and period found in scence folder for given
        tile name.

        :param
        :param tile_name: str, specify tile name
        """
        self._ricemap.ricemap_get_all(tile_name)

    def ricemap_get(self, orbit_number, period, direct, inter=False, lzw=False, mask=False, nr=False):
        """
         Georice - generation of classified rice map
        "no_data":0, "rice":1, "urban_tree":2, "water":3, "other":4

        Generete rice maps for given parameters of orbit number, orbit path and period and save them
        into rice_output path defined.
        orbit_number - orbit number; type: str; - three digits string representation i.e. '018'
        period - starting_date / ending_date => YYYYMMDD, type: tuple('str','str')
        direct - orbit direction; type: str; values ASC - ascending, DES - descending; default = 'DES'
        inter - save intermediate products (min/max/mean/max_increase); type: bool; default = False
        lzv - use LZW compression; type: bool; default = False i.e. DEFLATE
        mask - generate and write rice, trees, water, other and nodata masks; type: bool; default = False
        nr - diable automatic reprojection to EPSG:4326, type: bool; default = True
        delete - delete used scenes; type: bool; default = True
        """
        self._ricemap.ricemap_get(orbit_number, period, direct, inter, lzw, mask, nr)

    def delete_scenes(self, tile_name):
        """Dele all downloaded scenes in folder for selected tile name """
        path = os.path.join(self.config['scn_output'], tile_name)
        with os.scandir(path) as files:
            for file in files:
                if file.name[:2] == 'S1' and file.name.split('.')[1] == 'tif':
                    os.remove(file.path)








