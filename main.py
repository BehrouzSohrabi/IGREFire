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

from src.analysis import Analysis
from src.config import Config
from src.GUI import GUI

if __name__ == '__main__':

    # Analysis Default Config Inputs
    # config = Config(
    #     analysis_run_title = 'IEEE BUS 30 Basic Run - High Resolution',
    # )

    # Load config by ID
    config = Config(id=2)

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
        # analysis._generate_inputs()
        # analysis._run_simulations()
        # analysis._prepare_matpower()
        analysis._run_powerflow()
        # analysis._visualize_results()