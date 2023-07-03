import shapefile
import string
import pandas as pd
from shapely.geometry import Point
from datetime import datetime, timedelta

from .utils import cloud_cover_mapping, wind_direction_curve, wind_speed_curve, temperature_curve, humidity_curve, traverse_branch, arrays_to_string, callback
from .messages import *

class Inputs:

    # Class Constructor
    def __init__(self, config):

        config.read_topology()
        self.config = config

        # Find and Iterate over the ignition points on each branch
        self.points = traverse_branch(
            config.topology,
            config.geod,
            config.ignition_points_number,
            config.ignition_points_distance
        )
    
    def _read_elevation(self, file):
        df = pd.read_csv(file, nrows=1)
        elevation = df['Elevation'][0]
        return elevation
    
    def _create_ignition_points(self):

        ignition_files = []

        for branch in self.points:
            for i, point in enumerate(branch['branch_points']):

                # Calculate relative position of ignition point to LCP file coordinates
                x = self.config.geod.inv(self.config.center.x, self.config.center.y, point.x, self.config.center.y)[2]
                y = self.config.geod.inv(self.config.center.x, self.config.center.y, self.config.center.x, point.y)[2]
                if point.x < self.config.center.x:
                    x = -x
                if point.y < self.config.center.y:
                    y = -y

                # Create fire ignition shapefile for each specified radius
                point_id = i+1
                radius = self.config.ignition_points_radius
                file_name = self.config.generate_file_name('ignition_points', branch_id=branch["branch_id"], point_id=point_id)

                # Write shapefile
                sf = shapefile.Writer(file_name, shapeType=shapefile.POLYGON)
                sf.field('name', 'C')
                sf.record('Circle')
                sf.poly([Point(x, y).buffer(radius).exterior.coords])
                sf.close()

                # Ignition Files Metadata
                ignition_files.append({
                    'Branch': branch['branch_id'],
                    'Ignition Point': point_id,
                    'Ignition Point X': point.x,
                    'Ignition Point Y': point.y,
                    'Ignition File': file_name,
                })
                
        return ignition_files
    
    def _create_weather_stream(self):
        
        # Calculate Burn Periods which is checked at each weather stream row
        def calculate_burn_periods(burn_periods, last_day, day, month):
            if day != last_day:
                last_day = day
                burn_periods.append([
                    f"{int(month)}",
                    f"{int(day)}",
                    "0",
                    "2359"
                ])
            return burn_periods, last_day

        # Write and return weather stream raws summary
        def write_raws(weather_summary, weather_title, raws, elevation, burn_periods):
            # Read the input template file
            with open(self.config.FARSITE_raws_template, 'r') as f:
                template = string.Template(f.read())
            
            # Substitute the placeholders with the actual values and Write the output to a new file
            file_name = self.config.generate_file_name('weather', weather=weather_title)
            params = {
                'elevation': elevation,
                'rows_length': len(raws),
                'rows': arrays_to_string(raws)
            }
            with open(file_name, 'w') as f:
                f.write(template.substitute(params))

            # Weather Files Metadata
            weather_summary.append({
                'Weather' : weather_title,
                'Weather File': file_name,
                'Burn Periods': burn_periods
            })

            return weather_summary

        # Summary of the generated weather files
        weather_summary = []
        
        # Using provided weather stream
        if self.config.weather_files:
            for weather_title, file in self.config.weather_files.items():

                # Select the rows based on farsite_start and farsite_burn_periods
                df = pd.read_csv(file, skiprows=2)
                df = df.iloc[self.config.farsite_start : self.config.farsite_start + self.config.farsite_burn_periods]

                # populate input data
                raws = []
                burn_periods = []
                last_day = 0
                elevation = self._read_elevation(file)

                for _, row in df.iterrows():
                    raws.append([
                        f"{int(row['Year'])}",
                        f"{int(row['Month']):02}",
                        f"{int(row['Day']):02}",
                        f"{int(row['Hour']):02}00",
                        f"{row['Temperature']:.2f}",
                        f"{row['Relative Humidity']:.2f}",
                        f"{row['Precipitable Water']/100:.2f}",
                        f"{round(row['Wind Speed'])}",
                        f"{round(row['Wind Direction'])}",
                        f"{cloud_cover_mapping[row['Cloud Type']]:.2f}"
                    ])
                    burn_periods, last_day = calculate_burn_periods(burn_periods, last_day, row['Day'], row['Month'])

                # Write and return summary
                weather_summary = write_raws(weather_summary, weather_title, raws, elevation, burn_periods)

        # Create Synthetic Data
        if self.config.weather_conditions:
            
            # Needs update to match any given data as arguments for curve functions in util
            # sample = {
            #     "N": {"wind_direction": {"degree":0}},
            #     "S": {"wind_direction": {"degree":180}}
            # }
            
            hours = self.config.farsite_burn_periods
            start_date = datetime.strptime(datetime.now().strftime('%Y-%m-%d'), '%Y-%m-%d')

            for weather_title, weather_info in self.config.weather_conditions.items():

                # populate input data
                raws = []
                burn_periods = []
                last_day = 0
                elevation = 200

                for i in range(hours):
                    date = start_date + timedelta(hours=i)
                    year = date.year
                    month = date.month
                    day = date.day
                    hour = date.hour
                    raws.append([
                        f"{int(year)}",
                        f"{int(month):02}",
                        f"{int(day):02}",
                        f"{int(hour):02}00",
                        f"{temperature_curve(i):.2f}",
                        f"{humidity_curve(i):.2f}",
                        "0.00",
                        f"{round(wind_speed_curve(i))}",
                        f"{round(wind_direction_curve(weather_info['wind_direction']['degree']))}",
                        "0.00"
                    ])
                    burn_periods, last_day = calculate_burn_periods(burn_periods, last_day, day, month)

                # Write and return summary
                weather_summary = write_raws(weather_summary, weather_title, raws, elevation, burn_periods)
        
        return weather_summary

    def _create_FARSITE_input(self, weather_summary):

        input_files = []

        for weather_file in weather_summary:

            # Read the input template file
            with open(self.config.FARSITE_input_template, 'r') as f:
                template = string.Template(f.read())
            
            # Substitute the placeholders with the actual values and Write the output to a new file
            file_name = self.config.generate_file_name('input', weather=weather_file['Weather'])
            params = {
                'time_step': self.config.farsite_time_step,
                'landscape_resolution': self.config.landscape_resolution,
                'perimeter_resolution': self.config.farsite_perimeter_resolution,
                'start_time': ' '.join(weather_file['Burn Periods'][0])[:-5],
                'end_time': ' '.join(weather_file['Burn Periods'][-1])[:-7] + ' 2359',
                'burn_periods_length': len(weather_file['Burn Periods']),
                'burn_periods': arrays_to_string(weather_file['Burn Periods']),
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
                run_dir = self.config.generate_file_name('run', weather=input_file['Weather'], branch_id=ignition_file['Branch'], point_id=ignition_file['Ignition Point'])
                params = {
                    'landscape': self.config.landscape_file,
                    'input': input_file['Input File'],
                    'ignition': ignition_file['Ignition File'],
                    'barrier': ("0" if self.config.barriers_file == '' else self.config.barriers_file),
                    'output_dir': run_dir
                }
                with open(f'{run_dir}{self.config.FARSITE_run_file}', 'w') as f:
                    f.write(template.substitute(params))

                # combine scenario's ignition and input entries
                run_file = {**ignition_file, **input_file}
                run_file['Run Directory'] = run_dir

                # delete unnecessary entries
                del run_file['Burn Periods']
                del run_file['Weather File']
                del run_file['Input File']
                
                # append to scenario run file summary info
                run_files.append(run_file)
        
        return run_files
    
    def generate(self):
        # Update Analysis Status
        callback('update', INPUT_GENERATION_STARTED)

        # Generate Simulation Input Files
        ignition_files = self._create_ignition_points()
        weather_files = self._create_weather_stream()
        input_files = self._create_FARSITE_input(weather_files)
        scenarios_run_files = self._create_FARSITE_run(ignition_files, input_files)

        # Update Analysis Record
        self.config.save_scenarios(scenarios_run_files)
        self.config.update_record(status='Inputs Ready')