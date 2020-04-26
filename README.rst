*****************
GeoRice processor
*****************

*(pre version of text)*

Description
###########

Georice processor creates classified maps of the presence of rice fields based on Sentinel 1A and Sentinel 1B imagery.
Sentinel 1 scenes are acquired from `Sentinel-hub <https://www.sentinel-hub.com/>`_. Processor can not be used without
specifying  of Sentinel hub credentials:

* client_id
* client_secret
* instance_id

*Install*

`` $ git clone https://github.com/gisat/georice.git ``
`` $ cd georice ``
`` $ python setup.py develop ``

Processor can be access as a command line interface or as a python package.

**Command line interface**

Processor can be access via command: ``$ georice``

Base subcommands are:

:config: Configuration of georice configuration file.
:imagery: Download Sentinel 1A/1B scenes from Sentinel Hub.
:ricemap: Generate rice map from Sentinel imagery.
:sentinel: Configuration of Sentinel Hub credentials.

*Setting of Sentinel Hub credentials*

| ``$ georice sentinel client_id <your clinet_id>``
| ``$ georice sentinel client_secret  <your client_secret >``
| ``$ georice sentinel instance_id  <instance_id >``

Credential are save into sentinel-hub config file that is internal part of `Sentinel-hub python package <https://github.com/sentinel-hub/sentinelhub-py>`_.
In any other use last used credentials are used and can not be set again.

*Setting of georice processor*

| In the base, two folders 'scn_output'  and 'rice_output'  have to be specified in georice config berofer usage of processor. The folder 'scn_output' is used as a temporal storage of Sentinel 1 scenes. Resulting rice maps are saved into folder 'rice_output'.
| ``$ georice config set scn_output <folder path>``
| ``$ georice config set rice_output <folder path>``

*Getting of Sentinel 1 scenes*

| Sentinel 1 scenes are obtained via command ``imagery``. It is necessary to specified AOI. AOI can be provided as BBOX or path to geofile that can be open by geopandas library via options:
| ``-b, --bbox``
| ``-g, --geopath``
| Epsg code of AOI coordinate system
| ``-e, --epsg``
| Period in the format starting date, ending date and date format is YYYYMMDD
| ``-p, --period``
| Last is a tile name
| ``-n, --name``

*Getting of rice map*

Classification script can be accessed via command ``ricemap``. To generate rice map it is necessary to set orbit number,
starting and ending date and orbit direction (default is descending path). Command ``ricemap`` has a option ``-a, --all``
that aromatically generate rice maps for each combination of orbir number and orbit path and for longest time period

Specific rice map can be obtained via subcommand ``get`` and modified by setting of several additional options.
More info via option ``--help``



