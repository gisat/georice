from area import Area
from statement import Statement


class Query:

    def __init__(self, statements):

        self.timeout = 360
        self.out = 'body geom'
        self._statements = statements
        self.format_output = 'json'


    @property
    def query(self):
        named_areas = '\n'.join((Query._get_statements(name, statement) for name, statement in self._statements._named_areas.items()))
        statements ='\n'.join((Query._get_statements(name,statement) for name, statement in self._statements._statement.items()))
        # 2) print process
        operations ='\n'.join((Query._print_operation(name,operation) for name, operation in self._statements._operation.items()))
        # 3 last named statemen or operation
        last = self._statements._name

        return f'[out:{self.format_output}][timeout:{self.timeout}];\n{named_areas}\n{statements}\n{operations}\n.{last} out {self.out};'

    @staticmethod
    def _get_statements(name,statement):
        area = Query._get_area(statement[1])
        tags = ''.join(Query._print_tag(statement[2]))

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

    # @property
    # def query(self):
    #     block_statements, _ = Query._get_block(self._statements)
    #     # statements ='\n'.join((Query._get_statements(name,statement) for name, statement in self._statements._statement.items()))
    #     # # 2) print process
    #     # operations ='\n'.join((Query._print_operation(name,operation) for name, operation in self._statements._operation.items()))
    #     # # 3 last named statemen or operation
    #     last = self._statements._name
    #
    #     return f'[out:{self.format_output}][timeout:{self.timeout}];\n{block_statements}\n .{last} out {self.out};'
    #
    # @staticmethod
    # def _get_block(block):
    #     st =''
    #     for name, statement in block._statement.items():
    #         if isinstance(statement[1], Statement):
    #             st, name = Query._get_block(statement[1])
    #             statement[1] = name
    #
    #     st += '\n'.join((Query._get_statements(name, statement) for name, statement in block._statement.items()))
    #     st += '\n'.join((Query._print_operation(name, operation) for name, operation in block._operation.items()))
    #     return st, name