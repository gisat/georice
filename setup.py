from setuptools import setup

setup(
    name="HarvestOSM",
    packages=['harvestosm'],
    version="0.1",
    description="Tool for  generating Overpass queries and harvesting data from OpenStreetMap",
    long_description="See README.md",
    author="Michal Opletal",
    author_email="michal.opletal@gisat.cz",
    url="",
    license="",
    keywords=["openstreetmap", "overpass", "wrapper"],
    classifiers=[
        "License ::",
        "Programming Language :: Python :: 3.7",
        "Topic :: Scientific/Engineering :: GIS",
        "Topic :: Utilities",
    ],
    install_requires=["requests>=2.22.0", "geojson>=2.5.0"],
    extras_require={"test": ["unittest"]},
)