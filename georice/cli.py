#!/usr/bin/env python

import click
from sentinelhub import SHConfig
import json
import os
import subprocess

from georice.utils import set_sh, load_config


@click.group()
@click.version_option()
def main():
    """
    Georie - generation of classified rice map
    "no_data":0, "rice":1, "urban_tree":2, "water":3, "other":4
    """
    pass


@main.group('sentinel', invoke_without_command=True)
@click.option('--show', '-s', 'show', is_flag=True,
              help='Show actual Sentinel-hub credentials (client_id, client_secret, instance_id)')
def sentinel(show):
    """Configuration of Sentinel Hub credentials"""
    if show:
        config = SHConfig()
        click.echo(f"Actual configuration of Sentinel hub config file:\n"
                   f"client_id:\t {config['sh_client_id']}\n"
                   f"client_secret:\t {config['sh_client_secret']}\n"
                   f"instance_id:\t {config['instance_id']}\n")


@sentinel.command('client_id')
@click.argument('value')
def client(value):
    """Set Sentinel hub client id"""
    set_sh('sh_client_id', value)
    click.echo(f'Client id: {value} was set')


@sentinel.command('client_secret')
@click.argument('value')
def client(value):
    """Set Sentinel hub client secret"""
    set_sh('sh_client_secret', value)
    click.echo(f'Client secret: {value} was set')


@sentinel.command('instance_id')
@click.argument('value')
def client(value):
    """Set Sentinel hub instance id"""
    set_sh('instance_id', value)
    click.echo(f'Instance id: {value} was set')


@main.group('config', invoke_without_command=True)
@click.option('--show', '-s', 'show', is_flag=True,
              help='Show actual setting georice config file')
def config(show):
    """Configuration of georice configuration file"""
    if show:
        config_rice = load_config()
        click.echo('Actual setting of georice is:')
        for k, v in config_rice.items():
            click.echo(f'{k} : {v}')


@config.command('set')
@click.argument('key')
@click.argument('value')
def set_config(key, value):
    """Save selected parameters of georice config file"""
    config_file = os.path.join(os.path.dirname(__file__), 'config.json')
    config = load_config()
    config.update({key: type(config[key])(value)})
    with open(config_file, 'w') as cfg_file:
        json.dump(config, cfg_file, indent=2)


@main.group(name="imagery", invoke_without_command=True)
@click.option('--bbox', '-b', 'bbox', type=float, required=False, nargs=4, help='AOI bbox as minx miny maxx maxy')
@click.option('--geopath', '-g', 'geopath', default='', required=False, type=str,
              help='Path to geofile with AOI. Geofile have to be opened via geopandas')
@click.option('--epsg', '-e','epsg', type=str, default=None, required=False,
              help='Epsg code of bbox projection')
@click.option('--period', '-p', 'period', type=(str, str), default=None, required=True,
              help='Time period in format YYYYMMDD. e.g. 20180101 20180101')
@click.option('--name', '-n', 'name', type=str, default='Tile', required=False, help='Tile name')
@click.option('--output', '-o', 'output', type=str, default=None, required=False,
              help='Path to output folder. If not set, path saved to config file is used. To see actual path use'
                   'command --info ')

def imagery(bbox, geopath, epsg, period, name, output):
    """Download Sentinel 1A/1B scenes from Sentinel Hub"""
    from .imagery import GetSentinel
    import geopandas

    if len(bbox) == 0 and len(geopath) == 0:
        click.echo('Command aborted. Is required to provide AOI as bbox or path to geofile')
        quit()
    elif len(bbox) == 0:
        task = GetSentinel()
        geofile = geopandas.read_file(geopath)
        task.search(bbox=geofile, epsg=epsg, period=period, tile_name=name)
        click.echo(f'For given parameters: {len(task._scenes)} scenes was found\n')
    elif len(geopath) == 0:
        task = GetSentinel()
        task.search(bbox=bbox, epsg=epsg, period=period, tile_name=name)
        click.echo(f'For given parameters: {len(task._scenes)} scenes were found')

    if len(task._scenes) > 0:
        if output is None:
            task.dump()
        else:
            task.dump(output)
        click.echo(f'Scenes were downloaded in folder {task.setting["rice_output"]}')


@main.group('ricemap', invoke_without_command=True)
@click.option('--all', '-a', 'a', is_flag=True, required=False,
              help='Generate rice maps for all combinations of orbit number, '
                   'direction a period found at scene directory')
def ricemap(a):
    """Generate rice map from Sentinel imagery"""
    if a:
        config_rice = load_config()
        period, orb_num, orb_path = set(), set(), set()
        with os.scandir(config_rice['scn_output']) as files:
            for file in files:
                if file.is_file():
                    parsed = file.name.split('_')
                    period.add(parsed[5])
                    orb_num.add(parsed[4])
                    orb_path.add(parsed[3])
        for orbit in orb_path:
            for num in orb_num:
                command = ['ricemap.py', config_rice['scn_output'], num, min(period), max(period),
                           config_rice['rice_output'], '-d', orbit]
                subprocess.run(' '.join(command), shell=True)
                click.echo(f'Ricemap for orbit path/orbit number/period: {orbit}/{num}/{min(period)}/{max(period)} '
                           f'saved at folder: {config_rice["rice_output"]}')

@ricemap.command('get')
@click.argument('orbit_number')
@click.argument('starting_date')
@click.argument('ending_date')
@click.option('--direction', '-d', 'direct', default='DES', required=False, type=str,
              help='Orbit direction. default DES, velues (ASC / DES)')
@click.option('--intermediate', '-i', 'inter', is_flag=True, required=False,
              help='write intermediate products (min/max/mean/max_increase)')
@click.option('-lzw', 'lzw', is_flag=True, required=False,
              help='write output tiff products using LZW compression instead of DEFLATE (compatibility with ENVI/IDL)')
@click.option('--mask', '-m', 'mask', is_flag=True, required=False,
              help='generate and write rice, trees, water, other and nodata masks')
@click.option('--noreproject', '-nr', 'nr', is_flag=True, required=False,
              help='diable automatic reprojection to EPSG:4326')
def get(orbit_number, starting_date, ending_date, direct, inter, lzw, mask, nr):
    """
    Set ricemap commands.
    NOTE: starting_date / ending_date => YYYYMMDD, inclusive
    """
    config_rice = load_config()
    command = ['ricemap.py', config_rice['scn_output'], orbit_number, starting_date, ending_date,
               config_rice['rice_output']]
    if direct:
        command.append('-d ' + direct)
    if inter:
        command.append('-i')
    if lzw:
        command.append('-lzw')
    if mask:
        command.append('-m')
    if nr:
        command.append('-nr')
    subprocess.run(' '.join(command), shell=True)
    click.echo(f'Rice map saved into folder: {config_rice["rice_output"]}')
