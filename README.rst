*****************
GeoRice processor
*****************

*(pre version of text)*

Description
###########

Georice processor creates classified maps of the presence of rice fields based on Sentinel 1A and Sentinel 1B imagery.
Classification script was creted by CNES. Sentinel 1 scenes are acquired from
`Sentinel-hub <https://www.sentinel-hub.com/>`_. Processor can not be used without
specifying  of Sentinel hub credentials:

* client_id
* client_secret
* instance_id

Rice map generation consisting of three steps. Acquisition of orthorectified and Gamma 0 Backscattered scenes from
SentinelHub, applying of SAR multi-temporal speckle filter developed by CNES. This step is optional. To use a filtering
step require instal OTB module including SARMultiTempFiltering (http://tully.ups-tlse.fr/koleckt/georice/tree/master/filtering).
The last step is generation of classified rice map itself.

Georice processor can be installed as a pure python package without installing filtering module. Or as dockerized application
that include OTB module with filtering.

| **Docerized app**
| Docker image can be built based on Dockerfile that located in this repository.

| *EuroDataCube version*
| ``docker run -it -p 5000:5000 eurodatacube/georice``

| Command will invoke Jupyter notebook and will be navigated into folder georice/jupyter/ with  notebook main.ipynb with a preprepared example of a processor usage

| **Package installation**

| `` $ git clone https://github.com/gisat/georice.git ``
| `` $ cd georice ``
| `` $ python setup.py develop ``

