import json
import shapefile
import string
import pandas as pd
from pyproj import Geod
from shapely.geometry import shape, Point, Polygon

from .utils import cloud_cover_mapping, arrays_to_string
from .messages import *

class InputsGenerator:

    # Class Constructor
    def __init__(self, config, callback, step):

        self.step = step
        self.config = config
        self.callback = callback
        self.topology = self._validate_topology()
        self._center = self._find_centroid() # Centroid of the LCP file
        self._geod = Geod(ellps='WGS84') # Coordinates System Transform Projection

    def _validate_topology(self):

        # Read GeoJSON file
        with open(self.config.test_system_topology) as f:
            topology = json.load(f)

        # Check if at least one branch exists
        branch_found = False
        for feature in topology['features']:
            if feature['geometry']['type'] == 'LineString':
                branch_found = True

                # Check if branch has the necessary properties fields
                if 'branch' not in feature['properties']:
                    self.callback("ValueError", MISSING_BRANCH_PROPERTY, self.step)

        if not branch_found:
            self.callback("ValueError", NO_LINESTRING_FEATURES, self.step)
        
        return topology

    def _find_centroid(self):
        xmin, ymin, xmax, ymax = self.config.landscape_bounds
        boundary = Polygon([(xmin, ymin), (xmax, ymin), (xmax, ymax), (xmin, ymax)])
        return boundary.centroid
    
    def _read_elevation(self, file):
        df = pd.read_csv(file, nrows=1)
        elevation = df['Elevation'][0]
        return elevation
    
    def _traverse_branch(self):

        points = []

        # loop through features and pick point on branches
        for feature in self.topology['features']:
            if feature['geometry']['type'] == 'LineString': # check if feature is a branch
                branch_points = []
                branch_id = feature['properties']['branch']
                branch_line = shape(feature['geometry'])

                # Calculate the Geodesic length in meters
                length = 0
                x_0, y_0 = branch_line.coords[0]
                for x, y in branch_line.coords[1:]:
                    partial_length = self._geod.inv(x_0, y_0, x, y)[2]
                    length += partial_length
                    x_0, y_0 = x, y
                geo_scale = branch_line.length / length

                # Fixed number of ignition points per branch
                if self.config.ignition_points_number:
                    step = length / self.config.ignition_points_number
                    initial_distance = step / 2
                # Fixed length between ignition points on all branches
                else:
                    step = self.config.ignition_points_distance
                    initial_distance = (length / 2) % step

                # move over the branch until it's covered
                i = 0
                while True:
                    distance = geo_scale * (initial_distance + (i * step))
                    if distance > branch_line.length:
                        break
                    i += 1

                    # find point at this distance along branch
                    point = branch_line.interpolate(distance)
                    branch_points.append(point)
                points.append({"branch_id": branch_id, "branch_points": branch_points})
                
        return points

    def _create_ignition_points(self):

        ignition_files = []

        # Find and Iterate over the ignition points on each branch
        points = self._traverse_branch()
        for branch in points:
            for i, point in enumerate(branch['branch_points']):

                # Calculate relative position of ignition point to LCP file coordinates
                x = self._geod.inv(self._center.x, self._center.y, point.x, self._center.y)[2]
                y = self._geod.inv(self._center.x, self._center.y, self._center.x, point.y)[2]
                if point.x < self._center.x:
                    x = -x
                if point.y < self._center.y:
                    y = -y

                # Create fire ignition shapefile for each specified radius
                radius = self.config.ignition_points_radius
                file_name = self.config.generate_file_name('ignition_points', branch_id=branch["branch_id"], point_id=i)

                # Write shapefile
                sf = shapefile.Writer(file_name, shapeType=shapefile.POLYGON)
                sf.field('name', 'C')
                sf.record('Circle')
                sf.poly([Point(x, y).buffer(radius).exterior.coords])
                sf.close()

                # Ignition Files Metadata
                ignition_files.append({
                    'Branch': branch['branch_id'],
                    'Ignition Point': i,
                    'Ignition Point X': point.x,
                    'Ignition Point Y': point.y,
                    'Ignition File': file_name,
                })
                
        return ignition_files
    
    def _create_weather_stream(self):

        weather_files = []

        for title, file in self.config.weather_files.items():

            # Select the rows based on farsite_start and farsite_burn_periods
            df = pd.read_csv(file, skiprows=2)
            df = df.iloc[self.config.farsite_start : self.config.farsite_start + self.config.farsite_burn_periods]

            # populate input data
            raws = []
            burn_periods = []
            for _, row in df.iterrows():
                raws.append([
                    f"{int(row['Year'])}",
                    f"{int(row['Month']):02}",
                    f"{int(row['Day']):02}",
                    f"{int(row['Hour']):02}00 {row['Temperature']:.2f}",
                    f"{row['Relative Humidity']:.2f}",
                    f"{row['Precipitable Water']:.2f}",
                    f"{round(row['Wind Speed'])}",
                    f"{round(row['Wind Direction'])}",
                    f"{cloud_cover_mapping[row['Cloud Type']]:.2f}"
                ])
                burn_periods.append([
                    f"{int(row['Month'])}",
                    f"{int(row['Day'])}",
                    "0",
                    "2359"
                ])

            # Read the input template file
            with open(self.config.FARSITE_raws_template, 'r') as f:
                template = string.Template(f.read())
            
            # Substitute the placeholders with the actual values and Write the output to a new file
            file_name = self.config.generate_file_name('weather', title=title)
            params = {
                'elevation': self._read_elevation(file),
                'rows_length': len(raws),
                'rows': arrays_to_string(raws)
            }
            with open(file_name, 'w') as f:
                f.write(template.substitute(params))

            # Weather Files Metadata
            weather_files.append({
                'Title' : title,
                'Weather File': file_name,
                'Burn Periods': arrays_to_string(burn_periods)
            })

        return weather_files

    def _create_FARSITE_input(self, weather_files):

        input_files = []

        for weather_file in weather_files:

            # Read the input template file
            with open(self.config.FARSITE_input_template, 'r') as f:
                template = string.Template(f.read())
            
            # Substitute the placeholders with the actual values and Write the output to a new file
            file_name = self.config.generate_file_name('input', title=weather_file['Title'])
            params = {
                'time_step': self.config.farsite_time_step,
                'landscape_resolution': self.config.landscape_resolution,
                'perimeter_resolution': self.config.farsite_perimeter_resolution,
                'start_date': weather_file['Burn Periods'][0][:-5],
                'end_date': weather_file['Burn Periods'][-1][:-7] + ' 2359',
                'burn_periods_length': len(weather_file['Burn Periods']),
                'burn_periods': weather_file['Burn Periods'],
                'fuel_moistures_length': len(self.config.fuel_moistures),
                'fuel_moistures': arrays_to_string(self.config.fuel_moistures),
                'weather_stream_file': weather_file['Weather File'],
                'crown_fire_method': self.config.crown_fire_method
            }
            with open(file_name, 'w') as f:
                f.write(template.substitute(params))
            
            # Input Files Metadata
            weather_file['Input File'] = file_name
            input_files.append(weather_file)

        return input_files

    def _create_FARSITE_run(self, ignition_files, input_files):

        run_files = []

        for ignition_file in ignition_files:
            for input_file in input_files:

                # Read the run template file
                with open(self.config.FARSITE_run_template, 'r') as f:
                    template = string.Template(f.read())
                
                # Substitute the placeholders with the actual values and Write the output to a new file
                file_name = self.config.generate_file_name('run', title=input_file['Title'], branch_id=ignition_file['Branch'], point_id=ignition_file['Ignition Point'])

                params = {
                    'landscape': self.config.landscape_file,
                    'input': input_file['Input File'],
                    'ignition': ignition_file['Ignition File'],
                    'barrier': ("0" if self.config.barriers_file == '' else self.config.barriers_file),
                    'output_dir': self.config.generate_file_name('outputs', title=input_file['Title'], branch_id=ignition_file['Branch'], point_id=ignition_file['Ignition Point'])
                }
                with open(file_name, 'w') as f:
                    f.write(template.substitute(params))

                run_file = {**ignition_file, **input_file}
                run_file['Run File'] = file_name
                del run_file['Burn Periods']
                run_files.append(run_file)
        
        return run_files
    
    def run(self):
        # Update Analysis Status
        self.callback('update', INPUT_GENERATION_STARTED, self.step)

        # Generate Simulation Input Files
        ignition_files = self._create_ignition_points()
        weather_files = self._create_weather_stream()
        input_files = self._create_FARSITE_input(weather_files)
        scenarios_run_files = self._create_FARSITE_run(ignition_files, input_files)

        # Update Analysis Record
        self.config.update_record(scenarios=len(scenarios_run_files), status='inputs ready')
        self.config.save_scenarios(scenarios_run_files)

        return scenarios_run_files