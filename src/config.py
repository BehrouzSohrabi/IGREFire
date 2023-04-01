import os
import csv
import pandas as pd
from datetime import datetime

from .messages import *

class Config:
    """
    Configuration class for the Wildfire Risk Assessment framework.

    This class holds the input parameters for the analysis and is used to pass
    the configuration to the WildfireRiskAssessment class.

    Attributes:
        analysis_run_title (str): Title for the analysis.
        test_system_topology (str): Path to the GeoJSON file containing the test system topology.
        test_system_matpower (str): Path to the Matpower file of the test system.
        landscape_file (str): Path to the LCP landscape file.
        landscape_bounds (list): Bounding box coordinates of the LCP matched with the topology in degrees [W, S, E, N].
        landscape_resolution (int): Resolution of the LCP file in meters (usually 30 or 60).
        farsite_perimeter_resolution (int): Resolution of FARSITE perimeters in meters (must be >= landscape resolution).
        farsite_time_step (int): Fire spread progression steps in minutes.
        fuel_moistures (list): Fuel moisture profiles for each fuel model in the LCP file.
        weather_files (dict): Dictionary of CSV files containing weather data. The keys will be displayed in scenario results. Can be obtained from https://nsrdb.nrel.gov/data-viewer (USA & Americas (60min / 4km / 2021))
        farsite_start (int): FARSITE start date row ID in weather files. (default = 0),
        farsite_burn_periods (int): FARSITE duration. The number of hour rows to include in the simulation (default = 72),
        barriers_file (str, optional): Path to the optional shapefile containing barriers. Defaults to an empty string.
        crown_fire_method (str): Crown fire calculation method ('Finney' or 'Reinhardt').
        ignition_points_number (int): Number of ignition points per branch (None for using ignition_points_distance).
        ignition_points_distance (int, optional): Space between each ignition point on branches in meters (None for using ignition_points_number). Defaults to None.
        ignition_points_radius (int): Radius of the ignition points in meters.

    Example:
        config = Config(
            analysis_run_title='IEEE BUS 30 Basic Run',
            test_system_topology='data/grid/IEEE_30_bus_system.geojson',
            test_system_matpower='data/grid/IEEE_30_bus_system.py',
            landscape_file='data/landscape/IEEE_30_bus_system_resolution_60.lcp',
            weather_files={
                'Autumn': 'data/weather/38.45_-120.90_2021_autumn.csv',
                'Summer': 'data/weather/38.45_-120.90_2021_summer.csv'
            },
            landscape_bounds=[-120.7, 37.6, -120, 38.1],
            landscape_resolution=60,
            farsite_perimeter_resolution=60,
            farsite_time_step=120,
            fuel_moistures=[[0, 6, 7, 8, 60, 90]],
            farsite_start=0,
            farsite_burn_periods=72,
            barriers_file='',
            crown_fire_method='Finney',
            ignition_points_number=3,
            ignition_points_distance=None,
            ignition_points_radius=10
        )
    """
    def __init__(
        self,
        analysis_run_title,
        test_system_topology,
        test_system_matpower,
        landscape_file,
        landscape_bounds,
        landscape_resolution,
        farsite_perimeter_resolution,
        farsite_time_step,
        fuel_moistures,
        weather_files,
        farsite_start=0,
        farsite_burn_periods=72,
        barriers_file='',
        crown_fire_method='Finney',
        ignition_points_number=3,
        ignition_points_distance=None,
        ignition_points_radius=10,
    ):
        self.id = 0
        self.analysis_run_title = analysis_run_title
        self.test_system_topology = test_system_topology
        self.test_system_matpower = test_system_matpower
        self.landscape_file = landscape_file
        self.landscape_bounds = landscape_bounds
        self.landscape_resolution = landscape_resolution
        self.farsite_perimeter_resolution = farsite_perimeter_resolution
        self.farsite_time_step = farsite_time_step
        self.fuel_moistures = fuel_moistures
        self.weather_files = weather_files
        self.farsite_start = farsite_start
        self.farsite_burn_periods = farsite_burn_periods
        self.barriers_file = barriers_file
        self.crown_fire_method = crown_fire_method
        self.ignition_points_number = ignition_points_number
        self.ignition_points_distance = ignition_points_distance
        self.ignition_points_radius = ignition_points_radius
        self.records_file = './outputs/records.csv'
        self.FARSITE_raws_template = './assets/FARSITE/templates/raws'
        self.FARSITE_input_template = './assets/FARSITE/templates/input'
        self.FARSITE_run_template = './assets/FARSITE/templates/run'
        self.scenarios = 0
        self.scenarios_done = 0

    # Validate, Build and Return the config instance
    def build(self, callback):

        # Validate analysis_run_title
        if not isinstance(self.analysis_run_title, str):
            return callback("ValueError", TITLE_ERROR)

        # Validate file paths
        files = [self.test_system_topology, self.test_system_matpower, self.landscape_file, self.barriers_file]
        for file in files:
            if not os.path.isfile(file) and file != "":
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
            if not os.path.isfile(file):
                return callback("ValueError", FILE_DOES_NOT_EXIST.format(file))

        # Validate crown_fire_method
        if self.crown_fire_method not in ["Finney", "Reinhardt"]:
            return callback("ValueError", CROWN_FIRE_ERROR)

        # Validate ignition_points_number and ignition_points_distance
        if (self.ignition_points_number is None and self.ignition_points_distance is None) or (self.ignition_points_number is not None and self.ignition_points_distance is not None):
            return callback("ValueError", IGNITION_POINT_VALUE_ERROR)

        # Validate ignition_points_radius
        if not isinstance(self.ignition_points_radius, int):
            return callback("ValueError", IGNITION_POINT_RADIUS_ERROR)
    
        # Save the inputs record and assign an ID for the config
        self.id = self.save_records()

        # Return status callback
        callback("update", ANALYSIS_INSTANTIATED.format(self.id, self.analysis_run_title))

        return self

    def generate_file_name(self, file_type, **kwargs):
        if file_type == 'ignition_points':
            file = f'./outputs/FARSITE/{self.id}/ignition_points/branch_{kwargs["branch_id"]}/point_{kwargs["point_id"]}.shp'
        elif file_type == 'weather':
            file = f'./outputs/FARSITE/{self.id}/weather_{kwargs["title"]}/FARSITE.raws'
        elif file_type == 'input':
            file = f'./outputs/FARSITE/{self.id}/weather_{kwargs["title"]}/FARSITE.input'
        elif file_type == 'run':
            file = f'./outputs/FARSITE/{self.id}/weather_{kwargs["title"]}/runs/branch_{kwargs["branch_id"]}/point_{kwargs["point_id"]}/FARSITE.run'
        elif file_type == 'outputs':
            file = f'./outputs/FARSITE/{self.id}/weather_{kwargs["title"]}/runs/branch_{kwargs["branch_id"]}/point_{kwargs["point_id"]}/Result_'
        elif file_type == 'scenarios':
            file = f'./outputs/reports/{self.id}/scenarios.csv'
        else:
            raise ValueError(f'Unsupported file_type: {file_type}')
        
        # Make sure the directory exists
        directory = os.path.dirname(file)
        if not os.path.exists(directory):
            os.makedirs(directory)
        
        return file

    def save_records(self):
        headers = [
            'ID',
            'analysis_run_title',
            'test_system_topology',
            'test_system_matpower',
            'landscape_file',
            'landscape_bounds',
            'landscape_resolution',
            'farsite_perimeter_resolution',
            'farsite_time_step',
            'farsite_start',
            'farsite_burn_periods',
            'fuel_moistures',
            'weather_files',
            'barriers_file',
            'crown_fire_method',
            'ignition_points_number',
            'ignition_points_distance',
            'ignition_points_radius',
            'date',
            'time',
            'scenarios',
            'elapsed',
            'status'
        ]

        # If the records file exists, read it into a DataFrame, otherwise create one
        if os.path.exists(self.records_file):
            df = pd.read_csv(self.records_file)
        else:
            df = pd.DataFrame(columns=headers)

        # Find the highest ID (if any) + 1
        if not df.empty:
            id = df['ID'].max() + 1
        else:
            id = 1

        now = datetime.now()

        # Create the new entry as a dictionary
        new_entry = {
            'ID': id,
            'analysis_run_title': self.analysis_run_title,
            'test_system_topology': self.test_system_topology,
            'test_system_matpower': self.test_system_matpower,
            'landscape_file': self.landscape_file,
            'landscape_bounds': str(self.landscape_bounds),
            'landscape_resolution': self.landscape_resolution,
            'farsite_perimeter_resolution': self.farsite_perimeter_resolution,
            'farsite_time_step': self.farsite_time_step,
            'farsite_start' : self.farsite_start,
            'farsite_burn_periods' : self.farsite_burn_periods,
            'fuel_moistures': str(self.fuel_moistures),
            'weather_files': str(self.weather_files),
            'barriers_file': self.barriers_file,
            'crown_fire_method': self.crown_fire_method,
            'ignition_points_number': self.ignition_points_number,
            'ignition_points_distance': self.ignition_points_distance,
            'ignition_points_radius': self.ignition_points_radius,
            'date': now.strftime('%Y-%m-%d'),
            'time': now.strftime('%H:%M:%S'),
            'scenarios': '',
            'elapsed': '',
            'status': 'config setup'
        }

        # Append the new entry to the DataFrame and save it
        new_entry_series = pd.Series(new_entry, index=df.columns)
        df = pd.concat([df, new_entry_series.to_frame().T], ignore_index=True)
        df.to_csv(self.records_file, index=False)

        return id
    
    def update_record(self, **kwargs):

        df = pd.read_csv(self.records_file)

        if self.id not in df['ID'].values:
            raise ValueError(RECORD_DOES_NOT_EXIST.format(self.id))

        # Update the specified columns
        for column_name, value in kwargs.items():
            if column_name in df.columns:
                df.loc[df['ID'] == self.id, column_name] = value
            else:
                raise KeyError(RECORD_COLUMN_INVALID.format(column_name))

        # Save the updated DataFrame to the CSV file
        df.to_csv(self.records_file, index=False)
    
    # Save a table of all FARSITE simulation scenarios
    def save_scenarios(self, scenarios):
        df = pd.DataFrame(scenarios)
        df.to_csv(self.generate_file_name('scenarios'), index=True)