from __future__ import division
from qgis.gui import QgsMapToolEmitPoint
import qgis.gui
from qgis.core import QgsSpatialIndex, QgsPoint, QgsRectangle, QgsRaster, QgsVectorLayer, QgsFeature
from qgis.analysis import  QgsGeometryAnalyzer
from PyQt4.QtGui import *
from PyQt4.QtCore import QVariant
from PyQt4.QtCore import QFileInfo
import csv
import os
import time
import processing
import sys
import shutil
from collections import OrderedDict
from math import exp
from math import log
from constants_dicts_lookups import *


BOUNDARY_LABEL = 'Zones'
SOIL_LABEL = 'Soil'
LULC_LABEL = 'Land-Use-Land-Cover'
SLOPE_LABEL = 'Slope'
CADESTRAL_LABEL = 'Cadestral'

CALCULATE_FOR_LULC_TYPES = ['agriculture', 'fallow land']

class Budget:
	
	def __init__(self):
		self.sm, self.runoff, self.infil, self.AET, self.GW_rech = [],[],[],[],[]
	
	def summarize(self, PET_sum, PET_sum_cropend, start_date_index, end_date_index, crop_end_index):
		self.sm_crop_end = self.sm[crop_end_index]
 		self.sm_monsoon_end = self.sm[end_date_index]
		self.runoff_crop_end = sum(self.runoff[start_date_index:crop_end_index+1]) 		
		self.runoff_monsoon_end = sum(self.runoff[start_date_index:end_date_index+1])
		self.infil_crop_end = sum(self.infil[start_date_index:crop_end_index+1])
		self.infil_monsoon_end = sum(self.infil[start_date_index:end_date_index+1])
		self.AET_crop_end = sum(self.AET[start_date_index:crop_end_index+1])
		self.AET_monsoon_end = sum(self.AET[start_date_index:end_date_index+1])
		self.GW_rech_crop_end = sum(self.GW_rech[start_date_index:crop_end_index+1])
		self.GW_rech_monsoon_end = sum(self.GW_rech[start_date_index:end_date_index+1])
		self.PET_minus_AET_monsoon_end = PET_sum - self.AET_monsoon_end
		self.PET_minus_AET_post_monsoon= (PET_sum_cropend - self.AET_crop_end)-self.PET_minus_AET_monsoon_end
		self.PET_minus_AET_crop_end= (PET_sum_cropend - self.AET_crop_end)
	
	def get_PET_minus_AET(self, PET):
		pass
	
class Point:
	
	def __init__(self, qgsPoint):
		self.qgsPoint = qgsPoint
		self.container_polygons = {}
		self.slope = None
		self.budget = Budget()
		self.crop_name = None
	
	def run_model(self, rain, PET, PET_sum, PET_sum_cropend, start_date_index, end_date_index,crop_end_index):
		self.setup_for_daily_computations()
		
		self.SM1_fraction = self.layer2_moisture = self.WP
		
		for day in range (0,max(end_date_index,crop_end_index)+1):
			self.primary_runoff(day, rain)
			self.aet(day, PET)
			self.percolation_below_root_zone(day)
			self.secondary_runoff(day)
			self.percolation_to_GW(day)
		
		self.budget.summarize(PET_sum, PET_sum_cropend, start_date_index, end_date_index,crop_end_index)
	
	def setup_for_daily_computations(self):
		"""
		"""
		poly_soil = self.container_polygons[SOIL_LABEL]
		texture = poly_soil[TEX].lower()
		Ksat = round(float(dict_SoilContent[texture][7]),4)
		self.Sat = round(float(dict_SoilContent[texture][6]),4)
		self.WP = round(float(dict_SoilContent[texture][4]),4)
		self.FC = round(float(dict_SoilContent[texture][5]),4)
		depth_value = float(dict_SoilDep[poly_soil[Depth].lower()])
		
		lu_Type = dict_lulc[self.container_polygons[LULC_LABEL][Desc].lower()]
		
		HSG =  dict_SoilContent[texture][0]
		cn_val = int(dict_RO[lu_Type][HSG])
		
		Sat_depth = self.Sat * depth_value*1000
		self.WP_depth = self.WP*depth_value*1000
		FC_depth = self.FC*depth_value*1000
		ROOT_LEVEL = dict_crop_root[self.crop_name]
		if(depth_value <= ROOT_LEVEL): #thin soil layer
			self.SM1 = depth_value - 0.01;	self.SM2 = 0.01
		else:
			self.SM1 = ROOT_LEVEL;	self.SM2 = depth_value - ROOT_LEVEL 
		
		cn_s = cn_val
		cn3 = (23*cn_val)/(10+0.13*cn_val)
		if (self.slope > 5.0):
			cn_s = (((cn3-cn_val)/float(3))*(1-2*exp(-13.86*self.slope * 0.01))) + cn_val
		cn1_s = cn_s - 20*(100-cn_s)/float(100-cn_s+exp(2.533-0.0636*(100-cn_s)))
		cn3_s = cn_s *exp(0.00673*(100-cn_s))
		
		self.Smax = 25.4 * (1000/float(cn1_s) - 10)
		S3 = 25.4 * (1000/float(cn3_s) - 10)
		self.W2 = (log((FC_depth- self.WP_depth)/(1-float(S3/self.Smax)) - (FC_depth - self.WP_depth )) - log ((Sat_depth - self.WP_depth)/(1-2.54/self.Smax) - (Sat_depth - self.WP_depth)))/((Sat_depth- self.WP_depth) - (FC_depth - self.WP_depth))
		self.W1 = log((FC_depth- self.WP_depth)/(1- S3/self.Smax) - (FC_depth - self.WP_depth)) + self.W2 * (FC_depth -self.WP_depth)
		
		TT_perc = (Sat_depth- FC_depth)/Ksat	#SWAT equation 2:3.2.4
		self.daily_perc_factor = 1 - exp(-24 / TT_perc)	#SWAT equation 2:3.2.3
		
		self.depletion_factor = dict_crop[self.crop_name][1]
	
	def primary_runoff(self, day, rain):
		"""
		Retention parameter 'S_swat' using SWAT equation 2:1.1.6
		Curve Number for the day 'Cn_swat' using SWAT equation 2:1.1.11
		Initial abstractions (surface storage,interception and infiltration prior to runoff)
			'Ia_swat' derived approximately as recommended by SWAT
		Primary Runoff 'Swat_RO' using SWAT equation 2:1.1.1
		"""
		self.budget.sm.append((self.SM1_fraction * self.SM1 + self.layer2_moisture * self.SM2) * 1000)
		self.SW = self.budget.sm[-1] - self.WP_depth
		S_swat = self.Smax*(1 - self.SW/(self.SW + exp(self.W1 - self.W2 * self.SW)))
		
		Cn_swat = 25400/float(S_swat+254)
		Ia_swat = 0.2 * S_swat
		#~ print 'len(rain), day : ', len(rain), day
		if(rain[day] > Ia_swat):
			self.budget.runoff.append(((rain[day]-Ia_swat)**2)/(rain[day] + 0.8*S_swat))
		else:
			self.budget.runoff.append(0)
		self.budget.infil.append(rain[day] - self.budget.runoff[day])
		assert len(self.budget.runoff) == day+1, (self.budget.runoff, day)
		assert len(self.budget.infil) == day+1
	
	def aet(self, day, PET):
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
		self.budget.AET.append( KS * PET[day] )
	
	def percolation_below_root_zone(self, day):
		"""
		Calculate soil moisture (fraction) 'SM1_before' as the one after infiltration and (then) AET occur,
		but before percolation starts below root-zone. Percolation below root-zone starts only if
		'SM1_before' is more than field capacity and the soil below root-zone is not saturated,i.e.
		'layer2_moisture' is less than saturation. When precolation occurs it is derived as
		the minimum of the maximum possible percolation (using SWAT equation 2:3.2.3) and
		the amount available in the root-zone for percolation.
		"""
		self.SM1_before = (self.SM1_fraction*self.SM1 +((self.budget.infil[day]-self.budget.AET[day])/float(1000)))/self.SM1
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
		self.budget.GW_rech.append(max((self.SM2_before - self.FC)*self.SM2*self.daily_perc_factor*1000,0))
		self.layer2_moisture = min(((self.SM2_before*self.SM2*1000- self.budget.GW_rech[day])/self.SM2/1000),self.Sat)
	

class VectorLayer:
	
	def __init__(self, qgsLayer, name=''):
		print name, qgsLayer
		self.qgsLayer = qgsLayer
		self.name = name
		self.feature_dict = {f.id(): f for f in qgsLayer.getFeatures()}
		self.index = QgsSpatialIndex(qgsLayer.getFeatures())
	
	def get_polygon_containing_point(self, point):
		intersector_ids = self.index.intersects( QgsRectangle( point.qgsPoint, point.qgsPoint ) )
		for intersector_id in intersector_ids:
			polygon = self.feature_dict[intersector_id]
			if (polygon.geometry().contains(point.qgsPoint)):
				return polygon

		return None


class KharifModelCalculator:
	"""
	The actual algorithm for calculating results of the Kharif Model
	"""
	
	def __init__(self, path, zones_layer, soil_layer, lulc_layer, cadestral_layer, slope_layer, rainfall_csv_path):
		self.zones_layer = VectorLayer(zones_layer, BOUNDARY_LABEL)
		self.soil_layer = VectorLayer(soil_layer, SOIL_LABEL)
		self.lulc_layer = VectorLayer(lulc_layer, LULC_LABEL)
		self.cadestral_layer = VectorLayer(cadestral_layer, CADESTRAL_LABEL)
		zone_polygon_ids = self.zones_layer.feature_dict.keys()
		self.zone_points_dict = dict(zip(zone_polygon_ids, [[]	for i in range(len(zone_polygon_ids))]))
		cadestral_polygon_ids = self.cadestral_layer.feature_dict.keys()
		#~ self.cadestral_points_dict = dict(zip(cadestral_polygon_ids, [[]	for i in range(len(cadestral_polygon_ids))]))
		#~ print 'zone_points_dict : ', self.zone_points_dict
		
		self.slope_layer = slope_layer
		
		# Working Directory path
		self.path = path

		self.path_et = path + '/ET0_file.csv'

		#~ rainfall_csv_path = path + '/rainfall.csv'
		rainfall_csv = open(rainfall_csv_path)
		self.rain = [int(row["Rainfall"]) for row in csv.DictReader(rainfall_csv)]
		print 'len(rain) = ', len(self.rain)
	
	def pet_calculation(self, crop_name):
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
			if (i in [0,3,5,10]):
				c = [a[i]]*30
				et0.extend(c)
			elif (i in [9]):
				c = [a[i]]*28
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
		#To handle long kharif crop 
		kc_len=len(d)
		if(kc_len<=183):
			d = d + [0]*(len(self.rain)-len(d))
		elif(kc_len>183):
			self.rain = self.rain + [0]*(len(d)-len(self.rain))
		et0=et0[0:len(d)]
		#To calculate till Nov 30 we are truncating KCs for remaingig duration
		return ([et0[i]*d[i] for i in range (0,len(d))] ,kc_len-1)
	
	def filter_out_cadestral_plots_outside_boundary(self):
		#~ QgsGeometryAnalyzer().dissolve(self.zones_layer.qgsLayer, 'temp.shp')
		#~ dissolved_zones_layer = QgsVectorLayer('temp.shp', 'dissolved boundary', 'ogr')
		filtered_feature_dict = {}
		for polygon_id in self.cadestral_layer.feature_dict:
			for feature in self.zones_layer.qgsLayer.getFeatures():
				if self.cadestral_layer.feature_dict[polygon_id].geometry().intersects(feature.geometry()):
					filtered_feature_dict[polygon_id] = self.cadestral_layer.feature_dict[polygon_id]
					break
		self.cadestral_layer.feature_dict = filtered_feature_dict
	
	def generate_output_points_grid(self, input_points_filename=None):
		if input_points_filename is None:
			xminB =  self.zones_layer.qgsLayer.extent().xMinimum()
			xmaxB = self.zones_layer.qgsLayer.extent().xMaximum()
			yminB = self.zones_layer.qgsLayer.extent().yMinimum()
			ymaxB = self.zones_layer.qgsLayer.extent().yMaximum()
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
		else:
			# Read from file
			pass
		output_points = [Point(QgsPoint(x,y))	for x in x_List	for y in y_List]
		return output_points
	
	def filter_out_points_outside_boundary(self):
		filtered_points = []
		for point in self.output_grid_points:
			polygon = self.zones_layer.get_polygon_containing_point(point)
			if polygon is not None:
				point.container_polygons[BOUNDARY_LABEL] = polygon
				self.zone_points_dict[polygon.id()].append(point)
				filtered_points.append(point)
		self.output_grid_points = filtered_points
	
	def generate_output_points_for_cadestral_plots(self):
		#~ cadestral_points_dict = {};
		output_cadestral_points = []
		for polygon_id in self.cadestral_layer.feature_dict:
			qgsPoint = self.cadestral_layer.feature_dict[polygon_id].geometry().centroid().asPoint()
			polygon_geom = self.cadestral_layer.feature_dict[polygon_id].geometry()
			if polygon_geom.contains(qgsPoint):
				point = Point(qgsPoint)
			else:
				for feature in self.zones_layer.qgsLayer.getFeatures():
					if polygon_geom.intersects(feature.geometry()):
						polygon_intersection_some_zone = polygon_geom.intersection(feature.geometry())
						point = Point(polygon_intersection_some_zone.pointOnSurface().asPoint())
						break
			point.container_polygons[CADESTRAL_LABEL] = self.cadestral_layer.feature_dict[polygon_id]
			#~ cadestral_points_dict[polygon_id] = point
			output_cadestral_points.append(point)
		#~ return cadestral_points_dict, output_cadestral_points
		return output_cadestral_points
	
	def set_container_polygon_of_points_for_layers(self, points, polygon_vector_layers):
		for layer in polygon_vector_layers:
			for p in points:
				p.container_polygons[layer.name] = layer.get_polygon_containing_point(p)
				#~ if p.container_polygons[layer.name] is None:	raise Exception(layer.name, p.qgsPoint.x(), p.qgsPoint.y())
	
	#~ def add_points_for_empty_cadestral_plots(self):
		#~ count = 0
		#~ for polygon_id in self.cadestral_layer.feature_dict:
			#~ count += 1;	print count
			#~ if len(self.cadestral_points_dict[polygon_id]) == 0:
				#~ point = Point(self.cadestral_layer.feature_dict[polygon_id].geometry().centroid().asPoint())
				#~ point.container_polygons[CADESTRAL_LABEL] = self.cadestral_layer.feature_dict[polygon_id]
				#~ self.cadestral_points_dict[polygon_id].append(point)
				#~ zone_polygon = self.zones_layer.get_polygon_containing_point(point)
				#~ point.container_polygons[BOUNDARY_LABEL] = zone_polygon
				#~ self.zone_points_dict[zone_polygon.id()].append(point)
				#~ self.output_points.append(point)
	
	def set_slope_at_points(self, points):
		for point in points:
			point.slope = self.slope_layer.dataProvider().identify(
							point.qgsPoint, QgsRaster.IdentifyFormatValue).results()[1]
	
	def set_crop_at_points(self, points,crop_name):
		for point in points:
			point.crop_name =crop_name

	def output_point_results_to_csv(self, pointwise_output_csv_filename):
		csvwrite = open(self.path + pointwise_output_csv_filename,'w+b')
		writer = csv.writer(csvwrite)
		writer.writerow(['X', 'Y','Monsoon PET-AET','Post Monsoon PET-AET' ,'Soil Moisture','Infiltration', 'Runoff', 'GW Recharge'])
		for point in self.output_grid_points:
			if not point.container_polygons[BOUNDARY_LABEL]:	continue
			writer.writerow([point.qgsPoint.x(), point.qgsPoint.y(), point.budget.PET_minus_AET_monsoon_end, point.budget.PET_minus_AET_post_monsoon, point.budget.sm_crop_end, point.budget.infil_monsoon_end, point.budget.runoff_monsoon_end, point.budget.GW_rech_monsoon_end])
		csvwrite.close()
	
	def compute_zonewise_budget(self):
		self.zonewise_budgets = OrderedDict()
		for zone_id in self.zone_points_dict:
			zone_points = self.zone_points_dict[zone_id]
			no_of_zone_points = len(zone_points)
			if no_of_zone_points == 0:	continue
			self.zonewise_budgets[zone_id] = {'agricultural': OrderedDict(), 'non-agricultural': OrderedDict()}
			all_agricultural_points = filter(lambda p:	dict_lulc[p.container_polygons[LULC_LABEL][Desc].lower()] in ['agriculture', 'fallow land'], zone_points)
			non_agricultural_points_dict = {lulc_type: filter(lambda p:	dict_lulc[p.container_polygons[LULC_LABEL][Desc].lower()] == lulc_type, zone_points)	for lulc_type in self.lulc_types if lulc_type not in ['agriculture', 'fallow land', 'water']}
			
			no_of_soil_type_points = {}
			for soil_type in self.soil_types:
				soil_type_points = filter(lambda p:	p.container_polygons[SOIL_LABEL][TEX].lower() == soil_type, all_agricultural_points)
				no_of_soil_type_points[soil_type] = len(soil_type_points)
				if no_of_soil_type_points[soil_type] == 0:	continue
				
				zb = self.zonewise_budgets[zone_id]['agricultural'][soil_type] = Budget()
				zb.sm_crop_end = sum([p.budget.sm_crop_end	for p in soil_type_points]) / no_of_soil_type_points[soil_type]
				zb.runoff_monsoon_end = sum([p.budget.runoff_monsoon_end	for p in soil_type_points]) / no_of_soil_type_points[soil_type]
				zb.infil_monsoon_end = sum([p.budget.infil_monsoon_end	for p in soil_type_points]) / no_of_soil_type_points[soil_type]
				zb.AET_crop_end = sum([p.budget.AET_crop_end	for p in soil_type_points]) / no_of_soil_type_points[soil_type]
				zb.GW_rech_monsoon_end = sum([p.budget.GW_rech_monsoon_end	for p in soil_type_points]) / no_of_soil_type_points[soil_type]
				zb.PET_minus_AET_monsoon_end = sum([p.budget.PET_minus_AET_monsoon_end	for p in soil_type_points]) / no_of_soil_type_points[soil_type]
				zb.PET_minus_AET_post_monsoon = sum([p.budget.PET_minus_AET_post_monsoon	for p in soil_type_points]) / no_of_soil_type_points[soil_type]
			
			no_of_non_ag_lulc_type_points = {}
			for lulc_type in non_agricultural_points_dict:
				lulc_type_points = non_agricultural_points_dict[lulc_type]
				no_of_non_ag_lulc_type_points[lulc_type] = len(lulc_type_points)
				if no_of_non_ag_lulc_type_points[lulc_type] == 0:	continue
				
				zb = self.zonewise_budgets[zone_id]['non-agricultural'][lulc_type] = Budget()
				zb.sm_crop_end = sum([p.budget.sm_crop_end	for p in lulc_type_points]) / no_of_non_ag_lulc_type_points[lulc_type]
				zb.runoff_monsoon_end = sum([p.budget.runoff_monsoon_end	for p in lulc_type_points]) / no_of_non_ag_lulc_type_points[lulc_type]
				zb.infil_monsoon_end = sum([p.budget.infil_monsoon_end	for p in lulc_type_points]) / no_of_non_ag_lulc_type_points[lulc_type]
				zb.AET_crop_end = sum([p.budget.AET_crop_end	for p in lulc_type_points]) / no_of_non_ag_lulc_type_points[lulc_type]
				zb.GW_rech_monsoon_end = sum([p.budget.GW_rech_monsoon_end	for p in lulc_type_points]) / no_of_non_ag_lulc_type_points[lulc_type]
				zb.PET_minus_AET_monsoon_end = sum([p.budget.PET_minus_AET_monsoon_end	for p in lulc_type_points]) / no_of_non_ag_lulc_type_points[lulc_type]
				zb.PET_minus_AET_post_monsoon = sum([p.budget.PET_minus_AET_post_monsoon	for p in lulc_type_points]) / no_of_non_ag_lulc_type_points[lulc_type]
			
			zb = Budget()
			zb.sm_crop_end = sum([p.budget.sm_crop_end	for p in zone_points]) / no_of_zone_points
			zb.runoff_monsoon_end = sum([p.budget.runoff_monsoon_end	for p in zone_points]) / no_of_zone_points
			zb.infil_monsoon_end = sum([p.budget.infil_monsoon_end	for p in zone_points]) / no_of_zone_points
			zb.AET_crop_end = sum([p.budget.AET_crop_end	for p in zone_points]) / no_of_zone_points
			zb.GW_rech_monsoon_end = sum([p.budget.GW_rech_monsoon_end	for p in zone_points]) / no_of_zone_points
			zb.PET_minus_AET_monsoon_end = sum([p.budget.PET_minus_AET_monsoon_end	for p in zone_points]) / no_of_zone_points
			zb.PET_minus_AET_post_monsoon = sum([p.budget.PET_minus_AET_post_monsoon	for p in zone_points]) / no_of_zone_points
			self.zonewise_budgets[zone_id]['zone'] = {'overall':zb}  # dict {'overall':zb} assigned instead of simple zb for convenience in iterating with ag and non-ag
	
	def output_zonewise_budget_to_csv(self, zonewise_budget_csv_filename, PET_sum_cropend, rain_sum):
		csvwrite = open(self.path + zonewise_budget_csv_filename,'wb')
		writer = csv.writer(csvwrite)
		writer.writerow([''] + ['zone-'+str(ID)+'-'+t	for ID in self.zonewise_budgets	for ag_or_non_ag in ['agricultural', 'non-agricultural', 'zone']	for t in self.zonewise_budgets[ID][ag_or_non_ag]])
		writer.writerow(['Rainfall'] + [rain_sum	for ID in self.zonewise_budgets	for ag_or_non_ag in ['agricultural', 'non-agricultural', 'zone']	for t in self.zonewise_budgets[ID][ag_or_non_ag]])
		writer.writerow(['Runoff in Monsoon'] + [self.zonewise_budgets[ID][ag_or_non_ag][t].runoff_monsoon_end	for ID in self.zonewise_budgets	for ag_or_non_ag in ['agricultural', 'non-agricultural', 'zone']	for t in self.zonewise_budgets[ID][ag_or_non_ag]])
		writer.writerow(['Infiltration in Monsoon'] + [self.zonewise_budgets[ID][ag_or_non_ag][t].infil_monsoon_end	for ID in self.zonewise_budgets	for ag_or_non_ag in ['agricultural', 'non-agricultural', 'zone']	for t in self.zonewise_budgets[ID][ag_or_non_ag]])
		writer.writerow(['Soil Moisture Crop end'] + [self.zonewise_budgets[ID][ag_or_non_ag][t].sm_crop_end	for ID in self.zonewise_budgets	for ag_or_non_ag in ['agricultural', 'non-agricultural', 'zone']	for t in self.zonewise_budgets[ID][ag_or_non_ag]])
		writer.writerow(['GW Recharge in Monsoon'] + [self.zonewise_budgets[ID][ag_or_non_ag][t].GW_rech_monsoon_end	for ID in self.zonewise_budgets	for ag_or_non_ag in ['agricultural', 'non-agricultural', 'zone']	for t in self.zonewise_budgets[ID][ag_or_non_ag]])
		writer.writerow(['AET'] + [self.zonewise_budgets[ID][ag_or_non_ag][t].AET_crop_end	for ID in self.zonewise_budgets	for ag_or_non_ag in ['agricultural', 'non-agricultural', 'zone']	for t in self.zonewise_budgets[ID][ag_or_non_ag]])
		writer.writerow(['PET'] + [PET_sum_cropend	for ID in self.zonewise_budgets	for ag_or_non_ag in ['agricultural', 'non-agricultural', 'zone']	for t in self.zonewise_budgets[ID][ag_or_non_ag]])
		writer.writerow(['Monsoon Deficit(PET-AET)'] + [self.zonewise_budgets[ID][ag_or_non_ag][t].PET_minus_AET_monsoon_end	for ID in self.zonewise_budgets		for ID in self.zonewise_budgets	for ag_or_non_ag in ['agricultural', 'non-agricultural', 'zone']	for t in self.zonewise_budgets[ID][ag_or_non_ag]])
		writer.writerow(['Post Monsoon Deficit(PET-AET)'] + [self.zonewise_budgets[ID][ag_or_non_ag][t].PET_minus_AET_post_monsoon	for ID in self.zonewise_budgets		for ID in self.zonewise_budgets	for ag_or_non_ag in ['agricultural', 'non-agricultural', 'zone']	for t in self.zonewise_budgets[ID][ag_or_non_ag]])
		csvwrite.close()
	
	def compute_and_output_cadestral_vulnerability_to_csv(self, cadestral_vulnerability_csv_filename):
		plot_vulnerability_dict = {
			p.container_polygons[CADESTRAL_LABEL].id(): p.budget.PET_minus_AET_crop_end
				for p in self.output_cadestral_points
		}
		sorted_keys = sorted(plot_vulnerability_dict.keys(), key=lambda ID:	plot_vulnerability_dict[ID], reverse=True)
		csvwrite = open(self.path + cadestral_vulnerability_csv_filename,'w+b')
		writer = csv.writer(csvwrite)
		writer.writerow(['Plot ID', 'Vulnerability', 'Deficit Waterings'])
		for key in sorted_keys:	writer.writerow([key, '{0:.2f}'.format(plot_vulnerability_dict[key]), round((plot_vulnerability_dict[key])/50)])
		csvwrite.close()
	
	def calculate(self, 
					crop_name,
					pointwise_output_csv_filename,
					zonewise_budget_csv_filename,
					cadestral_vulnerability_csv_filename,
					start_date_index=0,
					end_date_index=182,
					input_points_filename=None
				):
		
		start_time = time.time()
		
		PET,crop_end_index = self.pet_calculation(crop_name.lower())
		PET_sum = sum(PET[start_date_index:end_date_index+1])
		PET_sum_cropend=sum(PET[start_date_index:crop_end_index+1])
		rain_sum = sum(self.rain[start_date_index:end_date_index+1])
		
		self.soil_types = dict_SoilContent.keys();	self.soil_types.remove('soil type')
		self.lulc_types = dict_RO.keys()
		
		self.output_grid_points = self.generate_output_points_grid(input_points_filename)
		self.filter_out_points_outside_boundary()
		self.set_container_polygon_of_points_for_layers(self.output_grid_points, [self.soil_layer, self.lulc_layer])
		self.output_grid_points = filter(lambda p:	dict_lulc[p.container_polygons[LULC_LABEL][Desc].lower()] != 'water', self.output_grid_points)
		print 'Number of grid points to process : ', len(self.output_grid_points)
		for zone_id in self.zone_points_dict:
			self.zone_points_dict[zone_id] = filter(lambda p:	dict_lulc[p.container_polygons[LULC_LABEL][Desc].lower()] != 'water', self.zone_points_dict[zone_id])
		self.set_slope_at_points(self.output_grid_points)
		self.set_crop_at_points(self.output_grid_points,crop_name)
		for point in self.output_grid_points:
			point.run_model(self.rain, PET, PET_sum, PET_sum_cropend, start_date_index, end_date_index,crop_end_index)
		self.output_point_results_to_csv(pointwise_output_csv_filename)
		self.compute_zonewise_budget()
		self.output_zonewise_budget_to_csv(zonewise_budget_csv_filename, PET_sum_cropend, rain_sum)
		
		self.filter_out_cadestral_plots_outside_boundary()
		#~ self.cadestral_points_dict, 
		self.output_cadestral_points = self.generate_output_points_for_cadestral_plots()
		self.set_container_polygon_of_points_for_layers(self.output_cadestral_points, [self.soil_layer, self.lulc_layer])
		self.output_cadestral_points = filter(lambda p:	dict_lulc[p.container_polygons[LULC_LABEL][Desc].lower()] != 'water', self.output_cadestral_points)
		print 'Number of cadestral points to process : ', len(self.output_cadestral_points)
		self.set_slope_at_points(self.output_cadestral_points)
		self.set_crop_at_points(self.output_cadestral_points,crop_name)
		for point in self.output_cadestral_points:
			point.run_model(self.rain, PET, PET_sum, PET_sum_cropend, start_date_index, end_date_index,crop_end_index)
		self.compute_and_output_cadestral_vulnerability_to_csv(cadestral_vulnerability_csv_filename)
		
		print("--- %s seconds ---" % (time.time() - start_time))
		print("done")
