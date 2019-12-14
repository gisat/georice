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
        last = self._statements._name

        return f'[out:{self.format_output}][timeout:{self.timeout}];\n{self._statements.statement}\n.{last} out {self.out};'

