import geopandas
import geojson
import utils

class ParseOSM:
    # used for parsing overpass response int geojson format. Parser includes simple check if closed way is linear ring
    # or polygon based on (https://wiki.openstreetmap.org/wiki/Overpass_turbo/Polygon_Features). It set
    POLY_KEYS = utils.get_area_tags()

    def __init__(self, osm_json):

        self.geojson = ParseOSM._get_collection(osm_json['elements'])

    @property
    def gpd(self):
        features = self.geojson

        return geopandas.GeoDataFrame.from_features(features, crs={'init':'epsg:3857'})

    @staticmethod
    def _get_collection(elements):
        """Parse overpass json into geojson - multipolygon is not implemented"""
        features = []
        for element in elements:
            if element.get('tags') is not None:
                if element.get('type') == 'node':
                    geom = geojson.Point(coordinates=[element['lon'], element['lat']])
                    features.append(geojson.Feature(element['id'], geom, element['tags']))
                elif element.get('type') == 'way' and (element.get("nodes")[0] == element.get("nodes")[-1]) is False:
                    features.append(ParseOSM._geojson_feature(element, 'LineString'))
                elif element.get('type') == 'way' and (element.get("nodes")[0] == element.get("nodes")[-1]) is True:
                    if any(ParseOSM._area_check(key, value) for key, value in element.get('tags').items()) is True:
                        # create polygon feature from closed way after passing the test on polygon tags
                        features.append(ParseOSM._geojson_feature(element, 'Polygon'))
                    else:
                        features.append(ParseOSM._geojson_feature(element, 'LineString'))
                else:
                    print(f'problem with {element.get("type")} and id no {element["id"]}')
        return geojson.FeatureCollection(features)

    @staticmethod
    def _get_element_coords(element):
        # extract coords from osm json output
        return [(e.get('lon'), e.get('lat')) for e in element['geometry']]

    @staticmethod
    def _geojson_feature(element, type):
        # create geojson feature based on type
        if type != 'Polygon':
            geom = getattr(geojson, type)(ParseOSM._get_element_coords(element))
        else:
            geom = getattr(geojson, type)([ParseOSM._get_element_coords(element)])
        return geojson.Feature(element['id'], geom, element['tags'])

    @staticmethod
    def _area_check(key, value):
        # check if key and value of input element tags are tags of polygon geometry
        try:
            if ParseOSM.POLY_KEYS[key] == 'all':
                return True
            elif any([value in v for k, v in ParseOSM.POLY_KEYS[key].items() if k == 'not']) is True:
                return False
            elif any([value in v for k, v in ParseOSM.POLY_KEYS[key].items() if k == 'is']) is True:
                return True
            else:
                return False
        except KeyError:
            return False


