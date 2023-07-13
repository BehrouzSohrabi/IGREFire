"""
IGREFire
Integrated Grid Resilience Evaluation Framework against wildFires

This script serves as the entry point for the IGREFire Framework.
The script initializes the graphical user interface (GUI) that allows users to
configure the inputs and run an analysis.

The GUI includes the following features:
1. Configuration of analysis parameters.
2. Progress tracking during the analysis.
3. Display of analysis results in a tabular format.

To run GUI, execute the following command in your terminal:
python main.py --gui

To run the script with a set of default configurations, execute the following command:
python main.py

Author:
Date:
"""
import os
import sys
import csv
import json
import warnings
warnings.simplefilter(action='ignore', category=FutureWarning)

from src.utils import callback
from src.main import Analysis
from src.config import Config
from src.GUI import GUI

def get_files_options(folder, format):
    return [folder+f for f in os.listdir(folder) if f.endswith(format)]

def select_from_list(prompt, choices, idx = False):

    print(f"\n{prompt}")
    for i, choice in enumerate(choices):
        print(f"    {i+1}. {choice}")
    
    try:
        selection = int(input('    Enter #: ')) - 1
    except:
        print('Invalid Input')
        return None
    
    return selection if idx else choices[selection]

def select_from_list_multiple(prompt, choices):

    print(f"\n{prompt}")
    for i, choice in enumerate(choices):
        print(f"    {i+1}. {choice}")
    
    try:
        selections = list(map(int, input('    Enter #: ').split(',')))
    except:
        print('Invalid Input')
        return None

    return json.dumps({selection: choices[selection-1] for selection in selections})

def select_from_list_id(prompt, choices):

    print(f"\n{prompt}")
    for i, choice in choices:
        print(f"    {i}. {choice}")
    
    try:
        selection = int(input('    Enter #: '))
    except:
        print('Invalid Input')
        return None
    
    return selection

if __name__ == '__main__':

    callback('header-top', 'IGREFire')
    callback('header-sub', 'Integrated Grid Resilience Evaluation Against Wildfire Framework')

    new_or_load = select_from_list("Create a new analysis or load a previously created one?", ["New", "Load"])
    impact_file = ''

    if new_or_load == "New":
        analysis_run_title = input("Enter a title for the analysis: ")

        callback('', 'Input Layers:')
        test_system_topology = select_from_list("Select a GeoJSON file for the test system topology: ", get_files_options('data/grid/', '.geojson'))
        test_system_matpower = select_from_list("Select a Matpower file of the test system: ", get_files_options('data/grid/', '.py'))
        landscape_file = select_from_list("Select a LCP landscape file: ", get_files_options('data/landscape/', '.lcp'))
        # landscape_bounds = input_json_list("Enter bounding box coordinates of the LCP matched with the topology in degrees [W, S, E, N]: ")
        landscape_resolution = select_from_list("Select resolution of the LCP file in meters: ", [30, 60, 90, 120, 180, 270])

        weather_files = select_from_list_multiple("Select weather stream dataframes: (separate with ,)", get_files_options('data/weather/', '.csv'))
        weather_conditions = input("Enter JSON inputs for synthetic weather conditions: ") or '{}'

        callback('', 'FARSITE Options:\n')
        farsite_perimeter_resolution = int(input(f"Perimeters resolution in meters (default = {landscape_resolution}): ") or landscape_resolution)
        farsite_time_step = int(input("Fire spread progression steps in minutes (default = 120): ") or 120)
        farsite_start = int(input("Start date row ID in weather files (default = 0): ") or 0)
        farsite_burn_periods = int(input("Steps duration (default = 96): ") or 96)
        # fuel_moistures = input_json_list("Enter fuel moisture profiles for each fuel model in the LCP file: ")
        # barriers_file = input("Enter path to the optional shapefile containing barriers (press enter to skip): ")
        crown_fire_method = select_from_list("Crown fire calculation method: ", ['Finney', 'Reinhardt'])

        callback('', 'Optimal Power Flow Method:')
        OPF_method = select_from_list("Crown fire calculation method: ", ['AC', 'DC'])

        callback('', 'Scenarios Options:\n')
        ignition_points_radius = int(input("Enter radius of the ignition points in meters: "))
        ignition_points_number = int(input("Number of ignition points per line: (0 for skip)") or 0)
        ignition_points_distance = int(input("Distance between ignition points in meters: "))
        
        # branch_effects = input_json_list("Enter how branches will be affected by wildfire: ")

        # Analysis Default Config Inputs
        config = Config(
            analysis_run_title = analysis_run_title,
            test_system_topology = test_system_topology,
            test_system_matpower = test_system_matpower,
            landscape_file = landscape_file,
            landscape_resolution = landscape_resolution,
            weather_files = weather_files,
            weather_conditions = weather_conditions,

            farsite_perimeter_resolution = farsite_perimeter_resolution,
            farsite_time_step = farsite_time_step,
            farsite_start = farsite_start,
            farsite_burn_periods = farsite_burn_periods,
            crown_fire_method = crown_fire_method,

            OPF = OPF_method,

            ignition_points_radius = ignition_points_radius,
            ignition_points_number = ignition_points_number,
            ignition_points_distance = ignition_points_distance,
        )

        # config = Config(
        #     analysis_run_title = 'IEEE BUS 30 - 2+4 Weathers - 1Km',
        #     test_system_topology = 'data/grid/IEEE_30_bus_system_labeled.geojson',
        #     ignition_points_distance = 1000,
        #     weather_files = '{"Fall": "data/weather/38.45_-120.90_2021_fall.csv", "Summer": "data/weather/38.45_-120.90_2021_summer.csv"}',
        #     weather_conditions = '{"Wind-N": {"wind_direction": {"degree":0}}, "Wind-E": {"wind_direction": {"degree":90}}, "Wind-S": {"wind_direction": {"degree":180}}, "Wind-W": {"wind_direction": {"degree":270}}}'
        # )

    elif new_or_load == "Load":
        with open('outputs/records.csv', 'r') as f:
            reader = csv.reader(f)
            analyses = list(reader)
        selected_idx = select_from_list_id("Select an analysis to load: ", [[analysis[0], f"{analysis[1]} - {analysis[2]}"] for analysis in analyses if analysis[0] != 'id'])

        # Load config by record ID
        config = Config(record_id=selected_idx)

        #  Check FARSITE Impact
        # impact_file = 'data/grid/IEEE_30_bus_system_check.json'

    else:
        print("Invalid option")

    # Ask the user the step of analysis
    analyses_stage = select_from_list("Select analysis stage: ", [
        "Wildfire Scenarios Generation",
        "Run FARSITE: Wildfire Spread Simulation",
        "Impact Analysis & Network Modification",
        "Run Optimal Power Flow Analysis",
        "Metrics Calculations & Report"
    ], idx = True)

    # Ask analysis flow
    analyses_progress = select_from_list("Analysis Mode: ", [
        "Progressive",
        "Only run the selected stage"
    ], idx = True) if analyses_stage < 4 else 1
    
    # Validate and build the config
    config.build()

    # Instantiate Analysis Object
    analysis = Analysis(config)

    # Initialize and Run the wildfire risk assessment framework with the configuration.
    if len(sys.argv) > 1 and sys.argv[1] == '--gui':
        GUI(analysis).launch()
    else:
        # Run a thorough analysis
        # analysis.run()

        # Run individual steps of the analysis
        if (analyses_stage <= 0 and analyses_progress == 0) or (analyses_stage == 0 and analyses_progress == 1):
            analysis._generate_inputs()
        if (analyses_stage <= 1 and analyses_progress == 0) or (analyses_stage == 1 and analyses_progress == 1):
            analysis._run_simulations(impact_file)
        if (analyses_stage <= 2 and analyses_progress == 0) or (analyses_stage == 2 and analyses_progress == 1):
            analysis._prepare_matpower(impact_file)
        if (analyses_stage <= 3 and analyses_progress == 0) or (analyses_stage == 3 and analyses_progress == 1):
            analysis._run_powerflow()
        if (analyses_stage <= 4 and analyses_progress == 0) or (analyses_stage == 4 and analyses_progress == 1):
            analysis._report()