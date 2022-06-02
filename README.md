# MDF DALEC GRASS  

## Description 

This is a python package that implements an ecosystem model of grassland carbon (C) biogeochemistry [(DALEC-Grass)](https://www.sciencedirect.com/science/article/abs/pii/S0308521X2030768X). DALEC-Grass is integrated into a model-data fusion (MDF) framework. The MDF framework implements DALEC-Grass probabilistically using location-specific (1) weather and soil data to drive the model and (2) earth observation (EO) data on vegetation leaf area, in order to calibrate the model's parameters, validate model predictions and estimate field-scale C cycling (i.e. C in biomass,roots, soil, C lost to the atmosphere and C removed via grazing/cutting). 

The package handles the sourcing and processing of all the necessary data, and the implementation of the model's code. The functions of this package allow the user to :

1. Collect earth observation (EO) data from the ESA Sentinel-1 (SAR) and Sentinel-2 (multispectral) systems
2. Process the EO data into weekly continuous time-series of grass Leaf Area Index (LAI)  
3. Implement the [(MDF)](https://www.sciencedirect.com/science/article/pii/S0168192321001490) algorithm 


## Requirements 

1. Python 3 
2. A user account on the [Alaska Satellite Facility](https://asf.alaska.edu) archive centre
3. A user account on the [European Centre for Medium-Range Weather Forecasts](https://www.ecmwf.int/en/forecasts/datasets)
4. A user account on [Amazon Web Services](https://digital-geography.com/accessing-landsat-and-sentinel-2-on-amazon-web-services/#.V3Lr1I68EfI)
5. The [Sentinel Application Platform](https://step.esa.int/main/download/snap-download/) should be installed on your system 

## Installation 

To install either "git clone https://github.com/vmyrgiotis/MDF_DALEC_GRASS.git" and then (while inside MDF_DALEC_GRASS) run "python setup.py install" 
--OR-- "pip install git+https://github.com/vmyrgiotis/MDF_DALEC_GRASS.git"

## Tutorial 

> To run the tutorial on a local machine : 

1. install miniconda on the machine (if not installed) : https://docs.conda.io/en/latest/miniconda.html
2. create a conda environment by running : "conda create -n dalec_grass python=3.9.7"
3. activate the dalec_grass conda environment : "conda activate dalec_grass"
4. install some python packages : "pip install matplotlib jupyter pandas numpy spotpy netCDF4 wand itermplot salem convertbng geopandas motionless joblib xarray"
5. clone the github repo : "git clone https://github.com/vmyrgiotis/MDF_DALEC_GRASS.git"
6. navigate to the location of the github repo that you just cloned : "cd /MDF_DALEC_GRASS"
7. run "jupyter notebook" , your default browser starts , click on dalec_grass_tutorial.ipynb 

> To run the tutorial on a remote server:

1. open a 1st terminal tab and : "ssh username@remote.server.address"
2. complete steps 1 to 6 from the running-on-local-machine shown above
3. then : "jupyter notebook --no-browser --port=8008"
4. open a 2nd terminal tab and : "ssh -L 8008:localhost:8008 username@remote.server.address"
5. on the local machine open an internet browser and go to http://localhost:8008/
