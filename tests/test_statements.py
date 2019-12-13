import unittest
from unittest.mock import Mock
from statement import Statement

class TestStatement(unittest.TestCase):

    def setUp(self):
        self.st1 = Statement.Node('AREA1', {'key1': 'value1'}, '1')
        self.st2 = Statement.Way('AREA2', {'key2': 'value2'}, '2')

    def test_Node(self):
        res = Statement.Node('AREA1', {'key1': 'value1'}, '1')



if __name__ == '__main__':
    unittest.main()