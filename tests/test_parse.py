import unittest
from unittest.mock import Mock
from parseosm import ParseOSM
import json


def get_test_elements():
    with open('test_elements.json', 'r') as f:
        return json.load(f)


class TestParse(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls._test_elements = get_test_elements()

    def test_gpd(self):
        self.fail()

    def test__get_collection(self):
        for e in ['node', 'line', 'linering', 'polygon']:
            p = ParseOSM._get_collection([self._test_elements[e]])
            self.assertEqual(p.__geo_interface__, self._test_elements[e + '_parsed'])

    def test__area_check(self):
        self.assertEqual(ParseOSM._area_check('building', 'yes'), True)  # Polygon Tag with all accepted values
        self.assertEqual(ParseOSM._area_check('barrier', 'city_wall'), True)  # Polygon when Tag have specific values
        self.assertEqual(ParseOSM._area_check('man_made', 'cutline'), False)  # Polygon when Tag hav not specific values
        self.assertEqual(ParseOSM._area_check('waterway', 'river'), False)  # Tag in area_tags.json but value not
        self.assertEqual(ParseOSM._area_check('waterway', 'river'), False)  # Not a Polygon Tag (not in area_tags.json)


if __name__ == '__main__':
    unittest.main()
