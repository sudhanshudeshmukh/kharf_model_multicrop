import csv
import itertools
from collections import OrderedDict
import numpy as np
from constants_dicts_lookups import *
from kharif_model_calculator import *
from qgis.core import QgsVectorLayer, QgsFeature, QgsField, QgsMapLayerRegistry, QgsSymbolV2, QgsRendererRangeV2, QgsGraduatedSymbolRendererV2, QgsVectorFileWriter

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
	
	def compute_zonewise_budget(self, zone_points_dict, zones_layer):
		zonewise_budgets = OrderedDict()
		self.zone_area_village =OrderedDict()
		for zone_id in zone_points_dict:
			zone_points = zone_points_dict[zone_id]
			no_of_zone_points = len(zone_points)
			if no_of_zone_points == 0:	continue
			
			if(zones_layer.qgsLayer.fieldNameIndex('Zone_name') != -1):
				zone_name = zones_layer.feature_dict[zone_id]['Zone_name']
			else:
				zone_name = zone_id
			zonewise_budgets[zone_name] = {}
			
			all_agricultural_points = filter(lambda p:	p.lulc_type in ['agriculture', 'fallow land'], zone_points)
			non_agricultural_points_dict = {lulc_type: filter(lambda p:	p.lulc_type == lulc_type, zone_points)	for lulc_type in dict_LULC_pseudo_crop}
			
			no_of_agricultural_points = len(all_agricultural_points)
			if (no_of_agricultural_points != 0):
				zb = zonewise_budgets[zone_name]['agricultural'] = Budget()
				zb.AET_crop_end = np.sum([p.budget.AET_crop_end	for p in all_agricultural_points], 0) / no_of_agricultural_points
				zb.AET_monsoon_end = np.sum([p.budget.AET_monsoon_end	for p in all_agricultural_points], 0) / no_of_agricultural_points
				zb.runoff_monsoon_end = np.sum([p.budget.runoff_monsoon_end	for p in all_agricultural_points], 0) / no_of_agricultural_points
				zb.runoff_crop_end = np.sum([p.budget.runoff_crop_end	for p in all_agricultural_points], 0) / no_of_agricultural_points
				zb.runoff_total = np.sum([p.budget.runoff_total	for p in all_agricultural_points], 0) / no_of_agricultural_points			
				zb.sm_monsoon_end = np.sum([p.budget.sm_monsoon_end	for p in all_agricultural_points], 0) / no_of_agricultural_points
				zb.sm_crop_end = np.sum([p.budget.sm_crop_end	for p in all_agricultural_points], 0) / no_of_agricultural_points
				zb.infil_monsoon_end = np.sum([p.budget.infil_monsoon_end	for p in all_agricultural_points], 0) / no_of_agricultural_points
				zb.AET_crop_end = np.sum([p.budget.AET_crop_end	for p in all_agricultural_points], 0) / no_of_agricultural_points
				zb.GW_rech_monsoon_end = np.sum([p.budget.GW_rech_monsoon_end	for p in all_agricultural_points], 0) / no_of_agricultural_points
				zb.GW_rech_crop_end = np.sum([p.budget.GW_rech_crop_end	for p in all_agricultural_points], 0) / no_of_agricultural_points
				zb.GW_rech_total = np.sum([p.budget.GW_rech_total	for p in all_agricultural_points], 0) / no_of_agricultural_points
				zb.PET_minus_AET_monsoon_end = np.sum([p.budget.PET_minus_AET_monsoon_end	for p in all_agricultural_points], 0) / no_of_agricultural_points
				zb.PET_minus_AET_crop_end = np.sum([p.budget.PET_minus_AET_crop_end	for p in all_agricultural_points], 0) / no_of_agricultural_points
			
			no_of_non_ag_lulc_type_points = {}
			for lulc_type in non_agricultural_points_dict:
				lulc_type_points = non_agricultural_points_dict[lulc_type]
				no_of_non_ag_lulc_type_points[lulc_type] = len(lulc_type_points)
				if no_of_non_ag_lulc_type_points[lulc_type] == 0:	continue

				zb = zonewise_budgets[zone_name][lulc_type] = Budget()
				zb.AET_monsoon_end = np.sum([p.budget.AET_monsoon_end	for p in lulc_type_points], 0) / no_of_non_ag_lulc_type_points[lulc_type]
				zb.AET_crop_end = np.sum([p.budget.AET_crop_end	for p in lulc_type_points], 0) / no_of_non_ag_lulc_type_points[lulc_type]
				zb.runoff_monsoon_end = np.sum([p.budget.runoff_monsoon_end	for p in lulc_type_points], 0) / no_of_non_ag_lulc_type_points[lulc_type]
				zb.runoff_crop_end = np.sum([p.budget.runoff_crop_end	for p in lulc_type_points], 0) / no_of_non_ag_lulc_type_points[lulc_type]
				zb.runoff_total = np.sum([p.budget.runoff_total	for p in lulc_type_points], 0) / no_of_non_ag_lulc_type_points[lulc_type]
				zb.sm_monsoon_end = np.sum([p.budget.sm_monsoon_end	for p in lulc_type_points], 0) / no_of_non_ag_lulc_type_points[lulc_type]
				zb.sm_crop_end = np.sum([p.budget.sm_crop_end	for p in lulc_type_points], 0) / no_of_non_ag_lulc_type_points[lulc_type]
				zb.infil_monsoon_end = np.sum([p.budget.infil_monsoon_end	for p in lulc_type_points], 0) / no_of_non_ag_lulc_type_points[lulc_type]				
				zb.GW_rech_monsoon_end = np.sum([p.budget.GW_rech_monsoon_end	for p in lulc_type_points], 0) / no_of_non_ag_lulc_type_points[lulc_type]
				zb.GW_rech_crop_end = np.sum([p.budget.GW_rech_crop_end	for p in lulc_type_points], 0) / no_of_non_ag_lulc_type_points[lulc_type]				
				zb.GW_rech_total = np.sum([p.budget.GW_rech_total	for p in lulc_type_points], 0) / no_of_non_ag_lulc_type_points[lulc_type]				
				zb.PET_minus_AET_monsoon_end = np.sum([p.budget.PET_minus_AET_monsoon_end	for p in lulc_type_points], 0) / no_of_non_ag_lulc_type_points[lulc_type]
				zb.PET_minus_AET_crop_end = np.sum([p.budget.PET_minus_AET_crop_end	for p in lulc_type_points], 0) / no_of_non_ag_lulc_type_points[lulc_type]
			self.zone_area_village[zone_name] ={}
			self.zone_area_village[zone_name]['area'] = zones_layer.feature_dict[zone_id].geometry().area()/10000
			self.zone_area_village[zone_name]['code'] = zones_layer.feature_dict[zone_id]['UNICODE']



			#~ zb = Budget()
			#~ zb.sm_crop_end = sum([p.budget.sm_crop_end	for p in zone_points]) / no_of_zone_points
			#~ zb.runoff_monsoon_end = sum([p.budget.runoff_monsoon_end	for p in zone_points]) / no_of_zone_points
			#~ zb.infil_monsoon_end = sum([p.budget.infil_monsoon_end	for p in zone_points]) / no_of_zone_points
			#~ zb.AET_crop_end = sum([p.budget.AET_crop_end	for p in zone_points]) / no_of_zone_points
			#~ zb.GW_rech_monsoon_end = sum([p.budget.GW_rech_monsoon_end	for p in zone_points]) / no_of_zone_points
			#~ zb.PET_minus_AET_monsoon_end = sum([p.budget.PET_minus_AET_monsoon_end	for p in zone_points]) / no_of_zone_points
			#~ zb.PET_minus_AET_crop_end = sum([p.budget.PET_minus_AET_crop_end	for p in zone_points]) / no_of_zone_points
			#~ zonewise_budgets[zone_id]['zone'] = {'overall':zb}  # dict {'overall':zb} assigned instead of simple zb for convenience in iterating with ag and non-ag
		'''for i in zonewise_budgets:
			print (i)
			for j in  zonewise_budgets[i]:
				print (j)
				print vars(zonewise_budgets[i][j])
				print("###")
		print("---")'''
		return zonewise_budgets
	
	def output_zonewise_budget_to_csv(self, zonewise_budgets, crops, pseudo_crops, zonewise_budget_csv_filepath, rain_sum):
		csvwrite = open(zonewise_budget_csv_filepath,'wb')
		writer = csv.writer(csvwrite)
		rows =[]

		rows.append(['Village Name']
			+ [str(ID).rsplit('-',1)[0] for ID in zonewise_budgets	if 'agricultural' in zonewise_budgets[ID] for crop in crops]
			+ [str(ID).rsplit('-',1)[0] for ID in zonewise_budgets for pseudo_crop in pseudo_crops if pseudo_crop.name in zonewise_budgets[ID]]
			)

		rows.append(['Census Code']
			+ [self.zone_area_village[ID]['code']	for ID in zonewise_budgets	if 'agricultural' in zonewise_budgets[ID] for crop in crops]
			+ [self.zone_area_village[ID]['code']	for ID in zonewise_budgets	for pseudo_crop in pseudo_crops if pseudo_crop.name in zonewise_budgets[ID]]
		)

		rows.append(['Zone']
			+ ['zone-'+str(ID)	for ID in zonewise_budgets	if 'agricultural' in zonewise_budgets[ID] for crop in crops]
			+ ['zone-'+str(ID)	for ID in zonewise_budgets	for pseudo_crop in pseudo_crops if pseudo_crop.name in zonewise_budgets[ID]]
		)
		
		rows.append(['Zone Area (ha)']
			+ [self.zone_area_village[ID]['area']	for ID in zonewise_budgets	if 'agricultural' in zonewise_budgets[ID] for crop in crops]
			+ [self.zone_area_village[ID]['area']	for ID in zonewise_budgets	for pseudo_crop in pseudo_crops if pseudo_crop.name in zonewise_budgets[ID]]
		)
		
		rows.append(['Crops']
			+ [crop.name	for ID in zonewise_budgets	if 'agricultural' in zonewise_budgets[ID] for crop in crops]
			+ [pseudo_crop.name	for ID in zonewise_budgets	for pseudo_crop in pseudo_crops if pseudo_crop.name in zonewise_budgets[ID]]
		)

		rows.append(['Rainfall (mm)']
			+ [rain_sum	for ID in zonewise_budgets	if 'agricultural' in zonewise_budgets[ID] for i in range(len(crops))]
			+ [rain_sum for ID in zonewise_budgets	for pseudo_crop in pseudo_crops if pseudo_crop.name in zonewise_budgets[ID]]
		)
		
		rows.append(['PET Monsoon End']
			+ [crop.PET_sum_monsoon.item() for ID in zonewise_budgets if 'agricultural' in zonewise_budgets[ID]	for crop in crops]
			+ [pseudo_crop.PET_sum_monsoon.item() for ID in zonewise_budgets	for pseudo_crop in pseudo_crops if pseudo_crop.name in zonewise_budgets[ID]]
		)

		rows.append(['AET Monsoon End']
			+ [zonewise_budgets[ID]['agricultural'].AET_monsoon_end[i].item() for ID in zonewise_budgets if 'agricultural' in zonewise_budgets[ID]	for i in range(len(crops))]
			+ [zonewise_budgets[ID][pseudo_crop.name].AET_monsoon_end[0].item() for ID in zonewise_budgets	for pseudo_crop in pseudo_crops if pseudo_crop.name in zonewise_budgets[ID]]
		)

		rows.append(['Monsoon Deficit(PET-AET)']
			+ [zonewise_budgets[ID]['agricultural'].PET_minus_AET_monsoon_end[i].item()	for ID in zonewise_budgets	if 'agricultural' in zonewise_budgets[ID] for i in range(len(crops))]
			+ [zonewise_budgets[ID][pseudo_crop.name].PET_minus_AET_monsoon_end[0].item() for ID in zonewise_budgets	for pseudo_crop in pseudo_crops if pseudo_crop.name in zonewise_budgets[ID]]
		)
		rows.append(['GW Recharge in Monsoon']
			+ [zonewise_budgets[ID]['agricultural'].GW_rech_monsoon_end[i].item() for ID in zonewise_budgets if 'agricultural' in zonewise_budgets[ID] for i in range(len(crops))]
			+ [zonewise_budgets[ID][pseudo_crop.name].GW_rech_monsoon_end[0].item() for ID in zonewise_budgets for pseudo_crop in pseudo_crops if pseudo_crop.name in zonewise_budgets[ID]]
		)
		rows.append(['Runoff in Monsoon (mm)']
			+ [zonewise_budgets[ID]['agricultural'].runoff_monsoon_end[i].item() for ID in zonewise_budgets	if 'agricultural' in zonewise_budgets[ID] for i in range(len(crops))]
			+ [zonewise_budgets[ID][pseudo_crop.name].runoff_monsoon_end[0].item() for ID in zonewise_budgets for pseudo_crop in pseudo_crops if pseudo_crop.name in zonewise_budgets[ID]]
		)
		
		rows.append(['Soil Moisture Monsoon end']
			+ [zonewise_budgets[ID]['agricultural'].sm_monsoon_end[i].item()	for ID in zonewise_budgets if 'agricultural' in zonewise_budgets[ID] for i in range(len(crops))]
			+ [zonewise_budgets[ID][pseudo_crop.name].sm_monsoon_end[0].item()	for ID in zonewise_budgets for pseudo_crop in pseudo_crops if pseudo_crop.name in zonewise_budgets[ID]]
		)

		rows.append(['Post Monsoon PET']
			+ [crop.PET_sum_cropend.item() - crop.PET_sum_monsoon.item() for ID in zonewise_budgets	if 'agricultural' in zonewise_budgets[ID] for crop in crops]
			+ [pseudo_crop.PET_sum_cropend.item() - pseudo_crop.PET_sum_monsoon.item()	for ID in zonewise_budgets	for pseudo_crop in pseudo_crops if pseudo_crop.name in zonewise_budgets[ID]]
		)
		rows.append(['Infilitration in Monsoon (mm)']
			+ [zonewise_budgets[ID]['agricultural'].infil_monsoon_end[i].item() for ID in zonewise_budgets if 'agricultural' in zonewise_budgets[ID] for i in range(len(crops))]
			+ [zonewise_budgets[ID][pseudo_crop.name].infil_monsoon_end[0].item() for ID in zonewise_budgets	for pseudo_crop in pseudo_crops if pseudo_crop.name in zonewise_budgets[ID]]
		)


		rows.append(['Soil Moisture Crop end']
			+ [zonewise_budgets[ID]['agricultural'].sm_crop_end[i]	for ID in zonewise_budgets	if 'agricultural' in zonewise_budgets[ID] for i in range(len(crops))]
			+ [zonewise_budgets[ID][pseudo_crop.name].sm_crop_end[0]	for ID in zonewise_budgets	for pseudo_crop in pseudo_crops if pseudo_crop.name in zonewise_budgets[ID]]
		)

		rows.append(['AET Crop End']
			+ [zonewise_budgets[ID]['agricultural'].AET_crop_end[i]	for ID in zonewise_budgets	if 'agricultural' in zonewise_budgets[ID] for i in range(len(crops))]
			+ [zonewise_budgets[ID][pseudo_crop.name].AET_crop_end[0]	for ID in zonewise_budgets	for pseudo_crop in pseudo_crops if pseudo_crop.name in zonewise_budgets[ID]]
		)

		rows.append(['PET Crop End']
			+ [crop.PET_sum_cropend	for ID in zonewise_budgets	if 'agricultural' in zonewise_budgets[ID] for crop in crops]
			+ [pseudo_crop.PET_sum_cropend	for ID in zonewise_budgets	for pseudo_crop in pseudo_crops if pseudo_crop.name in zonewise_budgets[ID]]
		)
		
		rows.append(['Crop duration Deficit(PET-AET)']
			+ [zonewise_budgets[ID]['agricultural'].PET_minus_AET_crop_end[i]	for ID in zonewise_budgets if 'agricultural' in zonewise_budgets[ID] for i in range(len(crops))]
			+ [zonewise_budgets[ID][pseudo_crop.name].PET_minus_AET_crop_end[0]	for ID in zonewise_budgets	for pseudo_crop in pseudo_crops if pseudo_crop.name in zonewise_budgets[ID]]
		)

		rows.append(['Post Monsoon Ground Water']
			+ [zonewise_budgets[ID]['agricultural'].GW_rech_total[i] - zonewise_budgets[ID]['agricultural'].GW_rech_monsoon_end[i] for ID in zonewise_budgets if 'agricultural' in zonewise_budgets[ID] for i in range (len(crops))]
			+ [zonewise_budgets[ID][pseudo_crop.name].GW_rech_total[0] - zonewise_budgets[ID][pseudo_crop.name].GW_rech_monsoon_end[0] for ID in zonewise_budgets for pseudo_crop in pseudo_crops if pseudo_crop.name in zonewise_budgets[ID] ]
			)

		rows.append(['Post Monsoon Runoff']
			+ [zonewise_budgets[ID]['agricultural'].runoff_total[i] - zonewise_budgets[ID]['agricultural'].runoff_monsoon_end[i] for ID in zonewise_budgets if 'agricultural' in zonewise_budgets[ID] for i in range (len(crops))]
			+ [zonewise_budgets[ID][pseudo_crop.name].runoff_total[0] - zonewise_budgets[ID][pseudo_crop.name].runoff_monsoon_end[0] for ID in zonewise_budgets for pseudo_crop in pseudo_crops if pseudo_crop.name in zonewise_budgets[ID] ]
			)

		cols = zip(*rows)
		cols.sort(key =  lambda x: x[2])


		writer.writerows(cols)
		csvwrite.close()



		'''writer.writerow(['']
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
		)'''
	
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

	def compute_and_output_cadastral_vulnerability_to_csv(self, crop_names, output_cadastral_points, cadastral_vulnerability_csv_filepath):
		plot_vulnerability_dict = {
			p.cadastral_polygon.id():
				[
					(
						p.budget.PET_minus_AET_crop_end[i],
						p.budget.PET_minus_AET_monsoon_end[i]
					)
					for i in range(len(crop_names))
				]
				for p in output_cadastral_points
					if p.lulc_type in ['agriculture', 'fallow land']
		}
		sorted_keys = sorted(plot_vulnerability_dict.keys(), key=lambda ID: plot_vulnerability_dict[ID], reverse=True)
		csvwrite = open(cadastral_vulnerability_csv_filepath, 'w+b')
		writer = csv.writer(csvwrite)
		writer.writerow(['Plot ID'] +
						list(itertools.chain(*[
								[
									crop + ' Crop end Deficit',
									crop + ' Crop end Deficit Waterings',
									crop + ' Monsoon end Deficit',
									crop + ' Monsoon end Deficit Waterings'
								]
								for crop in crop_names
							])
						)
		)
		for key in sorted_keys:
			writer.writerow([key] +
							list(itertools.chain(*[
									[
										'{0:.2f}'.format(plot_vulnerability_dict[key][i][0]),
										round((plot_vulnerability_dict[key][i][0]) / 50),
										'{0:.2f}'.format(plot_vulnerability_dict[key][i][1]),
										round((plot_vulnerability_dict[key][i][1]) / 50)
									]
									for i in range(len(crop_names))
								])
						 	)
			)
		csvwrite.close()

	def compute_and_display_cadastral_vulnerability(self, cadastral_layer, output_grid_points, output_cadastral_points, crop_index, crop_name, base_path):
		cadastral_points_per_plot = {}
		for p in (output_grid_points + output_cadastral_points):
			if p.cadastral_polygon is None:    continue
			if p.lulc_type	not in ['agriculture', 'fallow land']:	continue
			if p.cadastral_polygon.id() in cadastral_points_per_plot:
				cadastral_points_per_plot[p.cadastral_polygon.id()].append(
					p.budget.PET_minus_AET_crop_end[crop_index])
			else:
				cadastral_points_per_plot[p.cadastral_polygon.id()] = [
					p.budget.PET_minus_AET_crop_end[crop_index]]
		for k, v in cadastral_points_per_plot.items():
			if len(v) > 0:
				cadastral_points_per_plot[k] = sum(v) / len(v)
			else:
				del cadastral_points_per_plot[k]

		#	Create duplicate cadastral layer in memory
		memory_cadastral_layer = QgsVectorLayer('Polygon?crs=epsg:32643', crop_name + ' Cadastral Level Vulnerability', 'memory')
		memory_cadastral_layer.startEditing()
		memory_cadastral_layer.dataProvider().addAttributes(
			cadastral_layer.qgsLayer.dataProvider().fields().toList())
		memory_cadastral_layer.updateFields()
		dict_new_feature_id_to_old_feature_id = {}
		for old_plot_id in cadastral_points_per_plot:
			result, output_features = memory_cadastral_layer.dataProvider().addFeatures(
				[cadastral_layer.feature_dict[old_plot_id]])
			dict_new_feature_id_to_old_feature_id[output_features[0].id()] = old_plot_id
		memory_cadastral_layer.dataProvider().addAttributes([QgsField('Deficit', QVariant.Double)])
		memory_cadastral_layer.updateFields()
		for new_feature in memory_cadastral_layer.getFeatures():
			new_feature['Deficit'] = cadastral_points_per_plot[dict_new_feature_id_to_old_feature_id[new_feature.id()]].item()
			# print cadastral_points_per_plot[dict_new_feature_id_to_old_feature_id[new_feature.id()]]
			memory_cadastral_layer.updateFeature(new_feature)
		memory_cadastral_layer.commitChanges()
		#	Graduated Rendering
		graduated_symbol_renderer_range_list = []
		ET_D_max = max(cadastral_points_per_plot.values())
		opacity = 1
		geometry_type = memory_cadastral_layer.geometryType()
		intervals_count = CADASTRAL_VULNERABILITY_DISPLAY_COLOUR_INTERVALS_COUNT
		dict_interval_colour = CADASTRAL_VULNERABILITY_DISPLAY_COLOURS_DICT
		for i in range(intervals_count):
			interval_min = 0 if i == 0 else (ET_D_max * float(
				i) / intervals_count) + 0.01
			interval_max = ET_D_max * float(i + 1) / intervals_count
			label = "{0:.2f} - {1:.2f}".format(interval_min, interval_max)
			colour = QColor(*dict_interval_colour[i])
			symbol = QgsSymbolV2.defaultSymbol(geometry_type)
			symbol.setColor(colour)
			symbol.setAlpha(opacity)
			interval_range = QgsRendererRangeV2(interval_min, interval_max, symbol, label)
			graduated_symbol_renderer_range_list.append(interval_range)
		renderer = QgsGraduatedSymbolRendererV2('', graduated_symbol_renderer_range_list)
		renderer.setMode(QgsGraduatedSymbolRendererV2.EqualInterval)
		renderer.setClassAttribute('Deficit')
		memory_cadastral_layer.setRendererV2(renderer)

		QgsMapLayerRegistry.instance().addMapLayer(memory_cadastral_layer)
		memory_cadastral_layer.setCustomProperty('labeling', 'pal')
		memory_cadastral_layer.setCustomProperty('labeling/enabled', 'true')
		memory_cadastral_layer.setCustomProperty('labeling/fieldName', 'Number')
		memory_cadastral_layer.setCustomProperty('labeling/fontSize', '10')
		memory_cadastral_layer.setCustomProperty('labeling/placement', '0')

		memory_cadastral_layer.dataProvider().forceReload()
		memory_cadastral_layer.triggerRepaint()
		
		QgsVectorFileWriter.writeAsVectorFormat(memory_cadastral_layer,
												base_path + '/kharif_'+crop_name+'_cadastral_level_vulnerability.shp', "utf-8", None,
												"ESRI Shapefile")
