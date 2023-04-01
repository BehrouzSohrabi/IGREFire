import sys

from .inputs_generator import InputsGenerator

class Analysis:
    def __init__(self, config):
        self.steps = 10
        self.callback('header', 'IGREFire')
        self.config = config.build(self.callback)

    def _prepare_inputs(self):
        self.inputs = InputsGenerator(self.config, self.callback, step=1)
        self.inputs.run()

    def _run_simulations(self):
        # Run FARSITE simulations using the FarsiteSimulation class.
        pass

    def _analyze_results(self):
        # Process and analyze the simulation results.
        pass

    def _visualize_results(self):
        # Visualize the analysis results.
        pass

    def callback(self, type, message, step = 0, width = 80, separator = True):
        if type == 'ValueError':
            raise ValueError(message)
        elif type == 'header':
            if width < len(message):
                width = int(len(message)*1.1)
            space = (width - len(message)) // 2
            print('=' * width)
            print(' '*space + message)
            print('=' * width)
        else:
            print(f'Step {step}/{self.steps}: {message}')
            if width < len(message):
                width = int(len(message)*1.1)
            if separator:
                print('-' * width)

    def run(self):
        self._prepare_inputs()
        self._run_simulations()
        self._analyze_results()
        self._visualize_results()
