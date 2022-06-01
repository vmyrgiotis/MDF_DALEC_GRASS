# -*- coding: utf-8 -*-
import spotpy
import numpy as np 
import pandas as pd 
from sklearn.metrics import mean_squared_error
from math import sqrt
import importlib
import subprocess
import DALEC_GRASS 

def run(workingdir,sitename) :

	class abc_dalec() :

		def __init__(self):   

			self.workingdir = workingdir
			self.sitename = sitename

			## Load drivers 
			self.met       = np.array(np.load('%s/%s_M.npy' %(self.workingdir,self.sitename)),order="F")   
			self.met       = np.append(self.met[:,:52],self.met,axis=1) ## add 1 spinup year 
			self.met[0,:]  = np.arange(1,len(self.met[0,:])+1) ## re-create index 

			## Fill DALEC-Grass input variables 
			self.deltat   = np.zeros([(self.met.shape[1])]) + 7 # weekly runs 
			self.nodays   = self.met.shape[1]
			self.noyears  = int(self.nodays/float(52)) - 1 # weekly runs 
			self.start    = 1     
			self.finish   = int(self.nodays)
			self.nopools  = 6     
			self.nofluxes = 21 
			self.nopars   = 34
			self.nomet    = self.met.shape[0]
			self.lat      = 50.77
			self.version_code = 1

			#### Load LAI observations 
			self.obs_lai = np.load("%s/%s_O.npy" %(self.workingdir,self.sitename)) 


		def parameters(self): 

			#### DEFAULT PRIORS 
			pars_lims = {0:  [1e-3,  0.1],     # Decomp rate [1e-5, 0.01]
						1:  [0.43,   0.48],    # GPP to resp fraction [~0.46]
						2:  [0.75,   1.5],     # GSI sens leaf growth [1.0, 1.025]
						3:  [0.10,   1.0],     # NPP belowground allocation exponential parameter [0.01, 1.00]
						4:  [1e-3,   2.0],     # GSI max leaf turnover [1e-5, 0.2]
						5:  [1e-3,   1e-1],    # TOR roots [0.0001, 0.01]
						6:  [1e-3,   1e-1],    # TOR litter [0.0001, 0.01]
						7:  [1e-7,   1e-4],    # TOR SOM [1e-7, 0.001]
						8:  [0.01,   0.20],    # T factor (Q10) [0.018,  0.08]
						9:  [7,      25],      # PNUE [7, 20]
						10: [1e-3,   1.0],     # GSI max labile turnover [1e-6, 0.2]
						11: [230,    290],     # GSI min T (K) [225, 330] 
						12: [250,    300],     # GSI max T (K) [225, 330] 
						13: [3600,   20000],   # GSI min photoperiod (sec) [3600, 36000]
						14: [35,     55],      # Leaf Mass per Area [20, 60]
						15: [20,     100],     # initial labile pool size [1, 1000]
						16: [20,     100],     # initial foliar pool size [1, 1000]
						17: [40,     2000],    # initial root pool size [1, 1000]
						18: [40,     2000],    # initial litter pool size [1, 10000]
						19: [10000,  40000],   # GSI max photoperiod (sec) [3600, 64800]
						20: [100,    3000],    # GSI min VPD (Pa) [1, 5500] 
						21: [1000,   5000],    # GSI max VPD (Pa) [1, 5500]
						22: [1e-3,   0.5],     # critical GPP for LAI growth [1e-10, 0.30]
						23: [0.96,   1.00],    # GSI sens for leaf senescenece [0.96, 1.00]
						24: [0.5,    3.0],     # GSI growing stage/step [0.50, 1.5]
						25: [1.0,    2.0],     # Initial GSI [1.0, 2.0]
						26: [500,    1500],    # DM min lim for grazing (kg.DM.ha-1)
						27: [1500,   3000],    # DM min lim for cutting (kg.DM.ha-1)
						28: [0.25,   0.75],    # leaf:stem allocation [0.05, 0.75]
						29: [19000,  21000],   # initial SOM pool size [5000, 10000] (UK) 19000, 21000
						30: [0.015,  0.035],   # livestock demand in DM (1-3% of animal weight) 
						31: [0.01,   0.10],    # Post-grazing labile loss (fraction)
						32: [0.50,   0.90],    # Post-cutting labile loss (fraction)
						33: [0.1,    1.0]}     # min DM removal for grazing instance to occur (g.C.m-2.w-1)

			#### REFINED PRIORS 
			# mcmc = pd.read_csv("Northwyke/sa_NW_lai_acc2.csv") # RMSE against ungrazed years' LAI
			# mcmc = mcmc[mcmc.simulation_0>=0.5]

			self.params=[]
			for x in range(0,self.nopars) : 
				self.params.append(spotpy.parameter.Uniform('P%s' %(x+1), pars_lims[x][0], pars_lims[x][1]))
			return spotpy.parameter.generate(self.params)



		def simulation(self,vector):   

			pars = np.array(vector, order='F')


			if ( (pars[26]>pars[27]) & (pars[12]<=pars[11]) or (pars[21]<=pars[20]) or (pars[19]<=pars[13]) or (pars[29]<pars[15:19].sum()) or (pars[17]>pars[15]+pars[16]+pars[18]) or (pars[7]>pars[6]) ) : return [-np.inf]

			else :

				lai,gpp,nee,pools,fluxes,rem = DALEC_GRASS.carbon_model_mod.carbon_model(self.start,self.finish,self.deltat,self.lat,self.met,pars,self.nopools,self.nofluxes,self.version_code,self.nodays,self.nopars,self.nomet)            

				## Collect havest outputs 
				REMDF = pd.DataFrame(index=range(self.nodays))
				REMDF['Csim'] = (rem[1,:]) * 0.021  
				REMDF['cutsno'] = self.met[7]
				REMDF.cutsno[REMDF.cutsno > 0] = 0
				REMDF.index = pd.date_range('2016-01-01', periods = self.nodays, freq='7D')
				REMDF = REMDF['2017':]

				## Collect LAI outputs 
				LAIDF = pd.DataFrame()
				LAIDF['sim'] = lai
				LAIDF.index = pd.date_range('2016-01-01', periods = self.nodays, freq='7D')
				LAIDF = LAIDF['2017':]
				LAIDF['obs'] = self.obs_lai[:-1]
				LAIDF = LAIDF.dropna()

				## Drop spinup year from results 
				rem = rem[:,52:] 
				lai = lai[52:] 
				gpp = gpp[52:] 
				pools = pools[52:,:] 
				fluxes = fluxes[52:,:] 
				nee = nee[52:] 

				#### Ecological and Dynamic Constrains 
				##################################################################################################
					### Math
				if  (  (np.isnan(pools).any()) or (np.isnan(lai).any()) 
					or (np.isnan(gpp).any()) or (np.isnan(fluxes).any())                           
					or (np.any(pools < 0)) or (np.any(fluxes < 0)) 
					or (np.any(lai < 0)) 
					or (np.all(fluxes[:,[0,1,2,3,4,5,6,7,8,9,11,12,13,14,15,17,18,19,20]]==0,axis=0)).any() 
					### Fluxes  										
					or (np.any(gpp > 25)) 
					or ((gpp*7).sum() < 500*self.noyears ) 
					or ((gpp*7).sum() > 2800*self.noyears) 
					or (np.any((fluxes[:,12]+fluxes[:,13]+fluxes[:,2]) > 20) ) 
					or (((fluxes[:,12]+fluxes[:,13]+fluxes[:,2])*7).sum() < 500*self.noyears) 
					or (((fluxes[:,12]+fluxes[:,13]+fluxes[:,2])*7).sum() > 2600*self.noyears)
					### Soil C 	 
					or (abs(pars[29] - pools[-1,5]) > pars[29]*0.05) ## soil C stable		
					### Management
					or ( (rem[0,:]*21/float(650*0.035) > 70).any() ) # max total LSU_ha_week
					or ( int(abs(REMDF.cutsno.sum())) != int(len(REMDF[REMDF.Csim>0])) ) # all cuts in inputs are simulated 
					) : return [-np.inf]

				return [ sqrt(mean_squared_error(LAIDF.obs,LAIDF.sim)) ]


		def evaluation(self) : return [0]


		def objectivefunction(self,simulation,evaluation) :
			objectivefunction = -spotpy.objectivefunctions.mae(evaluation,simulation)    
			return objectivefunction


	"""
	> Run the model-data fusion using Seamulated Annealing as the algorithm
	""" 

	results = [] 
	spotpy_setup = abc_dalec() 

	# # # ### MCMC Metropolis-Hastings 
	# sampler = spotpy.algorithms.mcmc(spotpy_setup, dbname='Northwyke/mcmc_NW_cut', dbformat='csv', save_sim=True, parallel='mpi') 
	# results.append(sampler.sample(10000000,nChains=1000))

	### Simulated Annealing 
	sampler = spotpy.algorithms.sa(spotpy_setup, dbname='%s/MDF_outs_%s'%(workingdir,sitename), dbformat='csv', save_sim=True) 
	results.append(sampler.sample(repetitions=10000000, Tini=90, Ntemp=3000, alpha=0.99)) # tini: Starting temperature | Ntemp: No of trials per T | alpha: T reduction




