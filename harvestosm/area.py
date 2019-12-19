import utils

class Area:

    def __init__(self, coords, out):
        """
        :param name: name of area
        :param coords: list of coords tupples (lon,lat)
        """
        self.coords = coords
        self.out = out
        self._name = utils.random_name()

    @classmethod
    def from_shape(cls, shape, **kwargs):
        """ Shapely objects with coords set as (lon,lat)"""
        coords = Area._get_coords(shape)

        return cls(coords, out='poly')

    @classmethod
    def from_coords(cls, coords, **kwargs):
        """ Coorodinates as tuple of tuples (lon,lat)"""
        return cls(coords, out='points')

    @classmethod
    def from_bbox(cls, bbox, **kwargs):
        """Bounding region (min_lat, min_lon, max_lat, max_lon) """
        coords=[(bbox[0],bbox[1]),(bbox[2],bbox[1]),(bbox[2],bbox[3]),(bbox[0],bbox[3])]
        return cls(coords, out='bbox')

    @property
    def poly(self):
        """Return overpass area by poly statement as string ie. return (poly: "lat1 lon1 lat2 lon2...")"""
        process = ['_switch_pair_order', '_dissolve_pair_list', '_overpass_poly']
        return Area._execute_process(process, self.coords)

    @property
    def points(self):
        """Return overpass area by poly statement as string ie. return (poly: "lat1 lon1 lat2 lon2...")"""
        process = ['_switch_pair_order', '_overpass_points']
        return Area._execute_process(process, self.coords)

    @property
    def bbox(self):
        """Returns minimum bounding region (minx, miny, maxx, maxy)"""
        min_lat = min(item[1] for item in self.coords)
        min_lon = min(item[0] for item in self.coords)
        max_lat = max(item[1] for item in self.coords)
        max_lon = max(item[0] for item in self.coords)

        return f'({min_lat},{min_lon},{max_lat},{max_lon})'

    @staticmethod
    def _execute_process(process, to_process):
        res = to_process
        for method in process:
            res = getattr(Area, method).__call__(res)
        return res

    @staticmethod
    def _get_coords(shape):
        """Extract coords fron shaply object"""
        if shape.geom_type == 'Polygon':
            return list(shape.exterior.coords)
        elif shape.geom_type in ['Point','LinearRing','LineString']:
            return list(shape.coords)
        else:
            print(f'Shape {shape.geom_type} is not supported')

    @staticmethod
    def _switch_pair_order(pair_list):
        """Switch order og lon lat coord to lat long
        (used for generating overpass poly query)"""
        return [(second, first) for first, second in pair_list]

    @staticmethod
    def _dissolve_pair_list(pair_list):
        """dissolve list of tupples to list of following elementssw
        (used for generating overpass poly query)"""
        return [item for pair in pair_list for item in pair]

    @staticmethod
    def _overpass_poly(coords_list):
        return '(poly: "{}")'.format(' '.join([str(x) for x in coords_list]))

    @staticmethod
    def _overpass_points(coords_list):
        return '("{}")'.format(' '.join([str(x) for x in coords_list]))
