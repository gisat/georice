#!/usr/bin/env python3

from setuptools import setup, find_packages

def readme():
    with open('README.rst') as f:
        return f.read()

setup(
    name='georice',
    version='0.7',
    description='Part of Georice processor responsible acquisition of scenes for given aoi  from Sentinel hub ',
    author='Michal opletal',
    author_email='michal.opletal@gisat.cz',
    long_description=readme(),
    packages=find_packages(),
    install_requires=[
        'numpy>=1.15.1',
        'sentinelhub==3.0.2',
        'rasterio',
        'click',
        'matplotlib==3.1.3',
        'shapely===1.6.4',
        'pyproj==2.4.1',
        'gdal',
        'psutil==5.7.0',
        'numba==0.48.0',
        'scikit-image==0.16.2'],
    zip_safe=False,
    package_data={"": ["*.json"]},
    include_package_data=True,
    classifiers=[
        'Programming Language :: Python :: 3.6',
    ],
    entry_points='''
        [console_scripts]
        georice=georice.cli:main
    ''',
    scripts=['bin/ricemap.py']
)