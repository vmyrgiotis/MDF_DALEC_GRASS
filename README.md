# MDF DALEC GRASS package 

## Description 

This is a python package that implements an  grassland-specific ecosystem biogeochemistry model (DALEC-Grass) by assimilating earth observation (EO) data on vegetation volume (@10-20m resolution). The package can be used to (1) source and process all the necessary model input data (climate and satellite-based leaf area index) and (2) implement the model's code.

The package allows the user to perform the following actions : 

1. Collect earth observation (EO) data from the ESA Sentinel-1 (SAR) and Sentinel-2 (multispectral) systems
2. Process the EO data into time series of grass vegetation 
3. Implement a probabilistic model-data fusion (MDF) algorithm to estimate C dynamics in a grassland field

## Requirements 

Working accounts with :
1. [Alaska Satellite Facility](https://asf.alaska.edu)
2. [European Centre for Medium-Range Weather Forecasts](https://www.ecmwf.int/en/forecasts/datasets)
3. [Amazon Web Services](https://digital-geography.com/accessing-landsat-and-sentinel-2-on-amazon-web-services/#.V3Lr1I68EfI) (if not accessing UK LAI data on datastore)

The [Sentinel Application Platform](https://step.esa.int/main/download/snap-download/) should be installed on your system 

## Package installation 

To isntall the package run "git clone https://github.com/vmyrgiotis/MDF_DALEC_GRASS.git"

## References 

1. [DALEC-Grass development and validation paper](https://www.sciencedirect.com/science/article/abs/pii/S0308521X2030768X)
2. [Paper on inferring field-scale grassland vegetation management (grazing,cutting) by fusing biogeochemical modelling and satellite-based observations](https://www.sciencedirect.com/science/article/pii/S0168192321001490)
