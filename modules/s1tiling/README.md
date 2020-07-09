S1Tiling is a CNES open-source software.

S1Tiling generates time series of S1 image over S2 tiles (MGRS).

Starting from a configuration file, S1Tiling performs the following processing:
 - download (from peps.cnes.fr) the requested GRD files
 - calibrate the GRD to sigma0
 - remove border in GRD
 - orthorectify over S2 MGRS tiles
 - merge images same orbit/same date
 - apply multichannel speckle filter

It uses:
   - OrfeoToolBox https://www.orfeo-toolbox.org/download/ 
   - a specific OTB remote module for multichannel speckle filtering http://tully.ups-tlse.fr/koleckt/otbsarmultitempfiltering.git 
   - gdal (gdal.org)


