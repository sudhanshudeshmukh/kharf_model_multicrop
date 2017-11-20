
"""
/***************************************************************************
 KharifModelDialog
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

import os

from PyQt4 import QtGui, uic

FORM_CLASS, _ = uic.loadUiType(os.path.join(
    os.path.dirname(__file__), 'kharif_model_dialog_base.ui'))


class KharifModelDialog(QtGui.QDialog, FORM_CLASS):
    def __init__(self, parent=None):
        """Constructor."""
        super(KharifModelDialog, self).__init__(parent)
        # Set up the user interface from Designer.
        # After setupUI you can access any designer object by doing
        # self.<objectname>, and you can use autoconnect slots - see
        # http://qt-project.org/doc/qt-4.8/designer-using-a-ui-file.html
        # #widgets-and-dialogs-with-auto-connect
        self.setupUi(self)
        
        self.last_path = ''
        
        self.watershed_layer_browse.clicked.connect(lambda : self.on_browse(self.watershed_layer_filename, 'Watershed Vector Layer', 'Shapefiles (*.shp)'))
        self.soil_layer_browse.clicked.connect(lambda : self.on_browse(self.soil_layer_filename, 'Soil-cover Vector Layer', 'Shapefiles (*.shp)'))
        self.lulc_layer_browse.clicked.connect(lambda : self.on_browse(self.lulc_layer_filename, 'Land-use-land-cover Vector Layer', 'Shapefiles (*.shp)'))
        self.slope_layer_browse.clicked.connect(lambda : self.on_browse(self.slope_layer_filename, 'Slope Raster Layer', 'TIFF files (*.tif *.tiff)'))
    
    def on_browse(self, lineEdit, caption, fltr):
		filename = QtGui.QFileDialog.getOpenFileName(self, caption, self.last_path, fltr)
		lineEdit.setText(filename)
		self.last_path = os.path.dirname(filename)
