from harvestosm.area import Area
from harvestosm.statement import Statement
from harvestosm.query import Query
from harvestosm.overpass import Overpass
from harvestosm.parseosm import ParseOSM


class Harvestosm:

    @staticmethod
    def get_geojson(statement):
        """Return geojson from Overpass api based on input statement"""
        query = Query(statement).query
        resp = Overpass(query)
        return ParseOSM(resp.get_from_overpass.json()).geojson

