# MDF DALEC GRASS package 

## Description 

This is a python package that implements a grassland-specific ecosystem biogeochemistry model [DALEC-Grass](https://www.sciencedirect.com/science/article/abs/pii/S0308521X2030768X) by [assimilating](https://www.sciencedirect.com/science/article/pii/S0168192321001490) satellite-based earth observation (EO) data on vegetation volume. Only two pieces of information are requested from the user : (1) the limits of a grassland field and (2) the time-period to be examined. The package's functions handle the sourcing and processing of all the necessary data and the implementation of the model's code.

The package allows the user to perform the following actions : 

1. Collect earth observation (EO) data from the ESA Sentinel-1 (SAR) and Sentinel-2 (multispectral) systems
2. Process the EO data into time series of grass vegetation 
3. Implement a probabilistic model-data fusion (MDF) algorithm to estimate C dynamics in a grassland field

## Requirements 

1. A user account on the [Alaska Satellite Facility](https://asf.alaska.edu) archive centre 
2. A user account on the [European Centre for Medium-Range Weather Forecasts](https://www.ecmwf.int/en/forecasts/datasets) 
3. A user account on [Amazon Web Services](https://digital-geography.com/accessing-landsat-and-sentinel-2-on-amazon-web-services/#.V3Lr1I68EfI)
4. The [Sentinel Application Platform](https://step.esa.int/main/download/snap-download/) should be installed on your system 

## Package installation 

To install simply run : git clone https://github.com/vmyrgiotis/MDF_DALEC_GRASS.git

