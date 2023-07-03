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
import sys
import warnings
warnings.simplefilter(action='ignore', category=FutureWarning)

from src.main import Analysis
from src.config import Config
from src.GUI import GUI

if __name__ == '__main__':

    # Analysis Default Config Inputs
    config = Config(
        analysis_run_title = 'IEEE BUS 30 - 2+4 Weathers - 1Km',
        test_system_topology = 'data/grid/IEEE_30_bus_system_labeled.geojson',
        ignition_points_distance = 1000,
        weather_files = '{"Fall": "data/weather/38.45_-120.90_2021_fall.csv", "Summer": "data/weather/38.45_-120.90_2021_summer.csv"}',
        weather_conditions = '{"Wind-N": {"wind_direction": {"degree":0}}, "Wind-E": {"wind_direction": {"degree":90}}, "Wind-S": {"wind_direction": {"degree":180}}, "Wind-W": {"wind_direction": {"degree":270}}}'
    )

    # Load config by record ID
    config = Config(record_id=7)

    # Validate and build the config
    # config.build()

    # Instantiate Analysis Object
    analysis = Analysis(config)

    # Initialize and Run the wildfire risk assessment framework with the configuration.
    if len(sys.argv) > 1 and sys.argv[1] == '--gui':
        GUI(analysis).launch()
    else:
        # Run a thorough analysis
        # analysis.run()

        # Run individual steps of the analysis
        # analysis._generate_inputs()
        # analysis._run_simulations('data/grid/IEEE_30_bus_system_check.json')
        # analysis._prepare_matpower('data/grid/IEEE_30_bus_system_check.json')
        # analysis._run_powerflow()
        analysis._report()