import concurrent.futures
import os
from datetime import datetime
from urllib.parse import urlencode
from rasterio import open as raster_open
from rasterio.transform import Affine
from rasterio.warp import calculate_default_transform
from rasterio.features import rasterize
from requests import get
from sentinelhub import BBox, SentinelHubRequest, SHConfig, MimeType
from itertools import repeat
from .utils import load_config, load_sh
from pyproj import CRS, Transformer
from shapely.ops import transform
from shapely.geometry import Polygon, MultiPolygon, shape
from shapely.wkt import loads
from shapely.geometry.base import BaseGeometry
from math import ceil, log10
from copy import deepcopy
import numpy


class GetSentinel:

    def __init__(self):
        self.SHConfig = load_sh()
        self.period = []
        self.tile_name = ''
        self.fld_name = ''
        self._scenes = []
        self.epsg = None
        self.aoi = None
        self.nodata = -999
        self.lx = self.config.get('img_width')*self.config.get('resolution')
        self.ly = self.config.get('img_height')*self.config.get('resolution')
        self.wsf_offset = 0

    @property
    def config(self):
        return load_config()

    @property
    def resolution(self):
        return load_config().get('resolution')

    @property
    def polar_modes(self):
        return load_config().get('polar_modes')

    def __copy__(self):
        return deepcopy(self)

    def scenes(self):
        """Return string representation of found scenes"""
        if len(self._scenes) == 0:
            print(f'For given input parameters 0 scenes were found')
        elif len(self._scenes) > 0:
            print(f"{len(self._scenes)} were found for period {'/'.join([p.isoformat() for p in self.period])}")
            for index, scene in enumerate(self._scenes):
                print(f'{index}: {scene}')

    def search(self, bbox, epsg, period):
        """
        set input parameters, then start processing of parameters i.e. find available scenes
        :param bbox: list of coordinates representing bbox or object with __geo_interface__ and bbox attribute
        :param epsg: int
        :param period: tuple (str, str). date format YYYYMMDD
        :param tile_name: str, serve to name the AOI, corresponding scenes and rice maps are download and saved into
               folder of the same name
        :param info: bool, turn off/on writing down list of found scenes
        """
        self.epsg = epsg
        self.aoi = Geometry.from_bbox(bbox, epsg)

        if self.epsg == 4326:
            self.aoi = self.aoi.transform(3857)
        self.aoi.round_geom(-int(log10(self.resolution)))
        self.period = [datetime.strptime(time, '%Y%m%d') for time in period]

        while True:
            self._scenes += [Scene(scene) for scene in self.search_archive().get('features')]
            if len(self._scenes) >= self.wsf_offset:
                self.wsf_offset += 100
            else:
                self.wsf_offset = 0
                break
        self._scenes = list(filter(lambda x: x.polar == 'DV', self._scenes))

    def filter(self, inplace, *args, **kwargs):
        scenes = []
        for name, value in kwargs.items():
            if value is not None:
                if isinstance(value, (tuple, list)):
                    for val in value:
                        scenes += list(filter(lambda x: x.__getattribute__(name) == val, self._scenes))
                else:
                    scenes += list(filter(lambda x: x.__getattribute__(name) == value, self._scenes))
        if inplace:
            self._scenes = list(set(scenes))
            return self
        else:
            return list(set(scenes))

    def set_tile_name(self, tile_name, part):
        if tile_name.find('_') < 0:
            self.tile_name = part + tile_name
            self.fld_name = tile_name
        else:
            raise ValueError('Tile name cannot contain underscore character "_". Underscore character is used to split '
                         'scene meta data writen into resulting scene name')

    def download(self, tile_name='Tile', part=''):
        self.set_tile_name(tile_name, part)

        for scene in self._scenes:
            debug = True
            self.aoi.grid_length = (self.lx, self.ly)
            nx, ny = self.aoi.grid_size
            for mode in self.polar_modes:
                scene.polar = mode
                if debug:
                    tiles = [self.download_tiles(scene, grid) for grid in self.aoi.iter()]
                else:
                    with concurrent.futures.ThreadPoolExecutor() as pool:
                        results = pool.map(self.download_tiles, repeat(scene), [grid for grid in iter(self.aoi)])
                        tiles = [res for res in results]

                blocks = [tiles[i:i + nx] for i in range(0, len(tiles), nx)]
                array = numpy.block(blocks)

                name = self.scene_name(scene, self.tile_name)
                self.save_raster(array, name)
                del tiles, array

    @staticmethod
    def scene_name(scene, tile_name):
        # satellite_tile-name_polarization_path_relative-orbit-number_date-txxxxxx.tif
        return '_'.join([scene.satellite, tile_name, scene.polar, scene.orbit_path,
                         scene.rel_orbit_num, scene.from_time.strftime('%Y%m%d'), 'txxxxxx.tif'])

    def download_tiles(self, scene, grid):
        bbox, shape = grid
        x, y = map(lambda coor: int(coor/self.resolution), shape)
        if scene.geometry.intersects(bbox):
            array = self.request(scene, bbox, (x, y))

            diff = bbox.difference(scene.geometry)
            if diff.area != 0:
                x0, _, _, ye = bbox.bounds
                transform = Affine(a=self.resolution, b=0, c=x0, d=0, e=-self.resolution, f=ye)
                mask = rasterize([(diff, True)], out_shape=(y, x), transform=transform, fill=False,
                                 all_touched=True)
                array = numpy.where(mask, self.nodata, array)
        else:
            array = None

        if array is not None:
            return array
        else:
            return self.nodata_tile((x, y))

    def nodata_tile(self, shape):
        x, y = shape
        return numpy.ones(shape=(y, x)).astype('float32')*self.nodata

    def request(self, scene, bbox, shape):
        x, y = shape
        evalscript = '''//VERSION=3
                    function setup() {
                      return {
                        input: ["POLAR"],
                        output: { id:"default", bands: 1, sampleType: SampleType.FLOAT32}
                      }
                    }
            
                    function evaluatePixel(samples) {
                      return [samples.POLAR]
                    }'''.replace('POLAR', scene.polar)

        request = SentinelHubRequest(
            evalscript=evalscript,
            input_data=[
                {
                    "type": "S1GRD",
                    "dataFilter": {
                        "timeRange": {
                            "from": scene.from_time.strftime('%Y-%m-%dT%H:%M:%SZ'),
                            "to": scene.to_time.strftime('%Y-%m-%dT%H:%M:%SZ')
                        },
                        "acquisitionMode": "IW",
                        "polarization": "DV",
                        "orbitDirection ": scene.orbit_path
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
            bbox=BBox(bbox, self.aoi.crs.to_epsg()),
            size=(x, y),
            config=SHConfig()
        )

        array = request.get_data(max_threads=min(32, os.cpu_count() + 4))[0]
        if array is not None:
            return array
        else:
            return None

    def search_archive(self):
        """ Collects data from WFS service
        :return: list o scenes properties for given input parameters
        :rtype: list
        """
        main_url = '{}/{}?'.format('https://services.sentinel-hub.com/ogc/wfs', self.SHConfig.instance_id)
        params = {
            'REQUEST': 'GetFeature',
            'TYPENAMES': 'DSS3',
            'BBOX': ','.join(map(str, self.aoi.bbox)),
            'OUTPUTFORMAT': 'application/json',
            'SRSNAME': f'{self.aoi.crs}'.upper(),
            'TIME': '/'.join([p.isoformat() for p in self.period]),
            'MAXCC': 100.0 * 100,
            'MAXFEATURES': 100,
            'FEATURE_OFFSET': self.wsf_offset,
            'VERSION': self.config.get('wsf_version')
        }
        url = main_url + urlencode(params)
        response = get(url)
        if response.status_code == 200:
            return response.json()
        else:
            raise Exception(f'Connection to Sentinel Hub WSF failed. Reason: {response.status_code}')

    def save_raster(self, array, name):
        height, width = array.shape
        if self.aoi.crs.to_epsg() == self.epsg:
            x, y = self.aoi.upper_left
            transform = Affine(a=self.resolution, b=0, c=x, d=0, e=-self.resolution, f=y)
        else:
            src = {'init': f'EPSG:{self.aoi.crs.to_epsg()}'}
            dst = {'init': f'EPSG:{str(self.epsg)}'}
            left, top = self.aoi.upper_left
            bottom = top - height * self.resolution
            right = left + width * self.resolution
            transform, width, height = calculate_default_transform(src, dst, width, height, left=left, bottom=bottom,
                                                                   right=right, top=top, dst_width=width,
                                                                   dst_height=height)
        profile = {'driver': 'GTiff',
                    'dtype': 'float32',
                   'nodata': self.nodata,
                   'width': width,
                   'height': height,
                   'count': 1,
                   'crs': f'http://www.opengis.net/def/crs/EPSG/0/{self.epsg}',
                   'transform': transform}

        path = os.path.join(self.config.get("output"), self.fld_name, 'scenes')
        if not os.path.exists(path):
            os.makedirs(path, exist_ok=True)

        with raster_open(os.path.join(path, name), "w", **profile, compress='lzw') as dest:
            dest.write(array, 1)


class Geometry:
    """ A class that combines shapely geometry with coordinate reference system. It currently supports polygons and
    multipolygons.

    It can be initialize with any of the following geometry representations:
    - `shapely.geometry.Polygon` or `shapely.geometry.MultiPolygon`
    - A GeoJSON dictionary with (multi)polygon coordinates
    - A WKT string with (multi)polygon coordinates
    """
    def __init__(self, geometry, crs, grid_leght=(1000, 1000)):
        """
        :param geometry: A polygon or multipolygon in any valid representation
        :type geometry: shapely.geometry.Polygon or shapely.geometry.MultiPolygon or dict or str
        :param crs: Coordinate reference system of the geometry
        :type crs: Pyproj.CRS or epsg as int or str
        :param  grid_leght: grid size in map units
        :type  grid_leght: tuple (x lenght, y length)
        """
        self._geometry = self._parse_geometry(geometry)
        self._crs = self._parse_crs(crs)
        self._grid_length = grid_leght

    @classmethod
    def from_geojson(cls, geojson):
        """Return Geometry from geojson"""
        try:
            crs = CRS.from_string(geojson.get('geometry').get('crs').get('properties').get('name'))
        except AttributeError:
            crs = CRS.from_string(geojson.get('properties').get('crs'))
        return cls(geojson.get('geometry'), crs)

    @classmethod
    def from_bbox(cls, bbox, crs):
        """ Construct Bbox

        :param bbox: A polygon or multipolygon in any valid representation
                1) ``((min_x,min_y),(max_x,max_y))``,
                2) ``(min_x,min_y,max_x,max_y)``,
                3) ``[min_x,min_y,max_x,max_y]``,
                4) ``[[min_x, min_y],[max_x,max_y]]``,
                5) ``[(min_x, min_y),(max_x,max_y)]``,
                6) ``([min_x, min_y],[max_x,max_y])``,
                7) ``'min_x,min_y,max_x,max_y'``,
        :param crs: Coordinate reference system of the geometry
        :type crs: Pyproj.CRS or epsg as int or str
        """

        return cls(Geometry._bbox2shapely(bbox), crs)

    def __repr__(self):
        """ Method for class representation
        """
        return '{}({}, crs={})'.format(self.__class__.__name__, self._geometry.wkt, self.crs)

    def __eq__(self, other):
        """ Method for comparing two Geometry classes

        :param other: Another Geometry object
        :type other: Geometry
        :return: `True` if geometry objects have the same geometry and CRS and `False` otherwise
        :rtype: bool
        """
        return self.geometry == other.geometry and self.crs == other.crs

    def iter(self):
        return self.__iter__()

    def __iter__(self):
        xs, ys = self.upper_left
        xe, ye = self.lower_right
        lx, ly = self.grid_length
        y = ys

        while y != ye:
            x, y0 = xs, y
            if y - ly > ye:
                y -= ly
            elif y - ly <= ye:
                y -= abs(y-ye)
            while x != xe:
                x0 = x
                if x + lx < xe:
                    x += lx
                elif x + lx >= xe:
                    x += abs(x-xe)
                yield self._bbox2shapely([(x0, y), (x, y0)]), (abs(x0-x), abs(y0-y))

    def __next__(self):
        return self

    @property
    def grid_length(self):
        """ Return x, y length of grid (default 1000, 1000) """
        return self._grid_length

    @grid_length.setter
    def grid_length(self, lengths):
        if isinstance(lengths, (list, tuple)) and all([isinstance(length, int) for length in lengths]):
            self._grid_length = lengths

    @property
    def grid_size(self):
        """ Return size of grid (nx ny) """
        x0, y0 = self.lower_left
        xe, ye = self.upper_right
        lx, ly = self.grid_length
        return ceil(abs(xe-x0)/lx), ceil(abs(ye-y0)/ly)

    @property
    def geometry(self):
        """ Returns shapely object representing geometry in this class
        :return: A polygon or a multipolygon in shapely format
        :rtype: shapely.geometry.Polygon or shapely.geometry.MultiPolygon
        """
        return self._geometry

    @property
    def crs(self):
        """ Returns crs representing coordination system
        :return: Pyproj.CRS
        """
        return self._crs

    @property
    def bbox(self):
        """ Returns bbox of the geometry
        :return: A bounding box
        """
        return self.geometry.bounds

    @property
    def lower_left(self):
        """ Returns lower left corner of bbox (minx, miny)

        :return: lower left corner of bbox (minx, miny)
        :rtype: touple
        """
        return self.geometry.bounds[0:2]

    @property
    def upper_left(self):
        """ Returns lower left corner of bbox (minx, miny)

        :return: lower left corner of bbox (minx, miny)
        :rtype: touple
        """
        return self.geometry.bounds[0], self.geometry.bounds[-1]

    @property
    def upper_right(self):
        """ Returns upper right corner of bbox (maxx, maxy)

        :return: upper right corner of bbox (maxx, maxy)
        :rtype: touple
        """
        return self.geometry.bounds[2:4]

    @property
    def lower_right(self):
        """ Returns upper right corner of bbox (maxx, maxy)

        :return: upper right corner of bbox (maxx, maxy)
        :rtype: touple
        """
        return self.geometry.bounds[2], self.geometry.bounds[1]

    def reverse(self):
        """ Returns a new Geometry object where x and y coordinates are switched

        :return: New Geometry object with switched coordinates
        :rtype: Geometry
        """
        return Geometry(transform(lambda x, y: (y, x), self.geometry), crs=self.crs)

    def round_geom(self, n=1):
        """ Returns a new Geometry object where x and y coordinates are round in units are meters

        :return: New Geometry object with switched coordinates
        :rtype: Geometry
        """
        if self.crs.to_dict().get('units') == 'm':
            self._geometry = transform(lambda x, y: (round(x, n), round(y, n)), self.geometry)
            return self
        else:
            raise Exception(f'Round method is define for "meters". Actual units of CRS is '
                            f'{self.crs.to_dict().get("units")}')

    def transform(self, crs):
        """ Transforms Geometry from current CRS to target CRS
        :param crs: target CRS
        :type crs: constants.CRS
        :return: Geometry in target CRS
        :rtype: Geometry
        """
        new_crs = self._parse_crs(crs)
        if new_crs is not self.crs:
            project = Transformer.from_crs(self.crs.to_epsg(), new_crs.to_epsg(), always_xy=True)
            self._geometry = transform(project.transform, self.geometry)
            self._crs = new_crs
        return self

    def difference(self, other):
        """
        Return Geometry object (self) - (other)
        :param other: Geometry object
        :return:
        """
        return Geometry(self.geometry.difference(other.geometry), self.crs)


    @staticmethod
    def _parse_crs(crs):
        if isinstance(crs, CRS):
            pass
        elif isinstance(crs, (int, str)):
            crs = CRS.from_epsg(crs)
        else:
            raise Exception('CRS should be Pyproj.CRS or epsg code given by int or str ')
        return crs

    @staticmethod
    def _parse_geometry(geometry):
        """ Parses given geometry into shapely object
        :param geometry:
        :return: Shapely polygon or multipolygon
        :rtype: shapely.geometry.Polygon or shapely.geometry.MultiPolygon
        :raises TypeError
        """
        if isinstance(geometry, str):
            geometry = loads(geometry)
        elif isinstance(geometry, dict):
            geometry = shape(geometry)
        elif not isinstance(geometry, BaseGeometry):
            raise TypeError('Unsupported geometry representation')
        if not isinstance(geometry, (Polygon, MultiPolygon)):
            raise ValueError('Supported geometry types are polygon and multipolygon, got {}'.format(type(geometry)))
        return geometry

    @staticmethod
    def _bbox2shapely(bbox):
        """ Converts the input coordination representation (see the constructor docstring for a list of valid
        representations) into a flat tuple

        :param bbox: A bbox in one of several forms listed in the class description.
        :return: shapely.geometry.polygon
        :raises: TypeError
        """
        if isinstance(bbox, (list, tuple)):
            if len(bbox) == 4:
                points = tuple(map(float, bbox))
                return Polygon(Geometry._bbox2poly(points))
            if len(bbox) == 2 and all([isinstance(point, (list, tuple)) for point in bbox]):
                points = [coor for coors in bbox for coor in coors]
                return Polygon(Geometry._bbox2poly(points))
            raise TypeError('Expected a valid list or tuple representation of a bbox')
        if isinstance(bbox, str):
            points = tuple([float(s) for s in bbox.replace(',', ' ').split() if s])
            return Polygon(list(zip(points[::2], points[1::2])))
        raise TypeError('Invalid bbox representation')

    @staticmethod
    def _bbox2poly(bbox):
        """From tuple (minx, miny, maxx, maxy) calculate remaining corners"""
        minx, miny, maxx, maxy = bbox
        return (minx, miny), (maxx, miny), (maxx, maxy), (minx, maxy)


class Scene(Geometry):
    """
    Class to handle with SH scenes and their geometries
    """

    def __init__(self, geojson):
        """
        Create Scenes class from wsf Geojson
        :param tile_name: str - Name of tile
        :param geojson: json - geojson - from wsf SH
        :return: List of
        """
        try:
            crs = CRS.from_string(geojson.get('geometry').get('crs').get('properties').get('name'))
        except Exception:
            crs = CRS.from_string(geojson.get('properties').get('crs'))

        geometry = shape(geojson.get('geometry'))
        orbit_path = geojson.get('properties').get('orbitDirection')[:3]

        satellite, polar, abs_orbit_num, from_time, to_time = Scene._parsename(geojson.get('properties').get('id'))

        self.satellite = satellite
        self.polar = polar
        self.abs_orbit_num = abs_orbit_num
        self.orbit_path = orbit_path
        self.from_time = from_time
        self.to_time = to_time
        super().__init__(geometry, crs)

    def __repr__(self):
        """String representation of scene"""
        return f'satellite: {self.satellite}, polarization: {self.polar}, orbit_number: {self.rel_orbit_num}, ' \
               f'orbit_path: {self.orbit_path}'

    def __key(self):
        return self.bbox, self.from_time, self.to_time, self.orbit_path, self.abs_orbit_num, self.satellite, self.polar

    def __hash__(self):
        return hash(self.__key())

    def __eq__(self, other):
        if isinstance(other, Scene):
            return self.__key() == other.__key()
        return NotImplemented

    @property
    def rel_orbit_num(self):
        orbit_number = int(self.abs_orbit_num.lstrip('0'))
        if self.satellite == 'S1A':
            rel_orbit_num = str(((orbit_number - 73) % 175) + 1)
        elif self.satellite == 'S1B':
            rel_orbit_num = str(((orbit_number - 27) % 175) + 1)
        while len(rel_orbit_num) < 3:
            rel_orbit_num = '0' + rel_orbit_num
        return rel_orbit_num

    @staticmethod
    def _parsename(name):
        satellite, _, _, polar, from_time, to_time, orbit_num, _, _ = name.split('_')
        from_time = datetime.strptime(from_time, '%Y%m%dT%H%M%S')
        to_time = datetime.strptime(to_time, '%Y%m%dT%H%M%S')
        return satellite, polar[-2:], orbit_num, from_time, to_time
