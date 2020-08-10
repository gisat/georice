from sentinelhub import SHConfig
import os, shutil
import json
import warnings
from rasterio import open as rio_open
from rasterio.merge import merge
from matplotlib.pyplot import imshow


SETTING = {
    "polar": ['VV', 'VH'],
    "orbit_path": ['ASC', 'DES'],
    "nodata": -999,
    "time_range": 3600,
    "output": "",
    "wsf_version": "1.0.0",
    "img_height": 1000,
    "img_width": 1000,
    "resx": 10,
    "resy": 10
}



def set_sh(name, value):
    config = SHConfig()
    setattr(config, name, value)
    print(f'{name} : {value} was set into SHConfig')
    config.save()


def show_sh():
    config = SHConfig()
    print('Actual setting of Sentinel Hub credentials:')
    for key in ['sh_client_id', 'sh_client_secret', 'instance_id']:
        print(f'{key} : {config[key]}')

def load_sh():
    config = SHConfig()
    for credentials in ['sh_client_id', 'sh_client_secret', 'instance_id']:
        if config.__getattribute__(credentials) == '':
            try:
                if credentials.startswith('sh_'):
                    env = credentials
                else:
                    env = 'sh_' + credentials
                setattr(config, credentials, os.environ.__getitem__(env.upper()))
                config.save()
            except KeyError:
                print(f'SentinelHub credential as environmental variable {env.upper()} was not found. '
                      f'Set credential {credentials} manualy')
    return SHConfig()


def show_config():
    config = load_config()
    print('Actual setting of Georice processor:')
    for key, value in config.items():
        print(f'{key} : {value}')
    if not os.path.exists(config['output']):
        warnings.warn(f' Output Folders path "output" in config file have to be set')


def save_config(update):
    """ Method save the configuration file."""
    config = load_config()
    for key, value in update.items():
        if key not in load_config().keys():
            raise Exception(f'Key "{key}" is not defined ind config file')
        else:
            if key == 'output':
                os.makedirs(value, exist_ok=True)
                config.update({key: value})
            else:
                config.update({key: value})

    config_file = os.path.join(os.path.dirname(__file__), 'config.json')
    with open(config_file, 'w') as cfg_file:
        json.dump(config, cfg_file, indent=2)


def load_config():
    config_file = os.path.join(os.path.dirname(__file__), 'config.json')
    if not os.path.isfile(config_file):
        raise IOError('Configuration file does not exist: %s' % os.path.abspath(config_file))
    with open(config_file, 'r') as cfg_file:
        return json.load(cfg_file)


def reset_config():
    config_file = os.path.join(os.path.dirname(__file__), 'config.json')
    if not os.path.isfile(config_file):
        raise IOError('Configuration file does not exist: %s' % os.path.abspath(config_file))
    with open(config_file, 'w') as cfg_file:
        json.dump(SETTING, cfg_file)


def mosaic(images_paths):
    output = images_paths[0].replace('part0-', '')
    files_to_mosaic = [rio_open(path) for path in images_paths]
    mosaic, out_trans = merge(files_to_mosaic)
    out_profile = files_to_mosaic[0].profile.copy()
    out_profile.update({"height": mosaic.shape[1], "width": mosaic.shape[2], "transform": out_trans})
    with rio_open(output, 'w', **out_profile) as dataset:
        dataset.write(mosaic)

    for path, file in zip(images_paths, files_to_mosaic):
        file.close()
        os.remove(path)



class Dir:
    def __init__(self, path):
        self._path = path
        for file in os.scandir(self._path):
            if file.is_dir():
                setattr(self, file.name, Dir(file.path))
            elif file.is_file() and file.name.endswith(('tif', 'tiff')):
                setattr(self, file.name.split('.')[0], Img(file.name.split('.')[0], file.path))

    def __call__(self):
        return [file.name for file in os.scandir(self._path)]

    def delete(self):
        """delete directory and child directory"""
        shutil.rmtree(self._path)

    def file_paths(self):
        return [file.path for file in os.scandir(self._path)]

class Img:
    def __init__(self, name, path):
        self.name = name
        self.path = path

    def plot(self, **kwargs):
        with rio_open(self.path, 'r') as dataset:
            imshow(dataset.read(1), **kwargs)

    def array(self):
        with rio_open(self.path, 'r') as dataset:
            return dataset.read(1)

    def delete(self):
        """delete directory and child directory"""
        shutil.rmtree(self.path)