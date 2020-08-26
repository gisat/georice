#!/usr/bin/env python3

from setuptools import setup, find_packages

def readme():
    with open('README.rst') as f:
        return f.read()

setup(
    name='georice',
    versiom='0.7',
    description='Part of Georice processor responsible acquisition of scenes for given aoi  from Sentinel hub ',
    author='Michal opletal',
    author_email='michal.opletal@gisat.cz',
    long_description=readme(),
    packages=find_packages(),
    install_requires=[
        'numpy>=1.15.1',
        'sentinelhub',
        'rasterio',
        'click',
        'matplotlib',
        'shapely',
        'pyproj',
        'gdal',
        'psutil',
        'numba',
        'scikit-image'],
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