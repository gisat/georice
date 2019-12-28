import unittest
from harvestosm.statement import Statement


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
        self.st1 = Statement.Node(self.area1, self.dict1, self.name1)
        self.st2 = Statement.Node(self.area2, self.dict2, self.name2)

    def test_constructors(self):
        # test of basic constructors
        for typ in ['Node', 'Way', 'NWR', 'Rel']:
            res = getattr(Statement, typ).__call__('AREA1', tags={'key1': 'value1'}, name='1')
            self.assertEqual(res._statement, {'1': [typ.lower(), 'AREA1', {'key1': 'value1'}]})

    def test_operations(self):
        # test of arithmetic operations
        for o, s in zip(self.op, self.sign):
            res = getattr(Statement, o).__call__(self.st1, self.st2)
            self.assertEqual(res._operation[res._name], ['1', s, '2'])

    def test_tag_import(self):
        # test for  key-value tags
        for tags in self.tags_list:
            res = Statement.Node(self.area1, tags, self.name1)
            self.assertEqual('node.AREA1["key1"="value1"]["key2"="value2"]->.1;', res.statement)
        # test for only key tags
        for tags in self.tags_list2:
            res = Statement.Node(self.area1, tags, self.name1)
            self.assertEqual('node.AREA1["key1"]->.1;', res.statement)

    def test_print_operation(self):
        print_op = ['(.1;.2;)', '(.1; - .2;)']
        for po, o in zip(print_op, self.op):
            res = getattr(Statement, o).__call__(self.st1, self.st2)
            self.assertEqual(Statement._get_operation(res._name, res._operation[res._name]), po + f'->.{res._name};')
        pass

    def test_union(self):
        res = self.st1.Union(self.st2)
        self.assertEqual(res.statement, f'node.AREA1["key1"="value1"]->.1;node.AREA2["key2"="value2"]->.2;(.1;.2;)->.{res._name};')


if __name__ == '__main__':
    unittest.main()