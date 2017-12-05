########	Constants Start	########

STEP =500.0
NEW_LU= 'LU_Type'
Desc = 'Descriptio'
TEX = 'TEXTURE'
Depth = 'DEPTH'
ROOT_LEVEL = 0.5 # Root level for plant

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
	'clay loam': ('D', '32', '34', '0', '0.206', '0.341', '0.442', '2.794', '1.48', '0.14'),
	'clayey': ('D', '28', '51', '0', '0.307', '0.427', '0.487', '0.52', '1.36', '0.12'),
	'gravelly clay': ('D', '23', '48', '10', '0.285', '0.415', '0.488', '0.89', '1.36', '0.12'),
	'gravelly clay loam': ('D', '31', '34', '10', '0.206', '0.343', '0.444', '2.54', '1.47', '0.13'),
	'gravelly loam': ('B', '41', '17', '10', '0.121', '0.265', '0.459', '18.19', '0.143', '0.14'),
	'gravelly sandy clay loam': ('B', '49', '26', '10', '0.16', '0.273', '0.412', '6.19', '1.56', '0.11'),
	'gravelly sandy loam': ('B', '63', '10', '10', '0.065', '0.158', '0.402', '35.32', '1.58', '0.09'),
	'gravelly silty clay': ('C', '7', '47', '10', '0.278', '0.416', '0.532', '3.81', '1.24', '0.14'),
	'gravelly silty loam': ('C', '21', '15', '10', '0.11', '0.303', '0.478', '16.44', '1.38', '0.19'),
	'loamy': ('B', '42', '20', '0', '0.137', '0.276', '0.457', '15.84', '1.44', '0.14'),
	'loamy sand': ('A', '82', '8', '0', '0.68', '0.132', '0.451', '76.67', '1.45', '0.06'),
	'sandy': ('A', '91', '5', '0', '0.05', '0.96', '0.462', '112.58', '1.42', '0.05'),
	'sandy clay': ('D', '51', '42', '0', '0.26', '0.371', '0.442', '0.88', '1.48', '0.11'),
	'sandy clay loam': ('C', '57', '28', '0', '0.172', '0.271', '0.406', '6.09', '1.57', '0.1'),
	'sandy loam': ('A', '65', '11', '0', '0.086', '0.184', '0.448', '46.25', '1.46', '0.1'),
	'silty clay': ('D', '9', '46', '0', '0.272', '0.415', '0.506', '1.9', '1.31', '0.14'),
	'silty clay loam': ('D', '11', '34', '0', '0.21', '0.378', '0.508', '5.87', '1.3', '0.17'),
	'silty loam': ('B', '19', '16', '0', '0.115', '0.311', '0.48', '14.99', '1.38', '0.2'),
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
	'bajra':[[[15,0.7],[25,1],[40,0.3],[25,1.5]],0.5],
	'moong':[[[20,0.5],[30,1.15],[35,1.1],[15,0.5]],0.5],
	'sorghum':[[[20,0.53],[35,0.82],[45,1.24],[30,0.85]],0.5],
	'cotton':[[[45,0.45],[90,0.75],[45,1.15],[45,0.75]],0.5],
	'udid':[[[20,0.5],[30,1.15],[35,0.35],[15,0.4]],0.5],
	'orange':[[[60,0.8],[90,0.8],[120,0.8],[95,3] ],0.5],
	'rice':[[[30,1.15],[30,1.23],[80,1.14],[40,1.02]],0.5],
	'sunflower':[[[25,0.63],[35,0.82],[45,1.12],[25,1.23]],0.5],
	'tur':[[[20,0.45],[30,0.85],[35,1.15],[15,1.05]],0.5],
	'grapes':[[[20,0.3],[40,0.7],[120,1.15],[60,2]],0.5],
	'maize':[[[20,0.55],[35,1],[40,1.23],[30,0.67]],0.5]
}

########	Lookup Dictionaries End		########
