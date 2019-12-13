from area import Area
from statement import Statement
from query import Query
from overpass import Overpass
import geopandas


# # dummy
# shape = geometry.Point(1,0)
# tags1={'key1':'value1'}
# area1=Area.from_shape(shape)
# tags2={'key2':'value2','key4':'value4'}
# area2='AREA2'
# tags3={'key3':'value3'}
# area3='AREA3'
# tags4={'key4':'value4'}
# area4='AREA4'
# st1=Statement.Node(area1, tags1,'1')
# st2=Statement.Way(area2,tags2,'2')
# st3=Statement.Way(area3,tags3,'3')
# st4=Statement.Way(area4,tags4,'4')
#
# s=st1 + st2 - st3
# s=s.recurse('>')
# q=Query(s)
# print(q.query)

# filed test
# pre operace
file = '/Users/opletalm/Documents/Michal/GISAT/PROJECTS/CROWDVAL/TEST_FILES/convex.geojson'
geo  = geopandas.read_file(file)
shape = geo.loc[0].geometry

#  interakce s HarvestOSM lib
area = Area.from_shape(shape)
st0 = Statement.Way(area, name='AREA')
st1 = Statement.Way(st0, tags=['highway'], name='st1')
st2 = Statement.Way(st0, tags=['highway=footway'], name='st2')
area2 = Area.from_bbox([0,0,1,1])
st3 = Statement.Way(area2, name='AREA2')
st4 = Statement.Way(st3, tags=['buildings'])
st5 = Statement.Way(st3, tags=['buildings=hospital'])


q = Query((st1-st2)+(st4-st5))


print(q.query)
# s=Server(q.query)
# r=s.get_from_overpass
# p=Parse(r.json())
# # vytup
# overpas_geojson = p.geojson
# overpas_gpd = p.gpd
#
# print(overpas_geojson)
# with open('/Users/opletalm/Documents/Michal/GISAT/PROJECTS/CROWDVAL/TEST_FILES/output.geojson', 'w') as f:
#     geojson.dump(overpas_geojson,f)
