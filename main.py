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
import os

from src.analysis import Analysis
from src.config import Config
from src.GUI import AnalysisGUI

if __name__ == '__main__':

    # Analysis Default Config Inputs
    config = Config(
        analysis_run_title = 'IEEE BUS 30 Basic Run',
        test_system_topology = './data/grid/IEEE_30_bus_system.geojson',
        test_system_matpower = './data/grid/IEEE_30_bus_system.py',
        landscape_file = './data/landscape/IEEE_30_bus_system_resolution_60.lcp',
        landscape_bounds = [-120.7, 37.6, -120, 38.1],
        landscape_resolution = 60,
        farsite_perimeter_resolution = 60,
        farsite_time_step = 120,
        fuel_moistures = [[0, 6, 7, 8, 60, 90]],
        weather_files = {
            'Autumn': './data/weather/38.45_-120.90_2021_autumn.csv',
            'Summer': './data/weather/38.45_-120.90_2021_summer.csv'
        }
    )

    # Initialize and Run the wildfire risk assessment framework with the configuration.
    if len(sys.argv) > 1 and sys.argv[1] == '--gui':
        AnalysisGUI(config).launch()
    else:
        Analysis(config).run()