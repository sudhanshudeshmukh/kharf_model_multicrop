from __future__ import division
from qgis.gui import QgsMapToolEmitPoint
import qgis.gui
from qgis.core import QgsSpatialIndex, QgsPoint, QgsRectangle, QgsRaster
from PyQt4.QtGui import *
from PyQt4.QtCore import QVariant
from PyQt4.QtCore import QFileInfo
import csv
import os
import time
import processing
import sys
import shutil
from math import exp
from math import log
from constants_dicts_lookups import *


class KharifModelCalculator:
	"""The actual algorithm for calculating results of the Kharif Model"""
	
	def __init__(self, path, ws_layer, soil_layer, lulc_layer, slope_layer, rainfall_csv_path):
		self.ws_layer = ws_layer
		self.soil_layer = soil_layer
		self.lulc_layer = lulc_layer
		self.slope_layer = slope_layer
		self.slope_provider = slope_layer.dataProvider()
		
		self.wsh_feature_dict = {f.id(): f for f in ws_layer.getFeatures()}
		self.soil_feature_dict = {f.id(): f for f in soil_layer.getFeatures()}
		self.lulc_feature_dict = {f.id(): f for f in lulc_layer.getFeatures()}

		#Index on miniwatershed
		self.index_MINIWSH = QgsSpatialIndex()
		for f in self.wsh_feature_dict.values():  
			self.index_MINIWSH.insertFeature(f)

		#Index on soil map
		self.index_Soil = QgsSpatialIndex()
		for f in self.soil_feature_dict.values():  
			self.index_Soil.insertFeature(f)

		#Index on LULC
		self.index_LULC = QgsSpatialIndex()
		for f in self.lulc_feature_dict.values():  
			self.index_LULC.insertFeature(f)

		
		#This path need to be changed for files having ET0 and KC lookup
		self.path = path

		self.path_et = path + '/ET0_file.csv'
		self.path_kc = path + '/KC_file.csv'

		#~ self.path_Rainfall = path + '/rainfall.csv'
		self.path_Rainfall = rainfall_csv_path
		
	
	def pet_calculation(self,crop_name):
		rainfall_csv = open(self.path_Rainfall)
		self.rain = [int(row["Rainfall"]) for row in csv.DictReader(rainfall_csv)]
		
		test_csv = open(self.path_et)
		a = [float(row["ET0"]) for row in csv.DictReader(test_csv)]
		Kc=[]
		stage=[]
		print (crop_name)
		for i in range (len(dict_crop[crop_name][0])):
		    stage.append(dict_crop[crop_name][0][i][0])
		    Kc.append(dict_crop[crop_name][0][i][1])
		et0=[]
		#Computation of ET0 from July to Nov
		for i in range (0,len(a)):
			if (i in [0,3,5]):
				c = [a[i]]*30
				et0.extend(c)
			else:
				c = [a[i]]*31
				et0.extend(c)
		d=[]
		for i in range(0,len(stage)):
			e=[Kc[i]]*stage[i]
			d.extend(e)
		#computes initial period where total rainfall is below 30mm for sowing date
		def compute_initial_period():
			rain_sum = 0 
			for i in range (0,len(self.rain)):
				if (rain_sum<30):
					rain_sum += self.rain[i]
				else :
					break
			return i
		initial_dry = compute_initial_period()
		d = [0]*initial_dry+ d
		#To calculate till Nov 30 we are truncating KCs for remaingig duration
		if(len(d)>len(et0)):
			d=d[0:len(et0)]
		if (len (d)<len (self.rain)):
			d = d + [0]*(len(self.rain)-len(d))
		elif(len (d)>len (self.rain)):
			self.rain = self.rain + [0]*(len(d)-len(self.rain))		
		pet = [et0[i]*d[i] for i in range (0,len(d))]
		return pet


	def calculate(self, output_csv_filename,crop_name,start_date_index=0,end_date_index=182):
		csvwrite = open(self.path + output_csv_filename,'w+b')
		writer = csv.writer(csvwrite)
		writer.writerow(['X', 'Y','PET-AET','Soil Moisture','Infiltration'])
		
		start_time = time.time()
		count =cn_sum = 0,0
		pet = self.pet_calculation(crop_name.lower())
		xminB =  self.ws_layer.extent().xMinimum()
		xmaxB = self.ws_layer.extent().xMaximum()
		yminB = self.ws_layer.extent().yMinimum()
		ymaxB = self.ws_layer.extent().yMaximum()
		def frange(start,end,step):
			i = start
			while i<=end :
				yield i
				i = i+step
		x_List = [x for x in frange(xminB,xmaxB,STEP)]
		y_List = [x for x in frange(yminB,ymaxB,STEP)]
		print len(x_List)
		print len (y_List)
		ctr=0
		poly_soil=[f for f in self.soil_layer.getFeatures()][0]
		poly_lulc = [f for f in self.lulc_layer.getFeatures()][0]
		self.min_pet_minus_aet = self.max_pet_minus_aet = 0
		#for loop over each point 
		for x_i in x_List:
			for y_i in y_List:
				pt = QgsPoint(x_i,y_i)
				#print "asda"
				#Check in soil layer and get feature for point:
				flag = 0
				#Checking if point lies in watershed or not
				wsh_intersect = self.index_MINIWSH.intersects( QgsRectangle( pt, pt ) )
				if (len(wsh_intersect) > 0):
					for k in wsh_intersect:
						poly_wsh = self.wsh_feature_dict [k]
						if (poly_wsh.geometry().contains(pt)):
							flag =1
				if (flag  == 1):
					soil_intersect = self.index_Soil.intersects(QgsRectangle(pt, pt ) )
					for soil_intersect_iter in soil_intersect:
						poly_soil = self.soil_feature_dict[soil_intersect_iter]
						if (poly_soil.geometry().contains(pt)):
							break
					#Check in LULC layer and get feature for point:
					lulc_intersect = self.index_LULC.intersects( QgsRectangle( pt, pt ) )
					for lulc_intersect_iter in lulc_intersect:
						poly_lulc = self.lulc_feature_dict[lulc_intersect_iter]
						if (poly_lulc.geometry().contains(pt)):
							break
					lu_Desc = poly_lulc[Desc]
					lu_Type = dict_lulc[lu_Desc.lower()]
					#Vulnerable zone computation only for point where LU_TYPE is agriculture or fallow
					if (lu_Type == 'agriculture' or lu_Type == 'fallow land'):
						ctr+=1
						slope_cat = self.slope_provider.identify(pt, QgsRaster.IdentifyFormatValue).results()[1] # Slope of point
						texture = poly_soil[TEX].lower()#Soil texture
						depth = poly_soil[Depth].lower() #Soil depth
						lu_Desc = poly_lulc[Desc] 
						lu_Type = dict_lulc[lu_Desc.lower()]
						HSG =  dict_SoilContent[texture][0]
						cn_val = int(dict_RO[lu_Type][HSG])
						Sand_per = round(float(dict_SoilContent[texture][1]),4)
						Clay_per = round(float(dict_SoilContent[texture][2]),4)
						Gravel_per = round(float(dict_SoilContent[texture][3]),4)
						Organic_matter = 0.7
						Bulk_density = round(float(dict_SoilContent[texture][8]),4)
						AWC = round(float(dict_SoilContent[texture][9]),4)
						Ksat = round(float(dict_SoilContent[texture][7]),4)
						depth_value = float(dict_SoilDep[depth.lower()])
						#derived parameter in input sheet
						Ksat_day = Ksat * 24
						Sat = round(1 - (Bulk_density/2.65),4)
						WP = round(0.4*Bulk_density*Clay_per/100,4)
						FC = WP + AWC
						Sat_depth = Sat * depth_value*1000 
						WP_depth = WP*depth_value*1000
						FC_depth = FC*depth_value*1000
						if(depth_value <= ROOT_LEVEL): #thin soil layer
							SM1 = depth_value - 0.01
							SM2 = 0.01
						else :
							SM1 = ROOT_LEVEL
							SM2 = depth_value - ROOT_LEVEL 
						cn_s = cn_val
						cn3 = (23*cn_val)/(10+0.13*cn_val)
						if (slope_cat > 5.0):
							cn_s = (((cn3-cn_val)/float(3))*(1-2*exp(-13.86*slope_cat * 0.01))) + cn_val
						cn1_s = cn_s - 20*(100-cn_s)/float(100-cn_s+exp(2.533-0.0636*(100-cn_s)))
						cn3_s = cn_s *exp(0.00673*(100-cn_s))
						Smax = 25.4 * (1000/float(cn1_s) - 10)
						S3 = 25.4 * (1000/float(cn3_s) - 10)
						W2 = (log((FC_depth- WP_depth)/(1-float(S3/Smax)) - (FC_depth - WP_depth )) - log ((Sat_depth - WP_depth)/(1-2.54/Smax) - (Sat_depth - WP_depth)))/((Sat_depth- WP_depth) - (FC_depth - WP_depth))
						W1 = log((FC_depth- WP_depth)/(1- S3/Smax) - (FC_depth - WP_depth)) + W2 * (FC_depth -WP_depth)
						TT_perc = (Sat_depth- FC_depth)/Ksat
						daily_perc_factor = 1 - exp(-24 / TT_perc) 
						depletion_factor = 0.5
						ini_sm_tot, S_swat, Cn_swat, Ia_swat, KS, SM1_before, R_to_second_layer, sec_run_off, SM2_before= 0, 0, 0, 0, 0, 0, 0, 0, 0
						Swat_RO, infiltration, AET,perc_to_GW = [], [], [],[] 
						SM1_fraction, layer2_moisture = WP, WP 
						for i in range (0,end_date_index+1):
							ini_sm_tot = (SM1_fraction*SM1+layer2_moisture*SM2)*1000
							S_swat = Smax*(1 - (ini_sm_tot	-WP_depth)/((ini_sm_tot	- WP_depth)+exp(W1 - W2*(ini_sm_tot- WP_depth))))
							Cn_swat = 25400/float(S_swat+254)
							Ia_swat = 0.2*S_swat
							if(self.rain[i]>Ia_swat):
								Swat_RO.append(((self.rain[i]-Ia_swat)**2)/(self.rain[i]+0.8*S_swat))
							else:
								Swat_RO.append(0)
							infiltration.append(self.rain[i]-Swat_RO[i])
							if (SM1_fraction < WP):
								KS= 0 
							elif (SM1_fraction > (FC *(1- depletion_factor) + depletion_factor*WP)):
								KS = 1
							else :	
								KS = (SM1_fraction - WP)/(FC - WP) /(1- depletion_factor)	
							AET.append(KS*pet[i])
							SM1_before = (SM1_fraction*SM1 +((infiltration[i]-AET[i])/float(1000)))/SM1
							if (SM1_before<FC):
								R_to_second_layer =0
							elif (layer2_moisture<Sat) :
								R_to_second_layer = min((Sat - layer2_moisture)*SM2*1000, (SM1_before - FC)*SM1*1000*daily_perc_factor)
							else :
								R_to_second_layer = 0
							if (((SM1_fraction*SM1 + (infiltration[i]-AET[i]-R_to_second_layer)/1000)/SM1) > Sat):
								sec_run_off= (((SM1_fraction*SM1 + (infiltration[i]-AET[i]-R_to_second_layer)/1000)/SM1) - WP) *0.1*1000
							else:
								sec_run_off = 0 
							SM1_fraction = min((SM1_before*SM1*1000 - R_to_second_layer)/SM1/1000,Sat)
							SM2_before = (layer2_moisture*SM2*1000+R_to_second_layer)/SM2/1000
							perc_to_GW.append(max((SM2_before - FC)*SM2*daily_perc_factor*1000,0))
							layer2_moisture = min(((SM2_before*SM2*1000- perc_to_GW[i])/SM2/1000),Sat)
						pet_minus_aet = sum(pet[start_date_index:end_date_index+1])- sum(AET[start_date_index:end_date_index+1])
						writer.writerow([x_i,y_i,pet_minus_aet,ini_sm_tot,sum(infiltration[start_date_index:end_date_index+1])])
						self.min_pet_minus_aet = min(self.min_pet_minus_aet, pet_minus_aet)
						self.max_pet_minus_aet = max(self.max_pet_minus_aet, pet_minus_aet)
		print (ctr)
		csvwrite.close()
		print("--- %s seconds ---" % (time.time() - start_time))
		print("done")
