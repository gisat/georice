import collections
import utils
import itertools
from area import Area

class Statement:
    """
    Class Statement represent single Overpass query statement i.e. node.area["key"="value"]->.Statement
    Statements area constructed by constructors Node and Way (nvr and rel are not fully supported)
    Constructor inputs:
    area - Area object viz documentation to Area, string with coords via Overpass, id of element and string represented named statement
    tags (optional) - dict, string or list of strings. If not provided, area query is constructed
                      e.g. way(50.6,7.0,50.8,7.3)->.area_query
    name (optional) - If provided, used for connecting of specific statements e.g.
                      area=Statement.Way('(50.6,7.0,50.8,7.3)',name=area_query)
                      st1 =Statement.Way(area,"highway=path")
                      Result:
                      way(50.6,7.0,50.8,7.3)->.area_query;
                      way.area_query["highway"="path"]->.ABCDE;
                      If it is not provided, unique identification is added.

    Suported operation with Statements
    Union:
    by '+' s = st1 + st2 => Overpass: (st1; st2;);
    by '|' s = st1 | st2 => Overpass: (st1; st2;);
    Difference:
    by '-' s = st1 - st2 => Overpass: (st1; -st2;);
    Attention difference as adding of negative statement s = -st1 + st2 is not supported in this version
    Intersection:
    by '.' s = st1 . st2 => Overpass: (st1.st2);
    by '&' s = st1 & st2 => Overpass: (st1.st2);
    Attention intersection is provided at the same type of statements i.e. node, way...
    Equal:
    by '==' st1 == st2 is True if all attributes are equal

    Methods
    Recurse:
    Represent Overpass recurse methods
    input: recurse - string of recurse sign e.g. st1.recurse('>') => Overpass (st1; >;);
    """
    _operation = collections.OrderedDict()
    _named_areas = dict()
    _containers = ['_named_areas','_statement','_operation']
    _count = 0

    def __init__(self, name, statement, operation=_operation, named_area=_named_areas):
        self._name = name
        self._statement = statement
        self._operation = operation
        self._named_areas = named_area
        self._length = sum([self.__getattribute__(x).__len__() for x in Statement._containers])
        self._chain = (y for x in self._containers for y in self.__getattribute__(x).items())

    @classmethod
    def Node(cls, area, tags=None, name=None):
       return Statement._constructor('node', area, tags, name)

    @classmethod
    def Way(cls, area, tags=None, name=None):
        return Statement._constructor('way', area, tags, name)

    @classmethod
    def NWR(cls, area, tags=None, name=None):
        return Statement._constructor('nwr', area, tags, name)

    @classmethod
    def Rel(cls, area, tags=None, name=None):
        return Statement._constructor('rel', area, tags, name)

    @classmethod
    def _constructor(cls, type, area, tags=None, name=None):
        if name is None: name = utils.random_name()
        if isinstance(area, Statement):
            return cls(name, {name: [type , area._name, tags]}, named_area=area._statement)
        else:
            statement = {name: [type, area, tags]}
            return cls(name, statement)

    #  definitions of operations over the Statement object
    def __add__(self, other):
        name = utils.random_name()
        named_area = {**self._named_areas, **other._named_areas}
        statement = {**self._statement, **other._statement}
        operation = Statement._make_opperation(self, other, name, '+')
        return Statement(name, statement, operation, named_area)

    def __or__(self, other):
        return Statement.__add__(self,other)

    def __sub__(self, other):
        name = utils.random_name()
        named_area = {**self._named_areas, **other._named_areas}
        statement = {**self._statement, **other._statement}
        operation = Statement._make_opperation(self, other, name, '-')
        return Statement(name, statement, operation, named_area)

    def __mul__(self, other):
        name = utils.random_name()
        named_area = {**self._named_areas, **other._named_areas}
        statement = {**self._statement, **other._statement}
        operation = Statement._make_opperation(self, other, name, '.')
        return Statement(name, statement, operation, named_area)

    def __and__(self, other):
        return Statement.__mul__(self, other)

    def __neg__(self):
        print('Standalone negative Statement "(-st)".\n Statemens can by substract only from other statement. Example:\n'
              'st1 = Statement.Way(area, "highway") => Overpass: node.area["highway"]->.st1\n'
              'st2 = Statement.Way(area,"highway=path") => Overpass: node.area["highway"="path"]->.st2 '
              's=st1-st2 => Overpass: (st1;- st2;);')
        quit()

    def __eq__(self, other):
        if all([self.__getattribute__(a) == other.__getattribute__(a) for a in self._containers]):
            return True
        else:
            return False

    def __iter__(self):
        return self

    def __next__(self):
        if Statement._count >= self._length:
            Statement._count = 0
            self._chain = (y for x in self._containers for y in self.__getattribute__(x).items())
            raise StopIteration
        Statement._count += 1
        return next(self._chain)

    @property
    def statement(self):
        return '\n'.join(self._get_statements(name,statement) for name, statement in iter(self))

    # methods
    def recurse(self, sign):
        name = utils.random_name()
        statement = self._statement
        operation = self._operation.copy()
        operation.update({name: [self._name, sign, None]})
        return Statement(name, statement, operation)

    # static function
    def _make_opperation(self, other, name, sign):
        operation = self._operation.copy()
        operation.update(other._operation)
        operation.update({name:[self._name, sign,other._name]})
        return operation

    @staticmethod
    def _get_statements(name,statement):
        area = Statement._get_area(statement[1])
        tags = ''.join(Statement._print_tag(statement[2]))

        return f'{statement[0]}{area}{tags}->.{name};'

    @staticmethod
    def _get_area(area):
        if isinstance(area, Area):
            return f'{area.__getattribute__(area.out)}'
        elif isinstance(area, str):
            return f'.{area}'

    @staticmethod
    def _print_operation(name,oper):
        if oper[1] == '+':
            return f'(.{oper[0]};.{oper[2]};)->.{name};'
        elif oper[1] == '-':
            return f'(.{oper[0]}; - .{oper[2]};)->.{name};'
        elif oper[1] in ['>', '>>', '<', '<<']:
            return f'(.{oper[0]}; {oper[1]};)->.{name};'
        elif oper[1] == '.':
            print('intersection is not supported in this version')
            quit()

    @staticmethod
    def _print_tag(tags):
        s = ''
        if isinstance(tags, dict):
            for key, value in tags.items():
                if value is None:
                    s += f'["{key}"]'
                else:
                    s += f'["{key}"="{value}"]'
        elif isinstance(tags, str):
            for tag in tags.split(','):
                s += f'[{tag}]'
        elif isinstance(tags, list):
            for tag in tags:
                s += f'[{tag}]'
        return s

