import unittest
from unittest.mock import Mock
from statement import Statement

class TestStatement(unittest.TestCase):

    def setUp(self):
        self.st1 = Statement.Node('AREA1', {'key1': 'value1'}, '1')
        self.st2 = Statement.Node('AREA2', {'key2': 'value2'}, '2')
        self.op = ['__add__', '__sub__', '__mul__']
        self.sign = ['+', '-', '.']

    def test_constructors(self):
        # test of basic constructors
        for typ in ['Node', 'Way', 'NWR', 'Rel']:
            res = getattr(Statement, typ).__call__('AREA1', tags={'key1': 'value1'}, name='1')
            self.assertEqual(res._statement, {'1': [typ.lower(), 'AREA1', {'key1': 'value1'}]})

    def test_operations(self):
        # test of arithmetic operations
        for o, s in zip(self.op,self.sign):
            res = getattr(Statement, o).__call__(self.st1, self.st2)
            self.assertEqual(res._operation[res._name], ['1', s, '2'])

    def test_print_operation(self):
        # print_op = ['(.1;.2;)','(.1; - .2;)']
        # for po, o in zip(print_op, self.op):
        #     res = getattr(Statement, o).__call__(self.st1, self.st2)
        #     st =
        #     self.assertEqual(Statement._get_operation(res._name, res._operation[res._name]), po + f'->.{res._name}')
        pass










if __name__ == '__main__':
    unittest.main()