import unittest
from harvestosm.statement import Statement
from shapely import geometry


class TestStatement(unittest.TestCase):

    def setUp(self):
        self.op = ['__add__', '__sub__']
        self.sign = ['+', '-', '.']
        self.area1 = 'AREA1'
        self.area2 = 'AREA2'
        self.name1 = '1'
        self.name2 = '2'
        self.dict1 = {'key1': 'value1'}
        self.dict2 = {'key2': 'value2'}
        self.tags_list = [{**self.dict1, **self.dict2}, 'key1=value1,key2=value2', ['key1=value1', 'key2=value2']]
        self.tags_list2 = ['key1', {'key1': None}, ['key1']]
        self.st1 = Statement.Node(area=self.area1, tags=self.dict1, name=self.name1)
        self.st2 = Statement.Node(area=self.area2, tags=self.dict2, name=self.name2)

    def test_constructors(self):
        # test of basic constructors
        for typ in ['Node', 'Way', 'NWR', 'Rel']:
            res = getattr(Statement, typ).__call__(area='AREA1', tags={'key1': 'value1'}, name='1')
            self.assertEqual(res._statement, {'1': [typ.lower(), 'AREA1', {'key1': 'value1'}]})
        # test for area input
        res = Statement.Node(shape=geometry.Point(1.0, 0.0))
        self.assertEqual(res.statement, f'node(poly: "0.0 1.0")->.{res._statement[res._name][1]};'
                                         f'node.{res._statement[res._name][1]}->.{res._name};')
        res = Statement.Node(coords=[(1.0, 0.0)])
        self.assertEqual(res.statement, f'node(poly: "(0.0, 1.0)")->.{res._statement[res._name][1]};'
                                        f'node.{res._statement[res._name][1]}->.{res._name};')
        res = Statement.Node(bbox=(0.0, 0.0, 1.0, 1.0))
        self.assertEqual(res.statement, f'node(0.0,0.0,1.0,1.0)->.{res._statement[res._name][1]};'
                                        f'node.{res._statement[res._name][1]}->.{res._name};')

    def test_operations(self):
        # test of arithmetic operations
        for o, s in zip(self.op, self.sign):
            res = getattr(Statement, o).__call__(self.st1, self.st2)
            self.assertEqual(res._operation[res._name], ['1', s, '2'])

    def test_tag_import(self):
        # test for  key-value tags
        for tags in self.tags_list:
            res = Statement.Node(area=self.area1, tags=tags, name=self.name1)
            self.assertEqual('node.AREA1["key1"="value1"]["key2"="value2"]->.1;', res.statement)
        # test for only key tags
        for tags in self.tags_list2:
            res = Statement.Node(area=self.area1, tags=tags, name=self.name1)
            self.assertEqual('node.AREA1["key1"]->.1;', res.statement)

    def test_print_operation(self):
        print_op = ['(.1;.2;)', '(.1; - .2;)']
        for po, o in zip(print_op, self.op):
            res = getattr(Statement, o).__call__(self.st1, self.st2)
            self.assertEqual(Statement._get_operation(res._name, res._operation[res._name]), po + f'->.{res._name};')
        pass

    def test_union(self):
        res = self.st1.union(self.st2)
        self.assertEqual(res.statement, f'node.AREA1["key1"="value1"]->.1;node.AREA2["key2"="value2"]->.2;(.1;.2;)->.'
                                        f'{res._name};')

    def test_difference(self):
        res = self.st1.difference(self.st2)
        self.assertEqual(res.statement, f'node.AREA1["key1"="value1"]->.1;node.AREA2["key2"="value2"]->.2;'
                                        f'(.1; - .2;)->.{res._name};')

    def test_intersection(self):
        res = self.st1.intersection(self.st2, 'node')
        self.assertEqual(res.statement, f'node.AREA1["key1"="value1"]->.1;node.AREA2["key2"="value2"]->.2;node.1.2->.'
                                        f'{res._name};')

if __name__ == '__main__':
    unittest.main()