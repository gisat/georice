#!/usr/bin/env python3

from setuptools import setup, find_packages

def readme():
    with open('README.rst') as f:
        return f.read()

setup(
    name='georice',
    version='0.1',
    description='Part of Georice processor responsible acquisition of scenes for given aoi  from Sentinel hub ',
    author='Michal opletal',
    author_email='michal.opletal@gisat.cz',
    long_description=readme(),
    packages=find_packages(),
    install_requires=[
        "sentinelhub",
        "rasterio",
        "numpy",
        "click",
        "geopandas"],
    zip_safe=False,
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