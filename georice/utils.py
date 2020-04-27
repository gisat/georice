from sentinelhub import SHConfig
import os
import json
import warnings

SETTING = {
    "polar": ['VV', 'VH'],
    "orbit_path": ['ASC', 'DES'],
    "nodata": -999,
    "time_range": 3600,
    "scn_output": "",
    "rice_output": "",
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


def show_config():
    config = load_config()
    print('Actual setting of Georice processor:')
    for key, value in config.items():
        print(f'{key} : {value}')
    if not all([os.path.exists(config['scn_output']), os.path.exists(config['rice_output'])]):
        warnings.warn(f'Folders path "scn_output" and "rice_output" in config file have to be set')


def save_config(update):
    """ Method save the configuration file."""
    config = load_config()
    for key, value in update.items():
        if key not in load_config().keys():
            raise Exception(f'Key "{key}" is not defined ind config file')
        else:
            if key in ['scn_output', 'rice_output']:
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
