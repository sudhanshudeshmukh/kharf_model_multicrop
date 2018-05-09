PLUGIN_MODE = 'REAL'	#	Possible values: 'DEBUG', 'TEST-SUITE', 'REAL'

#	Set the following for debugging or testing mode
DEBUG_BASE_FOLDER_PATH = 'D:\MTP related\Datasets\Sample'
TEST_SUITE_BASE_FOLDER_PATH = 'NO PATH YET'
DEBUG_OR_TEST_CROPS = ['bajra']	#	Possible values: subset of dict_crop.keys()
DEBUG_OR_TEST_RABI_CROPS = ['harbhara']
DEBUG_OR_TEST_GRADUATED_RENDERING_INTERVAL_POINTS = [0, 50]

#	Input-Output protocol constants
RAINFALL_CSV_FILENAME = 'Rainfall.csv'
ET0_CSV_FILENAME = 'ET0_file.csv'
POINTWISE_OUTPUT_CSV_FILENAME = 'kharif_model_pointwise_output.csv'
ZONEWISE_BUDGET_CSV_FILENAME = 'kharif_model_zonewise_budget.xls'
CADESTRAL_VULNERABILITY_CSV_FILENAME = 'kharif_model_cadastral_vulnerability.csv'
#	Optional inputs for debugging/testing
OVERRIDE_FILECROPS_BY_DEBUG_OR_TEST_CROPS = True
CROPS_FILENAME = 'crops.csv'

#	Computation Settings
STEP = 400.0
DEFAULT_SOWING_THRESHOLD = 30
START_DATE_INDEX = 0
MONSOON_END_DATE_INDEX = 132
END_DATE_INDEX = 364
CADASTRAL_VULNERABILITY_DISPLAY_COLOUR_INTERVALS_COUNT = 4
CADASTRAL_VULNERABILITY_DISPLAY_COLOURS_DICT = {0: [200, 200, 255], 1: [255, 0, 255], 2: [255, 165, 0], 3: [255, 0, 0]}