import pandas as pd
import subprocess
from os import remove, listdir, path

from .messages import *
from .utils import callback, progress_bar

class FARSITE:
    
    # Class Constructor
    def __init__(self, config):

        config.read_scenarios()
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

        # Remove Unnecessary Files
        for filename in listdir(run_dir):
            for prefix in self.config.FARSITE_remove_files:
                if filename.startswith(prefix):
                    file_path = path.join(run_dir, filename)
                    remove(file_path)
                    break

        return True

    def run(self, impact_file=''):
        
        # Update Analysis Status
        callback('update', FARSITE_SCENARIOS.format(self.config.scenarios_rows))
        
        print() # wrap progress bar

        # Iterate over scenarios
        for index, row in self.config.scenarios.iterrows():
            
            # Show progress bar
            id = index+1
            description = FARSITE_DESCRIPTION.format(id, row["Branch"], row["Ignition Point"], row["Weather"])
            progress_bar(id, self.config.scenarios_rows, prefix='Progress:', description=description)
            
            # Run FARSITE Simulation
            if (impact_file == ''):
                self.run_farsite(row["Run Directory"], description)

        print() # wrap progress bar

        # Update Analysis Status
        callback('update', FARSITE_FINISHED)

        # Update Analysis Records
        self.config.update_record(status='FARSITE Finished')
