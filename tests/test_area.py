import unittest
from area import Area
from shapely import geometry

class TestStatement(unittest.TestCase):

    def setUp(self):
        self.point_shape = geometry.Point(1.0, 0.0)
        self.point_coords = [(1.0, 0.0)]
        self.line_shape = geometry.LineString([(0, 0), (1, 1)])
        self.line_coords = [(0.0, 0.0), (1.0, 1.0)]
        self.poly_shape = geometry.Polygon([(0.0, 0.0), (1.0, 0.0), (1.0, 1.0), (0.0, 1.0)])
        self.poly_coords = [(0.0, 0.0), (1.0, 0.0), (1.0, 1.0), (0.0, 1.0), (0.0, 0.0)]
        self.bbox_coords = [(0.0, 0.0), (1.0, 0.0), (1.0, 1.0), (0.0, 1.0)]
        self.poly = Area.from_shape(self.poly_shape)

    def test_from_shape(self):
        point = Area.from_shape(self.point_shape)
        line  = Area.from_shape(self.line_shape)
        poly  = Area.from_shape(self.poly_shape)
        self.assertEqual(point.coords, self.point_coords)
        self.assertEqual(line.coords, self.line_coords)
        self.assertEqual(poly.coords, self.poly_coords)

    def test_from_bbox(self):
        bbox = Area.from_bbox((0.0, 0.0, 1.0, 1.0))
        self.assertEqual(bbox.coords, self.bbox_coords)

    def test_poly(self):
        self.assertEqual(self.poly.poly, '(poly: "0.0 0.0 0.0 1.0 1.0 1.0 1.0 0.0 0.0 0.0")')

    def test_points(self):
        self.assertEqual(self.poly.points, '("(0.0, 0.0) (0.0, 1.0) (1.0, 1.0) (1.0, 0.0) (0.0, 0.0)")')

    def test_bbox(self):
        self.assertEqual(self.poly.bbox, '(0.0,0.0,1.0,1.0)')

    def test_tuple_coords(self):
        tup = Area.from_coords(((0.0, 0.0), (1.0, 1.0)))
        self.assertEqual(tup.points, '("(0.0, 0.0) (1.0, 1.0)")')


if __name__ == '__main__':
    unittest.main()