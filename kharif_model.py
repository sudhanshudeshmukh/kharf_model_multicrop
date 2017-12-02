# -*- coding: utf-8 -*-
"""
/***************************************************************************
 KharifModel
                                 A QGIS plugin
 Generates kharif season vulnerability map
                              -------------------
        begin                : 2017-11-18
        git sha              : $Format:%H$
        copyright            : (C) 2017 by IITB
        email                : sohoni@cse.iitb.ac.in
 ***************************************************************************/

/***************************************************************************
 *                                                                         *
 *   This program is free software; you can redistribute it and/or modify  *
 *   it under the terms of the GNU General Public License as published by  *
 *   the Free Software Foundation; either version 2 of the License, or     *
 *   (at your option) any later version.                                   *
 *                                                                         *
 ***************************************************************************/
"""
from PyQt4.QtCore import QSettings, QTranslator, qVersion, QCoreApplication, QDate
from PyQt4.QtGui import QAction, QIcon, QFileDialog, QColor
# Initialize Qt resources from file resources.py
import resources
# Import the code for the dialog
from kharif_model_dialog import KharifModelDialog
import os.path
# Import code for the calculation
from kharif_model_calculator import KharifModelCalculator
from qgis.core import QgsMapLayerRegistry, QgsVectorLayer, QgsSymbolV2, QgsRendererRangeV2, QgsGraduatedSymbolRendererV2, QgsVectorFileWriter
from constants_dicts_lookups import *


class KharifModel:
	"""QGIS Plugin Implementation."""

	def __init__(self, iface):
		"""Constructor.

		:param iface: An interface instance that will be passed to this class
			which provides the hook by which you can manipulate the QGIS
			application at run time.
		:type iface: QgsInterface
		"""
		# Save reference to the QGIS interface
		self.iface = iface
		# initialize plugin directory
		self.plugin_dir = os.path.dirname(__file__)
		# initialize locale
		locale = QSettings().value('locale/userLocale')[0:2]
		locale_path = os.path.join(
			self.plugin_dir,
			'i18n',
			'KharifModel_{}.qm'.format(locale))

		if os.path.exists(locale_path):
			self.translator = QTranslator()
			self.translator.load(locale_path)

			if qVersion() > '4.3.3':
				QCoreApplication.installTranslator(self.translator)


		# Declare instance attributes
		self.actions = []
		self.menu = self.tr(u'&Kharif Model')
		# TODO: We are going to let the user set this up in a future iteration
		self.toolbar = self.iface.addToolBar(u'KharifModel')
		self.toolbar.setObjectName(u'KharifModel')
		

	# noinspection PyMethodMayBeStatic
	def tr(self, message):
		"""Get the translation for a string using Qt translation API.

		We implement this ourselves since we do not inherit QObject.

		:param message: String for translation.
		:type message: str, QString

		:returns: Translated version of message.
		:rtype: QString
		"""
		# noinspection PyTypeChecker,PyArgumentList,PyCallByClass
		return QCoreApplication.translate('KharifModel', message)


	def add_action(
		self,
		icon_path,
		text,
		callback,
		enabled_flag=True,
		add_to_menu=True,
		add_to_toolbar=True,
		status_tip=None,
		whats_this=None,
		parent=None):
		"""Add a toolbar icon to the toolbar.

		:param icon_path: Path to the icon for this action. Can be a resource
			path (e.g. ':/plugins/foo/bar.png') or a normal file system path.
		:type icon_path: str

		:param text: Text that should be shown in menu items for this action.
		:type text: str

		:param callback: Function to be called when the action is triggered.
		:type callback: function

		:param enabled_flag: A flag indicating if the action should be enabled
			by default. Defaults to True.
		:type enabled_flag: bool

		:param add_to_menu: Flag indicating whether the action should also
			be added to the menu. Defaults to True.
		:type add_to_menu: bool

		:param add_to_toolbar: Flag indicating whether the action should also
			be added to the toolbar. Defaults to True.
		:type add_to_toolbar: bool

		:param status_tip: Optional text to show in a popup when mouse pointer
			hovers over the action.
		:type status_tip: str

		:param parent: Parent widget for the new action. Defaults None.
		:type parent: QWidget

		:param whats_this: Optional text to show in the status bar when the
			mouse pointer hovers over the action.

		:returns: The action that was created. Note that the action is also
			added to self.actions list.
		:rtype: QAction
		"""

		# Create the dialog (after translation) and keep reference
		self.dlg = KharifModelDialog(crops=dict_crop.keys())

		icon = QIcon(icon_path)
		action = QAction(icon, text, parent)
		action.triggered.connect(callback)
		action.setEnabled(enabled_flag)

		if status_tip is not None:
			action.setStatusTip(status_tip)

		if whats_this is not None:
			action.setWhatsThis(whats_this)

		if add_to_toolbar:
			self.toolbar.addAction(action)

		if add_to_menu:
			self.iface.addPluginToMenu(
				self.menu,
				action)

		self.actions.append(action)

		return action

	def initGui(self):
		"""Create the menu entries and toolbar icons inside the QGIS GUI."""

		icon_path = ':/plugins/KharifModel/icon.png'
		self.add_action(
			icon_path,
			text=self.tr(u'Kharif Model'),
			callback=self.run,
			parent=self.iface.mainWindow())


	def unload(self):
		"""Removes the plugin menu item and icon from QGIS GUI."""
		for action in self.actions:
			self.iface.removePluginMenu(
				self.tr(u'&Kharif Model'),
				action)
			self.iface.removeToolBarIcon(action)
		# remove the toolbar
		del self.toolbar


	def run(self):
		"""Run method that performs all the real work"""
		# show the dialog
		self.dlg.show()
		# See if Cancel was pressed
		if self.dlg.exec_() == QFileDialog.Rejected:	return
		
		# Load input layers
		ws_layer = self.iface.addVectorLayer(self.dlg.watershed_layer_filename.text(), 'Watershed', 'ogr')
		soil_layer = self.iface.addVectorLayer(self.dlg.soil_layer_filename.text(), 'Soil Cover', 'ogr')
		lulc_layer = self.iface.addVectorLayer(self.dlg.lulc_layer_filename.text(), 'Land-Use-Land-Cover', 'ogr')
		slope_layer = self.iface.addRasterLayer(self.dlg.slope_layer_filename.text(), 'Slope')
		#~ ws_layer = self.iface.addVectorLayer('C:/Users/Rahul/.qgis2/python/plugins/KharifModel/test/user examples/Wahegaon_Cluster_Data/Wahegaon_Cluster_Boundary_correct.shp', 'Watershed', 'ogr')
		#~ soil_layer = self.iface.addVectorLayer('C:/Users/Rahul/.qgis2/python/plugins/KharifModel/test/user examples/Wahegaon_Cluster_Data/Soil_correct.shp', 'Soil Cover', 'ogr')
		#~ lulc_layer = self.iface.addVectorLayer('C:/Users/Rahul/.qgis2/python/plugins/KharifModel/test/user examples/Wahegaon_Cluster_Data/LULC_correct.shp', 'Land-Use-Land-Cover', 'ogr')
		#~ slope_layer = self.iface.addRasterLayer('C:/Users/Rahul/.qgis2/python/plugins/KharifModel/test/user examples/Wahegaon_Cluster_Data/Slope.tif', 'Slope')
		
		rainfall_csv = self.dlg.rainfall_csv_filename.text()
		#~ rainfall_csv = 'C:/Users/Rahul/.qgis2/python/plugins/KharifModel/test/user examples/Wahegaon_Cluster_Data/W2017.csv'
		
		crop = self.dlg.crop_combo_box.currentText()
		
		start_qdate = self.dlg.from_date_edit.date()
		date_with_index_0 = QDate(start_qdate.year(), 6, 1).dayOfYear()
		start_date_index = start_qdate.dayOfYear() - date_with_index_0
		end_qdate = self.dlg.to_date_edit.date()
		end_date_index = end_qdate.dayOfYear() - date_with_index_0
		
		interval_points = [int(self.dlg.colour_code_intervals_list_widget.item(i).text().split('-')[0])	for i in range(1,self.dlg.colour_code_intervals_list_widget.count())]
		
		
		path = os.path.dirname(self.dlg.watershed_layer_filename.text())
		#~ path = 'C:/Users/Rahul/.qgis2/python/plugins/KharifModel/test/user examples/Wahegaon_Cluster_Data'
		output_csv_filename = '/kharif_model_output.csv'
		model_calculator = KharifModelCalculator(path, ws_layer, soil_layer, lulc_layer, slope_layer, rainfall_csv)
		model_calculator.calculate(output_csv_filename,crop,start_date_index,end_date_index)
		uri = 'file:///' + path + output_csv_filename + '?delimiter=%s&crs=epsg:32643&xField=%s&yField=%s' % (',', 'X', 'Y')
		kharif_model_output_layer = QgsVectorLayer(uri, 'Kharif Model Output','delimitedtext')
		
		
		graduated_symbol_renderer_range_list = []
		ET_D_max = model_calculator.max_pet_minus_aet
		opacity = 1
		intervals_count = self.dlg.colour_code_intervals_list_widget.count()
		for i in range(intervals_count):
			percent_interval_start_text, percent_interval_end_text = self.dlg.colour_code_intervals_list_widget.item(i).text().split('-')
			interval_min = 0 if percent_interval_start_text == '0' else (int(percent_interval_start_text)*ET_D_max/100.0 + 0.01)
			interval_max = (int(percent_interval_end_text)*ET_D_max/100.0)
			label = "{0:.2f} - {1:.2f}".format(interval_min, interval_max)
			colour = QColor(int(255*(1-(i+1.0)/(intervals_count+1.0))), 0, 0)	# +1 done to tackle boundary cases
			symbol = QgsSymbolV2.defaultSymbol(kharif_model_output_layer.geometryType())
			symbol.setColor(colour)
			symbol.setAlpha(opacity)
			interval_range = QgsRendererRangeV2(interval_min, interval_max, symbol, label)
			graduated_symbol_renderer_range_list.append(interval_range)
		renderer = QgsGraduatedSymbolRendererV2('', graduated_symbol_renderer_range_list)
		renderer.setMode(QgsGraduatedSymbolRendererV2.EqualInterval)
		renderer.setClassAttribute('PET-AET')

		kharif_model_output_layer.setRendererV2(renderer)
		QgsMapLayerRegistry.instance().addMapLayer(kharif_model_output_layer)
		
		QgsVectorFileWriter.writeAsVectorFormat(kharif_model_output_layer, path+'/kharif_et_deficit.shp', "utf-8", None, "ESRI Shapefile")
		
		if self.dlg.save_image_group_box.isChecked():
			self.iface.mapCanvas.saveAsImage(self.dlg.save_image_filename.text())
