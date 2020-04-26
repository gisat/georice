import concurrent.futures
import os
from datetime import datetime, timedelta
from urllib.parse import urlencode
from numpy import block, ones
from rasterio import open as raster_open
from rasterio.transform import Affine
from rasterio.warp import calculate_default_transform
from requests import get
from sentinelhub import BBox, SentinelHubRequest, SHConfig, MimeType
from itertools import repeat
from .utils import load_config, save_config
from math import ceil


_SCENE = {'name': None,
          'sat_name': None,
          'acquisitionMode': None,
          'polarizationMode': None,
          'polarization': None,
          'orbit_path': None,
          'orbit_num': None,
          'rel_orbit_num': None,
          'from_time': None,
          'to_time': None,
          'time': None}


class GetSentinel:

    def __init__(self):
        self.config = SHConfig()
        self.aoi = None
        self.epsg = None
        self.period = []
        self.tile_name = ''
        self.setting = load_config()
        self._scenes = []

    @property
    def scenes(self):
        """Print list of founded scenes"""
        if len(self._scenes) > 0:
            print(f'Total number of scenes {len(self._scenes)} in period {self.period[0]} / {self.period[1]}')
            for index, scene in enumerate(self._scenes):
                print(f'No{index}: Satelite: {scene["sat_name"]}, polarization: {scene["polarization"]}, '
                      f'rel. orbit number: {scene["rel_orbit_num"]}, orbit path: {scene["orbit_path"]}')


    # methods
    def search(self, bbox=None, epsg=None, period=None, tile_name='Tile'):
        """
        set input parameters, then start processing of parametrs i.e. find available scenes
        :param bbox: list of coordinates representing bbox or object with __geo_interface__ and bbox attribute
        :param epsg: int
        :param period: tuple (str, str). date format YYYYMMDD
        :param tile_name: str
        :param kwargs: additional parameters
        """
        self.epsg = epsg
        self.aoi = self._set_bbox(bbox, epsg)
        self.period = [self._srt2time(time, '%Y%m%d').isoformat() for time in period]
        self.tile_name = tile_name

        scenes = self._wsf_query()

        if len(scenes) > 0:
            while len(scenes) > 0:
                scene = scenes.pop(0)
                try:
                    start_period = scene['from_time'] - timedelta(seconds=self.setting['time_range'])
                    end_period = scene['from_time'] + timedelta(seconds=self.setting['time_range'])
                    if self._time_in_range(start_period, end_period, scenes[0]['from_time']):
                        scene.update(from_time=scenes[0]['from_time'])
                        self._scene_update(scene)
                        scenes.pop(0)
                    else:
                        self._scene_update(scene)
                        scenes.pop(0)
                except IndexError:
                    self._scene_update(scene)
        else:
            raise Exception('No scenes find for given set of input parameters')


    def _scene_update(self, scene):
        if scene['polarizationMode'] == 'DV':
            for polar in self.setting['polar']:
                tmp = scene.copy()
                tmp['polarization'] = polar
                tmp['name'] = self._get_img_name(tmp)
                self._scenes.append(tmp)

    # download tiles
    def dump(self, path=None):
        """
        Get
        params:
        path - path to output folder
        """
        if self.epsg == 4326:
            self.aoi = self.aoi.transform(3857)

        nx, _ = self._set_wh()
        if path is None:
            path = self.setting["scn_output"]
        else:
            self.setting.update(scn_output=path)
            save_config(self.setting)

        for n in range(len(self._scenes)):
            tiles = self.download_tiles(self._scenes[n])
            blocks = [tiles[i:i + nx] for i in range(0, len(tiles), nx)]
            blocks.reverse()
            array = block(blocks)
            self._save_raster(path, array, self._scenes[n]['name'])
            del tiles, array

    def download_tiles(self, scene):
        self.request(scene, next(self.grid))
        with concurrent.futures.ThreadPoolExecutor() as pool:
            results = pool.map(self.request, repeat(scene), [bbox for bbox in self.grid])
            return [res for res in results]

    def request(self, scene, bbox):
        evalscript = '''//VERSION=3
                    function setup() {
                      return {
                        input: ["POLAR"],
                        output: { id:"default", bands: 1, sampleType: SampleType.FLOAT32}
                      }
                    }
            
                    function evaluatePixel(samples) {
                      return [samples.POLAR]
                    }'''.replace('POLAR', scene['polarization'])

        request = SentinelHubRequest(
            evalscript=evalscript,
            input_data=[
                {
                    "type": "S1GRD",
                    "dataFilter": {
                        "timeRange": {
                            "from": scene['from_time'].strftime('%Y-%m-%dT%H:%M:%SZ'),
                            "to": scene['to_time'].strftime('%Y-%m-%dT%H:%M:%SZ')
                        },
                        "acquisitionMode": "IW",
                        "polarization": "DV",
                        "orbitDirection ": scene['orbit_path']
                    },
                    "processing": {
                        "backCoeff": "GAMMA0_ELLIPSOID",
                        "orthorectify": "true"
                    }
                }

            ],
            responses=[
                SentinelHubRequest.output_response('default', MimeType.TIFF, )
            ],
            bbox=bbox,
            resolution=[self.setting['resx'], self.setting['resy']],
            config=SHConfig()
        )

        array = request.get_data(max_threads=min(32, os.cpu_count() + 4))[0]
        if array is not None:
            return array
        else:
            return ones(shape=(self.setting['img_width'], self.setting['img_height'])) * self.setting['nodata']

    def _set_wh(self):
        """set number of n 10000m long tiles"""
        x0, y0 = self.aoi.lower_left
        xe, ye = self.aoi.upper_right
        nx = ceil(abs(x0 - xe) / (self.setting['img_width'] * self.setting['resx']))
        ny = ceil(abs(y0 - ye) / (self.setting['img_height'] * self.setting['resy']))
        return nx, ny

    # geometry
    @staticmethod
    def _set_bbox(geom, crs):
        try:
            return BBox(bbox=geom, crs=crs)
        except TypeError:
            if hasattr(geom, '__geo_interface__') and geom.__geo_interface__.__contains__('bbox'):
                return BBox(bbox=geom.__geo_interface__['bbox'], crs=crs)

    @property
    def grid(self):
        x0, y0 = self.aoi.lower_left
        xe, ye = self.aoi.upper_right
        j, length = 1, self.setting['img_width'] * self.setting['resx']
        x, y = x0, y0
        while y < ye:
            i = 1
            while x < xe:
                yield BBox(bbox=((x, y), (x + length, y + length)), crs=self.aoi.crs)
                x += length
                i += 1
            y += length
            j += 1
            x = x0

    # wsf
    def _wsf_query(self):
        """ Collects data from WFS service
        :return: list o scenes properties for given input parameters
        :rtype: list
        """
        main_url = '{}/{}?'.format('https://services.sentinel-hub.com/ogc/wfs', self.config.instance_id)
        params = {
            'REQUEST': 'GetFeature',
            'TYPENAMES': 'DSS3',
            'BBOX': str(self.aoi),
            'OUTPUTFORMAT': 'application/json',
            'SRSNAME': f'EPSG:{self.aoi.crs.value}',
            'TIME': '{}/{}'.format(self.period[0], self.period[1]),
            'MAXCC': 100.0 * 100,
            'MAXFEATURES': 100,
            'FEATURE_OFFSET': 0,
            'VERSION': self.setting['wsf_version']
        }
        url = main_url + urlencode(params)
        response = get(url)
        if response.status_code == 200:
            return [self._parse_wsf(scenes['properties']) for scenes in response.json()['features']]
        else:
            raise Exception(f'Connection to Sentinel Hub WSF failed. Reason: {response.status_code}')

    def _parse_wsf(self, scene):
        tmp = _SCENE.copy()
        parts = scene['id'].split('_')
        tmp['sat_name'] = parts[0]
        tmp['acquisitionMode'] = parts[1]
        tmp['polarizationMode'] = parts[3][-2:]
        tmp['orbit_path'] = scene['orbitDirection']
        tmp['orbit_num'] = parts[6]
        tmp['rel_orbit_num'] = self._get_rel_orbit_num(parts[0], parts[6])
        tmp['from_time'] = self._srt2time(parts[4], '%Y%m%dT%H%M%S')
        tmp['to_time'] = self._srt2time(parts[5], '%Y%m%dT%H%M%S')
        tmp['time'] = parts[4][:8]
        return tmp

    @staticmethod
    def _time_in_range(start, end, x):
        """Return true if x is in the range [start, end]"""
        if start <= end:
            return start <= x <= end
        else:
            return start <= x or x <= end

    @staticmethod
    def _srt2time(time, patern):
        return datetime.strptime(time, patern)

    @staticmethod
    def _get_rel_orbit_num(sat_name, abs_orbit_number):
        orbit_number = int(abs_orbit_number.lstrip('0'))
        if sat_name == 'S1A':
            rel_orbit_num = str(((orbit_number - 73) % 175) + 1)
        elif sat_name == 'S1B':
            rel_orbit_num = str(((orbit_number - 27) % 175) + 1)

        while len(rel_orbit_num) < 3:
            rel_orbit_num = '0' + rel_orbit_num
        return rel_orbit_num

    def _get_img_name(self, scene):
        # satellite-name_S2-tile-name_polarization_path_relative-orbit-number_date-txxxxxx.tif
        return '_'.join([scene["sat_name"], self.tile_name, scene["polarization"], scene["orbit_path"][:3],
                         scene['rel_orbit_num'], scene['time'], 'txxxxxx.tif'])

    def _save_raster(self, path, array, name):
        src_w, src_h = array.shape
        if self.aoi.crs.value == str(self.epsg):
            x, _ = self.aoi.lower_left
            _, y = self.aoi.upper_right
            transform = Affine(a=self.setting['resx'], b=0, c=x, d=0, e=-self.setting['resy'], f=y)
            profile = {'driver': 'GTiff',
                       'dtype': 'float32',
                       'nodata': self.setting['nodata'],
                       'width': src_w,
                       'height': src_h,
                       'count': 1,
                       'crs': self.aoi.crs.opengis_string,
                       'transform': transform}
        else:
            src = {'init': f'EPSG:{self.aoi.crs.value}'}
            dst = {'init': f'EPSG:{str(self.epsg)}'}
            left, bottom = self.aoi.lower_left
            right, top = self.aoi.upper_right
            self.aoi = self.aoi.transform(self.epsg)
            transform, width, height = calculate_default_transform(src, dst, src_w, src_h, left=left, bottom=bottom,
                                                                   right=right, top=top, dst_width=src_w, dst_height=src_h)
            profile = {'driver': 'GTiff',
                       'dtype': 'float32',
                       'nodata': self.setting['nodata'],
                       'width': width,
                       'height': height,
                       'count': 1,
                       'crs': self.aoi.crs.opengis_string,
                       'transform': transform}

        with raster_open(os.path.join(path, name), "w", **profile) as dest:
                dest.write(array, 1)