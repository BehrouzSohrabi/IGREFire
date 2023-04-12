from .messages import *
from .utils import callback, progress_bar

from assets.pypower.runopf import runopf

class PowerFlow:
    
    # Class Constructor
    def __init__(self, config):
        
        self.config = config

        self.scenarios = self.config.read_scenarios()
        
    def run(self):

        callback('update', POWERFLOW_STANDARD)

        # Run standard power flow analysis with the initial MATPOWER file
        output = self.config.generate_file_name('powerflow_output_standard')

        standard_output = runopf(self.config.test_system_matpower, fname=output)

        callback('update', POWERFLOW_SCENARIOS)

        print() # wrap progress bar

        # Iterate over scenarios
        for index, row in self.scenarios.iterrows():

            # Show progress bar
            id = index+1
            if id != 1: continue
            description = POWERFLOW_SCENARIOS_DESCRIPTION.format(id, row["Branch"], row["Ignition Point"], row["Weather"])
            progress_bar(id, self.config.scenarios, prefix='Progress:', description=description)

            # Run power flow analysis for the scenario with the modified MATPOWER file
            _, extension, case_name = self.config.read_MATPOWER_path()
            for branch_effect in self.config.branch_effects:
                MATPOWER_file = self.config.generate_file_name(f'MATPOWER_{branch_effect}', weather=row['Weather'], branch_id=row['Branch'], point_id=row['Ignition Point'], matpower_file=f'{case_name}{extension}')
                output_file = self.config.generate_file_name(f'powerflow_output_{branch_effect}_branch', weather=row['Weather'], branch_id=row['Branch'], point_id=row['Ignition Point'])
                scenario_output = runopf(MATPOWER_file, fname=output_file)

                # Use the successful scenario
                if scenario_output['success']:
                    break
            
            # print(scenario_output['order'])

            # dict_keys(['baseMVA', 'bus', 'gen', 'branch', 'gencost', 'areas', 'order', 'om', 'x', 'mu', 'f', 'var', 'lin', 'nln', 'et', 'success', 'raw'])

            # if not scenario_output['success']:
                # print(scenario_output['success'])

            # Append analysis outputs to scenario df
            # for key, value in affected_lines.items():
                # self.scenarios.at[index, f'Affect Branch {key}'] = value
            
            # Compare to the standard powerflow
            # Find Branches Differences
            # Find Bus Generation Differences
    
            # break # TEST for the first point
    
        print() # wrap progress bar

        # Update Analysis Status
        callback('update', POWERFLOW_FINISHED)

        # Update Analysis Records
        self.scenarios.to_csv(self.config.scenarios_file, index=True)
        self.config.update_record(status='Powerflow Finished')