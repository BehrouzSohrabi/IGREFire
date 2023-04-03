import pandas as pd
import subprocess

from .messages import *
from .utils import callback, progress_bar

class FARSITE:
    
    # Class Constructor
    def __init__(self, config):

        self.config = config
    
    def run_farsite(self, run_dir, description=''):

        # Command to run FARSITE
        cmd = f'{self.config.FARSITE} {run_dir}{self.config.FARSITE_run_file}'
        log_file_name = self.config.generate_file_name('FARSITE_log')

        # Run the process and write outputs to a log file
        with open(log_file_name, "a") as log_file:
            log_file.write(f'> {description}\n')
            subprocess.run(cmd, shell=True, stdout=log_file, stderr=log_file)

        # Read the contents of the log file
        with open(log_file_name, 'r') as log_file:
            log_contents = log_file.read()

        # Check if FARSITE prompts invalid inputs
        if "invalid" in log_contents.lower():
            callback('Exception', FARSITE_ERROR.format(log_contents))
            return None

        return True

    def run(self):
        
        # Update Analysis Status
        callback('update', FARSITE_SCENARIOS.format(self.config.scenarios))
        
        print() # wrap progress bar

        # Iterate over scenarios
        scenarios = self.config.read_scenarios()
        for index, row in scenarios.iterrows():
            
            # Show progress bar
            id = index+1
            description = FARSITE_DESCRIPTION.format(id, row["Branch"], row["Ignition Point"], row["Title"])
            progress_bar(id, self.config.scenarios, prefix='Progress:', description=description)
            
            # Run FARSITE Simulation
            self.run_farsite(row["Run Directory"], description)

        print() # wrap progress bar

        # Update Analysis Status
        callback('update', FARSITE_FINISHED)

        # Update Analysis Records
        self.config.update_record(status='FARSITE Finished')