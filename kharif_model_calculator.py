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
import numpy as np
from collections import OrderedDict
from configuration import *
from constants_dicts_lookups import *


BOUNDARY_LABEL = 'Zones'
SOIL_LABEL = 'Soil'
LULC_LABEL = 'Land-Use-Land-Cover'
SLOPE_LABEL = 'Slope'
CADASTRAL_LABEL = 'Cadastral'
class Budget:
	
	def __init__(self):
		self.sm, self.runoff, self.infil, self.AET, self.GW_rech = [],[],[],[],[]
		
	def summarize(self, crops, start_date_index, end_date_index , monsoon_end_date_index):
		self.runoff = np.array(self.runoff)	
		self.infil = np.array(self.infil)
		self.AET = np.array(self.AET)
		self.GW_rech = np.array(self.GW_rech)
		self.sm = np.array(self.sm)
		self.sm_crop_end = np.array([self.sm[crops[i].end_date_index][i]	for i in range(len(crops))])
 		self.sm_monsoon_end = np.array([self.sm[monsoon_end_date_index][i]	for i in range(len(crops))])
		self.runoff_crop_end = [np.sum(self.runoff[start_date_index:crops[i].end_date_index+1,i])	for i in range(len(crops))]
		self.runoff_monsoon_end = [np.sum(self.runoff[start_date_index:monsoon_end_date_index+1,i])	for i in range(len(crops))]
		self.runoff_total = [np.sum(self.runoff[start_date_index:end_date_index+1,i])	for i in range(len(crops))]
		self.infil_crop_end = [np.sum(self.infil[start_date_index:crops[i].end_date_index+1,i])	for i in range(len(crops))]
		self.infil_monsoon_end = [np.sum(self.infil[start_date_index:monsoon_end_date_index+1,i]) for i in range(len(crops))]
		self.AET_crop_end = [np.sum(self.AET[start_date_index:crops[i].end_date_index+1,i])	for i in range(len(crops))]
		self.AET_monsoon_end = [np.sum(self.AET[start_date_index:monsoon_end_date_index+1,i])	for i in range(len(crops))]
		self.GW_rech_crop_end = [np.sum(self.GW_rech[start_date_index:crops[i].end_date_index+1,i])	for i in range(len(crops))]
		self.GW_rech_monsoon_end = [np.sum(self.GW_rech[start_date_index:monsoon_end_date_index+1,i])	for i in range(len(crops))]
		self.GW_rech_total = [np.sum(self.GW_rech[start_date_index:end_date_index+1,i])	for i in range(len(crops))]
		self.PET_minus_AET_monsoon_end = np.array([crops[i].PET_sum_monsoon - self.AET_monsoon_end[i]	for i in range(len(crops))])
		self.PET_minus_AET_post_monsoon = np.array([(crops[i].PET_sum_cropend - self.AET_crop_end[i])-self.PET_minus_AET_monsoon_end[i]	for i in range(len(crops))])
		self.PET_minus_AET_crop_end = np.array([crops[i].PET_sum_cropend - self.AET_crop_end[i]		for i in range(len(crops))])
		# print self.GW_rech_monsoon_end
		# gwl=[float(k[0]) for k in self.GW_rech.tolist()]
		# ro =[float(k[0]) for k in self.runoff.tolist()]
		# ssm = [float(k[0]) for k in self.sm.tolist()]
		# infi = [float(k[0]) for k in self.infil.tolist()]
		# a = [float(k[0]) for k in self.AET.tolist()]
		# for j in range (0,150):
		# 	print (ssm[j],ro[j],infi[j],a[j],gwl[j])
		# print ssm
		# print monsoon_end_date_index, end_date_index
		# print self.sm_crop_end, self.sm_monsoon_end


class Crop:
	def __init__(self, name):
		self.name = name
		self.PET = [];	self.end_date_index = self.PET_sum_monsoon = self.PET_sum_cropend = None
	@property
	def root_depth(self):	return dict_crop[self.name][2] if self.name in dict_crop.keys() else dict_LULC_pseudo_crop[self.name][2]
	@property
	def KC(self):	return dict_crop[self.name][0] if self.name in dict_crop.keys() else dict_LULC_pseudo_crop[self.name][0]
	@property
	def depletion_factor(self):	return dict_crop[self.name][1] if self.name in dict_crop.keys() else dict_LULC_pseudo_crop[self.name][1]


class Point:
	
	def __init__(self, qgsPoint):
		self.qgsPoint = qgsPoint
		self.container_polygons = {}
		self.slope = None
		self.budget = Budget()
	
	@property
	def zone_polygon(self):	return self.container_polygons[BOUNDARY_LABEL]
	@property
	def soil_polygon(self):	return self.container_polygons[SOIL_LABEL]
	@property
	def lulc_polygon(self):	return self.container_polygons[LULC_LABEL]
	@property
	def cadastral_polygon(self):	return self.container_polygons[CADASTRAL_LABEL]
	@property
	def texture(self):
		try:
			return self.soil_polygon[TEX].lower()
		except Exception:
			print self.qgsPoint.x(), self.qgsPoint.y()

	@property
	def depth_value(self):	return dict_SoilDep[self.soil_polygon[Depth].lower()]
	@property
	def Ksat(self):	return dict_SoilDep[self.soil_polygon[Depth].lower()]
	@property
	def Sat(self):	return dict_SoilProperties[self.texture][6]
	@property
	def WP(self):	return dict_SoilProperties[self.texture][4]
	@property
	def FC(self):	return dict_SoilProperties[self.texture][5]
	@property
	def lulc_type(self):	return dict_lulc[self.lulc_polygon[Desc].lower()]
	@property
	def HSG(self):	return dict_SoilProperties[self.texture][0]
	@property
	def cn_val(self):	return dict_RO[self.lulc_type][self.HSG]
	
	@zone_polygon.setter
	def zone_polygon(self, polygon):	self.container_polygons[BOUNDARY_LABEL] = polygon
	@soil_polygon.setter
	def soil_polygon(self, polygon):	self.container_polygons[SOIL_LABEL] = polygon
	@lulc_polygon.setter
	def lulc_polygon(self, polygon):	self.container_polygons[LULC_LABEL] = polygon
	@cadastral_polygon.setter
	def cadastral_polygon(self, polygon):	self.container_polygons[CADASTRAL_LABEL] = polygon
	
	def run_model(self, rain, crops, start_date_index, end_date_index, monsoon_end_date_index):
		
		self.setup_for_daily_computations(crops)
		
		self.SM1_fraction = self.layer2_moisture = self.WP
		
		for day in range (start_date_index, end_date_index+1):
			self.primary_runoff(day, rain)
			self.aet(day, crops)
			self.percolation_below_root_zone(day)
			self.secondary_runoff(day)
			self.percolation_to_GW(day)

		self.budget.summarize(crops, start_date_index, end_date_index, monsoon_end_date_index)
		self.budget.sm_crop_end -= self.WP_depth	# requirement expressed by users
		self.budget.sm_monsoon_end -= self.WP_depth	# requirement expressed by users
	
	def setup_for_daily_computations(self, crops):
		"""
		"""
		Sat_depth = self.Sat * self.depth_value * 1000
		self.WP_depth = self.WP * self.depth_value * 1000
		FC_depth = self.FC * self.depth_value * 1000
		
		root_depths = np.array([crop.root_depth	for crop in crops])
		self.SM1 = np.where(self.depth_value <= root_depths, self.depth_value - 0.01, root_depths)
		self.SM2 = np.where(self.depth_value <= root_depths, 0.01, self.depth_value - root_depths)
		
		cn_s = cn_val = self.cn_val
		cn3 = cn_s *np.exp(0.00673*(100-cn_s))
		if (self.slope > 5.0):
			cn_s = (((cn3-cn_val)/3)*(1-2*np.exp(-13.86*self.slope * 0.01))) + cn_val
		cn1_s = cn_s - 20*(100-cn_s)/(100-cn_s+np.exp(2.533-0.0636*(100-cn_s)))
		cn3_s = cn_s *np.exp(0.00673*(100-cn_s))
		
		self.Smax = 25.4 * (1000/cn1_s - 10)
		S3 = 25.4 * (1000/cn3_s - 10)
		self.W2 = (np.log((FC_depth- self.WP_depth)/(1-S3/self.Smax) - (FC_depth - self.WP_depth )) - np.log ((Sat_depth - self.WP_depth)/(1-2.54/self.Smax) - (Sat_depth - self.WP_depth)))/((Sat_depth- self.WP_depth) - (FC_depth - self.WP_depth))
		self.W1 = np.log((FC_depth- self.WP_depth)/(1- S3/self.Smax) - (FC_depth - self.WP_depth)) + self.W2 * (FC_depth -self.WP_depth)
		
		TT_perc = (Sat_depth- FC_depth)/self.Ksat	#SWAT equation 2:3.2.4
		self.daily_perc_factor = 1 - np.exp(-24 / TT_perc)	#SWAT equation 2:3.2.3
		
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
		S_swat = self.Smax*(1 - self.SW/(self.SW + np.exp(self.W1 - self.W2 * self.SW)))
		
		Cn_swat = 25400/(S_swat+254)
		Ia_swat = 0.2 * S_swat
		self.budget.runoff.append(	np.where(rain[day] > Ia_swat,
											((rain[day]-Ia_swat)**2)/(rain[day] + 0.8*S_swat),
											0
									)	)
		self.budget.infil.append(rain[day] - self.budget.runoff[day])
	
	def aet(self, day, crops):
		"""
		Water Stress Coefficient 'KS' using FAO Irrigation and Drainage Paper 56, page 167 and
			page 169 equation 84
		Actual Evapotranspiration 'AET' using FAO Irrigation and Drainage Paper 56, page 6 and 
			page 161 equation 81
		"""
		depletion_factors = np.array([crop.depletion_factor	for crop in crops])
		KS = np.where(self.SM1_fraction < self.WP, 0,
						np.where(self.SM1_fraction > (self.FC *(1- depletion_factors) + depletion_factors * self.WP), 1,
							(self.SM1_fraction - self.WP)/(self.FC - self.WP) /(1- depletion_factors)
							)
						)
		PETs = np.array([crop.PET[day]	if day <= crop.end_date_index	else 0	for crop in crops])
		self.budget.AET.append( KS * PETs )
	
	def percolation_below_root_zone(self, day):
		"""
		Calculate soil moisture (fraction) 'SM1_before' as the one after infiltration and (then) AET occur,
		but before percolation starts below root-zone. Percolation below root-zone starts only if
		'SM1_before' is more than field capacity and the soil below root-zone is not saturated,i.e.
		'layer2_moisture' is less than saturation. When precolation occurs it is derived as
		the minimum of the maximum possible percolation (using SWAT equation 2:3.2.3) and
		the amount available in the root-zone for percolation.
		"""
		self.SM1_before = (self.SM1_fraction*self.SM1 +((self.budget.infil[day]-self.budget.AET[day])/1000))/self.SM1
		#~ print np.logical_or(self.SM1_before < self.FC, self.layer2_moisture < self.Sat)
		#~ print np.minimum((self.Sat - self.layer2_moisture) * self.SM2 * 1000,
										 #~ (self.SM1_before - self.FC) * self.SM1 * 1000 * self.daily_perc_factor)
		self.R_to_second_layer = np.where(self.SM1_before < self.FC, 0,
									np.where(self.layer2_moisture < self.Sat,
									np.minimum((self.Sat - self.layer2_moisture) * self.SM2 * 1000,
										 (self.SM1_before - self.FC) * self.SM1 * 1000 * self.daily_perc_factor),
										0
									 ))
		self.SM2_before = (self.layer2_moisture*self.SM2*1000 + self.R_to_second_layer)/self.SM2/1000
	
	def secondary_runoff(self, day):
		"""
		
		"""
		sec_run_off = np.where(
							((self.SM1_before*self.SM1 - self.R_to_second_layer/1000)/self.SM1) > self.Sat,
							(((self.SM1_before*self.SM1 - self.R_to_second_layer/1000)/self.SM1) - self.Sat) * self.SM1 * 1000,
							0
							)
		self.SM1_fraction = np.minimum((self.SM1_before*self.SM1*1000 - self.R_to_second_layer)/self.SM1/1000,self.Sat)
	
	def percolation_to_GW(self, day):
		"""
		
		"""
		self.budget.GW_rech.append(np.maximum((self.SM2_before - self.FC)*self.SM2*self.daily_perc_factor*1000,0))
		self.layer2_moisture = np.minimum(((self.SM2_before*self.SM2*1000- self.budget.GW_rech[day])/self.SM2/1000),self.Sat)
	

class VectorLayer:
	
	def __init__(self, qgsLayer, name=''):
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
	
	def __init__(self, path, et0, zones_layer, soil_layer, lulc_layer, cadastral_layer, slope_layer):

		self.path = path

		self.zones_layer = VectorLayer(zones_layer, BOUNDARY_LABEL)
		self.soil_layer = VectorLayer(soil_layer, SOIL_LABEL)
		self.lulc_layer = VectorLayer(lulc_layer, LULC_LABEL)
		self.cadastral_layer = VectorLayer(cadastral_layer, CADASTRAL_LABEL)
		
		zone_polygon_ids = self.zones_layer.feature_dict.keys()
		self.zone_points_dict = dict(zip(zone_polygon_ids, [[]	for i in range(len(zone_polygon_ids))]))
		cadastral_polygon_ids = self.cadastral_layer.feature_dict.keys()
		
		self.slope_layer = slope_layer
		
		self.et0 = et0
		assert et0 is not None
	
	@property
	def soil_types(self):	sts = dict_SoilProperties.keys();	sts.remove('soil type');	return sts
	@property
	def lulc_types(self):	return dict_RO.keys()
		
	def set_PET_and_end_date_index_of_crops(self, et0, sowing_threshold):
		def compute_sowing_index():
			rain_sum = 0
			for i in range (0,len(self.rain)):
				if (rain_sum < sowing_threshold):	rain_sum += self.rain[i]
				else :								break
			return i
		pre_sowing_kc = [0]*compute_sowing_index()
		PETs = {}
		for crop in self.crops + self.LULC_pseudo_crops.values():
			kc = (pre_sowing_kc if crop in self.crops else []) + crop.KC
			crop.end_date_index = len(kc) - 1
			kc = kc + [0]*(365-len(kc))
			self.rain = self.rain + [0]*(365-len(self.rain))
			kc = kc[0:365]
			crop.PET = np.array(et0[0:len(kc)]) * np.array(kc)
		
	def generate_output_points_grid(self):
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
				 
		# x_List = [749019.848090772]
		# y_List = [2262579.4183734786]
		x_List = [x for x in frange(xminB,xmaxB,STEP)]
		y_List = [x for x in frange(yminB,ymaxB,STEP)]
		print len(x_List), len (y_List)
		output_points = [Point(QgsPoint(x,y))	for x in x_List	for y in y_List]
		return output_points
	
	def filter_out_points_outside_boundary(self):
		filtered_points = []
		for point in self.output_grid_points:
			polygon = self.zones_layer.get_polygon_containing_point(point)
			if polygon is not None:
				point.zone_polygon = polygon
				self.zone_points_dict[polygon.id()].append(point)
				filtered_points.append(point)
		self.output_grid_points = filtered_points
	
	def filter_out_cadastral_plots_outside_boundary(self):
		#~ QgsGeometryAnalyzer().dissolve(self.zones_layer.qgsLayer, 'temp.shp')
		#~ dissolved_zones_layer = QgsVectorLayer('temp.shp', 'dissolved boundary', 'ogr')
		filtered_feature_dict = {}
		for polygon_id in self.cadastral_layer.feature_dict:
			for feature in self.zones_layer.qgsLayer.getFeatures():
				if self.cadastral_layer.feature_dict[polygon_id].geometry().intersects(feature.geometry()):
					filtered_feature_dict[polygon_id] = self.cadastral_layer.feature_dict[polygon_id]
					break
		self.cadastral_layer.feature_dict = filtered_feature_dict
	
	def generate_output_points_for_cadastral_plots(self):
		output_cadastral_points = []
		for polygon_id in self.cadastral_layer.feature_dict:
			qgsPoint = self.cadastral_layer.feature_dict[polygon_id].geometry().centroid().asPoint()
			polygon_geom = self.cadastral_layer.feature_dict[polygon_id].geometry()
			if polygon_geom.contains(qgsPoint):
				point = Point(qgsPoint)
			else:
				for feature in self.zones_layer.qgsLayer.getFeatures():
					if polygon_geom.intersects(feature.geometry()):
						polygon_intersection_some_zone = polygon_geom.intersection(feature.geometry())
						point = Point(polygon_intersection_some_zone.pointOnSurface().asPoint())
						break
			point.cadastral_polygon = self.cadastral_layer.feature_dict[polygon_id]
			output_cadastral_points.append(point)
		return output_cadastral_points
	
	def set_container_polygon_of_points_for_layers(self, points, polygon_vector_layers):
		for layer in polygon_vector_layers:
			for p in points:
				p.container_polygons[layer.name] = layer.get_polygon_containing_point(p)
	
	def set_slope_at_points(self, points):
		for point in points:
			point.slope = self.slope_layer.dataProvider().identify(
							point.qgsPoint, QgsRaster.IdentifyFormatValue).results()[1]

	def filter_out_points_with_incomplete_data(self, points):
		log_file = open(os.path.join(self.path, 'log'), 'a')
		log_file.write(time.ctime(time.time()) + '\n')
		filtered_points = []
		for point in points:
			if (None not in [
				point.container_polygons[SOIL_LABEL],
				point.container_polygons[LULC_LABEL],
				point.slope
			]):
				filtered_points.append(point)
			else:
				if point.container_polygons[SOIL_LABEL] is None:
					log_file.write('Soil polygon could not be obtained for point at: x = '
								   + str(point.qgsPoint.x()) + ', y = ' + str(point.qgsPoint.y()))
				if point.container_polygons[LULC_LABEL] is None:
					log_file.write('LULC polygon could not be obtained for point at: x = '
								   + str(point.qgsPoint.x()) + ', y = ' + str(point.qgsPoint.y()))
				if point.slope is None:
					log_file.write('Slope could not be obtained for point at: x = '
								   + str(point.qgsPoint.x()) + ', y = ' + str(point.qgsPoint.y()))
		log_file.close()
		return filtered_points

	def calculate(self,
					rain,
					crop_names,
					sowing_threshold,
					start_date_index=START_DATE_INDEX,
					end_date_index=END_DATE_INDEX,
					monsoon_end_date_index = MONSOON_END_DATE_INDEX
				):
		
		start_time = time.time()
		
		self.rain = rain
		self.crops = [Crop(crop_name)	for crop_name in crop_names]
		self.LULC_pseudo_crops = {crop_name: Crop(crop_name)	for crop_name in dict_LULC_pseudo_crop}
		
		self.set_PET_and_end_date_index_of_crops(self.et0, sowing_threshold)
		for crop in self.crops:
			crop.PET_sum_monsoon = sum(crop.PET[start_date_index:monsoon_end_date_index+1])
			crop.PET_sum_cropend = sum(crop.PET[start_date_index:crop.end_date_index+1])
		for crop_name in self.LULC_pseudo_crops:
			crop = self.LULC_pseudo_crops[crop_name]
			crop.PET_sum_monsoon = sum(crop.PET[start_date_index:monsoon_end_date_index+1])
			crop.PET_sum_cropend = sum(crop.PET[start_date_index:crop.end_date_index+1])
		
		rain_sum = sum(self.rain[start_date_index:monsoon_end_date_index+1])
		#~ end_date_index = max(end_date_index, max([crop.end_date_index	for crop in self.crops]))
		
		self.output_grid_points = self.generate_output_points_grid()
		self.filter_out_points_outside_boundary()
		self.set_container_polygon_of_points_for_layers(self.output_grid_points, [self.soil_layer, self.lulc_layer, self.cadastral_layer])
		self.set_slope_at_points(self.output_grid_points)
		self.output_grid_points = self.filter_out_points_with_incomplete_data(self.output_grid_points)
		for zone_id in self.zone_points_dict:
			self.zone_points_dict[zone_id] = self.filter_out_points_with_incomplete_data(self.zone_points_dict[zone_id])
		self.output_grid_points = filter(lambda p:	p.lulc_type not in ['water','habitation'], self.output_grid_points)
		print 'Number of grid points to process : ', len(self.output_grid_points)
		for zone_id in self.zone_points_dict:
			self.zone_points_dict[zone_id] = filter(lambda p:	p.lulc_type not in ['water','habitation'], self.zone_points_dict[zone_id])
		count = 0
		for point in self.output_grid_points:
			count += 1
			if count % 100 == 0:	print count
			if point.lulc_type in ['agriculture', 'fallow land']:
				point.run_model(self.rain, self.crops, start_date_index, end_date_index, monsoon_end_date_index)
			else:
				point.run_model(self.rain, [self.LULC_pseudo_crops[point.lulc_type]], start_date_index, end_date_index, monsoon_end_date_index)
		
		self.filter_out_cadastral_plots_outside_boundary()
		self.output_cadastral_points = self.generate_output_points_for_cadastral_plots()
		self.set_container_polygon_of_points_for_layers(self.output_cadastral_points, [self.soil_layer, self.lulc_layer, self.cadastral_layer])
		self.set_slope_at_points(self.output_cadastral_points)
		self.output_cadastral_points = self.filter_out_points_with_incomplete_data(self.output_cadastral_points)
		self.output_cadastral_points = filter(lambda p:	p.lulc_type not in ['water','habitation'], self.output_cadastral_points)
		print 'Number of cadastral points to process : ', len(self.output_cadastral_points)
		count = 0
		for point in self.output_cadastral_points:
			count += 1
			if count % 20 == 0:	print count
			if point.lulc_type in ['agriculture', 'fallow land']:
				point.run_model(self.rain, self.crops, start_date_index, end_date_index, monsoon_end_date_index)
			else:
				point.run_model(self.rain, [self.LULC_pseudo_crops[point.lulc_type]], start_date_index, end_date_index, monsoon_end_date_index)
		print 'done'
		return
		
		print("--- %s seconds ---" % (time.time() - start_time))
		print("done")
