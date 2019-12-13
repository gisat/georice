import geopandas
import geojson

class Parse:

    def __init__(self, osm_json):

        self.geojson = Parse.get_collection(osm_json['elements'])

    @property
    def gpd(self):
        features = self.geojson

        return geopandas.GeoDataFrame.from_features(features, crs={'init':'epsg:3857'})

    @staticmethod
    def get_collection(elements):
        """Parse overpass json into geojson - multipolygon is not implemented"""
        features = []
        for element in elements:
            if element.get('tags') is not None:
                if element.get('type') == 'node':
                    geom = geojson.Point(coordinates=[element['lon'], element['lat']])
                    features.append(geojson.Feature(element['id'], geom, element['tags']))
                elif element.get('type') == 'way' and (element.get("nodes")[0] == element.get("nodes")[-1]) is False:
                    coords = [(e.get('lon'), e.get('lat')) for e in element['geometry']]
                    geom = geojson.LineString(coordinates=[coords])
                    features.append(geojson.Feature(element['id'], geom, element['tags']))
                elif element.get('type') == 'way' and (element.get("nodes")[0] == element.get("nodes")[-1]) is True:
                    coords = [(e.get('lon'), e.get('lat')) for e in element['geometry']]
                    geom = geojson.Polygon(coordinates=[coords])
                    features.append(geojson.Feature(element['id'], geom, element['tags']))
        return geojson.FeatureCollection(features)