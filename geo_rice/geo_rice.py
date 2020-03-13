from oauthlib.oauth2 import BackendApplicationClient
from requests_oauthlib import OAuth2Session
from requests import post
from rasterio.merge import merge
from rasterio import open as rastopen, MemoryFile
from datetime import datetime
import os, concurrent.futures, geojson, numpy
from rasterio.crs import CRS
from rasterio.transform import Affine


class GeoRice:
    """
    GeoRice class - encapsulated methods and scripts to get geo rice product from Sentinel hub. The task for gathering
    rice tiles is initiated by initialization of class by inputting sentinel hub credentials.
    task = GeoRice(hub_id, secret)
    It is necessary to set the following inputs:
    - AOI       / by 'area_by_bbox(bbox)' method where bbox is a list of int of [minx, miny, maxx, maxy]
                / alternatively by any geofile object with __geo_interface__ via method 'area_by_file(object)'
    - period    / by 'set_period(period)' method where period is a list of start and end time ad datetime object
    - epsg      / by 'set_epsg(epsg)' method where epsg code is given by integer. This version is writen only for
                / projected coordinate systems with units of measurements in meters (grid is calculated according to
                / tile width and height that is 10000m. Tested on UTM 32648
    - path      / path of output folder via 'set_output(path)'

    Data are harvested into the output folder after the setting of all inputs by dump() method.
    """
    _TOKEN_ENDPOINT = 'https://services.sentinel-hub.com/oauth/token'
    _SENTINEL_ENDPOIT = 'https://services.sentinel-hub.com/api/v1/process'
    _TILE_LENGTH = 10000 #m
    _TILE_PX = 1000 #px
    _PARAMS_TEMPLATE = {'epsg': None, 'sat_name': None, 's2_time_name': None, 'polar': None, 'orbit_path': None,
                        'orbit_num': None, 'no_data': None}

    def __init__(self, hub_id=None, secret=None, period=None, bbox=None, params=None):
        """
        hub_id - sentinel hub clinet id
        secret - sentinel hub client secret
        period - list [start, end] / datetime objects
        bbox   - lits of [minx, miny, maxx, maxy]
        params - dict payload parameters:
            epsg            - epsg code (UTM)
            sat_name        - satelite name
            s2_time_name    -
            polar           - polarization ('VV', 'VH', 'HV', 'HH')
            orbit_path      - DESC - DESCENDING, ASC - ASCENDING
        """
        self.token = GeoRice._get_token(hub_id, secret)
        self.period = period
        self.bbox = bbox
        self.name = []
        self._tiles = []
        self._pars = []
        self._bounds = None

        if params is None:
            self.pars = GeoRice._PARAMS_TEMPLATE
        elif isinstance(params, dict):
            self.pars = params
        else:
            raise Exception('Parameters can dictionary with all parameters similar to set_params method or None')

    def set_period(self, start, end):
        """Set a period as list [start,end] / datetime objects """
        if isinstance(start, datetime) and isinstance(end, datetime):
            self.period = [start, end]
        else:
            raise Exception('Start or End input is not a datetime object')
        return self

    def area_by_bbox(self, bbox):
        """bbox as [minx,miny,maxx,maxy]"""
        self.bbox = bbox
        return self

    def area_by_file(self, file):
        """Set the aoi from geofile with __geo_interface__ """
        try:
            self.bbox = file.__geo_interface__['bbox']
        except KeyError:
            self.bbox = GeoRice._get_bbox(file.__geo_interface__["features"])
        except AttributeError:
            raise Exception('Imported file has not __geo_interface__ attribute')
        return self

    # def set_pars(self, *args, epsg=None, sat_name=None, s2_time_name=None, polar=None, orbit_path=None, orbit_num=None,
    #              no_data=-999):
    #     """Setting of scihub request payload parameters. Parameters as keywords arguments or dict"""
    #
    #     pars = GeoRice._wrap_pars(epsg, sat_name, s2_time_name, polar, orbit_path, orbit_num, no_data, *args)
    #
    #     self.name = GeoRice._crt_out_name(pars)
    #     for k, v in pars.items():
    #         self.pars[k] = GeoRice._check_pars(k, v)
    #     return self

    def set_pars(self, *args, epsg=None, sat_name=None, s2_time_name=None, polar=None, orbit_path=None, orbit_num=None,
                     no_data=-999):
        """Setting of scihub request payload parameters. Parameters as keywords arguments or dict"""
        pars = GeoRice._wrap_pars(epsg, sat_name, s2_time_name, polar, orbit_path, orbit_num, no_data, *args)
        self._bounds = max([len(v) for k, v in pars.items() if isinstance(v, list)])

        for n in range(self._bounds):
            self._pars.append({})
            for k, v in pars.items():
                if isinstance(v, list):
                    self._pars[n][k] = GeoRice._check_pars(k, v[n])
                else:
                    self._pars[n][k] = GeoRice._check_pars(k, v)
            self.name.append(GeoRice._crt_out_name(self._pars[n]))

        return self

    @staticmethod
    def _check_pars(key, value):
        check = {'epsg': GeoRice._set_epsg,
                 'sat_name': GeoRice._set_sat_name,
                 's2_time_name': GeoRice._return_value,
                 'polar': GeoRice._set_polar,
                 'orbit_path': GeoRice._set_orbit,
                 'orbit_num': GeoRice._return_value,
                 'no_data': GeoRice._return_value}


        method = check[key]
        return method(value)

    @staticmethod
    def _set_orbit(val):
        if val.upper().find('ASC') >= 0:
            return 'ASCENDING'
        elif val.upper().find('DESC') >= 0:
            return 'DESCENDING'
        else:
            raise Exception('Orbit path does not recognized. Set "ASC" for ascending or "DESC" for descending')

    @staticmethod
    def _set_polar(val):
        if val.upper() in ['VV', 'VH', 'HV', 'HH']:
            return val.upper()
        else:
            raise Exception("Supported values of polarization are: 'VV', 'VH', 'HV', 'HH'" )

    @staticmethod
    def _return_value(val):
        return val

    @staticmethod
    def _set_sat_name(sat_name):
        if sat_name.upper() in ['S1GRD', 'S1', 'S1A', 'S1B', 'S1C', 'S1D']:
            return 'S1GRD'
        else:
            raise Exception('Satellite name does not recognized. Recommended to use sentinel-hub identifier')

    @staticmethod
    def _set_epsg(epsg):
        if type(epsg) is int:
            pass
        elif type(epsg) is str and epsg.isdigit():
            epsg = int(epsg)
        else:
            raise Exception('EPSG code have to be set as int or str of digits')
        if epsg == 4326:
            raise Exception('EPSG code should be UTM')
        else:
            return epsg

    @staticmethod
    def _wrap_pars(epsg=None, sat_name=None, s2_time_name=None, polar=None, orbit_path=None, orbit_num=None,
                   no_data=None, *args):
        pars = GeoRice._PARAMS_TEMPLATE
        try:
            pars.update(args[0])
        except IndexError:
            pass
        for key in pars.keys():
            if pars[key] is None:
                pars[key] = locals()[key]
        return pars

    @staticmethod
    def _crt_out_name(pars):
        name_k = ['sat_name', 's2_time_name', 'polar', 'orbit_path', 'orbit_num']
        return '_'.join([str(pars[k]).upper() for k in name_k])

    def dump(self, path, name=None):
        """
        This method will download tiles from sentinel hub for generated grid. Method use threding for sped up.vEach tile
        is hold in memory. Result is a mosaic.
        params:
        path - path to output folder
        name - optional. If is None, default name generated from input parameters is used
        """
        for n in range(self._bounds):
            if name is None:
                name = self.name[n] + '_' + '_'.join([p.strftime('%Y%m%d') for p in self.period]) +'txxxxxx.tif'
            elif name.find('.tiff') < 0:
                name = name + '.tiff'

            with concurrent.futures.ThreadPoolExecutor() as pool:
                results = pool.map(lambda p: self.get_from_sh(*p), ((coors, n) for coors in self._grid_generator()))
                self._tiles = [res for res in results if res is not None]
                self.mosaic(path, name)
                self._tiles = []

    def get_from_sh(self, coors, bound):
        payload = self._crt_payload(coors, bound)
        response = post(GeoRice._SENTINEL_ENDPOIT, headers={"Authorization": "Bearer " + self.token},
                        json=payload, files={}, allow_redirects=False)
        if response.status_code == 200:
            return self._memfile(response.content, coors[0][3][0], coors[0][3][1])
        else:
            print(response.status_code)
            print(response.text)

    def dump_slow(self, path, name=None):
        """
        This method will generate grided payloads from bbox and download geotiff tiles from sentinel to output folder
        path: path to output folder
        """
        grid = self._grid_generator()

        for coors, i, j in grid:
            payload = self._crt_payload(coors)
            response = post(GeoRice._SENTINEL_ENDPOIT, headers={"Authorization": "Bearer " + self.token},
                            json=payload, files={}, allow_redirects=False)
            if response.status_code == 200:
                self._tiles.append(self._memfile(response.content, coors[0][3][0], coors[0][3][1]))
            else:
                print(response.status_code)
                print(response.text)
        self.mosaic(path, name)


    @staticmethod
    def _bite2array(data):
        with MemoryFile(data) as memfile:
            with memfile.open() as dataset:
                return dataset.read()

    def _memfile(self, data, x, y):
        """Return a virtual dataset
        data : bites
        x : upper left x coors
        y : upper left y coors
        """

        array = self._bite2array(data)
        resolution = self._TILE_LENGTH/self._TILE_PX
        transform = Affine(a=resolution, b=0, c=x, d=0, e=-resolution, f=y)
        profile = {'driver': 'GTiff', 'dtype': 'float32', 'nodata': None, 'width': self._TILE_PX,
               'height': self._TILE_PX, 'count': 1, 'crs': CRS.from_epsg(self.pars['epsg']), 'transform': transform}

        memfile = MemoryFile()
        dataset = memfile.open(**profile)
        dataset.write(array)
        return dataset

    def mosaic(self, path, name):
        """
        """
        # setting up the output name
        mosaic, out_trans = merge(self._tiles, nodata=self.pars['no_data'])
        out_meta = self._tiles[1].meta.copy()
        # Update the metadata
        out_meta.update({"driver": "GTiff",
                         "height": mosaic.shape[1],
                         "width": mosaic.shape[2],
                         "transform": out_trans,
                         "crs": f'http://www.opengis.net/def/crs/EPSG/0/{str(self.pars["epsg"])}'})
        # Write the mosaic raster to disk
        with rastopen(os.path.join(path, name), "w", **out_meta) as dest:
            dest.write(mosaic)

    @staticmethod
    def _get_token(hub_id, secret):
        """Return sentinel hub acess tokoen for given client_id and client_secret """
        # Create a session
        client = BackendApplicationClient(client_id=hub_id)
        oauth = OAuth2Session(client=client)
        # Get token for the session
        try:
            return oauth.fetch_token(token_url=GeoRice._TOKEN_ENDPOINT, client_id=hub_id,
                                     client_secret=secret)['access_token']
        except Exception as e:
            print(e)

    def _grid_generator(self):
        x, y, j, length = self.bbox[0], self.bbox[1], 1, GeoRice._TILE_LENGTH
        while y < self.bbox[3]:
            i = 1
            while x < self.bbox[2]:
                yield [[[x, y], [x+length, y], [x+length, y+length], [x, y+length], [x, y]]]
                x += length
                i += 1
            y += length
            j += 1
            x = self.bbox[0]

    def _crt_payload(self, coors, bound):
        """return payload"""
        return {

            "input": {
                "bounds": {
                    "geometry": {
                        "type": "Polygon",
                        "coordinates": coors
                    },
                    "properties": {
                        "crs": f'http://www.opengis.net/def/crs/EPSG/0/{str(self._pars[bound]["epsg"])}'
                    }
                },
                "data": [
                    {
                        "type": self._pars[bound]['sat_name'].upper(),
                        "dataFilter": {
                            "timeRange": {
                                "from": self.period[0].isoformat() + 'Z',
                                "to": self.period[1].isoformat() + 'Z'
                            },
                            "acquisitionMode": "IW",
                            "polarization": "DV",
                            "orbitDirection": self._pars[bound]['orbit_path'].upper()
                        },
                        "processing": {
                            "orthorectify": "true",
                            "backCoeff": "GAMMA0_ELLIPSOID"
                        }
                    }
                ]
            },
            "output": {
                "width": GeoRice._TILE_PX,
                "height": GeoRice._TILE_PX,
                "responses": [
                    {
                        "identifier": "default",
                        "format": {
                            "type": "image/tiff"
                        }
                    }
                ]
            },
            "evalscript": '''//VERSION=3
                    function setup() {
                      return {
                        input: ["POLAR"],
                        output: { id:"default", bands: 1, sampleType: SampleType.FLOAT32}
                      }
                    }
            
                    function evaluatePixel(samples) {
                      return [samples.POLAR]
                    }'''.replace('POLAR', self._pars[bound]['polar'])
        }

    @staticmethod
    def _get_bbox(features):
        x, y = [], []
        for feature in features:
            cors = list(geojson.utils.coords(feature))
            x += [cor1[0] for cor1 in cors]
            y += [cor2[1] for cor2 in cors]
        return [min(x), min(y), max(x), max(y)]


if __name__ == '__main__':

    # set sentinel hub credentials
    client_id = 'e41fd1c6-1567-460c-b0e5-778a47823153'
    client_secret = 'IeGysaJCLwmMtYBfQzqi'

    # set input geofile as object with __geo_interface_ protocol  and epsg (int). Works for UTM
    import geopandas
    epsg=32648
    geofile = "C:\Michal\gisat\projects\Euro_Cube\\48PWS.geojson"

    aoi = geopandas.read_file(geofile).to_crs(epsg=epsg)
    # geofile = "C:\Michal\gisat\projects\Euro_Cube\\rice2.geojson"
    # with open(geofile,  'r', encoding="utf8") as f:
    #     aoi = geojson.load(f)

    # set output folder
    output = "C:\Michal\gisat\projects\Euro_Cube\output"

    # set period as datetime object

    period1 = datetime.strptime(str(20180501), '%Y%m%d')
    period2 = datetime.strptime(str(20181231), '%Y%m%d')


    # create a task
    # parameters can be set as key word arguments. Important parameters are sat_name (right just only for S! satelites,
    # polarization and orbit path. Rest is fakeing
    task = GeoRice(client_id, client_secret).set_period(period1, period2).area_by_file(aoi).set_pars(epsg=epsg,
                                sat_name='S1a', s2_time_name='48PWS', polar=['VV','VH'], orbit_path='ASC', orbit_num=18)

    # or as dictionary payload
    # parameters = {'epsg': '32648', 'sat_name': 'S1a', 's2_time_name': '48PWS', 'polar': 'vv', 'orbit_path': 'ASC',
    #                'orbit_num': 18}
    # task = GeoRice(client_id, client_secret).set_period(period1, period2).area_by_file(aoi).set_pars(parameters)

    # dump method is used for getting of resulting mosaic
    task.dump(output)




