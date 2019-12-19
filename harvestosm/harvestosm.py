from area import Area
from statement import Statement
from query import Query
from overpass import Overpass
from parse import Parse
import geopandas
import shapely.geometry
import geojson


# pre operace
file = '/Users/opletalm/Documents/Michal/GISAT/PROJECTS/CROWDVAL/TEST_FILES/convex.geojson'
geo = geopandas.read_file(file)
shape = geo.loc[0].geometry

area=Area.from_shape(shape)
s=Statement.NWR(area, tags='highway')
q=Query(s)
o=Overpass(q.query)
print(q.query)
res = o.get_from_overpass
p=Parse(res.json())

# with open('_response.geojson', 'w') as f:
#     geojson.dump(p.geojson,f)
#
#


