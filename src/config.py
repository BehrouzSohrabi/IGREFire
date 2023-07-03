from os.path import basename, splitext, exists, isfile, dirname
from os import makedirs, remove
import json
import ast
import pandas as pd
from numpy import array
from datetime import datetime
from pyproj import Geod
from shapely.geometry import Polygon

from .messages import *
from .utils import callback

class Config:
    """
    Configuration class for the Wildfire Risk Assessment framework.

    This class holds the input parameters for the analysis and is used to pass
    the configuration to the WildfireRiskAssessment class.

    Attributes:
        id (int): Load previously created analysis configs by id. Analysis records can be found in the /outputs directory.
        analysis_run_title (str): Title for the analysis.
        test_system_topology (str): Path to the GeoJSON file containing the test system topology.
        test_system_matpower (str): Path to the Matpower file of the test system.
        landscape_file (str): Path to the LCP landscape file.
        landscape_bounds (list): Bounding box coordinates of the LCP matched with the topology in degrees [W, S, E, N].
        landscape_resolution (int): Resolution of the LCP file in meters (usually 30 or 60).
        farsite_perimeter_resolution (int): Resolution of FARSITE perimeters in meters (must be >= landscape resolution).
        farsite_time_step (int): Fire spread progression steps in minutes.
        farsite_start (int): FARSITE start date row ID in weather files. (default = 0)
        farsite_burn_periods (int): FARSITE duration. The number of hour rows to include in the simulation using weather stream data (default = 96).
        fuel_moistures (list): Fuel moisture profiles for each fuel model in the LCP file.
        weather_files (dict): Dictionary of CSV files containing weather data. The keys will be displayed in scenario results. Can be obtained from https://nsrdb.nrel.gov/data-viewer (USA & Americas (60min / 4km / 2021)). Blank to create synthetic extreme weather stream.
        weather_conditions (dict): Dictionary of weather conditions. Key is the title of weather stream. Value is another dict with wind direction and speed, temperature and humidity arguments. Priority is weather_files. (See utils.py)
        barriers_file (str, optional): Path to the optional shapefile containing barriers. Defaults to an empty string.
        crown_fire_method (str): Crown fire calculation method ('Finney' or 'Reinhardt').
        ignition_points_number (int): Number of ignition points per branch (0 for using ignition_points_distance).
        ignition_points_distance (int): Space between each ignition points on branches in meters (0 for using ignition_points_number).
        ignition_points_radius (int): Radius of the ignition points in meters.
        branch_effects (list): Determines how branches will be affected by wildfire ('trip' and or 'degrade')
    """

    def __init__(self, record_id=None, **kwargs):

        # Print and intro of the framework
        callback('header', 'IGREFire')

        # Static Attributes
        self.records_file           = './outputs/records.csv'
        self.FARSITE_raws_template  = './assets/templates/FARSITE_raws'
        self.FARSITE_input_template = './assets/templates/FARSITE_input'
        self.FARSITE_run_template   = './assets/templates/FARSITE_run'
        self.MATPOWER_template      = './assets/templates/MATPOWER'
        self.FARSITE                = './assets/FARSITE/FARSITE'
        self.FARSITE_run_file       = 'FARSITE.run'
        self.FARSITE_intensity_file = '_Intensity.asc'
        self.FARSITE_remove_files   = ['_ArrivalTime', '_CrownFire', '_FlameLength', '_HeatPerUnitArea', '_Ignitions', '_Perimeters', '_ReactionIntensity', '_SpotGrid', '_Spots', '_SpreadDirection', '_SpreadRate', '_Timings']
        self.intensity_threshold    = .00005

        # Create Config from the given arguments, or load from analysis records by id
        if record_id is None:
            load_from = kwargs
            self.started = datetime.now()
        else:
            load_from = self.load_record(record_id)
            self.started = datetime.strptime(load_from['started'], '%Y-%m-%d %H:%M:%S')
        
        # Analysis Config Attributes
        self.id                           = record_id
        self.analysis_run_title           = load_from.get('analysis_run_title', 'Untitled Analysis on IEEE BUS 30')
        self.test_system_topology         = load_from.get('test_system_topology', 'data/grid/IEEE_30_bus_system.geojson')
        self.test_system_matpower         = load_from.get('test_system_matpower', 'data/grid/IEEE_30_bus_system.py')
        self.landscape_file               = load_from.get('landscape_file', 'data/landscape/IEEE_30_bus_system_resolution_60.lcp')
        self.landscape_bounds             = ast.literal_eval(load_from.get('landscape_bounds', '[-120.7, 37.6, -120, 38.1]'))
        self.landscape_resolution         = int(load_from.get('landscape_resolution', 60))
        self.farsite_perimeter_resolution = int(load_from.get('farsite_perimeter_resolution', 60))
        self.farsite_time_step            = int(load_from.get('farsite_time_step', 240))
        self.farsite_start                = int(load_from.get('farsite_start', 0))
        self.farsite_burn_periods         = int(load_from.get('farsite_burn_periods', 24))
        self.fuel_moistures               = ast.literal_eval(load_from.get('fuel_moistures', '[[0, 6, 7, 8, 60, 90]]'))
        self.weather_files                = ast.literal_eval(load_from.get('weather_files', '{}'))
        self.weather_conditions           = ast.literal_eval(load_from.get('weather_conditions', '{"N": {"wind_direction": {"degree":0}}, "S": {"wind_direction": {"degree":180}}}'))
        self.barriers_file                = load_from.get('barriers_file', None)
        self.crown_fire_method            = load_from.get('crown_fire_method', 'Finney')
        self.ignition_points_number       = int(load_from.get('ignition_points_number', 0))
        self.ignition_points_distance     = int(load_from.get('ignition_points_distance', 0))
        self.ignition_points_radius       = int(load_from.get('ignition_points_radius', 30))
        self.branch_effects               = ast.literal_eval(load_from.get('branch_effects', '["trip"]'))
        self.scenarios                    = int(load_from.get('scenarios', 0))
        self.scenarios_file               = load_from.get('scenarios_file', None)

        # Centroid of the LCP file
        self.center = self._find_centroid()

        # Coordinates System Transform Projection
        self.geod = Geod(ellps='WGS84')

    def _find_centroid(self):
        xmin, ymin, xmax, ymax = self.landscape_bounds
        boundary = Polygon([(xmin, ymin), (xmax, ymin), (xmax, ymax), (xmin, ymax)])
        return boundary.centroid
    
    def read_MATPOWER_path(self):
        root_name, extension = splitext(self.test_system_matpower)
        case_name = basename(root_name)
        return root_name, extension, case_name

    def read_matpower(self):
        root_name, extension, case_name = self.read_MATPOWER_path()
        exec(compile(open(root_name + extension).read(), root_name + extension, 'exec'))
        self.matpower = eval(case_name)()
    
    def read_topology(self):
        with open(self.test_system_topology) as f:
            self.topology = json.load(f)

    def read_record(self):
        self.record = self.load_record(self.id)

    # Validate, Build and Return the config instance
    def build(self):

        # Validate analysis_run_title
        if not isinstance(self.analysis_run_title, str):
            return callback("ValueError", TITLE_ERROR)

        # Validate file paths
        files = [self.test_system_topology, self.test_system_matpower, self.landscape_file, self.barriers_file]
        for file in files:
            if file != "" and file is not None and not isfile(file):
                return callback("ValueError", FILE_DOES_NOT_EXIST.format(file))

        # Validate landscape_bounds
        if not isinstance(self.landscape_bounds, list) or len(self.landscape_bounds) != 4:
            return callback("ValueError", LANDSCAPE_BOUNDS_ERROR)

        # Validate landscape_resolution
        if self.landscape_resolution not in [30, 60, 90, 120, 180, 270]:
            return callback("ValueError", LANDSCAPE_RESOLUTION_ERROR)

        # Validate farsite_perimeter_resolution
        if self.farsite_perimeter_resolution < self.landscape_resolution:
            return callback("ValueError", LANDSCAPE_FARSITE_RESOLUTION_ERROR)

        # Validate farsite_time_step
        if not isinstance(self.farsite_time_step, int):
            return callback("ValueError", FARSITE_TIMESTEP_ERROR)

        # Validate fuel_moistures
        if not isinstance(self.fuel_moistures, list) or not all(isinstance(i, list) for i in self.fuel_moistures):
            return callback("ValueError", FUEL_MOISTURES_ERROR)

        # Validate weather_files
        if not isinstance(self.weather_files, dict):
            return callback("ValueError", WEATHER_FILES_NOT_DICT)
        for file in self.weather_files.values():
            if not isfile(file):
                return callback("ValueError", FILE_DOES_NOT_EXIST.format(file))

        # Validate crown_fire_method
        if self.crown_fire_method not in ["Finney", "Reinhardt"]:
            return callback("ValueError", CROWN_FIRE_ERROR)

        # Validate ignition_points_number and ignition_points_distance
        if (self.ignition_points_number <= 0 and self.ignition_points_distance <= 0):
            return callback("ValueError", IGNITION_POINT_VALUE_ERROR)
        if self.ignition_points_number == 0 and self.ignition_points_distance == 0:
            self.ignition_points_number = 1

        # Validate ignition_points_radius
        if not isinstance(self.ignition_points_radius, int):
            return callback("ValueError", IGNITION_POINT_RADIUS_ERROR)
    
        # Validate and Load Topology. Check if at least one branch exists.
        self.read_topology()
        branch_found = False
        for feature in self.topology['features']:
            if feature['geometry']['type'] == 'LineString':
                branch_found = True
                # Check if branch has the necessary properties fields
                if 'branch' not in feature['properties']:
                    callback("ValueError", MISSING_BRANCH_PROPERTY)
        if not branch_found:
            callback("ValueError", NO_LINESTRING_FEATURES)

        # Validate and Load MATPOWER
        try:
            self.read_matpower()
        except:
            callback("ValueError", MATPOWER_LOAD_ERROR)

        # Save the inputs record and assign an ID for the config
        if self.id is None:
            self.id = self.save_records()
            new_config = True
        else:
            new_config = False

        # Return status callback
        callback("update", CONFIG_VALIDATED.format("" if new_config else CONFIG_LOADED), separator=False)
        callback("update", CONFIG_SUMMARY.format(self.id, self.analysis_run_title, self.landscape_resolution, self.farsite_perimeter_resolution, self.crown_fire_method, self.farsite_time_step, self.farsite_start, self.farsite_burn_periods, self.ignition_points_number, self.ignition_points_distance, self.ignition_points_radius))

    def generate_file_name(self, file_type, **kwargs):

        remove_old = False

        if file_type == 'ignition_points':
            file = f'./outputs/FARSITE/{self.id}/ignition_points/branch_{kwargs["branch_id"]}/point_{kwargs["point_id"]}.shp'

        elif file_type == 'weather':
            file = f'./outputs/FARSITE/{self.id}/weather_{kwargs["weather"]}/FARSITE.raws'

        elif file_type == 'input':
            file = f'./outputs/FARSITE/{self.id}/weather_{kwargs["weather"]}/FARSITE.input'

        elif file_type == 'run':
            file = f'./outputs/FARSITE/{self.id}/weather_{kwargs["weather"]}/runs/branch_{kwargs["branch_id"]}/point_{kwargs["point_id"]}/'
        
        elif file_type in ['scenarios', 'report_record', 'report_nodes', 'report_lines', 'report_areas']:
            file = f'./outputs/reports/{self.id}/{file_type}.csv'

        elif file_type == 'scenarios_gis':
            file = f'./outputs/reports/{self.id}/scenarios.geojson'

        elif file_type == 'report_gis':
            file = f'./outputs/reports/{self.id}/report.geojson'
            
        elif file_type == 'FARSITE_log':
            file = f'./outputs/reports/{self.id}/FARSITE.log'

        elif file_type == 'MATPOWER_trip':
            file = f'./outputs/MATPOWER/{self.id}/weather_{kwargs["weather"]}/runs/branch_{kwargs["branch_id"]}/point_{kwargs["point_id"]}/trip_{kwargs["matpower_file"]}'

        elif file_type == 'MATPOWER_degrade':
            file = f'./outputs/MATPOWER/{self.id}/weather_{kwargs["weather"]}/runs/branch_{kwargs["branch_id"]}/point_{kwargs["point_id"]}/degrade_{kwargs["matpower_file"]}'

        elif file_type == 'powerflow_output_standard':
            file = f'./outputs/MATPOWER/{self.id}/powerflow_standard.log'
            remove_old = True

        elif file_type == 'powerflow_output_trip_branch':
            file = f'./outputs/MATPOWER/{self.id}/weather_{kwargs["weather"]}/runs/branch_{kwargs["branch_id"]}/point_{kwargs["point_id"]}/powerflow_trip_branch.log'
            remove_old = True

        elif file_type == 'powerflow_output_degrade_branch':
            file = f'./outputs/MATPOWER/{self.id}/weather_{kwargs["weather"]}/runs/branch_{kwargs["branch_id"]}/point_{kwargs["point_id"]}/powerflow_degrade_branch.log'
            remove_old = True
            
        else:
            raise ValueError(f'Unsupported file_type: {file_type}')
        
        # Make sure the directory exists
        directory = dirname(file)
        if not exists(directory):
            makedirs(directory)
        
        # Remove old file if exists
        if remove_old and isfile(file):
            remove(file)
        
        return file

    def save_records(self):
        
        # If the records file exists, read it into a DataFrame, otherwise create one
        if exists(self.records_file):
            df = pd.read_csv(self.records_file)
            record_id = df['id'].max() + 1
        else:
            record_id = 1

        # Create the new entry as a dictionary
        new_entry = {
            'id': record_id,
            'analysis_run_title'            : self.analysis_run_title,
            'test_system_topology'          : self.test_system_topology,
            'test_system_matpower'          : self.test_system_matpower,
            'landscape_file'                : self.landscape_file,
            'landscape_bounds'              : str(self.landscape_bounds),
            'landscape_resolution'          : self.landscape_resolution,
            'farsite_perimeter_resolution'  : self.farsite_perimeter_resolution,
            'farsite_time_step'             : self.farsite_time_step,
            'farsite_start'                 : self.farsite_start,
            'farsite_burn_periods'          : self.farsite_burn_periods,
            'fuel_moistures'                : str(self.fuel_moistures),
            'weather_files'                 : str(self.weather_files),
            'weather_conditions'            : str(self.weather_conditions),
            'barriers_file'                 : self.barriers_file,
            'crown_fire_method'             : self.crown_fire_method,
            'ignition_points_number'        : self.ignition_points_number,
            'ignition_points_distance'      : self.ignition_points_distance,
            'ignition_points_radius'        : self.ignition_points_radius,
            'branch_effects'                : self.branch_effects,
            'scenarios'                     : self.scenarios,
            'scenarios_file'                : self.scenarios_file,
            'started'                       : self.started.strftime('%Y-%m-%d %H:%M:%S'),
            'elapsed'                       : 0,
            'status'                        : 'Config Built'
        }

        try:
            # Append the new entry to the DataFrame and save it
            new_entry_series = pd.Series(new_entry, index=df.columns)
            df = pd.concat([df, new_entry_series.to_frame().T], ignore_index=True)
        except NameError:
            # Create the dataframe with the first entry
            df = pd.DataFrame(new_entry, index=[0])
        
        # Save the updated records file
        df.to_csv(self.records_file, index=False)

        return record_id
    
    def load_record(self, record_id, return_row=True):

        # Load Records File
        df = pd.read_csv(self.records_file).applymap(lambda x: None if pd.isna(x) else x)

        # Check if the given row exists
        if record_id not in df['id'].values:
            raise ValueError(RECORD_DOES_NOT_EXIST.format(record_id))

        # Return the selected record
        if return_row:
            return df.loc[df['id'] == record_id].to_dict(orient='records')[0]
        else:
            return df
    
    def update_record(self, **kwargs):

        # Load Records File Dataframe
        df = self.load_record(self.id, return_row = False)

        # Update elapsed
        df['elapsed'] = datetime.now() - self.started

        # Update the specified columns
        for column_name, value in kwargs.items():
            if column_name in df.columns:
                df.loc[df['id'] == self.id, column_name] = value
            else:
                raise KeyError(RECORD_COLUMN_INVALID.format(column_name))

        # Save the updated DataFrame to the CSV file
        df.to_csv(self.records_file, index=False)

    def save_scenarios(self, scenarios):

        # Save a table of all FARSITE simulation scenarios
        df = pd.DataFrame(scenarios)
        self.scenarios = df.shape[0]
        self.scenarios_file = self.generate_file_name('scenarios')

        # Update Analysis Records
        self.update_record(scenarios=self.scenarios, scenarios_file=self.scenarios_file)

        # Save Scenarios
        df.to_csv(self.scenarios_file, index=True)
    
    def read_scenarios(self):
        self.scenarios_file = self.generate_file_name('scenarios')
        self.scenarios = pd.read_csv(self.scenarios_file, index_col=[0])