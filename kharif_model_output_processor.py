import csv
import itertools
from collections import OrderedDict
import numpy as np
from constants_dicts_lookups import *
from kharif_model_calculator import *

class KharifModelOutputProcessor:
	
	def output_point_results_to_csv(self, output_grid_points, pointwise_output_csv_filepath, crops):
		"""
		#~ <all_crops> includes actual (selected) crops and also pseudo-crops
		"""
		parameters = ['PET-AET', 'Soil Moisture', 'Infiltration', 'Runoff', 'GW Recharge']
		csvwrite = open(pointwise_output_csv_filepath,'w+b')
		writer = csv.writer(csvwrite)
		writer.writerow(['X', 'Y'] + [crops[i]+'-'+parameter+'-'+duration for i in range(len(crops)) for parameter in parameters for duration in ['Monsoon end', 'Crop end']] + ['Vegetation-'+parameter+'-'+duration for parameter in parameters for duration in ['Monsoon end', 'Crop end']])
		for point in output_grid_points:
			#~ if not point.zone_polygon:	continue
			if point.lulc_type in ['agriculture', 'fallow land']:
				writer.writerow([point.qgsPoint.x(), point.qgsPoint.y()] + 
								list(itertools.chain(*[
									[
									point.budget.runoff_monsoon_end[i], point.budget.runoff_crop_end[i],
									point.budget.sm_monsoon_end[i], point.budget.sm_crop_end[i],
									point.budget.infil_monsoon_end[i], point.budget.infil_crop_end[i],
									point.budget.PET_minus_AET_monsoon_end[i], point.budget.PET_minus_AET_crop_end[i],
									point.budget.GW_rech_monsoon_end[i], point.budget.GW_rech_crop_end[i]
									]
										for i in range(len(crops))
								])) +
								['']*10
							)
			else:
				writer.writerow([point.qgsPoint.x(), point.qgsPoint.y()] + 
								['']*(10*len(crops)) +
								[
									point.budget.runoff_monsoon_end[0], point.budget.runoff_crop_end[0],
									point.budget.sm_monsoon_end[0], point.budget.sm_crop_end[0],
									point.budget.infil_monsoon_end[0], point.budget.infil_crop_end[0],
									point.budget.PET_minus_AET_monsoon_end[0], point.budget.PET_minus_AET_crop_end[0],
									point.budget.GW_rech_monsoon_end[0], point.budget.GW_rech_crop_end[0]
								]
							)
		csvwrite.close()
	
	def compute_zonewise_budget(self, zone_points_dict):
		zonewise_budgets = OrderedDict()
		for zone_id in zone_points_dict:
			zone_points = zone_points_dict[zone_id]
			no_of_zone_points = len(zone_points)
			if no_of_zone_points == 0:	continue
			
			zonewise_budgets[zone_id] = {}
			
			all_agricultural_points = filter(lambda p:	p.lulc_type in ['agriculture', 'fallow land'], zone_points)
			non_agricultural_points_dict = {lulc_type: filter(lambda p:	p.lulc_type == lulc_type, zone_points)	for lulc_type in dict_LULC_pseudo_crop}
			
			no_of_agricultural_points = len(all_agricultural_points)
			zb = zonewise_budgets[zone_id]['agricultural'] = Budget()
			zb.runoff_monsoon_end = np.sum([p.budget.runoff_monsoon_end	for p in all_agricultural_points], 0) / no_of_agricultural_points
			zb.sm_crop_end = np.sum([p.budget.sm_crop_end	for p in all_agricultural_points], 0) / no_of_agricultural_points
			zb.infil_monsoon_end = np.sum([p.budget.infil_monsoon_end	for p in all_agricultural_points], 0) / no_of_agricultural_points
			zb.AET_crop_end = np.sum([p.budget.AET_crop_end	for p in all_agricultural_points], 0) / no_of_agricultural_points
			zb.GW_rech_monsoon_end = np.sum([p.budget.GW_rech_monsoon_end	for p in all_agricultural_points], 0) / no_of_agricultural_points
			zb.PET_minus_AET_monsoon_end = np.sum([p.budget.PET_minus_AET_monsoon_end	for p in all_agricultural_points], 0) / no_of_agricultural_points
			zb.PET_minus_AET_crop_end = np.sum([p.budget.PET_minus_AET_crop_end	for p in all_agricultural_points], 0) / no_of_agricultural_points
			
			no_of_non_ag_lulc_type_points = {}
			for lulc_type in non_agricultural_points_dict:
				lulc_type_points = non_agricultural_points_dict[lulc_type]
				no_of_non_ag_lulc_type_points[lulc_type] = len(lulc_type_points)
				if no_of_non_ag_lulc_type_points[lulc_type] == 0:	continue
				
				zb = zonewise_budgets[zone_id][lulc_type] = Budget()
				zb.sm_crop_end = np.sum([p.budget.sm_crop_end	for p in lulc_type_points], 0) / no_of_non_ag_lulc_type_points[lulc_type]
				zb.runoff_monsoon_end = np.sum([p.budget.runoff_monsoon_end	for p in lulc_type_points], 0) / no_of_non_ag_lulc_type_points[lulc_type]
				zb.infil_monsoon_end = np.sum([p.budget.infil_monsoon_end	for p in lulc_type_points], 0) / no_of_non_ag_lulc_type_points[lulc_type]
				zb.AET_crop_end = np.sum([p.budget.AET_crop_end	for p in lulc_type_points], 0) / no_of_non_ag_lulc_type_points[lulc_type]
				zb.GW_rech_monsoon_end = np.sum([p.budget.GW_rech_monsoon_end	for p in lulc_type_points], 0) / no_of_non_ag_lulc_type_points[lulc_type]
				zb.PET_minus_AET_monsoon_end = np.sum([p.budget.PET_minus_AET_monsoon_end	for p in lulc_type_points], 0) / no_of_non_ag_lulc_type_points[lulc_type]
				zb.PET_minus_AET_crop_end = np.sum([p.budget.PET_minus_AET_crop_end	for p in lulc_type_points], 0) / no_of_non_ag_lulc_type_points[lulc_type]
			
			#~ zb = Budget()
			#~ zb.sm_crop_end = sum([p.budget.sm_crop_end	for p in zone_points]) / no_of_zone_points
			#~ zb.runoff_monsoon_end = sum([p.budget.runoff_monsoon_end	for p in zone_points]) / no_of_zone_points
			#~ zb.infil_monsoon_end = sum([p.budget.infil_monsoon_end	for p in zone_points]) / no_of_zone_points
			#~ zb.AET_crop_end = sum([p.budget.AET_crop_end	for p in zone_points]) / no_of_zone_points
			#~ zb.GW_rech_monsoon_end = sum([p.budget.GW_rech_monsoon_end	for p in zone_points]) / no_of_zone_points
			#~ zb.PET_minus_AET_monsoon_end = sum([p.budget.PET_minus_AET_monsoon_end	for p in zone_points]) / no_of_zone_points
			#~ zb.PET_minus_AET_crop_end = sum([p.budget.PET_minus_AET_crop_end	for p in zone_points]) / no_of_zone_points
			#~ zonewise_budgets[zone_id]['zone'] = {'overall':zb}  # dict {'overall':zb} assigned instead of simple zb for convenience in iterating with ag and non-ag
			
			return zonewise_budgets
	
	def output_zonewise_budget_to_csv(self, zonewise_budgets, crops, pseudo_crops, zonewise_budget_csv_filepath, rain_sum):
		csvwrite = open(zonewise_budget_csv_filepath,'wb')
		writer = csv.writer(csvwrite)
		writer.writerow(['']
			+ ['zone-'+str(ID)+'-'+crop.name	for ID in zonewise_budgets	for crop in crops]
			+ ['zone-'+str(ID)+'-'+pseudo_crop.name	for ID in zonewise_budgets	for pseudo_crop in pseudo_crops if pseudo_crop.name in zonewise_budgets[ID]]
		)
		writer.writerow(['Rainfall']
			+ [rain_sum	for ID in zonewise_budgets	for i in range(len(crops))]
			+ [rain_sum	for ID in zonewise_budgets	for pseudo_crop in pseudo_crops if pseudo_crop.name in zonewise_budgets[ID]]
		)
		writer.writerow(['Runoff in Monsoon']
			+ [zonewise_budgets[ID]['agricultural'].runoff_monsoon_end[i]	for ID in zonewise_budgets	for i in range(len(crops))]
			+ [zonewise_budgets[ID][pseudo_crop.name].runoff_monsoon_end[0]	for ID in zonewise_budgets	for pseudo_crop in pseudo_crops if pseudo_crop.name in zonewise_budgets[ID]]
		)
		writer.writerow(['Infiltration in Monsoon']
			+ [zonewise_budgets[ID]['agricultural'].infil_monsoon_end[i]	for ID in zonewise_budgets	for i in range(len(crops))]
			+ [zonewise_budgets[ID][pseudo_crop.name].infil_monsoon_end[0]	for ID in zonewise_budgets	for pseudo_crop in pseudo_crops if pseudo_crop.name in zonewise_budgets[ID]]
		)
		writer.writerow(['Soil Moisture Crop end']
			+ [zonewise_budgets[ID]['agricultural'].sm_crop_end[i]	for ID in zonewise_budgets	for i in range(len(crops))]
			+ [zonewise_budgets[ID][pseudo_crop.name].sm_crop_end[0]	for ID in zonewise_budgets	for pseudo_crop in pseudo_crops if pseudo_crop.name in zonewise_budgets[ID]]
		)
		writer.writerow(['GW Recharge in Monsoon']
			+ [zonewise_budgets[ID]['agricultural'].GW_rech_monsoon_end[i]	for ID in zonewise_budgets	for i in range(len(crops))]
			+ [zonewise_budgets[ID][pseudo_crop.name].GW_rech_monsoon_end[0]	for ID in zonewise_budgets	for pseudo_crop in pseudo_crops if pseudo_crop.name in zonewise_budgets[ID]]
		)
		writer.writerow(['AET']
			+ [zonewise_budgets[ID]['agricultural'].AET_crop_end[i]	for ID in zonewise_budgets	for i in range(len(crops))]
			+ [zonewise_budgets[ID][pseudo_crop.name].AET_crop_end[0]	for ID in zonewise_budgets	for pseudo_crop in pseudo_crops if pseudo_crop.name in zonewise_budgets[ID]]
		)
		writer.writerow(['PET']
			+ [crop.PET_sum_cropend	for ID in zonewise_budgets	for crop in crops]
			+ [pseudo_crop.PET_sum_cropend	for ID in zonewise_budgets	for pseudo_crop in pseudo_crops if pseudo_crop.name in zonewise_budgets[ID]]
		)
		writer.writerow(['Monsoon Deficit(PET-AET)']
			+ [zonewise_budgets[ID]['agricultural'].PET_minus_AET_monsoon_end[i]	for ID in zonewise_budgets	for i in range(len(crops))]
			+ [zonewise_budgets[ID][pseudo_crop.name].PET_minus_AET_monsoon_end[0]	for ID in zonewise_budgets	for pseudo_crop in pseudo_crops if pseudo_crop.name in zonewise_budgets[ID]]
		)
		writer.writerow(['Crop duration Deficit(PET-AET)']
			+ [zonewise_budgets[ID]['agricultural'].PET_minus_AET_crop_end[i]	for ID in zonewise_budgets	for i in range(len(crops))]
			+ [zonewise_budgets[ID][pseudo_crop.name].PET_minus_AET_crop_end[0]	for ID in zonewise_budgets	for pseudo_crop in pseudo_crops if pseudo_crop.name in zonewise_budgets[ID]]
		)
		csvwrite.close()
	
	def render_and_save_pointwise_output_layer(self,
												pointwise_output_csv_filepath, 
												output_layer_name, 
												on_values_of_attribute, 
												graduated_rendering_interval_points,
												shapefile_path=''
											):
		
		uri = 'file:///' + pointwise_output_csv_filepath + \
			'?delimiter=%s&crs=epsg:32643&xField=%s&yField=%s' % (',', 'X', 'Y')
		output_layer = QgsVectorLayer(uri, output_layer_name, 'delimitedtext')
		
		if 'Crop' in on_values_of_attribute:
			ET_D_max = max([point.budget.PET_minus_AET_crop_end	for point in model_calculator.output_grid_points])
		elif 'Monsoon' in on_values_of_attribute:
			ET_D_max = max([point.budget.PET_minus_AET_monsoon_end	for point in model_calculator.output_grid_points])
		
		graduated_symbol_renderer_range_list = []
		opacity = 1
		intervals_count = len(graduated_rendering_interval_points)
		for i in range(intervals_count):
			interval_min = 0 if graduated_rendering_interval_points[i] == 0 else (graduated_rendering_interval_points[i]*ET_D_max/100.0 + 0.01)
			interval_max = (graduated_rendering_interval_points*ET_D_max/100.0)
			label = "{0:.2f} - {1:.2f}".format(interval_min, interval_max)
			colour = QColor(int(255*(1-(i+1.0)/(intervals_count+1.0))), 0, 0)	# +1 done to tackle boundary cases
			symbol = QgsSymbolV2.defaultSymbol(output_layer.geometryType())
			symbol.setColor(colour)
			symbol.setAlpha(opacity)
			interval_range = QgsRendererRangeV2(interval_min, interval_max, symbol, label)
			graduated_symbol_renderer_range_list.append(interval_range)
		renderer = QgsGraduatedSymbolRendererV2('', graduated_symbol_renderer_range_list)
		renderer.setMode(QgsGraduatedSymbolRendererV2.EqualInterval)
		renderer.setClassAttribute(on_values_of_attribute)
		output_layer.setRendererV2(renderer)
		QgsMapLayerRegistry.instance().addMapLayer(output_layer)
		
		if shapefile_path != '':
			QgsVectorFileWriter.writeAsVectorFormat(output_layer, shapefile_path, "utf-8", None, "ESRI Shapefile")
		
		return output_layer
