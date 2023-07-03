import numpy as np
import pandas as pd

from .messages import *
from .utils import callback, progress_bar

from assets.pypower.runopf import runopf

class PowerFlow:
    
    # Class Constructor
    def __init__(self, config):
        
        config.read_scenarios()
        self.config = config
        
    def run(self):

        def process_scenario(config, standard_output, row):
            scenario_data = {}
            
            # Run power flow analysis for the scenario with the modified MATPOWER file
            _, extension, case_name = config.read_MATPOWER_path()
            for branch_effect in config.branch_effects:

                # Run a Standard Powerflow
                MATPOWER_file = config.generate_file_name(
                    f'MATPOWER_{branch_effect}',
                    weather=row['Weather'],
                    branch_id=row['Branch'],
                    point_id=row['Ignition Point'],
                    matpower_file=f'{case_name}{extension}')
                output_file = config.generate_file_name(
                    f'powerflow_output_{branch_effect}_branch',
                    weather=row['Weather'],
                    branch_id=row['Branch'],
                    point_id=row['Ignition Point']
                )
                scenario_output = runopf(MATPOWER_file, fname=output_file)

                # Extract loads on each bus from standard scenario with no isolate bus
                loads = {int(load[0]): load[2] for load in standard_output['bus']}
                gen_dict = {int(gen[0]): gen[1] for gen in scenario_output['gen']}
                outages = {bus: gen_dict.get(bus, load) if load > 0 else 0 for bus, load in loads.items()}
                
                # Save Bus Loads and Outages
                total_outage = 0
                total_load = 0
                for bus, load in loads.items():
                    outage = outages.get(bus, load)
                    total_outage += outage
                    total_load += load
                    scenario_data[f'Bus Load {bus}'] = load
                    scenario_data[f'Bus Outage {bus}'] = outage
                scenario_data['Total Outage'] = total_outage
                scenario_data['Total Load'] = total_outage

            return scenario_data

        # Start running powerflow analysis
        callback('update', POWERFLOW_STANDARD)

        # Run standard power flow analysis with the initial MATPOWER file
        output = self.config.generate_file_name('powerflow_output_standard')
        standard_output = runopf(self.config.test_system_matpower, fname=output)

        callback('update', POWERFLOW_SCENARIOS)

        print() # wrap progress bar

        # Iterate over scenarios
        scenario_list = []
        for index, row in self.scenarios.iterrows():

            # Show progress bar
            id = index+1
            description = POWERFLOW_SCENARIOS_DESCRIPTION.format(id, row["Branch"], row["Ignition Point"], row["Weather"])
            progress_bar(id, self.config.scenarios, prefix='Progress:', description=description)

            scenario_data = process_scenario(self.config, standard_output, row)
            scenario_list.append(scenario_data)
    
        print() # wrap progress bar

        # Drop any old columns
        cols_to_remove = self.scenarios.filter(regex='^(Bus Load|Bus Outage|Total Outage|Total Load)').columns
        self.scenarios = self.scenarios.drop(columns=cols_to_remove)

        # Only add columns from scenario_df that do not already exist
        scenario_df = pd.DataFrame(scenario_list)
        self.scenarios = pd.concat([self.scenarios, scenario_df.loc[:, ~scenario_df.columns.isin(self.scenarios.columns)]], axis=1)

        # Update Analysis Records with new powerflow output data (loads, outages, total outages, and Total Load)
        self.scenarios.to_csv(self.config.scenarios_file, index=True)
        self.config.update_record(status='Powerflow Finished')

        # Update Analysis Status
        callback('update', POWERFLOW_FINISHED)