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
	"""
	The actual algorithm for calculating results of the Kharif Model
	"""
	
	
	
	def __init__(self, path, ws_layer, soil_layer, lulc_layer, slope_layer, rainfall_csv_path):
		self.ws_layer = ws_layer
		self.soil_layer = soil_layer
		self.lulc_layer = lulc_layer
		self.slope_layer = slope_layer
		
		self.wsh_feature_dict = {f.id(): f for f in ws_layer.getFeatures()}
		self.soil_feature_dict = {f.id(): f for f in soil_layer.getFeatures()}
		self.lulc_feature_dict = {f.id(): f for f in lulc_layer.getFeatures()}

		#Index on miniwatershed
		self.index_MINIWSH = QgsSpatialIndex(ws_layer.getFeatures())
		#~ self.index_MINIWSH = QgsSpatialIndex()
		#~ for f in self.wsh_feature_dict.values():  
			#~ self.index_MINIWSH.insertFeature(f)

		#Index on soil map
		self.index_Soil = QgsSpatialIndex(soil_layer.getFeatures())
		#~ self.index_Soil = QgsSpatialIndex()
		#~ for f in self.soil_feature_dict.values():  
			#~ self.index_Soil.insertFeature(f)

		#Index on LULC
		self.index_LULC = QgsSpatialIndex(lulc_layer.getFeatures())
		#~ self.index_LULC = QgsSpatialIndex()
		#~ for f in self.lulc_feature_dict.values():  
			#~ self.index_LULC.insertFeature(f)

		
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
		self.pet = [et0[i]*d[i] for i in range (0,len(d))]
		#~ print 'pet : ', self.pet
	
	def get_containing_polygon(self, index, feature_dict, point):
		intersectors = index.intersects( QgsRectangle( point, point ) )
		for intersector in intersectors:
			polygon = feature_dict[intersector]
			if (polygon.geometry().contains(point)):
				return polygon
		return False
	
	def set_output_points(self):
		xminB =  self.ws_layer.extent().xMinimum()
		xmaxB = self.ws_layer.extent().xMaximum()
		yminB = self.ws_layer.extent().yMinimum()
		ymaxB = self.ws_layer.extent().yMaximum()
		print 'boundary min, max : ' , xminB, xmaxB, yminB, ymaxB
		def frange(start,end,step):
			i = start
			while i<=end :
				yield i
				i = i+step
		x_List = [x for x in frange(xminB,xmaxB,STEP)]
		y_List = [x for x in frange(yminB,ymaxB,STEP)]
		print len(x_List)
		print len (y_List)
		self.output_points = [QgsPoint(x,y)	for x in x_List	for y in y_List]	
		
	def setup_for_daily_computations(self, point):
		"""
		"""
		poly_soil = self.get_containing_polygon(self.index_Soil, self.soil_feature_dict, point)
		texture = poly_soil[TEX].lower()
		Ksat = round(float(dict_SoilContent[texture][7]),4)
		self.Sat = round(float(dict_SoilContent[texture][6]),4)
		self.WP = round(float(dict_SoilContent[texture][4]),4)
		self.FC = round(float(dict_SoilContent[texture][5]),4)
		depth_value = float(dict_SoilDep[poly_soil[Depth].lower()])
		
		poly_lulc = self.get_containing_polygon(self.index_LULC, self.lulc_feature_dict, point)
		lu_Type = dict_lulc[poly_lulc[Desc].lower()]
		
		if (lu_Type != 'agriculture' and lu_Type != 'fallow land'):	return False
		
		HSG =  dict_SoilContent[texture][0]
		cn_val = int(dict_RO[lu_Type][HSG])
		
		slope_cat = self.slope_layer.dataProvider().identify(point, QgsRaster.IdentifyFormatValue).results()[1] # Slope of point
		
		Sat_depth = self.Sat * depth_value*1000
		self.WP_depth = self.WP*depth_value*1000
		FC_depth = self.FC*depth_value*1000
		if(depth_value <= ROOT_LEVEL): #thin soil layer
			self.SM1 = depth_value - 0.01;	self.SM2 = 0.01
		else :
			self.SM1 = ROOT_LEVEL;	self.SM2 = depth_value - ROOT_LEVEL 
		
		cn_s = cn_val
		cn3 = (23*cn_val)/(10+0.13*cn_val)
		if (slope_cat > 5.0):
			cn_s = (((cn3-cn_val)/float(3))*(1-2*exp(-13.86*slope_cat * 0.01))) + cn_val
		cn1_s = cn_s - 20*(100-cn_s)/float(100-cn_s+exp(2.533-0.0636*(100-cn_s)))
		cn3_s = cn_s *exp(0.00673*(100-cn_s))
		
		self.Smax = 25.4 * (1000/float(cn1_s) - 10)
		S3 = 25.4 * (1000/float(cn3_s) - 10)
		self.W2 = (log((FC_depth- self.WP_depth)/(1-float(S3/self.Smax)) - (FC_depth - self.WP_depth )) - log ((Sat_depth - self.WP_depth)/(1-2.54/self.Smax) - (Sat_depth - self.WP_depth)))/((Sat_depth- self.WP_depth) - (FC_depth - self.WP_depth))
		self.W1 = log((FC_depth- self.WP_depth)/(1- S3/self.Smax) - (FC_depth - self.WP_depth)) + self.W2 * (FC_depth -self.WP_depth)
		
		TT_perc = (Sat_depth- FC_depth)/Ksat	#SWAT equation 2:3.2.4
		self.daily_perc_factor = 1 - exp(-24 / TT_perc)	#SWAT equation 2:3.2.3
		
		self.depletion_factor = 0.5
	
	def primary_runoff(self, day):
		"""
		Retention parameter 'S_swat' using SWAT equation 2:1.1.6
		Curve Number for the day 'Cn_swat' using SWAT equation 2:1.1.11
		Initial abstractions (surface storage,interception and infiltration prior to runoff)
			'Ia_swat' derived approximately as recommended by SWAT
		Primary Runoff 'Swat_RO' using SWAT equation 2:1.1.1
		"""
		
		self.ini_sm_tot = (self.SM1_fraction * self.SM1 + self.layer2_moisture * self.SM2) * 1000
		self.SW = self.ini_sm_tot - self.WP_depth
		self.S_swat = self.Smax*(1 - self.SW/(self.SW + exp(self.W1 - self.W2 * self.SW)))
		
		self.Cn_swat = 25400/float(self.S_swat+254)
		Ia_swat = 0.2 * self.S_swat
		if(self.rain[day] > Ia_swat):
			self.Swat_RO.append(((self.rain[day]-Ia_swat)**2)/(self.rain[day] + 0.8*self.S_swat))
		else:
			self.Swat_RO.append(0)
		self.infiltration.append(self.rain[day]-self.Swat_RO[day])
	
	def aet(self, day):
		"""
		Water Stress Coefficient 'KS' using FAO Irrigation and Drainage Paper 56, page 167 and
			page 169 equation 84
		Actual Evapotranspiration 'AET' using FAO Irrigation and Drainage Paper 56, page 6 and 
			page 161 equation 81
		"""
		if (self.SM1_fraction < self.WP):
			KS= 0 
		elif (self.SM1_fraction > (self.FC *(1- self.depletion_factor) + self.depletion_factor * self.WP)):
			KS = 1
		else :	
			KS = (self.SM1_fraction - self.WP)/(self.FC - self.WP) /(1- self.depletion_factor)
		self.AET.append( KS * self.pet[day] )
	
	def percolation_below_root_zone(self, day):
		"""
		Calculate soil moisture (fraction) 'SM1_before' as the one after infiltration and (then) AET occur,
		but before percolation starts below root-zone. Percolation below root-zone starts only if
		'SM1_before' is more than field capacity and the soil below root-zone is not saturated,i.e.
		'layer2_moisture' is less than saturation. When precolation occurs it is derived as
		the minimum of the maximum possible percolation (using SWAT equation 2:3.2.3) and
		the amount available in the root-zone for percolation.
		"""
		self.SM1_before = (self.SM1_fraction*self.SM1 +((self.infiltration[day]-self.AET[day])/float(1000)))/self.SM1
		if (self.SM1_before < self.FC):
			self.R_to_second_layer =0
		elif (self.layer2_moisture < self.Sat) :
			self.R_to_second_layer = min((self.Sat - self.layer2_moisture) * self.SM2 * 1000,
										 (self.SM1_before - self.FC) * self.SM1 * 1000 * self.daily_perc_factor)
		else :
			self.R_to_second_layer = 0
		self.SM2_before = (self.layer2_moisture*self.SM2*1000 + self.R_to_second_layer)/self.SM2/1000
	
	def secondary_runoff(self, day):
		"""
		
		"""
		if (((self.SM1_before*self.SM1 - self.R_to_second_layer/1000)/self.SM1) > self.Sat):
			sec_run_off= (((self.SM1_before*self.SM1 - self.R_to_second_layer/1000)/self.SM1) - self.WP) *0.1*1000
		else:
			sec_run_off = 0
		self.SM1_fraction = min((self.SM1_before*self.SM1*1000 - self.R_to_second_layer)/self.SM1/1000,self.Sat)
	
	def percolation_to_GW(self, day):
		"""
		
		"""
		self.perc_to_GW.append(max((self.SM2_before - self.FC)*self.SM2*self.daily_perc_factor*1000,0))
		self.layer2_moisture = min(((self.SM2_before*self.SM2*1000- self.perc_to_GW[day])/self.SM2/1000),self.Sat)
	
	def calculate(self, output_csv_filename,crop_name,start_date_index=0,end_date_index=182):
		csvwrite = open(self.path + output_csv_filename,'w+b')
		writer = csv.writer(csvwrite)
		writer.writerow(['X', 'Y','PET-AET','Soil Moisture','Infiltration'])
		
		start_time = time.time()
		
		self.pet_calculation(crop_name.lower())
		self.set_output_points()
		self.max_pet_minus_aet = 0;	count = 0
		for point in self.output_points:
			if self.get_containing_polygon(self.index_MINIWSH, self.wsh_feature_dict, point) == False:	continue
			if self.setup_for_daily_computations(point) == False:	continue
			self.ini_sm_tot = self.S_swat = self.Cn_swat = self.Ia_swat = self.KS = self.SM1_before = self.R_to_second_layer = self.sec_run_off = self.SM2_before = 0
			self.Swat_RO, self.infiltration, self.AET, self.perc_to_GW = [], [], [],[] 
			self.SM1_fraction = self.layer2_moisture = self.WP
			count += 1
			#~ if count > 1 :	break
			if count != 0 and count%100 == 0:	print count
			for day in range (0,end_date_index+1):
				self.primary_runoff(day)
				self.aet(day)
				self.percolation_below_root_zone(day)
				self.secondary_runoff(day)
				self.percolation_to_GW(day)
			pet_minus_aet = sum(self.pet[start_date_index:end_date_index+1])- sum(self.AET[start_date_index:end_date_index+1])
			writer.writerow([point.x(),point.y(), pet_minus_aet,self.ini_sm_tot,sum(self.infiltration[start_date_index:end_date_index+1])])
			self.max_pet_minus_aet = max(self.max_pet_minus_aet, pet_minus_aet)
		csvwrite.close()
		print("--- %s seconds ---" % (time.time() - start_time))
		print("done")
