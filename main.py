from georice import Georice


# export SH_CLIENT_ID='e41c5e66-d86b-49ac-90c2-be620fd09fd4'
# export SH_CLIENT_SECRET='[J*kkV/zYBJ-ZJcOh07jb+($6Apk,ddmj>Zjs%_X'
# export SH_INSTANCE_ID='c99541e0-93ff-44ab-a555-f557ea30610d'



# connection to Sentinel Hub

client_id = 'e41c5e66-d86b-49ac-90c2-be620fd09fd4'
client_secret = '[J*kkV/zYBJ-ZJcOh07jb+($6Apk,ddmj>Zjs%_X'
instance = 'c99541e0-93ff-44ab-a555-f557ea30610d'

sh_credentials = dict(sh_client_id='e41c5e66-d86b-49ac-90c2-be620fd09fd4',
                      sh_client_secret='[J*kkV/zYBJ-ZJcOh07jb+($6Apk,ddmj>Zjs%_X',
                      instance_id='c99541e0-93ff-44ab-a555-f557ea30610d')

task = Georice()
task.find_scenes(bbox=[502105.6280661971541122,1184410.5953210531733930,520309.7550376804429106,1197661.2870531221851707],
                 epsg=32648,
                 period=('20180701', '20180804'),
                 tile_name='TEST',
                 nodata=0)
# task.get_scenes()
task.ricemap_get('018', ('20180701', '20180804'), 'DES')

print('')

import georice
