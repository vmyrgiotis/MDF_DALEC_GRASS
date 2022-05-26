from sentinelhub import BBoxSplitter, WebFeatureService, BBox, CRS, DataSource, SHConfig, AwsTileRequest,AwsTile,get_area_info
from sentinelhub import BBoxSplitter, OsmSplitter, TileSplitter, CustomGridSplitter, UtmZoneSplitter, UtmGridSplitter
import pandas as pd 
import numpy as np 
import json
from shapely.geometry import shape, Point
import datetime
import glob
import matplotlib.pyplot as plt
import os 
import subprocess 
import geopandas as gpd
import pandas as pd 
import cdsapi


class IDP() :

	"""
	---------------------------------------------------------------------------------
	> Input Data Production
	The functions in this class perform the following actions : 
	1. Collect S1 data from ASF (ASF_download)
	2. Collect S2 data from AWS (AWS_download)
	3. Colelct meteorological data from ECMWF (ERA5_download)
	4. Process the S1 data into radar VV/VH intensity for the provided grassland field (S1_to_VVVH)
	5. Process the S2 data into LAI for the provided grassland field (S2_to_LAI)
	6. Process and save the data as inputs for the DALEC_Grass model (drivers_creation)
	7. Compile the DALEC-Grass.f90 into a python shared object (.so)

	> User inputs
	jsonloc (str)         : location of geojson file for grassland field
	workingdir (str)      : working directory (will be created if not existing)
	startdate (str)       : first day of simulations (e.g. 2018-01-01)
	enddate (str)         : last day of simulations (e.g. 2020-12-31)
	asf_usrname (str)     : your ASF username 
	asf_pass (str)        : your ASF password 
	snap_graphs_dir (str) : directory containing the ESA SNAP graphs  
	snap_gtp_dir (str)    : directory containing the ESA SNAP gpt app/exe 
	cloudcovmax (in)      : maximum cloud coverage (%) limit for the downloaded S2 images (e.g. 40)
	---------------------------------------------------------------------------------
	""" 

	def __init__(self,jsonloc, workingdir, startdate, enddate, asf_usrname, asf_pass, snap_graphs_dir, snap_gtp_dir, cloudcovmax): 

		self.workingdir      = workingdir
		self.jsonloc         = jsonloc
		self.startdate       = startdate
		self.enddate         = enddate
		self.asf_usrname     = asf_usrname
		self.asf_pass        = asf_pass
		self.snap_graphs_dir = snap_graphs_dir
		self.snap_gtp_dir    = snap_gtp_dir
		self.cloudcovmax     = cloudcovmax

		subprocess.call('mkdir -p %s' %self.workingdir)
	

	def DALEC_Grass_compile():

		os.chdir(self.workingdir)
		subprocess.call('f2py -c DALEC_GRASS.f90 -m DALEC_GRASS ; mv DALEC_GRASS.cpython-38-darwin.so DALEC_GRASS.so',shell=True)		


	def ASF_download(): 

		"""
		> Queries the Alaska Satellite Facility archive for S1 data during/at given period/location and downloads data
		"""
		
		fieldpolygonloc = gpd.read_file(self.jsonloc) 
		poly = str(fieldpolygonloc.geometry.iloc[0])
		
		## edit polygon string to be curl / ASF compatible 
		poly = poly.replace(" ", "+")
		poly = poly.replace("+((", "((")
		poly = poly.replace(",+", ",")
		
		## double check the curl download call 
		document = """#!/bin/bash \n

		POLYGON="%s"

		curl https://api.daac.asf.alaska.edu/services/search/param?intersectsWith=$POLYGON\&start=%sT00:00:00UTC\&end=%sT23:59:59UTC\&platform=S1\&processingLevel=GRD_HD\&output=csv > query.csv

		""" % (poly,startdate,enddate)
			
		subprocess.call('mkdir -p %s/s1_data' %self.workingdir,shell=True)
		os.chdir('%s/s1_data' %self.workingdir)
		file1 = open("query.sh","w") 
		file1.write(document)
		file1.close() 

		subprocess.call('sh query.sh',shell=True)

		S1_data = pd.read_csv("query.csv",sep=',')

		subprocess.call("mkdir -p %s/s1_data/ASF_downloads" %self.workingdir , shell=True)
		os.chdir('%s/s1_data/ASF_downloads' %self.workingdir)

		# download data from ASF archive 
		for i in range(len(S1_data)):
			subprocess.call("wget -c --http-user=\"%s\" --http-password=\"%s\" %s" % (self.asf_usrname,self.asf_pass,S1_data.URL.iloc[i]) , shell=True)


	def S1_to_VVVH() : 

		"""
		> Uses ESA SNAP to produce VV/VH db from S1 data 
		> For the data processing pipeline see Truckenbrodt et al 2019 (https://doi.org/10.3390/data4030093)
		""" 

		fieldpolygonloc = gpd.read_file(self.jsonloc) 
		poly = str(fieldpolygonloc.geometry.iloc[0])
		os.chdir('%s/s1_data/ASF_downloads' %self.workingdir)
		folds = glob.glob('*')

		for i in range(len(folds)):

			document = """\
			<graph id="Graph">
			<version>1.0</version>
			<node id="Read">
				<operator>Read</operator>
				<sources/>
				<parameters class="com.bc.ceres.binding.dom.XppDomElement">
					<file>%s/s1_data/ASF_downloads/%s</file>
					<formatName>SENTINEL-1</formatName>
				</parameters>
			</node>
			<node id="Apply-Orbit-File">
				<operator>Apply-Orbit-File</operator>
				<sources>
					<sourceProduct refid="Read"/>
				</sources>
				<parameters class="com.bc.ceres.binding.dom.XppDomElement">
					<orbitType>Sentinel Precise (Auto Download)</orbitType>
					<polyDegree>3</polyDegree>
					<continueOnFail>false</continueOnFail>
				</parameters>
			</node>
			<node id="Remove-GRD-Border-Noise">
				<operator>Remove-GRD-Border-Noise</operator>
				<sources>
					<sourceProduct refid="Apply-Orbit-File"/>
				</sources>
				<parameters class="com.bc.ceres.binding.dom.XppDomElement">
					<selectedPolarisations>VH,VV</selectedPolarisations>
					<borderLimit>500</borderLimit>
					<trimThreshold>0.5</trimThreshold>
				</parameters>
			</node>
			<node id="ThermalNoiseRemoval">
				<operator>ThermalNoiseRemoval</operator>
				<sources>
					<sourceProduct refid="Remove-GRD-Border-Noise"/>
				</sources>
				<parameters class="com.bc.ceres.binding.dom.XppDomElement">
					<selectedPolarisations>VH,VV</selectedPolarisations>
					<removeThermalNoise>true</removeThermalNoise>
					<reIntroduceThermalNoise>false</reIntroduceThermalNoise>
				</parameters>
			</node>
			<node id="Calibration">
				<operator>Calibration</operator>
				<sources>
					<sourceProduct refid="ThermalNoiseRemoval"/>
				</sources>
				<parameters class="com.bc.ceres.binding.dom.XppDomElement">
					<sourceBands/>
					<auxFile>Product Auxiliary File</auxFile>
					<externalAuxFile/>
					<outputImageInComplex>false</outputImageInComplex>
					<outputImageScaleInDb>false</outputImageScaleInDb>
					<createGammaBand>false</createGammaBand>
					<createBetaBand>false</createBetaBand>
					<selectedPolarisations>VH,VV</selectedPolarisations>
					<outputSigmaBand>true</outputSigmaBand>
					<outputGammaBand>false</outputGammaBand>
					<outputBetaBand>false</outputBetaBand>
				</parameters>
			</node>
			<node id="Multilook">
				<operator>Multilook</operator>
				<sources>
					<sourceProduct refid="Calibration"/>
				</sources>
				<parameters class="com.bc.ceres.binding.dom.XppDomElement">
					<sourceBands>Sigma0_VH,Sigma0_VV</sourceBands>
					<nRgLooks>1</nRgLooks>
					<nAzLooks>1</nAzLooks>
					<outputIntensity>true</outputIntensity>
					<grSquarePixel>true</grSquarePixel>
				</parameters>
			</node>
			<node id="Terrain-Correction">
				<operator>Terrain-Correction</operator>
				<sources>
					<sourceProduct refid="Multilook"/>
				</sources>
				<parameters class="com.bc.ceres.binding.dom.XppDomElement">
					<sourceBands>Sigma0_VH,Sigma0_VV</sourceBands>
					<demName>SRTM 3Sec</demName>
					<externalDEMFile/>
					<externalDEMNoDataValue>0.0</externalDEMNoDataValue>
					<externalDEMApplyEGM>true</externalDEMApplyEGM>
					<demResamplingMethod>BILINEAR_INTERPOLATION</demResamplingMethod>
					<imgResamplingMethod>BILINEAR_INTERPOLATION</imgResamplingMethod>
					<pixelSpacingInMeter>10.0</pixelSpacingInMeter>
					<pixelSpacingInDegree>8.983152841195215E-5</pixelSpacingInDegree>
					<mapProjection>GEOGCS[&quot;WGS84(DD)&quot;, 
			DATUM[&quot;WGS84&quot;, 
				SPHEROID[&quot;WGS84&quot;, 6378137.0, 298.257223563]], 
			PRIMEM[&quot;Greenwich&quot;, 0.0], 
			UNIT[&quot;degree&quot;, 0.017453292519943295], 
			AXIS[&quot;Geodetic longitude&quot;, EAST], 
			AXIS[&quot;Geodetic latitude&quot;, NORTH]]</mapProjection>
					<alignToStandardGrid>false</alignToStandardGrid>
					<standardGridOriginX>0.0</standardGridOriginX>
					<standardGridOriginY>0.0</standardGridOriginY>
					<nodataValueAtSea>true</nodataValueAtSea>
					<saveDEM>false</saveDEM>
					<saveLatLon>false</saveLatLon>
					<saveIncidenceAngleFromEllipsoid>false</saveIncidenceAngleFromEllipsoid>
					<saveLocalIncidenceAngle>false</saveLocalIncidenceAngle>
					<saveProjectedLocalIncidenceAngle>false</saveProjectedLocalIncidenceAngle>
					<saveSelectedSourceBand>true</saveSelectedSourceBand>
					<outputComplex>false</outputComplex>
					<applyRadiometricNormalization>false</applyRadiometricNormalization>
					<saveSigmaNought>false</saveSigmaNought>
					<saveGammaNought>false</saveGammaNought>
					<saveBetaNought>false</saveBetaNought>
					<incidenceAngleForSigma0>Use projected local incidence angle from DEM</incidenceAngleForSigma0>
					<incidenceAngleForGamma0>Use projected local incidence angle from DEM</incidenceAngleForGamma0>
					<auxFile>Latest Auxiliary File</auxFile>
					<externalAuxFile/>
				</parameters>
			</node>
			<node id="Speckle-Filter">
				<operator>Speckle-Filter</operator>
				<sources>
					<sourceProduct refid="Terrain-Correction"/>
				</sources>
				<parameters class="com.bc.ceres.binding.dom.XppDomElement">
					<sourceBands>Sigma0_VH,Sigma0_VV</sourceBands>
					<filter>Lee Sigma</filter>
					<filterSizeX>3</filterSizeX>
					<filterSizeY>3</filterSizeY>
					<dampingFactor>2</dampingFactor>
					<estimateENL>true</estimateENL>
					<enl>1.0</enl>
					<numLooksStr>1</numLooksStr>
					<windowSize>7x7</windowSize>
					<targetWindowSizeStr>3x3</targetWindowSizeStr>
					<sigmaStr>0.9</sigmaStr>
					<anSize>50</anSize>
				</parameters>
			</node>
			<node id="Subset">
				<operator>Subset</operator>
				<sources>
					<sourceProduct refid="Speckle-Filter"/>
				</sources>
				<parameters class="com.bc.ceres.binding.dom.XppDomElement">
					<sourceBands>Sigma0_VH,Sigma0_VV</sourceBands>
					<region>0,0,0,0</region>
					<referenceBand/>
					<geoRegion>%s</geoRegion>
					<subSamplingX>1</subSamplingX>
					<subSamplingY>1</subSamplingY>
					<fullSwath>false</fullSwath>
					<tiePointGridNames/>
					<copyMetadata>true</copyMetadata>
				</parameters>
			</node>
			<node id="Write">
				<operator>Write</operator>
				<sources>
					<sourceProduct refid="Subset"/>
				</sources>
				<parameters class="com.bc.ceres.binding.dom.XppDomElement">
					<file>%sS1_data/ASF_downloads/processed/Subset_%s_Orb_NR_Cal_ML_TC_dB.tif</file>
					<formatName>GeoTIFF</formatName>
				</parameters>
			</node>
			<applicationData id="Presentation">
				<Description/>
				<node id="Read">
					<displayPosition x="37.0" y="134.0"/>
				</node>
				<node id="Apply-Orbit-File">
					<displayPosition x="157.0" y="75.0"/>
				</node>
				<node id="Remove-GRD-Border-Noise">
					<displayPosition x="275.0" y="161.0"/>
				</node>
				<node id="ThermalNoiseRemoval">
					<displayPosition x="475.0" y="90.0"/>
				</node>
				<node id="Calibration">
					<displayPosition x="634.0" y="166.0"/>
				</node>
				<node id="Multilook">
					<displayPosition x="734.0" y="92.0"/>
				</node>
				<node id="Terrain-Correction">
					<displayPosition x="854.0" y="168.0"/>
				</node>
				<node id="Speckle-Filter">
					<displayPosition x="981.0" y="112.0"/>
				</node>
				<node id="Subset">
					<displayPosition x="1101.0" y="136.0"/>
				</node>
				<node id="Write">
					<displayPosition x="1195.0" y="181.0"/>
				</node>
			</applicationData>
			</graph>
			""" %(self.workingdir,folds[i],poly,self.workingdir,folds[i][:-4])
				
			os.chdir(self.snap_graphs_dir)
			file1 = open("S1_to_VVVH.xml","w") 
			file1.write(document)
			file1.close() 

			subprocess.call('%s S1_to_VVVH.xml' %self.snap_gtp_dir , shell=True)



	def AWS_download():
		
		"""
		> Downloads S2 L2A images from AWS bucket 
		> Requires a AWS account, permissions & credentials
		> Downloads 20m data (edit relevant lines for other res)
		[!] 1st 15GB of downloaded data per month are free of charge 
		[!] AWS S2 data download cost = £0.08 per GB 
		[!] 1 image ~ 500MB (for 20m resolution images)
		[!] expect 20-30 images per year for UK locations 
		""" 

		INSTANCE_ID = '' 

		if INSTANCE_ID:
			config = SHConfig()
			config.instance_id = INSTANCE_ID
		else:
			config = None

		subprocess.call('mkdir -p %s/S2_data/ ; mkdir -p %s/S2_data/AWS_downloads' %(self.workingdir,self.workingdir), shell=True)


		with open(self.jsonloc) as f: js = json.load(f)
		for feature in js['features']: polygon = shape(feature['geometry'])
		osm_splitter = OsmSplitter([polygon], CRS.WGS84, zoom_level=8) # Open Street Map Grid
		search_bbox = osm_splitter

		search_time_interval = ('%sT00:00:00' %startdate,'%sT23:59:59' %enddate)

		datainfo = pd.DataFrame(columns=['productIdentifier','tilecode','completionDate'])
		for i in range(len(search_bbox.get_bbox_list())):
			for tile_info in get_area_info(search_bbox.get_bbox_list()[i], search_time_interval, maxcc=cloudcovmax):
				datainfo = datainfo.append({'productIdentifier': tile_info['properties']['productIdentifier'],
											'tilecode' : tile_info['properties']['title'][49:55],
											'completionDate': tile_info['properties']['completionDate'][:10]}, ignore_index=True)

		donetiles = []
		for file in glob.glob("%s/*" %self.s2_data_dir): donetiles.append(file[-6:]) 

		## Exclude done tiles
		datainfo = datainfo.drop_duplicates(subset='productIdentifier')
		datainfo = datainfo[~datainfo.tilecode.isin(donetiles)]
		datainfo.index = np.arange(0,len(datainfo))

		datainfo['datacoveragepct'] = np.nan 
		datainfo['cloudpixelpct'] = np.nan 

		### collect metadata 
		for i in range(len(datainfo)):
			try:
				tile_id = datainfo.productIdentifier[i]
				tile_name, time, aws_index = AwsTile.tile_id_to_tile(tile_id)
				request = AwsTileRequest(
					tile = tile_name,
					time = time,
					aws_index = aws_index,
					bands=[''],
					metafiles = ['tileInfo'],
					data_collection = DataSource.SENTINEL2_L2A)
				infos = request.get_data() 
				datainfo['datacoveragepct'][datainfo.productIdentifier == datainfo.productIdentifier[i]] = infos[0]['dataCoveragePercentage']
				datainfo['cloudpixelpct'][datainfo.productIdentifier == datainfo.productIdentifier[i]] = infos[0]['cloudyPixelPercentage']
			except : pass 

		datainfo = datainfo[datainfo.datacoveragepct > 33]
		datainfo = datainfo[datainfo.cloudpixelpct < cloudcovmax]
		datainfo = datainfo.dropna(subset=['datacoveragepct','datacoveragepct'])
		datainfo.index = np.arange(0,len(datainfo))

		if self.S2_res == 10 : bands_list = ['R10m/B02', 'R10m/B03', 'R10m/B04', 'R10m/B08', 'R10m/AOT', 'R10m/TCI', 'R10m/WVP']
		if self.S2_res == 20 : bands_list = ['R20m/B02', 'R20m/B03', 'R20m/B04', 'R20m/B05', 'R20m/B06', 'R20m/B07', 'R20m/B8A', 'R20m/B11', 'R20m/B12', 'R20m/AOT', 'R20m/SCL', 'R20m/TCI', 'R20m/VIS', 'R20m/WVP']
		if self.S2_res == 60 : bands_list = ['R60m/B01', 'R60m/B02', 'R60m/B03', 'R60m/B04', 'R60m/B05', 'R60m/B06', 'R60m/B07', 'R60m/B8A', 'R60m/B09', 'R60m/B11', 'R60m/B12', 'R60m/AOT', 'R60m/SCL', 'R60m/TCI', 'R60m/WVP']

		### Donwload complete folders
		for i in range(len(set(datainfo.tilecode))):
			datainfosub = datainfo[datainfo.tilecode == list(set(datainfo.tilecode))[i]]
			print (str(list(set(datainfo.tilecode))[i]))
			for ii in range(len(datainfosub)):
				try:
					tile_id = datainfosub.productIdentifier.iloc[ii]
					tile_name, time, aws_index = AwsTile.tile_id_to_tile(tile_id)
					request = AwsTileRequest(
						tile = tile_name,
						time = time,
						aws_index = aws_index,
						bands = bands_list,
						data_folder = '%s/S2_data/AWS_downloads/' % self.workingdir,
						data_collection = DataSource.SENTINEL2_L2A, 
						safe_format = True)
					request.save_data() 
				except : pass


	def S2_to_LAI() : 

		"""\
		1. Apply ESA SNAP resampling and biophysical calculator to produce LAI data
		2. Reproject to EPSG:4326
		3. Remove cloud pixels from final .tif
		>  Final .tif has _p2 ending attached to its name 
		""" 

		fieldpolygonloc = gpd.read_file(self.jsonloc) 
		poly = str(fieldpolygonloc.geometry.iloc[0])
		os.chdir("%s/AWS_downloads" %s2_data_dir)
		subprocess.call('rm -r processed',shell=True)
		folds = glob.glob('*')

		for i in range(len(folds)):

			document = """\
			<graph id="Graph">
			  <version>1.0</version>
			  <node id="Read">
				<operator>Read</operator>
				<sources/>
				<parameters class="com.bc.ceres.binding.dom.XppDomElement">
				  <file>%s/AWS_downloads/%s/MTD_TL.xml</file>
				</parameters>
			  </node>
			  <node id="BiophysicalOp">
				<operator>BiophysicalOp</operator>
				<sources>
				  <sourceProduct refid="Resample"/>
				</sources>
				<parameters class="com.bc.ceres.binding.dom.XppDomElement">
				  <sensor>S2A</sensor>
				  <computeLAI>true</computeLAI>
				  <computeFapar>false</computeFapar>
				  <computeFcover>false</computeFcover>
				  <computeCab>false</computeCab>
				  <computeCw>false</computeCw>
				</parameters>
			  </node>
			  <node id="Resample">
				<operator>Resample</operator>
				<sources>
				  <sourceProduct refid="Read"/>
				</sources>
				<parameters class="com.bc.ceres.binding.dom.XppDomElement">
				  <referenceBand/>
				  <targetWidth/>
				  <targetHeight/>
				  <targetResolution>40</targetResolution>
				  <upsampling>Nearest</upsampling>
				  <downsampling>Mean</downsampling>
				  <flagDownsampling>First</flagDownsampling>
				  <resamplingPreset/>
				  <bandResamplings/>
				  <resampleOnPyramidLevels>true</resampleOnPyramidLevels>
				</parameters>
			  </node>
			  <node id="Write">
				<operator>Write</operator>
				<sources>
				  <sourceProduct refid="BiophysicalOp"/>
				</sources>
				<parameters class="com.bc.ceres.binding.dom.XppDomElement">
				  <file>%s/AWS_downloads/processed/%s.tif</file>
				  <formatName>GeoTIFF</formatName>
				</parameters>
			  </node>
			  <applicationData id="Presentation">
				<Description/>
				<node id="Read">
						<displayPosition x="37.0" y="134.0"/>
				</node>
				<node id="BiophysicalOp">
				  <displayPosition x="308.0" y="102.0"/>
				</node>
				<node id="Resample">
				  <displayPosition x="184.0" y="98.0"/>
				</node>
				<node id="Write">
						<displayPosition x="455.0" y="135.0"/>
				</node>
			  </applicationData>
			</graph>
			""" %(s2_data_dir,folds[i],s2_data_dir,folds[i][:-4])
				
			os.chdir(snap_graphs_dir)
			file1 = open("S2_to_LAI.xml","w") 
			file1.write(document)
			file1.close() 

			subprocess.call('%s S2_to_LAI.xml' %self.snap_gtp_dir , shell=True)
			subprocess.call('rm -R %s/var/cache/s2tbx/l2a-reader/8.0.0/*' %self.snap_graphs_dir[:-6],shell=True)

		## Reproject LAI tiffs and remove cloud pixels 
		os.chdir("%s/AWS_downloads/processed" %self.s2_data_dir)
		folders = []
		for file in glob.glob("*.tif"): folders.append(file)
		folders.sort()

		for y in range(len(folders)):
			subprocess.call('gdalwarp %s %s_p1.tif -s_srs EPSG:32630 -t_srs EPSG:4326' %(folders[y],folders[y][:-4]),shell=True)
			subprocess.call('rm %s' %folders[y],shell=True)
			subprocess.call('gdal_calc.py -A %s_p1.tif --A_band=1 -B %s_p1.tif --B_band=2 --outfile=%s_p2.tif --NoDataValue=0 --calc="A*(B==0)"' %(folders[y][:-4],folders[y][:-4],folders[y][:-4]),shell=True) 
			subprocess.call('rm *s_p1.tif',shell=True)


			
	def ERA5_download() : 

		"""
		> Downloads met data (T, dewpoint T, surface pressure, surface solar radiation) from ECMWF for requested time period
		""" 

		fieldpolygonloc = gpd.read_file(self.jsonloc) 

		## upper left , lower right 
		loc_box = "%s,%s,%s,%s," % (float(fieldpolygonloc.geometry.bounds.maxy),
								   float(fieldpolygonloc.geometry.bounds.maxx),
								   float(fieldpolygonloc.geometry.bounds.miny),
								   float(fieldpolygonloc.geometry.bounds.minx),) 

		for i in range(len(years)):

			document = """\
			
	import cdsapi
	c = cdsapi.Client()

	c.retrieve(
		'reanalysis-era5-land',
		{
			'format': 'netcdf',
			'variable': [
				'2m_temperature', '2m_dewpoint_temperature', 'surface_pressure', 'surface_solar_radiation_downwards',
			],
			'year': [
				'%s', 
			],
			'month': [
				'01', '02', '03',
				'04', '05', '06',
				'07', '08', '09',
				'10', '11', '12',
			],
			'day': [
				'01', '02', '03',
				'04', '05', '06',
				'07', '08', '09',
				'10', '11', '12',
				'13', '14', '15',
				'16', '17', '18',
				'19', '20', '21',
				'22', '23', '24',
				'25', '26', '27',
				'28', '29', '30',
				'31',
			],
			'time': [
				'00:00', '01:00', '02:00',
				'03:00', '04:00', '05:00',
				'06:00', '07:00', '08:00',
				'09:00', '10:00', '11:00',
				'12:00', '13:00', '14:00',
				'15:00', '16:00', '17:00',
				'18:00', '19:00', '20:00',
				'21:00', '22:00', '23:00',
			],
			'area': [
				%s
			],
		},
		'ERA5_%s.nc')
			""" %(self.years[i],loc_box,self.years[i])

			os.chdir(self.met_data_dir)
			file1 = open("ERA5_data_download.py","w") 
			file1.write(document)
			file1.close() 

			subprocess.call('python ERA5_data_download.py',shell=True)
			subprocess.call('rm ERA5_data_download.py',shell=True)


	def daylength(dayOfYear, lat):

		"""
		Computes the length of the day (the time between sunrise and
		sunset) given the day of the year and latitude of the location.
		Function uses the Brock model for the computations.
		Forsythe et al., "A model comparison for daylength as a function of latitude and day of year", Ecological Modelling, 1995

		Parameters
		----------
		dayOfYear : int | The day of the year
		lat : float | latitude of the location in degrees | + for north and - for south

		Returns
		-------
		d : float | daylength in hours.
		"""

		latInRad = np.deg2rad(lat)
		declinationOfEarth = 23.45*np.sin(np.deg2rad(360.0*(283.0+dayOfYear)/365.0))
		if -np.tan(latInRad) * np.tan(np.deg2rad(declinationOfEarth)) <= -1.0:
			return 24.0
		elif -np.tan(latInRad) * np.tan(np.deg2rad(declinationOfEarth)) >= 1.0:
			return 0.0
		else:
			hourAngle = np.rad2deg(np.arccos(-np.tan(latInRad) * np.tan(np.deg2rad(declinationOfEarth))))
			return 2.0*hourAngle/15.0



	def drivers_creation() : 

		"""
		Collect the downloaded and processed S1 and S2 data and create inputs for the DALEC-Grass model 
		1. A numpy array of time series on : weekly min/max T, srad, VDP, photoperiod, atm CO2 and LAI reduction
		2. A numpy array of weekly LAI (m2.m-2)
		"""

		fieldpolygonloc = self.jsonloc
		
		### S2 data directory 
		os.chdir("/Users/vm/awsdata/processed")
		folders_S2 = []
		for file in glob.glob("*_p2.tif") : 
			if (file.find('T30UVB') > 0) : folders_S2.append(file)
		folders_S2.sort()

		### Split fields in sub-fields 
		with open(fieldpolygonloc) as f: js = json.load(f)
		for feature in js['features']: polygon = shape(feature['geometry'])
		bbox_splitter = BBoxSplitter([polygon], CRS.WGS84, (5,5))  # bounding box will be split into x-times-x bounding boxes

		### collect S2 LAI data per box 
		S2_DF = pd.DataFrame()
		for y in range(len(folders_S2)) : 
			for i in range(len((bbox_splitter.get_bbox_list()))):
				listofzones_lai = rasterstats.zonal_stats((bbox_splitter.bbox_list[i]).geometry.to_wkt(),folders_S2[y],stats=['mean','std','count'],band=1,nodata=0)
				S2_DF = S2_DF.append({'box': int(i),
									  'date': datetime.datetime.strptime(folders_S2[y][19:27], '%Y%m%d'),
									  'lai': listofzones_lai[0]['mean'],
									  'lai_std': listofzones_lai[0]['std']},ignore_index=True)
		del y

		S2_DF.index = S2_DF.date
		S2_DF = S2_DF.sort_index()

		### S1 SAR data directory (contains only T30UVB tile)
		os.chdir("/Users/vm/ASF_S1_GRD/processed")
		folders_S1 = []
		for file in glob.glob("*.tif") : folders_S1.append(file)
		folders_S1.sort()

		### Collect S1 backscatter data per box/subfield 
		S1_DF = pd.DataFrame()
		for y in range(len(folders_S1)) : 
			for ii in range(len((bbox_splitter.get_bbox_list()))):
				band1 = rasterstats.zonal_stats((bbox_splitter.bbox_list[ii]).geometry.to_wkt(),folders_S1[y],stats=['mean','std'],band=1,nodata=0)
				band2 = rasterstats.zonal_stats((bbox_splitter.bbox_list[ii]).geometry.to_wkt(),folders_S1[y],stats=['mean','std'],band=2,nodata=0)
				S1_DF = S1_DF.append({'box': int(ii),
									  'date': datetime.datetime.strptime(folders_S1[y][24:32], '%Y%m%d'),
									  'band1': band1[0]['mean'],
									  'band1_std': band1[0]['std'],
									  'band2': band2[0]['mean'],
									  'band2_std': band2[0]['std'],},ignore_index=True)
		del y , ii

		S1_DF.index = S1_DF.date
		S1_DF = S1_DF.sort_index()
		S1_DF['bandratio'] = S1_DF.band1 / S1_DF.band2

		### Merge S1 and S2 per box/subfield 
		DF = S1_DF['2017':'2019']
		DF = DF.sort_index()
		DF['lai'] = np.nan
		DF['lai_std'] = np.nan
		S2_DF_v2 = S2_DF[S2_DF.lai>0]
		DF = DF[DF.date.isin(list(set(S2_DF_v2.date)))]
		for ii in range(len(set(DF.date))):
			for b in range(len(set(S2_DF_v2.box))):
				if len(S2_DF_v2[(S2_DF_v2.date==list(set(DF.date))[ii])&(S2_DF_v2.box==list(set(S2_DF_v2.box))[b])]) > 0 :
					DF['lai'][(DF.date==list(set(DF.date))[ii])&(DF.box==list(set(S2_DF_v2.box))[b])] = float(S2_DF_v2.lai[(S2_DF_v2.date==list(set(DF.date))[ii])&(S2_DF_v2.box==list(set(S2_DF_v2.box))[b])])
					DF['lai_std'][(DF.date==list(set(DF.date))[ii])&(DF.box==list(set(S2_DF_v2.box))[b])] = float(S2_DF_v2.lai_std[(S2_DF_v2.date==list(set(DF.date))[ii])&(S2_DF_v2.box==list(set(S2_DF_v2.box))[b])])
		del b , ii

		### Load and process met data
		os.chdir("/Users/vm/Desktop/ERA5")
		folders_met = []
		for file in glob.glob("*.nc"): folders_met.append(file)
		folders_met.sort()
		
		shapefile = gpd.read_file(fieldpolygonloc) 
		shapefile['lat'] = shapefile.geometry.centroid.y.iloc[0]
		shapefile['lon'] = shapefile.geometry.centroid.x.iloc[0]

		met_DF = pd.DataFrame(columns=['date','minT','maxT','srad','vpd','photoperiod','21d_vpd','21d_minT','21d_photoperiod'])

		for ii in [2,3,4]:
			ds = xr.open_dataset(folders_met[ii])
			dsloc = ds.sel(longitude=float(shapefile['lon']), # polygon centroid lon 
						   latitude=float(shapefile['lat']), # polygon centroid lat 
						   method='nearest') 
			df = dsloc.to_dataframe()
			## unit conversion
			df.t2m = df.t2m - 273.15
			# df.mx2t = df.mx2t - 273.15
			# df.mn2t = df.mn2t - 273.15
			df.d2m = df.d2m - 273.15
			## relative humidity (http:/andrew.rsmas.miami.edu/bmcnoldy/Humidity.html)
			df['RH'] = 100*(np.exp((17.625*df.d2m)/(243.04+df.d2m))/np.exp((17.625*df.t2m)/(243.04+df.t2m))) 
			## vapor pressure deficit (http:/cronklab.wikidot.com/calculation-of-vapour-pressure-deficit)
			df['VPD'] = (1-(df.RH/100)) * (610.7*10**(7.5*df.t2m/(237.3+df.t2m)))
			
			df = df.reset_index()
			df.index = pd.date_range('%s-01-01' %folders_met[ii][5:9], periods = len(df),freq='H')

			for t in range(int(len(df)/float(24))):
				met_DF = met_DF.append({'date' : pd.date_range('%s-01-01' %folders_met[ii][5:9], periods = int(len(df)/float(8)),freq='D')[t],
										'minT': (df.t2m.resample('D',label='left').min()).iloc[t],
										'maxT': (df.t2m.resample('D',label='left').max()).iloc[t],
										'srad': (df.ssrd.resample('D',label='left').max()).iloc[t] * 1e-6, # to MJ.m-2.d-1
										'vpd' : (df.VPD.resample('D',label='left').mean()).iloc[t]},ignore_index=True)
			del t 
			
			for x in range(int(len(df)/float(24))):
				met_DF['photoperiod'][(met_DF.date==pd.date_range('%s-01-01' %folders_met[ii][5:9], periods = int(len(df)/float(8)),freq='D')[x])] = DC.daylength(x+1,float(shapefile['lat']))
			del x 
			
			## 21-day rolling average photoperiod - minT - vpd 
			met_DF['21d_vpd'] = met_DF['vpd'].rolling(window=21).mean() 
			met_DF['21d_vpd'] = met_DF['21d_vpd'].fillna(method='bfill')
			met_DF['21d_minT'] = met_DF['minT'].rolling(window=21).mean() + 273.15
			met_DF['21d_minT'] = met_DF['21d_minT'].fillna(method='bfill')
			met_DF['21d_photoperiod'] = met_DF['photoperiod'].rolling(window=21).mean() * 3600 # hrs to sec 
			met_DF['21d_photoperiod'] = met_DF['21d_photoperiod'].fillna(method='bfill')
			
			met_DF.index = met_DF.date
			met_DF['DOY'] = met_DF.index.dayofyear
		del ii
		
		### T, SRAD, VPD, Photoperiod time-series
		weekly_tmax = met_DF.maxT.resample('7D',label='right').mean()[:-1]
		weekly_tmin = met_DF.minT.resample('7D',label='right').mean()[:-1]
		weekly_rad  = met_DF['srad'].resample('7D',label='right').max()[:-1]
		weekly_DOY  = met_DF.DOY.resample('7D',label='right').max()[:-1]
		weekly_21d_vpd = met_DF['21d_vpd'].resample('7D',label='right').mean()[:-1]
		weekly_21d_minT = met_DF['21d_minT'].resample('7D',label='right').mean()[:-1]
		weekly_21d_photoperiod = met_DF['21d_photoperiod'].resample('7D',label='right').mean()[:-1]
		
		### Atmospheric CO2 time-series
		co2 = pd.read_csv("/Users/vm/Dropbox/atm_co2_data.csv")
		co2.index = pd.to_datetime((co2.YYYY*10000+co2.MM*100+co2.DD).apply(str),format='%Y%m%d')
		co2_ppm = co2.ppm.resample('W',label='right').max()
		co2_ppm[co2_ppm<=0] = np.nan ; co2_ppm = co2_ppm.interpolate()
		co2_ppm = co2_ppm["%s-01-01" %(folders_met[2][5:9]) : "%s-12-31" %(folders_met[4][5:9])]

		### Add met info to S1+S2 dataframe
		DF = DF.dropna()
		DF['DOY'] = DF.index.dayofyear
		DF['vpd'] = met_DF.vpd

		### Train Random Forest algorithm using box/subfield data 
		X_train, X_test, y_train, y_test = train_test_split( DF[['band1','band2','DOY','vpd']], DF.lai, test_size=0.2,random_state=0)
		rf = RandomForestRegressor(n_estimators=100) 
		rf.fit(X_train, y_train)
		RF_score = (rf.score(X_test, y_test))
		print(RF_score)

		### Fill S1 dataframe with RF predcited LAI 
		S1_DF = S1_DF['2017':]
		S1_DF['DOY'] = S1_DF.index.dayofyear
		S1_DF = S1_DF.resample('D').median() # daily average cross all boxes
		S1_DF = S1_DF.dropna()
		S1_DF['vpd'] = met_DF.vpd
		S1_DF['rf_LAI'] = np.nan
		S1_DF['rf_LAI'] = rf.predict(S1_DF[['band1','band2','DOY','vpd']])
	 
		## Use mean field VV/VH to RF-predict mean field LAI 
		daily_rfLAI = pd.DataFrame(columns={'emptycol'},index=pd.date_range(start="2017-01-01", end="2019-12-31" ,freq='D'))
		daily_rfLAI['rf_LAI'] = round(S1_DF['rf_LAI'],2)
		daily_rfLAI['rf_LAI'].iloc[0] = 0	
		daily_rfLAI = daily_rfLAI.interpolate('linear') # interpolated RF LAI time series
		lailoss = pd.DataFrame()
		lailoss['loss'] = daily_rfLAI.rf_LAI.diff(periods=1) # day2day difference
		lailoss = round(lailoss.resample('7D',label='right').sum(),4) # grass biomass removed during week
		lailoss.loss[lailoss.loss > 0 ] = 0 # LAI reduction as positive values 
		lailoss.loss = abs(lailoss.loss) # LAI reduction as positive values 
		lailoss = lailoss['2017':'2019']
		lailoss['lai_ini'] = daily_rfLAI.rf_LAI.resample('7D',label='right').first()[:-1]
		lailoss.loss[ (lailoss.loss>=2) & (~lailoss.index.month.isin([1,2,3,10,11,12])) ] = -1 

		# RF predicted LAI 
		np.save(("%s/DALEC_Grass/inputs/lai_obs_%s.npy" %(self.workingdir,Fname)),lailoss.lai_ini) 

		## Create model inputs array 
		met = np.zeros([14,len(weekly_DOY)]) - 9999. # 14 variables - n weeks 
		met[0,:]  = np.array(np.arange(7,len(weekly_tmax)*7+7,7)) # run day 
		met[1,:]  = np.array(weekly_tmin) # min T 
		met[2,:]  = np.array(weekly_tmax) # max T  
		met[3,:]  = np.array(weekly_rad) # solar rad 
		met[4,:]  = np.array(co2_ppm[:-1]) # atm CO2
		met[5,:]  = np.array(weekly_DOY) # DOY 
		met[7,:]  = np.array(lailoss.loss) # LAI reduction 
		met[9,:]  = np.array(weekly_21d_minT) # 21 day avg min T  
		met[10,:] = np.array(weekly_21d_photoperiod) # 21 day avg photoperiod 
		met[11,:] = np.array(weekly_21d_vpd) # 21 day avg vpd

		np.save(("%s/DALEC_Grass/inputs/met_%s.npy" %(self.workingdir,Fname)),met)

		
