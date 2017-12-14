########	Constants Start	########

STEP =100.0
NEW_LU= 'LU_Type'
Desc = 'Descriptio'
TEX = 'TEXTURE'
Depth = 'DEPTH'

########	Constants End	########



########	Lookup Dictionaries Start	########

#Dictionary for generic land use types:
dict_lulc = {
	'forest-forest blank':'scrub forest',
	'forest-deciduous (dry/moist/thorn)-open': 'deciduous open',
	'agricultural land-crop land-rabi crop': 'agriculture',
	'forest-scrub forest': 'scrub forest',	
	'agricultural land-crop land-kharif crop': 'agriculture',
	'agricultural land-fallow-current fallow': 'fallow land',
	'wastelands-scrub land-open scrub': 'scrub open',
	'forest-deciduous (dry/moist/thorn)-dense/closed': 'deciduous - dense',
	'wastelands-scrub land-dense scrub': 'scrub dense',
	'built up-built up (rural)-built up area (rural)': 'habitation',
	'waterbodies-reservoir/tanks-dry-zaid extent': 'water',
	'waterbodies-reservoir/tanks-dry-rabi extent': 'water',
	'agricultural land-crop land-zaid crop': 'agriculture',
	'waterbodies-reservoir/tanks-dry-kharif extent': 'water',
	'agricultural land-crop land-two crop area': 'agriculture',
	'built up-built up (urban)-vegetated area': 'habitation',
	'wastelands-barren rocky/stony waste': 'scrub dense',
	'agricultural land-plantation-agriculture plantation': 'agriculture',
	'agricultural land-crop land-more than two crop': 'agriculture',
	'waterbodies-river/stream-perennial': 'water',
	'built up-built up (urban)-transportation': 'habitation',
	'built up-built up (urban)-recreational':'habitation',
	'built up-built up (urban)-residential': 'habitation'
}

#Lookup for soiltype and soil dependent values for computation 
dict_SoilContent = {
	'soil type': (
		'HSG',
		'Sand %',
		'Clay %',
		'Gravel %',
		'WP',
		'FC',
		'Saturation',
		'Ksat mm/hr',
		'Bulk Density',
		'AWC'
	),
	 'clay loam': ('D', '32', '34', '0', '0.206', '0.341', '0.442', '2.7', '1.48', '0.14'),
	 'clayey': ('D', '28', '51', '0', '0.303', '0.427', '0.487', '0.52', '1.36', '0.12'),
	 'gravelly clay': ('D', '23', '48', '10', '0.285', '0.415', '0.488', '0.83', '1.36', '0.12'),
	 'gravelly clay loam': ('D', '31', '34', '10', '0.206', '0.343', '0.444', '2.32', '1.47', '0.12'),
	 'gravelly loam': ('B', '41', '17', '10', '0.109', '0.0244', '0.408', '10.83', '1.57', '0.12'),
	 'gravelly sandy clay loam': ('B', '49', '26', '10', '0.16', '0.273', '0.412', '5.83', '1.56', '0.1'),
	 'gravelly sandy loam': ('B', '63', '10', '10', '0.065', '0.158', '0.402', '33.29', '1.58', '0.08'),
	 'gravelly silty clay': ('C', '7', '47', '10', '0.277', '0.42', '0.512', '1.7', '1.29', '0.13'),
	 'gravelly silty loam': ('C', '21', '15', '10', '0.099', '0.282', '0.415', '6.8', '1.55', '0.16'),
	 'loamy': ('B', '42', '20', '0', '0.126', '0.256', '0.411', '10.2', '1.56', '0.13'),
	 'loamy sand': ('A', '82', '8', '0', '0.05', '0.106', '0.41', '69.09', '1.56', '0.06'),
	 'sandy': ('A', '91', '5', '0', '0.03', '0.071', '0.424', '108.06', '1.53', '0.04'),
	 'sandy clay': ('D', '51', '42', '0', '0.254', '0.364', '0.43', '0.73', '1.51', '0.11'),
	 'sandy clay loam': ('C', '57', '28', '0', '0.172', '0.271', '0.406', '6.09', '1.57', '0.1'),
	 'sandy loam': ('A', '65', '11', '0', '0.172', '0.258', '0.399', '6.67', '1.59', '0.09'),
	 'silty clay': ('D', '9', '46', '0', '0.272', '0.415', '0.506', '1.9', '1.31', '0.14'),
	 'silty clay loam': ('D', '11', '34', '0', '0.206', '0.371', '0.47', '2.65', '1.41', '0.17'),
	 'silty loam': ('B', '19', '16', '0', '0.105', '0.291', '0.418', '6.97', '1.54', '0.19'),
	 'waterbody mask': ('D', '28', '51', '0', '0.303', '0.427', '0.487', '0.52', '1.36', '0.12'),
 'habitation mask': ('D', '32', '34', '0', '0.206', '0.341', '0.442', '2.7', '1.48', '0.14')
}

#Lookup for SCS curve no based on land ussage and HSG: 
dict_RO = {
	'agriculture': {'A': '67', 'B': '78', 'C': '85', 'D': '89'},
	'deciduous - dense': {'A': '30', 'B': '55', 'C': '70', 'D': '77'},
	'deciduous open': {'A': '36', 'B': '60', 'C': '73', 'D': '79'},
	'fallow land': {'A': '77', 'B': '86', 'C': '91', 'D': '94'},
	'habitation': {'A': '77', 'B': '85', 'C': '90', 'D': '92'},
	'scrub dense': {'A': '49', 'B': '69', 'C': '79', 'D': '84'},
	'scrub forest': {'A': '57', 'B': '73', 'C': '82', 'D': '86'},
	'scrub open': {'A': '68', 'B': '79', 'C': '86', 'D': '89'},
	'water': {'A': '100', 'B': '100', 'C': '100', 'D': '100'}
}

#Lookup for Soil depth with respect to given soil depth in Soil map: 
dict_SoilDep = {
	'deep (50 to 100 cm)': '1',
	'habitation mask': '0.1',
	'shallow (10 to 25 cm)': '0.25',
	'very deep (> 100 cm)': '1.5',
	'waterbody mask': '0.1',
	'moderately deep (25 to 50 cm)': '0.5',
	'shallow to very shallow (< 25 cm)': '0.25',
	'very shallow (< 10 cm)': '0.1'
}

#Lookup for Crop KC and crop depletion factor
dict_crop = {
	'soyabean':[[[20,0.3],[25,0.7],[45,1.15],[20,0.7]],0.5],
	'bajra':[[[15,0.7],[25,1],[40,0.3],[25,1.5]],0.55],
	'moong':[[[20,0.5],[30,1.15],[35,1.1],[15,0.5]],0.45],
	'sorghum':[[[20,0.53],[35,0.82],[45,1.24],[30,0.85]],0.55],
	'cotton':[[[45,0.45],[90,0.75],[45,1.15],[45,0.75]],0.65],
	'udid':[[[20,0.5],[30,1.15],[35,0.35],[15,0.4]],0.45],
	'orange':[[[60,0.8],[90,0.8],[120,0.8],[95,3] ],0.5],
	'rice':[[[30,1.15],[30,1.23],[80,1.14],[40,1.02]],0.2],
	'sunflower':[[[25,0.63],[35,0.82],[45,1.12],[25,1.23]],0.45],
	'tur':[[[20,0.45],[30,0.85],[35,1.15],[15,1.05]],0.45],
	'grapes':[[[20,0.3],[40,0.7],[120,1.15],[60,2]],0.5],
	'maize':[[[20,0.55],[35,1],[40,1.23],[30,0.67]],0.55]
}

#Lookup for Crop and root zone
dict_crop_root = {
	'soyabean':0.9,
	'bajra':1.5,
	'moong':0.75,
	'sorghum':1.5,
	'cotton':1.35,
	'udid':0.75,
	'orange':1.1,
	'rice':0.75,
	'sunflower':1.15,
	'tur':0.75,
	'grapes':0.9,
	'maize':1.35
}

#Long Kharif crops list
long_kharif_crops = ['cotton','orange','grapes','tur']

########	Lookup Dictionaries End		########
