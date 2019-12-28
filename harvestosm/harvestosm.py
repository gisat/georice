from harvestosm.area import Area
from harvestosm.statement import Statement
from harvestosm.query import Query
from harvestosm.overpass import Overpass
from harvestosm.parseosm import ParseOSM
import geopandas


# pre operace
file = '/Users/opletalm/Documents/Michal/GISAT/PROJECTS/CROWDVAL/TEST_FILES/convex.geojson'
geo = geopandas.read_file(file)

shape = geo.loc[0].geometry
area=Area.from_shape(shape)
s=Statement.Way(area, tags='highway=footway').recurse('>').Intersecton(Statement.Way(area, tags='highway').recurse('>'),'node')
print(s)

# q=Query(s)
# o=Overpass(q.query)
# print(q.query)
# res = o.get_from_overpass
# p=ParseOSM(res.json())

